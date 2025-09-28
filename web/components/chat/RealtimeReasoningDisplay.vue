<template>
  <div class="realtime-reasoning-display">
    <div class="message-item">
      <!-- Message header -->
      <div class="message-header">
        <div class="message-avatar">
          <div class="avatar-container">
            <el-icon class="avatar-icon"><Cpu /></el-icon>
          </div>
        </div>
        <div class="message-info">
          <div class="sender-name">{{ $t('chat.realtimeReasoning.aiAssistant') }}</div>
          <div class="message-status">
            <div class="status-dot"></div>
            <span>{{ $t('chat.realtimeReasoning.thinking') }}</span>
          </div>
        </div>
      </div>

      <!-- Message content -->
      <div class="message-content">
        <!-- Reasoning process -->
        <div v-if="reasoningContent || reasoningSteps.length > 0" class="reasoning-section">
          <div class="section-header">
            <el-icon class="section-icon"><Cpu /></el-icon>
            <span class="section-title">{{ $t('chat.realtimeReasoning.thoughtProcess') }}</span>
            <div class="step-counter" v-if="reasoningSteps.length > 0">
              {{ reasoningSteps.length }} {{ $t('chat.realtimeReasoning.steps') }}
            </div>
          </div>
          <div class="reasoning-content">
            <!-- Progressive display of reasoning steps -->
            <div class="reasoning-steps">
              <div 
                v-for="(step, index) in reasoningSteps" 
                :key="step.id || index"
                class="reasoning-step-wrapper"
                :style="{ animationDelay: `${index * 0.1}s` }"
              >
                <div class="step-content" v-html="formatSingleReasoningStep(step.content)"></div>
              </div>
            </div>
            <!-- If there's additional reasoning content, also display it -->
            <div v-if="reasoningContent && !reasoningSteps.length" class="reasoning-text" v-html="formatReasoningContent(reasoningContent)"></div>
          </div>
        </div>

        <!-- Streaming output -->
        <div v-if="streamContent || streamChunks.length > 0" class="stream-section">
          <div class="section-header">
            <el-icon class="section-icon"><EditPen /></el-icon>
            <span class="section-title">{{ $t('chat.realtimeReasoning.generatingAnswer') }}</span>
            <div class="progress-indicator">
              <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
          <div class="stream-content">
            <!-- Progressive display of streaming content -->
            <div class="stream-text">
              <span v-if="streamChunks.length > 0" class="progressive-content">
                <span 
                  v-for="(chunk, index) in streamChunks" 
                  :key="chunk.id || index"
                  class="stream-chunk"
                  :style="{ animationDelay: `${index * 0.05}s` }"
                  v-html="formatStreamContent(chunk.content)"
                ></span>
              </span>
              <span v-else-if="streamContent" v-html="formatStreamContent(streamContent)"></span>
            </div>
            <span class="typing-cursor">|</span>
          </div>
        </div>

        <!-- Tool confirmation dialog -->
        <div v-if="pendingToolConfirmation && pendingTools.length > 0" class="tool-confirmation-section">
          <div class="section-header">
            <el-icon class="section-icon warning"><Tools /></el-icon>
            <span class="section-title">{{ $t('chat.realtimeReasoning.waitingForConfirmation') }}</span>
            <el-tag type="warning" size="small">{{ $t('chat.realtimeReasoning.needsConfirmation') }}</el-tag>
          </div>
          <div class="tool-confirmation-container">
            <ToolConfirmationDialog
              :pending-tools="pendingTools"
              :allow-batch-confirmation="allowBatchConfirmation"
              :timeout-duration="confirmationTimeout"
              @confirm="handleToolConfirm"
              @reject="handleToolReject"
              @timeout="handleToolTimeout"
            />
          </div>
        </div>

        <!-- Progress information -->
        <div v-if="progressMessage" class="progress-section">
          <div class="progress-content">
            <div class="spinner"></div>
            <span class="progress-text">{{ progressMessage }}</span>
          </div>
        </div>

        <!-- Default thinking state -->
        <div v-if="!reasoningContent && !streamContent && !progressMessage && reasoningSteps.length === 0 && streamChunks.length === 0" class="thinking-section">
          <div class="thinking-animation">
            <div class="thinking-icon">
              <el-icon><Cpu /></el-icon>
            </div>
            <div class="thinking-waves">
              <span class="wave"></span>
              <span class="wave"></span>
              <span class="wave"></span>
            </div>
          </div>
          <div class="thinking-text">
            <div class="main-text">{{ $t('chat.realtimeReasoning.deepThinking') }}</div>
            <div class="sub-text">
              {{ $t('chat.realtimeReasoning.analyzing') }}<span class="dots">{{ $t('chat.realtimeReasoning.dots') }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch, ref } from 'vue'
