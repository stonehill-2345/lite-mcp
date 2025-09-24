import { ref, reactive } from 'vue'
import { getCacheByKey, setCache } from '@/utils/storage.js'
import DebugLogger from "@/utils/DebugLogger";

const logger = DebugLogger.createLogger('McpStateManager')

/**
 * MCP State Manager
 * Acts as an intermediary layer between system tools and components, centrally managing MCP state
 */
class McpStateManager {
  constructor() {
    // Server configuration state
    this.serverConfigs = ref([])
    
    // User state cache
    this.userState = reactive({
      enabledServers: {},
      enabledTools: {},
      expandedServers: {},
      lastConnectedTime: null,
      autoConnectOnLoad: true
    })
    
    // Connection status
    this.connectionStatus = reactive({
      connecting: false,
      lastReconnectTime: null,
      reconnectResult: null
    })
    
    // Event listeners
    this.listeners = new Map()
    
    // Cache key names
    this.CONFIG_CACHE_KEY = 'mcp_config_cache'
    this.USER_STATE_CACHE_KEY = 'mcp_user_state_cache'
    
    // Initialization
    this.init()
  }

  /**
   * Initialize state manager
   */
  init() {
    this.loadFromCache()
  }

  /**
   * Load state from cache
   */
  loadFromCache() {
    // Load server configuration
    const configData = this.getMcpConfigFromCache()
    this.serverConfigs.value = configData.serverConfigs || []
    
    // Load user state
    const userState = this.getUserStateFromCache()
    Object.assign(this.userState, userState)
  }

  /**
   * Read MCP configuration from cache
   */
  getMcpConfigFromCache() {
    const configJson = getCacheByKey(this.CONFIG_CACHE_KEY)
    
    if (!configJson) {
      return { serverConfigs: [] }
    }

    try {
      const config = JSON.parse(configJson)
      if (!config.mcpServers) {
        return { serverConfigs: [] }
      }

      const servers = []
      let originalIndex = 0

      for (const [name, serverConfig] of Object.entries(config.mcpServers)) {
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
        servers.push(server)
      }

      // Sort by timestamp (newest first)
      servers.sort((a, b) => {
        if (a.addedAt && b.addedAt) {
          return b.addedAt - a.addedAt
        }
        if (a.addedAt && !b.addedAt) return -1
        if (!a.addedAt && b.addedAt) return 1
        return a.originalIndex - b.originalIndex
      })

      return { serverConfigs: servers }
    } catch (error) {
      console.error('[McpStateManager] Failed to parse MCP configuration:', error)
      return { serverConfigs: [] }
    }
  }

  /**
   * Read user state from cache
   */
  getUserStateFromCache() {
    const userState = getCacheByKey(this.USER_STATE_CACHE_KEY)
    
    return {
      enabledServers: userState?.enabledServers || {},
      enabledTools: userState?.enabledTools || {},
      expandedServers: userState?.expandedServers || {},
      lastConnectedTime: userState?.lastConnectedTime,
      autoConnectOnLoad: userState?.autoConnectOnLoad !== false
    }
  }

  /**
   * Apply user state to server configuration
   */
  applyUserStateToServers() {
    this.serverConfigs.value.forEach(server => {
      // Restore server enabled state
      if (this.userState.enabledServers.hasOwnProperty(server.name)) {
        server.enabled = this.userState.enabledServers[server.name]
      }

      // Restore server expanded state
      if (this.userState.expandedServers.hasOwnProperty(server.name)) {
        server.toolsExpanded = this.userState.expandedServers[server.name]
      }

      // Restore tool enabled state
      if (server.tools) {
        server.tools.forEach(tool => {
          const toolKey = `${server.name}.${tool.name}`
          if (this.userState.enabledTools.hasOwnProperty(toolKey)) {
            tool.enabled = this.userState.enabledTools[toolKey]
            logger.log(`[McpStateManager] Restored tool state from cache ${toolKey}: ${tool.enabled}`)
          } else {
            // For tools without cache records, enable by default for immediate use
            tool.enabled = true
            logger.log(`[McpStateManager] Tool ${toolKey} has no cache record, enabled by default`)
          }
        })
      }
    })
  }

