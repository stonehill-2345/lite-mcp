import mcpClientManager from '@/utils/mcpClient'
import { setCache, getCacheByKey } from '@/utils/storage'
import DebugLogger from '@/utils/DebugLogger'

/**
 * MCP Connection Service
 * Shared service providing MCP server connection, disconnection, reconnection and other functions
 */
export class McpConnectionService {
  constructor() {
    this.mcpClient = mcpClientManager
    this.logger = DebugLogger.createLogger('McpConnectionService')
    this.CONNECTION_CACHE_KEY = 'mcp_connection_service_state'
  }

  /**
   * Connect to MCP server
   * @param {Object} server - Server configuration object
   * @param {boolean} skipStateUpdate - Whether to skip state update
   * @returns {Promise<boolean>} - Whether connection was successful
   */
  async connectToServer(server, skipStateUpdate = false) {
    if (server.connecting || server.connected) {
      return false
    }

    server.connecting = true
    server.hasError = false

    try {
      this.logger.log(`🔌 Connecting to server: ${server.name} (Type: ${server.type})`)

      // Build connection configuration, supporting both SSE and Streamable HTTP types
      const config = {
        serverName: server.name,
        serverType: server.type,
        serverConfig: {
          command: server.command,
          args: server.args,
          env: server.env,
          url: server.url,
          description: server.description
        }
      }

      // If it's Streamable HTTP type, add apiPath configuration
      if (server.type === 'streamable-http' && server.apiPath) {
        config.serverConfig.apiPath = server.apiPath
      }

      this.logger.log(`🔗 Connection configuration:`, {
        serverName: server.name,
        type: server.type,
        url: server.url,
        apiPath: server.apiPath || 'None',
        hasApiPath: !!(server.type === 'streamable-http' && server.apiPath)
      })

      const sessionId = await this.mcpClient.connect(config)
      server.sessionId = sessionId
      server.connected = true
      server.enabled = true
      server.hasError = false

      this.logger.log(`🔗 Server ${server.name} connected successfully, Session ID: ${sessionId}`)

      // Get real tool list
      const tools = await this.mcpClient.getSessionTools(sessionId)
      this.logger.log(`🔧 Server ${server.name} obtained ${tools.length} tools`)

      server.tools = tools.map(tool => ({
        name: tool.name,
        description: tool.description || '',
        inputSchema: tool.inputSchema || {},
        enabled: false // Disabled by default, caller decides whether to enable
      }))

      this.logger.log(`✅ Server ${server.name} fully initialized`)
      return true
    } catch (error) {
      server.hasError = true
      server.connected = false
      server.enabled = false

      this.logger.error(`❌ Failed to connect to server ${server.name}:`, error)
      throw new Error(`Failed to connect to server ${server.name}: ${error.message}`)
    } finally {
      server.connecting = false
    }
  }

  /**
   * Disconnect from server
   * @param {Object} server - Server configuration object
   */
  async disconnectFromServer(server) {
    if (!server.connected || server.connecting) {
      return
    }

    const oldSessionId = server.sessionId

    try {
      this.logger.log(`🔌 Starting to disconnect server ${server.name} (sessionId: ${oldSessionId})`)

      if (server.sessionId) {
        // Clean up local state first to avoid operations using old sessionId during disconnection
        server.connected = false
        server.connecting = false
        server.hasError = false
        
        // Disconnect
        await this.mcpClient.disconnect(server.sessionId)
        
        this.logger.log(`🔌 Disconnected mcpClient connection ${server.name} (sessionId: ${oldSessionId})`)
      }

      // Completely clean up server state
      server.sessionId = null
      server.tools = []

      this.logger.log(`🔌 Cleaned up all state for server ${server.name}`)
    } catch (error) {
      this.logger.error(`❌ Failed to disconnect server ${server.name}:`, error)
      
      // Even if disconnection fails, clean up local state
      server.connected = false
      server.sessionId = null
      server.tools = []
      server.hasError = true
      
      throw error
    }
  }

