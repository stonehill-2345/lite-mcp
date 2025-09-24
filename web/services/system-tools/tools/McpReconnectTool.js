import { SystemTool } from '@/services/system-tools/base/SystemTool.js'
import mcpConnectionService from '@/services/mcp/McpConnectionService.js'
import { getCacheByKey } from '@/utils/storage.js'
import DebugLogger from "@/utils/DebugLogger";

const logger = DebugLogger.createLogger('McpReconnectTool')

/**
 * MCP Reconnect Tool
 * Reconnect to historically configured and enabled MCP servers
 */
export class McpReconnectTool extends SystemTool {
  constructor(config = {}) {
    super({
      name: 'mcp_reconnect',
      description: 'Reconnect to MCP server, first disconnect existing connections to clean up historical session_id, then re-establish connections to resolve connection state inconsistency issues',
      category: 'mcp',
      version: '1.0.0',
      author: 'system',
      inputSchema: {
        type: 'object',
        properties: {
          reconnectType: {
            type: 'string',
            description: 'Reconnect type',
            enum: ['auto', 'all', 'enabled_only'],
            default: 'auto'
          },
          disconnectFirst: {
            type: 'boolean',
            description: 'Whether to disconnect existing connections first to clean up historical session_id (recommended to enable, can resolve connection state inconsistency issues)',
            default: true
          },
          showProgress: {
            type: 'boolean',
            description: 'Whether to show connection progress',
            default: true
          }
        },
        required: []
      },
      config: {
        timeout: 30000, // 30 second timeout
        maxRetries: 3,
        retryDelay: 2000
      },
      ...config
    })
  }

