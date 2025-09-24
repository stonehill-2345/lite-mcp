import { SystemTool } from '@/services/system-tools/base/SystemTool.js'
import { McpReconnectTool } from '@/services/system-tools/tools/McpReconnectTool.js'
import { DateTimeTool } from '@/services/system-tools/tools/DateTimeTool.js'
import { CodeExecutorTool } from '@/services/system-tools/tools/CodeExecutorTool.js'
import DebugLogger from '@/utils/DebugLogger.js'
import { setCache, getCacheByKey } from '@/utils/storage.js'


/**
 * System Tools Manager
 * Responsible for registering, managing, and calling all system tools
 */
export class SystemToolsManager {
  constructor() {
    this.tools = new Map()
    this.categories = new Map()
    this.config = {
      enabledTools: [], // Enabled tools list
      globalConfig: {}, // Global configuration
      autoLoad: true,   // Whether to automatically load tools
      cacheKey: 'system_tools_config'
    }
    this.initialized = false
    
    // State change listeners
    this.listeners = new Set()
    
    // Asynchronous initialization
    this.init().catch(error => {
      console.error('SystemToolsManager initialization failed:', error)
    })
  }

  /**
   * Initialize system tools manager
   */
  async init() {
    try {
      this.log('Initializing system tools manager')
      
      // Load saved configuration
      this.loadConfig()
      
      // Register default tools
      this.registerDefaultTools()
      
      // If auto-load is set, enable saved tool configuration
      if (this.config.autoLoad) {
        this.applyEnabledTools()
      }
      
      this.initialized = true
      this.log('System tools manager initialization completed')
    } catch (error) {
      this.log('System tools manager initialization failed:', error)
      // Even if initialization fails, ensure the basic structure exists
      this.tools = this.tools || new Map()
      this.categories = this.categories || new Map()
      this.initialized = true // Mark as initialized to avoid repeated attempts
    }
  }

  /**
   * Register default system tools
   */
  registerDefaultTools() {
    this.log('Registering default system tools')
    
    // Register MCP reconnect tool
    this.registerTool(new McpReconnectTool())
    
    // Register date time tool
    this.registerTool(new DateTimeTool()) // Temporarily disabled for debugging
    
    // Register code execution tool
    this.registerTool(new CodeExecutorTool())
    
    // More default tools can be registered here in the future
    // this.registerTool(new CalculatorTool())
    // this.registerTool(new WeatherTool())
    // this.registerTool(new TranslationTool())
    
    this.log(`Default tools registration completed, total ${this.tools.size} tools`)
  }

  /**
   * Register a single tool
   * @param {SystemTool} tool - System tool instance
   */
  registerTool(tool) {
    if (!(tool instanceof SystemTool)) {
      throw new Error('Tool must be an instance of SystemTool')
    }

    const toolName = tool.name
    if (this.tools.has(toolName)) {
      this.log(`Warning: Tool ${toolName} already exists and will be overwritten`)
    }

    // Register tool
    this.tools.set(toolName, tool)

    // Group by category
    const category = tool.category || 'general'
    if (!this.categories.has(category)) {
      this.categories.set(category, [])
    }
    this.categories.get(category).push(toolName)

    this.log(`Registered tool: ${toolName} (category: ${category})`)
  }

  /**
   * Get all tools
   * @param {boolean} enabledOnly - Whether to return only enabled tools
   * @returns {Array} Tool list
   */
  getAllTools(enabledOnly = false) {
    // If not yet initialized, return empty array
    if (!this.initialized || !this.tools) {
      return []
    }
    
    const tools = Array.from(this.tools.values())
    
    if (enabledOnly) {
      return tools.filter(tool => tool.isAvailable())
    }
    
    return tools
  }

