// AI Model Configuration - Support for major AI service providers
export const MODEL_CONFIGS = {
  // Azure OpenAI Configuration
  azure: {
    apiKeyRequired: true,
    baseUrl: '',
    headers: {
      'Content-Type': 'application/json',
      'api-key': '{apiKey}'
    },
    supportsFunctions: true,
    defaultModel: 'gpt-4.1-mini',
    needsCustomFields: true, // Mark as needing custom fields
    customFields: {
      azureEndpoint: '', // Azure Endpoint
      deploymentName: '', // Deployment Name  
      apiVersion: '2025-01-01-preview' // API Version
    }
  },

  // DashScope (Alibaba Cloud) Model Configuration
  dashscope: {
    apiKeyRequired: true,
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer {apiKey}'
    },
    supportsFunctions: true,
    defaultModel: 'qwen-plus-latest'
  },

  // Custom Model Configuration (OpenAI API compatible)
  custom: {
    apiKeyRequired: true,
    baseUrl: '',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer {apiKey}'
    },
    supportsFunctions: true,
    defaultModel: ''
  }
}

// Default Model Configuration
export const DEFAULT_MODEL_CONFIG = {
  provider: 'dashscope', // Default to DashScope
  modelId: 'qwen-plus-latest',
  temperature: 0.7,
  maxTokens: 8000, // Updated output token limit (increased from 4000 to 8000)
  maxContextTokens: 500000, // Updated context window size (increased from 120000 to 500000, leaving enough space for GPT-4.1 Mini's 1M tokens)
  topP: 1.0,
  presencePenalty: 0.0,
  frequencyPenalty: 0.0,
  stream: false,
  apiKey: '', // User needs to configure
  baseUrl: '',
  customHeaders: {},
  // Azure OpenAI specific fields
  azureEndpoint: 'https://shang-m814jp47-eastus2.cognitiveservices.azure.com/',
  deploymentName: 'gpt-4.1-mini',
  apiVersion: '2025-01-01-preview'
}

// ReAct Specific Model Configuration
export const REACT_MODEL_CONFIGS = {
  // Configuration optimized for ReAct tasks
  reasoning: {
    temperature: 0.3, // Lower temperature for improved reasoning accuracy
    topP: 0.9,
    maxTokens: 2000,
    maxContextTokens: 120000, // Reasoning tasks require more context
    presencePenalty: 0.1,
    frequencyPenalty: 0.1
  },
  
  // Tool calling configuration
  toolCalling: {
    temperature: 0.1, // Very low temperature to ensure tool calling accuracy
    topP: 0.8,
    maxTokens: 5000,
    maxContextTokens: 80000, // Tool calling requires relatively less context
    presencePenalty: 0.0,
    frequencyPenalty: 0.0
  },
  
  // Creative task configuration
  creative: {
    temperature: 0.9, // Higher temperature to increase creativity
    topP: 1.0,
    maxTokens: 3000,
    maxContextTokens: 100000, // Creative tasks require medium context
    presencePenalty: 0.3,
    frequencyPenalty: 0.3
  }
}

// Default context length for different models
export const MODEL_CONTEXT_LIMITS = {
  // Azure OpenAI supported models
  'gpt-4': 8192,
  'gpt-4-32k': 32768,
  'gpt-4-turbo': 128000,
  'gpt-4.1': 1000000,         // 1M tokens context
  'gpt-4.1-mini': 1000000,    // 1M tokens context  
  'gpt-4.1-nano': 1000000,    // 1M tokens context
  'gpt-4o': 128000,
  'gpt-4o-mini': 128000,
  'gpt-3.5-turbo': 16384,     // Updated to 16K
  'gpt-3.5-turbo-16k': 16384,
  
  // DashScope (Qwen) models - 2024-2025 latest data
  'qwen-turbo': 32768,        // Maintained at 32K
  'qwen-plus': 128000,        // Updated to 128K
  'qwen-max': 128000,         // Updated to 128K
  'qwen2.5-72b-instruct': 128000,  // Added Qwen2.5
  'qwen2.5-coder-32b-instruct': 128000,  // Added Qwen2.5 Coder
  'qwen-plus-latest': 128000,    // Qwen Plus Latest Version (128K)
  'qwen-turbo-latest': 128000,   // Qwen Turbo Latest Version (128K)
  'qwen-max-latest': 128000,     // Qwen Max Latest Version (128K)
  
  // Default value
  'default': 8192
}

