<template>
  <div class="mcp-index-container">
    <!-- AI Assistant Workspace -->
    <div class="assistant-workspace">
      <ChatInterface
        :session-id="'default'"
        :available-tools="enabledTools"
        :enabled-sessions="enabledSessions"
        :initial-config="chatConfig"
        @tool-called="handleToolCalled"
        @config-change="handleChatConfigChange"
        @message-sent="handleMessageSent"
        @error="handleError"
        ref="chatInterfaceRef"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import ChatInterface from '@/components/chat/ChatInterface.vue'
import { DEFAULT_MODEL_CONFIG } from '@/services/config/modelConfigs.js'
import { PromptTemplates } from '@/services/config/defaultPrompts.js'
import { getCacheByKey } from '@/utils/storage.js'
import DebugLogger from "@/utils/DebugLogger";

// Multi-language support
const { t } = useI18n()

// Reactive data
const assistantConfig = ref('')
const currentAssistantConfig = ref(null)
const enabledToolsList = ref([]) // Directly store the enabled tools list
const chatInterfaceRef = ref(null)
const enabledTools = ref([])
const enabledSessions = ref([])

const logger = DebugLogger.createLogger('LiteMCPIndex')

// Cache key name
const MCP_CONFIG_KEY = 'mcp_assistant_config'

// Chat configuration
const chatConfig = ref({
  modelConfig: {
    ...DEFAULT_MODEL_CONFIG,
    provider: 'dashscope', // Default to DashScope
    modelId: 'qwen-plus-latest',
    apiKey: '', // User needs to configure in settings
    temperature: 0.7,
    maxTokens: 8000
  },
  customPrompts: {
    reactSystemPrompt: PromptTemplates.buildReActSystemPrompt([], [], false)
  },
  reactEnabled: true,
  mcpConfigJson: ''
})

// Simple localStorage cache utility (setCache only, getCacheByKey imported from utils)
const setCache = (key, value) => {
  try {
    localStorage.setItem(key, value)
  } catch (error) {
    console.warn('Failed to save cache:', error)
  }
}

// Computed properties
const availableTools = computed(() => {
  // Ensure enabledToolsList is a valid array
  if (!Array.isArray(enabledToolsList.value)) {
    return []
  }

  // Filter out possible null/undefined items and validate each tool object
  return enabledToolsList.value.filter((tool) => {
    return (
      tool &&
      typeof tool === 'object' &&
      tool.name &&
      typeof tool.name === 'string'
    )
  })
})

const configuredTools = computed(() => {
  return availableTools.value.filter(tool => tool.enabled !== false)
})

// Methods
const updateMcpConfiguration = (config) => {
  try {
    // Update enabled tools
    enabledTools.value = availableTools.value.filter(tool => {
      // Determine tool enablement based on configuration
      return tool.enabled !== false
    })
    
    // Update enabled sessions
    enabledSessions.value = config.enabledSessions || []
  } catch (error) {
    logger.error('Failed to update MCP configuration:', error)
    ElMessage.error(t('mcp.messages.updateConfigFailed') + ': ' + error.message)
  }
}

const handleChatConfigChange = (data) => {
  // Handle chat configuration changes
  if (data.type === 'model' && data.config) {
    chatConfig.value.modelConfig = { ...chatConfig.value.modelConfig, ...data.config }
  } else if (data.type === 'prompts' && data.config) {
    chatConfig.value.customPrompts = { ...chatConfig.value.customPrompts, ...data.config }
  } else if (data.type === 'react' && data.config) {
    chatConfig.value.reactEnabled = data.config.enabled
  } else if (data.type === 'mcp') {
    // Handle MCP configuration changes
    if (data.configJson) {
      chatConfig.value.mcpConfigJson = data.configJson
      assistantConfig.value = data.configJson
    }
    
    // Update tool list
    if (data.enabledTools) {
      enabledTools.value = data.enabledTools
      enabledToolsList.value = data.enabledTools
    }
    
    // Update session information
    if (data.enabledSessions) {
      enabledSessions.value = data.enabledSessions
    }
    
    // Directly update MCP configuration
    try {
      const config = JSON.parse(data.configJson || '{}')
      updateMcpConfiguration(config)
    } catch (error) {
      logger.warn('Failed to parse MCP configuration:', error)
    }
  }
  
  // Save configuration to local storage
  saveConfiguration()
  
  // Handle legacy assistant config change format
  handleAssistantConfigChange({
    configJson: data.type === 'mcp' ? data.configJson : assistantConfig.value,
    enabledTools: data.type === 'mcp' ? data.enabledTools : enabledToolsList.value
  })
}