import { marked } from 'marked'
import { useI18n } from 'vue-i18n'
import {
  Cpu,
  EditPen,
  Tools
} from '@element-plus/icons-vue'
import ToolConfirmationDialog from '@/components/chat/ToolConfirmationDialog.vue'

// Internationalization
const { t } = useI18n()

// Configure marked
marked.setOptions({
  breaks: true,
  gfm: true,
})

// Props
const props = defineProps({
  reasoningContent: {
    type: String,
    default: ''
  },
  streamContent: {
    type: String,
    default: ''
  },
  progressMessage: {
    type: String,
    default: ''
  },
  isProcessing: {
    type: Boolean,
    default: true
  },
  // New: accumulated reasoning steps and streaming content arrays
  accumulatedReasoningSteps: {
    type: Array,
    default: () => []
  },
  accumulatedStreamChunks: {
    type: Array,
    default: () => []
  },
  // Tool confirmation related
  pendingToolConfirmation: {
    type: Boolean,
    default: false
  },
  pendingTools: {
    type: Array,
    default: () => []
  },
  allowBatchConfirmation: {
    type: Boolean,
    default: true
  },
  confirmationTimeout: {
    type: Number,
    default: 60
  }
})

// Emits
const emit = defineEmits(['tool-confirm', 'tool-reject', 'tool-timeout'])

// Computed property: handle accumulated reasoning steps
const reasoningSteps = computed(() => {
  if (props.accumulatedReasoningSteps && props.accumulatedReasoningSteps.length > 0) {
    return props.accumulatedReasoningSteps
  }
  
  // If no accumulated steps but there's reasoning content, try to parse into steps
  if (props.reasoningContent) {
    return parseReasoningIntoSteps(props.reasoningContent)
  }
  
  return []
})

// Computed property: handle accumulated streaming content chunks
const streamChunks = computed(() => {
  if (props.accumulatedStreamChunks && props.accumulatedStreamChunks.length > 0) {
    return props.accumulatedStreamChunks
  }
  
  // If no accumulated chunks but there's streaming content, create a single chunk
  if (props.streamContent) {
    return [{
      id: 'single_chunk',
      content: props.streamContent,
      timestamp: Date.now()
    }]
  }
  
  return []
})

// Parse reasoning content into steps array
const parseReasoningIntoSteps = (content) => {
  if (!content) return []
  
  // Split by line breaks, filter empty lines
  const lines = content.split('\n').filter(line => line.trim())
  
  return lines.map((line, index) => ({
    id: `parsed_step_${index}`,
    content: line.trim(),
    timestamp: Date.now() + index
  }))
}

