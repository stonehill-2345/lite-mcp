<template>
  <div class="chat-settings">
    <!-- Settings button -->
    <el-button 
      :icon="Setting" 
      size="small"
      @click="showSettingsDialog = true"
      class="settings-button"
    >
      {{ $t('chat.settings.title') }}
    </el-button>

    <!-- Settings dialog -->
    <el-dialog
      v-model="showSettingsDialog"
      :title="$t('chat.settings.title')"
      width="900px"
      :close-on-click-modal="false"
      :append-to-body="true"
      :modal="true"
      class="settings-dialog"
    >
      <el-tabs v-model="activeTab" class="settings-tabs">
        <!-- Model configuration -->
        <el-tab-pane :label="$t('chat.settings.modelConfig')" name="model">
          <div class="tab-content">
            <ModelConfig
              :model-config="localModelConfig"
              @config-change="handleModelConfigChange"
            />
          </div>
        </el-tab-pane>

        <!-- Prompt configuration -->
        <el-tab-pane :label="$t('chat.settings.promptConfig')" name="prompts">
          <div class="tab-content">
            <PromptConfig
              :custom-prompts="localCustomPrompts"
              @prompts-change="handlePromptsChange"
            />
          </div>
        </el-tab-pane>

        <!-- ReAct settings -->
        <el-tab-pane :label="$t('chat.settings.reactSettings')" name="react">
          <div class="tab-content">
            <ReActConfig
              :react-enabled="localReactEnabled"
              :react-config="localReactConfig"
              @react-toggle="handleReactToggle"
              @react-config-change="handleReactConfigChange"
            />
          </div>
        </el-tab-pane>

        <!-- System tools -->
        <el-tab-pane :label="$t('chat.settings.systemTools')" name="system-tools">
          <div class="tab-content">
            <SystemToolsConfig />
          </div>
        </el-tab-pane>

        <!-- Advanced settings -->
        <el-tab-pane :label="$t('chat.settings.advancedSettings')" name="advanced">
          <div class="tab-content">
            <AdvancedConfig
              :advanced-config="localAdvancedConfig"
              @config-change="handleAdvancedConfigChange"
            />
          </div>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="resetToDefaults">{{ $t('common.reset') }} {{ $t('common.default') }}</el-button>
          <el-button type="primary" @click="saveSettings">{{ $t('chat.settings.saveSettings') }}</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { Setting } from '@element-plus/icons-vue'

import ModelConfig from '@/components/config/ModelConfig.vue'
import PromptConfig from '@/components/config/PromptConfig.vue'
import ReActConfig from '@/components/config/ReActConfig.vue'
import SystemToolsConfig from '@/components/config/SystemToolsConfig.vue'
import AdvancedConfig from '@/components/config/AdvancedConfig.vue'

import { DEFAULT_MODEL_CONFIG } from '@/services/config/modelConfigs.js'
import ConfigManager from '@/services/config/ConfigStorage.js'
import DebugLogger from '@/utils/DebugLogger.js'

// Internationalization
const { t } = useI18n()

// Create component-specific logger
const logger = DebugLogger.createLogger('ChatSettings')

// Props
const props = defineProps({
  modelConfig: {
    type: Object,
    default: () => ({ ...DEFAULT_MODEL_CONFIG })
  },
  customPrompts: {
    type: Object,
    default: () => ({})
  },
  reactEnabled: {
    type: Boolean,
    default: true
  }
})

// Emits
const emit = defineEmits([
  'model-config-change',
  'prompts-change',
  'react-toggle',
  'config-change',
  'config-export',
  'config-import'
])

// Reactive data
const showSettingsDialog = ref(false)
const activeTab = ref('model')

// Local configuration copies - initialize with default values, load from local storage later
const localModelConfig = ref({ ...props.modelConfig })
const localCustomPrompts = ref({ ...props.customPrompts })
const localReactEnabled = ref(props.reactEnabled)
const localReactConfig = ref({})
const localAdvancedConfig = ref({})

// Flag to prevent recursive updates
let isUpdatingFromProps = false

// Watch property changes - only update when really needed
watch(() => props.modelConfig, (newConfig) => {
  if (!isUpdatingFromProps && newConfig) {
    isUpdatingFromProps = true
    localModelConfig.value = { ...newConfig }
    setTimeout(() => {
      isUpdatingFromProps = false
    }, 50)
  }
}, { deep: true, immediate: true })

watch(() => props.customPrompts, (newPrompts) => {
  if (!isUpdatingFromProps && newPrompts) {
    isUpdatingFromProps = true
    localCustomPrompts.value = { ...newPrompts }
    setTimeout(() => {
      isUpdatingFromProps = false
    }, 50)
  }
}, { deep: true, immediate: true })

watch(() => props.reactEnabled, (enabled) => {
  if (!isUpdatingFromProps && enabled !== localReactEnabled.value) {
    isUpdatingFromProps = true
    localReactEnabled.value = enabled
    setTimeout(() => {
      isUpdatingFromProps = false
    }, 50)
  }
}, { immediate: true })

