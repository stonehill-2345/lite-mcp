import DebugLogger from '@/utils/DebugLogger.js'

/**
 * Tool Resolution Service
 * Unified management system for finding, resolving, and mapping system tools and MCP tools
 */
export class ToolResolutionService {
  constructor() {
    this.logger = DebugLogger.createLogger('ToolResolutionService')
  }

  /**
   * Find the session corresponding to a tool
   * @param {string} toolName - Tool name
   * @param {Array} systemTools - System tools list
   * @param {Array} availableTools - Available MCP tools list
   * @param {Array} enabledSessions - Enabled sessions list
   * @returns {string|null} Session ID, returns 'system' for system tools, null if not found
   */
  findToolSession(toolName, systemTools = [], availableTools = [], enabledSessions = []) {
    this.logger.log('🔍 Finding tool session:', {
      toolName,
      systemToolsCount: systemTools.length,
      availableToolsCount: availableTools.length,
      enabledSessionsCount: enabledSessions.length
    })

    // First check if it's a system tool
    const systemTool = systemTools.find(tool => tool.function.name === toolName)
    if (systemTool) {
      this.logger.log('✅ System tool found:', toolName)
      return 'system' // Return special identifier indicating this is a system tool
    }

    // If not a system tool, find MCP session
    return this.findMcpToolSession(toolName, availableTools, enabledSessions)
  }

  /**
   * Find the session corresponding to an MCP tool
   * @param {string} toolName - Tool name
   * @param {Array} availableTools - Available MCP tools list
   * @param {Array} enabledSessions - Enabled sessions list
   * @returns {string|null} Session ID, null if not found
   */
  findMcpToolSession(toolName, availableTools = [], enabledSessions = []) {
    if (!enabledSessions || enabledSessions.length === 0) {
      this.logger.log('❌ No available MCP sessions')
      return null
    }
    
    // Build tool name to session mapping
    const toolToSessionMap = new Map()
    
    // Iterate through all available tools to build tool name to session mapping
    availableTools.forEach(tool => {
      const toolSessionId = this.getToolSessionId(tool, enabledSessions)
      if (toolSessionId) {
        toolToSessionMap.set(tool.name, toolSessionId)
      }
    })
    
    this.logger.log('🔍 MCP tool session mapping:', {
      totalTools: availableTools.length,
      toolToSessionMap: Object.fromEntries(toolToSessionMap),
      searchingTool: toolName
    })
    
    // Directly find the session for the tool
    const sessionId = toolToSessionMap.get(toolName)
    if (sessionId) {
      this.logger.log('✅ MCP tool session found:', {
        toolName,
        sessionId,
        sessionName: this.getSessionName(sessionId, enabledSessions)
      })
      return sessionId
    }
    
    // If direct mapping not found, try searching in all sessions
    for (const session of enabledSessions) {
      const sessionId = session.id || session
      const sessionTools = this.getSessionTools(sessionId, availableTools, enabledSessions)
      
      if (sessionTools.includes(toolName)) {
        this.logger.log('✅ Tool found in MCP session:', {
          toolName,
          sessionId,
          sessionName: this.getSessionName(sessionId, enabledSessions)
        })
        return sessionId
      }
    }
    
    // If still not found, log detailed information and return null
    this.logger.log('❌ No MCP session found for tool:', {
      toolName,
      totalSessions: enabledSessions.length,
      sessionDetails: enabledSessions.map(s => ({
        id: s.id || s,
        name: s.name || 'Unknown',
        toolCount: s.toolCount || 0
      })),
      availableToolNames: availableTools.map(t => t.name)
    })
    
    return null
  }