// Format single reasoning step
const formatSingleReasoningStep = (content) => {
  if (!content) return ''
  
  try {
    let formatted = content
    
    // Check if contains reasoning markers
    const hasReasoningMarkers = /[🚀🔄🤔🛠️📊👀💭✅❌⚠️🔚🧠]/.test(content)
    
    if (hasReasoningMarkers) {
      // Format reasoning step markers
      formatted = formatted
        .replace(/🚀 \*\*(.*?)\*\*/g, '<div class="step-item step-start"><span class="step-emoji">🚀</span><span class="step-text">$1</span></div>')
        .replace(/🔄 \*\*(.*?)\*\*/g, '<div class="step-item step-iteration"><span class="step-emoji">🔄</span><span class="step-text">$1</span></div>')
        .replace(/🤔 \*\*(.*?)\*\*/g, '<div class="step-item step-thinking"><span class="step-emoji">🤔</span><span class="step-text">$1</span></div>')
        .replace(/🛠️ \*\*(.*?)\*\*/g, '<div class="step-item step-action"><span class="step-emoji">🛠️</span><span class="step-text">$1</span></div>')
        .replace(/📊 \*\*(.*?)\*\*/g, '<div class="step-item step-result"><span class="step-emoji">📊</span><span class="step-text">$1</span></div>')
        .replace(/👀 \*\*(.*?)\*\*/g, '<div class="step-item step-observation"><span class="step-emoji">👀</span><span class="step-text">$1</span></div>')
        .replace(/💭 \*\*(.*?)\*\*/g, '<div class="step-item step-reasoning"><span class="step-emoji">💭</span><span class="step-text">$1</span></div>')
        .replace(/✅ \*\*(.*?)\*\*/g, '<div class="step-item step-success"><span class="step-emoji">✅</span><span class="step-text">$1</span></div>')
        .replace(/❌ \*\*(.*?)\*\*/g, '<div class="step-item step-error"><span class="step-emoji">❌</span><span class="step-text">$1</span></div>')
        .replace(/⚠️ \*\*(.*?)\*\*/g, '<div class="step-item step-warning"><span class="step-emoji">⚠️</span><span class="step-text">$1</span></div>')
        .replace(/🔚 \*\*(.*?)\*\*/g, '<div class="step-item step-end"><span class="step-emoji">🔚</span><span class="step-text">$1</span></div>')
        .replace(/🧠 \*\*(.*?)\*\*/g, '<div class="step-item step-model"><span class="step-emoji">🧠</span><span class="step-text">$1</span></div>')
    } else {
      // Plain text, wrap as simple step
      formatted = `<div class="step-item step-plain"><span class="step-text">${formatted}</span></div>`
    }
    
    return formatted
  } catch (error) {
    console.error('Error formatting reasoning step:', error)
    return content
  }
}

// Format reasoning content (backward compatibility)
const formatReasoningContent = (content) => {
  if (!content) return ''
  
  try {
    let formatted = content
    
    // Concise reasoning step styles
    formatted = formatted
      .replace(/🚀 \*\*(.*?)\*\*/g, '<div class="step-item step-start"><span class="step-emoji">🚀</span><span class="step-text">$1</span></div>')
      .replace(/🔄 \*\*(.*?)\*\*/g, '<div class="step-item step-iteration"><span class="step-emoji">🔄</span><span class="step-text">$1</span></div>')
      .replace(/🤔 \*\*(.*?)\*\*/g, '<div class="step-item step-thinking"><span class="step-emoji">🤔</span><span class="step-text">$1</span></div>')
      .replace(/🛠️ \*\*(.*?)\*\*/g, '<div class="step-item step-action"><span class="step-emoji">🛠️</span><span class="step-text">$1</span></div>')
      .replace(/📊 \*\*(.*?)\*\*/g, '<div class="step-item step-result"><span class="step-emoji">📊</span><span class="step-text">$1</span></div>')
      .replace(/👀 \*\*(.*?)\*\*/g, '<div class="step-item step-observation"><span class="step-emoji">👀</span><span class="step-text">$1</span></div>')
      .replace(/💭 \*\*(.*?)\*\*/g, '<div class="step-item step-reasoning"><span class="step-emoji">💭</span><span class="step-text">$1</span></div>')
      .replace(/✅ \*\*(.*?)\*\*/g, '<div class="step-item step-success"><span class="step-emoji">✅</span><span class="step-text">$1</span></div>')
      .replace(/❌ \*\*(.*?)\*\*/g, '<div class="step-item step-error"><span class="step-emoji">❌</span><span class="step-text">$1</span></div>')
      .replace(/⚠️ \*\*(.*?)\*\*/g, '<div class="step-item step-warning"><span class="step-emoji">⚠️</span><span class="step-text">$1</span></div>')
      .replace(/🔚 \*\*(.*?)\*\*/g, '<div class="step-item step-end"><span class="step-emoji">🔚</span><span class="step-text">$1</span></div>')
      .replace(/🧠 \*\*(.*?)\*\*/g, '<div class="step-item step-model"><span class="step-emoji">🧠</span><span class="step-text">$1</span></div>')
    
    return formatted
  } catch (error) {
    console.error('Error formatting reasoning content:', error)
    return content.replace(/\n/g, '<br>')
  }
}

