<template>
  <div class="advanced-config">
    <el-form 
      ref="formRef"
      :model="formData"
      label-width="140px"
      class="config-form"
    >
      <!-- Language Settings -->
      <el-card class="setting-card" shadow="never">
        <template #header>
          <span class="card-title">{{ $t('config.advanced.languageSettings') }}</span>
        </template>

        <el-form-item :label="$t('config.advanced.language')">
          <el-select
            v-model="formData.locale"
            @change="handleLanguageChange"
            style="width: 200px"
          >
            <el-option
              v-for="locale in availableLocales"
              :key="locale.value"
              :label="locale.label"
              :value="locale.value"
            >
              <span>{{ locale.nativeLabel }}</span>
            </el-option>
          </el-select>
          <div class="form-help">
            {{ $t('config.advanced.languageDescription') }}
          </div>
        </el-form-item>
      </el-card>

      <!-- Function Settings -->
      <el-card class="setting-card" shadow="never">
        <template #header>
          <span class="card-title">{{ $t('config.advanced.functionSettings') }}</span>
        </template>

        <el-form-item :label="$t('config.advanced.autoSave')">
          <el-switch
            v-model="formData.autoSave"
            :active-text="$t('common.enable')"
            :inactive-text="$t('common.disable')"
            @change="handleFormChange"
          />
          <div class="form-help">
            {{ $t('config.advanced.autoSaveDescription') }}
          </div>
        </el-form-item>

        <el-form-item v-if="formData.autoSave" :label="$t('config.advanced.autoSaveInterval')">
          <el-input-number
            v-model="formData.autoSaveInterval"
            :min="10"
            :max="300"
            :step="10"
            controls-position="right"
            @change="handleFormChange"
          />
          <span class="input-suffix">{{ $t('config.advanced.autoSaveIntervalUnit') }}</span>
          <div class="form-help">
            {{ $t('config.advanced.autoSaveIntervalDescription') }}
          </div>
        </el-form-item>
      </el-card>

      <!-- Developer Options -->
      <el-card class="setting-card" shadow="never">
        <template #header>
          <span class="card-title">{{ $t('config.advanced.developerOptions') }}</span>
        </template>

        <el-form-item :label="$t('config.advanced.debugMode')">
          <el-switch
            v-model="formData.debugMode"
            :active-text="$t('common.enable')"
            :inactive-text="$t('common.disable')"
            @change="handleFormChange"
          />
          <div class="form-help">
            {{ $t('config.advanced.debugModeDescription') }}
          </div>
        </el-form-item>
      </el-card>

      <!-- Tool Execution Settings -->
      <el-card class="setting-card" shadow="never">
        <template #header>
          <span class="card-title">{{ $t('config.advanced.toolExecutionSettings') }}</span>
        </template>

        <el-form-item :label="$t('config.advanced.requireToolConfirmation')">
          <el-switch
            v-model="formData.requireToolConfirmation"
            :active-text="$t('config.advanced.requireToolConfirmationActive')"
            :inactive-text="$t('config.advanced.requireToolConfirmationInactive')"
            @change="handleFormChange"
          />
          <div class="form-help">
            {{ $t('config.advanced.requireToolConfirmationDescription') }}
          </div>
        </el-form-item>

        <el-form-item v-if="formData.requireToolConfirmation" :label="$t('config.advanced.toolConfirmationTimeout')">
          <el-input-number
            v-model="formData.toolConfirmationTimeout"
            :min="30"
            :max="300"
            :step="30"
            controls-position="right"
            @change="handleFormChange"
          />
          <span class="input-suffix">{{ $t('config.advanced.toolConfirmationTimeoutUnit') }}</span>
          <div class="form-help">
            {{ $t('config.advanced.toolConfirmationTimeoutDescription') }}
          </div>
        </el-form-item>

        <el-form-item v-if="formData.requireToolConfirmation" :label="$t('config.advanced.allowBatchToolConfirmation')">
          <el-switch
            v-model="formData.allowBatchToolConfirmation"
            :active-text="$t('config.advanced.allowBatchToolConfirmationAllow')"
            :inactive-text="$t('config.advanced.allowBatchToolConfirmationDisallow')"
            @change="handleFormChange"
          />
          <div class="form-help">
            {{ $t('config.advanced.allowBatchToolConfirmationDescription') }}
          </div>
        </el-form-item>
      </el-card>

      <!-- Action Buttons -->
      <el-form-item class="action-buttons">
        <el-button type="primary" @click="saveSettings">{{ $t('config.advanced.saveSettings') }}</el-button>
        <el-button @click="resetToDefaults">{{ $t('config.advanced.resetDefaults') }}</el-button>
        <el-button type="danger" @click="clearAllData">{{ $t('config.advanced.clearAllData') }}</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { setLocale, getAvailableLocales } from '@/i18n/index.js'