  /**
   * Get tool definitions (for model calls)
   * @param {boolean} enabledOnly - Whether to return only enabled tools
   * @returns {Array} Tool definition list
   */
  getToolDefinitions(enabledOnly = true) {
    // If not yet initialized, return empty array
    if (!this.initialized || !this.tools) {
      this.log('[SystemToolsManager] ⚠️ Not initialized or tools are empty')
      return []
    }
    
    const allTools = this.getAllTools(false) // Get all tools
    const enabledTools = this.getAllTools(true) // Get enabled tools
    
    this.log('[SystemToolsManager] 🔍 Getting tool definitions:', {
      enabledOnly,
      initialized: this.initialized,
      totalToolsCount: allTools.length,
      enabledToolsCount: enabledTools.length,
      allToolsStatus: allTools.map(t => ({ name: t.name, enabled: t.enabled, available: t.isAvailable() })),
      enabledTools: enabledTools.map(t => ({ name: t.name, enabled: t.enabled }))
    })
    
    const tools = enabledOnly ? enabledTools : allTools
    return tools.map(tool => tool.getDefinition())
  }

  /**
   * Get specified tool
   * @param {string} toolName - Tool name
   * @returns {SystemTool|null} Tool instance
   */
  getTool(toolName) {
    return this.tools.get(toolName) || null
  }

  /**
   * Call tool
   * @param {string} toolName - Tool name
   * @param {Object} parameters - Tool parameters
   * @param {Object} context - Execution context
   * @returns {Promise<Object>} Execution result
   */
  async callTool(toolName, parameters = {}, context = {}) {
    const tool = this.getTool(toolName)
    
    if (!tool) {
      throw new Error(`System tool ${toolName} does not exist`)
    }

    if (!tool.isAvailable()) {
      throw new Error(`System tool ${toolName} is not enabled`)
    }

    // Add execution context
    const execContext = {
      ...context,
      startTime: Date.now(),
      manager: this,
      toolType: 'system'
    }

    this.log(`Calling system tool: ${toolName}`, parameters)

    try {
      const result = await tool.execute(parameters, execContext)
      
      this.log(`Tool call completed: ${toolName}`, {
        success: result.success,
        duration: result.duration || 0
      })

      return result

    } catch (error) {
      this.log(`Tool call failed: ${toolName}`, error.message)
      throw error
    }
  }

  /**
   * Enable tool
   * @param {string} toolName - Tool name
   */
  enableTool(toolName) {
    const tool = this.getTool(toolName)
    if (tool) {
      tool.updateConfig({ enabled: true })
      
      if (!this.config.enabledTools.includes(toolName)) {
        this.config.enabledTools.push(toolName)
      }
      
      this.saveConfig()
      this.log(`Enabled tool: ${toolName}`)
      
      // Notify state change
      this.notifyStateChange('tool_enabled', { toolName })
    }
  }

  /**
   * Disable tool
   * @param {string} toolName - Tool name
   */
  disableTool(toolName) {
    const tool = this.getTool(toolName)
    if (tool) {
      tool.updateConfig({ enabled: false })
      
      const index = this.config.enabledTools.indexOf(toolName)
      if (index > -1) {
        this.config.enabledTools.splice(index, 1)
      }
      
      this.saveConfig()
      this.log(`Disabled tool: ${toolName}`)
      
      // Notify state change
      this.notifyStateChange('tool_disabled', { toolName })
    }
  }

  /**
   * Batch set tool states
   * @param {Object} toolStates - Tool state mapping {toolName: enabled}
   */
  setToolStates(toolStates) {
    const changes = []
    
    for (const [toolName, enabled] of Object.entries(toolStates)) {
      if (enabled) {
        this.enableTool(toolName)
        changes.push({ toolName, enabled: true })
      } else {
        this.disableTool(toolName)
        changes.push({ toolName, enabled: false })
      }
    }
    
    // Notify batch state change
    this.notifyStateChange('tools_batch_updated', { changes })
  }

  /**
   * Get tools grouped by category
   * @returns {Object} Tools grouped by category
   */
  getToolsByCategory() {
    const categorizedTools = {}
    
    for (const [category, toolNames] of this.categories.entries()) {
      categorizedTools[category] = toolNames.map(name => {
        const tool = this.getTool(name)
        return tool ? tool.getConfig() : null
      }).filter(Boolean)
    }
    
    return categorizedTools
  }