// Format streaming content
const formatStreamContent = (content) => {
  if (!content) return ''
  
  try {
    // For streaming content, we don't use marked as it might break progressive display
    // Simply handle line breaks and basic formatting
    return content
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
  } catch (error) {
    console.error('Error formatting streaming content:', error)
    return content.replace(/\n/g, '<br>')
  }
}

// Tool confirmation handling methods
const handleToolConfirm = (confirmedTools) => {
  emit('tool-confirm', confirmedTools)
}

const handleToolReject = () => {
  emit('tool-reject')
}

const handleToolTimeout = () => {
  emit('tool-timeout')
}

// Watch reasoning steps changes, ensure scrolling
watch(reasoningSteps, (newSteps) => {
  if (newSteps.length > 0) {
    // Delay scrolling to ensure new content is rendered
    setTimeout(() => {
      const container = document.querySelector('.reasoning-content')
      if (container) {
        container.scrollTop = container.scrollHeight
      }
    }, 100)
  }
}, { deep: true })

// Watch streaming content changes, ensure scrolling
watch(streamChunks, (newChunks) => {
  if (newChunks.length > 0) {
    // Delay scrolling to ensure new content is rendered
    setTimeout(() => {
      const container = document.querySelector('.stream-content')
      if (container) {
        container.scrollTop = container.scrollHeight
      }
    }, 50)
  }
}, { deep: true })
</script>

