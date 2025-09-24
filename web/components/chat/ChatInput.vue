<template>
  <div class="chat-input">
    <!-- Input area -->
    <div class="input-container">
      <!-- Toolbar -->
      <div class="input-toolbar">
        <div class="toolbar-left">
          <!-- File upload -->
          <el-upload
            :show-file-list="false"
            :before-upload="handleFileUpload"
            accept=".txt,.md,.json,.csv"
          >
            <el-button size="small" :icon="Paperclip" text :title="$t('chat.input.uploadFile')">
              {{ $t('chat.input.file') }}
            </el-button>
          </el-upload>
        </div>
        
        <div class="toolbar-right">
          
          <!-- Action buttons -->
          <div class="action-buttons">
            <!-- MCP configuration button -->
            <el-badge 
              :value="connectedToolsCount" 
              :hidden="connectedToolsCount === 0"
              :max="99"
              type="primary"
            >
              <el-button 
                :icon="Connection" 
                size="small"
                @click="openAssistantMcpConfig"
                :title="$t('chat.input.mcpConfig')"
                class="primary-action"
              >
                {{ $t('chat.input.mcpConfig') }}
              </el-button>
            </el-badge>
            
            <!-- Chat settings -->
            <ChatSettings
              :model-config="modelConfig"
              :custom-prompts="customPrompts"
              :react-enabled="reactEnabled"
              @model-config-change="handleModelConfigChange"
              @prompts-change="handlePromptsChange"
              @react-toggle="handleReactToggle"
              @config-change="handleSettingsConfigChange"
            />
            
            <!-- Clear conversation -->
            <el-button 
              :icon="Delete" 
              size="small"
              @click="handleClearHistory"
              :title="$t('chat.input.clearHistory')"
              text
              class="text-action danger"
            >
              {{ $t('common.clear') }}
            </el-button>
          </div>
          
          <!-- Input statistics -->
          <div class="input-stats">
            <span class="char-count">{{ inputMessage.length }} {{ $t('common.characters') }}</span>
            <span v-if="estimatedTokens > 0" class="token-count">
              ~{{ estimatedTokens }} tokens
            </span>
          </div>
          
          <!-- Send settings -->
          <el-dropdown @command="handleSendSetting">
            <el-button 
              size="small" 
              :icon="MoreFilled" 
              :title="$t('common.moreSettings')" 
              class="text-action"
            />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="enter-to-send">
                  <el-checkbox v-model="enterToSend">
                    {{ $t('chat.input.enterToSend') }}
                  </el-checkbox>
                </el-dropdown-item>
                <el-dropdown-item command="auto-clear">
                  <el-checkbox v-model="autoClear">
                    {{ $t('chat.input.autoClear') }}
                  </el-checkbox>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
      
      <!-- Main input area -->
      <div class="main-input">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="inputRows"
          :maxlength="maxLength"
          :placeholder="enterToSend ? $t('chat.input.placeholder').replace('Ctrl+Enter', 'Enter') : $t('chat.input.placeholder')"
          :disabled="disabled"
          resize="none"
          @keydown="handleKeyDown"
          @input="handleInput"
          @focus="handleFocus"
          @blur="handleBlur"
          ref="inputRef"
          class="message-input"
        />
        
        <!-- Send/Stop button -->
        <div class="send-button-container">
          <!-- Stop button - shown when processing -->
          <el-button
            v-if="disabled"
            type="danger"
            :icon="StopIcon"
            @click="stopProcessing"
            size="large"
            circle
            class="stop-button"
                :title="$t('chat.input.stopProcessing')"
          />
          <!-- Send button - shown when not processing -->
          <el-button
            v-else
            type="primary"
            :icon="sendButtonIcon"
            :disabled="!canSend"
            @click="sendMessage"
            size="large"
            circle
            class="send-button"
            :title="sendButtonTitle"
          />
        </div>
      </div>
      
      <!-- Input suggestions -->
      <div v-if="showSuggestions && suggestions.length > 0" class="suggestions">
        <div class="suggestions-header">
          <el-icon><Bell /></el-icon>
          <span>{{ $t('chat.input.suggestions') }}:</span>
        </div>
        <div class="suggestions-list">
          <el-tag
            v-for="(suggestion, index) in suggestions"
            :key="index"
            size="small"
            @click="applySuggestion(suggestion)"
            class="suggestion-item"
          >
            {{ suggestion }}
          </el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import {
  Loading,
  Paperclip,
  Bell,
  Promotion,
  Tools,
  Connection,
  Delete,
  MoreFilled,
  VideoPause
} from '@element-plus/icons-vue'
import $Bus from '@/utils/event-bus'
import ChatSettings from '@/components/chat/ChatSettings.vue'
import { DEFAULT_MODEL_CONFIG } from '@/services/config/modelConfigs.js'
import DebugLogger from '@/utils/DebugLogger.js'