  /**
   * Get the session ID corresponding to a tool
   * @param {Object} tool - Tool object
   * @param {Array} enabledSessions - Enabled sessions list
   * @returns {string|null} Session ID
   */
  getToolSessionId(tool, enabledSessions = []) {
    this.logger.log(`🔍 Finding session ID for tool ${tool.name}:`, {
      toolServerName: tool.serverName,
      toolSessionId: tool.sessionId,
      enabledSessionsCount: enabledSessions.length
    })
    
    // Method 1: Tool object may contain serverName field, which can be used to map to session
    if (tool.serverName) {
      // Find session based on serverName
      const session = enabledSessions.find(s => s.name === tool.serverName)
      if (session) {
        const sessionId = session.id || session
        this.logger.log(`✅ Session found for tool ${tool.name} via serverName:`, {
          serverName: tool.serverName,
          sessionId: sessionId,
          sessionName: session.name
        })
        return sessionId
      } else {
        this.logger.log(`❌ Session not found for tool ${tool.name} via serverName:`, {
          toolServerName: tool.serverName,
          availableSessionNames: enabledSessions.map(s => s.name)
        })
      }
    }
    
    // Method 2: Fallback mechanism - if tool directly contains sessionId and that sessionId exists in enabledSessions, use it directly
    if (tool.sessionId) {
      const sessionExists = enabledSessions.find(s => {
        const sessionId = s.id || s
        return sessionId === tool.sessionId
      })
      
      if (sessionExists) {
        this.logger.log(`✅ Session found for tool ${tool.name} via sessionId:`, {
          sessionId: tool.sessionId,
          sessionName: sessionExists.name || 'Unknown'
        })
        return tool.sessionId
      } else {
        this.logger.log(`❌ Tool ${tool.name}'s sessionId not found in enabledSessions:`, {
          toolSessionId: tool.sessionId,
          availableSessionIds: enabledSessions.map(s => s.id || s)
        })
      }
    } else {
      this.logger.log(`⚠️ Tool ${tool.name} has no sessionId field`)
    }
    
    this.logger.log(`❌ No session found for tool ${tool.name}`)
    return null
  }

  /**
   * Get session name
   * @param {string} sessionId - Session ID
   * @param {Array} enabledSessions - Enabled sessions list
   * @returns {string} Session name
   */
  getSessionName(sessionId, enabledSessions = []) {
    const session = enabledSessions.find(s => (s.id || s) === sessionId)
    return session ? (session.name || sessionId) : sessionId
  }

  /**
   * Get tool list for a specified session
   * @param {string} sessionId - Session ID
   * @param {Array} availableTools - Available tools list
   * @param {Array} enabledSessions - Enabled sessions list (for serverName matching)
   * @returns {Array} Tool names list
   */
  getSessionTools(sessionId, availableTools = [], enabledSessions = []) {
    // Directly use tool object properties to determine, avoiding circular calls
    return availableTools
      .filter(tool => {
        // Method 1: Directly check tool's sessionId property
        if (tool.sessionId === sessionId) {
          return true
        }
        
        // Method 2: Match via serverName (avoid circular call to getToolSessionId)
        if (tool.serverName && enabledSessions.length > 0) {
          const session = enabledSessions.find(s => s.name === tool.serverName)
          if (session && (session.id || session) === sessionId) {
            return true
          }
        }
        
        return false
      })
      .map(tool => tool.name)
  }

  /**
   * Validate if tool exists
   * @param {string} toolName - Tool name
   * @param {Array} systemTools - System tools list
   * @param {Array} availableTools - Available MCP tools list
   * @returns {Object} Validation result { exists: boolean, toolType: 'system'|'mcp'|null, tool: Object|null }
   */
  validateTool(toolName, systemTools = [], availableTools = []) {
    // Check system tools
    const systemTool = systemTools.find(tool => tool.function.name === toolName)
    if (systemTool) {
      return {
        exists: true,
        toolType: 'system',
        tool: systemTool
      }
    }

    // Check MCP tools
    const mcpTool = availableTools.find(tool => tool.name === toolName)
    if (mcpTool) {
      return {
        exists: true,
        toolType: 'mcp',
        tool: mcpTool
      }
    }

    return {
      exists: false,
      toolType: null,
      tool: null
    }
  }

  /**
   * Get summary of all available tools
   * @param {Array} systemTools - System tools list
   * @param {Array} availableTools - Available MCP tools list
   * @param {Array} enabledSessions - Enabled sessions list
   * @returns {Object} Tools summary
   */
  getToolsSummary(systemTools = [], availableTools = [], enabledSessions = []) {
    const systemToolNames = systemTools.map(t => t.function.name)
    const mcpToolNames = availableTools.map(t => t.name)
    
    // Calculate session distribution of MCP tools
    const toolSessionMapping = new Map()
    availableTools.forEach(tool => {
      const sessionId = this.getToolSessionId(tool, enabledSessions)
      if (sessionId) {
        if (!toolSessionMapping.has(sessionId)) {
          toolSessionMapping.set(sessionId, [])
        }
        toolSessionMapping.get(sessionId).push(tool.name)
      }
    })

    return {
      systemTools: {
        count: systemToolNames.length,
        tools: systemToolNames
      },
      mcpTools: {
        count: mcpToolNames.length,
        tools: mcpToolNames,
        sessionMapping: Object.fromEntries(toolSessionMapping)
      },
      totalTools: systemToolNames.length + mcpToolNames.length,
      enabledSessions: enabledSessions.length
    }
  }
}

// Create singleton instance
export const toolResolutionService = new ToolResolutionService()

// Default export
export default toolResolutionService