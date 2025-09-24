<template>
  <div class="mcp-chat-interface">
    <!-- Chat messages area -->
    <div class="chat-messages" ref="messagesContainer" @scroll="handleScroll">
      <div v-if="messages.length === 0" class="empty-chat">
        <el-empty :description="welcomeMessage">
          <div class="quick-actions">
            <h4>{{ $t('chat.quickStart') }}</h4>
            <el-tooltip
              v-for="suggestion in quickSuggestions"
              :key="suggestion.text"
              :content="suggestion.fullDescription || suggestion.text"
              placement="top"
              :disabled="!suggestion.fullDescription"
            >
              <el-button
                size="small"
                @click="sendQuickMessage(suggestion.text?.split('\n')[0], suggestion)"
                :disabled="isProcessing"
                :type="suggestion.toolName ? 'primary' : 'default'"
              >
                <el-icon v-if="suggestion.toolName" style="margin-right: 4px">
                  <Tools />
                </el-icon>
                {{ suggestion.text?.split('\n')[0]}}
              </el-button>
            </el-tooltip>

            <!-- Configuration hint - only shown when config is loaded but invalid -->
            <div v-if="configLoaded && !isConfigValid" class="config-hint">
              <el-alert
                :title="$t('chat.configHint.title')"
                type="warning"
                :closable="false"
                show-icon
              >
                <template #default>
                  <p>{{ $t('chat.configHint.incomplete') }}</p>
                  <ol>
                    <li v-for="(step, index) in $t('chat.configHint.steps')" :key="index">{{ step }}</li>
                  </ol>
                </template>
              </el-alert>
            </div>
          </div>
        </el-empty>
      </div>

      <!-- Message list -->
      <ChatMessages
        :messages="messages"
        :is-processing="isProcessing"
        :current-reasoning-content="currentReasoningContent"
        :current-stream-content="currentStreamContent"
        :current-progress="currentProgress"
        :accumulated-reasoning-steps="accumulatedReasoningSteps"
        :accumulated-stream-chunks="accumulatedStreamChunks"
        :pending-tool-confirmation="pendingToolConfirmation"
        :pending-tools="pendingTools"
        :allow-batch-tool-confirmation="
          toolConfirmationConfig.allowBatchToolConfirmation
        "
        :tool-confirmation-timeout="
          toolConfirmationConfig.toolConfirmationTimeout
        "
        @copy-message="handleCopyMessage"
        @retry-message="handleRetryMessage"
        @tool-confirm="handleToolConfirm"
        @tool-reject="handleToolReject"
        @tool-timeout="handleToolTimeout"
      />
    </div>

    <!-- Reserved space for fixed positioned input -->
    <div class="chat-input-placeholder"></div>

    <!-- Chat input area -->
    <ChatInput
      :disabled="isProcessing"
      :progress-message="currentProgress"
      :available-tools-count="availableTools.length"
      :connected-tools-count="connectedToolsCount"
      :model-config="modelConfig"
      :custom-prompts="customPrompts"
      :react-enabled="reactEnabled"
      @send-message="handleSendMessage"
      @stop-processing="handleStopProcessing"
      @clear-history="handleClearHistory"
      @model-config-change="handleModelConfigChange"
      @prompts-change="handlePromptsChange"
      @react-toggle="handleReActToggle"
      @settings-config-change="handleSettingsConfigChange"
      @mcp-config-applied="handleMcpConfigApplied"
      @open-assistant-mcp-config="handleOpenAssistantMcpConfig"
      @open-mcp-config-center="handleOpenMcpConfigCenter"
    />

    <!-- Tool call details dialog -->
    <el-dialog
      v-model="toolCallDialogVisible"
      :title="$t('chat.dialogs.toolCallDetails')"
      width="70%"
      :close-on-click-modal="false"
    >
      <ToolCallDisplay v-if="currentToolCall" :tool-call="currentToolCall" />
    </el-dialog>

    <!-- ReAct reasoning trace dialog -->
    <el-dialog
      v-model="reasoningDialogVisible"
      :title="$t('chat.dialogs.reactReasoningTrace')"
      width="80%"
      :close-on-click-modal="false"
    >
      <ReasoningTrace v-if="currentReasoning" :reasoning="currentReasoning" />
    </el-dialog>

    <!-- MCP configuration dialog -->
    <el-dialog
      v-model="showMcpConfigDialog"
      :title="$t('chat.dialogs.mcpConfigTitle')"
      width="90%"
      :close-on-click-modal="false"
      :destroy-on-close="false"
    >
      <div class="mcp-config-dialog-content">
        <!-- MCP configuration editor - delayed destruction to maintain state -->
        <McpConfigEditor
          v-model="mcpConfigJson"
          @config-change="handleMcpConfigChange"
          ref="mcpConfigEditorRef"
        />
      </div>
    </el-dialog>

    <!-- Preloaded MCP configuration editor (rendered off-screen when needed) -->
    <div 
      v-if="needsPreloadEditor" 
      class="preload-mcp-editor"
      style="position: fixed; left: -10000px; top: -10000px; width: 800px; height: 600px; overflow: hidden; opacity: 0; pointer-events: none; z-index: -1;"
    >
      <McpConfigEditor
        v-model="mcpConfigJson"
        @config-change="handleMcpConfigChange"
        ref="preloadMcpConfigEditorRef"
      />
    </div>
  </div>
</template>

<script setup>
import {computed, nextTick, onMounted, onUnmounted, ref, watch} from 'vue'
import {ElMessage, ElMessageBox} from 'element-plus'
import {useI18n} from 'vue-i18n'
import {Tools} from '@element-plus/icons-vue'

import {ChatService} from '@/services/chat/ChatService.js'
import {DEFAULT_MODEL_CONFIG} from '@/services/config/modelConfigs.js'
import {useClipboard} from '@/utils/UseClipboardHook.js'
import {getCacheByKey} from '@/utils/storage.js'
import ConfigManager from '@/services/config/ConfigStorage.js'
import DebugLogger from '@/utils/DebugLogger.js'
import ChatMessages from '@/components/chat/ChatMessages.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import ToolCallDisplay from '@/components/chat/ToolCallDisplay.vue'
import ReasoningTrace from '@/components/chat/ReasoningTrace.vue'
import McpConfigEditor from '@/components/mcp/McpConfigEditor.vue'
import mcpStateManager from '@/services/mcp/McpStateManager.js'

// Create component-specific logger
const logger = DebugLogger.createLogger('ChatInterface')

// Props
const props = defineProps({
  sessionId: {
    type: String,
    default: () => `session_${Date.now()}`
  },
  availableTools: {
    type: Array,
    default: () => []
  },
  enabledSessions: {
    type: Array,
    default: () => []
  },
  initialConfig: {
    type: Object,
    default: () => ({})
  }
})

// Emits
const emit = defineEmits([
  'tool-called',
  'config-change',
  'message-sent',
  'error'
])

// Hooks
const { copyToClipboard } = useClipboard()

// Internationalization
const { t } = useI18n()

// Reactive data
const messages = ref([])
const isProcessing = ref(false)
const currentProgress = ref('')
const messagesContainer = ref(null)

// Real-time reasoning state - changed to cumulative arrays
const currentReasoningContent = ref('')
const currentStreamContent = ref('')