  /**
   * Update tool configuration
   * @param {string} toolName - Tool name
   * @param {Object} config - New configuration
   */
  updateToolConfig(toolName, config) {
    const tool = this.getTool(toolName)
    if (tool) {
      tool.updateConfig(config)
      this.saveConfig()
      this.log(`Updated tool configuration: ${toolName}`)
    }
  }

  /**
   * Test tool connection
   * @param {string} toolName - Tool name
   * @returns {Promise<boolean>} Test result
   */
  async testTool(toolName) {
    const tool = this.getTool(toolName)
    if (!tool) {
      return false
    }

    try {
      return await tool.testConnection()
    } catch (error) {
      this.log(`Tool test failed: ${toolName}`, error.message)
      return false
    }
  }

  /**
   * Execute tool (using default parameters)
   * @param {string} toolName - Tool name
   * @param {Object} parameters - Tool parameters, if not provided, use default parameters
   * @returns {Promise<Object>} Execution result
   */
  async executeTool(toolName, parameters = null) {
    const tool = this.getTool(toolName)
    if (!tool) {
      throw new Error(`Tool ${toolName} does not exist`)
    }

    if (!tool.enabled) {
      throw new Error(`Tool ${toolName} is not enabled`)
    }

    try {
      // If no parameters are provided, use the tool's default parameters
      let executeParams = parameters
      if (!executeParams) {
        executeParams = this.getToolDefaultParameters(tool)
      }

      this.log(`Executing tool: ${toolName}, parameters:`, executeParams)
      const result = await tool.execute(executeParams)
      this.log(`Tool execution completed: ${toolName}, result:`, result)
      
      return result
    } catch (error) {
      this.log(`Tool execution failed: ${toolName}`, error.message)
      throw error
    }
  }

  /**
   * Get tool's default parameters
   * @param {SystemTool} tool - Tool instance
   * @returns {Object} Default parameters
   */
  getToolDefaultParameters(tool) {
    const schema = tool.inputSchema
    const defaultParams = {}

    if (schema && schema.properties) {
      for (const [key, propSchema] of Object.entries(schema.properties)) {
        if (propSchema.default !== undefined) {
          defaultParams[key] = propSchema.default
        }
      }
    }

    // Provide reasonable default parameters for specific tools
    if (tool.name === 'mcp_reconnect') {
      return {
        reconnectType: 'auto',
        disconnectFirst: true,
        showProgress: true,
        ...defaultParams
      }
    }

    return defaultParams
  }

  /**
   * Test all enabled tools
   * @returns {Promise<Object>} Test results summary
   */
  async testAllTools() {
    const results = {}
    const enabledTools = this.getAllTools(true)
    
    for (const tool of enabledTools) {
      results[tool.name] = await this.testTool(tool.name)
    }
    
    return results
  }

  /**
   * Load configuration
   */
  loadConfig() {
    try {
      const savedConfig = getCacheByKey(this.config.cacheKey)
      this.log('[SystemToolsManager] 🔄 Loading configuration:', {
        cacheKey: this.config.cacheKey,
        savedConfig: savedConfig,
        currentConfig: this.config
      })
      
      if (savedConfig && typeof savedConfig === 'object') {
        this.config = { ...this.config, ...savedConfig }
        this.log('[SystemToolsManager] ✅ System tools configuration loaded successfully:', this.config)
      } else {
        this.log('[SystemToolsManager] ⚠️ No saved configuration found, using default configuration')
        // If no saved configuration, enable all tools by default
        this.config.enabledTools = ['mcp_reconnect', 'get_datetime'] // Enable system tools by default
      }
    } catch (error) {
      console.error('[SystemToolsManager] ❌ Failed to load system tools configuration:', error.message)
    }
  }

  /**
   * Save configuration
   */
  saveConfig() {
    try {
      setCache(this.config.cacheKey, {
        enabledTools: this.config.enabledTools,
        globalConfig: this.config.globalConfig
      })
      this.log('System tools configuration saved successfully')
    } catch (error) {
      this.log('Failed to save system tools configuration:', error.message)
    }
  }