const handleToolCalled = (toolCall) => {
  logger.log('Tool call:', toolCall)
  
  // Enhance tool call information
  const enhancedToolCall = {
    ...toolCall,
    sessionId: 'default',
    timestamp: Date.now()
  }
  
  // Can emit to parent if needed
  logger.log('Enhanced tool call:', enhancedToolCall)
}

const handleMessageSent = (data) => {
  logger.log('Message sent:', data)
  
  // Can add message statistics or logging here
  updateMessageStats(data)
}

const handleError = (error) => {
  logger.error('Chat error:', error)
  ElMessage.error(t('mcp.messages.chatError') + ': ' + error.message)
}

const updateMessageStats = (data) => {
  // Update message statistics
  // Can add statistics logic here
}

const autoConnectMcpTools = async () => {
  try {
    // MCP configuration editor in ChatInterface now automatically loads and connects tools
    // No additional operations needed, tool status monitoring mechanism handles automatically
  } catch (error) {
    logger.error('Failed to auto-connect MCP tools:', error)
  }
}

const saveConfiguration = () => {
  try {
    const config = {
      chatConfig: chatConfig.value,
      timestamp: Date.now()
    }
    localStorage.setItem('mcp_chat_config_default', JSON.stringify(config))
    
    // Also save to legacy format
    if (assistantConfig.value) {
      setCache(MCP_CONFIG_KEY, assistantConfig.value)
    }
  } catch (error) {
    logger.warn('Failed to save configuration:', error)
  }
}

const loadConfiguration = () => {
  try {
    const config = getCacheByKey('mcp_chat_config_default', null)
    if (config) {
      if (config.chatConfig) {
        chatConfig.value = { ...chatConfig.value, ...config.chatConfig }
      }
    }
  } catch (error) {
    logger.warn('Failed to load configuration:', error)
  }
}

// Legacy method for compatibility
const handleAssistantConfigChange = (data) => {
  if (data.configJson) {
    assistantConfig.value = data.configJson

    // Save configuration to cache
    try {
      JSON.parse(data.configJson)
      setCache(MCP_CONFIG_KEY, data.configJson)
    } catch (error) {
      console.warn('Invalid configuration JSON, not saving to cache')
    }

    // Parse configuration (mainly for caching, not for tool calculation)
    try {
      currentAssistantConfig.value = JSON.parse(data.configJson)
    } catch (error) {
      currentAssistantConfig.value = null
    }
  }

  // Directly use the enabled tools list sent by the configuration editor
  if (data.enabledTools) {
    enabledToolsList.value = data.enabledTools
    logger.log('Updated available tools list:', enabledToolsList.value)
  }
}

// Exposed methods
const sendMessage = (message) => {
  if (chatInterfaceRef.value) {
    return chatInterfaceRef.value.sendMessage(message)
  }
}

const clearHistory = () => {
  if (chatInterfaceRef.value) {
    return chatInterfaceRef.value.clearHistory()
  }
}

const updateConfig = (config) => {
  if (chatInterfaceRef.value) {
    return chatInterfaceRef.value.updateConfig(config)
  }
}

// Watchers
watch(() => availableTools.value, (newTools) => {
  enabledTools.value = newTools.filter(tool => tool.enabled !== false)
}, { deep: true, immediate: true })

watch(() => assistantConfig.value, (newConfig) => {
  if (newConfig && newConfig !== chatConfig.value.mcpConfigJson) {
    // Update MCP configuration in chat config
    chatConfig.value.mcpConfigJson = newConfig
    
    try {
      updateMcpConfiguration(newConfig)
    } catch (error) {
      logger.warn('Failed to parse configuration JSON:', error)
    }
  }
})

