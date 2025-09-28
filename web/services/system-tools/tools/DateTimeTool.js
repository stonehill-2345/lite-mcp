import { SystemTool } from '@/services/system-tools/base/SystemTool.js'
import DebugLogger from "@/utils/DebugLogger"

const logger = DebugLogger.createLogger('DateTimeTool')

/**
 * DateTime Tool
 * Get current time, format time, timezone conversion and other functions
 */
export class DateTimeTool extends SystemTool {
  constructor(config = {}) {
    super({
      name: 'get_datetime',
      description: 'Get current date and time, support multiple formats and timezone conversion, can be used for time-related queries and calculations',
      category: 'utility',
      version: '1.0.0',
      author: 'system',
      inputSchema: {
        type: 'object',
        properties: {
          format: {
            type: 'string',
            description: 'Time format',
            enum: ['iso', 'locale', 'timestamp', 'custom', 'relative'],
            default: 'locale'
          },
          timezone: {
            type: 'string',
            description: 'Timezone (e.g.: Asia/Shanghai, America/New_York, UTC)',
            default: 'local'
          },
          customFormat: {
            type: 'string',
            description: 'Custom format template (used when format is custom, e.g.: YYYY-MM-DD HH:mm:ss)'
          },
          includeWeekday: {
            type: 'boolean',
            description: 'Whether to include weekday information',
            default: true
          },
          language: {
            type: 'string',
            description: 'Language code (e.g.: zh-CN, en-US)',
            default: 'zh-CN'
          }
        },
        required: []
      },
      config: {
        timeout: 5000,
        maxRetries: 1
      },
      ...config
    })
  }

  /**
   * Execute time retrieval
   */
  async doExecute(parameters, context) {
    logger.log(`[DateTimeTool] Starting to get time information`)
    logger.log(`[DateTimeTool] Received parameters:`, parameters)

    try {
      const {
        format = 'locale',
        timezone = 'local',
        customFormat,
        includeWeekday = true,
        language = 'zh-CN'
      } = parameters

      const now = new Date()
      const result = {
        timestamp: now.getTime(),
        utc: now.toISOString()
      }

      // Return time based on different formats
      switch (format) {
        case 'iso':
          result.formatted = now.toISOString()
          result.description = 'ISO 8601 format'
          break

        case 'timestamp':
          result.formatted = now.getTime().toString()
          result.description = 'Unix timestamp (milliseconds)'
          break

        case 'locale':
          const localeOptions = {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            timeZoneName: 'short'
          }
          
          if (includeWeekday) {
            localeOptions.weekday = 'long'
          }

          if (timezone !== 'local') {
            localeOptions.timeZone = timezone
          }

          result.formatted = now.toLocaleString(language, localeOptions)
          result.description = `Localized format (${language})`
          break

        case 'custom':
          if (customFormat) {
            result.formatted = this.formatCustomDateTime(now, customFormat, timezone)
            result.description = `Custom format: ${customFormat}`
          } else {
            result.formatted = now.toLocaleString(language)
            result.description = 'Default localized format (no custom format provided)'
          }
          break

        case 'relative':
          result.formatted = this.getRelativeTime(now)
          result.description = 'Relative time description'
          break

        default:
          result.formatted = now.toLocaleString(language)
          result.description = 'Default localized format'
      }

      // Add extra information
      result.timezone = timezone === 'local' ? Intl.DateTimeFormat().resolvedOptions().timeZone : timezone
      result.weekday = now.toLocaleDateString(language, { weekday: 'long' })
      result.year = now.getFullYear()
      result.month = now.getMonth() + 1
      result.day = now.getDate()
      result.hour = now.getHours()
      result.minute = now.getMinutes()
      result.second = now.getSeconds()

      // Calculate some useful information
      result.dayOfYear = this.getDayOfYear(now)
      result.weekOfYear = this.getWeekOfYear(now)
      result.isWeekend = now.getDay() === 0 || now.getDay() === 6
      result.season = this.getSeason(now.getMonth() + 1)

      logger.log(`[DateTimeTool] ✅ Time retrieval successful:`, result)

      // Build user-friendly time description
      let timeDescription = `Current time: ${result.formatted}`
      
      // Add extra useful information
      const extraInfo = []
      if (result.weekday) {
        extraInfo.push(`Today is ${result.weekday}`)
      }
      if (result.season) {
        extraInfo.push(`It's ${result.season}`)
      }
      if (result.isWeekend) {
        extraInfo.push('Today is a weekend')
      }
      if (result.timezone) {
        extraInfo.push(`Timezone: ${result.timezone}`)
      }
      
      if (extraInfo.length > 0) {
        timeDescription += `\n${extraInfo.join(', ')}`
      }
      
      // Add more detailed information
      timeDescription += `\nThis is day ${result.dayOfYear} of ${result.year}, week ${result.weekOfYear}`

      return {
        success: true,
        message: timeDescription,
        data: result,
        duration: Date.now() - context.startTime
      }

    } catch (error) {
      logger.error(`[DateTimeTool] ❌ Failed to get time:`, error)
      return {
        success: false,
        message: `Failed to get time: ${error.message}`,
        error: error.message,
        duration: Date.now() - context.startTime
      }
    }
  }