// Internationalization
const { t } = useI18n()

// Create component-specific logger
const logger = DebugLogger.createLogger('ChatInput')

// Props
const props = defineProps({
  disabled: {
    type: Boolean,
    default: false
  },
  progressMessage: {
    type: String,
    default: ''
  },
  maxLength: {
    type: Number,
    default: 4000
  },
  placeholder: {
    type: String,
    default: 'Enter your message, Ctrl+Enter to send...'
  },
  suggestions: {
    type: Array,
    default: () => []
  },
  availableToolsCount: {
    type: Number,
    default: 0
  },
  connectedToolsCount: {
    type: Number,
    default: 0
  },
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
  'send-message',
  'stop-processing',
  'file-upload',
  'clear-history',
  'open-assistant-mcp-config',
  'open-mcp-config-center',
  'mcp-config-applied',
  'model-config-change',
  'prompts-change',
  'react-toggle',
  'settings-config-change'
])

// Reactive data
const inputMessage = ref('')
const inputRows = ref(3)
const inputRef = ref(null)
const isFocused = ref(false)
const showSuggestions = ref(false)

// Settings options
const enterToSend = ref(false)
const autoClear = ref(true)

// Computed properties
const canSend = computed(() => {
  return inputMessage.value.trim().length > 0 && !props.disabled
})

const sendButtonIcon = computed(() => {
  return Promotion
})

const StopIcon = VideoPause

const sendButtonTitle = computed(() => {
  if (!canSend.value) return t('chat.input.pleaseEnterMessage')
  return enterToSend.value ? t('chat.input.enterToSend') : t('chat.input.ctrlEnterToSend')
})

const estimatedTokens = computed(() => {
  if (!inputMessage.value) return 0
  // Simplified token estimation
  const chineseChars = (inputMessage.value.match(/[\u4e00-\u9fff]/g) || []).length
  const otherChars = inputMessage.value.length - chineseChars
  return Math.ceil(chineseChars / 1.5 + otherChars / 4)
})

// Methods
const sendMessage = () => {
  if (!canSend.value) return
  
  const message = inputMessage.value.trim()
  emit('send-message', message)
  
  if (autoClear.value) {
    inputMessage.value = ''
    updateInputRows()
  }
  
  // Focus back to input
  nextTick(() => {
    inputRef.value?.focus()
  })
}

const stopProcessing = () => {
  emit('stop-processing')
}

const handleKeyDown = (event) => {
  // Ctrl+Enter or Cmd+Enter to send
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
    event.preventDefault()
    sendMessage()
  }
  
  // Enter to send directly (if enabled)
  if (enterToSend.value && event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
  
  // Shift+Enter for new line
  if (event.shiftKey && event.key === 'Enter') {
    // Allow default behavior
  }
  
  // Esc to clear input
  if (event.key === 'Escape') {
    inputMessage.value = ''
    updateInputRows()
  }
}

const handleInput = () => {
  updateInputRows()
  updateSuggestions()
}

const handleFocus = () => {
  isFocused.value = true
  showSuggestions.value = true
}

