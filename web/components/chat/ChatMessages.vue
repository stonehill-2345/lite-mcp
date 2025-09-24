<template>
  <div class="messages-list">
    <div 
      v-for="(message, index) in messages" 
      :key="message.id"
      class="message-item"
      :class="[message.role, { 'has-error': message.error }]"
    >
      <!-- Message header -->
      <div class="message-header">
        <div class="message-avatar">
          <el-avatar 
            v-if="message.role === 'user'"
            :size="32"
            :icon="UserFilled"
            style="background-color: var(--el-color-primary);"
          />
          <el-avatar 
            v-else
            :size="32"
            :icon="Avatar"
            style="background-color: var(--el-color-success);"
          />
        </div>
        
        <div class="message-meta">
          <span class="role-label">
            {{ message.role === 'user' ? t('chat.messages.user') : t('chat.messages.assistant') }}
          </span>
          <span class="message-time">
            {{ formatTime(message.timestamp) }}
          </span>
        </div>
      </div>
      
      <!-- Message content -->
      <div class="message-content">
        <!-- User message -->
        <div v-if="message.role === 'user'" class="user-message">
          {{ message.content }}
        </div>
        
        <!-- Assistant message -->
        <div v-else class="assistant-message">
          <!-- Error message -->
          <div v-if="message.error" class="error-message">
            <el-icon><WarnTriangleFilled /></el-icon>
            {{ message.content }}
          </div>
          
          <!-- User stopped message -->
          <div v-else-if="message.stopped" class="stopped-message">
            <el-icon><VideoPause /></el-icon>
            {{ message.content }}
          </div>
          
          <!-- Normal message -->
          <div v-else class="normal-message">
            <!-- Reasoning status prompt (if there's reasoning process) -->
            <div 
              v-if="message.reasoning || message.reasoningContent || (message.toolCalls && message.toolCalls.length > 0)" 
              class="thinking-status"
            >
              <div class="thinking-header" @click="toggleReasoningDetails(message.id)">
                <div class="thinking-info">
                  <el-icon 
                    class="thinking-icon" 
                    :class="{ 'rotating': props.isProcessing && isLastAssistantMessage(message) }"
                  >
                    <Cpu />
                  </el-icon>
                  <span class="thinking-text">
                    {{ getThinkingStatusText(message) }}
                  </span>
                  <el-tag 
                    size="small" 
                    :type="props.isProcessing && isLastAssistantMessage(message) ? 'warning' : 'success'"
                  >
                    {{ getThinkingDuration(message) }}
                  </el-tag>
                </div>
                <el-icon 
                  class="expand-icon" 
                  :class="{ 'expanded': isReasoningExpanded(message.id) }"
                >
                  <ArrowRight />
                </el-icon>
              </div>
              
              <!-- Reasoning details (expandable) -->
              <el-collapse 
                v-model="expandedReasoningItems[message.id]" 
                class="reasoning-collapse"
              >
                <el-collapse-item name="reasoning" class="reasoning-collapse-item">
                  <!-- Reasoning process content -->
                  <div v-if="message.reasoningContent || message.reasoning?.content || message.reasoning?.trace" class="reasoning-section">
                    <div class="section-header">
                      <el-icon><Cpu /></el-icon>
                      <span>{{ t('chat.messages.reasoningProcess') }}</span>
                      <el-tag v-if="message.reasoning?.iterations" size="small" type="info">
                        {{ message.reasoning.iterations }} {{ t('chat.messages.iterations') }}
                      </el-tag>
                    </div>
                    
                    <!-- Detailed reasoning trace -->
                    <div v-if="message.reasoning?.trace && message.reasoning.trace.length > 0" class="reasoning-trace">
                      <div class="trace-header">
                        <el-icon><List /></el-icon>
                        <span>{{ t('chat.messages.detailedTrace') }}</span>
                        <el-tag size="small" type="info">{{ message.reasoning.trace.length }} {{ t('chat.messages.steps') }}</el-tag>
                      </div>
                      
                      <div class="trace-timeline">
                        <div 
                          v-for="(step, stepIndex) in message.reasoning.trace"
                          :key="stepIndex"
                          class="trace-step"
                          :class="step.type"
                        >
                          <div class="step-marker">
                            <el-icon class="step-icon">
                              <component :is="getStepIcon(step.type)" />
                            </el-icon>
                            <span class="step-number">{{ stepIndex + 1 }}</span>
                          </div>
                          
                          <div class="step-content">
                            <div class="step-header">
                              <span class="step-type">{{ getStepTypeName(step.type) }}</span>
                              <span class="step-time">{{ formatStepTime(step.timestamp) }}</span>
                            </div>
                            
                            <div class="step-body">
                              <!-- Different step types display different content -->
                              <div v-if="step.type === 'action_plan'" class="action-plan-content">
                                <div v-if="typeof step.content === 'object'">
                                  <div class="plan-detail">
                                    <span class="detail-label">{{ t('chat.messages.actionType') }}</span>
                                    <el-tag size="small" :type="getActionTypeColor(step.content.type)">
                                      {{ step.content.type }}
                                    </el-tag>
                                  </div>
                                  <div v-if="step.content.toolName" class="plan-detail">
                                    <span class="detail-label">{{ t('chat.messages.toolName') }}</span>
                                    <code>{{ step.content.toolName }}</code>
                                  </div>
                                  <div v-if="step.content.parameters" class="plan-detail">
                                    <span class="detail-label">{{ t('chat.messages.parameters') }}</span>
                                    <pre class="json-content">{{ JSON.stringify(step.content.parameters, null, 2) }}</pre>
                                  </div>
                                  <div v-if="step.content.sessionId" class="plan-detail">
                                    <span class="detail-label">{{ t('chat.messages.sessionId') }}</span>
                                    <code>{{ step.content.sessionId }}</code>
                                  </div>
                                  <div v-if="step.content.reasoning" class="plan-detail">
                                    <span class="detail-label">{{ t('chat.messages.reasoningBasis') }}</span>
                                    <p class="reasoning-text">{{ step.content.reasoning }}</p>
                                  </div>
                                </div>
                                <pre v-else class="text-content">{{ step.content }}</pre>
                              </div>
                              
                              <div v-else-if="step.type === 'action_result'" class="action-result-content">
                                <div v-if="typeof step.content === 'object'">
                                  <div class="result-status">
                                    <el-tag :type="step.content.success ? 'success' : 'danger'" size="small">
                                      {{ step.content.success ? t('chat.messages.success') : t('chat.messages.failure') }}
                                    </el-tag>
                                    <span v-if="step.content.duration" class="duration">
                                      {{ t('chat.messages.duration', { duration: step.content.duration }) }}
                                    </span>
                                  </div>
                                  <div v-if="step.content.toolName" class="result-detail">
                                    <span class="detail-label">{{ t('chat.messages.tool') }}</span>
                                    <code>{{ step.content.toolName }}</code>
                                  </div>
                                  <div v-if="step.content.result" class="result-detail">
                                    <span class="detail-label">{{ t('chat.messages.result') }}</span>
                                    <pre class="json-content">{{ JSON.stringify(step.content.result, null, 2) }}</pre>
                                  </div>
                                  <div v-if="step.content.error" class="result-detail">
                                    <span class="detail-label">{{ t('chat.messages.error') }}</span>
                                    <div class="error-message">{{ step.content.error }}</div>
                                  </div>
                                </div>
                                <pre v-else class="text-content">{{ step.content }}</pre>
                              </div>
                              
                              <div v-else-if="step.type === 'thought'" class="thought-content">
                                <div class="thought-text">{{ step.content }}</div>
                              </div>
                              
                              <div v-else-if="step.type === 'observation'" class="observation-content">
                                <div class="observation-text">{{ step.content }}</div>
                              </div>
                              
                              <div v-else-if="step.type === 'reasoning'" class="reasoning-content">
                                <div class="reasoning-text">{{ step.content }}</div>
                              </div>
                              
                              <div v-else class="generic-content">
                                <pre class="text-content">{{ typeof step.content === 'object' ? JSON.stringify(step.content, null, 2) : step.content }}</pre>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <!-- Reasoning content summary -->
                    <div v-if="message.reasoningContent || message.reasoning?.content" class="reasoning-summary-section">
                      <div class="summary-header">
                        <el-icon><Document /></el-icon>
                        <span>{{ t('chat.messages.reasoningSummary') }}</span>
                      </div>
                      <div class="reasoning-content">
                        <pre class="reasoning-text">{{ message.reasoningContent || message.reasoning?.content }}</pre>
                      </div>
                    </div>
                    
                    <!-- Temporary debug information (force display) -->
                    <div v-if="message.reasoning" class="debug-info">
                      <el-collapse>
                        <el-collapse-item :title="'🔍 ' + t('chat.messages.debugInfo')" name="debug">
                          <div class="debug-content">
                            <div class="debug-section">
                              <h5>1. {{ t('chat.messages.reasoningStructure') }}</h5>
                              <pre class="debug-json">{{ JSON.stringify(message.reasoning, null, 2) }}</pre>
                            </div>
                            <div class="debug-section">
                              <h5>2. {{ t('chat.messages.traceCheck') }}</h5>
                              <pre class="debug-text">
{{ t('chat.messages.hasTrace') }}{{ message.reasoning.trace ? t('chat.messages.has') : t('chat.messages.notHas') }}
{{ t('chat.messages.traceIsArray') }}{{ Array.isArray(message.reasoning.trace) ? t('chat.messages.is') : t('chat.messages.notIs') }}
{{ t('chat.messages.traceLength') }}{{ message.reasoning.trace?.length || 0 }}
{{ t('chat.messages.traceContent') }}{{ JSON.stringify(message.reasoning.trace, null, 2) }}
                              </pre>
                            </div>
                            <div class="debug-section">
                              <h5>3. {{ t('chat.messages.toolCallsCheck') }}</h5>
                              <pre class="debug-text">
{{ t('chat.messages.hasToolCalls') }}{{ message.toolCalls ? t('chat.messages.has') : t('chat.messages.notHas') }}
{{ t('chat.messages.toolCallsIsArray') }}{{ Array.isArray(message.toolCalls) ? t('chat.messages.is') : t('chat.messages.notIs') }}
{{ t('chat.messages.toolCallsLength') }}{{ message.toolCalls?.length || 0 }}
{{ t('chat.messages.toolCallsContent') }}{{ JSON.stringify(message.toolCalls, null, 2) }}
                              </pre>
                            </div>
                            <div class="debug-section">
                              <h5>4. {{ t('chat.messages.conditionCheck') }}</h5>
                              <pre class="debug-text">
{{ t('chat.messages.condition1') }}
{{ message.reasoning?.trace && message.reasoning.trace.length > 0 ? t('chat.messages.satisfied') : t('chat.messages.notSatisfied') }}

{{ t('chat.messages.condition2') }}
{{ message.toolCalls && message.toolCalls.length > 0 ? t('chat.messages.satisfied') : t('chat.messages.notSatisfied') }}
                              </pre>
                            </div>
                          </div>
                        </el-collapse-item>
                      </el-collapse>
                    </div>
                    
                    <!-- Reasoning statistics -->
                    <div v-if="message.reasoning" class="reasoning-stats">
                      <div class="stats-item">
                        <span class="stats-label">{{ t('chat.messages.traceSteps') }}</span>
                        <span class="stats-value">{{ message.reasoning.trace?.length || 0 }}</span>
                      </div>
                      <div class="stats-item">
                        <span class="stats-label">{{ t('chat.messages.iterationCount') }}</span>
                        <span class="stats-value">{{ message.reasoning.iterations !== undefined ? message.reasoning.iterations : 0 }}</span>
                      </div>
                      <div class="stats-item">
                        <span class="stats-label">{{ t('chat.messages.finalStatus') }}</span>
                        <el-tag :type="message.reasoning.final ? 'success' : 'warning'" size="small">
                          {{ message.reasoning.final ? t('chat.messages.completed') : t('chat.messages.notCompleted') }}
                        </el-tag>
                      </div>
                    </div>
                    
                    <!-- Debug information (development environment display) -->
                    <div v-if="isDevelopment && message.reasoning" class="debug-info">
                      <el-collapse>
                        <el-collapse-item :title="'🔍 ' + t('chat.messages.debugInfoTitle')" name="debug">
                          <div class="debug-content">
                            <div class="debug-section">
                              <h5>{{ t('chat.messages.reasoningStructureTitle') }}</h5>
                              <pre class="debug-json">{{ JSON.stringify(message.reasoning, null, 2) }}</pre>
                            </div>
                            <div class="debug-section">
                              <h5>{{ t('chat.messages.reasoningContent') }}</h5>
                              <pre class="debug-text">{{ message.reasoningContent || t('chat.messages.empty') }}</pre>
                            </div>
                            <div class="debug-section">
                              <h5>{{ t('chat.messages.toolCalls') }}：</h5>
                              <pre class="debug-json">{{ JSON.stringify(message.toolCalls, null, 2) }}</pre>
                            </div>
                          </div>
                        </el-collapse-item>
                      </el-collapse>
                    </div>
                  </div>
                
                <!-- Tool call information -->
                <div v-if="message.toolCalls && message.toolCalls.length > 0" class="tools-section">
                  <div class="section-header">
                    <el-icon><Tools /></el-icon>
                    <span>{{ t('chat.messages.toolCalls') }}</span>
                    <el-tag size="small" type="info">
                      {{ message.toolCalls.length }} {{ t('chat.messages.tools') }}
                    </el-tag>
                  </div>
                  
                  <div class="tool-list">
                    <div 
                      v-for="(toolCall, tcIndex) in message.toolCalls"
                      :key="tcIndex"
                      class="tool-item"
                      :class="{ 'success': toolCall.success, 'error': !toolCall.success }"
                    >
                      <div class="tool-summary">
                        <div class="tool-basic-info">
                          <el-icon class="tool-status-icon">
                            <Tools v-if="toolCall.success" />
                            <CircleCloseFilled v-else />
                          </el-icon>
                          <span class="tool-name">{{ toolCall.toolName }}</span>
                          <el-tag 
                            :type="toolCall.success ? 'success' : 'danger'" 
                            size="small"
                          >
                            {{ toolCall.success ? t('chat.messages.success') : t('chat.messages.failure') }}
                          </el-tag>
                          <span v-if="toolCall.duration" class="tool-duration">
                            {{ toolCall.duration >= 1000 ? Math.round(toolCall.duration / 1000) + t('chat.time.seconds') : toolCall.duration + t('chat.time.milliseconds') }}
                          </span>
                        </div>
                        
                        <el-button
                          size="small"
                          type="primary"
                          link
                          @click="toggleToolDetails(message.id, tcIndex)"
                        >
                          {{ isToolExpanded(message.id, tcIndex) ? t('chat.messages.collapse') : t('chat.messages.viewDetails') }}
                        </el-button>
                      </div>
                      
                      <!-- Tool details -->
                      <el-collapse 
                        v-model="expandedToolItems[`${message.id}-${tcIndex}`]"
                        class="tool-details-collapse"
                      >
                        <el-collapse-item name="details" class="tool-details-item">
                          <!-- Tool parameters -->
                          <div v-if="Object.keys(toolCall.parameters || {}).length > 0" class="tool-parameters">
                            <div class="detail-title">{{ t('chat.messages.parameters') }}</div>
                            <div class="param-list">
                              <el-tag 
                                v-for="(value, key) in toolCall.parameters"
                                :key="key"
                                size="small"
                                class="param-tag"
                              >
                                {{ key }}: {{ formatParameterValue(value) }}
                              </el-tag>
                            </div>
                          </div>
                          
                          <!-- Tool result -->
                          <div class="tool-result">
                            <div class="detail-title">
                              {{ toolCall.success ? t('chat.messages.executionResult') : t('chat.messages.errorInfo') }}
                            </div>
                            <pre class="result-content">{{
                              toolCall.success 
                                ? JSON.stringify(toolCall.result, null, 2)
                                : toolCall.error
                            }}</pre>
                          </div>
                        </el-collapse-item>
                      </el-collapse>
                    </div>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>
            </div>
            
            <!-- Main answer content (highlighted) -->
            <div class="main-answer">
              <div class="answer-content">
                <div class="formatted-text" v-html="renderMarkdown(message.content)"></div>
              </div>
            </div>
            
            <!-- Quality assessment information -->
            <div v-if="message.quality" class="quality-assessment">
              <div class="quality-header">
                <el-icon><Medal /></el-icon>
                <span>{{ t('chat.messages.qualityAssessment') }}</span>
              </div>
              <div class="quality-content">
                <div class="quality-score">
                  <el-progress
                    :percentage="Math.max(0, Math.min(100, message.quality.score))"
                    :color="getQualityColor(message.quality.score)"
                    :stroke-width="8"
                    :format="format => `${format}${t('chat.messages.score')}`"
                  />
                  <span class="score-label">{{ getQualityLabel(message.quality.score) }}</span>
                </div>
                
                <!-- Quality issues -->
                <div v-if="message.quality.issues && message.quality.issues.length > 0" class="quality-issues">
                  <div class="issues-title">{{ t('chat.messages.issuesFound') }}</div>
                  <ul class="issues-list">
                    <li v-for="issue in message.quality.issues" :key="issue" class="issue-item">
                      <el-icon class="issue-icon"><WarnTriangleFilled /></el-icon>
                      {{ issue }}
                    </li>
                  </ul>
                </div>
                
                <!-- Improvement recommendations -->
                <div v-if="message.quality.recommendations && message.quality.recommendations.length > 0" class="quality-recommendations">
                  <div class="recommendations-title">{{ t('chat.messages.recommendations') }}</div>
                  <ul class="recommendations-list">
                    <li v-for="recommendation in message.quality.recommendations" :key="recommendation" class="recommendation-item">
                                              <el-icon class="recommendation-icon"><InfoFilled /></el-icon>
                      {{ recommendation }}
                    </li>
                  </ul>
                </div>
              </div>
            </div>
            
            <!-- Bottom information bar -->
            <div class="message-footer">
              <!-- Cost information -->
              <div v-if="message.cost" class="cost-info">
                <el-tag size="small" type="info">
                  {{ t('chat.messages.cost', { cost: message.cost.totalCost?.toFixed(4) || '0.0000' }) }}
                </el-tag>
              </div>
              
              <!-- Quality quick indicators -->
              <div v-if="message.quality" class="quality-quick-info">
                <el-tag 
                  size="small" 
                  :type="getQualityTagType(message.quality.score)"
                >
                  {{ t('chat.messages.quality', { score: message.quality.score }) }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Message action buttons -->
        <div class="message-actions">
          <div style="display: flex;">
            <el-button
                :icon="DocumentCopy"
                size="small"
                text
                @click="copyMessage(message.content)"
                :title="t('chat.messages.copyMessage')"
            />

            <el-button
                v-if="message.role === 'assistant' && !message.error"
                :icon="RefreshRight"
                size="small"
                text
                @click="retryMessage(message.id)"
                :title="t('chat.messages.regenerate')"
            />

            <el-button
                v-if="message.role === 'assistant' && message.toolCalls?.length > 0"
                :icon="View"
                size="small"
                text
                @click="showToolCallDetails(message.toolCalls)"
                :title="t('chat.messages.viewToolDetails')"
            />
          </div>
        </div>
      </div>
    </div>
    
    <!-- Real-time reasoning and streaming results display -->
    <RealtimeReasoningDisplay
      v-if="isProcessing"
      :reasoning-content="currentReasoningContent"
      :stream-content="currentStreamContent"
      :progress-message="currentProgress"
      :is-processing="isProcessing"
      :accumulated-reasoning-steps="accumulatedReasoningSteps"
      :accumulated-stream-chunks="accumulatedStreamChunks"
      :pending-tool-confirmation="pendingToolConfirmation"
      :pending-tools="pendingTools"
      :allow-batch-confirmation="allowBatchConfirmation"
      :confirmation-timeout="confirmationTimeout"
      @tool-confirm="handleToolConfirm"
      @tool-reject="handleToolReject"
      @tool-timeout="handleToolTimeout"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { marked } from 'marked'
import { useI18n } from 'vue-i18n'
import {
  UserFilled,
  Avatar,
  Tools,
  Cpu,
  DocumentCopy,
  RefreshRight,
  View,
  WarnTriangleFilled,
  CircleCloseFilled,
  ArrowRight,
  List,
  Document,
  Lightning,
  Search,
  DataAnalysis,
  Check,
  Close,
  ChatLineRound,
  InfoFilled,
  Medal,
  VideoPause
} from '@element-plus/icons-vue'

import RealtimeReasoningDisplay from '@/components/chat/RealtimeReasoningDisplay.vue'
import DebugLogger from "@/utils/DebugLogger";

// Configure marked
marked.setOptions({
  breaks: true, // Support line breaks
  gfm: true,    // Support GitHub Flavored Markdown
})

// Props
const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  isProcessing: {
    type: Boolean,
    default: false
  },
  // Real-time reasoning content
  currentReasoningContent: {
    type: String,
    default: ''
  },
  // Real-time streaming content
  currentStreamContent: {
    type: String,
    default: ''
  },
  // Current progress information
  currentProgress: {
    type: String,
    default: ''
  },
  // New: accumulated reasoning steps array
  accumulatedReasoningSteps: {
    type: Array,
    default: () => []
  },
  // New: accumulated streaming content chunks array
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
const emit = defineEmits([
  'copy-message',
  'retry-message',
  'show-tool-details',
  'show-reasoning-trace',
  'tool-confirm',
  'tool-reject',
  'tool-timeout'
])

const logger = DebugLogger.createLogger('ChatMessages')

// Internationalization
const { t } = useI18n()

// Reactive data
const expandedReasoningItems = ref({}) // Expanded reasoning details {messageId: ['reasoning']}
const expandedToolItems = ref({}) // Expanded tool details {messageId-toolIndex: ['details']}
const autoExpandedMessages = ref(new Set()) // Record automatically expanded message IDs

// Computed properties
const isDevelopment = computed(() => {
  return process.env.NODE_ENV === 'development'
})

// Methods
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  
  if (diffMins < 1) {
    return t('chat.time.justNow')
  } else if (diffMins < 60) {
    return t('chat.time.minutesAgo', { minutes: diffMins })
  } else if (diffMins < 1440) {
    return t('chat.time.hoursAgo', { hours: Math.floor(diffMins / 60) })
  } else {
    return date.toLocaleDateString()
  }
}

// Render markdown content
const renderMarkdown = (content) => {
  if (!content) return ''
  
  try {
    // Use marked to convert markdown to HTML
    return marked(content)
  } catch (error) {
    console.error('Markdown rendering error:', error)
    // If rendering fails, return original content
    return content.replace(/\n/g, '<br>')
  }
}

const formatParameterValue = (value) => {
  if (value === null || value === undefined) {
    return 'null'
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value).length > 50 
    ? String(value).substring(0, 50) + '...' 
    : String(value)
}

const copyMessage = (content) => {
  emit('copy-message', content)
}

const retryMessage = (messageId) => {
  emit('retry-message', messageId)
}

const showToolCallDetails = (toolCalls) => {
  emit('show-tool-details', toolCalls)
}

const showReasoningTrace = (reasoning) => {
  emit('show-reasoning-trace', reasoning)
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

// Expand/collapse reasoning details
const toggleReasoningDetails = (messageId) => {
  if (expandedReasoningItems.value[messageId] && expandedReasoningItems.value[messageId].includes('reasoning')) {
    expandedReasoningItems.value[messageId] = []
  } else {
    expandedReasoningItems.value[messageId] = ['reasoning']
  }
}

const isReasoningExpanded = (messageId) => {
  return expandedReasoningItems.value[messageId] && expandedReasoningItems.value[messageId].includes('reasoning')
}

// Expand/collapse tool details
const toggleToolDetails = (messageId, toolIndex) => {
  const key = `${messageId}-${toolIndex}`
  if (expandedToolItems.value[key] && expandedToolItems.value[key].includes('details')) {
    expandedToolItems.value[key] = []
  } else {
    expandedToolItems.value[key] = ['details']
  }
}

const isToolExpanded = (messageId, toolIndex) => {
  const key = `${messageId}-${toolIndex}`
  return expandedToolItems.value[key] && expandedToolItems.value[key].includes('details')
}

// Get thinking status text
const getThinkingStatusText = (message) => {
  const hasReasoning = message.reasoning
  const hasTools = message.toolCalls && message.toolCalls.length > 0
  const isStopped = message.stopped || (message.reasoning && message.reasoning.stopped)
  
  // Check if currently processing this message
  const isCurrentlyProcessing = props.isProcessing && isLastAssistantMessage(message)
  
  // If it's a user-stopped message
  if (isStopped) {
    const iterations = hasReasoning ? (message.reasoning.iterations || 0) : 0
    return t('chat.thinking.stopped', { iterations })
  }
  
  if (isCurrentlyProcessing) {
    if (hasReasoning && hasTools) {
      return t('chat.thinking.reasoningWithTools', { count: message.toolCalls.length })
    } else if (hasReasoning) {
      const iterations = message.reasoning.iterations
      return t('chat.thinking.reasoning', { iteration: iterations !== undefined ? iterations : 1 })
    } else if (hasTools) {
      return t('chat.thinking.toolCalling', { count: message.toolCalls.length })
    }
    return t('chat.thinking.processing')
  } else {
    if (hasReasoning && hasTools) {
      return t('chat.thinking.reasoningCompleted', { count: message.toolCalls.length })
    } else if (hasReasoning) {
      const iterations = message.reasoning.iterations
      return t('chat.thinking.reasoningDone', { iterations: iterations !== undefined ? iterations : 0 })
    } else if (hasTools) {
      return t('chat.thinking.toolCallingCompleted', { count: message.toolCalls.length })
    }
    return t('chat.thinking.completed')
  }
}

// Check if it's the last assistant message
const isLastAssistantMessage = (message) => {
  const assistantMessages = props.messages.filter(msg => msg.role === 'assistant')
  return assistantMessages.length > 0 && assistantMessages[assistantMessages.length - 1].id === message.id
}

// Get thinking duration
const getThinkingDuration = (message) => {
  const isStopped = message.stopped || (message.reasoning && message.reasoning.stopped)
  
  // Check if currently processing this message
  const isCurrentlyProcessing = props.isProcessing && isLastAssistantMessage(message)
  
  if (isCurrentlyProcessing) {
    return t('chat.time.processing')
  }
  
  // If it's a user-stopped message
  if (isStopped) {
    if (message.totalDuration) {
      const duration = message.totalDuration
      if (duration >= 1000) {
        return t('chat.time.stoppedFor', { duration: Math.round(duration / 1000) + t('chat.time.seconds') })
      } else {
        return t('chat.time.stoppedFor', { duration: duration + t('chat.time.milliseconds') })
      }
    }
    return t('chat.time.stopped')
  }
  
  // Prioritize using totalDuration (entire conversation duration)
  if (message.totalDuration) {
    const duration = message.totalDuration
    if (duration >= 1000) {
      return t('chat.time.used', { duration: Math.round(duration / 1000) + t('chat.time.seconds') })
    } else {
      return t('chat.time.used', { duration: duration + t('chat.time.milliseconds') })
    }
  }
  
  // Then use time from reasoning information
  if (message.reasoning && message.reasoning.duration) {
    const duration = message.reasoning.duration
    if (duration >= 1000) {
      return t('chat.time.used', { duration: Math.round(duration / 1000) + t('chat.time.seconds') })
    } else {
      return t('chat.time.used', { duration: duration + t('chat.time.milliseconds') })
    }
  }
  
  // Finally use sum of tool call times
  if (message.toolCalls && message.toolCalls.length > 0) {
    const totalDuration = message.toolCalls.reduce((sum, tool) => sum + (tool.duration || 0), 0)
    if (totalDuration > 0) {
      if (totalDuration >= 1000) {
        return t('chat.time.used', { duration: Math.round(totalDuration / 1000) + t('chat.time.seconds') })
      } else {
        return t('chat.time.used', { duration: totalDuration + t('chat.time.milliseconds') })
      }
    }
  }
  
  return t('chat.time.instant')
}

// Get reasoning step icon
const getStepIcon = (stepType) => {
  const iconMap = {
    'thought': ChatLineRound,
    'action_plan': Lightning,
    'action_result': Check,
    'observation': Search,
    'reasoning': Cpu,
    'tool_call': Tools,
    'analysis': DataAnalysis,
    'information_gathering': Search,
    'error': Close
  }
  return iconMap[stepType] || Document
}

// Get reasoning step type name
const getStepTypeName = (stepType) => {
  const typeNames = {
    'thought': t('chat.reasoningSteps.thought'),
    'action_plan': t('chat.reasoningSteps.actionPlan'),
    'action_result': t('chat.reasoningSteps.actionResult'),
    'observation': t('chat.reasoningSteps.observation'),
    'reasoning': t('chat.reasoningSteps.reasoning'),
    'tool_call': t('chat.reasoningSteps.toolCall'),
    'analysis': t('chat.reasoningSteps.analysis'),
    'information_gathering': t('chat.reasoningSteps.informationGathering'),
    'error': t('chat.reasoningSteps.error')
  }
  return typeNames[stepType] || stepType
}

// Get action type color
const getActionTypeColor = (actionType) => {
  const colorMap = {
    'tool_call': 'primary',
    'information_gathering': 'info',
    'analysis': 'success',
    'reasoning': 'warning',
    'error': 'danger'
  }
  return colorMap[actionType] || 'info'
}

// Format reasoning step time
const formatStepTime = (timestamp) => {
  if (!timestamp) return ''
  
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit',
    fractionalSecondDigits: 3
  })
}