  /**
   * Apply enabled tool configuration
   */
  applyEnabledTools() {
    this.log('[SystemToolsManager] 🔧 Applying enabled tool configuration:', {
      enabledToolsInConfig: this.config.enabledTools,
      allToolNames: Array.from(this.tools.keys())
    })
    
    // First disable all tools
    for (const tool of this.tools.values()) {
      tool.updateConfig({ enabled: false })
    }
    
    // Then enable tools in configuration
    let appliedCount = 0
    for (const toolName of this.config.enabledTools) {
      const tool = this.getTool(toolName)
      if (tool) {
        tool.updateConfig({ enabled: true })
        appliedCount++
        this.log(`[SystemToolsManager] ✅ Enabled tool: ${toolName}`)
      } else {
        this.log(`[SystemToolsManager] ❌ Tool does not exist: ${toolName}`)
      }
    }
    
    this.log(`[SystemToolsManager] 🎯 Tool configuration applied: ${appliedCount}/${this.config.enabledTools.length} tools enabled`)
  }

  /**
   * Get tool statistics
   * @returns {Object} Statistics information
   */
  getStats() {
    const totalTools = this.tools.size
    const enabledTools = this.getAllTools(true).length
    const categories = this.categories.size
    
    return {
      totalTools,
      enabledTools,
      disabledTools: totalTools - enabledTools,
      categories,
      toolsByCategory: Object.fromEntries(
        Array.from(this.categories.entries()).map(([cat, tools]) => [cat, tools.length])
      )
    }
  }

  /**
   * Reset configuration
   */
  resetConfig() {
    this.config.enabledTools = []
    this.config.globalConfig = {}
    
    // Disable all tools
    for (const tool of this.tools.values()) {
      tool.updateConfig({ enabled: false })
    }
    
    this.saveConfig()
    this.log('System tools configuration has been reset')
  }

  /**
   * Export configuration
   * @returns {Object} Configuration data
   */
  exportConfig() {
    return {
      enabledTools: [...this.config.enabledTools],
      globalConfig: { ...this.config.globalConfig },
      toolConfigs: Object.fromEntries(
        Array.from(this.tools.entries()).map(([name, tool]) => [name, tool.getConfig()])
      )
    }
  }

  /**
   * Import configuration
   * @param {Object} configData - Configuration data
   */
  importConfig(configData) {
    if (configData.enabledTools) {
      this.config.enabledTools = configData.enabledTools
    }
    
    if (configData.globalConfig) {
      this.config.globalConfig = configData.globalConfig
    }
    
    if (configData.toolConfigs) {
      for (const [toolName, toolConfig] of Object.entries(configData.toolConfigs)) {
        this.updateToolConfig(toolName, toolConfig)
      }
    }
    
    this.applyEnabledTools()
    this.saveConfig()
    this.log('System tools configuration import completed')
  }

  /**
   * Add state change listener
   */
  addStateChangeListener(listener) {
    if (typeof listener === 'function') {
      this.listeners.add(listener)
      this.log('Added state change listener')
    }
  }

  /**
   * Remove state change listener
   */
  removeStateChangeListener(listener) {
    this.listeners.delete(listener)
    this.log('Removed state change listener')
  }

  /**
   * Notify state change
   */
  notifyStateChange(changeType, details) {
    try {
      const changeEvent = {
        type: changeType,
        timestamp: Date.now(),
        details: details || {},
        manager: this
      }

      this.log('Notifying state change:', changeEvent)

      // Asynchronously notify all listeners
      this.listeners.forEach(listener => {
        try {
          if (typeof listener === 'function') {
            listener(changeEvent)
          }
        } catch (error) {
          console.warn('State change listener execution failed:', error)
        }
      })
    } catch (error) {
      console.error('Failed to notify state change:', error)
    }
  }

  /**
   * Log output
   */
  log(...args) {
    if (DebugLogger.isDebugEnabled()) {
      console.log(DebugLogger.formatPrefix('debug', 'SystemToolsManager'), ...args)
    }
  }

  /**
   * Destroy manager
   */
  destroy() {
    this.tools.clear()
    this.categories.clear()
    this.log('System tools manager has been destroyed')
  }
}

// Create global instance
export const systemToolsManager = new SystemToolsManager()

// Default export
export default systemToolsManager