<style scoped lang="scss">
.realtime-reasoning-display {
  .message-item {
    background: #fff;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    margin-bottom: 16px;
    animation: fadeInUp 0.3s ease-out;
    
    .message-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
      
      .message-avatar {
        .avatar-container {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          animation: gentleRotate 4s linear infinite;
          
          .avatar-icon {
            color: #fff;
            font-size: 18px;
          }
        }
      }
      
      .message-info {
        .sender-name {
          font-size: 14px;
          font-weight: 500;
          color: #333;
          margin-bottom: 2px;
        }
        
        .message-status {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 12px;
          color: #666;
          
          .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #52c41a;
            animation: pulse 2s infinite;
          }
        }
      }
    }
    
    .message-content {
      .reasoning-section, .stream-section, .progress-section {
        background: #f8f9fa;
        border-radius: 8px;
        margin-bottom: 8px;
        animation: slideIn 0.3s ease-out;
      }
      
      .reasoning-section {
        border-left: 3px solid #667eea;
        
        .section-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 16px 8px 16px;
          
          .section-icon {
            color: #667eea;
            font-size: 14px;
            animation: gentlePulse 2s ease-in-out infinite;
          }
          
          .section-title {
            font-size: 13px;
            font-weight: 500;
            color: #667eea;
            flex: 1;
          }
          
          .step-counter {
            font-size: 11px;
            color: #999;
            background: #e0e7ff;
            padding: 2px 6px;
            border-radius: 10px;
          }
        }
        
        .reasoning-content {
          padding: 0 16px 12px 16px;
          max-height: 300px;
          overflow-y: auto;
          scroll-behavior: smooth;
          
          .reasoning-steps {
            .reasoning-step-wrapper {
              animation: progressiveSlideIn 0.4s ease-out forwards;
              opacity: 0;
              transform: translateY(10px);
              
              .step-content {
                :deep(.step-item) {
                  display: flex;
                  align-items: flex-start;
                  gap: 8px;
                  margin-bottom: 8px;
                  padding: 8px 12px;
                  background: #fff;
                  border-radius: 6px;
                  transition: all 0.2s ease;
                  
                  &:hover {
                    transform: translateX(2px);
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
                  }
                  
                  .step-emoji {
                    font-size: 14px;
                    min-width: 20px;
                  }
                  
                  .step-text {
                    flex: 1;
                    font-size: 13px;
                    line-height: 1.4;
                    color: #555;
                  }
                  
                  &.step-success .step-text {
                    color: #52c41a;
                  }
                  
                  &.step-error .step-text {
                    color: #ff4d4f;
                  }
                  
                  &.step-plain {
                    border-left: 2px solid #e0e0e0;
                    
                    .step-text {
                      color: #666;
                    }
                  }
                }
              }
            }
          }
          
          .reasoning-text {
            :deep(.step-item) {
              display: flex;
              align-items: flex-start;
              gap: 8px;
              margin-bottom: 8px;
              padding: 8px 12px;
              background: #fff;
              border-radius: 6px;
              transition: all 0.2s ease;
              animation: stepIn 0.3s ease-out;
              
              &:hover {
                transform: translateX(2px);
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
              }
              
              .step-emoji {
                font-size: 14px;
                min-width: 20px;
              }
              
              .step-text {
                flex: 1;
                font-size: 13px;
                line-height: 1.4;
                color: #555;
              }
              
              &.step-success .step-text {
                color: #52c41a;
              }
              
              &.step-error .step-text {
                color: #ff4d4f;
              }
            }
          }
        }
      }
      
      .stream-section {
        border-left: 3px solid #52c41a;
        
        .section-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 16px 8px 16px;
          
          .section-icon {
            color: #52c41a;
            font-size: 14px;
            animation: writeAnimation 1.5s ease-in-out infinite;
          }
          
          .section-title {
            font-size: 13px;
            font-weight: 500;
            color: #52c41a;
            flex: 1;
          }
          
          .progress-indicator {
            .typing-dots {
              display: flex;
              gap: 3px;
              
              span {
                width: 4px;
                height: 4px;
                border-radius: 50%;
                background: #52c41a;
                animation: typingDots 1.4s infinite ease-in-out both;
                
                &:nth-child(1) { animation-delay: -0.32s; }
                &:nth-child(2) { animation-delay: -0.16s; }
                &:nth-child(3) { animation-delay: 0s; }
              }
            }
          }
        }
        
        .stream-content {
          padding: 0 16px 12px 16px;
          max-height: 300px;
          overflow-y: auto;
          scroll-behavior: smooth;
          
          .stream-text {
            font-size: 14px;
            line-height: 1.5;
            color: #333;
            
            .progressive-content {
              .stream-chunk {
                animation: progressiveAppear 0.3s ease-out forwards;
                opacity: 0;
                
                :deep(strong) {
                  font-weight: 600;
                  color: #2c3e50;
                }
                
                :deep(em) {
                  font-style: italic;
                  color: #555;
                }
                
                :deep(code) {
                  background: #f1f1f1;
                  padding: 2px 4px;
                  border-radius: 3px;
                  font-size: 12px;
                  color: #d63384;
                  font-family: 'Monaco', 'Consolas', monospace;
                }
              }
            }
            
            :deep(h1), :deep(h2), :deep(h3) {
              margin: 12px 0 6px 0;
              color: #333;
              font-weight: 500;
            }
            
            :deep(p) {
              margin: 6px 0;
            }
            
            :deep(code) {
              background: #f1f1f1;
              padding: 2px 4px;
              border-radius: 3px;
              font-size: 12px;
              color: #d63384;
            }
            
            :deep(pre) {
              background: #f5f5f5;
              border: 1px solid #e0e0e0;
              border-radius: 4px;
              padding: 8px;
              margin: 8px 0;
              overflow-x: auto;
              font-size: 12px;
            }
          }
          
          .typing-cursor {
            display: inline-block;
            font-weight: 100;
            color: #52c41a;
            animation: blink 1s infinite;
            margin-left: 1px;
          }
        }
      }
      
      .tool-confirmation-section {
        border-left: 3px solid var(--el-color-warning);
        background: var(--el-color-warning-light-9);
        padding: 16px;
        border-radius: 8px;
        margin: 12px 0;
        
        .section-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 16px;
          
          .section-icon {
            font-size: 16px;
            
            &.warning {
              color: var(--el-color-warning);
            }
          }
          
          .section-title {
            font-weight: 600;
            color: var(--el-text-color-primary);
            font-size: 14px;
          }
        }
        
        .tool-confirmation-container {
          // Tool confirmation dialog container styles
          // Keep simple since internal component already has styles
        }
      }

      .progress-section {
        border-left: 3px solid #1890ff;
        padding: 12px 16px;
        
        .progress-content {
          display: flex;
          align-items: center;
          gap: 8px;
          
          .spinner {
            width: 16px;
            height: 16px;
            border: 2px solid #f0f0f0;
            border-top: 2px solid #1890ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
          }
          
          .progress-text {
            font-size: 13px;
            color: #666;
          }
        }
      }
      
      .thinking-section {
        padding: 24px 16px;
        text-align: center;
        
        .thinking-animation {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 12px;
          margin-bottom: 16px;
          
          .thinking-icon {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-size: 16px;
            animation: gentleFloat 3s ease-in-out infinite;
          }
          
          .thinking-waves {
            display: flex;
            gap: 4px;
            
            .wave {
              width: 4px;
              height: 16px;
              background: #667eea;
              border-radius: 2px;
              animation: wave 1.2s ease-in-out infinite;
              
              &:nth-child(1) { animation-delay: 0s; }
              &:nth-child(2) { animation-delay: 0.2s; }
              &:nth-child(3) { animation-delay: 0.4s; }
            }
          }
        }
        
        .thinking-text {
          .main-text {
            font-size: 15px;
            font-weight: 500;
            color: #333;
            margin-bottom: 4px;
          }
          
          .sub-text {
            font-size: 12px;
            color: #999;
            
            .dots {
              animation: typing 1.5s infinite;
            }
          }
        }
      }
    }
  }
}

