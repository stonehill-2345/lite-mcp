import { REGEX_PATTERNS } from '@/constants'

/**
 * Validate MCP server name
 * @param {string} name - Server name
 * @returns {boolean} Whether valid
 */
export function validateMcpServerName(name) {
  if (!name || typeof name !== 'string') {
    return false
  }
  return REGEX_PATTERNS.MCP_SERVER_NAME.test(name)
}

/**
 * Validate URL format
 * @param {string} url - URL string
 * @returns {boolean} Whether valid
 */
export function validateUrl(url) {
  if (!url || typeof url !== 'string') {
    return false
  }
  return REGEX_PATTERNS.URL.test(url)
}

/**
 * Validate JSON format
 * @param {string} jsonString - JSON string
 * @returns {boolean} Whether valid
 */
export function validateJson(jsonString) {
  if (!jsonString || typeof jsonString !== 'string') {
    return false
  }
  try {
    JSON.parse(jsonString)
    return true
  } catch (e) {
    return false
  }
}

/**
 * Validate Email format
 * @param {string} email - Email address
 * @returns {boolean} Whether valid
 */
export function validateEmail(email) {
  if (!email || typeof email !== 'string') {
    return false
  }
  return REGEX_PATTERNS.EMAIL.test(email)
}

/**
 * Validate port number
 * @param {number|string} port - Port number
 * @returns {boolean} Whether valid
 */
export function validatePort(port) {
  const portNum = typeof port === 'string' ? parseInt(port, 10) : port
  return Number.isInteger(portNum) && portNum > 0 && portNum <= 65535
}

/**
 * Validate MCP configuration
 * @param {Object} config - MCP configuration object
 * @returns {Object} Validation result { valid: boolean, errors: string[] }
 */
export function validateMcpConfig(config) {
  const errors = []
  
  if (!config || typeof config !== 'object') {
    errors.push('Configuration must be an object')
    return { valid: false, errors }
  }
  
  // Validate required fields
  if (!config.name) {
    errors.push('Server name is required')
  } else if (!validateMcpServerName(config.name)) {
    errors.push('Server name format is invalid')
  }
  
  if (!config.command) {
    errors.push('Startup command is required')
  }
  
  // Validate optional fields
  if (config.env && typeof config.env !== 'object') {
    errors.push('Environment variables must be in object format')
  }
  
  if (config.args && !Array.isArray(config.args)) {
    errors.push('Arguments must be in array format')
  }
  
  return {
    valid: errors.length === 0,
    errors
  }
}

/**
 * Validate chat message
 * @param {Object} message - Message object
 * @returns {Object} Validation result { valid: boolean, errors: string[] }
 */
export function validateChatMessage(message) {
  const errors = []
  
  if (!message || typeof message !== 'object') {
    errors.push('Message must be an object')
    return { valid: false, errors }
  }
  
  // Validate role
  const validRoles = ['user', 'assistant', 'system', 'tool']
  if (!message.role || !validRoles.includes(message.role)) {
    errors.push(`Role must be one of: ${validRoles.join(', ')}`)
  }
  
  // Validate content
  if (!message.content && message.role !== 'tool') {
    errors.push('Message content is required')
  }
  
  // Validate tool calls
  if (message.tool_calls && !Array.isArray(message.tool_calls)) {
    errors.push('Tool calls must be in array format')
  }
  
  return {
    valid: errors.length === 0,
    errors
  }
}

/**
 * Validate model configuration
 * @param {Object} config - Model configuration object
 * @returns {Object} Validation result { valid: boolean, errors: string[] }
 */
export function validateModelConfig(config) {
  const errors = []
  
  if (!config || typeof config !== 'object') {
    errors.push('Model configuration must be an object')
    return { valid: false, errors }
  }
  
  // Validate required fields
  if (!config.provider) {
    errors.push('Model provider is required')
  }
  
  if (!config.model) {
    errors.push('Model name is required')
  }
  
  // Validate numeric fields
  if (config.temperature !== undefined) {
    const temp = parseFloat(config.temperature)
    if (isNaN(temp) || temp < 0 || temp > 2) {
      errors.push('Temperature value must be between 0-2')
    }
  }
  
  if (config.maxTokens !== undefined) {
    const maxTokens = parseInt(config.maxTokens, 10)
    if (isNaN(maxTokens) || maxTokens < 1) {
      errors.push('Maximum tokens must be a positive integer')
    }
  }
  
  return {
    valid: errors.length === 0,
    errors
  }
}

/**
 * Validate batch data
 * @param {Array} items - Data array to validate
 * @param {Function} validator - Validation function
 * @returns {Object} Validation result { valid: boolean, errors: Array, validItems: Array }
 */
export function validateBatch(items, validator) {
  if (!Array.isArray(items)) {
    return {
      valid: false,
      errors: ['Input must be an array'],
      validItems: []
    }
  }
  
  const results = items.map((item, index) => {
    const result = validator(item)
    return {
      index,
      item,
      ...result
    }
  })
  
  const errors = results
    .filter(r => !r.valid)
    .map(r => `Item ${r.index}: ${r.errors.join(', ')}`)
  
  const validItems = results
    .filter(r => r.valid)
    .map(r => r.item)
  
  return {
    valid: errors.length === 0,
    errors,
    validItems
  }
}

export default {
  validateMcpServerName,
  validateUrl,
  validateJson,
  validateEmail,
  validatePort,
  validateMcpConfig,
  validateChatMessage,
  validateModelConfig,
  validateBatch
}