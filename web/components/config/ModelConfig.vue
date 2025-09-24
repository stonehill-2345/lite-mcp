<template>
  <div class="model-config">
    <el-form 
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="120px"
      class="config-form"
    >
      <!-- Model Provider -->
      <el-form-item :label="$t('config.modelConfig.modelProvider')" prop="provider">
        <el-select 
          v-model="formData.provider" 
          :placeholder="$t('config.modelConfig.selectModelProvider')"
          @change="handleProviderChange"
        >
          <el-option 
            v-for="provider in availableProviders"
            :key="provider.value"
            :label="provider.label"
            :value="provider.value"
          />
        </el-select>
      </el-form-item>

      <!-- API Key -->
      <el-form-item :label="$t('config.modelConfig.apiKey')" prop="apiKey">
        <el-input
          v-model="formData.apiKey"
          type="password"
          :placeholder="$t('config.modelConfig.inputApiKey')"
          show-password
          clearable
        />
        <div class="form-help">
          {{ $t('config.modelConfig.pleaseInputApiKey', { provider: getProviderLabel(formData.provider) }) }}
        </div>
      </el-form-item>

      <!-- Azure OpenAI Specific Configuration -->
      <template v-if="isAzureProvider">
        <!-- Azure Endpoint -->
        <el-form-item :label="$t('config.modelConfig.azureEndpoint')" prop="azureEndpoint">
          <el-input
            v-model="formData.azureEndpoint"
            :placeholder="$t('config.modelConfig.azureEndpointPlaceholder')"
            clearable
            @input="handleFormChange"
          />
          <div class="form-help">
            {{ $t('config.modelConfig.azureEndpointHelp') }}
          </div>
        </el-form-item>

        <!-- Deployment Name -->
        <el-form-item :label="$t('config.modelConfig.deploymentName')" prop="deploymentName">
          <el-input
            v-model="formData.deploymentName"
            :placeholder="$t('config.modelConfig.deploymentNamePlaceholder')"
            clearable
            @input="handleFormChange"
          />
          <div class="form-help">
            {{ $t('config.modelConfig.deploymentNameHelp') }}
          </div>
        </el-form-item>

        <!-- API Version -->
        <el-form-item :label="$t('config.modelConfig.apiVersion')" prop="apiVersion">
          <el-input
            v-model="formData.apiVersion"
            :placeholder="$t('config.modelConfig.apiVersionPlaceholder')"
            clearable
            @input="handleFormChange"
          />
          <div class="form-help">
            {{ $t('config.modelConfig.apiVersionHelp') }}
          </div>
        </el-form-item>
      </template>

      <!-- Model ID (Required for all providers) -->
      <el-form-item :label="$t('config.modelConfig.model')" prop="modelId">
        <!-- Directly input model name -->
        <el-input
          v-model="formData.modelId"
          :placeholder="getModelPlaceholder()"
          clearable
          @input="handleModelIdChange"
        />
        <div class="form-help">
          {{ getModelHelp() }}
        </div>
      </el-form-item>

      <!-- Base URL -->
      <el-form-item 
        v-if="needsBaseUrl" 
        :label="$t('config.modelConfig.baseUrl')" 
        prop="baseUrl"
      >
        <el-input
          v-model="formData.baseUrl"
          :placeholder="getBaseUrlPlaceholder()"
          clearable
          @input="handleFormChange"
        />
        <div class="form-help">
          {{ getBaseUrlHelp() }}
        </div>
      </el-form-item>

      <!-- Temperature -->
      <el-form-item :label="$t('config.modelConfig.temperature')" prop="temperature">
        <el-slider
          v-model="formData.temperature"
          :min="0"
          :max="2"
          :step="0.1"
          :format-tooltip="formatTemperature"
          show-input
          :input-size="'small'"
          @change="handleFormChange"
        />
        <div class="form-help">
          {{ $t('config.modelConfig.temperatureHelp') }}
        </div>
      </el-form-item>

      <!-- Maximum Tokens -->
      <el-form-item :label="$t('config.modelConfig.maxTokens')" prop="maxTokens">
        <el-input-number
          v-model="formData.maxTokens"
          :min="1"
          :max="32000"
          :step="100"
          controls-position="right"
          @change="handleFormChange"
        />
        <div class="form-help">
          {{ $t('config.modelConfig.maxTokensHelp') }}
        </div>
      </el-form-item>

      <!-- Context Tokens -->
      <el-form-item :label="$t('config.modelConfig.maxContextTokens')" prop="maxContextTokens">
        <el-input-number
          v-model="formData.maxContextTokens"
          :min="10000"
          :max="1000000"
          :step="10000"
          controls-position="right"
          @change="handleFormChange"
        />
        <div class="form-help">
          {{ $t('config.modelConfig.maxContextTokensHelp') }}
        </div>
      </el-form-item>

      <!-- Top P -->
      <el-form-item :label="$t('config.modelConfig.topP')" prop="topP">
        <el-slider
          v-model="formData.topP"
          :min="0"
          :max="1"
          :step="0.01"
          :format-tooltip="formatPercentage"
          show-input
          :input-size="'small'"
        />
        <div class="form-help">
          {{ $t('config.modelConfig.topPHelp') }}
        </div>
      </el-form-item>

      <!-- Advanced Options -->
      <el-collapse class="advanced-options">
        <el-collapse-item :title="$t('config.modelConfig.advancedOptions')">
          <!-- Frequency Penalty -->
          <el-form-item :label="$t('config.modelConfig.frequencyPenalty')" prop="frequencyPenalty">
            <el-slider
              v-model="formData.frequencyPenalty"
              :min="-2"
              :max="2"
              :step="0.1"
              :format-tooltip="formatPenalty"
              show-input
              :input-size="'small'"
            />
            <div class="form-help">
              {{ $t('config.modelConfig.frequencyPenaltyHelp') }}
            </div>
          </el-form-item>

          <!-- Presence Penalty -->
          <el-form-item :label="$t('config.modelConfig.presencePenalty')" prop="presencePenalty">
            <el-slider
              v-model="formData.presencePenalty"
              :min="-2"
              :max="2"
              :step="0.1"
              :format-tooltip="formatPenalty"
              show-input
              :input-size="'small'"
            />
            <div class="form-help">
              {{ $t('config.modelConfig.presencePenaltyHelp') }}
            </div>
          </el-form-item>

          <!-- Seed Value -->
          <el-form-item :label="$t('config.modelConfig.seed')" prop="seed">
            <el-input-number
              v-model="formData.seed"
              :min="0"
              :max="999999"
              controls-position="right"
              :placeholder="$t('config.modelConfig.seedPlaceholder')"
            />
            <div class="form-help">
              {{ $t('config.modelConfig.seedHelp') }}
            </div>
          </el-form-item>

          <!-- Stream Output -->
          <el-form-item :label="$t('config.modelConfig.streamOutput')">
            <el-switch
              v-model="formData.stream"
              :active-text="$t('config.modelConfig.enable')"
              :inactive-text="$t('config.modelConfig.disable')"
            />
            <div class="form-help">
              {{ $t('config.modelConfig.streamOutputHelp') }}
            </div>
          </el-form-item>
        </el-collapse-item>
      </el-collapse>

      <!-- Test Connection -->
      <el-form-item>
        <el-button 
          type="primary" 
          @click="testConnection"
          :loading="testing"
          :disabled="!canTest"
        >
          {{ $t('config.modelConfig.testConnection') }}
        </el-button>
        <el-button @click="resetToDefaults">{{ $t('config.modelConfig.resetToDefaults') }}</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { Refresh as RefreshIcon } from '@element-plus/icons-vue'
