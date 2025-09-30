/**
 * MCP API Interface Wrapper
 * Provides communication interface with LiteMCP backend API
 */

import axios from 'axios'
import { API_CONFIG, getApiUrl } from '@/services/config/ApiConfig'

// Create axios instance using environment configuration
const apiClient = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Can add authentication token here
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API request failed:', error)

    // Improved error message extraction, prioritize detailed error information from server
    let errorMessage = 'Request failed'

    if (error.response?.data) {
      // Prioritize detail field (FastAPI standard error format)
      if (error.response.data.detail) {
        errorMessage = error.response.data.detail
      }
      // Then use message field
      else if (error.response.data.message) {
        errorMessage = error.response.data.message
      }
      // If it is a string, use it directly
      else if (typeof error.response.data === 'string') {
        errorMessage = error.response.data
      }
    }
    // Network error or timeout
    else if (error.message) {
      if (error.message.includes('timeout')) {
        errorMessage = 'Request timeout, external MCP service startup may take longer, please try again later'
      } else {
        errorMessage = error.message
      }
    }

    return Promise.reject(new Error(errorMessage))
  }
)

/**
 * Get MCP configuration
 * @param {object} params - Query parameters
 * @returns {Promise} API response
 */
export const getMcpConfig = (params = {}) => {
  return apiClient.get('/api/v1/config', { params })
}

/**
 * Get server status
 * @returns {Promise} API response
 */
export const getServerStatus = () => {
  return apiClient.get('/api/v1/status')
}

/**
 * Health check
 * @returns {Promise} API response
 */
export const healthCheck = () => {
  return apiClient.get('/api/v1/health')
}

/**
 * Get debug information
 * @returns {Promise} API response
 */
export const getDebugInfo = () => {
  return apiClient.get('/api/v1/debug')
}

/**
 * Get statistics overview
 * @returns {Promise} API response
 */
export const getStatistics = () => {
  return apiClient.get('/api/v1/statistics/')
}

/**
 * Get full statistics information
 * @returns {Promise} API response
 */
export const getFullStatistics = () => {
  return apiClient.get('/api/v1/statistics/full')
}

/**
 * Get server statistics
 * @returns {Promise} API response
 */
export const getServerStatistics = () => {
  return apiClient.get('/api/v1/statistics/servers')
}

/**
 * Get specific server statistics
 * @param {string} serverName - Server name
 * @returns {Promise} API response
 */
export const getServerDetail = (serverName) => {
  return apiClient.get(`/api/v1/statistics/servers/${encodeURIComponent(serverName)}`)
}

/**
 * Get tool statistics
 * @returns {Promise} API response
 */
export const getToolStatistics = () => {
  return apiClient.get('/api/v1/statistics/tools')
}

/**
 * Get specific tool statistics
 * @param {string} toolName - Tool name
 * @returns {Promise} API response
 */
export const getToolDetail = (toolName) => {
  return apiClient.get(`/api/v1/statistics/tools/${encodeURIComponent(toolName)}`)
}

/**
 * Get author statistics
 * @returns {Promise} API response
 */
export const getAuthorStatistics = () => {
  return apiClient.get('/api/v1/statistics/authors')
}

/**
 * Get project statistics
 * @returns {Promise} API response
 */
export const getProjectStatistics = () => {
  return apiClient.get('/api/v1/statistics/projects')
}

/**
 * Get department statistics
 * @returns {Promise} API response
 */
export const getDepartmentStatistics = () => {
  return apiClient.get('/api/v1/statistics/departments')
}

/**
 * Generate statistics report
 * @returns {Promise} API response
 */
export const generateStatisticsReport = () => {
  return apiClient.get('/api/v1/statistics/report')
}

/**
 * Rebuild statistics data
 * @returns {Promise} API response
 */
export const rebuildStatistics = () => {
  return apiClient.post('/api/v1/statistics/rebuild')
}

/**
 * Refresh statistics data
 * @returns {Promise} API response
 */
export const refreshStatistics = () => {
  return apiClient.post('/api/v1/statistics/refresh')
}

