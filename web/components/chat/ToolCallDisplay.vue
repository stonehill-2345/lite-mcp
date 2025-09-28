<template>
  <div class="tool-call-display">
    <div class="tool-call-header">
      <div class="tool-info">
        <el-icon><Tools /></el-icon>
        <h4>{{ toolCall.toolName || t('chat.toolCallDisplay.unknownTool') }}</h4>
        <el-tag 
          :type="toolCall.success ? 'success' : 'danger'" 
          size="small"
        >
          {{ toolCall.success ? t('chat.toolCallDisplay.success') : t('chat.toolCallDisplay.failure') }}
        </el-tag>
      </div>
      <div class="tool-meta">
        <span class="execution-time">
          {{ formatExecutionTime(toolCall.executionTime) }}
        </span>
      </div>
    </div>

    <!-- Tool description -->
    <div v-if="toolCall.description" class="tool-description">
      <h5>{{ $t('chat.toolCallDisplay.toolDescription') }}</h5>
      <p>{{ toolCall.description }}</p>
    </div>

    <!-- Call parameters -->
    <div v-if="toolCall.parameters" class="call-parameters">
      <h5>{{ $t('chat.toolCallDisplay.callParameters') }}</h5>
      <div class="parameters-content">
        <pre><code>{{ JSON.stringify(toolCall.parameters, null, 2) }}</code></pre>
      </div>
    </div>

    <!-- Execution result -->
    <div class="call-result">
      <h5>{{ $t('chat.toolCallDisplay.executionResult') }}</h5>
      <div class="result-content" :class="{ 'error': !toolCall.success }">
        <div v-if="toolCall.success && toolCall.result">
          <!-- Success result -->
          <div v-if="typeof toolCall.result === 'string'" class="text-result">
            {{ toolCall.result }}
          </div>
          <div v-else class="json-result">
            <pre><code>{{ JSON.stringify(toolCall.result, null, 2) }}</code></pre>
          </div>
        </div>
        <div v-else-if="!toolCall.success" class="error-result">
          <el-alert
            :title="toolCall.error || t('chat.toolCallDisplay.toolCallFailed')"
            type="error"
            :description="toolCall.errorDetails"
            show-icon
            :closable="false"
          />
        </div>
        <div v-else class="no-result">
          <el-empty :description="$t('chat.toolCallDisplay.noExecutionResult')" :image-size="60" />
        </div>
      </div>
    </div>

    <!-- Tool session information -->
    <div v-if="toolCall.sessionInfo" class="session-info">
      <h5>{{ $t('chat.toolCallDisplay.sessionInfo') }}</h5>
      <div class="session-details">
        <div class="info-item">
          <span class="label">{{ $t('chat.toolCallDisplay.sessionId') }}</span>
          <span class="value">{{ toolCall.sessionInfo.sessionId }}</span>
        </div>
        <div class="info-item">
          <span class="label">{{ $t('chat.toolCallDisplay.server') }}</span>
          <span class="value">{{ toolCall.sessionInfo.serverName }}</span>
        </div>
        <div class="info-item">
          <span class="label">{{ $t('chat.toolCallDisplay.executionTime') }}</span>
          <span class="value">{{ formatTime(toolCall.timestamp) }}</span>
        </div>
      </div>
    </div>

    <!-- Action buttons -->
    <div class="tool-actions">
      <el-button 
        size="small" 
        @click="copyResult"
        :icon="DocumentCopy"
      >
        {{ $t('chat.toolCallDisplay.copyResult') }}
      </el-button>
      <el-button 
        v-if="toolCall.success && canRetry" 
        size="small" 
        type="primary"
        @click="retryTool"
        :icon="Refresh"
      >
        {{ $t('chat.toolCallDisplay.retryTool') }}
      </el-button>
      <el-button 
        size="small" 
        @click="exportDetails"
        :icon="Download"
      >
        {{ $t('chat.toolCallDisplay.exportDetails') }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { 
  Tools, 
  DocumentCopy, 
  Refresh, 
  Download 
} from '@element-plus/icons-vue'
import { useClipboard } from '@/utils/UseClipboardHook.js'

// Internationalization
const { t } = useI18n()

// Props
const props = defineProps({
  toolCall: {
    type: Object,
    required: true,
    default: () => ({})
  }
})

// Emits
const emit = defineEmits(['retry-tool', 'close'])

// Hooks
const { copyToClipboard } = useClipboard()

// Computed properties
const canRetry = computed(() => {
  return props.toolCall.parameters && props.toolCall.toolName
})

// Methods
const formatExecutionTime = (time) => {
  if (!time) return t('chat.toolCallDisplay.unknown')
  if (time < 1000) return `${time}${t('chat.toolCallDisplay.milliseconds')}`
  return `${(time / 1000).toFixed(2)}${t('chat.toolCallDisplay.seconds')}`
}

const formatTime = (timestamp) => {
  if (!timestamp) return t('chat.toolCallDisplay.unknown')
  return new Date(timestamp).toLocaleString()
}

const copyResult = () => {
  let contentToCopy = ''
  
  if (props.toolCall.success && props.toolCall.result) {
    if (typeof props.toolCall.result === 'string') {
      contentToCopy = props.toolCall.result
    } else {
      contentToCopy = JSON.stringify(props.toolCall.result, null, 2)
    }
  } else if (!props.toolCall.success) {
    contentToCopy = props.toolCall.error || t('chat.toolCallDisplay.toolCallFailed')
  }
  
  if (contentToCopy) {
    copyToClipboard(contentToCopy)
  } else {
    ElMessage.warning(t('chat.toolCallDisplay.noContentToCopy'))
  }
}

const retryTool = () => {
  emit('retry-tool', {
    toolName: props.toolCall.toolName,
    parameters: props.toolCall.parameters
  })
}

const exportDetails = () => {
  const details = {
    toolName: props.toolCall.toolName,
    description: props.toolCall.description,
    parameters: props.toolCall.parameters,
    result: props.toolCall.result,
    success: props.toolCall.success,
    error: props.toolCall.error,
    executionTime: props.toolCall.executionTime,
    timestamp: props.toolCall.timestamp,
    sessionInfo: props.toolCall.sessionInfo
  }
  
  const blob = new Blob([JSON.stringify(details, null, 2)], { 
    type: 'application/json' 
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `tool-call-${props.toolCall.toolName}-${Date.now()}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  
  ElMessage.success(t('chat.toolCallDisplay.toolCallDetailsExported'))
}
</script>

<style scoped lang="scss">
.tool-call-display {
  .tool-call-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--el-border-color);
    
    .tool-info {
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
    
    .tool-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .execution-time {
        font-size: 12px;
        color: var(--el-text-color-secondary);
        background: var(--el-fill-color-light);
        padding: 4px 8px;
        border-radius: 4px;
      }
    }
  }
  
  .tool-description {
    margin-bottom: 20px;
    
    h5 {
      margin: 0 0 8px 0;
      font-size: 14px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }
    
    p {
      margin: 0;
      color: var(--el-text-color-regular);
      line-height: 1.5;
    }
  }
  
  .call-parameters,
  .call-result {
    margin-bottom: 20px;
    
    h5 {
      margin: 0 0 12px 0;
      font-size: 14px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }
  }
  
  .parameters-content,
  .result-content {
    background: var(--el-fill-color-lighter);
    border-radius: 6px;
    padding: 16px;
    
    pre {
      margin: 0;
      font-family: 'Courier New', monospace;
      font-size: 12px;
      line-height: 1.4;
      white-space: pre-wrap;
      word-break: break-all;
    }
    
    &.error {
      background: var(--el-color-error-light-9);
    }
  }
  
  .text-result {
    font-family: inherit;
    line-height: 1.5;
    white-space: pre-wrap;
  }
  
  .json-result {
    font-size: 12px;
  }
  
  .error-result {
    .el-alert {
      --el-alert-bg-color: transparent;
      --el-alert-border-color: transparent;
    }
  }
  
  .session-info {
    margin-bottom: 20px;
    
    h5 {
      margin: 0 0 12px 0;
      font-size: 14px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }
    
    .session-details {
      background: var(--el-fill-color-light);
      padding: 12px 16px;
      border-radius: 6px;
      
      .info-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 4px 0;
        
        .label {
          font-weight: 500;
          color: var(--el-text-color-regular);
        }
        
        .value {
          font-family: 'Courier New', monospace;
          font-size: 12px;
          color: var(--el-text-color-primary);
        }
      }
    }
  }
  
  .tool-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    padding-top: 16px;
    border-top: 1px solid var(--el-border-color);
  }
}
</style> 