import { DEFAULT_MODEL_CONFIG, MODEL_PROVIDERS, ModelUtils } from '@/services/config/modelConfigs.js'

// Internationalization
const { t } = useI18n()

// Props
const props = defineProps({
  modelConfig: {
    type: Object,
    default: () => ({ ...DEFAULT_MODEL_CONFIG })
  }
})

// Emits
const emit = defineEmits(['config-change'])

// Reactive data
const formRef = ref()
const testing = ref(false)
const loadingModels = ref(false)

const formData = ref({
  provider: 'dashscope', // Default to DashScope
  apiKey: '',
  modelId: '', // Default model
  baseUrl: '',
  temperature: 0.7,
  maxTokens: 8000, // Updated output token limit (from 4000 to 8000)
  maxContextTokens: 500000, // Updated context window size (from 120000 to 500000, leaving enough space for GPT-4.1 Mini's 1M tokens)
  topP: 1.0,
  frequencyPenalty: 0,
  presencePenalty: 0,
  seed: null,
  stream: true,
  // Azure OpenAI specific fields
  azureEndpoint: 'https://xxx.azure.com/',
  deploymentName: 'gpt-4.1-mini',
  apiVersion: '2025-01-01-preview',
  ...props.modelConfig // Override default values from props
})

// Computed properties
const availableProviders = computed(() => {
  return Object.entries(MODEL_PROVIDERS).map(([key, provider]) => ({
    value: key,
    label: provider.name,
    description: provider.description
  }))
})