// Lifecycle
onMounted(async () => {
  // Load saved configuration
  loadConfiguration()
  
  // Load cached configuration
  try {
    const cachedConfig = getCacheByKey(MCP_CONFIG_KEY)
    if (cachedConfig) {
      assistantConfig.value = cachedConfig
      currentAssistantConfig.value = cachedConfig
    }
  } catch (error) {
    console.warn('Failed to load cached configuration:', error)
  }
  
  // Initialize tools and sessions
  enabledTools.value = configuredTools.value
  
  // Try to auto-connect historically enabled MCP tools
  await autoConnectMcpTools()
})

onUnmounted(() => {
  // Save configuration
  saveConfiguration()
})

// Exposed methods for external access
defineExpose({
  sendMessage,
  clearHistory,
  updateConfig,
  autoConnectMcpTools,
  chatInterfaceRef
})
</script>

<style lang="scss" scoped>
// Modern chat interface style variables
$primary-color: #409EFF;
$secondary-color: #69b1ff;
$user-message-bg: #f0f9ff;
$assistant-message-bg: #ffffff;
$border-radius: 12px;
$shadow-light: 0 2px 12px rgba(0, 0, 0, 0.08);
$shadow-medium: 0 4px 16px rgba(0, 0, 0, 0.12);
$transition-default: all 0.3s ease;

.mcp-index-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4eaf5 100%);
  overflow: hidden;
}

.assistant-workspace {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border-radius: $border-radius;
  box-shadow: $shadow-medium;
  overflow: hidden;
  transition: $transition-default;

  // Responsive adjustments
  @media (max-width: 768px) {
    border-radius: 0;
    box-shadow: none;
  }

  // Chat interface container
  :deep(.chat-messages) {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 16px;

    // Message area
    :deep(.chat-messages .message-list) {
      flex: 1;
      overflow-y: auto;
      padding-right: 8px;
      scroll-behavior: smooth;

      // Custom scrollbar
      &::-webkit-scrollbar {
        width: 6px;
      }
      &::-webkit-scrollbar-track {
        background: transparent;
      }
      &::-webkit-scrollbar-thumb {
        background: rgba(144, 147, 153, 0.3);
        border-radius: 3px;
        &:hover {
          background: rgba(144, 147, 153, 0.5);
        }
      }
    }

    // Message bubble styles
    .message {
      margin-bottom: 16px;
      max-width: 85%;
      animation: fadeIn 0.3s ease forwards;

      &.user-message {
        align-self: flex-end;
        margin-left: auto;

        :deep(.message-bubble) {
          background: linear-gradient(135deg, $primary-color 0%, $secondary-color 100%);
          color: white;
          border-top-right-radius: 4px;
          box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
        }
      }

      &.assistant-message {
        .message-bubble {
          background: $assistant-message-bg;
          border-top-left-radius: 4px;
          box-shadow: $shadow-light;
        }
      }

      .message-bubble {
        padding: 12px 16px;
        border-radius: $border-radius;
        position: relative;
        transition: $transition-default;

        &:hover {
          transform: translateY(-2px);
          box-shadow: $shadow-medium;
        }

        .message-content {
          line-height: 1.6;
          font-size: 14px;
        }

        .message-time {
          font-size: 12px;
          color: #909399;
          margin-top: 4px;
          text-align: right;
        }
      }
    }

    // Input area
    :deep(.chat-input) {
      margin-top: 16px;
      background: white;
      border-radius: $border-radius;
      padding: 12px;
      box-shadow: $shadow-light;
      transition: $transition-default;

      &:focus-within {
        box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
      }

      .input-wrapper {
        display: flex;
        gap: 8px;

        textarea {
          flex: 1;
          border: none;
          resize: none;
          padding: 10px 12px;
          border-radius: 8px;
          background: #f5f7fa;
          transition: $transition-default;
          outline: none;

          &:focus {
            background: white;
            box-shadow: 0 0 0 1px $primary-color;
          }
        }

        button {
          background: linear-gradient(135deg, $primary-color 0%, $secondary-color 100%);
          color: white;
          border: none;
          border-radius: 8px;
          padding: 0 16px;
          cursor: pointer;
          transition: $transition-default;
          display: flex;
          align-items: center;
          justify-content: center;

          &:hover {
            opacity: 0.9;
            transform: translateY(-2px);
          }

          &:disabled {
            background: #c0c4cc;
            cursor: not-allowed;
            transform: none;
          }
        }
      }
    }
  }
}

// Fade in animation
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>