// New: cumulative reasoning steps and streaming content arrays
const accumulatedReasoningSteps = ref([])
const accumulatedStreamChunks = ref([])

// Tool confirmation state
const pendingToolConfirmation = ref(false)
const pendingTools = ref([])

// Chat service
const chatService = ref(null)

// Configuration - use default values first, load from local storage later
const modelConfig = ref({
  ...DEFAULT_MODEL_CONFIG,
  ...props.initialConfig.modelConfig
})
const customPrompts = ref(props.initialConfig.customPrompts || {})
const reactEnabled = ref(false) // Temporarily set to false, will be loaded correctly in loadSavedConfigs

// Tool confirmation configuration
const toolConfirmationConfig = ref({
  requireToolConfirmation: false,
  toolConfirmationTimeout: 60,
  allowBatchToolConfirmation: true
})

// Configuration loading state
const configLoaded = ref(false)

// Statistics
const stats = ref({
  totalMessages: 0,
  totalTokensUsed: 0,
  totalCost: 0,
  toolCallsCount: 0,
  averageResponseTime: 0
})

// Dialog state
const toolCallDialogVisible = ref(false)
const reasoningDialogVisible = ref(false)
const showMcpConfigDialog = ref(false)
const currentToolCall = ref(null)
const currentReasoning = ref(null)

// MCP configuration related
const mcpConfigJson = ref('')
const mcpConfigEditorRef = ref(null)
const preloadMcpConfigEditorRef = ref(null) // Preload editor reference
const needsPreloadEditor = ref(true) // Control whether to show preload editor
const editorInitialized = ref(false) // Track if editor has been initialized
const mcpToolsCount = ref(0) // Independent tool count state

// Height observer reference
const heightObserver = ref(null)

const connectedToolsCount = computed(() => {
  // Get the currently active editor (visible dialog takes priority)
  const activeEditor = mcpConfigEditorRef.value || preloadMcpConfigEditorRef.value
  
  if (activeEditor && activeEditor.getEnabledToolsCount) {
    const count = activeEditor.getEnabledToolsCount()
    mcpToolsCount.value = count // Synchronize independent state
    return count
  }

  // If no editor is available yet, use cached state
  if (mcpToolsCount.value > 0) {
    return mcpToolsCount.value
  }

  // Otherwise calculate enabled tools count based on availableTools
  if (props.availableTools) {
    return props.availableTools.filter((tool) => tool.enabled !== false).length
  }

  return 0
})

// Load tool state from local storage
const loadMcpToolsCount = () => {
  try {
    const userStateCache = getCacheByKey('mcp_user_state_cache', {})
    if (userStateCache?.enabledTools) {
      mcpToolsCount.value = Object.values(userStateCache.enabledTools).filter(
        (enabled) => enabled
      ).length
    }
  } catch (error) {
    logger.warn('Failed to load MCP tool state:', error)
  }
}

// Basic quick suggestions (when no MCP tools available)
const defaultQuickSuggestions = [
  { text: t('chat.quickSuggestions.showAvailableTools') },
  { text: t('chat.quickSuggestions.getCurrentTime') },
  { text: t('chat.quickSuggestions.calculateAverage') }
]

// Simplify tool description, extract key information
const simplifyToolDescription = (toolName, description) => {
  if (!description || description.trim() === '') {
    return t('chat.quickSuggestions.useTool', { toolName })
  }
  
  // Truncate description to first 30 characters for conciseness
  let simplified = description.trim()
  if (simplified.length > 30) {
    simplified = simplified.substring(0, 30) + '...'
  }
  
  return simplified
}

// Dynamically generate quick suggestions
const quickSuggestions = computed(() => {
  const connectedTools = getConnectedTools()
  
  if (connectedTools.length === 0) {
    return defaultQuickSuggestions
  }
  
  const suggestions = []
  
  // Add a general tool overview suggestion
  suggestions.push({ text: t('chat.quickSuggestions.viewConnectedTools', { count: connectedTools.length }) })
  
  // Generate suggestions based on specific tools (max 4)
  const selectedTools = connectedTools.slice(0, 4)
  
  selectedTools.forEach(tool => {
    const suggestionText = simplifyToolDescription(tool.name, tool.description)
    
    suggestions.push({ 
      text: suggestionText,
      toolName: tool.name,
      serverName: tool.serverName,
      fullDescription: tool.description // Keep full description for hover tooltip
    })
  })
  
  // If there are many tools, add an "explore more" suggestion
  if (connectedTools.length > 4) {
    suggestions.push({ text: t('chat.quickSuggestions.exploreMoreTools') })
  }
  
  return suggestions.slice(0, 5) // Show max 5 suggestions
})

// Computed properties
const welcomeMessage = computed(() => {
  const connectedTools = getConnectedTools()
  const toolCount = connectedTools.length
  
  if (toolCount === 0) {
    return t('chat.welcome.noTools')
  } else {
    const serverNames = [...new Set(connectedTools.map(tool => tool.serverName))]
    const serverCount = serverNames.length
    
    return t('chat.welcome.withTools', { serverCount, toolCount })
  }
})

const isConfigValid = computed(() => {
  // Don't show error prompt when config is not loaded yet
  if (!configLoaded.value) {
    return true
  }

  const validation = validateModelConfig()
  return validation.valid
})

// Methods
const initializeChatService = () => {
  if (chatService.value) {
    chatService.value.destroy()
  }

  // Get debug mode setting from advanced config
  const advancedConfig = ConfigManager.loadAdvancedConfig()

  chatService.value = new ChatService({
    sessionId: props.sessionId,
    modelConfig: modelConfig.value,
    customPrompts: customPrompts.value,
    enableReAct: reactEnabled.value,
    debugMode: advancedConfig.debugMode || false,
    onMessage: handleServiceMessage,
    onToolCall: handleServiceToolCall,
    onError: handleServiceError,
    onProgress: handleServiceProgress,
    onStreamChunk: handleStreamChunk,
    onReasoningUpdate: handleReasoningUpdate,
    onToolConfirmationRequest: handleToolConfirmationRequest
  })

  // Update tools and sessions - prioritize currently connected tools and sessions
  const connectedTools = getConnectedTools()
  const currentSessions = props.enabledSessions || []
  
  // If there are connected tools, use them; otherwise use tools from props
  const toolsToUse = connectedTools.length > 0 ? connectedTools : (props.availableTools || [])
  
  logger.log('Tool and session state when initializing ChatService:', {
    connectedToolsCount: connectedTools.length,
    propsToolsCount: props.availableTools?.length || 0,
    currentSessionsCount: currentSessions.length,
    usingConnectedTools: connectedTools.length > 0
  })
  
  chatService.value.updateAvailableTools(toolsToUse, currentSessions)

  // Set tool confirmation configuration
  if (chatService.value.reactEngine) {
    chatService.value.reactEngine.setToolConfirmationConfig(
      toolConfirmationConfig.value
    )
  }

  // Load message history
  messages.value = chatService.value.getHistory()

  // Update statistics
  stats.value = chatService.value.getStats()

  logger.log('Chat service initialization completed')
}

