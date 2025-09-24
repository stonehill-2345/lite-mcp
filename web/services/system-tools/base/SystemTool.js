/**
 * System Tool Base Class
 * All system tools should inherit from this base class
 */
export class SystemTool {
  constructor(config = {}) {
    this.name = config.name || ''
    this.description = config.description || ''
    this.category = config.category || 'general'
    this.enabled = config.enabled !== false // Enabled by default
    this.config = config.config || {}
    this.version = config.version || '1.0.0'
    this.author = config.author || 'system'
    
    // Tool input parameter definition (JSON Schema format)
    this.inputSchema = config.inputSchema || {
      type: 'object',
      properties: {},
      required: []
    }
    
    // Validate required properties
    if (!this.name) {
      throw new Error('System tool must provide a name')
    }
    if (!this.description) {
      throw new Error('System tool must provide a description')
    }
  }

  /**
   * Execute tool
   * @param {Object} parameters - Tool parameters
   * @param {Object} context - Execution context
   * @returns {Promise<Object>} Execution result
   */
  async execute(parameters = {}, context = {}) {
    try {
      // Validate parameters
      const validationResult = this.validateParameters(parameters)
      if (!validationResult.valid) {
        throw new Error(`Parameter validation failed: ${validationResult.error}`)
      }

      // Log tool call
      this.logToolCall(parameters, context)

      // Pre-execution processing
      await this.beforeExecute(parameters, context)

      // Execute specific logic (subclass must implement)
      const result = await this.doExecute(parameters, context)

      // Post-execution processing
      await this.afterExecute(result, parameters, context)

      // Return in unified MCP-compatible format
      const mcpCompatibleResult = this.formatToMcpResult(result, context)
      
      const finalResult = {
        success: true,
        toolName: this.name,
        timestamp: Date.now(),
        duration: Date.now() - context.startTime,
        ...mcpCompatibleResult  // Ensure MCP format fields are not overwritten
      }
      
      return finalResult

    } catch (error) {
      // Handle errors
      const errorResult = await this.handleError(error, parameters, context)
      return {
        success: false,
        error: errorResult.message,
        toolName: this.name,
        timestamp: Date.now(),
        details: errorResult.details || null
      }
    }
  }

  /**
   * Specific execution logic (subclass must implement)
   * @param {Object} parameters - Tool parameters
   * @param {Object} context - Execution context
   * @returns {Promise<any>} Execution result
   */
  async doExecute(parameters, context) {
    throw new Error('Subclass must implement doExecute method')
  }

  /**
   * Validate parameters
   * @param {Object} parameters - Parameters to validate
   * @returns {Object} Validation result
   */
  validateParameters(parameters) {
    try {
      // Simple JSON Schema validation
      const schema = this.inputSchema
      
      // Check required parameters
      if (schema.required && Array.isArray(schema.required)) {
        for (const requiredField of schema.required) {
          if (!(requiredField in parameters)) {
            return {
              valid: false,
              error: `Missing required parameter: ${requiredField}`
            }
          }
        }
      }

      // Check parameter types
      if (schema.properties) {
        for (const [key, value] of Object.entries(parameters)) {
          const propSchema = schema.properties[key]
          if (propSchema) {
            const typeValid = this.validateType(value, propSchema.type)
            if (!typeValid) {
              return {
                valid: false,
                error: `Parameter ${key} type error, expected ${propSchema.type}, actual ${typeof value}`
              }
            }
          }
        }
      }

      return { valid: true }

    } catch (error) {
      return {
        valid: false,
        error: `Parameter validation exception: ${error.message}`
      }
    }
  }

  /**
   * Validate data type
   * @param {any} value - Value to validate
   * @param {string} expectedType - Expected type
   * @returns {boolean} Whether it matches
   */
  validateType(value, expectedType) {
    switch (expectedType) {
      case 'string':
        return typeof value === 'string'
      case 'number':
        return typeof value === 'number' && !isNaN(value)
      case 'integer':
        return Number.isInteger(value)
      case 'boolean':
        return typeof value === 'boolean'
      case 'array':
        return Array.isArray(value)
      case 'object':
        return typeof value === 'object' && value !== null && !Array.isArray(value)
      default:
        return true // Unknown types pass by default
    }
  }

