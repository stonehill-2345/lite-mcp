/**
 * Format timestamp
 * @param {Date|number|string} timestamp - Timestamp
 * @param {string} format - Format string, default 'YYYY-MM-DD HH:mm:ss'
 * @returns {string} Formatted time string
 */
export function formatTimestamp(timestamp, format = 'YYYY-MM-DD HH:mm:ss') {
  const date = new Date(timestamp)
  
  if (isNaN(date.getTime())) {
    return 'Invalid Date'
  }
  
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  
  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds)
}

/**
 * Format file size
 * @param {number} bytes - Number of bytes
 * @param {number} decimals - Decimal places, default 2
 * @returns {string} Formatted size string
 */
export function formatFileSize(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
  
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

/**
 * Format duration
 * @param {number} milliseconds - Milliseconds
 * @returns {string} Formatted duration string
 */
export function formatDuration(milliseconds) {
  const seconds = Math.floor(milliseconds / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 0) {
    return `${days}d ${hours % 24}h ${minutes % 60}m`
  } else if (hours > 0) {
    return `${hours}h ${minutes % 60}m ${seconds % 60}s`
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`
  } else {
    return `${seconds}s`
  }
}

/**
 * Format JSON string
 * @param {any} data - Data to format
 * @param {number} indent - Indent spaces, default 2
 * @returns {string} Formatted JSON string
 */
export function formatJson(data, indent = 2) {
  try {
    return JSON.stringify(data, null, indent)
  } catch (error) {
    return String(data)
  }
}

/**
 * Format error message
 * @param {Error|string} error - Error object or string
 * @returns {string} Formatted error message
 */
export function formatError(error) {
  if (error instanceof Error) {
    return `${error.name}: ${error.message}`
  }
  
  if (typeof error === 'string') {
    return error
  }
  
  return String(error)
}

/**
 * Format API response
 * @param {Object} response - API response object
 * @returns {Object} Formatted response object
 */
export function formatApiResponse(response) {
  return {
    success: response.success || false,
    data: response.data || null,
    message: response.message || '',
    timestamp: formatTimestamp(new Date()),
    ...response
  }
}

/**
 * Format chat message
 * @param {Object} message - Chat message object
 * @returns {Object} Formatted message object
 */
export function formatChatMessage(message) {
  return {
    id: message.id || generateId(),
    role: message.role || 'user',
    content: message.content || '',
    timestamp: message.timestamp || Date.now(),
    formattedTime: formatTimestamp(message.timestamp || Date.now(), 'HH:mm:ss'),
    ...message
  }
}

/**
 * Format tool call result
 * @param {Object} result - Tool call result
 * @returns {Object} Formatted result object
 */
export function formatToolResult(result) {
  return {
    success: result.success || false,
    data: result.data || null,
    error: result.error ? formatError(result.error) : null,
    duration: result.duration || 0,
    formattedDuration: formatDuration(result.duration || 0),
    timestamp: formatTimestamp(new Date()),
    ...result
  }
}

/**
 * Truncate text
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @param {string} ellipsis - Ellipsis, default '...'
 * @returns {string} Truncated text
 */
export function truncateText(text, maxLength, ellipsis = '...') {
  if (!text || typeof text !== 'string') {
    return ''
  }
  
  if (text.length <= maxLength) {
    return text
  }
  
  return text.slice(0, maxLength - ellipsis.length) + ellipsis
}

/**
 * Format percentage
 * @param {number} value - Value
 * @param {number} total - Total
 * @param {number} decimals - Decimal places, default 1
 * @returns {string} Formatted percentage string
 */
export function formatPercentage(value, total, decimals = 1) {
  if (total === 0) return '0%'
  
  const percentage = (value / total) * 100
  return `${percentage.toFixed(decimals)}%`
}

/**
 * Format number
 * @param {number} num - Number
 * @param {Object} options - Formatting options
 * @returns {string} Formatted number string
 */
export function formatNumber(num, options = {}) {
  const {
    decimals = 0,
    thousands = ',',
    decimal = '.',
    prefix = '',
    suffix = ''
  } = options
  
  if (isNaN(num)) return 'NaN'
  
  const fixed = Math.abs(num).toFixed(decimals)
  const parts = fixed.split('.')
  
  // Add thousands separator
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, thousands)
  
  // Combine result
  const result = parts.join(decimal)
  const sign = num < 0 ? '-' : ''
  
  return sign + prefix + result + suffix
}

/**
 * Generate unique ID
 * @param {string} prefix - Prefix, default 'id'
 * @returns {string} Unique ID
 */
export function generateId(prefix = 'id') {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Deep clone object
 * @param {any} obj - Object to clone
 * @returns {any} Cloned object
 */
export function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') {
    return obj
  }
  
  if (obj instanceof Date) {
    return new Date(obj.getTime())
  }
  
  if (obj instanceof Array) {
    return obj.map(item => deepClone(item))
  }
  
  if (typeof obj === 'object') {
    const cloned = {}
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        cloned[key] = deepClone(obj[key])
      }
    }
    return cloned
  }
  
  return obj
}

export default {
  formatTimestamp,
  formatFileSize,
  formatDuration,
  formatJson,
  formatError,
  formatApiResponse,
  formatChatMessage,
  formatToolResult,
  truncateText,
  formatPercentage,
  formatNumber,
  generateId,
  deepClone
}