import DebugLogger from '@/utils/DebugLogger.js'

// Props
const props = defineProps({
  advancedConfig: {
    type: Object,
    default: () => ({})
  }
})

// Emits
const emit = defineEmits(['config-change'])

// Internationalization
const { t } = useI18n()

// Available locales list
const availableLocales = getAvailableLocales()

// Reactive data
const formRef = ref()

const formData = ref({
  // Language settings
  locale: 'en-US',
  
  // Function settings
  autoSave: true,
  autoSaveInterval: 30,
  
  // Developer options
  debugMode: false,
  
  // Tool execution settings
  requireToolConfirmation: false,
  toolConfirmationTimeout: 60,
  allowBatchToolConfirmation: true,
  
  ...props.advancedConfig
})

// Methods
const saveSettings = () => {
  ElMessage.success(t('config.advanced.saveSuccess'))
  handleFormChange()
}

// Handle language change
const handleLanguageChange = (locale) => {
  setLocale(locale)
  // Refresh page to update Element Plus language pack
  setTimeout(() => {
    window.location.reload()
  }, 100)
}

const resetToDefaults = async () => {
  try {
    await ElMessageBox.confirm(
      t('config.advanced.resetConfirm'),
      t('config.advanced.resetConfirmTitle'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )
    
    formData.value = {
      locale: 'en-US',
      autoSave: true,
      autoSaveInterval: 30,
      debugMode: false,
      requireToolConfirmation: false,
      toolConfirmationTimeout: 60,
      allowBatchToolConfirmation: true
    }
    
    ElMessage.success(t('config.advanced.resetSuccess'))
    handleFormChange()
    
  } catch (error) {
    // User cancelled operation
  }
}

const clearAllData = async () => {
  try {
    await ElMessageBox.confirm(
      t('config.advanced.clearDataConfirm'),
      t('config.advanced.clearDataConfirmTitle'),
      {
        confirmButtonText: t('config.advanced.clearDataConfirmButton'),
        cancelButtonText: t('common.cancel'),
        type: 'error',
        confirmButtonClass: 'el-button--danger'
      }
    )
    
    // Clear localStorage
    const keysToRemove = []
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && (key.startsWith('mcp_') || key.startsWith('chat_'))) {
        keysToRemove.push(key)
      }
    }
    
    keysToRemove.forEach(key => localStorage.removeItem(key))
    
    ElMessage.success(t('config.advanced.clearDataSuccess'))
    
  } catch (error) {
    // User cancelled operation
  }
}

// Flag to prevent recursive updates
let isUpdatingFromProps = false

// Watch external changes - avoid recursive updates
watch(() => props.advancedConfig, (config) => {
  if (!isUpdatingFromProps && config) {
    isUpdatingFromProps = true
    const updatedData = { ...formData.value }
    Object.keys(config).forEach(key => {
      if (config[key] !== undefined && config[key] !== formData.value[key]) {
        updatedData[key] = config[key]
      }
    })
    formData.value = updatedData
    setTimeout(() => {
      isUpdatingFromProps = false
    }, 50)
  }
}, { deep: true, immediate: true })

// Method to manually trigger change events
const handleFormChange = () => {
  if (!isUpdatingFromProps) {
    // If debug mode changes, refresh DebugLogger status
    if (formData.value.debugMode !== undefined) {
      DebugLogger.refreshDebugStatus()
    }
    
    emit('config-change', { ...formData.value })
  }
}
</script>

<style scoped lang="scss">
.advanced-config {
  .config-form {
    max-width: 800px;
    
    .setting-card {
      margin-bottom: 20px;
      
      .card-title {
        font-weight: 600;
        color: var(--el-text-color-primary);
      }
      
      :deep(.el-card__body) {
        padding-top: 0;
      }
    }
    
    .form-help {
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-top: 4px;
      line-height: 1.4;
    }
    
    .input-suffix {
      margin-left: 8px;
      color: var(--el-text-color-secondary);
      font-size: 12px;
    }
    
    .action-buttons {
      margin-top: 30px;
      padding-top: 20px;
      border-top: 1px solid var(--el-border-color);
      
      .el-button {
        margin-right: 12px;
        margin-bottom: 8px;
      }
    }
  }
}
</style>