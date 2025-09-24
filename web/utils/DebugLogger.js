import ConfigManager from '@/services/config/ConfigStorage.js'

/**
 * Debug Logger Utility Class
 * Provides unified debug log management, controlling output based on debugMode in advanced settings
 */
export class DebugLogger {
  static _isDebugEnabled = null
  static _checkInterval = null

  /**
   * Check if debug mode is enabled
   */
  static isDebugEnabled() {
    if (this._isDebugEnabled === null) {
      this.updateDebugStatus()
      // Periodically update debug status (check every 5 seconds)
      this._checkInterval = setInterval(() => {
        this.updateDebugStatus()
      }, 5000)
    }
    return this._isDebugEnabled
  }

  /**
   * Update debug status
   */
  static updateDebugStatus() {
    try {
      const advancedConfig = ConfigManager.loadAdvancedConfig()
      const newStatus = advancedConfig.debugMode || false
      
      if (newStatus !== this._isDebugEnabled) {
        this._isDebugEnabled = newStatus
        // Output提示 when debug status changes (not controlled by debug mode)
        console.log(`🔧 Debug mode ${newStatus ? 'enabled' : 'disabled'}`)
      }
    } catch (error) {
      this._isDebugEnabled = false
    }
  }

  /**
   * Force refresh debug status
   */
  static refreshDebugStatus() {
    this._isDebugEnabled = null
    return this.isDebugEnabled()
  }

  /**
   * Clean up timer
   */
  static cleanup() {
    if (this._checkInterval) {
      clearInterval(this._checkInterval)
      this._checkInterval = null
    }
  }

  /**
   * Format log prefix
   */
  static formatPrefix(level, component = '') {
    const timestamp = new Date().toLocaleTimeString()
    const componentStr = component ? `[${component}]` : ''
    return `[${timestamp}]${componentStr}[${level.toUpperCase()}]`
  }

  /**
   * Debug log - general information
   */
  static log(message, ...args) {
    if (this.isDebugEnabled()) {
      const component = this.getCallerComponent()
      console.log(this.formatPrefix('debug', component), message, ...args)
    }
  }

  /**
   * Info log - important information (not controlled by debug mode)
   */
  static info(message, ...args) {
    const component = this.getCallerComponent()
    console.info(this.formatPrefix('info', component), message, ...args)
  }

  /**
   * Warning log - warning information (not controlled by debug mode)
   */
  static warn(message, ...args) {
    const component = this.getCallerComponent()
    console.warn(this.formatPrefix('warn', component), message, ...args)
  }

  /**
   * Error log - error information (not controlled by debug mode)
   */
  static error(message, ...args) {
    const component = this.getCallerComponent()
    console.error(this.formatPrefix('error', component), message, ...args)
  }

  /**
   * Table log - debug only
   */
  static table(data, columns) {
    if (this.isDebugEnabled()) {
      const component = this.getCallerComponent()
      console.log(this.formatPrefix('table', component))
      console.table(data, columns)
    }
  }

  /**
   * Group log - debug only
   */
  static group(label, collapsed = false) {
    if (this.isDebugEnabled()) {
      const component = this.getCallerComponent()
      const method = collapsed ? 'groupCollapsed' : 'group'
      console[method](this.formatPrefix('group', component), label)
    }
  }

  /**
   * End group
   */
  static groupEnd() {
    if (this.isDebugEnabled()) {
      console.groupEnd()
    }
  }

  /**
   * Timer start - debug only
   */
  static time(label) {
    if (this.isDebugEnabled()) {
      console.time(label)
    }
  }

  /**
   * Timer end - debug only
   */
  static timeEnd(label) {
    if (this.isDebugEnabled()) {
      console.timeEnd(label)
    }
  }

  /**
   * Get caller component name
   */
  static getCallerComponent() {
    try {
      const stack = new Error().stack
      const lines = stack.split('\n')
      
      // Find the first caller that is not DebugLogger
      for (let i = 2; i < lines.length; i++) {
        const line = lines[i]
        if (line && !line.includes('DebugLogger')) {
          // Try to extract filename
          const match = line.match(/\/([^\/]+\.(vue|js))/)
          if (match) {
            return match[1].replace(/\.(vue|js)$/, '')
          }
          break
        }
      }
    } catch (error) {
      // Ignore errors
    }
    return ''
  }

  /**
   * Create component-specific logger
   */
  static createLogger(componentName) {
    return {
      log: (message, ...args) => {
        if (DebugLogger.isDebugEnabled()) {
          console.log(DebugLogger.formatPrefix('debug', componentName), message, ...args)
        }
      },
      debug: (message, ...args) => {
        if (DebugLogger.isDebugEnabled()) {
          console.debug(DebugLogger.formatPrefix('debug', componentName), message, ...args)
        }
      },
      info: (message, ...args) => {
        console.info(DebugLogger.formatPrefix('info', componentName), message, ...args)
      },
      warn: (message, ...args) => {
        console.warn(DebugLogger.formatPrefix('warn', componentName), message, ...args)
      },
      error: (message, ...args) => {
        console.error(DebugLogger.formatPrefix('error', componentName), message, ...args)
      },
      table: (data, columns) => {
        if (DebugLogger.isDebugEnabled()) {
          console.log(DebugLogger.formatPrefix('table', componentName))
          console.table(data, columns)
        }
      },
      group: (label, collapsed = false) => {
        if (DebugLogger.isDebugEnabled()) {
          const method = collapsed ? 'groupCollapsed' : 'group'
          console[method](DebugLogger.formatPrefix('group', componentName), label)
        }
      },
      groupEnd: () => {
        if (DebugLogger.isDebugEnabled()) {
          console.groupEnd()
        }
      },
      time: (label) => {
        if (DebugLogger.isDebugEnabled()) {
          console.time(`${componentName}-${label}`)
        }
      },
      timeEnd: (label) => {
        if (DebugLogger.isDebugEnabled()) {
          console.timeEnd(`${componentName}-${label}`)
        }
      }
    }
  }
}

// Default export
export default DebugLogger

// Separately export createLogger method
export const createLogger = DebugLogger.createLogger.bind(DebugLogger)

// Clean up on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    DebugLogger.cleanup()
  })
}