  /**
   * Auto-connect enabled server list
   * @param {Array} serverConfigs - Server configuration list
   * @param {Object} options - Option configuration
   * @returns {Promise<Object>} - Connection result statistics
   */
  async autoConnectEnabledServers(serverConfigs, options = {}) {
    const {
      autoConnectOnLoad = true,
      enabledStateCheck = null, // Function to check if server is enabled
      onProgress = null, // Progress callback
      onComplete = null  // Completion callback
    } = options

    if (!autoConnectOnLoad) {
      this.logger.log('⏭️ Skipping auto-connection, user has disabled')
      return { total: 0, success: 0, failed: 0, connected: [] }
    }

    // Filter servers that need to be connected
    const enabledServers = serverConfigs.filter(server => {
      // If custom check function is provided, use it
      if (enabledStateCheck && typeof enabledStateCheck === 'function') {
        return enabledStateCheck(server) && !server.connected && !server.connecting
      }
      // Default check
      return server.enabled && !server.connected && !server.connecting
    })

    if (enabledServers.length === 0) {
      this.logger.log('ℹ️ No servers need auto-connection')
      return { total: 0, success: 0, failed: 0, connected: [] }
    }

    this.logger.log(`🔄 Starting auto-connection of ${enabledServers.length} enabled servers:`, enabledServers.map(s => s.name))

    // Connect all enabled servers in parallel
    const connectPromises = enabledServers.map(async (server, index) => {
      try {
        onProgress && onProgress({
          current: index + 1,
          total: enabledServers.length,
          serverName: server.name,
          status: 'connecting'
        })

        const success = await this.connectToServer(server, true)
        
        onProgress && onProgress({
          current: index + 1,
          total: enabledServers.length,
          serverName: server.name,
          status: success ? 'success' : 'failed'
        })

        return { server, success }
      } catch (error) {
        onProgress && onProgress({
          current: index + 1,
          total: enabledServers.length,
          serverName: server.name,
          status: 'failed',
          error: error.message
        })

        return { server, success: false, error }
      }
    })

    try {
      const results = await Promise.allSettled(connectPromises)

      // Statistics connection results
      const processedResults = results.map(result => 
        result.status === 'fulfilled' ? result.value : { success: false, error: result.reason }
      )

      const successResults = processedResults.filter(r => r.success)
      const failedResults = processedResults.filter(r => !r.success)
      const connectedServers = successResults.map(r => r.server)

      const stats = {
        total: enabledServers.length,
        success: successResults.length,
        failed: failedResults.length,
        connected: connectedServers
      }

      this.logger.log(`📊 Connection statistics:`, stats)

      // Call completion callback
      onComplete && onComplete(stats)

      return stats
    } catch (error) {
      this.logger.error('❌ Error occurred during auto-connection:', error)
      throw error
    }
  }

  /**
   * Reconnect all configured servers
   * @param {Array} serverConfigs - Server configuration list
   * @param {Object} options - Option configuration
   * @returns {Promise<Object>} - Reconnection result
   */
  async reconnectAllServers(serverConfigs, options = {}) {
    const {
      disconnectFirst = true, // Whether to disconnect existing connections first
      onProgress = null,
      onComplete = null
    } = options

    this.logger.log(`🔄 Starting reconnection operation, total ${serverConfigs.length} servers`)

    let disconnected = 0
    
    // If need to disconnect first
    if (disconnectFirst) {
      this.logger.log('🔌 Disconnecting existing connections...')
      
      const connectedServers = serverConfigs.filter(server => server.connected)
      
      for (const server of connectedServers) {
        try {
          await this.disconnectFromServer(server)
          disconnected++
          
          onProgress && onProgress({
            phase: 'disconnect',
            current: disconnected,
            total: connectedServers.length,
            serverName: server.name,
            status: 'disconnected'
          })
        } catch (error) {
          this.logger.error(`Failed to disconnect server ${server.name}:`, error)
        }
      }
      
      this.logger.log(`🔌 Disconnection completed, disconnected ${disconnected} servers`)
    }

    // Reconnect
    const reconnectStats = await this.autoConnectEnabledServers(serverConfigs, {
      autoConnectOnLoad: true,
      onProgress: (progressInfo) => {
        onProgress && onProgress({
          phase: 'reconnect',
          ...progressInfo
        })
      },
      onComplete
    })

    const finalStats = {
      ...reconnectStats,
      disconnected
    }

    this.logger.log(`🔄 Reconnection operation completed:`, finalStats)
    return finalStats
  }

  /**
   * Get all connected tools list
   * @param {Array} serverConfigs - Server configuration list
   * @returns {Array} - Connected tools list
   */
  getConnectedTools(serverConfigs) {
    const connectedTools = []
    
    serverConfigs.forEach(server => {
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
   * Refresh server tool list
   * @param {Object} server - Server configuration object
   * @returns {Promise<Array>} - Refreshed tool list
   */
  async refreshServerTools(server) {
    if (!server.connected || !server.sessionId) {
      throw new Error(`Server ${server.name} is not connected`)
    }

    try {
      const tools = await this.mcpClient.refreshTools(server.sessionId)
      
      // Maintain original tool enabled status
      const oldToolsMap = new Map()
      if (server.tools) {
        server.tools.forEach(tool => {
          oldToolsMap.set(tool.name, tool.enabled)
        })
      }

      server.tools = tools.map(tool => ({
        name: tool.name,
        description: tool.description || '',
        inputSchema: tool.inputSchema || {},
        enabled: oldToolsMap.get(tool.name) || false
      }))

      this.logger.log(`🔧 Server ${server.name} tool list refreshed, total ${tools.length} tools`)
      return server.tools
    } catch (error) {
      this.logger.error(`❌ Failed to refresh tools for server ${server.name}:`, error)
      server.hasError = true
      throw error
    }
  }

  /**
   * Clean up all connections
   */
  async cleanup() {
    try {
      await this.mcpClient.cleanup()
      this.logger.log('🧹 MCP connection cleanup completed')
    } catch (error) {
      this.logger.error('❌ MCP connection cleanup failed:', error)
    }
  }
}

// Export singleton instance
export default new McpConnectionService()