const handleSendMessage = async (message) => {
  if (!chatService.value) {
    ElMessage.error(t('chat.messages.chatServiceNotInitialized'))
    return
  }

  // Check if model configuration is complete
  const configValidation = validateModelConfig()
  if (!configValidation.valid) {
    ElMessage.error(`${t('chat.messages.configError')}: ${configValidation.error}`)
    ElMessage.info(t('chat.messages.clickSettingsToConfig'))
    return
  }

  try {
    isProcessing.value = true
    currentProgress.value = t('chat.messages.startProcessing')

    // Reset all real-time state - including cumulative arrays
    currentReasoningContent.value = ''
    currentStreamContent.value = ''
    accumulatedReasoningSteps.value = []
    accumulatedStreamChunks.value = []

    const result = await chatService.value.sendMessage(message)

    // Emit event
    emit('message-sent', {
      userMessage: message,
      assistantMessage: result
    })

    // When user sends message, immediately scroll to bottom
    userScrolled.value = false
    await nextTick()
    scrollToBottom(true) // Immediately scroll to show user message
  } catch (error) {
    logger.error('Detailed error sending message:', error)
    ElMessage.error(`${t('chat.messages.sendMessageFailed')}: ${error.message}`)
    emit('error', error)
  } finally {
    isProcessing.value = false
    currentProgress.value = ''

    // Clear accumulated state after processing is complete
    setTimeout(() => {
      currentReasoningContent.value = ''
      currentStreamContent.value = ''
      accumulatedReasoningSteps.value = []
      accumulatedStreamChunks.value = []
    }, 500) // Delay clearing to let user see the complete process
  }
}

// Validate model configuration
const validateModelConfig = () => {
  if (!modelConfig.value.provider) {
    logger.log(
      '❌ Validation failed: Please select model provider, current value:',
      modelConfig.value.provider
    )
    return { valid: false, error: t('chat.validation.selectProvider') }
  }

  if (!modelConfig.value.modelId) {
    logger.log(
      '❌ Validation failed: Please select or enter model, current value:',
      modelConfig.value.modelId
    )
    return { valid: false, error: t('chat.validation.selectModel') }
  }

  // Check if API Key is required
  const needsApiKey = [
    'openai',
    'anthropic',
    'deepseek',
    'dashscope',
    'azure'
  ].includes(modelConfig.value.provider)
  if (needsApiKey && !modelConfig.value.apiKey) {
    logger.log(
      `❌ Validation failed: ${modelConfig.value.provider} requires API key, current value:`,
      modelConfig.value.apiKey
    )
    return {
      valid: false,
      error: `${modelConfig.value.provider} ${t('chat.validation.apiKeyRequired')}`
    }
  }

  // Special validation for Azure OpenAI
  if (modelConfig.value.provider === 'azure') {
    if (!modelConfig.value.azureEndpoint && !modelConfig.value.baseUrl) {
      logger.log('❌ Validation failed: Azure OpenAI requires endpoint or base URL configuration')
      return { valid: false, error: t('chat.validation.azureEndpointRequired') }
    }
    if (modelConfig.value.azureEndpoint && !modelConfig.value.deploymentName) {
      logger.log(
        '❌ Validation failed: Azure OpenAI requires deployment name configuration, current value:',
        modelConfig.value.deploymentName
      )
      return { valid: false, error: t('chat.validation.deploymentNameRequired') }
    }
    if (!modelConfig.value.apiVersion) {
      logger.log(
        '❌ Validation failed: Azure OpenAI requires API version configuration, current value:',
        modelConfig.value.apiVersion
      )
      return { valid: false, error: t('chat.validation.apiVersionRequired') }
    }
  }

  // Check if Base URL is required (now excluding azure)
  const needsBaseUrl = ['custom'].includes(modelConfig.value.provider)
  if (needsBaseUrl && !modelConfig.value.baseUrl) {
    logger.log(
      '❌ Validation failed: Please configure base URL, current value:',
      modelConfig.value.baseUrl
    )
    return { valid: false, error: t('chat.validation.baseUrlRequired') }
  }

  logger.log('✅ Configuration validation passed')
  return { valid: true }
}

const sendQuickMessage = (message, suggestion = null) => {
  if (!isProcessing.value) {
    // If suggestion contains tool information, generate more detailed message
    if (suggestion && suggestion.toolName) {
      let enhancedMessage = t('chat.quickSuggestions.helpWithTask', { message })
      
      // If there's a complete description, add more context
      enhancedMessage += t('chat.quickSuggestions.useToolForTask', {
          serverName: suggestion.serverName,
          toolName: suggestion.toolName
        })
      
      handleSendMessage(enhancedMessage)
    } else {
      handleSendMessage(message)
    }
  }
}

const handleServiceMessage = (message) => {
  messages.value = chatService.value.getHistory()
  stats.value = chatService.value.getStats()
}

const handleServiceToolCall = (toolCall) => {
  emit('tool-called', toolCall)
}

const handleServiceError = (error) => {
  ElMessage.error(`${t('chat.messages.chatServiceError')}: ${error.message}`)
  isProcessing.value = false
  currentProgress.value = ''
  emit('error', error)
}

const handleServiceProgress = (progress) => {
  currentProgress.value = progress
  isProcessing.value = !!progress
}

// 【*】Streaming content callback
const handleStreamChunk = (chunk) => {
  // Accumulate streaming content chunks
  accumulatedStreamChunks.value.push({
    content: chunk,
    timestamp: Date.now(),
    id: `chunk_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  })

  // Merge all streaming content
  currentStreamContent.value = accumulatedStreamChunks.value
    .map((item) => item.content)
    .join('')
}

// 【*】Reasoning process update callback
const handleReasoningUpdate = (reasoning) => {
  // Check if it's a new reasoning step (avoid adding duplicate content)
  const lastStep =
    accumulatedReasoningSteps.value[accumulatedReasoningSteps.value.length - 1]

  if (!lastStep || lastStep.content !== reasoning) {
    // Add new reasoning step
    accumulatedReasoningSteps.value.push({
      content: reasoning,
      timestamp: Date.now(),
      id: `reasoning_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    })

    // Merge all reasoning steps into complete content
    currentReasoningContent.value = accumulatedReasoningSteps.value
      .map((step) => step.content)
      .join('\n')
  }

  // Also trigger UI update to show reasoning process (preserve original logic)
  if (messages.value.length > 0) {
    const lastMessage = messages.value[messages.value.length - 1]
    if (lastMessage.role === 'assistant') {
      // Update reasoning content of the last assistant message
      lastMessage.reasoningContent = currentReasoningContent.value
      lastMessage.reasoning = lastMessage.reasoning || {}
      lastMessage.reasoning.content = currentReasoningContent.value
    }
  }
}

