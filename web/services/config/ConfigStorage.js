import { getCacheByKey, setCache } from '@/utils/storage.js'
import { DEFAULT_MODEL_CONFIG } from '@/services/config/modelConfigs.js'
// Remove direct import of PromptTemplates to avoid circular dependencies

// Configuration storage key names
export const CONFIG_KEYS = {
  CHAT_CONFIG: 'mcp_chat_config',
  MODEL_CONFIG: 'mcp_model_config', 
  PROMPTS_CONFIG: 'mcp_prompts_config',
  REACT_CONFIG: 'mcp_react_config',
  ADVANCED_CONFIG: 'mcp_advanced_config',
  MCP_CONFIG: 'mcp_server_config',
  USER_PREFERENCES: 'mcp_user_preferences'
}

// Default configurations
export const DEFAULT_CONFIGS = {
  modelConfig: {
    ...DEFAULT_MODEL_CONFIG
  },
  
  promptsConfig: {
    // Use default prompt strings to avoid circular dependencies
    systemPrompt: '',
    reactPrompt: '',
    toolCallPrompt: '',
    errorHandlingPrompt: ''
  },
  
  reactConfig: {
    enabled: true,
    maxIterations: 5,
    timeout: 30000,
    reasoningTemperature: 0.3,
    actionTemperature: 0.5,
    chainOfThoughtLength: 'medium',
    toolSelectionStrategy: 'best_match',
    earlyStopConditions: ['goal_completed', 'confidence_achieved'],
    enableMemory: true,
    memoryCapacity: 100,
    enableParallelProcessing: false,
    parallelismDegree: 2,
    reasoningMode: 'sequential',
    confidenceThreshold: 0.8,
    errorTolerance: 3,
    enableAdaptiveAdjustment: false
  },
  
  advancedConfig: {
    autoSave: true,
    autoSaveInterval: 30,
    debugMode: false,
    requireToolConfirmation: false,
    toolConfirmationTimeout: 60,
    allowBatchToolConfirmation: true
  },
  
  userPreferences: {
    theme: 'auto',
    language: 'zh-CN',
    fontSize: 'medium',
    enableAnimations: true,
    enableSounds: false
  }
}

/**
 * Configuration Storage Management Class
 */
export class ConfigStorage {
  
  /**
   * Save configuration
   */
  static save(key, config) {
    try {
      const configToSave = {
        ...config,
        lastUpdated: new Date().toISOString(),
        version: '1.0.0'
      }
      
      setCache(key, configToSave)
      return true
    } catch (error) {
      console.error(`Failed to save configuration: ${key}`, error)
      return false
    }
  }
  
  /**
   * Load configuration
   */
  static load(key, defaultConfig = {}) {
    try {
      const saved = getCacheByKey(key, null)
      if (saved && typeof saved === 'object') {
        // Remove metadata, return only actual configuration
        const { lastUpdated, version, ...actualConfig } = saved
        return { ...defaultConfig, ...actualConfig }
      }
      return defaultConfig
    } catch (error) {
      console.error(`Failed to load configuration: ${key}`, error)
      return defaultConfig
    }
  }
  
  /**
   * Delete configuration
   */
  static remove(key) {
    try {
      localStorage.removeItem(key)
      sessionStorage.removeItem(key)
      return true
    } catch (error) {
      console.error(`Failed to delete configuration: ${key}`, error)
      return false
    }
  }
  
  /**
   * Check if configuration exists
   */
  static exists(key) {
    try {
      const saved = getCacheByKey(key)
      return saved !== null && saved !== undefined
    } catch (error) {
      return false
    }
  }
  
  /**
   * Get configuration information (including metadata)
   */
  static getInfo(key) {
    try {
      const saved = getCacheByKey(key)
      if (saved && typeof saved === 'object') {
        return {
          exists: true,
          lastUpdated: saved.lastUpdated,
          version: saved.version,
          size: JSON.stringify(saved).length
        }
      }
      return { exists: false }
    } catch (error) {
      return { exists: false, error: error.message }
    }
  }
  
  /**
   * Save configurations in batch
   */
  static saveAll(configs) {
    const results = {}
    Object.entries(configs).forEach(([key, config]) => {
      results[key] = this.save(key, config)
    })
    return results
  }
  
  /**
   * Load configurations in batch
   */
  static loadAll(keys, defaults = {}) {
    const configs = {}
    keys.forEach(key => {
      configs[key] = this.load(key, defaults[key] || {})
    })
    return configs
  }
  
  /**
   * Export all configurations
   */
  static exportAll() {
    try {
      const allConfigs = {}
      Object.values(CONFIG_KEYS).forEach(key => {
        const saved = getCacheByKey(key)
        if (saved) {
          allConfigs[key] = saved
        }
      })
      
      return {
        configs: allConfigs,
        exportTime: new Date().toISOString(),
        version: '1.0.0'
      }
    } catch (error) {
      throw new Error(`Failed to export configurations: ${error.message}`)
    }
  }
  
  /**
   * Import all configurations
   */
  static importAll(data) {
    try {
      if (!data.configs || typeof data.configs !== 'object') {
        throw new Error('Invalid configuration data format')
      }
      
      const results = {}
      Object.entries(data.configs).forEach(([key, config]) => {
        if (Object.values(CONFIG_KEYS).includes(key)) {
          results[key] = this.save(key, config)
        }
      })
      
      return results
    } catch (error) {
      throw new Error(`Failed to import configurations: ${error.message}`)
    }
  }
  
