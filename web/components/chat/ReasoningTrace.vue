<template>
  <div class="reasoning-trace">
    <div class="trace-header">
      <div class="header-info">
        <el-icon><Cpu /></el-icon>
        <h4>{{ $t('chat.realtimeReasoning.reactReasoningTrace') }}</h4>
        <el-tag type="primary" size="small">
          {{ reasoning.iterations }} {{ $t('chat.reasoningSteps.iterations') }}
        </el-tag>
      </div>
      <div class="trace-stats">
        <span class="stat-item">
          {{ $t('chat.realtimeReasoning.totalSteps') }} <strong>{{ reasoning.trace?.length || 0 }}</strong>
        </span>
        <span class="stat-item">
          {{ $t('chat.realtimeReasoning.toolCalls') }} <strong>{{ toolCallCount }}</strong>
        </span>
      </div>
    </div>

    <!-- Reasoning process timeline -->
    <div class="reasoning-timeline">
      <el-timeline>
        <el-timeline-item
          v-for="(step, index) in reasoning.trace"
          :key="index"
          :timestamp="formatTime(step.timestamp)"
          :type="getStepType(step.type)"
          :icon="getStepIcon(step.type)"
          placement="top"
        >
          <div class="step-content" :class="`step-${step.type}`">
            <div class="step-header">
              <h5>{{ getStepTitle(step.type) }}</h5>
              <el-tag :type="getStepTagType(step.type)" size="small">
                {{ $t('chat.realtimeReasoning.step', { step: index + 1 }) }}
              </el-tag>
            </div>
            
            <div class="step-body">
              <!-- Thought step -->
              <div v-if="step.type === 'thought'" class="thought-content">
                <p>{{ step.content }}</p>
              </div>
              
              <!-- Action plan -->
              <div v-else-if="step.type === 'action_plan'" class="action-plan-content">
                <div class="plan-summary">
                  <strong>{{ $t('chat.realtimeReasoning.planType') }}</strong> {{ step.content.type || $t('common.unknown') }}
                </div>
                <div v-if="step.content.toolName" class="tool-info">
                  <strong>{{ $t('chat.realtimeReasoning.tool') }}</strong> {{ step.content.toolName }}
                </div>
                <div v-if="step.content.parameters" class="parameters">
                  <strong>{{ $t('chat.realtimeReasoning.parameters') }}</strong>
                  <pre><code>{{ JSON.stringify(step.content.parameters, null, 2) }}</code></pre>
                </div>
                <div v-if="step.content.reasoning" class="reasoning">
                  <strong>{{ $t('chat.realtimeReasoning.reasoning') }}</strong> {{ step.content.reasoning }}
                </div>
              </div>
              
              <!-- Action result -->
              <div v-else-if="step.type === 'action_result'" class="action-result-content">
                <div v-if="step.content.success" class="success-result">
                  <el-icon class="success-icon"><CircleCheckFilled /></el-icon>
                  <span>{{ $t('chat.realtimeReasoning.actionExecutedSuccessfully') }}</span>
                </div>
                <div v-else class="error-result">
                  <el-icon class="error-icon"><CircleCloseFilled /></el-icon>
                  <span>{{ $t('chat.realtimeReasoning.actionExecutionFailed') }}</span>
                </div>
                
                <div v-if="step.content.result" class="result-data">
                  <div v-if="typeof step.content.result === 'string'">
                    {{ step.content.result }}
                  </div>
                  <div v-else>
                    <pre><code>{{ JSON.stringify(step.content.result, null, 2) }}</code></pre>
                  </div>
                </div>
                
                <div v-if="step.content.error" class="error-info">
                  <el-alert
                    :title="step.content.error"
                    type="error"
                    :closable="false"
                    show-icon
                  />
                </div>
              </div>
              
              <!-- Observation result -->
              <div v-else-if="step.type === 'observation'" class="observation-content">
                <div class="observation-summary">
                  {{ step.content }}
                </div>
              </div>
              
              <!-- Generic content -->
              <div v-else class="generic-content">
                <div v-if="typeof step.content === 'string'">
                  {{ step.content }}
                </div>
                <div v-else>
                  <pre><code>{{ JSON.stringify(step.content, null, 2) }}</code></pre>
                </div>
              </div>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
    </div>

    <!-- Final result -->
    <div v-if="reasoning.result" class="final-result">
      <div class="result-header">
        <el-icon><Trophy /></el-icon>
        <h4>{{ $t('chat.realtimeReasoning.finalResult') }}</h4>
        <el-tag 
          :type="reasoning.result.final ? 'success' : 'warning'" 
          size="small"
        >
          {{ reasoning.result.final ? $t('chat.realtimeReasoning.completed') : $t('chat.realtimeReasoning.notCompleted') }}
        </el-tag>
      </div>
      
      <div class="result-content">
        <div v-if="reasoning.result.answer" class="final-answer">
          <h5>{{ $t('chat.realtimeReasoning.answer') }}</h5>
          <p>{{ reasoning.result.answer }}</p>
        </div>
        
        <div v-if="reasoning.result.thought" class="final-thought">
          <h5>{{ $t('chat.realtimeReasoning.finalThought') }}</h5>
          <p>{{ reasoning.result.thought }}</p>
        </div>
        
        <div v-if="reasoning.result.reason && !reasoning.result.final" class="incomplete-reason">
          <h5>{{ $t('chat.realtimeReasoning.incompleteReason') }}</h5>
          <p>{{ getIncompleteReason(reasoning.result.reason) }}</p>
        </div>
      </div>
    </div>

    <!-- Action buttons -->
    <div class="trace-actions">
      <el-button 
        size="small" 
        @click="exportTrace"
        :icon="Download"
      >
        {{ $t('chat.realtimeReasoning.exportTrace') }}
      </el-button>
      <el-button 
        size="small" 
        @click="copyTrace"
        :icon="DocumentCopy"
      >
        {{ $t('chat.realtimeReasoning.copyTrace') }}
      </el-button>
      <el-button 
        v-if="reasoning.result && reasoning.result.final"  
        size="small" 
        type="primary"
        @click="continueReasoning"
        :icon="ArrowRight"
      >
        {{ $t('chat.realtimeReasoning.continueReasoning') }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import {
  Cpu,
  Trophy,
  CircleCheckFilled,
  CircleCloseFilled,
  Download,
  DocumentCopy,
  ArrowRight,
  View,
  Setting,
  Search,
  Tools
} from '@element-plus/icons-vue'
import { useClipboard } from '@/utils/UseClipboardHook.js'

// Internationalization
const { t } = useI18n()

// Props
const props = defineProps({
  reasoning: {
    type: Object,
    required: true,
    default: () => ({})
  }
})

// Emits
const emit = defineEmits(['continue-reasoning', 'close'])

// Hooks
const { copyToClipboard } = useClipboard()

// Computed properties
const toolCallCount = computed(() => {
  return props.reasoning.trace?.filter(step => 
    step.type === 'action_result' && step.content.success
  ).length || 0
})

// Methods
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString()
}