// Removed availableModels, now most providers directly input model names

const needsBaseUrl = computed(() => {
  return ['custom'].includes(formData.value.provider)
})

const isAzureProvider = computed(() => {
  return formData.value.provider === 'azure'
})



const canTest = computed(() => {
  if (!formData.value.provider) {
    return false
  }
  
  // Providers that need API Key
  const needsApiKey = ['azure', 'dashscope', 'custom'].includes(formData.value.provider)
  if (needsApiKey && !formData.value.apiKey) {
    return false
  }
  
  // All providers need model ID
  if (!formData.value.modelId || !formData.value.modelId.trim()) {
    return false
  }
  
  // Special validation for Azure OpenAI
  if (formData.value.provider === 'azure') {
    if (!formData.value.azureEndpoint || !formData.value.deploymentName || !formData.value.apiVersion) {
      return false
    }
  }
  
  // Providers that need Base URL (not including azure now)
  if (needsBaseUrl.value && !formData.value.baseUrl) {
    return false
  }
  
  return true
})

// Form validation rules
const rules = computed(() => {
  const baseRules = {
    provider: [
      { required: true, message: t('config.modelConfig.pleaseSelectModelProvider'), trigger: 'change' }
    ],
    temperature: [
      { type: 'number', min: 0, max: 2, message: t('config.modelConfig.temperatureRange'), trigger: 'change' }
    ],
    maxTokens: [
      { type: 'number', min: 1, max: 32000, message: t('config.modelConfig.tokenRange'), trigger: 'change' }
    ],
    maxContextTokens: [
      { type: 'number', min: 5000, max: 1000000, message: t('config.modelConfig.contextTokenRange'), trigger: 'change' }
    ]
  }
  
  // Only validate API Key for providers that need it
  const needsApiKey = ['azure', 'dashscope', 'custom'].includes(formData.value.provider)
  if (needsApiKey) {
    baseRules.apiKey = [
      { required: true, message: t('config.modelConfig.pleaseInputApiKey'), trigger: 'blur' }
    ]
  }
  
  // All providers need modelId validation
  baseRules.modelId = [
    { required: true, message: t('config.modelConfig.pleaseSelectOrInputModel'), trigger: 'change' }
  ]
  
  // Azure OpenAI specific field validation
  if (formData.value.provider === 'azure') {
    baseRules.azureEndpoint = [
      { required: true, message: t('config.modelConfig.pleaseInputAzureEndpoint'), trigger: 'blur' }
    ]
    baseRules.deploymentName = [
      { required: true, message: t('config.modelConfig.pleaseInputDeploymentName'), trigger: 'blur' }
    ]
    baseRules.apiVersion = [
      { required: true, message: t('config.modelConfig.pleaseInputApiVersion'), trigger: 'blur' }
    ]
  }
  
  // Providers that need baseUrl validation (not including azure now)
  if (needsBaseUrl.value) {
    baseRules.baseUrl = [
      { required: true, message: t('config.modelConfig.pleaseInputBaseUrl'), trigger: 'blur' }
    ]
  }
  
  return baseRules
})

// Methods
const formatTemperature = (value) => {
  if (value <= 0.3) return `${value} (${t('config.modelConfig.temperatureConservative')})`
  if (value <= 0.7) return `${value} (${t('config.modelConfig.temperatureBalanced')})`
  if (value <= 1.2) return `${value} (${t('config.modelConfig.temperatureCreative')})`
  return `${value} (${t('config.modelConfig.temperatureVeryCreative')})`
}

const formatPercentage = (value) => {
  return `${(value * 100).toFixed(0)}%`
}

const formatPenalty = (value) => {
  if (value < 0) return `${value} (${t('config.modelConfig.penaltyEncourage')})`
  if (value > 0) return `${value} (${t('config.modelConfig.penaltyPunish')})`
  return `${value} (${t('config.modelConfig.penaltyNeutral')})`
}

