/**
 * API Configuration Service
 * Manages API endpoints and configuration using environment variables
 */

/**
 * Get environment variable with fallback
 * @param {string} key - Environment variable key
 * @param {string} defaultValue - Default value if env var is not set
 * @returns {string} Environment variable value or default
 */
const getEnvVar = (key, defaultValue) => {
  return import.meta.env[key] || defaultValue
}

/**
 * API Configuration
 */
export const API_CONFIG = {
  // API Server Configuration
  BASE_URL: getEnvVar('VITE_API_BASE_URL', 'http://localhost:9000'),
  TIMEOUT: parseInt(getEnvVar('VITE_API_TIMEOUT', '40000')),
  
  // Proxy Server Configuration
  PROXY_BASE_URL: getEnvVar('VITE_PROXY_BASE_URL', 'http://localhost:1888'),
  
  // Application Configuration
  APP_TITLE: getEnvVar('VITE_APP_TITLE', 'LiteMCP Configuration'),
  APP_VERSION: getEnvVar('VITE_APP_VERSION', '1.0.0'),
  
  // Debug Configuration
  DEBUG_MODE: getEnvVar('VITE_DEBUG_MODE', 'true') === 'true',
  LOG_LEVEL: getEnvVar('VITE_LOG_LEVEL', 'info')
}

/**
 * Get full API URL
 * @param {string} path - API path (should start with /)
 * @returns {string} Full API URL
 */
export const getApiUrl = (path = '') => {
  const baseUrl = API_CONFIG.BASE_URL.replace(/\/$/, '') // Remove trailing slash
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  return `${baseUrl}${cleanPath}`
}

/**
 * Get full proxy URL
 * @param {string} path - Proxy path (should start with /)
 * @returns {string} Full proxy URL
 */
export const getProxyUrl = (path = '') => {
  const baseUrl = API_CONFIG.PROXY_BASE_URL.replace(/\/$/, '') // Remove trailing slash
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  return `${baseUrl}${cleanPath}`
}

/**
 * Environment-specific configurations
 */
export const ENV_CONFIGS = {
  development: {
    API_BASE_URL: 'http://localhost:9000',
    PROXY_BASE_URL: 'http://localhost:1888',
    DEBUG_MODE: true,
    LOG_LEVEL: 'debug'
  },
  
  production: {
    API_BASE_URL: 'https://api.your-domain.com',
    PROXY_BASE_URL: 'https://proxy.your-domain.com',
    DEBUG_MODE: false,
    LOG_LEVEL: 'error'
  },
  
  staging: {
    API_BASE_URL: 'https://staging-api.your-domain.com',
    PROXY_BASE_URL: 'https://staging-proxy.your-domain.com',
    DEBUG_MODE: true,
    LOG_LEVEL: 'info'
  }
}

/**
 * Get current environment
 * @returns {string} Current environment (development, production, staging)
 */
export const getCurrentEnvironment = () => {
  return import.meta.env.MODE || 'development'
}

/**
 * Check if running in development mode
 * @returns {boolean} True if in development mode
 */
export const isDevelopment = () => {
  return getCurrentEnvironment() === 'development'
}

/**
 * Check if running in production mode
 * @returns {boolean} True if in production mode
 */
export const isProduction = () => {
  return getCurrentEnvironment() === 'production'
}

/**
 * Log configuration (only in development)
 */
if (API_CONFIG.DEBUG_MODE) {
  console.log('🔧 API Configuration:', {
    environment: getCurrentEnvironment(),
    baseUrl: API_CONFIG.BASE_URL,
    proxyUrl: API_CONFIG.PROXY_BASE_URL,
    timeout: API_CONFIG.TIMEOUT,
    debugMode: API_CONFIG.DEBUG_MODE
  })
}

export default API_CONFIG