// Model Utility Class
export const ModelUtils = {
  // Get provider configuration
  getProviderConfig(provider) {
    return MODEL_CONFIGS[provider] || null
  },

  // Get provider's default model
  getDefaultModel(provider) {
    const config = MODEL_CONFIGS[provider]
    return config?.defaultModel || ''
  },

  // Get model information by provider and model ID (simplified version, as we no longer hardcode model lists)
  getModelInfo(provider, modelId) {
    const providerConfig = this.getProviderConfig(provider)
    if (!providerConfig) return null
    
    return {
      id: modelId,
      provider: provider,
      name: modelId,
      providerConfig: providerConfig,
      supportsFunctions: providerConfig.supportsFunctions,
      // Since we no longer hardcode cost information, return default cost estimate
      costPer1kTokens: this.getDefaultCostEstimate(provider, modelId)
    }
  },

  // Get model information by full model ID (compatibility method)
  getModelById(modelId) {
    // Model ID format: "provider:modelName" or "modelName"
    let provider, modelName
    
    if (modelId.includes(':')) {
      [provider, modelName] = modelId.split(':', 2)
    } else {
      // If no provider prefix, try to infer from default configuration
      provider = 'azure'  // Use Azure OpenAI as default provider
      modelName = modelId
    }
    
    return this.getModelInfo(provider, modelName)
  },

  // Get model context length limit
  getModelContextLimit(modelId) {
    // Extract the actual model name from the model ID
    const modelName = modelId.includes(':') ? modelId.split(':')[1] : modelId
    
    // Find matching context length
    for (const [pattern, limit] of Object.entries(MODEL_CONTEXT_LIMITS)) {
      if (pattern === 'default') continue
      
      if (modelName.toLowerCase().includes(pattern.toLowerCase()) || 
          pattern.toLowerCase().includes(modelName.toLowerCase())) {
        return limit
      }
    }
    
    return MODEL_CONTEXT_LIMITS.default
  },

  // Get default cost estimate (based on provider's approximate cost)
  getDefaultCostEstimate(provider, modelId) {
    const costEstimates = {
      azure: {
        input: 0.001,  // Azure OpenAI estimate
        output: 0.002
      },
      dashscope: {
        input: 0.0005, // Qwen estimate
        output: 0.0015
      },
      custom: {
        input: 0.001,  // Default estimate
        output: 0.002
      }
    }
    
    return costEstimates[provider] || { input: 0.001, output: 0.002 }
  },

  // Estimate cost
  estimateCost(config, inputTokens, outputTokens = 0) {
    const costInfo = this.getDefaultCostEstimate(config.provider, config.modelId)
    if (!costInfo) {
      return null
    }
    
    const inputCost = (inputTokens / 1000) * costInfo.input
    const outputCost = (outputTokens / 1000) * costInfo.output
    
    return {
      inputCost,
      outputCost,
      totalCost: inputCost + outputCost,
      currency: 'USD'
    }
  },

  // Build request headers
  buildHeaders(config) {
    const providerConfig = this.getProviderConfig(config.provider)
    if (!providerConfig) return {}

    const headers = { ...providerConfig.headers }
    
    // Replace API key placeholder
    Object.keys(headers).forEach(key => {
      if (typeof headers[key] === 'string' && headers[key].includes('{apiKey}')) {
        headers[key] = headers[key].replace('{apiKey}', config.apiKey || '')
      }
    })
    
    // Add custom headers
    return {
      ...headers,
      ...config.customHeaders
    }
  },

  // Build request body
  buildRequestBody(config, messages, tools = []) {
    const providerConfig = this.getProviderConfig(config.provider)
    if (!providerConfig) return null
    
    const body = {
      model: config.modelId,
      messages,
      temperature: config.temperature,
      max_tokens: config.maxTokens,
      top_p: config.topP,
      stream: config.stream || false
    }
    
    // Add provider-specific parameters
    if (config.provider === 'azure' || config.provider === 'dashscope' || config.provider === 'custom') {
      if (config.presencePenalty !== undefined) {
        body.presence_penalty = config.presencePenalty
      }
      if (config.frequencyPenalty !== undefined) {
        body.frequency_penalty = config.frequencyPenalty
      }
      if (tools.length > 0 && providerConfig.supportsFunctions) {
        body.tools = tools
        body.tool_choice = 'auto'
      }
    }
    
    return body
  },

  // Validate configuration completeness
  validateConfig(config) {
    const providerConfig = this.getProviderConfig(config.provider)
    if (!providerConfig) {
      return { valid: false, error: `Unsupported provider: ${config.provider}` }
    }
    
    if (providerConfig.apiKeyRequired && !config.apiKey) {
      return { valid: false, error: `${config.provider} requires API key` }
    }
    
    if (!config.modelId) {
      return { valid: false, error: 'Please specify model name' }
    }
    
    // Azure OpenAI special validation
    if (config.provider === 'azure') {
      if (!config.azureEndpoint) {
        return { valid: false, error: 'Please enter Azure Endpoint' }
      }
      if (!config.deploymentName) {
        return { valid: false, error: 'Please enter Deployment Name' }
      }
      if (!config.apiVersion) {
        return { valid: false, error: 'Please enter API Version' }
      }
    }
    
    // Validate numeric ranges
    if (config.temperature < 0 || config.temperature > 2) {
      return { valid: false, error: 'Temperature value must be between 0-2' }
    }
    
    if (config.maxTokens < 1 || config.maxTokens > 200000) {
      return { valid: false, error: 'Maximum tokens must be between 1-200000' }
    }
    
    return { valid: true }
  },

  // Get request URL (handle different provider URL formats)
  getRequestUrl(config, endpoint = 'chat/completions') {
    const providerConfig = this.getProviderConfig(config.provider)
    if (!providerConfig) return null
    
    let baseUrl = config.baseUrl || providerConfig.baseUrl
    
    // Azure OpenAI special handling
    if (config.provider === 'azure') {
      // Prioritize using new structured configuration
      if (config.azureEndpoint && config.deploymentName) {
        const azureEndpoint = config.azureEndpoint.replace(/\/$/, '') // Remove trailing slash
        const deploymentName = config.deploymentName
        const apiVersion = config.apiVersion || '2025-01-01-preview'
        
        return `${azureEndpoint}/openai/deployments/${deploymentName}/chat/completions?api-version=${apiVersion}`
      }
      
      // Backward compatibility: if user is still using full baseUrl approach
      if (baseUrl) {
        // If baseUrl doesn't already contain api-version parameter, add it
        if (!baseUrl.includes('api-version=')) {
          const separator = baseUrl.includes('?') ? '&' : '?'
          const apiVersion = config.apiVersion || '2025-01-01-preview'
          baseUrl += `${separator}api-version=${apiVersion}`
        }
        return baseUrl
      }
      
      throw new Error('Azure OpenAI requires Azure Endpoint and Deployment Name configuration')
    }
    
    // Ensure other URLs end with /
    if (baseUrl && !baseUrl.endsWith('/')) {
      baseUrl += '/'
    }
    
    // Azure OpenAI and custom providers both use OpenAI compatible format
    return `${baseUrl}${endpoint}`
  },

  // Test model connection
  async testConnection(config) {
    const startTime = Date.now()
    
    try {
      const validation = this.validateConfig(config)
      if (!validation.valid) {
        throw new Error(validation.error)
      }
      
      const url = this.getRequestUrl(config)
      const headers = this.buildHeaders(config)
      
      // Send a simple test request
      const testMessages = [{ role: 'user', content: 'Please reply "Connection test successful"' }]
      const body = this.buildRequestBody(config, testMessages)
      
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body)
      })
      
      const responseTime = Date.now() - startTime
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        const errorMessage = errorData.error?.message || errorData.message || `HTTP ${response.status}`
        throw new Error(errorMessage)
      }
      
      const data = await response.json()
      let responseContent = 'No response content'
      
      // Azure OpenAI and custom providers both use OpenAI compatible format
      responseContent = data.choices?.[0]?.message?.content || responseContent
      
      return { 
        success: true, 
        message: 'Connection test successful',
        responseTime,
        response: responseContent
      }
    } catch (error) {
      return { 
        success: false, 
        error: error.message,
        responseTime: Date.now() - startTime
      }
    }
  }
}