const handleBlur = () => {
  isFocused.value = false
  // Delay hiding suggestions to allow clicking suggestion items
  setTimeout(() => {
    showSuggestions.value = false
  }, 200)
}

const updateInputRows = () => {
  const lines = inputMessage.value.split('\n').length
  inputRows.value = Math.min(Math.max(lines, 3), 8)
}

const updateSuggestions = () => {
  // Here we can dynamically update suggestions based on input content
  // Currently using static suggestions passed as props
}

const handleSendSetting = (command) => {
  // Other settings are handled automatically through v-model
}

const handleFileUpload = (file) => {
  // Check file size (max 10MB)
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error(t('chat.fileUpload.maxSize'))
    return false
  }
  
  // Read file content
  const reader = new FileReader()
  reader.onload = (e) => {
    const content = e.target.result
    inputMessage.value += `\n\n${t('chat.input.filePrefix', { fileName: file.name })}\n${content}`
    updateInputRows()
  }
  
  reader.onerror = () => {
    ElMessage.error(t('chat.input.fileReadFailed'))
  }
  
  reader.readAsText(file)
  
  emit('file-upload', file)
  return false // Prevent automatic upload
}

const applySuggestion = (suggestion) => {
  inputMessage.value = suggestion
  showSuggestions.value = false
  nextTick(() => {
    inputRef.value?.focus()
  })
}

// Configuration related methods
const openAssistantMcpConfig = () => {
  // Open assistant MCP configuration dialog
  emit('open-assistant-mcp-config')
}

const handleClearHistory = () => {
  // Directly trigger event, let parent component handle confirmation logic
  // Avoid duplicate confirmation dialogs
  emit('clear-history')
}

// Configuration change handlers
const handleModelConfigChange = (config) => {
  emit('model-config-change', config)
}

const handlePromptsChange = (prompts) => {
  emit('prompts-change', prompts)
}

const handleReactToggle = (enabled) => {
  emit('react-toggle', enabled)
}

const handleSettingsConfigChange = (data) => {
  emit('settings-config-change', data)
}

// Mitt event handling
const handleMcpConfigApply = (configData) => {
  ElMessage.success(`${t('chat.messages.mcpConfigAppliedSuccess')}: ${configData.serverName}`)
  // Here we can add specific configuration application logic
  // For example, notify parent component to update configuration
  emit('mcp-config-applied', configData)
}

// Lifecycle
onMounted(() => {
  // Auto focus on input
  nextTick(() => {
    inputRef.value?.focus()
  })
  
  // Listen for MCP configuration application events
  $Bus.on('applyMcpConfigToAssistant', handleMcpConfigApply)
})

onUnmounted(() => {
  // Remove event listeners
  $Bus.off('applyMcpConfigToAssistant', handleMcpConfigApply)
})

// Watch disabled state changes
watch(() => props.disabled, (disabled) => {
  if (!disabled) {
    nextTick(() => {
      inputRef.value?.focus()
    })
  }
})
</script>