// Update context tokens based on model ID
const updateContextTokensForModel = (modelId) => {
  if (!modelId) return
  
  // Use ModelUtils to get the context limit of the model
  const contextLimit = ModelUtils.getModelContextLimit(modelId)
  
  // Reserve some space for output (usually 10-20% of context limit)
  const reserveTokens = Math.max(formData.value.maxTokens || 4000, contextLimit * 0.1)
  const recommendedContextTokens = Math.max(contextLimit - reserveTokens, 1000)
  
  // Only auto-update when current value is default or obviously mismatched
  if (formData.value.maxContextTokens === 120000 || // Default value
      formData.value.maxContextTokens > contextLimit || // Exceeds model limit
      formData.value.maxContextTokens < contextLimit * 0.1) { // Too small
    formData.value.maxContextTokens = recommendedContextTokens
  }
}

const getProviderLabel = (provider) => {
  return MODEL_PROVIDERS[provider]?.name || provider
}

const getBaseUrlPlaceholder = () => {
  const placeholders = {
    custom: t('config.modelConfig.customBaseUrlPlaceholder')
  }
  return placeholders[formData.value.provider] || t('config.modelConfig.baseUrlPlaceholder')
}

const getBaseUrlHelp = () => {
  const helps = {
    custom: t('config.modelConfig.customBaseUrlHelp'),
  }
  return helps[formData.value.provider] || t('config.modelConfig.baseUrlHelp')
}

const getModelPlaceholder = () => {
  const placeholders = {
    openai: t('config.modelConfig.openaiModelPlaceholder'),
    anthropic: t('config.modelConfig.anthropicModelPlaceholder'),
    deepseek: t('config.modelConfig.deepseekModelPlaceholder'),
    dashscope: t('config.modelConfig.dashscopeModelPlaceholder'),
    custom: t('config.modelConfig.customModelPlaceholder'),
    azure: t('config.modelConfig.azureModelPlaceholder')
  }
  return placeholders[formData.value.provider] || t('config.modelConfig.modelPlaceholder')
}

const getModelHelp = () => {
  const helps = {
    openai: t('config.modelConfig.openaiModelHelp'),
    anthropic: t('config.modelConfig.anthropicModelHelp'),
    deepseek: t('config.modelConfig.deepseekModelHelp'),
    dashscope: t('config.modelConfig.dashscopeModelHelp'),
    custom: t('config.modelConfig.customModelHelp'),
    azure: t('config.modelConfig.azureModelHelp')
  }
  return helps[formData.value.provider] || t('config.modelConfig.modelHelp')
}

// Handle model ID changes
const handleModelIdChange = (modelId) => {
  // Update context tokens
  updateContextTokensForModel(modelId)
  // Trigger form changes
  handleFormChange()
}

const handleProviderChange = (provider) => {
  // Set default model name for all providers (if available)
  const defaultModel = ModelUtils.getDefaultModel(provider)
  formData.value.modelId = defaultModel || ''
  
  // Set context length based on model
  updateContextTokensForModel(formData.value.modelId)
  
  // Azure OpenAI specific field settings
  if (provider === 'azure') {
    // Set default values (if currently empty)
    if (!formData.value.azureEndpoint) {
      formData.value.azureEndpoint = ''
    }
    if (!formData.value.deploymentName) {
      formData.value.deploymentName = ''
    }
    if (!formData.value.apiVersion) {
      formData.value.apiVersion = '2025-01-01-preview'
    }
    // Clear baseUrl (Azure doesn't use it)
    formData.value.baseUrl = ''
  } else {
    // Clear Azure-specific fields
    formData.value.azureEndpoint = ''
    formData.value.deploymentName = ''
    formData.value.apiVersion = '2025-01-01-preview'
  }
  
  // Set default baseUrl
  if (!needsBaseUrl.value) {
    formData.value.baseUrl = ''
  } else {
    // Set default values for providers that need baseUrl
    const providerConfig = ModelUtils.getProviderConfig(provider)
    formData.value.baseUrl = providerConfig?.baseUrl || ''
  }
  
  
  // Clear form validation errors
  setTimeout(() => {
    if (formRef.value) {
      formRef.value.clearValidate()
    }
  }, 50)
  
  handleFormChange()
}