  /**
   * Clear all configurations
   */
  static clearAll() {
    try {
      Object.values(CONFIG_KEYS).forEach(key => {
        this.remove(key)
      })
      return true
    } catch (error) {
      console.error('Failed to clear configurations:', error)
      return false
    }
  }
  
  /**
   * Reset to default configurations
   */
  static resetToDefaults() {
    try {
      this.clearAll()
      
      // Save default configurations
      this.save(CONFIG_KEYS.MODEL_CONFIG, DEFAULT_CONFIGS.modelConfig)
      this.save(CONFIG_KEYS.PROMPTS_CONFIG, DEFAULT_CONFIGS.promptsConfig)
      this.save(CONFIG_KEYS.REACT_CONFIG, DEFAULT_CONFIGS.reactConfig)
      this.save(CONFIG_KEYS.ADVANCED_CONFIG, DEFAULT_CONFIGS.advancedConfig)
      this.save(CONFIG_KEYS.USER_PREFERENCES, DEFAULT_CONFIGS.userPreferences)
      
      console.log('Reset to default configurations')
      return true
    } catch (error) {
      console.error('Failed to reset configurations:', error)
      return false
    }
  }
}

/**
 * Configuration Manager - Provides convenient configuration operation methods
 */
export class ConfigManager {
  
  /**
   * Save model configuration
   */
  static saveModelConfig(config) {
    return ConfigStorage.save(CONFIG_KEYS.MODEL_CONFIG, config)
  }
  
  /**
   * Load model configuration
   */
  static loadModelConfig() {
    return ConfigStorage.load(CONFIG_KEYS.MODEL_CONFIG, DEFAULT_CONFIGS.modelConfig)
  }
  
  /**
   * Save prompt configuration
   */
  static savePromptsConfig(config) {
    return ConfigStorage.save(CONFIG_KEYS.PROMPTS_CONFIG, config)
  }
  
  /**
   * Load prompt configuration
   */
  static loadPromptsConfig() {
    return ConfigStorage.load(CONFIG_KEYS.PROMPTS_CONFIG, DEFAULT_CONFIGS.promptsConfig)
  }
  
  /**
   * Save ReAct configuration
   */
  static saveReActConfig(config) {
    return ConfigStorage.save(CONFIG_KEYS.REACT_CONFIG, config)
  }
  
  /**
   * Load ReAct configuration
   */
  static loadReActConfig() {
    return ConfigStorage.load(CONFIG_KEYS.REACT_CONFIG, DEFAULT_CONFIGS.reactConfig)
  }
  
  /**
   * Save advanced configuration
   */
  static saveAdvancedConfig(config) {
    return ConfigStorage.save(CONFIG_KEYS.ADVANCED_CONFIG, config)
  }
  
  /**
   * Load advanced configuration
   */
  static loadAdvancedConfig() {
    return ConfigStorage.load(CONFIG_KEYS.ADVANCED_CONFIG, DEFAULT_CONFIGS.advancedConfig)
  }
  
  /**
   * Save MCP configuration
   */
  static saveMcpConfig(config) {
    return ConfigStorage.save(CONFIG_KEYS.MCP_CONFIG, config)
  }
  
  /**
   * Load MCP configuration
   */
  static loadMcpConfig() {
    return ConfigStorage.load(CONFIG_KEYS.MCP_CONFIG, {})
  }
  
  /**
   * Save user preferences
   */
  static saveUserPreferences(config) {
    return ConfigStorage.save(CONFIG_KEYS.USER_PREFERENCES, config)
  }
  
  /**
   * Load user preferences
   */
  static loadUserPreferences() {
    return ConfigStorage.load(CONFIG_KEYS.USER_PREFERENCES, DEFAULT_CONFIGS.userPreferences)
  }
  
  /**
   * Load all configurations
   */
  static loadAllConfigs() {
    return {
      modelConfig: this.loadModelConfig(),
      promptsConfig: this.loadPromptsConfig(),
      reactConfig: this.loadReActConfig(),
      advancedConfig: this.loadAdvancedConfig(),
      mcpConfig: this.loadMcpConfig(),
      userPreferences: this.loadUserPreferences()
    }
  }
  
  /**
   * Save all configurations
   */
  static saveAllConfigs(configs) {
    const results = {}
    
    if (configs.modelConfig) {
      results.modelConfig = this.saveModelConfig(configs.modelConfig)
    }
    if (configs.promptsConfig) {
      results.promptsConfig = this.savePromptsConfig(configs.promptsConfig)
    }
    if (configs.reactConfig) {
      results.reactConfig = this.saveReActConfig(configs.reactConfig)
    }
    if (configs.advancedConfig) {
      results.advancedConfig = this.saveAdvancedConfig(configs.advancedConfig)
    }
    if (configs.mcpConfig) {
      results.mcpConfig = this.saveMcpConfig(configs.mcpConfig)
    }
    if (configs.userPreferences) {
      results.userPreferences = this.saveUserPreferences(configs.userPreferences)
    }
    
    return results
  }
  
  /**
   * Export all configurations
   */
  static exportAll() {
    return ConfigStorage.exportAll()
  }
  
  /**
   * Import all configurations
   */
  static importAll(data) {
    return ConfigStorage.importAll(data)
  }
  
  /**
   * Reset to default configurations
   */
  static resetToDefaults() {
    return ConfigStorage.resetToDefaults()
  }
}

// Default export configuration manager
export default ConfigManager