// Tool confirmation request callback
const handleToolConfirmationRequest = (data) => {
  logger.log('Received tool confirmation request:', data)

  if (data.pendingTools && data.pendingTools.length > 0) {
    // Set confirmation state
    pendingToolConfirmation.value = true
    pendingTools.value = data.pendingTools

    // Ensure real-time reasoning is currently displayed
    if (!isProcessing.value) {
      isProcessing.value = true
    }

    // Show tool confirmation status information (through dedicated status prompt, doesn't affect AI reasoning context)
    if (data.status === 'waiting_confirmation' && data.message) {
      // Can add a dedicated status prompt component here or use ElMessage
      ElMessage({
        message: t('chat.toolConfirmation.waitingConfirmation', { message: data.message }),
        type: 'info',
        duration: 3000,
        showClose: true
      })
    }
  } else {
    // Reset confirmation state
    pendingToolConfirmation.value = false
    pendingTools.value = []

    // Show confirmation result status information
    if (data.status && data.message) {
      let messageType = 'info'
      let icon = ''

      switch (data.status) {
        case 'confirmed':
          messageType = 'success'
          icon = '✅'
          break
        case 'rejected':
          messageType = 'warning'
          icon = '❌'
          break
        case 'timeout':
          messageType = 'error'
          icon = '⏰'
          break
      }

      ElMessage({
        message: `${icon} ${data.message}`,
        type: messageType,
        duration: 3000,
        showClose: true
      })
    }

    if (data.confirmed) {
      logger.log(t('chat.toolConfirmation.executionConfirmed'))
    } else if (data.rejected) {
      logger.log(t('chat.toolConfirmation.executionRejected'))
    } else if (data.timedOut) {
      logger.log(t('chat.toolConfirmation.confirmationTimeout'))
    }
  }
}

const handleModelConfigChange = (config) => {
  modelConfig.value = { ...modelConfig.value, ...config }
  if (chatService.value) {
    chatService.value.updateModelConfig(modelConfig.value)
  }

  // Save configuration to local storage
  ConfigManager.saveModelConfig(modelConfig.value)
  logger.log('Model configuration saved:', modelConfig.value)

  emit('config-change', {
    type: 'model',
    config: modelConfig.value
  })
}

const handlePromptsChange = (prompts) => {
  customPrompts.value = { ...customPrompts.value, ...prompts }
  if (chatService.value) {
    chatService.value.updateCustomPrompts(customPrompts.value)
  }

  // Save configuration to local storage
  ConfigManager.savePromptsConfig(customPrompts.value)
  logger.log('Prompts configuration saved:', customPrompts.value)

  emit('config-change', {
    type: 'prompts',
    config: customPrompts.value
  })
}

const handleReActToggle = (enabled) => {
  reactEnabled.value = enabled
  
  // Only reinitialize when ReAct state actually changes
  if (chatService.value && chatService.value.enableReAct !== enabled) {
    // Save current tool and session state
    const currentTools = chatService.value.availableTools || []
    const currentSessions = chatService.value.enabledSessions || []
    
    logger.log('ReAct state changed, reinitializing ChatService:', {
      enabled,
      preservedToolsCount: currentTools.length,
      preservedSessionsCount: currentSessions.length
    })
    
    // Reinitialize chat service
    initializeChatService()
    
    // Restore tool and session state
    if (chatService.value && (currentTools.length > 0 || currentSessions.length > 0)) {
      chatService.value.updateAvailableTools(currentTools, currentSessions)
      logger.log('Tool and session state restored')
    }
  } else if (chatService.value) {
    // If ChatService exists but ReAct state hasn't changed, only update configuration
    chatService.value.enableReAct = enabled
    if (chatService.value.reactEngine) {
      // If needed, can update ReActEngine configuration here
      logger.log('Updated existing ChatService ReAct configuration:', enabled)
    }
  }

  // Save configuration to local storage
  ConfigManager.saveReActConfig({ enabled })
  logger.log('ReAct configuration saved:', { enabled })

  emit('config-change', {
    type: 'react',
    config: { enabled }
  })
}

const handleAdvancedConfigChange = (config) => {
  logger.log('Advanced configuration changed:', config)

  // If debug mode changes, need to update ChatService
  if (config.debugMode !== undefined && chatService.value) {
    chatService.value.debugMode = config.debugMode
    if (chatService.value.reactEngine) {
      chatService.value.reactEngine.debugMode = config.debugMode
    }
  }

  // If tool confirmation configuration changes, update related configuration
  if (
    config.requireToolConfirmation !== undefined ||
    config.toolConfirmationTimeout !== undefined ||
    config.allowBatchToolConfirmation !== undefined
  ) {
    toolConfirmationConfig.value = {
      ...toolConfirmationConfig.value,
      ...config
    }

    // Update ReActEngine tool confirmation configuration
    if (chatService.value && chatService.value.reactEngine) {
      chatService.value.reactEngine.setToolConfirmationConfig(
        toolConfirmationConfig.value
      )
    }

    logger.log('Tool confirmation configuration updated:', toolConfirmationConfig.value)
  }

  emit('config-change', {
    type: 'advanced',
    config: config
  })
}

const handleSettingsConfigChange = (data) => {
  logger.log('Settings configuration changed:', data)

  // Handle configuration changes based on type
  if (data.type === 'advanced') {
    handleAdvancedConfigChange(data.config)
  } else {
    // Forward other types of configuration changes
    emit('config-change', data)
  }
}

// Handle MCP configuration application event
const handleMcpConfigApplied = (configData) => {
  logger.log('Received MCP configuration application event:', configData)
  ElMessage.success(`${t('chat.messages.mcpConfigApplied')}: ${configData.serverName || t('chat.messages.unknownServer')}`)

  // Can add specific configuration application logic here
  if (configData.configJson) {
    mcpConfigJson.value = configData.configJson
    handleMcpConfigChange({
      configJson: configData.configJson,
      enabledTools: configData.enabledTools,
      enabledSessions: configData.enabledSessions
    })
  }
}

// Handle opening assistant MCP configuration dialog
const handleOpenAssistantMcpConfig = async () => {
  showMcpConfigDialog.value = true
  logger.log('Opening assistant MCP configuration dialog')
  
  // When dialog opens, transfer state from preload editor to main editor
  await nextTick()
  
  // Wait for main editor to be ready, then hide preload editor to avoid conflicts
  setTimeout(() => {
    if (mcpConfigEditorRef.value && preloadMcpConfigEditorRef.value) {
      logger.log('🔄 Transferring from preload editor to main editor')
      needsPreloadEditor.value = false // Hide preload editor to avoid conflicts
    }
  }, 500)
}

// Handle opening MCP configuration center
const handleOpenMcpConfigCenter = () => {
  // This event is just for logging, actual navigation is handled in ChatInput
  logger.log('User requested to open MCP configuration center')
}

// MCP configuration change protection timestamp
let lastMcpConfigChangeTime = 0

const handleMcpConfigChange = (data) => {
  lastMcpConfigChangeTime = Date.now() // Record last MCP configuration change time

  // Handle MCP configuration change
  if (data.configJson) {
    mcpConfigJson.value = data.configJson
  }

  // Update tool count state
  const activeEditor = mcpConfigEditorRef.value || preloadMcpConfigEditorRef.value
  if (activeEditor && activeEditor.getEnabledToolsCount) {
    mcpToolsCount.value = activeEditor.getEnabledToolsCount()
  }

  // Get currently connected tools and sessions and update to ChatService
  updateChatService(data.enabledTools, data.enabledSessions)

  // Forward configuration change to parent component
  emit('config-change', {
    type: 'mcp',
    configJson: data.configJson || mcpConfigJson.value,
    enabledTools: data.enabledTools || props.availableTools,
    enabledSessions: data.enabledSessions || [], // New: pass session information
    enabledToolsCount: mcpToolsCount.value
  })
}