<style scoped lang="scss">
.chat-input {
  position: fixed; /* Fixed positioning at bottom of page */
  bottom: 0;
  left: 0;
  right: 0;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  background: transparent;
  padding: 12px 24px 16px; /* Reduced vertical padding */
  backdrop-filter: blur(10px);
  z-index: 10; /* Ensure input is on top layer */
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(to bottom, rgba(248, 250, 252, 0.95), rgba(241, 245, 249, 0.98));
    z-index: -1;
  }

  .input-container {
    max-width: 1000px;
    margin: 0 auto;
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(20px);
    border-radius: 24px;
    border: 1px solid rgba(255, 255, 255, 0.3);
    box-shadow: 
      0 0 0 1px rgba(0, 0, 0, 0.02),
      0 4px 12px rgba(0, 0, 0, 0.08),
      0 20px 40px rgba(0, 0, 0, 0.06);
    padding: 16px; /* 减少内部padding */
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

    &:focus-within {
      transform: translateY(-2px);
      background: rgba(255, 255, 255, 0.95);
      border-color: rgba(255, 255, 255, 0.5);
      box-shadow: 
        0 0 0 1px rgba(0, 0, 0, 0.03),
        0 8px 20px rgba(0, 0, 0, 0.12),
        0 32px 64px rgba(0, 0, 0, 0.08);
    }

    .input-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px; /* Reduced bottom margin for toolbar */
      padding: 0 4px;
      
      .toolbar-left,
      .toolbar-right {
        display: flex;
        align-items: center;
        gap: 8px;

        .el-button {
          height: 36px;
          min-width: 36px;
          padding: 0 14px;
          border-radius: 12px;
          border: 1px solid transparent;
          background: rgba(0, 0, 0, 0.04);
          color: rgba(0, 0, 0, 0.7);
          font-size: 13px;
          font-weight: 500;
          transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
          
          &:hover {
            background: rgba(0, 0, 0, 0.06);
            border-color: rgba(0, 0, 0, 0.12);
            color: var(--el-color-primary);
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          }

          &:active {
            transform: translateY(0);
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
          }

          .el-icon {
            font-size: 15px;
            transition: transform 0.2s ease;
          }
          
          &:hover .el-icon {
            transform: scale(1.05);
          }

          // Disabled state
          &:disabled,
          &.is-disabled {
            background: rgba(0, 0, 0, 0.04) !important;
            border-color: rgba(0, 0, 0, 0.06) !important;
            color: rgba(0, 0, 0, 0.3) !important;
            cursor: not-allowed;
            transform: none !important;
            box-shadow: none !important;

            .el-icon {
              transform: none !important;
            }
          }
        }
      }

      .action-buttons {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 4px 6px;
        border-radius: 16px;
        background: rgba(0, 0, 0, 0.04);
        border: 1px solid rgba(0, 0, 0, 0.08);

        .el-button {
          height: 36px;
          min-width: 36px;
          border-radius: 12px;
          font-size: 13px;
          font-weight: 500;
          padding: 0 14px;
          transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
          border: 1px solid transparent;
          position: relative;
          overflow: hidden;

          // 统一的基础样式
          &::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: currentColor;
            opacity: 0;
            transition: opacity 0.25s ease;
          }

          &.primary-action {
            background: var(--el-color-primary-light-9);
            border-color: var(--el-color-primary-light-7);
            color: var(--el-color-primary);
            box-shadow: 0 1px 3px rgba(var(--el-color-primary-rgb), 0.1);

            &:hover {
              background: var(--el-color-primary-light-8);
              border-color: var(--el-color-primary-light-5);
              transform: translateY(-1px);
              box-shadow: 0 4px 12px rgba(var(--el-color-primary-rgb), 0.15);

              &::before {
                opacity: 0.05;
              }
            }

            &:active {
              transform: translateY(0);
              box-shadow: 0 2px 6px rgba(var(--el-color-primary-rgb), 0.1);
            }
          }

          &.text-action {
            background: transparent;
            border-color: transparent;
            color: rgba(0, 0, 0, 0.6);

            &:hover {
              background: rgba(var(--el-color-primary-rgb), 0.08);
              border-color: rgba(var(--el-color-primary-rgb), 0.15);
              color: var(--el-color-primary);
              transform: translateY(-1px);
              box-shadow: 0 2px 6px rgba(var(--el-color-primary-rgb), 0.1);
            }

            &:active {
              transform: translateY(0);
              box-shadow: none;
            }

            &.danger {
              &:hover {
                background: rgba(var(--el-color-danger-rgb), 0.08);
                border-color: rgba(var(--el-color-danger-rgb), 0.15);
                color: var(--el-color-danger);
                box-shadow: 0 2px 6px rgba(var(--el-color-danger-rgb), 0.1);
              }
            }
          }

          .el-icon {
            font-size: 15px;
            transition: transform 0.2s ease;
          }

          // Icon animation
          &:hover .el-icon {
            transform: scale(1.05);
          }

          // Disabled state
          &:disabled,
          &.is-disabled {
            background: rgba(0, 0, 0, 0.04) !important;
            border-color: rgba(0, 0, 0, 0.06) !important;
            color: rgba(0, 0, 0, 0.3) !important;
            cursor: not-allowed;
            transform: none !important;
            box-shadow: none !important;

            &::before {
              opacity: 0 !important;
            }

            .el-icon {
              transform: none !important;
            }
          }
        }

        // Button styles in ChatSettings component
        :deep(.settings-button) {
          height: 36px;
          min-width: 36px;
          border-radius: 12px;
          font-size: 13px;
          font-weight: 500;
          padding: 0 14px;
          transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
          border: 1px solid rgba(0, 0, 0, 0.08);
          background: rgba(0, 0, 0, 0.04);
          color: rgba(0, 0, 0, 0.7);

          &:hover {
            background: rgba(0, 0, 0, 0.06);
            border-color: rgba(0, 0, 0, 0.12);
            color: var(--el-color-primary);
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          }

          &:active {
            transform: translateY(0);
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
          }

          .el-icon {
            font-size: 15px;
            transition: transform 0.2s ease;
          }
          
          &:hover .el-icon {
            transform: scale(1.05);
          }

          // Disabled state
          &:disabled,
          &.is-disabled {
            background: rgba(0, 0, 0, 0.04) !important;
            border-color: rgba(0, 0, 0, 0.06) !important;
            color: rgba(0, 0, 0, 0.3) !important;
            cursor: not-allowed;
            transform: none !important;
            box-shadow: none !important;

            .el-icon {
              transform: none !important;
            }
          }
        }

        .el-badge {
          :deep(.el-badge__content) {
            top: 4px;
            right: 4px;
            height: 18px;
            min-width: 18px;
            line-height: 18px;
            padding: 0 6px;
            font-size: 11px;
            font-weight: 600;
            border-radius: 9px;
            border: 2px solid #fff;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
          }
        }
      }
      
      .input-stats {
        display: inline-flex;
        align-items: center;
        height: 32px;
        padding: 0 14px;
        border-radius: 12px;
        background: rgba(0, 0, 0, 0.04);
        border: 1px solid rgba(0, 0, 0, 0.06);
        font-size: 12px;
        font-weight: 500;
        color: rgba(0, 0, 0, 0.5);
        gap: 8px;
        transition: all 0.2s ease;
        
        &:hover {
          background: rgba(0, 0, 0, 0.06);
          border-color: rgba(0, 0, 0, 0.1);
        }
        
        .char-count {
          &.warning {
            color: var(--el-color-warning);
            font-weight: 600;
          }
          
          &.danger {
            color: var(--el-color-danger);
            font-weight: 600;
          }
        }
        
        .token-count {
          &::before {
            content: '•';
            margin: 0 6px;
            opacity: 0.4;
            font-size: 10px;
          }
        }
      }
    }
    
    .main-input {
      position: relative;
      display: flex;
      gap: 16px;
      align-items: flex-end;
      
      .message-input {
        flex: 1;
        
        :deep(.el-textarea__inner) {
          min-height: 24px;
          max-height: 200px;
          padding: 12px 16px;
          font-size: 15px;
          line-height: 1.6;
          border: none;
          background: rgba(0, 0, 0, 0.02);
          border-radius: 16px;
          resize: none;
          transition: all 0.3s ease;
          
          &::placeholder {
            color: rgba(0, 0, 0, 0.3);
          }
          
          &:hover {
            background: rgba(0, 0, 0, 0.03);
          }
          
          &:focus {
            background: rgba(0, 0, 0, 0.04);
            box-shadow: none;
          }
        }
      }
      
      .send-button-container {
        .send-button {
          width: 44px;
          height: 44px;
          border-radius: 14px;
          padding: 0;
          transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
          background: var(--el-color-primary);
          border: none;
          
          &:hover:not(:disabled) {
            transform: scale(1.05) translateY(-1px);
            box-shadow: 
              0 4px 12px rgba(var(--el-color-primary-rgb), 0.3),
              0 0 0 1px rgba(var(--el-color-primary-rgb), 0.1);
          }
          
          &:active:not(:disabled) {
            transform: scale(0.96);
          }

          &:disabled {
            background: rgba(0, 0, 0, 0.1);
            opacity: 0.8;
          }

          :deep(.el-icon) {
            font-size: 18px;
            color: #fff;
          }
        }
        
        .stop-button {
          width: 44px;
          height: 44px;
          border-radius: 14px;
          padding: 0;
          transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
          background: var(--el-color-danger);
          border: none;
          
          &:hover {
            transform: scale(1.05) translateY(-1px);
            box-shadow: 
              0 4px 12px rgba(var(--el-color-danger-rgb), 0.3),
              0 0 0 1px rgba(var(--el-color-danger-rgb), 0.1);
          }
          
          &:active {
            transform: scale(0.96);
          }

          :deep(.el-icon) {
            font-size: 18px;
            color: #fff;
          }
        }
      }
    }
    
    .suggestions {
      margin-top: 16px;
      padding: 12px 16px;
      background: rgba(0, 0, 0, 0.02);
      border-radius: 12px;
      
      .suggestions-header {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 10px;
        font-size: 13px;
        color: rgba(0, 0, 0, 0.4);

        .el-icon {
          font-size: 14px;
          color: var(--el-color-primary);
        }
      }
      
      .suggestions-list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        
        .suggestion-item {
          height: 32px;
          padding: 0 14px;
          border-radius: 12px;
          font-size: 13px;
          font-weight: 500;
          border: 1px solid rgba(0, 0, 0, 0.08);
          background: rgba(255, 255, 255, 0.9);
          color: rgba(0, 0, 0, 0.6);
          cursor: pointer;
          transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
          display: inline-flex;
          align-items: center;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
          
          &:hover {
            background: var(--el-color-primary-light-9);
            border-color: var(--el-color-primary-light-5);
            color: var(--el-color-primary);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(var(--el-color-primary-rgb), 0.15);
          }

          &:active {
            transform: translateY(-1px);
            box-shadow: 0 2px 6px rgba(var(--el-color-primary-rgb), 0.1);
          }
        }
      }
    }
  }
}