// Methods
const handleModelConfigChange = (config) => {
  logger.log('Model configuration changed:', config)
  localModelConfig.value = { ...localModelConfig.value, ...config }
  logger.log('Updated model configuration:', localModelConfig.value)
  
  // Auto-save (if auto-save is enabled)
  if (localAdvancedConfig.value.autoSave !== false) {
    logger.log('Auto-saving model configuration:', localModelConfig.value)
    ConfigManager.saveModelConfig(localModelConfig.value)
  }
}

const handlePromptsChange = (prompts) => {
  localCustomPrompts.value = { ...localCustomPrompts.value, ...prompts }
  // Auto-save (if auto-save is enabled)
  if (localAdvancedConfig.value.autoSave !== false) {
    ConfigManager.savePromptsConfig(localCustomPrompts.value)
  }
}

const handleReactToggle = (enabled) => {
  localReactEnabled.value = enabled
  // Auto-save (if auto-save is enabled)
  if (localAdvancedConfig.value.autoSave !== false) {
    ConfigManager.saveReActConfig({
      enabled: localReactEnabled.value,
      ...localReactConfig.value
    })
  }
}

const handleReactConfigChange = (config) => {
  localReactConfig.value = { ...localReactConfig.value, ...config }
  // Auto-save (if auto-save is enabled)
  if (localAdvancedConfig.value.autoSave !== false) {
    ConfigManager.saveReActConfig({
      enabled: localReactEnabled.value,
      ...localReactConfig.value
    })
  }
}

const handleAdvancedConfigChange = (config) => {
  localAdvancedConfig.value = { ...localAdvancedConfig.value, ...config }
  // Auto-save (if auto-save is enabled)
  if (localAdvancedConfig.value.autoSave !== false) {
    ConfigManager.saveAdvancedConfig(localAdvancedConfig.value)
  }
  
  // Emit configuration change event
  emit('config-change', {
    type: 'advanced',
    config: config
  })
}

const saveSettings = () => {
  try {
    // Validate configuration
    if (!validateConfigs()) {
      return
    }

    // Prevent recursive updates
    isUpdatingFromProps = true
    
    // Save to local storage
    ConfigManager.saveModelConfig(localModelConfig.value)
    ConfigManager.savePromptsConfig(localCustomPrompts.value)
    ConfigManager.saveReActConfig({
      enabled: localReactEnabled.value,
      ...localReactConfig.value
    })
    ConfigManager.saveAdvancedConfig(localAdvancedConfig.value)
    
    // Emit configuration change events
    emit('model-config-change', localModelConfig.value)
    emit('prompts-change', localCustomPrompts.value)
    emit('react-toggle', localReactEnabled.value)

    showSettingsDialog.value = false
    ElMessage.success('Settings saved and stored locally')
    
    // Reset flag
    setTimeout(() => {
      isUpdatingFromProps = false
    }, 100)
    
  } catch (error) {
    isUpdatingFromProps = false
    ElMessage.error(t('chat.settings.settingsSaveFailed') + ': ' + error.message)
  }
}