// Update ChatService tools
const updateChatService = (overrideTools = null, overrideSessions = null) => {
  if (chatService.value) {
    try {
      // Get tool information
      let connectedTools = overrideTools
      if (!connectedTools && (mcpConfigEditorRef.value || preloadMcpConfigEditorRef.value)) {
        connectedTools = getConnectedTools()
      }
      if (!connectedTools) {
        connectedTools = props.availableTools || []
      }

      // Get session information - prioritize existing session information to avoid clearing
      let enabledSessions = overrideSessions
      if (!enabledSessions) {
        // First try to get session information from current state
        const currentSessions = chatService.value.enabledSessions || []
        if (
          currentSessions.length > 0 &&
          (!props.enabledSessions || props.enabledSessions.length === 0)
        ) {
          // If current has sessions but props is empty, keep current sessions from being cleared
          enabledSessions = currentSessions
        } else {
          enabledSessions = props.enabledSessions || []
        }
      }

      // Update chat service available tools and sessions
      chatService.value.updateAvailableTools(connectedTools, enabledSessions)
    } catch (error) {
      logger.error('Failed to update ChatService tools:', error)
    }
  } else {
    logger.warn('⚠️ ChatInterface cannot update tool state:', {
      hasChatService: !!chatService.value,
      hasMcpConfigEditor: !!mcpConfigEditorRef.value
    })
  }
}

// Get currently connected tools
const getConnectedTools = () => {
  // Get the currently active editor (visible dialog takes priority)
  const activeEditor = mcpConfigEditorRef.value || preloadMcpConfigEditorRef.value
  
  if (activeEditor && activeEditor.getConnectedTools) {
    try {
      return activeEditor.getConnectedTools()
    } catch (error) {
      logger.error('Failed to get connected tools from active editor:', error)
    }
  }

  return []
}