// Format byte size
const formatBytes = (bytes) => {
  if (!bytes) return t('config.modelConfig.unknownSize')
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  if (bytes === 0) return '0 B'
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

// Format date
const formatDate = (dateString) => {
  if (!dateString) return t('config.modelConfig.unknownTime')
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const testConnection = async () => {
  try {
    testing.value = true
    
    // Form validation - handle by provider
    if (formData.value.provider === 'azure') {
      // Azure OpenAI special validation logic
      if (!formData.value.apiKey || formData.value.apiKey.trim() === '') {
        ElMessage.error(t('config.modelConfig.azureNeedsApiKey'))
        return
      }
      if (!formData.value.modelId || formData.value.modelId.trim() === '') {
        ElMessage.error(t('config.modelConfig.pleaseSelectOrInputModel'))
        return
      }
      // Azure can use azureEndpoint+deploymentName or complete baseUrl
      if (!formData.value.azureEndpoint && !formData.value.baseUrl) {
        ElMessage.error(t('config.modelConfig.pleaseConfigureAzureEndpoint'))
        return
      }
      if (formData.value.azureEndpoint && !formData.value.deploymentName) {
        ElMessage.error(t('config.modelConfig.pleaseConfigureDeploymentName'))
        return
      }
    } else {
      // Other providers use standard form validation
      try {
        const valid = await formRef.value.validate()
        if (!valid) return
      } catch (error) {
        console.error('Form validation failed:', error)
        ElMessage.error(t('config.modelConfig.configValidationFailed'))
        return
      }
    }
    
    // Validate required parameters
    if (!formData.value.provider) {
      ElMessage.error(t('config.modelConfig.pleaseSelectProvider'))
      return
    }
    
    // All providers need model ID
    if (!formData.value.modelId) {
      ElMessage.error(t('config.modelConfig.pleaseConfigureModel'))
      return
    }
    
    // Generic validation (avoid duplicate checks)
    const needsApiKey = ['azure', 'dashscope', 'custom'].includes(formData.value.provider)
    if (needsApiKey && (!formData.value.apiKey || formData.value.apiKey.trim() === '')) {
      ElMessage.error(t('config.modelConfig.pleaseInputApiKeyForProvider', { provider: getProviderLabel(formData.value.provider) }))
      return
    }
    
    // Build test configuration
    const testConfig = {
      provider: formData.value.provider,
      modelId: formData.value.modelId,
      apiKey: formData.value.apiKey,
      baseUrl: formData.value.baseUrl,
      temperature: 0.1, // Use lower temperature for testing
      maxTokens: 50, // Limit test response length
      stream: false,
      // Azure OpenAI specific fields
      azureEndpoint: formData.value.azureEndpoint,
      deploymentName: formData.value.deploymentName,
      apiVersion: formData.value.apiVersion
    }
    
    // Build test requests based on provider
    let testResult
    if (testConfig.provider === 'openai') {
      testResult = await testOpenAIConnection(testConfig)
    } else if (testConfig.provider === 'anthropic') {
      testResult = await testAnthropicConnection(testConfig)
    } else if (testConfig.provider === 'deepseek') {
      // DeepSeek uses OpenAI compatible interface
      testResult = await testOpenAICompatibleConnection(testConfig)
    } else if (testConfig.provider === 'dashscope') {
      // DashScope uses OpenAI compatible interface
      testResult = await testOpenAICompatibleConnection(testConfig)
    } else if (testConfig.provider === 'custom') {
      // Custom provider uses OpenAI compatible interface test
      testResult = await testCustomConnection(testConfig)
    } else if (testConfig.provider === 'azure') {
      testResult = await testAzureConnection(testConfig)
    } else {
      ElMessage.error(t('config.modelConfig.notSupportTestProvider', { provider: testConfig.provider }))
      return
    }
    
    if (testResult.success) {
      ElMessage.success(t('config.modelConfig.connectionTestSuccess', { time: testResult.responseTime }))
    } else {
      ElMessage.error(t('config.modelConfig.connectionTestFailed', { error: testResult.error }))
    }
    
  } catch (error) {
    console.error('Connection test error:', error)
    ElMessage.error(t('config.modelConfig.connectionTestError', { error: error.message }))
  } finally {
    testing.value = false
  }
}

// Test OpenAI connection
const testOpenAIConnection = async (config) => {
  const startTime = Date.now()
  
  try {
    const baseUrl = config.baseUrl || 'https://api.openai.com/v1'
    const response = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.apiKey}`
      },
      body: JSON.stringify({
        model: config.modelId,
        messages: [
          { role: 'user', content: 'Please reply "Connection test successful"' }
        ],
        max_tokens: config.maxTokens,
        temperature: config.temperature
      })
    })
    
    const responseTime = Date.now() - startTime
    
    if (!response.ok) {
      const errorData = await response.json()
      return {
        success: false,
        error: `HTTP ${response.status}: ${errorData.error?.message || 'Unknown error'}`,
        responseTime
      }
    }
    
    const data = await response.json()
    return {
      success: true,
      responseTime,
      response: data.choices?.[0]?.message?.content || 'No response content'
    }
    
  } catch (error) {
    return {
      success: false,
      error: error.message,
      responseTime: Date.now() - startTime
    }
  }
}

// Test Anthropic connection
const testAnthropicConnection = async (config) => {
  const startTime = Date.now()
  
  try {
    const baseUrl = config.baseUrl || 'https://api.anthropic.com/v1'
    const response = await fetch(`${baseUrl}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': config.apiKey,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: config.modelId,
        max_tokens: config.maxTokens,
        messages: [
          { role: 'user', content: 'Please reply "Connection test successful"' }
        ]
      })
    })
    
    const responseTime = Date.now() - startTime
    
    if (!response.ok) {
      const errorData = await response.json()
      return {
        success: false,
        error: `HTTP ${response.status}: ${errorData.error?.message || 'Unknown error'}`,
        responseTime
      }
    }
    
    const data = await response.json()
    return {
      success: true,
      responseTime,
      response: data.content?.[0]?.text || 'No response content'
    }
    
  } catch (error) {
    return {
      success: false,
      error: error.message,
      responseTime: Date.now() - startTime
    }
  }
}