const getStepType = (stepType) => {
  const typeMap = {
    thought: 'primary',
    action_plan: 'warning',
    action_result: 'success',
    observation: 'info'
  }
  return typeMap[stepType] || 'primary'
}

const getStepIcon = (stepType) => {
  const iconMap = {
    thought: View,
    action_plan: Setting,
    action_result: Tools,
    observation: Search
  }
  return iconMap[stepType] || View
}

const getStepTitle = (stepType) => {
  const titleMap = {
    thought: t('chat.realtimeReasoning.thoughtPhase'),
    action_plan: t('chat.realtimeReasoning.actionPlan'),
    action_result: t('chat.realtimeReasoning.actionResult'),
    observation: t('chat.realtimeReasoning.observationPhase')
  }
  return titleMap[stepType] || t('chat.realtimeReasoning.unknownStep')
}

const getStepTagType = (stepType) => {
  const tagTypeMap = {
    thought: 'primary',
    action_plan: 'warning',
    action_result: 'success',
    observation: 'info'
  }
  return tagTypeMap[stepType] || ''
}

const getIncompleteReason = (reason) => {
  const reasonMap = {
    max_iterations_reached: t('chat.realtimeReasoning.maxIterationsReached'),
    no_more_actions: t('chat.realtimeReasoning.noMoreActions'),
    timeout: t('chat.realtimeReasoning.timeout'),
    error: t('chat.realtimeReasoning.error')
  }
  return reasonMap[reason] || reason
}