  /**
   * Pre-execution processing (optional)
   * @param {Object} parameters - Tool parameters
   * @param {Object} context - Execution context
   */
  async beforeExecute(parameters, context) {
    // Subclass can override this method
  }

  /**
   * Post-execution processing (optional)
   * @param {any} result - Execution result
   * @param {Object} parameters - Tool parameters
   * @param {Object} context - Execution context
   */
  async afterExecute(result, parameters, context) {
    // Subclass can override this method
  }

  /**
   * Error handling
   * @param {Error} error - Error object
   * @param {Object} parameters - Tool parameters
   * @param {Object} context - Execution context
   * @returns {Object} Error handling result
   */
  async handleError(error, parameters, context) {
    console.error(`System tool ${this.name} execution failed:`, error)
    
    return {
      message: error.message || 'Tool execution failed',
      details: {
        toolName: this.name,
        parameters: parameters,
        stack: error.stack
      }
    }
  }

  /**
   * Log tool call
   * @param {Object} parameters - Tool parameters
   * @param {Object} context - Execution context
   */
  logToolCall(parameters, context) {
  }

  /**
   * Get tool definition (for prompts and model calls)
   * @returns {Object} Tool definition
   */
  getDefinition() {
    return {
      type: 'function',
      function: {
        name: this.name,
        description: this.description,
        parameters: this.inputSchema
      },
      category: this.category,
      enabled: this.enabled,
      version: this.version,
      author: this.author,
      toolType: 'system' // Distinguish between system tools and MCP tools
    }
  }

  /**
   * Get tool configuration
   * @returns {Object} Tool configuration
   */
  getConfig() {
    return {
      name: this.name,
      description: this.description,
      category: this.category,
      enabled: this.enabled,
      config: this.config,
      version: this.version,
      author: this.author,
      inputSchema: this.inputSchema
    }
  }

  /**
   * Update tool configuration
   * @param {Object} newConfig - New configuration
   */
  updateConfig(newConfig) {
    if (newConfig.enabled !== undefined) {
      this.enabled = newConfig.enabled
    }
    if (newConfig.config) {
      this.config = { ...this.config, ...newConfig.config }
    }
  }

  /**
   * Check if tool is available
   * @returns {boolean} Whether it's available
   */
  isAvailable() {
    return this.enabled
  }

  /**
   * Format result to MCP-compatible format
   * @param {any} result - Tool execution result
   * @param {Object} context - Execution context
   * @returns {Object} MCP-compatible result format
   */
  formatToMcpResult(result, context) {
    // If subclass already returns MCP format, use it directly
    if (result && result.content && Array.isArray(result.content)) {
      return result
    }
    
    // If it's standard system tool format {success, message, data}
    if (result && typeof result === 'object' && result.message) {
      return {
        content: [
          {
            type: "text",
            text: result.message
          }
        ],
        metadata: {
          toolType: "system",
          duration: result.duration || (Date.now() - context.startTime),
          data: result.data || null
        }
      }
    }
    
    // If it's a string result
    if (typeof result === 'string') {
      return {
        content: [
          {
            type: "text", 
            text: result
          }
        ],
        metadata: {
          toolType: "system",
          duration: Date.now() - context.startTime
        }
      }
    }
    
    // If it's another object, convert to JSON string
    if (typeof result === 'object') {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2)
          }
        ],
        metadata: {
          toolType: "system", 
          duration: Date.now() - context.startTime,
          data: result
        }
      }
    }
    
    // Default case
    return {
      content: [
        {
          type: "text",
          text: String(result || "Tool execution completed")
        }
      ],
      metadata: {
        toolType: "system",
        duration: Date.now() - context.startTime
      }
    }
  }

  /**
   * Test tool connection (optional)
   * @returns {Promise<boolean>} Whether connection is normal
   */
  async testConnection() {
    return true // Available by default
  }
}