// Test OpenAI compatible interface (for DeepSeek, DashScope, etc.)
const testOpenAICompatibleConnection = async (config) => {
  const startTime = Date.now()
  
  try {
    const baseUrl = config.baseUrl || getDefaultBaseUrl(config.provider)
    
    const response = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.apiKey}`
      },
      body: JSON.stringify({
        model: config.modelId,
        messages: [
          { role: 'user', content: 'Please reply "Connection test successful"' }
        ],
        max_tokens: config.maxTokens,
        temperature: config.temperature
      })
    })
    
    const responseTime = Date.now() - startTime
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      return {
        success: false,
        error: `HTTP ${response.status}: ${errorData.error?.message || `${config.provider} response error`}`,
        responseTime
      }
    }
    
    const data = await response.json()
    return {
      success: true,
      responseTime,
      response: data.choices?.[0]?.message?.content || 'No response content'
    }
    
  } catch (error) {
    return {
      success: false,
      error: error.message,
      responseTime: Date.now() - startTime
    }
  }
}

// Get default Base URL
const getDefaultBaseUrl = (provider) => {
  const defaultUrls = {
    deepseek: 'https://api.deepseek.com/v1',
    dashscope: 'https://dashscope.aliyuncs.com/compatible-mode/v1'
  }
  return defaultUrls[provider] || ''
}

// Test custom model connection (OpenAI compatible)  
const testCustomConnection = async (config) => {
  const startTime = Date.now()
  
  try {
    if (!config.baseUrl) {
      return {
        success: false,
        error: 'Please configure custom API endpoint URL',
        responseTime: Date.now() - startTime
      }
    }
    
    const response = await fetch(`${config.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.apiKey}`
      },
      body: JSON.stringify({
        model: config.modelId,
        messages: [
          { role: 'user', content: 'Please reply "Connection test successful"' }
        ],
        max_tokens: config.maxTokens,
        temperature: config.temperature
      })
    })
    
    const responseTime = Date.now() - startTime
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      return {
        success: false,
        error: `HTTP ${response.status}: ${errorData.error?.message || 'Custom endpoint response error'}`,
        responseTime
      }
    }
    
    const data = await response.json()
    return {
      success: true,
      responseTime,
      response: data.choices?.[0]?.message?.content || 'No response content'
    }
    
  } catch (error) {
    return {
      success: false,
      error: error.message,
      responseTime: Date.now() - startTime
    }
  }
}

// Test Azure OpenAI connection (using new structured configuration)
const testAzureConnection = async (config) => {
  const startTime = Date.now()
  
  try {
    // Prefer to use new structured configuration
    let apiUrl = ''
    if (config.azureEndpoint && config.deploymentName) {
      const azureEndpoint = config.azureEndpoint.replace(/\/$/, '') // Remove trailing slash
      const deploymentName = config.deploymentName
      const apiVersion = config.apiVersion || '2025-01-01-preview'
      
      apiUrl = `${azureEndpoint}/openai/deployments/${deploymentName}/chat/completions?api-version=${apiVersion}`
    } else if (config.baseUrl) {
      // Backward compatibility: if user is still using complete baseUrl approach
      apiUrl = config.baseUrl
    } else {
      return {
        success: false,
        error: 'Please configure Azure endpoint and deployment name, or complete API URL',
        responseTime: Date.now() - startTime
      }
    }
    
    const requestBody = {
        messages: [
          { role: 'user', content: 'Please reply "Connection test successful"' }
        ],
      max_tokens: config.maxTokens || 50,
      temperature: config.temperature || 0.1
    }
    
    // If there is a model ID, add it to the request body (although Azure may not need it, it might be useful in some cases)
    if (config.modelId) {
      requestBody.model = config.modelId
    }

    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'api-key': config.apiKey
      },
      body: JSON.stringify(requestBody)
    })
    
    const responseTime = Date.now() - startTime
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage = errorData.error?.message || errorData.message || `HTTP ${response.status} error`
      console.error('Azure OpenAI test failed:', errorData)
      return {
        success: false,
        error: `Connection failed: ${errorMessage}`,
      }
    }
    
    const data = await response.json()

    return {
      success: true,
      responseTime,
      response: data.choices?.[0]?.message?.content || 'No response content'
    }
    
  } catch (error) {
    console.error('Azure OpenAI test exception:', error)
    return {
      success: false,
      error: `Connection exception: ${error.message}`,
      responseTime: Date.now() - startTime
    }
  }
}

const resetToDefaults = () => {
  formData.value = { ...DEFAULT_MODEL_CONFIG }
  emitChange()
  ElMessage.success(t('config.modelConfig.hasResetToDefaults'))
}

const emitChange = () => {
  // Send configuration directly, no longer force default values
  emit('config-change', { ...formData.value })
}

// Flag to prevent recursive updates
let isUpdatingFromProps = false

// Watch external configuration changes - avoid recursive updates
watch(() => props.modelConfig, (newConfig) => {
  if (!isUpdatingFromProps && newConfig) {
    isUpdatingFromProps = true
    // Update configuration, allow empty values
    const updatedData = { ...formData.value }
    Object.keys(newConfig).forEach(key => {
      // Allow all values, including empty strings and other values, but exclude undefined
      if (newConfig[key] !== undefined && newConfig[key] !== formData.value[key]) {
        updatedData[key] = newConfig[key]
      }
    })
    formData.value = updatedData
    
    // Delay reset flag to ensure update completion
    setTimeout(() => {
      isUpdatingFromProps = false
    }, 50)
  }
}, { deep: true, immediate: true }) // Changed to immediate: true to respond to initial values immediately

// Method to manually trigger change event
const handleFormChange = () => {
  if (!isUpdatingFromProps) {
    emitChange()
  }
}

// Watch form data changes, auto-save configuration
watch(formData, (newData) => {
  if (!isUpdatingFromProps) {
    emitChange()
  }
}, { deep: true })
</script>

<style scoped lang="scss">
.model-config {
  .config-form {
    max-width: 600px;
    
    .form-help {
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-top: 4px;
      line-height: 1.4;
    }
    
    .model-description {
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-left: 8px;
    }
    
    .advanced-options {
      margin-top: 16px;
      
      :deep(.el-collapse-item__header) {
        font-weight: 500;
      }
      
      :deep(.el-collapse-item__content) {
        padding-top: 0;
      }
    }
    
    .el-slider {
      margin-right: 16px;
    }
    
    // Refresh button styles
    :deep(.el-input-group__append) {
      .el-button {
        padding: 0 8px;
        
        &.is-loading {
          .el-icon {
            animation: rotating 2s linear infinite;
          }
        }
      }
    }
  }
}

@keyframes rotating {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>