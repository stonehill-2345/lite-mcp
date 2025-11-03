import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js'
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js'
import DebugLogger from "@/utils/DebugLogger"

const logger = DebugLogger.createLogger('mcpClient')

/**
 * MCP Client Manager
 * Implementation using official @modelcontextprotocol/sdk, supports only SSE and Streamable HTTP
 */
class McpClientManager {
  constructor() {
    // Store client instances
    this.clients = new Map()
    // Store session information
    this.sessions = new Map()
    // Store connection status
    this.connectionStatus = new Map()
    // Store available tools
    this.availableTools = new Map()
    // Store chat history
    this.chatHistory = new Map()
  }

  /**
   * Connect to MCP server
   * @param {Object} config - Connection configuration
   * @returns {Promise<string>} Session ID
   */
  async connect(config) {
    const sessionId = `session-${Date.now()}-${Math.random().toString(36).substring(2, 15)}`
    
    try {
      logger.log(`🔗 Connecting to MCP server [${config.serverName}]:`, config)
      
      // Select appropriate connection method based on server type
      switch (config.serverType) {
        case 'sse':
          await this.connectSSE(config, sessionId)
          break
        case 'streamable-http':
          await this.connectStreamableHTTP(config, sessionId)
          break
        default:
          throw new Error(`Unsupported server type: ${config.serverType}`)
      }

      logger.log(`✅ MCP server connected successfully [${config.serverName}]:`, sessionId)
      return sessionId
    } catch (error) {
      console.error(`❌ MCP server connection failed [${config.serverName}]:`, error)
      throw error
    }
  }

  /**
   * Connect to SSE MCP server
   */
  async connectSSE(config, sessionId) {
    const client = new Client({
      name: 'mcp-web-client',
      version: '1.0.0'
    })

    // Create SSE transport
    const transport = new SSEClientTransport(new URL(config.serverConfig.url))
    
    // Store client and transport
    this.clients.set(sessionId, { client, transport })
    
    // Store session information
    this.sessions.set(sessionId, {
      serverName: config.serverName,
      serverType: config.serverType,
      config: config.serverConfig,
      connectedAt: new Date()
    })
    
    // Initialize chat history
    this.chatHistory.set(sessionId, [])
    
    try {
      // Connect to server
      await client.connect(transport)
      
      // Set connection status
      this.connectionStatus.set(sessionId, 'connected')
      
      // Get tool list
      const tools = await this.getTools(sessionId)
      this.availableTools.set(sessionId, tools)
      
    } catch (error) {
      console.warn(`⚠️ SSE connection failed [${sessionId}]:`, error)
      this.connectionStatus.set(sessionId, 'disconnected')
      this.availableTools.set(sessionId, [])
    }
  }

  

  /**
   * Connect to Streamable HTTP MCP server
   */
  async connectStreamableHTTP(config, sessionId) {
    const client = new Client({
      name: 'cursor-vscode',
      version: '1.0.0'
    })

    // Create Streamable HTTP transport
    const baseUrl = new URL(config.serverConfig.url)
    const customHeaders = config.serverConfig?.headers
    const hasCustomHeaders = customHeaders && typeof customHeaders === 'object' && Object.keys(customHeaders).length > 0

    const transportOptions = hasCustomHeaders
      ? {
          requestInit: {
            headers: { ...customHeaders }
          }
        }
      : undefined

    const transport = new StreamableHTTPClientTransport(baseUrl, transportOptions)
    
    // Store client and transport
    this.clients.set(sessionId, { client, transport })
    // Store session information
    this.sessions.set(sessionId, {
      serverName: config.serverName,
      serverType: config.serverType,
      config: config.serverConfig,
      connectedAt: new Date()
    })
    
    // Initialize chat history
    this.chatHistory.set(sessionId, [])
    
    try {
      // Connect to server
      await client.connect(transport)
      
      // Set connection status
      this.connectionStatus.set(sessionId, 'connected')
      
      // Get tool list
      const tools = await this.getTools(sessionId)
      this.availableTools.set(sessionId, tools)
      
    } catch (error) {
      console.warn(`⚠️ Streamable HTTP connection failed [${sessionId}]:`, error)
      this.connectionStatus.set(sessionId, 'disconnected')
      this.availableTools.set(sessionId, [])
    }
  }