const exportTrace = () => {
  const traceData = {
    reasoning: props.reasoning,
    exportTime: new Date().toISOString(),
    summary: {
      totalSteps: props.reasoning.trace?.length || 0,
      iterations: props.reasoning.iterations,
      toolCalls: toolCallCount.value,
      completed: props.reasoning.result?.final || false
    }
  }
  
  const blob = new Blob([JSON.stringify(traceData, null, 2)], { 
    type: 'application/json' 
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `reasoning-trace-${Date.now()}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  
  ElMessage.success(t('chat.realtimeReasoning.reasoningTraceExported'))
}

const copyTrace = () => {
  let traceText = `# ${t('chat.realtimeReasoning.reactReasoningTrace')}\n\n`
  traceText += `${t('chat.realtimeReasoning.totalIterations')} ${props.reasoning.iterations}\n`
  traceText += `${t('chat.realtimeReasoning.totalStepsCount')} ${props.reasoning.trace?.length || 0}\n`
  traceText += `${t('chat.realtimeReasoning.toolCallsCount')} ${toolCallCount.value}\n\n`
  
  if (props.reasoning.trace) {
    props.reasoning.trace.forEach((step, index) => {
      traceText += `## ${t('chat.realtimeReasoning.stepNumber', { step: index + 1, title: getStepTitle(step.type) })}\n`
      traceText += `${t('chat.realtimeReasoning.time')} ${formatTime(step.timestamp)}\n`
      
      if (typeof step.content === 'string') {
        traceText += `${t('chat.realtimeReasoning.content')} ${step.content}\n\n`
      } else {
        traceText += `${t('chat.realtimeReasoning.content')} ${JSON.stringify(step.content, null, 2)}\n\n`
      }
    })
  }
  
  if (props.reasoning.result) {
    traceText += `## ${t('chat.realtimeReasoning.finalResultStatus')}\n`
    traceText += `${t('chat.realtimeReasoning.status')} ${props.reasoning.result.final ? t('chat.realtimeReasoning.completed') : t('chat.realtimeReasoning.notCompleted')}\n`
    if (props.reasoning.result.answer) {
      traceText += `${t('chat.realtimeReasoning.finalAnswer')} ${props.reasoning.result.answer}\n`
    }
    if (props.reasoning.result.thought) {
      traceText += `${t('chat.realtimeReasoning.finalThoughtLabel')} ${props.reasoning.result.thought}\n`
    }
  }
  
  copyToClipboard(traceText)
}

const continueReasoning = () => {
  emit('continue-reasoning', props.reasoning)
}
</script>

<style scoped lang="scss">
.reasoning-trace {
  .trace-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--el-border-color);
    
    .header-info {
      display: flex;
      align-items: center;
      gap: 12px;
      
      .el-icon {
        font-size: 20px;
        color: var(--el-color-primary);
      }
      
      h4 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
      }
    }
    
    .trace-stats {
      display: flex;
      gap: 16px;
      
      .stat-item {
        font-size: 12px;
        color: var(--el-text-color-secondary);
        
        strong {
          color: var(--el-text-color-primary);
        }
      }
    }
  }
  
  .reasoning-timeline {
    margin-bottom: 24px;
    
    .step-content {
      background: var(--el-bg-color);
      border-radius: 8px;
      padding: 16px;
      margin-left: 12px;
      border: 1px solid var(--el-border-color);
      
      &.step-thought {
        border-left: 4px solid var(--el-color-primary);
      }
      
      &.step-action_plan {
        border-left: 4px solid var(--el-color-warning);
      }
      
      &.step-action_result {
        border-left: 4px solid var(--el-color-success);
      }
      
      &.step-observation {
        border-left: 4px solid var(--el-color-info);
      }
      
      .step-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        
        h5 {
          margin: 0;
          font-size: 14px;
          font-weight: 600;
          color: var(--el-text-color-primary);
        }
      }
      
      .step-body {
        .thought-content p,
        .observation-content .observation-summary {
          margin: 0;
          line-height: 1.6;
          color: var(--el-text-color-regular);
        }
        
        .action-plan-content {
          .plan-summary,
          .tool-info {
            margin-bottom: 8px;
            
            strong {
              color: var(--el-text-color-primary);
            }
          }
          
          .parameters,
          .reasoning {
            margin-bottom: 12px;
            
            strong {
              display: block;
              margin-bottom: 4px;
              color: var(--el-text-color-primary);
            }
            
            pre {
              background: var(--el-fill-color-lighter);
              padding: 8px;
              border-radius: 4px;
              font-size: 12px;
              margin: 0;
              overflow-x: auto;
            }
          }
        }
        
        .action-result-content {
          .success-result,
          .error-result {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
            
            .success-icon {
              color: var(--el-color-success);
            }
            
            .error-icon {
              color: var(--el-color-danger);
            }
          }
          
          .result-data {
            background: var(--el-fill-color-light);
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 8px;
            
            pre {
              margin: 0;
              font-size: 12px;
              overflow-x: auto;
            }
          }
          
          .error-info {
            margin-top: 8px;
          }
        }
        
        .generic-content {
          pre {
            background: var(--el-fill-color-lighter);
            padding: 12px;
            border-radius: 6px;
            font-size: 12px;
            margin: 0;
            overflow-x: auto;
          }
        }
      }
    }
  }
  
  .final-result {
    background: var(--el-fill-color-light);
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
    
    .result-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
      
      .el-icon {
        font-size: 20px;
        color: var(--el-color-warning);
      }
      
      h4 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
      }
    }
    
    .result-content {
      .final-answer,
      .final-thought,
      .incomplete-reason {
        margin-bottom: 16px;
        
        &:last-child {
          margin-bottom: 0;
        }
        
        h5 {
          margin: 0 0 8px 0;
          font-size: 14px;
          font-weight: 600;
          color: var(--el-text-color-primary);
        }
        
        p {
          margin: 0;
          line-height: 1.6;
          color: var(--el-text-color-regular);
        }
      }
      
      .incomplete-reason {
        p {
          color: var(--el-color-warning);
        }
      }
    }
  }
  
  .trace-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    padding-top: 16px;
    border-top: 1px solid var(--el-border-color);
  }
}

// Timeline style overrides
:deep(.el-timeline-item__timestamp) {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

:deep(.el-timeline-item__wrapper) {
  padding-left: 20px;
}
</style> 