  /**
   * Custom format time
   */
  formatCustomDateTime(date, format, timezone = 'local') {
    let targetDate = date
    
    // Convert if timezone is specified
    if (timezone !== 'local') {
      const utc = date.getTime() + (date.getTimezoneOffset() * 60000)
      // Simple timezone handling, actual projects may need more complex timezone libraries
      targetDate = new Date(utc)
    }

    const year = targetDate.getFullYear()
    const month = String(targetDate.getMonth() + 1).padStart(2, '0')
    const day = String(targetDate.getDate()).padStart(2, '0')
    const hour = String(targetDate.getHours()).padStart(2, '0')
    const minute = String(targetDate.getMinutes()).padStart(2, '0')
    const second = String(targetDate.getSeconds()).padStart(2, '0')

    return format
      .replace(/YYYY/g, year)
      .replace(/MM/g, month)
      .replace(/DD/g, day)
      .replace(/HH/g, hour)
      .replace(/mm/g, minute)
      .replace(/ss/g, second)
  }

  /**
   * Get relative time description
   */
  getRelativeTime(date) {
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffSeconds = Math.floor(diffMs / 1000)
    const diffMinutes = Math.floor(diffSeconds / 60)
    const diffHours = Math.floor(diffMinutes / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (Math.abs(diffSeconds) < 60) {
      return 'just now'
    } else if (Math.abs(diffMinutes) < 60) {
      return `${Math.abs(diffMinutes)} minutes ${diffMinutes > 0 ? 'ago' : 'from now'}`
    } else if (Math.abs(diffHours) < 24) {
      return `${Math.abs(diffHours)} hours ${diffHours > 0 ? 'ago' : 'from now'}`
    } else {
      return `${Math.abs(diffDays)} days ${diffDays > 0 ? 'ago' : 'from now'}`
    }
  }

  /**
   * Get day of year
   */
  getDayOfYear(date) {
    const start = new Date(date.getFullYear(), 0, 0)
    const diff = date - start
    return Math.floor(diff / (1000 * 60 * 60 * 24))
  }

  /**
   * Get week of year
   */
  getWeekOfYear(date) {
    const start = new Date(date.getFullYear(), 0, 1)
    const days = Math.floor((date - start) / (24 * 60 * 60 * 1000))
    return Math.ceil((days + start.getDay() + 1) / 7)
  }

  /**
   * Get season
   */
  getSeason(month) {
    if (month >= 3 && month <= 5) return 'Spring'
    if (month >= 6 && month <= 8) return 'Summer'
    if (month >= 9 && month <= 11) return 'Autumn'
    return 'Winter'
  }

  /**
   * Test tool connectivity
   */
  async testConnection() {
    try {
      const now = new Date()
      return {
        status: 'success',
        message: `Time tool is working properly, current time: ${now.toLocaleString('zh-CN')}`,
        details: {
          timestamp: now.getTime(),
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
        }
      }
    } catch (error) {
      return {
        status: 'error',
        message: `Time tool test failed: ${error.message}`,
        details: { error: error.message }
      }
    }
  }

  /**
   * Get tool status information
   */
  getStatus() {
    return {
      name: this.name,
      enabled: this.enabled,
      category: this.category,
      version: this.version,
      description: this.description,
      supportedFormats: ['iso', 'locale', 'timestamp', 'custom', 'relative'],
      supportedTimezones: ['local', 'UTC', 'Asia/Shanghai', 'America/New_York', 'Europe/London'],
      lastUsed: this.lastUsed || null
    }
  }
}