const resetToDefaults = async () => {
  try {
    await ElMessageBox.confirm(
      'Are you sure you want to reset to default settings? This will clear all custom configurations.',
      'Reset Settings',
      {
        confirmButtonText: 'Confirm',
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    // Reset local storage to default values
    const success = ConfigManager.resetToDefaults()
    if (success) {
      // Reload configuration
      loadSavedConfigs()
      ElMessage.success('Reset to default settings')
    } else {
      ElMessage.error('Failed to reset configuration')
    }
  } catch (error) {
    // User cancelled
  }
}

const validateConfigs = () => {
  // Validate model configuration
  if (!localModelConfig.value.provider) {
    ElMessage.error('Please select a model provider')
    activeTab.value = 'model'
    return false
  }

  // All providers need model ID, including Azure OpenAI
  if (!localModelConfig.value.modelId) {
    ElMessage.error('Please select or enter a model')
    activeTab.value = 'model'
    return false
  }

  if (localModelConfig.value.temperature < 0 || localModelConfig.value.temperature > 2) {
    ElMessage.error('Temperature value must be between 0-2')
    activeTab.value = 'model'
    return false
  }

  if (localModelConfig.value.maxTokens < 1 || localModelConfig.value.maxTokens > 200000) {
    ElMessage.error('Max tokens must be between 1-200000')
    activeTab.value = 'model'
    return false
  }

  // Validate API key - update supported provider list
  const needsApiKey = ['openai', 'anthropic', 'deepseek', 'dashscope', 'azure'].includes(localModelConfig.value.provider)
  if (needsApiKey && !localModelConfig.value.apiKey) {
    ElMessage.error(`${localModelConfig.value.provider} requires API key`)
    activeTab.value = 'model'
    return false
  }

  // Special validation for Azure OpenAI
  if (localModelConfig.value.provider === 'azure') {
    if (!localModelConfig.value.azureEndpoint && !localModelConfig.value.baseUrl) {
      ElMessage.error('Please configure Azure endpoint or base URL')
      activeTab.value = 'model'
      return false
    }
    if (localModelConfig.value.azureEndpoint && !localModelConfig.value.deploymentName) {
      ElMessage.error('Please configure deployment name')
      activeTab.value = 'model'
      return false
    }
    if (!localModelConfig.value.apiVersion) {
      ElMessage.error('Please configure API version')
      activeTab.value = 'model'
      return false
    }
  }

  // Validate providers that need Base URL (now excluding azure)
  const needsBaseUrl = ['custom'].includes(localModelConfig.value.provider)
  if (needsBaseUrl && !localModelConfig.value.baseUrl) {
    ElMessage.error('Please enter base URL')
    activeTab.value = 'model'
    return false
  }

  return true
}

const exportConfig = () => {
  try {
    // Use ConfigStorage to export all configurations
    const allConfigs = ConfigManager.exportAll()
    
    const blob = new Blob([JSON.stringify(allConfigs, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `mcp-chat-config-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)

    ElMessage.success('Configuration exported')
  } catch (error) {
    ElMessage.error('Failed to export configuration: ' + error.message)
  }
}

const importConfig = (file) => {
  if (!file) return
  
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const configData = JSON.parse(e.target.result)
      
      // Use ConfigStorage to import configuration
      ConfigManager.importAll(configData)
      
      // Reload configuration to interface
      loadSavedConfigs()

      ElMessage.success('Configuration imported and applied')
    } catch (error) {
      ElMessage.error('Failed to import configuration: ' + error.message)
    }
  }
  reader.readAsText(file)
}

// Load saved configurations
const loadSavedConfigs = () => {
  try {
    // Load saved configurations - ConfigManager.loadModelConfig() already handles default value merging
    const savedModelConfig = ConfigManager.loadModelConfig()
    const savedPromptsConfig = ConfigManager.loadPromptsConfig()
    const savedReActConfig = ConfigManager.loadReActConfig()
    const savedAdvancedConfig = ConfigManager.loadAdvancedConfig()
    
    // Directly use ConfigManager returned configurations, no longer manually merge default values
    // ConfigManager.loadModelConfig() already correctly handles merging of default values and saved values, including null values
    localModelConfig.value = { ...savedModelConfig }
    localCustomPrompts.value = { ...savedPromptsConfig }
    localReactEnabled.value = savedReActConfig.enabled !== undefined ? savedReActConfig.enabled : true
    localReactConfig.value = { ...savedReActConfig }
    localAdvancedConfig.value = { ...savedAdvancedConfig }
  } catch (error) {
    logger.error('Failed to load configuration:', error)
    ElMessage.warning('Failed to load saved configuration, using default configuration')
  }
}

// Auto-save configuration (when configuration changes)
const autoSaveConfigs = () => {
  try {
    ConfigManager.saveModelConfig(localModelConfig.value)
    ConfigManager.savePromptsConfig(localCustomPrompts.value)
    ConfigManager.saveReActConfig({
      enabled: localReactEnabled.value,
      ...localReactConfig.value
    })
    ConfigManager.saveAdvancedConfig(localAdvancedConfig.value)
    logger.log('Configuration auto-saved')
  } catch (error) {
    logger.error('Failed to auto-save configuration:', error)
  }
}

// Lifecycle - read saved configuration when component loads
onMounted(() => {
  loadSavedConfigs()
})

// Expose methods
defineExpose({
  exportConfig,
  importConfig,
  loadSavedConfigs
})
</script>

<style scoped lang="scss">
.chat-settings {
  .el-button {
    transition: all 0.3s ease;
    border-radius: 6px;
    background-color: var(--el-color-primary-light-9);
    border: 1px solid var(--el-color-primary-light-5);
    color: var(--el-color-primary);
    
    &:hover {
      color: var(--el-color-white);
      background-color: var(--el-color-primary);
      border-color: var(--el-color-primary);
      transform: translateY(-1px);
      box-shadow: 0 2px 8px rgba(var(--el-color-primary-rgb), 0.2);
    }
  }

  .settings-dialog {
    :deep(.el-dialog) {
      max-width: 1000px;
      
      .el-dialog__body {
        padding: 0;
      }
    }
    
    .settings-tabs {
      :deep(.el-tabs__header) {
        margin: 0;
        background: var(--el-fill-color-lighter);
        
        .el-tabs__nav-wrap {
          padding: 0 20px;
        }
      }
      
      :deep(.el-tabs__content) {
        padding: 0;
      }
      
      .tab-content {
        padding: 20px;
        min-height: 400px;
        max-height: 60vh;
        overflow-y: auto;
      }
    }
    
    .dialog-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .export-import {
        display: flex;
        gap: 8px;
      }
    }
  }
}

// Scrollbar styles
.tab-content::-webkit-scrollbar {
  width: 6px;
}

.tab-content::-webkit-scrollbar-track {
  background: var(--el-fill-color-lighter);
  border-radius: 3px;
}

.tab-content::-webkit-scrollbar-thumb {
  background: var(--el-fill-color-dark);
  border-radius: 3px;
  
  &:hover {
    background: var(--el-fill-color-darker);
  }
}
</style> 