// Mobile adaptation
@media (max-width: 768px) {
  .chat-input {
    padding: 12px 16px 16px;

    .input-container {
      border-radius: 20px;
      padding: 16px;
      
      .input-toolbar {
        flex-direction: column;
        align-items: stretch;
        gap: 12px;
        margin-bottom: 12px;
        
        .toolbar-left,
        .toolbar-right {
          justify-content: space-between;
        }

        .action-buttons {
          order: 1;
          justify-content: center;
          padding: 8px 12px;

          .el-button {
            height: 32px;
            min-width: 32px;
            font-size: 12px;
            padding: 0 10px;
            border-radius: 10px;
            
            .el-icon {
              font-size: 14px;
            }
          }
          
          // Mobile ChatSettings button styles
          :deep(.settings-button) {
            height: 32px;
            min-width: 32px;
            font-size: 12px;
            padding: 0 10px;
            border-radius: 10px;
            
            .el-icon {
              font-size: 14px;
            }
          }
        }

        .input-stats {
          order: 2;
          justify-content: center;
        }
      }
      
      .main-input {
        gap: 12px;
        
        .message-input {
          :deep(.el-textarea__inner) {
            font-size: 16px;
            padding: 10px 14px;
          }
        }
        
        .send-button-container {
          .send-button {
            width: 40px;
            height: 40px;
            border-radius: 12px;
          }
          
          .stop-button {
            width: 40px;
            height: 40px;
            border-radius: 12px;
          }
        }
      }

      .suggestions {
        padding: 10px 12px;
        margin-top: 12px;
        
        .suggestions-list {
          gap: 6px;
          
          .suggestion-item {
            height: 30px;
            padding: 0 12px;
            font-size: 12px;
            border-radius: 10px;
            
            &:hover {
              transform: translateY(-1px);
            }
          }
        }
      }
    }
  }
}
</style> 