// Get quality assessment color
const getQualityColor = (score) => {
  if (score >= 90) return '#67c23a' // Green - excellent
  if (score >= 80) return '#409eff' // Blue - good
  if (score >= 70) return '#e6a23c' // Orange - average
  if (score >= 60) return '#f56c6c' // Red - poor
  return '#909399' // Gray - very poor
}

// Get quality assessment text label
const getQualityLabel = (score) => {
  if (score >= 90) return t('chat.quality.excellent')
  if (score >= 80) return t('chat.quality.good')
  if (score >= 70) return t('chat.quality.average')
  if (score >= 60) return t('chat.quality.poor')
  return t('chat.quality.veryPoor')
}

// Get quality tag type (Element Plus tag type)
const getQualityTagType = (score) => {
  if (score >= 90) return 'success'  // Green
  if (score >= 80) return 'primary'  // Blue
  if (score >= 70) return 'warning'  // Orange
  if (score >= 60) return 'danger'   // Red
  return 'info'                      // Gray
}

// Record currently processing message ID
const currentProcessingMessageId = ref(null)

// Auto expand/collapse reasoning details logic
watch(() => props.messages, (newMessages, oldMessages) => {
  if (!newMessages || newMessages.length === 0) return
  
  // Check if there are new assistant messages
  const newMessagesCount = newMessages.length
  const oldMessagesCount = oldMessages?.length || 0
  
  if (newMessagesCount > oldMessagesCount) {
    // New message added
    const newMessage = newMessages[newMessages.length - 1]
    
    if (newMessage.role === 'assistant') {
      logger.log('🆕 New assistant message detected:', newMessage.id)
      
      // Clean up previous expand state
      if (currentProcessingMessageId.value && currentProcessingMessageId.value !== newMessage.id) {
        logger.log('🧹 Cleaning previous message expand state:', currentProcessingMessageId.value)
        if (expandedReasoningItems.value[currentProcessingMessageId.value]) {
          expandedReasoningItems.value[currentProcessingMessageId.value] = []
        }
        autoExpandedMessages.value.delete(currentProcessingMessageId.value)
      }
      
      // Record new processing message ID
      currentProcessingMessageId.value = newMessage.id
      
      // If new message has reasoning content, auto-expand
      if (newMessage.reasoning || newMessage.toolCalls) {
        expandedReasoningItems.value[newMessage.id] = ['reasoning']
        autoExpandedMessages.value.add(newMessage.id)
        logger.log('🔄 Auto-expanding new message reasoning details:', newMessage.id)
      }
    }
  }
}, { deep: true })