  /**
   * Update server states
   */
  updateServerStates(connectedServers) {
    logger.log('[McpStateManager] Starting to update server status:', connectedServers.length, 'servers')
    
    // First reset all server connection states
    this.serverConfigs.value.forEach(server => {
      server.connected = false
      server.connecting = false
      server.hasError = false
      server.sessionId = null
    })
    
    // Update reconnected server states
    connectedServers.forEach(connectedServer => {
      const server = this.serverConfigs.value.find(s => s.name === connectedServer.name)
      if (server) {
        logger.log(`[McpStateManager] Update server ${server.name} status:`, {
          connected: true,
          toolsCount: connectedServer.tools?.length || 0
        })
        
        server.connected = true
        server.enabled = true
        server.hasError = false
        server.sessionId = connectedServer.sessionId
        server.connecting = false
        
        // Update tool list
        if (connectedServer.tools && Array.isArray(connectedServer.tools)) {
          server.tools = connectedServer.tools.map(tool => {
            const toolKey = `${server.name}.${tool.name}`
            const enabledFromCache = this.userState.enabledTools.hasOwnProperty(toolKey)
              ? this.userState.enabledTools[toolKey]
              : false

            return {
              name: tool.name,
              description: tool.description || '',
              inputSchema: tool.inputSchema || {},
              enabled: enabledFromCache
            }
          })
        } else {
          server.tools = []
        }
      } else {
        console.warn(`[McpStateManager] Server configuration not found: ${connectedServer.name}`)
      }
    })
    
    // Save state immediately
    this.saveUserState()
  }

  /**
   * Save user state to cache
   */
  saveUserState() {
    const currentState = {
      enabledServers: {},
      enabledTools: {},
      expandedServers: {},
      lastConnectedTime: Date.now(),
      autoConnectOnLoad: this.userState.autoConnectOnLoad
    }

    // Collect server enabled state
    this.serverConfigs.value.forEach(server => {
      currentState.enabledServers[server.name] = server.enabled
      currentState.expandedServers[server.name] = server.toolsExpanded

      // Collect tool enabled state
      if (server.tools) {
        server.tools.forEach(tool => {
          const toolKey = `${server.name}.${tool.name}`
          currentState.enabledTools[toolKey] = tool.enabled
        })
      }
    })

    Object.assign(this.userState, currentState)
    setCache(this.USER_STATE_CACHE_KEY, currentState)
    
    logger.log('[McpStateManager] User state saved')
  }

  /**
   * Get count of enabled tools
   */
  getEnabledToolsCount() {
    return Object.values(this.userState.enabledTools).filter(enabled => enabled).length
  }

  /**
   * Get count of enabled servers
   */
  getEnabledServersCount() {
    return Object.values(this.userState.enabledServers).filter(enabled => enabled).length
  }

  /**
   * Get list of connected tools (only return user-enabled tools)
   */
  getConnectedTools() {
    const connectedTools = []
    this.serverConfigs.value.forEach(server => {
      if (server.connected && server.enabled && server.tools) {
        server.tools.forEach(tool => {
          if (tool.enabled) {
            connectedTools.push({
              name: tool.name,
              description: tool.description,
              inputSchema: tool.inputSchema,
              serverName: server.name,
              sessionId: server.sessionId,
              enabled: true
            })
          }
        })
      }
    })
    return connectedTools
  }

  /**
   * Get list of all connected tools (including disabled tools)
   */
  getAllConnectedTools() {
    const connectedTools = []
    this.serverConfigs.value.forEach(server => {
      if (server.connected && server.tools) {
        server.tools.forEach(tool => {
          connectedTools.push({
            name: tool.name,
            description: tool.description,
            inputSchema: tool.inputSchema,
            serverName: server.name,
            sessionId: server.sessionId,
            enabled: tool.enabled
          })
        })
      }
    })
    return connectedTools
  }

  /**
   * Add event listener
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event).add(callback)
  }

  /**
   * Remove event listener
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(callback)
    }
  }

  /**
   * Emit event
   */
  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`[McpStateManager] Event listener error:`, error)
        }
      })
    }
  }

  /**
   * Refresh state (reload from cache)
   */
  refresh() {
    this.loadFromCache()
    this.emit('state-refreshed', {
      servers: this.serverConfigs.value.length,
      enabledTools: this.getEnabledToolsCount()
    })
  }

  /**
   * Clean up resources
   */
  cleanup() {
    this.listeners.clear()
    logger.log('[McpStateManager] Resources cleaned up')
  }
}

// Export singleton instance
export default new McpStateManager()