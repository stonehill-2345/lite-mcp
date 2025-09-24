import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN.js'
import enUS from './locales/en-US.js'

// Get user's language setting from localStorage, default to Chinese
const getStoredLocale = () => {
  try {
    const advancedConfig = localStorage.getItem('mcp_advanced_config')
    if (advancedConfig) {
      const config = JSON.parse(advancedConfig)
      return config.locale || 'zh-CN'
    }
  } catch (error) {
    console.warn('Failed to get stored language setting:', error)
  }
  return 'zh-CN'
}

// Create i18n instance
export const i18n = createI18n({
  legacy: false,
  locale: getStoredLocale(),
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS
  },
  globalInjection: true
})

// Method to switch language
export const setLocale = (locale) => {
  i18n.global.locale.value = locale
  
  // Save to localStorage
  try {
    const advancedConfig = localStorage.getItem('mcp_advanced_config')
    let config = {}
    
    if (advancedConfig) {
      config = JSON.parse(advancedConfig)
    }
    
    config.locale = locale
    localStorage.setItem('mcp_advanced_config', JSON.stringify(config))
  } catch (error) {
    console.warn('Failed to save language setting:', error)
  }
}

// Get current language
export const getCurrentLocale = () => {
  return i18n.global.locale.value
}

// Get available language list
export const getAvailableLocales = () => {
  return [
    { value: 'zh-CN', label: '中文（简体）', nativeLabel: '中文' },
    { value: 'en-US', label: 'English (US)', nativeLabel: 'English' }
  ]
}

export default i18n