// Monitor processing state changes, delay collapse after processing completion
watch(() => props.isProcessing, (isProcessing, wasProcessing) => {
  if (!isProcessing && wasProcessing && currentProcessingMessageId.value) {
    // Processing completed: delay 3 seconds then collapse current message
    const messageIdToFold = currentProcessingMessageId.value
    logger.log('✅ Processing completed, auto-collapsing message in 3 seconds:', messageIdToFold)
    
    setTimeout(() => {
      if (expandedReasoningItems.value[messageIdToFold]) {
        expandedReasoningItems.value[messageIdToFold] = []
        autoExpandedMessages.value.delete(messageIdToFold)
        logger.log('⏰ Auto-collapsing reasoning details:', messageIdToFold)
      }
      
      // Clean up current processing message ID
      if (currentProcessingMessageId.value === messageIdToFold) {
        currentProcessingMessageId.value = null
      }
    }, 3000)
  }
})
</script>

<style scoped lang="scss">
.messages-list {
  .message-item {
    margin-bottom: 24px;
    position: relative;
    
    &.processing {
      opacity: 0.8;
    }
    
    &.has-error {
      .message-content {
        border-left: 3px solid var(--el-color-danger);
      }
    }
    
    // User message styles - right aligned
    &.user {
      // Right align entire message item
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      
      .message-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
        flex-direction: row-reverse;
        
        .message-meta {
          display: flex;
          flex-direction: column;
          gap: 2px;
          text-align: right;
          
          .role-label {
            font-weight: 600;
            color: var(--el-text-color-primary);
            font-size: 14px;
          }
          
          .message-time {
            font-size: 12px;
            color: var(--el-text-color-secondary);
          }
        }
      }
      
      .message-content {
        margin-left: 0;
        margin-right: 0;
        position: relative;
        display: flex;
        justify-content: flex-end;
        
        .user-message {
          background: linear-gradient(135deg, var(--el-color-primary), var(--el-color-primary-light-3));
          color: white;
          padding: 14px 18px;
          border-radius: 16px 16px 6px 16px;
          max-width: 75%;
          word-break: break-word;
          line-height: 1.5;
          box-shadow: 
            0 2px 8px rgba(var(--el-color-primary-rgb), 0.2),
            0 1px 3px rgba(0, 0, 0, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.1);
          transition: all 0.3s ease;
          
          &:hover {
            transform: translateY(-1px);
            box-shadow: 
              0 4px 12px rgba(var(--el-color-primary-rgb), 0.25),
              0 2px 6px rgba(0, 0, 0, 0.15);
          }
        }
      }
      
      .message-actions {
        right: auto;
        left: -60px;
      }
    }
    
    // Assistant message styles - left aligned
    &.assistant {
      // Left align entire message item
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      
      .message-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
        
        .message-meta {
          display: flex;
          flex-direction: column;
          gap: 2px;
          
          .role-label {
            font-weight: 600;
            color: var(--el-text-color-primary);
            font-size: 14px;
          }
          
          .message-time {
            font-size: 12px;
            color: var(--el-text-color-secondary);
          }
        }
      }
      
      .message-content {
        margin-left: 44px;
        position: relative;
        
        .assistant-message {
        .error-message {
          background: var(--el-color-error-light-9);
          border: 1px solid var(--el-color-error-light-8);
          color: var(--el-color-error);
          padding: 12px 16px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        
        .stopped-message {
          background: var(--el-color-warning-light-9);
          border: 1px solid var(--el-color-warning-light-8);
          color: var(--el-color-warning-dark-2);
          padding: 12px 16px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          gap: 8px;
          
          .el-icon {
            font-size: 16px;
            color: var(--el-color-warning);
          }
        }
        
        .normal-message {
          // Thinking status area
          .thinking-status {
            margin-bottom: 16px;
            max-width: fit-content;
            
            .thinking-header {
              background: rgba(255, 255, 255, 0.8);
              backdrop-filter: blur(10px);
              border: 1px solid rgba(34, 197, 94, 0.2);
              border-radius: 12px;
              padding: 14px 18px;
              cursor: pointer;
              transition: all 0.3s ease;
              display: flex;
              justify-content: space-between;
              align-items: center;
              min-width: 280px;
              max-width: 75%;
              box-shadow: 
                0 2px 8px rgba(34, 197, 94, 0.1),
                0 1px 3px rgba(0, 0, 0, 0.05);
              
              &:hover {
                background: rgba(255, 255, 255, 0.9);
                border-color: rgba(34, 197, 94, 0.3);
                transform: translateY(-1px);
                box-shadow: 
                  0 4px 12px rgba(34, 197, 94, 0.15),
                  0 2px 6px rgba(0, 0, 0, 0.1);
              }
              
              .thinking-info {
                display: flex;
                align-items: center;
                gap: 8px;
                
                .thinking-icon {
                  color: var(--el-color-success);
                  font-size: 16px;
                  
                  &.rotating {
                    animation: spin 2s linear infinite;
                    color: var(--el-color-warning);
                  }
                }
                
                .thinking-text {
                  color: var(--el-color-success-dark-2);
                  font-weight: 500;
                  font-size: 14px;
                }
              }
              
              .expand-icon {
                color: var(--el-color-success);
                transition: transform 0.2s ease;
                
                &.expanded {
                  transform: rotate(90deg);
                }
              }
            }
            
                        .reasoning-collapse {
              margin-top: 12px;
              border: none;
              max-width: 100%;
              
              :deep(.el-collapse-item__header) {
                display: none; // Hide default collapse header since we have custom thinking-header
              }
              
              :deep(.el-collapse-item__wrap) {
                border: none;
              }
              
              :deep(.el-collapse-item__content) {
                padding: 16px;
                background: var(--el-fill-color-extra-light);
                border-radius: 8px;
                border: 1px solid var(--el-border-color-light);
                box-sizing: border-box;
              }
              
              .reasoning-section, .tools-section {
                margin-bottom: 16px;
                
                &:last-child {
                  margin-bottom: 0;
                }
                
                // Reasoning trace styles
                .reasoning-trace {
                  margin-bottom: 20px;
                  
                  .trace-header {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 16px;
                    padding: 8px 12px;
                    background: var(--el-color-info-light-9);
                    border-radius: 6px;
                    border: 1px solid var(--el-color-info-light-8);
                    
                    span {
                      font-weight: 500;
                      color: var(--el-color-info-dark-2);
                    }
                  }
                  
                  .trace-timeline {
                    position: relative;
                    
                    // Timeline connection line
                    &::before {
                      content: '';
                      position: absolute;
                      left: 20px;
                      top: 0;
                      bottom: 0;
                      width: 2px;
                      background: var(--el-border-color-light);
                      z-index: 1;
                    }
                    
                    .trace-step {
                      position: relative;
                      margin-bottom: 16px;
                      display: flex;
                      align-items: flex-start;
                      gap: 12px;
                      
                      &:last-child {
                        margin-bottom: 0;
                      }
                      
                      .step-marker {
                        position: relative;
                        z-index: 2;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        width: 40px;
                        height: 40px;
                        border-radius: 50%;
                        background: var(--el-fill-color-lighter);
                        border: 2px solid var(--el-border-color-light);
                        flex-shrink: 0;
                        
                        .step-icon {
                          font-size: 16px;
                          color: var(--el-text-color-regular);
                        }
                        
                        .step-number {
                          position: absolute;
                          bottom: -4px;
                          right: -4px;
                          font-size: 10px;
                          background: var(--el-color-primary);
                          color: white;
                          border-radius: 50%;
                          width: 16px;
                          height: 16px;
                          display: flex;
                          align-items: center;
                          justify-content: center;
                          font-weight: bold;
                        }
                      }
                      
                      // Different step type styles
                      &.thought .step-marker {
                        background: var(--el-color-info-light-9);
                        border-color: var(--el-color-info-light-6);
                        .step-icon { color: var(--el-color-info); }
                      }
                      
                      &.action_plan .step-marker {
                        background: var(--el-color-warning-light-9);
                        border-color: var(--el-color-warning-light-6);
                        .step-icon { color: var(--el-color-warning); }
                      }
                      
                      &.action_result .step-marker {
                        background: var(--el-color-success-light-9);
                        border-color: var(--el-color-success-light-6);
                        .step-icon { color: var(--el-color-success); }
                      }
                      
                      &.observation .step-marker {
                        background: var(--el-color-primary-light-9);
                        border-color: var(--el-color-primary-light-6);
                        .step-icon { color: var(--el-color-primary); }
                      }
                      
                      &.reasoning .step-marker {
                        background: var(--el-color-success-light-9);
                        border-color: var(--el-color-success-light-6);
                        .step-icon { color: var(--el-color-success); }
                      }
                      
                      .step-content {
                        flex: 1;
                        background: var(--el-fill-color-extra-light);
                        border: 1px solid var(--el-border-color-lighter);
                        border-radius: 8px;
                        padding: 12px;
                        
                        .step-header {
                          display: flex;
                          justify-content: space-between;
                          align-items: center;
                          margin-bottom: 8px;
                          
                          .step-type {
                            font-weight: 600;
                            color: var(--el-text-color-primary);
                          }
                          
                          .step-time {
                            font-size: 12px;
                            color: var(--el-text-color-secondary);
                            font-family: monospace;
                          }
                        }
                        
                        .step-body {
                          .action-plan-content, .action-result-content {
                            .plan-detail, .result-detail {
                              margin-bottom: 8px;
                              
                              &:last-child {
                                margin-bottom: 0;
                              }
                              
                              .detail-label {
                                font-weight: 500;
                                color: var(--el-text-color-regular);
                                margin-right: 4px;
                              }
                              
                              code {
                                background: var(--el-color-info-light-9);
                                padding: 2px 6px;
                                border-radius: 4px;
                                font-size: 12px;
                                color: var(--el-color-info-dark-2);
                              }
                              
                              .json-content {
                                background: var(--el-fill-color-light);
                                border: 1px solid var(--el-border-color-lighter);
                                border-radius: 4px;
                                padding: 8px;
                                font-size: 12px;
                                color: var(--el-text-color-regular);
                                margin-top: 4px;
                                white-space: pre-wrap;
                                word-wrap: break-word;
                              }
                              
                              .reasoning-text {
                                color: var(--el-text-color-regular);
                                line-height: 1.5;
                                margin-top: 4px;
                              }
                            }
                            
                            .result-status {
                              display: flex;
                              align-items: center;
                              gap: 8px;
                              margin-bottom: 8px;
                              
                              .duration {
                                font-size: 12px;
                                color: var(--el-text-color-secondary);
                              }
                            }
                            
                            .error-message {
                              background: var(--el-color-error-light-9);
                              border: 1px solid var(--el-color-error-light-8);
                              color: var(--el-color-error);
                              padding: 8px;
                              border-radius: 4px;
                              font-size: 12px;
                              margin-top: 4px;
                            }
                          }
                          
                          .thought-content, .observation-content, .reasoning-content {
                            .thought-text, .observation-text, .reasoning-text {
                              color: var(--el-text-color-regular);
                              line-height: 1.5;
                              white-space: pre-wrap;
                              word-wrap: break-word;
                            }
                          }
                          
                          .text-content {
                            background: var(--el-fill-color-light);
                            border: 1px solid var(--el-border-color-lighter);
                            border-radius: 4px;
                            padding: 8px;
                            font-size: 12px;
                            color: var(--el-text-color-regular);
                            white-space: pre-wrap;
                            word-wrap: break-word;
                          }
                        }
                      }
                    }
                                     }
                 }
                 
                 // Debug information styles
                 .debug-info {
                   margin-top: 16px;
                   border: 2px dashed var(--el-color-warning-light-7);
                   border-radius: 8px;
                   background: var(--el-color-warning-light-9);
                   
                   .debug-content {
                     padding: 12px;
                     
                     .debug-section {
                       margin-bottom: 12px;
                       
                       &:last-child {
                         margin-bottom: 0;
                       }
                       
                       h5 {
                         margin: 0 0 8px 0;
                         color: var(--el-color-warning-dark-2);
                         font-size: 14px;
                         font-weight: 600;
                       }
                       
                       .debug-json, .debug-text {
                         background: var(--el-fill-color-light);
                         border: 1px solid var(--el-border-color-light);
                         border-radius: 4px;
                         padding: 8px;
                         font-size: 11px;
                         color: var(--el-text-color-regular);
                         white-space: pre-wrap;
                         word-wrap: break-word;
                         max-height: 200px;
                         overflow-y: auto;
                       }
                     }
                   }
                 }
                 
                 // Reasoning summary styles
                .reasoning-summary-section {
                  .summary-header {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 12px;
                    
                    span {
                      font-weight: 500;
                      color: var(--el-text-color-primary);
                    }
                  }
                }
                
                // Reasoning statistics styles
                .reasoning-stats {
                  display: flex;
                  gap: 16px;
                  margin-top: 12px;
                  padding: 8px 12px;
                  background: var(--el-fill-color-extra-light);
                  border-radius: 6px;
                  border: 1px solid var(--el-border-color-lighter);
                  
                  .stats-item {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    
                    .stats-label {
                      font-size: 12px;
                      color: var(--el-text-color-secondary);
                    }
                    
                    .stats-value {
                      font-size: 12px;
                      font-weight: 500;
                      color: var(--el-text-color-primary);
                    }
                  }
                }
                
                .section-header {
                  display: flex;
                  align-items: center;
                  gap: 8px;
                  margin-bottom: 12px;
                  
                  .el-icon {
                    color: var(--el-color-primary);
                  }
                  
                  span {
                    font-weight: 600;
                    color: var(--el-text-color-primary);
                  }
                }
                
                .reasoning-content {
                  margin-bottom: 12px;
                  
                  .reasoning-text {
                    background: var(--el-fill-color);
                    border: 1px solid var(--el-border-color-lighter);
                    border-radius: 6px;
                    padding: 12px;
                    margin: 0;
                    font-family: inherit;
                    font-size: 13px;
                    line-height: 1.5;
                    color: var(--el-text-color-regular);
                    white-space: pre-wrap;
                    word-break: break-word;
                    max-height: 300px;
                    overflow-y: auto;
                  }
                }
                
                .reasoning-summary {
                  margin-bottom: 12px;
                  
                  .reasoning-item {
                    display: flex;
                    gap: 8px;
                    margin-bottom: 6px;
                    font-size: 14px;
                    
                    .item-label {
                      color: var(--el-text-color-secondary);
                      min-width: 80px;
                    }
                  }
                }
              }
              
              .tools-section {
                .tool-list {
                  .tool-item {
                    background: white;
                    border: 1px solid var(--el-border-color);
                    border-radius: 6px;
                    margin-bottom: 8px;
                    overflow: hidden;
                    
                    &.success {
                      border-color: var(--el-color-success-light-8);
                    }
                    
                    &.error {
                      border-color: var(--el-color-danger-light-8);
                    }
                    
                    .tool-summary {
                      padding: 12px;
                      display: flex;
                      justify-content: space-between;
                      align-items: center;
                      
                      .tool-basic-info {
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        
                        .tool-status-icon {
                          &.success {
                            color: var(--el-color-success);
                          }
                          
                          &.error {
                            color: var(--el-color-danger);
                          }
                        }
                        
                        .tool-name {
                          font-weight: 500;
                          color: var(--el-text-color-primary);
                        }
                        
                        .tool-duration {
                          font-size: 12px;
                          color: var(--el-text-color-secondary);
                        }
                      }
                    }
                    
                    .tool-details-collapse {
                      border: none;
                      
                      :deep(.el-collapse-item__header) {
                        display: none; // Hide default collapse header
                      }
                      
                      :deep(.el-collapse-item__wrap) {
                        border: none;
                      }
                      
                      :deep(.el-collapse-item__content) {
                        padding: 0 12px 12px;
                        border-top: 1px solid var(--el-border-color-lighter);
                        background: var(--el-fill-color-extra-light);
                      }
                      
                      .tool-parameters {
                        margin-bottom: 12px;
                        
                        .detail-title {
                          font-size: 12px;
                          color: var(--el-text-color-secondary);
                          margin-bottom: 6px;
                        }
                        
                        .param-list {
                          .param-tag {
                            margin-right: 6px;
                            margin-bottom: 4px;
                          }
                        }
                      }
                      
                      .tool-result {
                        .detail-title {
                          font-size: 12px;
                          color: var(--el-text-color-secondary);
                          margin-bottom: 6px;
                        }
                        
                        .result-content {
                          background: var(--el-fill-color);
                          padding: 8px;
                          border-radius: 4px;
                          font-size: 12px;
                          margin: 0;
                          white-space: pre-wrap;
                          overflow-x: auto;
                          max-height: 200px;
                          overflow-y: auto;
                          border: 1px solid var(--el-border-color-lighter);
                        }
                      }
                    }
                  }
                }
              }
            }
          }
          
          // Main answer content (highlighted)
          .main-answer {
            .answer-content {
              background: var(--el-fill-color-light);
              border: 2px solid var(--el-color-primary-light-8);
              border-radius: 12px 12px 12px 4px;
              padding: 16px 20px;
              position: relative;
              
              &::before {
                content: '';
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                width: 4px;
                background: var(--el-color-primary);
                border-radius: 2px 0 0 2px;
              }
              
              .formatted-text {
                margin: 0;
                font-family: inherit;
                word-break: break-word;
                line-height: 1.6;
                color: var(--el-text-color-primary);
                font-size: 14px;
                
                // Markdown styles
                :deep(h1), :deep(h2), :deep(h3), :deep(h4), :deep(h5), :deep(h6) {
                  margin: 16px 0 8px 0;
                  font-weight: 600;
                  color: var(--el-text-color-primary);
                  
                  &:first-child {
                    margin-top: 0;
                  }
                }
                
                :deep(h1) { font-size: 20px; }
                :deep(h2) { font-size: 18px; }
                :deep(h3) { font-size: 16px; }
                :deep(h4) { font-size: 15px; }
                :deep(h5) { font-size: 14px; }
                :deep(h6) { font-size: 13px; }
                
                :deep(p) {
                  margin: 8px 0;
                  
                  &:first-child {
                    margin-top: 0;
                  }
                  
                  &:last-child {
                    margin-bottom: 0;
                  }
                }
                
                :deep(ul), :deep(ol) {
                  margin: 8px 0;
                  padding-left: 20px;
                  
                  li {
                    margin: 4px 0;
                  }
                }
                
                :deep(blockquote) {
                  margin: 12px 0;
                  padding: 8px 12px;
                  border-left: 4px solid var(--el-color-primary-light-6);
                  background: var(--el-color-primary-light-9);
                  color: var(--el-text-color-regular);
                }
                
                :deep(code) {
                  background: var(--el-color-info-light-9);
                  padding: 2px 6px;
                  border-radius: 4px;
                  font-size: 13px;
                  color: var(--el-color-info-dark-2);
                  font-family: 'Courier New', Consolas, monospace;
                }
                
                :deep(pre) {
                  background: var(--el-fill-color-light);
                  border: 1px solid var(--el-border-color-lighter);
                  border-radius: 6px;
                  padding: 12px;
                  margin: 12px 0;
                  overflow-x: auto;
                  font-family: 'Courier New', Consolas, monospace;
                  font-size: 13px;
                  
                  code {
                    background: none;
                    padding: 0;
                    border-radius: 0;
                    color: inherit;
                  }
                }
                
                :deep(strong) {
                  font-weight: 600;
                  color: var(--el-text-color-primary);
                }
                
                :deep(em) {
                  font-style: italic;
                  color: var(--el-text-color-regular);
                }
                
                :deep(a) {
                  color: var(--el-color-primary);
                  text-decoration: none;
                  
                  &:hover {
                    text-decoration: underline;
                  }
                }
                
                :deep(table) {
                  border-collapse: collapse;
                  margin: 12px 0;
                  width: 100%;
                  
                  th, td {
                    border: 1px solid var(--el-border-color-light);
                    padding: 8px 12px;
                    text-align: left;
                  }
                  
                  th {
                    background: var(--el-fill-color-light);
                    font-weight: 600;
                  }
                }
                
                :deep(hr) {
                  margin: 16px 0;
                  border: none;
                  border-top: 1px solid var(--el-border-color-light);
                }
              }
            }
          }
          
          // Bottom information bar
          .message-footer {
            margin-top: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            
            .cost-info {
              color: var(--el-text-color-secondary);
              font-size: 12px;
            }
          }
        }
      }
    }
      
    .message-actions {
      position: absolute;
      top: 8px;
      right: -60px;
      display: flex;
      flex-direction: column;
      gap: 4px;
      opacity: 0;
      transition: opacity 0.2s;
    }
    
    &:hover .message-actions {
      opacity: 1;
    }
  }
  }
  
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// Mobile adaptation
@media (max-width: 768px) {
  .chat-messages {
    .message-item {
      &.user {
        // Keep right aligned
        align-items: flex-end;
        
        .message-content {
          margin-left: 0;
          margin-right: 0;
          
          .user-message {
            max-width: 80%;
          }
        }
        
        .message-actions {
          position: static;
          flex-direction: row;
          justify-content: flex-start;
          margin-top: 8px;
          opacity: 1;
        }
      }
      
      &.assistant {
        // Keep left aligned
        align-items: flex-start;
        
        .message-content {
          margin-left: 44px;
          
          .assistant-message {
            .thinking-status {
              max-width: 90%;
              
              .thinking-header {
                min-width: 200px;
                max-width: 100%;
              }
            }
            
            .message-text {
              max-width: 80%;
            }
          }
        }
        
        .message-actions {
          position: static;
          flex-direction: row;
          justify-content: flex-end;
          margin-top: 8px;
          opacity: 1;
        }
      }
    }
  }
}

// Rotation animation
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style> 