// Cache key names
export const MODEL_CACHE_KEYS = {
  CONFIG: 'mcp_model_config',
  HISTORY: 'mcp_model_history',
  PREFERENCES: 'mcp_model_preferences'
}

// Model Provider Information
export const MODEL_PROVIDERS = {
  azure: {
    name: 'Azure OpenAI',
    description: 'Microsoft Azure hosted OpenAI service',
    needsApiKey: true,
    needsBaseUrl: false, // No longer need traditional baseUrl
    needsCustomFields: true, // Need custom fields
    customFields: {
      azureEndpoint: {
        label: 'Azure Endpoint',
        placeholder: 'https://your-resource.openai.azure.com',
        help: 'Azure OpenAI resource endpoint address',
        required: true
      },
      deploymentName: {
        label: 'Deployment Name',
        placeholder: 'my-gpt4-deployment',
        help: 'Deployment name created in Azure',
        required: true
      },
      apiVersion: {
        label: 'API Version',
        placeholder: '2025-01-01-preview',
        help: 'Azure OpenAI API version, can be adjusted as needed',
        required: true,
        default: '2025-01-01-preview'
      }
    },
    modelHelp: 'Enter the actual model name (e.g., gpt-4.1, gpt-35-turbo)'
  },
  dashscope: {
    name: 'DashScope',
    description: 'Alibaba Cloud Qwen model service',
    needsApiKey: true,
    needsBaseUrl: false,
    defaultBaseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1'
  },
  custom: {
    name: 'Custom',
    description: 'Custom endpoint compatible with OpenAI API',
    needsApiKey: true,
    needsBaseUrl: true,
    defaultBaseUrl: ''
  }
}