  /**
   * Get tool list
   */
  async getTools(sessionId) {
    try {
      const clientInfo = this.clients.get(sessionId)
      const session = this.sessions.get(sessionId)
      
      if (!clientInfo || !session) {
        return []
      }

      if (clientInfo.client && clientInfo.client.listTools) {
        // Use official SDK's listTools method
        const response = await clientInfo.client.listTools()
        return response.tools || []
      }
      
      return []
    } catch (error) {
      console.error(`Failed to get tool list [${sessionId}]:`, error)
      return []
    }
  }



  /**
   * Call tool
   */
  async callTool(sessionId, toolName, parameters = {}) {
    try {
      const clientInfo = this.clients.get(sessionId)
      const session = this.sessions.get(sessionId)
      
      if (!clientInfo || !session) {
        throw new Error(`Session ${sessionId} does not exist or is not connected`)
      }

      // Check if tool exists
      const availableTools = this.availableTools.get(sessionId) || []
      const tool = availableTools.find(t => t.name === toolName)
      
      if (!tool) {
        throw new Error(`Tool ${toolName} is not available in session ${sessionId}. Available tools: ${availableTools.map(t => t.name).join(', ')}`)
      }

      let result

      if (clientInfo.client && clientInfo.client.callTool) {
        // Use official SDK's callTool method
        result = await clientInfo.client.callTool({
          name: toolName,
          arguments: parameters
        })
      } else {
        throw new Error(`Unsupported server type: ${session.serverType}`)
      }

      logger.log(`✅ Tool call successful: ${toolName}`, result)

      // Record tool call in chat history
      const chatHistory = this.chatHistory.get(sessionId) || []
      chatHistory.push({
        type: 'tool_call',
        toolName,
        parameters,
        result,
        timestamp: new Date()
      })
      this.chatHistory.set(sessionId, chatHistory)

      return result

    } catch (error) {
      console.error(`❌ Tool call failed: ${toolName}`, {
        sessionId,
        parameters,
        error: error.message
      })
      
      // Record failed tool call
      const chatHistory = this.chatHistory.get(sessionId) || []
      chatHistory.push({
        type: 'tool_call_error',
        toolName,
        parameters,
        error: error.message,
        timestamp: new Date()
      })
      this.chatHistory.set(sessionId, chatHistory)
      
      throw error
    }
  }



  /**
   * Disconnect
   */
  async disconnect(sessionId) {
    try {
      const clientInfo = this.clients.get(sessionId)
      const session = this.sessions.get(sessionId)
      
      if (!clientInfo || !session) {
        return
      }

      // Disconnect
      if (clientInfo.client && clientInfo.client.close) {
        await clientInfo.client.close()
      }

      // Clean up local state
      this.clients.delete(sessionId)
      this.sessions.delete(sessionId)
      this.connectionStatus.delete(sessionId)
      this.availableTools.delete(sessionId)
      this.chatHistory.delete(sessionId)

      logger.log(`🔌 MCP connection disconnected [${sessionId}]`)
    } catch (error) {
      console.error('MCP disconnection failed:', error)
      throw error
    }
  }

  /**
   * Refresh tool list
   */
  async refreshTools(sessionId) {
    try {
      const tools = await this.getTools(sessionId)
      this.availableTools.set(sessionId, tools)
      return tools
    } catch (error) {
      console.error('Failed to refresh tool list:', error)
      return []
    }
  }

  /**
   * Get session tools
   */
  getSessionTools(sessionId) {
    return this.availableTools.get(sessionId) || []
  }

  /**
   * Get connection status
   */
  getConnectionStatus(sessionId) {
    return this.connectionStatus.get(sessionId) || 'disconnected'
  }

  /**
   * Get all active sessions
   */
  getActiveSessions() {
    return Array.from(this.sessions.entries()).map(([sessionId, session]) => ({
      sessionId,
      ...session,
      status: this.connectionStatus.get(sessionId),
      toolsCount: (this.availableTools.get(sessionId) || []).length
    }))
  }

  /**
   * Get chat history
   */
  getChatHistory(sessionId) {
    return this.chatHistory.get(sessionId) || []
  }

  /**
   * Clean up all connections
   */
  async cleanup() {
    try {
      const sessionIds = Array.from(this.sessions.keys())
      await Promise.all(sessionIds.map(sessionId => this.disconnect(sessionId)))

      logger.log('🧹 MCP client cleanup completed')
    } catch (error) {
      console.error('Failed to clean up MCP connections:', error)
    }
  }
}

// Create global instance
const mcpClientManager = new McpClientManager()

export default mcpClientManager