const handleClearHistory = async () => {
  try {
    await ElMessageBox.confirm(
      t('chat.dialogs.clearHistoryConfirm'),
      t('chat.dialogs.clearHistoryTitle'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    if (chatService.value) {
      chatService.value.clearHistory()
      messages.value = []
      stats.value = chatService.value.getStats()
    }

    ElMessage.success(t('chat.dialogs.clearHistorySuccess'))
  } catch (error) {
    // User cancelled operation
  }
}

const handleCopyMessage = async (content) => {
  try {
    const success = await copyToClipboard(
      content,
      t('chat.dialogs.copySuccess'),
      t('chat.dialogs.copyFailed')
    )
    if (!success) {
      logger.error('Failed to copy message')
    }
  } catch (error) {
    logger.error('Error occurred while copying message:', error)
  }
}

const handleRetryMessage = (messageId) => {
  // Find message and resend
  const messageIndex = messages.value.findIndex((m) => m.id === messageId)
  if (messageIndex > 0) {
    const previousMessage = messages.value[messageIndex - 1]
    if (previousMessage.role === 'user') {
      handleSendMessage(previousMessage.content)
    }
  }
}

const handleStopProcessing = () => {
  if (chatService.value) {
    logger.log('User requested to stop processing')
    chatService.value.stopProcessing()
    ElMessage({
      message: t('chat.dialogs.stopProcessing'),
      type: 'warning',
      duration: 2000,
      showClose: true
    })
  } else {
    // If no chatService, directly reset state
    isProcessing.value = false
    currentProgress.value = ''
    ElMessage.info(t('chat.dialogs.stopSuccess'))
  }
}

// Tool confirmation handling methods
const handleToolConfirm = (confirmedTools) => {
  logger.log('User confirmed tool execution:', confirmedTools)

  if (chatService.value && chatService.value.reactEngine) {
    chatService.value.reactEngine.handleToolConfirmation(confirmedTools)
  }

  // Reset confirmation state
  pendingToolConfirmation.value = false
  pendingTools.value = []
}

const handleToolReject = () => {
  logger.log('User rejected tool execution')

  if (chatService.value && chatService.value.reactEngine) {
    chatService.value.reactEngine.handleToolRejection()
  }

  // Reset confirmation state
  pendingToolConfirmation.value = false
  pendingTools.value = []
}

const handleToolTimeout = () => {
  logger.log('Tool confirmation timeout')

  if (chatService.value && chatService.value.reactEngine) {
    chatService.value.reactEngine.handleToolConfirmationTimeout()
  }

  // Reset confirmation state
  pendingToolConfirmation.value = false
  pendingTools.value = []
}

const scrollToBottom = (force = false) => {
  if (messagesContainer.value) {
    const container = messagesContainer.value
    // Immediately attempt to scroll
    if (force || !userScrolled.value || isUserAtBottom()) {
      container.scrollTop = container.scrollHeight
    }

    // Use requestAnimationFrame to ensure DOM is updated before scrolling
    requestAnimationFrame(() => {
      if (force || !userScrolled.value || isUserAtBottom()) {
        container.scrollTop = container.scrollHeight
      }
    })
  } else {
    console.log('❌ messagesContainer does not exist')
  }
}

// Monitor tool changes - add debouncing and conditional checks to avoid infinite loops
let propsUpdateTimeout = null
const updateFromProps = () => {
  if (propsUpdateTimeout) clearTimeout(propsUpdateTimeout)
  propsUpdateTimeout = setTimeout(() => {
    if (chatService.value) {
      // Additional check: avoid clearing existing sessions when they are stable
      const currentSessions = chatService.value.enabledSessions || []
      const propsSessions = props.enabledSessions || []

      if (currentSessions.length > 0 && propsSessions.length === 0) {
        logger.log('🔒 Skip Props update to avoid clearing existing sessions:', {
          currentSessionsCount: currentSessions.length,
          propsSessionsCount: propsSessions.length
        })
        return // Return directly without executing update
      }

      logger.log('🔄 Update tool state from Props:', {
        availableToolsCount: props.availableTools?.length || 0,
        enabledSessionsCount: props.enabledSessions?.length || 0,
        source: 'props_watch'
      })
      chatService.value.updateAvailableTools(
        props.availableTools || [],
        props.enabledSessions || []
      )
    }
  }, 200) // Increase debounce time to 200ms
}

watch(
  () => props.availableTools,
  (newTools, oldTools) => {
    // Only update when there are real changes to avoid invalid updates
    if (JSON.stringify(newTools) !== JSON.stringify(oldTools)) {
      updateFromProps()
    }
  },
  { deep: true }
)

watch(
  () => props.enabledSessions,
  (newSessions, oldSessions) => {
    // Only update when there are real changes to avoid invalid updates
    if (JSON.stringify(newSessions) !== JSON.stringify(oldSessions)) {
      updateFromProps()
    }
  },
  { deep: true }
)

// Load saved configurations
const loadSavedConfigs = () => {
  try {
    // Use ConfigManager to load configurations, it has already properly handled default value merging and null value preservation
    const savedModelConfig = ConfigManager.loadModelConfig()
    const savedPromptsConfig = ConfigManager.loadPromptsConfig()
    const savedReActConfig = ConfigManager.loadReActConfig()
    const savedAdvancedConfig = ConfigManager.loadAdvancedConfig()

    // Check original localStorage data (for debugging)
    const rawStorageData = localStorage.getItem('mcp_model_config')
    if (rawStorageData) {
      logger.debug('Original localStorage data:', rawStorageData.substring(0, 100) + '...')
    }

    // Apply initial configuration overrides (if any)
    // Note: only apply non-empty initial configuration values to avoid overriding saved valid configurations
    const initialOverrides = props.initialConfig?.modelConfig || {}
    const filteredInitialConfig = Object.fromEntries(
      Object.entries(initialOverrides).filter(
        ([key, value]) => value !== null && value !== undefined && value !== ''
      )
    )

    modelConfig.value = {
      ...filteredInitialConfig, // Only apply non-empty initial configuration values
      ...savedModelConfig,
    }

    customPrompts.value = {
      ...savedPromptsConfig,
      ...props.initialConfig?.customPrompts
    }

    // ReAct configuration loading: prioritize local storage config, then props override, finally default value
    const savedReActEnabled = savedReActConfig.enabled
    const propsReActEnabled = props.initialConfig?.reactEnabled

    if (propsReActEnabled !== undefined) {
      // If props explicitly specifies reactEnabled, use props value
      reactEnabled.value = propsReActEnabled
    } else if (savedReActEnabled !== undefined) {
      // If local storage has configuration, use local storage value
      reactEnabled.value = savedReActEnabled
    } else {
      // If neither, use default value (enable ReAct)
      reactEnabled.value = true
    }

    logger.log('🔄 ReAct configuration loading result:', {
      savedReActEnabled,
      propsReActEnabled,
      finalReActEnabled: reactEnabled.value,
      source:
        propsReActEnabled !== undefined
          ? 'props'
          : savedReActEnabled !== undefined
          ? 'localStorage'
          : 'default'
    })

    // Load tool confirmation configuration
    if (savedAdvancedConfig) {
      toolConfirmationConfig.value = {
        ...toolConfirmationConfig.value,
        requireToolConfirmation:
          savedAdvancedConfig.requireToolConfirmation !== undefined
            ? savedAdvancedConfig.requireToolConfirmation
            : toolConfirmationConfig.value.requireToolConfirmation,
        toolConfirmationTimeout:
          savedAdvancedConfig.toolConfirmationTimeout ||
          toolConfirmationConfig.value.toolConfirmationTimeout,
        allowBatchToolConfirmation:
          savedAdvancedConfig.allowBatchToolConfirmation !== undefined
            ? savedAdvancedConfig.allowBatchToolConfirmation
            : toolConfirmationConfig.value.allowBatchToolConfirmation
      }

      logger.log('🔄 Tool confirmation configuration loading result:', toolConfirmationConfig.value)
    }

    // Mark configuration as loaded
    configLoaded.value = true

    // Immediately validate configuration once
    const validation = validateModelConfig()
    logger.log('🔍 Configuration validation result after loading:', validation)
  } catch (error) {
    logger.error('Failed to load saved configurations:', error)
    logger.log('Using default configuration')

    // Even if there's an error, mark as loaded to avoid showing prompts continuously
    configLoaded.value = true
  }
}

// Tool state monitoring timers
let toolsCheckInterval = null
let quickCheckInterval = null

// Start tool state monitoring
const startToolsMonitoring = () => {
  // Clear previous timers (if they exist)
  if (toolsCheckInterval) clearInterval(toolsCheckInterval)
  if (quickCheckInterval) clearInterval(quickCheckInterval)

  // Regularly check tool state and update ChatService
  toolsCheckInterval = setInterval(() => {
    // Only execute monitoring updates when no MCP configuration update is in progress
    if (!isProcessing.value) {
      updateChatService()
    }
  }, 5000) // Check every 5 seconds

  // Immediately update when MCP configuration changes
  let lastToolsCount = 0
  let lastSessionsCount = 0
  quickCheckInterval = setInterval(() => {
    const currentCount = mcpToolsCount.value
    const currentSessionsCount = mcpConfigEditorRef.value
      ? mcpConfigEditorRef.value.getConnectedServersCount
        ? mcpConfigEditorRef.value.getConnectedServersCount()
        : 0
      : 0

    if (
      currentCount !== lastToolsCount ||
      currentSessionsCount !== lastSessionsCount
    ) {
      // Avoid immediate interference after MCP configuration changes
      const timeSinceLastMcpChange = Date.now() - lastMcpConfigChangeTime
      if (timeSinceLastMcpChange > 5000) {
        // 5-second protection period
        logger.log('🔄 Detected tool or session state change:', {
          toolsCount: { old: lastToolsCount, new: currentCount },
          sessionsCount: { old: lastSessionsCount, new: currentSessionsCount }
        })
        lastToolsCount = currentCount
        lastSessionsCount = currentSessionsCount
        updateChatService()
      } else {
        // Still update count to avoid duplicate detection
        lastToolsCount = currentCount
        lastSessionsCount = currentSessionsCount
      }
    }
  }, 3000) // Reduce frequency to check every 3 seconds

  logger.log('🔧 Tool state monitoring started')
}

// Stop tool state monitoring
const stopToolsMonitoring = () => {
  if (toolsCheckInterval) {
    clearInterval(toolsCheckInterval)
    toolsCheckInterval = null
  }
  if (quickCheckInterval) {
    clearInterval(quickCheckInterval)
    quickCheckInterval = null
  }
  logger.log('🔧 Tool state monitoring stopped')
}

// Initialize MCP editor (preload)
const initializeMcpEditor = async () => {
  try {
    if (editorInitialized.value) {
      logger.log('🔧 MCP editor already initialized, skipping')
      return
    }

    // Enable preload editor rendering
    needsPreloadEditor.value = true
    await nextTick() // Wait for component creation

    // Wait for the preload editor to be fully initialized
    await new Promise(resolve => setTimeout(resolve, 200))

    if (preloadMcpConfigEditorRef.value) {
      logger.log('🔧 Preload MCP editor initialized, ready for automatic tool connection')
      editorInitialized.value = true
      
      // Keep the preload editor active until user opens the dialog
      // When dialog opens, the main editor will take over
    } else {
      logger.warn('⚠️ Preload MCP editor failed to initialize')
    }
  } catch (error) {
    logger.error('Failed to initialize MCP editor:', error)
  }
}

// Dynamically update ChatInput height
const updateChatInputHeight = (height) => {
  if (typeof document !== 'undefined') {
    document.documentElement.style.setProperty(
      '--chat-input-height',
      `${height}px`
    )
    logger.log(`🔧 ChatInput height updated: ${height}px`)
  }
}

// Observer for monitoring ChatInput height changes
const setupInputHeightObserver = () => {
  if (typeof ResizeObserver !== 'undefined') {
    const observer = new ResizeObserver((entries) => {
      for (let entry of entries) {
        if (entry.target.classList.contains('chat-input')) {
          const height = entry.contentRect.height
          updateChatInputHeight(height)
        }
      }
    })

    // Wait for ChatInput component to mount before starting observation
    nextTick(() => {
      const chatInputElement = document.querySelector('.chat-input')
      if (chatInputElement) {
        observer.observe(chatInputElement)
        // Initialize height
        updateChatInputHeight(chatInputElement.offsetHeight)
      }
    })

    return observer
  } else {
    // Fallback solution: periodically check height changes
    let lastHeight = 0
    const intervalId = setInterval(() => {
      const chatInputElement = document.querySelector('.chat-input')
      if (chatInputElement) {
        const currentHeight = chatInputElement.offsetHeight
        if (currentHeight !== lastHeight) {
          updateChatInputHeight(currentHeight)
          lastHeight = currentHeight
        }
      }
    }, 500) // Check every 500ms

    // Create an object to simulate ResizeObserver interface
    return {
      disconnect: () => clearInterval(intervalId)
    }
  }
}

// Lifecycle
onMounted(async () => {
  // First load saved configurations
  loadSavedConfigs()

  // Load MCP tool state (for badge display)
  loadMcpToolsCount()

  // Then initialize chat service
  initializeChatService()

  // Set up input height monitoring
  // Save observer reference for cleanup
  heightObserver.value = setupInputHeightObserver()

  // Initialize MCP configuration
  if (props.initialConfig?.mcpConfigJson) {
    mcpConfigJson.value = props.initialConfig.mcpConfigJson
  }

  // Listen to MCP state manager events - important: for syncing system tool reconnection state
  mcpStateManager.on('servers-reconnected', handleMcpServersReconnected)
  mcpStateManager.on('state-refreshed', handleMcpStateRefreshed)

  // Preload MCP editor and automatically connect tools
  setTimeout(async () => {
    await initializeMcpEditor()

    // Start tool state monitoring
    startToolsMonitoring()

    // Delay update ChatService once to ensure getting connected session information
    setTimeout(() => {
      const timeSinceLastMcpChange = Date.now() - lastMcpConfigChangeTime
      if (timeSinceLastMcpChange > 5000) {
        // Ensure not in MCP configuration change protection period
        logger.log('🔄 Delayed update ChatService to get session information')
        updateChatService()
      } else {
        logger.log('🔒 Delayed update skipped, in MCP configuration change protection period')
      }
    }, 3000) // Additional 3-second delay to ensure MCP auto-connection completes
  }, 1000) // Delay 1 second execution to ensure page is fully loaded

  // Scroll to bottom on initial load
  nextTick(() => {
    // Delay longer to ensure all components are rendered
    setTimeout(() => {
      scrollToBottom(true) // Force scroll to bottom
    }, 200)
  })
})

onUnmounted(() => {
  // Clean up chat service
  if (chatService.value) {
    chatService.value.destroy()
  }

  // Stop tool state monitoring
  stopToolsMonitoring()

  // Clean up height observer
  if (heightObserver.value) {
    heightObserver.value.disconnect()
    heightObserver.value = null
  }

  // Remove MCP state manager event listeners
  mcpStateManager.off('servers-reconnected', handleMcpServersReconnected)
  mcpStateManager.off('state-refreshed', handleMcpStateRefreshed)
})

// Handle MCP server reconnection event (from system tools)
const handleMcpServersReconnected = async (result) => {
  logger.log('🔔 [ChatInterface] Received system tool reconnection event:', result)
}

// Handle MCP state refresh event
const handleMcpStateRefreshed = (data) => {
  logger.log('🔔 [ChatInterface] Received state refresh event:', data)

  // Refresh tool count display
  if (data.enabledTools !== undefined) {
    mcpToolsCount.value = data.enabledTools
  }
}

// Monitor MCP configuration editor changes to ensure real-time badge updates
watch(
  mcpConfigEditorRef,
  (newRef) => {
    if (newRef) {
      // When MCP configuration editor is loaded, monitor its configuration changes
      logger.log('MCP configuration editor loaded, starting to monitor tool state changes')
    }
  },
  { immediate: true }
)

// Monitor preload MCP configuration editor initialization
watch(
  preloadMcpConfigEditorRef,
  (newRef) => {
    if (newRef) {
      logger.log('Preload MCP configuration editor loaded and ready')
      // Update tool count immediately when preload editor is ready
      if (newRef.getEnabledToolsCount) {
        mcpToolsCount.value = newRef.getEnabledToolsCount()
      }
    }
  },
  { immediate: true }
)

// Monitor dialog visibility to manage editor switching
watch(
  showMcpConfigDialog,
  (isVisible) => {
    if (!isVisible && mcpConfigEditorRef.value) {
      // When dialog closes, we can optionally keep the main editor or switch back to preload
      // For now, keep the main editor active since destroy-on-close="false"
      logger.log('MCP configuration dialog closed, main editor remains active')
    }
  }
)

// Record whether user manually scrolled the message area
const userScrolled = ref(false)
const lastScrollTop = ref(0)

// Check if user is at bottom position
const isUserAtBottom = () => {
  if (!messagesContainer.value) return true
  const { scrollTop, scrollHeight, clientHeight } = messagesContainer.value
  return scrollHeight - scrollTop - clientHeight < 100 // Increased to 100px tolerance, more lenient
}

// Monitor user scroll behavior
const handleScroll = () => {
  if (!messagesContainer.value) return

  const { scrollTop } = messagesContainer.value

  // Determine if user actively scrolled up (requires scroll difference greater than 30px)
  if (scrollTop < lastScrollTop.value - 30) {
    userScrolled.value = true
  }

  // If user scrolled to bottom, reset scroll state
  if (isUserAtBottom()) {
    userScrolled.value = false
  }

  lastScrollTop.value = scrollTop
}

// Smart scrolling: more aggressive auto-scroll strategy
const smartScrollToBottom = () => {
  // If user hasn't manually scrolled, or user is near bottom, auto-scroll
  if (!userScrolled.value || isUserAtBottom()) {
    nextTick(() => {
      scrollToBottom(true) // More aggressive scrolling
    })
  }
}

// Monitor message changes, force scroll
watch(
  messages,
  (newMessages, oldMessages) => {
    // Only consider scrolling when new messages are added
    if (newMessages.length > (oldMessages?.length || 0)) {
      // If new messages added, reset user scroll state and force scroll
      userScrolled.value = false

      // Delay scroll to ensure DOM is updated
      nextTick(() => {
        setTimeout(() => {
          scrollToBottom(true) // Force scroll
        }, 100)
      })
    }
  },
  { deep: true, immediate: true }
)

// Monitor processing state changes, scroll both when starting and finishing processing
watch(isProcessing, (newValue, oldValue) => {
  if (!oldValue && newValue) {
    // From idle to processing
    userScrolled.value = false
    nextTick(() => {
      scrollToBottom(true)
      // Delay scroll to ensure "processing..." UI is fully rendered
      setTimeout(() => scrollToBottom(true), 50)
      setTimeout(() => scrollToBottom(true), 200)
    })
  }

  if (oldValue && !newValue) {
    // From processing to processing complete
    // Delay scroll after processing complete to ensure last message content is fully rendered
    setTimeout(() => {
      scrollToBottom(true)
    }, 200)
    setTimeout(() => {
      scrollToBottom(true)
    }, 500) // Ensure scroll again
  }
})

// Monitor processing progress changes to ensure progress information is visible
watch(currentProgress, (newProgress) => {
  if (newProgress && isProcessing.value) {
    // Light scrolling, don't reset user scroll state unless user is at bottom
    if (!userScrolled.value || isUserAtBottom()) {
      setTimeout(() => scrollToBottom(true), 50)
    }
  }
})

// Expose methods
defineExpose({
  sendMessage: handleSendMessage,
  clearHistory: handleClearHistory,
  updateConfig: (config) => {
    if (config.modelConfig) handleModelConfigChange(config.modelConfig)
    if (config.customPrompts) handlePromptsChange(config.customPrompts)
    if (config.reactEnabled !== undefined)
      handleReActToggle(config.reactEnabled)
  },
  mcpConfigEditorRef, // Expose MCP configuration editor reference
  preloadMcpConfigEditorRef, // Expose preload MCP configuration editor reference
  getConnectedTools, // Expose method to get connected tools
  updateChatService, // Expose method to update chat service
  initializeMcpEditor // Expose MCP editor initialization method
})
</script>

<style scoped lang="scss">
.mcp-chat-interface {
  height: 100vh; /* Explicitly set to viewport height */
  width: 100%;
  background: linear-gradient(to bottom, #f8fafc, #f1f5f9); /* Soft gradient background */
  padding: 0;
  box-sizing: border-box;
  position: relative; /* Maintain relative positioning */
  overflow: hidden; /* Prevent page-level scrolling */
  display: flex;
  flex-direction: column; /* Use flex layout to automatically allocate space */

  .chat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    //background: linear-gradient(to right, var(--el-bg-color-page), var(--el-bg-color-page)); /* Changed to solid color background */
    border: 1px solid var(--el-border-color-light);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
    border-radius: 8px;
    margin-bottom: 8px;

    .header-left {
      display: flex;
      align-items: center;
      gap: 16px;

      .chat-title {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--el-text-color-primary);

        .el-icon {
          font-size: 20px;
          color: var(--el-color-primary);
        }
      }

      .status-indicators {
        display: flex;
        gap: 8px;

        .el-tag {
          border-radius: 6px;
          padding: 0 10px;
          height: 28px;
          line-height: 28px;
          transition: all 0.3s ease;

          &:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          }
        }
      }
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 12px;

      .el-badge {
        display: inline-flex;
      }

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

        &.is-circle {
          width: 32px;
          height: 32px;
          padding: 8px;
        }

        .el-icon {
          font-size: 16px;
        }
      }
    }
  }

  .chat-messages {
    flex: 1; /* Automatically occupy remaining space */
    overflow-y: auto;
    overflow-x: hidden; /* Prevent horizontal scrolling */
    padding: 40px 60px 20px 60px; /* Adjust padding for better coordination */
    display: flex; /* Add flex layout */
    flex-direction: column; /* Vertical arrangement */
    /* Ensure message area can scroll correctly */
    overflow-anchor: none;
    scroll-behavior: auto; /* Disable smooth scrolling, ensure immediate scrolling */
    box-sizing: border-box; /* Ensure padding is included in height calculation */
    min-height: 0; /* Allow flex children to shrink */
    background: transparent; /* Transparent background, show main container gradient */

    .empty-chat {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%; /* Fill entire message area */
      padding: 40px;

      .quick-actions {
        text-align: center;
        background: rgba(255, 255, 255, 0.7); /* Semi-transparent white background */
        backdrop-filter: blur(10px); /* Background blur effect */
        border-radius: 24px;
        padding: 40px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        max-width: 600px;
        transition: all 0.3s ease;

        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12),
            0 2px 6px rgba(0, 0, 0, 0.15);
        }

        h4 {
          margin: 16px 0 20px 0;
          color: #374151;
          font-size: 18px;
          font-weight: 600;
        }

        .el-button {
          margin: 6px 8px;
          border-radius: 12px;
          padding: 8px 16px;
          font-weight: 500;
          transition: all 0.3s ease;
          display: inline-flex;
          align-items: center;
          
          &:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          }
          
          // Button styles with tool icons
          &.el-button--primary {
            background: linear-gradient(135deg, var(--el-color-primary), var(--el-color-primary-light-3));
            border: none;
            color: white;
            
            .el-icon {
              animation: pulse 2s infinite;
            }
            
            &:hover {
              background: linear-gradient(135deg, var(--el-color-primary-dark-2), var(--el-color-primary));
              box-shadow: 0 6px 16px rgba(var(--el-color-primary-rgb), 0.3);
            }
          }
        }

        .config-hint {
          margin-top: 24px;
          text-align: left;
          background: rgba(251, 191, 36, 0.1);
          border: 1px solid rgba(251, 191, 36, 0.2);
          border-radius: 12px;
          padding: 16px;

          ol {
            margin: 8px 0;
            padding-left: 20px;
            color: #6b7280;
          }

          .el-button {
            margin-top: 12px;
          }
        }
      }
    }
  }

  .stats-popup {
    .stat-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid var(--el-border-color-lighter);

      &:last-child {
        border-bottom: none;
      }

      span {
        color: var(--el-text-color-regular);
      }

      strong {
        color: var(--el-text-color-primary);
      }
    }
  }

  // Reserved space for fixed positioned ChatInput component
  .chat-input-placeholder {
    flex-shrink: 0; /* Don't allow shrinking */
    height: var(--chat-input-height, 140px); /* Use CSS variable, default 140px */
    min-height: 120px; /* Minimum height */
    max-height: 220px; /* Maximum height, prevent input box from being too high */
    transition: height 0.3s ease; /* Smooth transition effect */
  }
}