  /**
   * Execute MCP reconnection - Simulate the manual disable and enable operation flow
   * 1. First disconnect existing connections, clean up historical session_id and connection status
   * 2. Then reconnect to enabled servers
   * 3. Restore tool enable status
   */
  async doExecute(parameters, context) {
    logger.log(`[McpReconnectTool] ================================`)
    logger.log(`[McpReconnectTool] Starting MCP reconnection`)
    logger.log(`[McpReconnectTool] Received parameters:`, parameters)
    logger.log(`[McpReconnectTool] Context information:`, context)

    try {
      // 1. Load MCP configuration from cache
      logger.log(`[McpReconnectTool] Step 1: Load MCP configuration from cache`)
      const configJson = getCacheByKey('mcp_config_cache')

      if (!configJson) {
        logger.log(`[McpReconnectTool] ❌ MCP configuration cache not found`)
        return {
          success: false,
          message: 'MCP reconnection failed: MCP configuration not found',
          details: { error: 'no_config_found' }
        }
      }
      
      logger.log(`[McpReconnectTool] ✅ Found MCP configuration cache, length: ${configJson.length} characters`)

      // 2. Parse configuration
      logger.log(`[McpReconnectTool] Step 2: Parse MCP configuration`)
      const config = JSON.parse(configJson)
      logger.log(`[McpReconnectTool] Parsed configuration:`, config)
      
      if (!config.mcpServers) {
        logger.log(`[McpReconnectTool] ❌ Missing mcpServers field in configuration`)
        return {
          success: false,
          message: 'MCP reconnection failed: Invalid configuration format',
          details: { error: 'invalid_config_format' }
        }
      }
      
      const serverNames = Object.keys(config.mcpServers)
      logger.log(`[McpReconnectTool] ✅ Found ${serverNames.length} server configurations:`, serverNames)

      // 3. Build server configuration list (reuse McpConfigEditor logic)
      logger.log(`[McpReconnectTool] Step 3: Build server configuration list`)
      const serverConfigs = []
      let originalIndex = 0

      for (const [name, serverConfig] of Object.entries(config.mcpServers)) {
        logger.log(`[McpReconnectTool] Building server configuration: ${name}`, serverConfig)
        
        const server = {
          id: `server_${Date.now()}_${Math.random()}`,
          name,
          type: serverConfig.type || 'sse',
          url: serverConfig.url || '',
          apiPath: serverConfig.apiPath || '',
          description: serverConfig.description || '',
          enabled: false,
          connected: false,
          connecting: false,
          tools: [],
          toolsExpanded: false,
          hasError: false,
          sessionId: null,
          addedAt: serverConfig.addedAt || null,
          originalIndex: originalIndex++
        }
        
        logger.log(`[McpReconnectTool] Built server object:`, {
          name: server.name,
          type: server.type,
          url: server.url,
          apiPath: server.apiPath,
          enabled: server.enabled,
          connected: server.connected
        })
        
        serverConfigs.push(server)
      }
      
      logger.log(`[McpReconnectTool] ✅ Built ${serverConfigs.length} server configurations`)

      // 4. Load user state and apply to server configurations
      logger.log(`[McpReconnectTool] Step 4: Load user state cache`)
      const userStateCache = getCacheByKey('mcp_user_state_cache') || {
        enabledServers: {},
        enabledTools: {},
        expandedServers: {},
        autoConnectOnLoad: true
      }
      
      logger.log(`[McpReconnectTool] User state cache:`, {
        enabledServersCount: Object.keys(userStateCache.enabledServers).length,
        enabledToolsCount: Object.keys(userStateCache.enabledTools).length,
        autoConnectOnLoad: userStateCache.autoConnectOnLoad,
        enabledServers: userStateCache.enabledServers,
        enabledTools: userStateCache.enabledTools
      })

      // Apply user state to server configurations
      logger.log(`[McpReconnectTool] Apply user state to server configurations`)
      serverConfigs.forEach(server => {
        const originalEnabled = server.enabled
        const originalExpanded = server.toolsExpanded
        
        if (userStateCache.enabledServers.hasOwnProperty(server.name)) {
          server.enabled = userStateCache.enabledServers[server.name]
        }
        if (userStateCache.expandedServers.hasOwnProperty(server.name)) {
          server.toolsExpanded = userStateCache.expandedServers[server.name]
        }
        
        logger.log(`[McpReconnectTool] Server ${server.name}: enabled ${originalEnabled} -> ${server.enabled}, expanded ${originalExpanded} -> ${server.toolsExpanded}`)
      })
      
      const enabledServers = serverConfigs.filter(s => s.enabled)
      logger.log(`[McpReconnectTool] ✅ State application complete, enabled servers: ${enabledServers.length}:`, enabledServers.map(s => s.name))

      // 5. Disconnect existing connections first, then reconnect (simulate manual disable and enable process)
      logger.log(`[McpReconnectTool] Step 5: Start reconnection operation`)
      const { disconnectFirst = true } = parameters
      
      logger.log(`[McpReconnectTool] Reconnection parameters:`, { disconnectFirst })
      logger.log(`[McpReconnectTool] Calling mcpConnectionService.reconnectAllServers`)
      logger.log(`[McpReconnectTool] Number of server configurations passed in: ${serverConfigs.length}`)
      
      // Pre-extract context information to ensure access in callbacks
      const reactEngine = context?.reactEngine
      const chatServiceFromContext = reactEngine?.chatService
      
      const result = await mcpConnectionService.reconnectAllServers(serverConfigs, {
        disconnectFirst, // Disconnect existing connections first, clean up historical session_id
        onProgress: (progressInfo) => {
          const phase = progressInfo.phase === 'disconnect' ? 'Disconnect' : 'Reconnect'
          logger.log(`[McpReconnectTool] 🔄 ${phase} progress: (${progressInfo.current}/${progressInfo.total}) - ${progressInfo.serverName} - ${progressInfo.status}`)
          if (progressInfo.error) {
            logger.log(`[McpReconnectTool] ❌ Error in progress:`, progressInfo.error)
          }
        },
        onComplete: async (stats) => {
          logger.log(`[McpReconnectTool] 📊 Reconnection statistics complete:`, stats)
          logger.log(`[McpReconnectTool] Details of successfully connected servers:`, stats.connected?.map(s => ({
            name: s.name,
            sessionId: s.sessionId,
            toolsCount: s.tools?.length || 0,
            connected: s.connected
          })))
          
          // Apply tool state (ensure correct recovery from cache)
          if (stats.connected && stats.connected.length > 0) {
            logger.log(`[McpReconnectTool] 🔧 Start applying tool state to ${stats.connected.length} connected servers`)
            
            // Ensure tool state application does not trigger additional network requests
            stats.connected.forEach(server => {
              logger.log(`[McpReconnectTool] Processing tool state for server ${server.name}:`, {
                toolsCount: server.tools?.length || 0,
                sessionId: server.sessionId,
                connected: server.connected
              })
              
              if (server.tools && server.tools.length > 0) {
                let appliedCount = 0
                let totalCachedCount = 0
                
                // Note: This only modifies local tool object properties, should not trigger any network requests
                server.tools.forEach(tool => {
                  const toolKey = `${server.name}.${tool.name}`
                  if (userStateCache.enabledTools.hasOwnProperty(toolKey)) {
                    totalCachedCount++
                    const cachedEnabled = userStateCache.enabledTools[toolKey]
                    const originalEnabled = tool.enabled
                    
                    // Directly modify the tool object's enabled property, do not call any methods that might trigger network requests
                    tool.enabled = cachedEnabled
                    if (cachedEnabled) appliedCount++
                    
                    logger.log(`[McpReconnectTool] Tool ${toolKey}: ${originalEnabled} -> ${cachedEnabled} (pure local modification)`)
                  }
                })
                
                logger.log(`[McpReconnectTool] ✅ Server ${server.name} tool state processing complete: ${appliedCount}/${totalCachedCount} enabled (no network requests)`)
              } else {
                logger.log(`[McpReconnectTool] ⚠️ Server ${server.name} has no tools`)
              }
            })
            
            logger.log(`[McpReconnectTool] 🔧 All server tool state applications complete (local state modification only)`)
            
            // [Key fix] Immediately sync state to ChatService and ReActEngine
            logger.log(`[McpReconnectTool] 🔄 Immediately sync state to ChatService and ReActEngine`)
            try {
              // Try multiple ways to get ChatService instance
              let chatService = null
              
              // Method 1: Try to get from global state
              if (typeof window !== 'undefined' && window.__chatService) {
                chatService = window.__chatService
                logger.log(`[McpReconnectTool] Get ChatService instance from global state`)
              }
              
              // Method 2: Use pre-extracted ChatService instance
              if (!chatService && chatServiceFromContext) {
                chatService = chatServiceFromContext
                logger.log(`[McpReconnectTool] Get ChatService instance from pre-extracted context`)
              }
              
              if (chatService && typeof chatService.updateAvailableTools === 'function') {
                logger.log(`[McpReconnectTool] Found ChatService instance, start immediate state update`)
                
                // Build new tool list (including new session_id)
                const newTools = []
                const newSessions = []
                
                stats.connected.forEach(server => {
                  logger.log(`[McpReconnectTool] Processing tool and session information for server ${server.name}:`, {
                    sessionId: server.sessionId,
                    toolsCount: server.tools?.length || 0
                  })
                  
                  // Add session information (new session_id)
                  newSessions.push({
                    id: server.sessionId,
                    name: server.name,
                    url: server.url,
                    toolCount: server.tools?.length || 0,
                    serverType: server.type || 'unknown',
                    connected: true
                  })
                  
                  // Add tool information (with new session_id)
                  if (server.tools && Array.isArray(server.tools)) {
                    server.tools.forEach(tool => {
                      newTools.push({
                        name: tool.name,
                        description: tool.description || '',
                        inputSchema: tool.inputSchema || {},
                        enabled: tool.enabled || false,
                        serverName: server.name,
                        sessionId: server.sessionId // Key: use new session_id
                      })
                    })
                  }
                })
                
                logger.log(`[McpReconnectTool] Built new state:`, {
                  toolsCount: newTools.length,
                  sessionsCount: newSessions.length,
                  sessions: newSessions.map(s => ({ id: s.id, name: s.name }))
                })
                
                // Immediately update ChatService state (this will automatically update ReActEngine)
                chatService.updateAvailableTools(newTools, newSessions)
                
                logger.log(`[McpReconnectTool] ✅ ChatService and ReActEngine state immediately updated`)
              } else {
                logger.log(`[McpReconnectTool] ⚠️ ChatService instance or updateAvailableTools method not found`)
              }
            } catch (error) {
              console.error(`[McpReconnectTool] Failed to immediately update ChatService state:`, error)
            }
          } else {
            logger.log(`[McpReconnectTool] ⚠️ No successfully connected servers`)
          }
        }
      })
      
      logger.log(`[McpReconnectTool] ✅ reconnectAllServers call complete, result:`, result)

      // 6. Reconnection complete, state sync has been handled in onComplete callback
      logger.log(`[McpReconnectTool] Step 6: Reconnection complete`)
      logger.log(`[McpReconnectTool] State sync has been immediately handled in onComplete callback to ensure the first tool call uses the new session_id`)

      // Build detailed reconnection message
      logger.log(`[McpReconnectTool] Step 7: Build return result`)
      let message = ''
      if (result.success > 0) {
        message = `MCP reconnection successful: `
        if (disconnectFirst && result.disconnected > 0) {
          message += `First disconnected ${result.disconnected} existing connections, then reconnected ${result.success} servers`
        } else {
          message += `Reconnected ${result.success} servers`
        }
        if (result.failed > 0) {
          message += `, ${result.failed} connections failed`
        }
        
        // If ChatService state was successfully updated, add note
        if (result.connected && result.connected.length > 0) {
          message += `, ChatService and ReActEngine state synchronized and updated`
        }
      } else {
        if (result.total > 0) {
          message = `MCP reconnection failed: All server connections failed`
          if (disconnectFirst && result.disconnected > 0) {
            message += ` (disconnected ${result.disconnected} existing connections)`
          }
        } else {
          message = `MCP reconnection failed: No enabled servers`
        }
      }

      const finalResult = {
        success: result.success > 0,
        message,
        statistics: {
          total: result.total,
          success: result.success,
          failed: result.failed,
          disconnected: result.disconnected || 0,
          disconnectFirst
        },
        details: {
          connectedServers: result.connected?.map(s => s.name) || [],
          timestamp: Date.now()
        }
      }
      
      logger.log(`[McpReconnectTool] ✅ Final return result:`, finalResult)
      logger.log(`[McpReconnectTool] ================================`)
      return finalResult

    } catch (error) {
      console.error('[McpReconnectTool] ❌❌❌ Exception occurred during reconnection process ❌❌❌')
      console.error('[McpReconnectTool] Error details:', error)
      console.error('[McpReconnectTool] Error stack:', error.stack)
      
      const errorResult = {
        success: false,
        message: `MCP reconnection failed: ${error.message}`,
        error: error.message,
        details: {
          timestamp: Date.now(),
          stack: error.stack
        }
      }
      
      logger.log('[McpReconnectTool] Error return result:', errorResult)
      logger.log(`[McpReconnectTool] ================================`)
      return errorResult
    }
  }