// New animation definitions
@keyframes progressiveSlideIn {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes progressiveAppear {
  from {
    opacity: 0;
    transform: scale(0.98);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes typingDots {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1.2);
    opacity: 1;
  }
}

// Animation definitions
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-5px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes stepIn {
  from {
    opacity: 0;
    transform: scale(0.98);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes gentleRotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.1);
  }
}

@keyframes gentlePulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

@keyframes writeAnimation {
  0%, 100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(1px);
  }
  75% {
    transform: translateX(-1px);
  }
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes gentleFloat {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-2px);
  }
}

@keyframes wave {
  0%, 100% {
    transform: scaleY(1);
  }
  50% {
    transform: scaleY(1.5);
  }
}

@keyframes typing {
  0%, 33% {
    content: '.';
  }
  34%, 66% {
    content: '..';
  }
  67%, 100% {
    content: '...';
  }
}

// Mobile adaptation
@media (max-width: 768px) {
  .realtime-reasoning-display {
    .message-item {
      padding: 12px;
      
      .message-header {
        gap: 10px;
        margin-bottom: 10px;
        
        .message-avatar .avatar-container {
          width: 32px;
          height: 32px;
          
          .avatar-icon {
            font-size: 16px;
          }
        }
      }
      
      .message-content {
        .reasoning-section, .stream-section {
          .section-header {
            padding: 10px 12px 6px 12px;
          }
          
          .reasoning-content, .stream-content {
            padding: 0 12px 10px 12px;
            max-height: 200px;
          }
        }
        
        .thinking-section {
          padding: 20px 12px;
          
          .thinking-animation {
            gap: 10px;
            margin-bottom: 12px;
            
            .thinking-icon {
              width: 28px;
              height: 28px;
              font-size: 14px;
            }
          }
        }
      }
    }
  }
}
</style> 