/**
 * Query tool details by tool name
 * @param {string} apiUrl - API base URL
 * @param {string} toolName - Tool name
 * @returns {Promise} Tool details
 */
export const queryToolByName = async (apiUrl, toolName) => {
  try {
    // Construct query URL
    const url = `${apiUrl}?tool_name=${encodeURIComponent(toolName)}`

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()

    return {
      success: true,
      data: data,
      message: 'Query successful'
    }
  } catch (error) {
    console.error('Failed to query tool details:', error)
    return {
      success: false,
      data: null,
      message: error.message || 'Query failed'
    }
  }
}

/**
 * Cleanup dead processes
 * @returns {Promise} API response
 */
export const cleanupDeadServers = () => {
  return apiClient.post('/registry/cleanup')
}

/**
 * Get proxy mode configuration
 * @param {object} params - Query parameters
 * @returns {Promise} API response
 */
export const getProxyConfig = (params = {}) => {
  return apiClient.get('/api/v1/config/proxy', { params })
}

/**
 * Get Cursor configuration
 * @returns {Promise} API response
 */
export const getCursorConfig = () => {
  return apiClient.get('/api/v1/config/cursor')
}

/**
 * Get Claude Desktop configuration
 * @returns {Promise} API response
 */
export const getClaudeConfig = () => {
  return apiClient.get('/api/v1/config/claude')
}

/**
 * Get configuration explanation
 * @returns {Promise} API response
 */
export const getConfigExplanation = () => {
  return apiClient.get('/api/v1/config/explain')
}

/**
 * Get MCP API base URL
 * @returns {string} API base URL
 */
export const getMcpApiUrl = () => {
  return getApiUrl('/api/v1/config')
}

/**
 * Get MCP configuration with custom URL
 * @param {string} customUrl - Custom API URL
 * @param {object} params - Query parameters
 * @returns {Promise} API response
 */
export const getMcpConfigWithUrl = async (customUrl, params = {}) => {
  try {
    // If it's a relative path, use internal API
    if (customUrl.startsWith('/')) {
      return getMcpConfig(params)
    }

    // Use external URL
    const url = new URL(customUrl)
    Object.keys(params).forEach(key => {
      url.searchParams.append(key, params[key])
    })

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return await response.json()
  } catch (error) {
    console.error('Failed to get MCP configuration:', error)
    throw error
  }
}

/**
 * Get MCP statistics information
 * @param {string} customUrl - Custom API URL (optional)
 * @returns {Promise} API response
 */
export const getMcpStatistics = async (customUrl = null) => {
  try {
    if (customUrl && !customUrl.startsWith('/')) {
      // Use external URL - extract base URL from config URL, then concatenate correct statistics API path
      let baseUrl = customUrl
      if (customUrl.endsWith('/api/v1/config')) {
        baseUrl = customUrl.replace('/api/v1/config', '')
      } else if (customUrl.endsWith('/config')) {
        baseUrl = customUrl.replace('/config', '')
      }
      const url = `${baseUrl}/api/v1/statistics/`
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } else {
      // Use internal API
      return getStatistics()
    }
  } catch (error) {
    console.error('Failed to get statistics information:', error)
    throw error
  }
}

// Default export all API methods
export default {
  // Basic configuration API
  getMcpConfig,
  getServerStatus,
  healthCheck,
  getDebugInfo,

  // Statistics API
  getStatistics,
  getFullStatistics,
  getServerStatistics,
  getServerDetail,
  getToolStatistics,
  getToolDetail,
  getAuthorStatistics,
  getProjectStatistics,
  getDepartmentStatistics,
  generateStatisticsReport,
  rebuildStatistics,
  refreshStatistics,

  // Tool query
  queryToolByName,

  // Management API
  cleanupDeadServers,

  // Configuration API
  getProxyConfig,
  getCursorConfig,
  getClaudeConfig,
  getConfigExplanation,

  // Helper methods
  getMcpApiUrl,
  getMcpConfigWithUrl,
  getMcpStatistics
}