// MCP configuration dialog content styles
.mcp-config-dialog-content {
  // Ensure content fills dialog
  height: 100%;
  overflow: hidden;

  // Editor style adjustments
  :deep(.mcp-enhanced-config-editor) {
    height: 100%;
    box-shadow: none; // Remove shadow, dialog already has one
    border-radius: 0;
    border: none;
  }
}

// Test mode dialog styles
.test-mode-content {
  h4 {
    margin: 16px 0 8px 0;
    color: var(--el-text-color-primary);
  }

  ul,
  ol {
    margin: 8px 0;
    padding-left: 20px;

    li {
      margin: 4px 0;
      line-height: 1.5;
    }
  }

  strong {
    color: var(--el-text-color-primary);
  }
}

// Scrollbar styles
.chat-messages::-webkit-scrollbar {
  width: 8px;
}

.chat-messages::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
  margin: 4px 0;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  transition: all 0.3s ease;

  &:hover {
    background: rgba(0, 0, 0, 0.3);
    transform: scaleY(1.1);
  }

  &:active {
    background: rgba(0, 0, 0, 0.4);
  }
}

// Responsive design
@media (max-width: 768px) {
  .mcp-chat-interface {
    background: linear-gradient(
      to bottom,
      #f9fafb,
      #f3f4f6
    ); /* Slightly adjust gradient for mobile */

    .chat-messages {
      padding: 20px 16px 20px 16px; /* Reduce left and right padding on mobile */

      .empty-chat {
        padding: 20px;

        .quick-actions {
          padding: 24px;
          border-radius: 16px;

          h4 {
            font-size: 16px;
          }

          .el-button {
            margin: 4px 6px;
            padding: 6px 12px;
            font-size: 14px;
          }

          .config-hint {
            padding: 12px;
            border-radius: 8px;

            ol {
              font-size: 14px;
            }
          }
        }
      }
    }

    .chat-input-placeholder {
      height: var(--chat-input-height, 160px); /* Mobile input box is usually taller */
      min-height: 140px;
      max-height: 240px;
    }
  }
}

// Tool icon pulse animation
@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.8;
  }
}
</style>