  /**
   * Test tool connectivity (check if MCP configuration exists)
   */
  async testConnection() {
    try {
      // Check MCP configuration cache
      const configJson = getCacheByKey('mcp_config_cache')
      if (!configJson) {
        return {
          status: 'warning',
          message: 'MCP server configuration not found',
          details: {
            configExists: false,
            serverCount: 0,
            enabledCount: 0
          }
        }
      }

      const config = JSON.parse(configJson)
      const serverCount = config.mcpServers ? Object.keys(config.mcpServers).length : 0
      
      // Check user state
      const userStateCache = getCacheByKey('mcp_user_state_cache') || {}
      const enabledCount = userStateCache.enabledServers 
        ? Object.values(userStateCache.enabledServers).filter(enabled => enabled).length 
        : 0

      return {
        status: serverCount > 0 ? 'success' : 'warning',
        message: serverCount > 0 
          ? `Detected ${serverCount} MCP server configurations, of which ${enabledCount} are enabled`
          : 'MCP server configuration not found',
        details: {
          configExists: serverCount > 0,
          serverCount,
          enabledCount,
          hasUserState: !!userStateCache.lastConnectedTime
        }
      }
    } catch (error) {
      return {
        status: 'error',
        message: `Failed to detect MCP configuration: ${error.message}`,
        details: { error: error.message }
      }
    }
  }

  /**
   * Get tool status information
   */
  getStatus() {
    try {
      const configJson = getCacheByKey('mcp_config_cache')
      const config = configJson ? JSON.parse(configJson) : {}
      const serverCount = config.mcpServers ? Object.keys(config.mcpServers).length : 0
      
      const userStateCache = getCacheByKey('mcp_user_state_cache') || {}
      const enabledCount = userStateCache.enabledServers 
        ? Object.values(userStateCache.enabledServers).filter(enabled => enabled).length 
        : 0
      const enabledToolsCount = userStateCache.enabledTools 
        ? Object.values(userStateCache.enabledTools).filter(enabled => enabled).length 
        : 0
      
      return {
        name: this.name,
        enabled: this.enabled,
        configurationCount: serverCount,
        enabledServersCount: enabledCount,
        enabledToolsCount: enabledToolsCount,
        lastConnectedTime: userStateCache.lastConnectedTime,
        autoConnectEnabled: userStateCache.autoConnectOnLoad !== false
      }
    } catch (error) {
      return {
        name: this.name,
        enabled: this.enabled,
        configurationCount: 0,
        enabledServersCount: 0,
        enabledToolsCount: 0,
        lastConnectedTime: null,
        autoConnectEnabled: true
      }
    }
  }
}