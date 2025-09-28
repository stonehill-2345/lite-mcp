<template>
  <div class="tool-confirmation-dialog">
    <!-- Confirmation header -->
    <div class="confirmation-header">
      <div class="header-content">
        <el-icon class="confirmation-icon"><Tools /></el-icon>
        <div class="header-text">
          <h3>{{ $t('chat.toolConfirmationDialog.toolExecutionConfirmation') }}</h3>
          <p>{{ $t('chat.toolConfirmationDialog.aiWantsToExecute') }}</p>
        </div>
      </div>
      <div class="countdown" v-if="timeoutSeconds > 0">
        <el-tag type="warning" size="small">
          {{ timeoutSeconds }}{{ $t('chat.toolConfirmationDialog.autoRejectIn') }}
        </el-tag>
      </div>
    </div>

    <!-- Tools list -->
    <div class="tools-list">
      <div 
        v-for="(tool, index) in pendingTools" 
        :key="index"
        class="tool-item"
        :class="{ 'selected': selectedTools.includes(index) }"
      >
                 <!-- Tool basic information -->
         <div class="tool-header">
           <el-checkbox 
             v-if="allowBatchConfirmation"
             :model-value="selectedTools.includes(index)"
             @change="toggleToolSelection(index)"
             class="tool-checkbox"
           />
          <div class="tool-info">
            <div class="tool-name">
              <el-icon><component :is="getToolIcon(tool.type)" /></el-icon>
              <span>{{ tool.toolName }}</span>
              <el-tag size="small" :type="getToolTypeColor(tool.type)">
                {{ getToolTypeName(tool.type) }}
              </el-tag>
            </div>
            <div class="tool-description">
              {{ getToolDescription(tool) }}
            </div>
          </div>
          <div class="tool-actions">
            <el-button
              size="small"
              @click="toggleToolDetails(index)"
              :icon="isToolExpanded(index) ? ArrowUp : ArrowDown"
              text
            >
              {{ isToolExpanded(index) ? $t('chat.toolConfirmationDialog.collapse') : $t('chat.toolConfirmationDialog.details') }}
            </el-button>
          </div>
        </div>

        <!-- Tool details (expandable) -->
        <el-collapse-transition>
          <div v-show="isToolExpanded(index)" class="tool-details">
            <!-- Execution plan -->
            <div class="detail-section">
              <h4>{{ $t('chat.toolConfirmationDialog.executionPlan') }}</h4>
              <div class="plan-content">
                <div class="plan-item">
                  <span class="plan-label">{{ $t('chat.toolConfirmationDialog.target') }}</span>
                  <span class="plan-value">{{ tool.reasoning || $t('chat.toolConfirmationDialog.executeToolOperation') }}</span>
                </div>
                <div class="plan-item" v-if="tool.sessionId">
                  <span class="plan-label">{{ $t('chat.toolConfirmationDialog.session') }}</span>
                  <span class="plan-value">{{ tool.sessionId }}</span>
                </div>
              </div>
            </div>

            <!-- Parameter list -->
            <div class="detail-section" v-if="tool.parameters && Object.keys(tool.parameters).length > 0">
              <h4>{{ $t('chat.toolConfirmationDialog.parameterList') }}</h4>
              <div class="parameters-list">
                <div 
                  v-for="(value, key) in tool.parameters"
                  :key="key"
                  class="parameter-item"
                >
                  <div class="param-header">
                    <span class="param-name">{{ key }}</span>
                    <span class="param-type">{{ getParameterType(value) }}</span>
                  </div>
                  <div class="param-value">
                    <el-input
                      v-if="isEditingParams"
                      v-model="editedParameters[index][key]"
                      size="small"
                      :placeholder="String(value)"
                    />
                    <pre v-else class="param-display">{{ formatParameterValue(value) }}</pre>
                  </div>
                </div>
              </div>
            </div>

            <!-- Security warning -->
            <div class="detail-section" v-if="getSecurityWarning(tool)">
              <h4>{{ $t('chat.toolConfirmationDialog.securityWarning') }}</h4>
              <el-alert
                :title="getSecurityWarning(tool)"
                type="warning"
                :closable="false"
                show-icon
              />
            </div>
          </div>
        </el-collapse-transition>
      </div>
    </div>

    <!-- Action buttons -->
    <div class="confirmation-actions">
      <div class="action-left">
        <el-button
          v-if="canEditParams"
          :type="isEditingParams ? 'primary' : 'default'"
          size="small"
          @click="toggleParamEditing"
          :icon="Edit"
        >
          {{ isEditingParams ? $t('chat.toolConfirmationDialog.finishEditing') : $t('chat.toolConfirmationDialog.editParameters') }}
        </el-button>
      </div>
      
      <div class="action-right">
        <el-button
          size="large"
          @click="handleReject"
          :icon="Close"
        >
          {{ $t('chat.toolConfirmationDialog.rejectExecution') }}
        </el-button>
        <el-button
          type="primary"
          size="large"
          @click="handleConfirm"
          :icon="Check"
          :disabled="allowBatchConfirmation && selectedTools.length === 0"
        >
          {{ $t('chat.toolConfirmationDialog.confirmExecution') }}
          <span v-if="allowBatchConfirmation && selectedTools.length > 0">
            ({{ selectedTools.length }}{{ $t('chat.toolConfirmationDialog.toolsSelected') }})
          </span>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Tools,
  ArrowUp,
  ArrowDown,
  Edit,
  Check,
  Close,
  Setting,
  Connection,
  Cpu
} from '@element-plus/icons-vue'

// Internationalization
const { t } = useI18n()

// Props
const props = defineProps({
  pendingTools: {
    type: Array,
    required: true
  },
  allowBatchConfirmation: {
    type: Boolean,
    default: true
  },
  timeoutDuration: {
    type: Number,
    default: 60
  }
})

// Emits
const emit = defineEmits(['confirm', 'reject', 'timeout'])

// Reactive data
const selectedTools = ref([])
const expandedTools = ref(new Set())
const isEditingParams = ref(false)
const editedParameters = ref({})
const timeoutSeconds = ref(props.timeoutDuration)
const timeoutTimer = ref(null)

// Computed properties
const canEditParams = computed(() => {
  return props.pendingTools.some(tool => 
    tool.parameters && Object.keys(tool.parameters).length > 0
  )
})

// Methods
const initializeEditedParameters = () => {
  editedParameters.value = {}
  props.pendingTools.forEach((tool, index) => {
    if (tool.parameters) {
      editedParameters.value[index] = { ...tool.parameters }
    }
  })
}

const toggleToolDetails = (index) => {
  if (expandedTools.value.has(index)) {
    expandedTools.value.delete(index)
  } else {
    expandedTools.value.add(index)
  }
}

const isToolExpanded = (index) => {
  return expandedTools.value.has(index)
}

const toggleParamEditing = () => {
  isEditingParams.value = !isEditingParams.value
  if (isEditingParams.value) {
    initializeEditedParameters()
  }
}

const toggleToolSelection = (index) => {
  const currentIndex = selectedTools.value.indexOf(index)
  if (currentIndex > -1) {
    // Already selected, remove
    selectedTools.value.splice(currentIndex, 1)
  } else {
    // Not selected, add
    selectedTools.value.push(index)
  }
}

const getToolIcon = (type) => {
  const iconMap = {
    'system': Setting,
    'mcp': Connection,
    'tool_call': Tools,
    'api': Cpu
  }
  return iconMap[type] || Tools
}

const getToolTypeColor = (type) => {
  const colorMap = {
    'system': 'success',
    'mcp': 'primary',
    'tool_call': 'info',
    'api': 'warning'
  }
  return colorMap[type] || 'info'
}

const getToolTypeName = (type) => {
  const nameMap = {
    'system': t('chat.toolConfirmationDialog.systemTool'),
    'mcp': t('chat.toolConfirmationDialog.mcpTool'),
    'tool_call': t('chat.toolConfirmationDialog.toolCall'),
    'api': t('chat.toolConfirmationDialog.apiCall')
  }
  return nameMap[type] || t('chat.toolConfirmationDialog.tool')
}

const getToolDescription = (tool) => {
  if (tool.description) return tool.description
  
  // Generate description based on tool name
  const descriptionMap = {
    'executeCommand': t('chat.toolConfirmationDialog.executeCommand'),
    'readFile': t('chat.toolConfirmationDialog.readFile'),
    'writeFile': t('chat.toolConfirmationDialog.writeFile'),
    'listDirectory': t('chat.toolConfirmationDialog.listDirectory'),
    'searchFiles': t('chat.toolConfirmationDialog.searchFiles'),
    'gitOperations': t('chat.toolConfirmationDialog.gitOperations'),
    'apiRequest': t('chat.toolConfirmationDialog.apiRequest'),
    'webScraping': t('chat.toolConfirmationDialog.webScraping'),
    'dataAnalysis': t('chat.toolConfirmationDialog.dataAnalysis')
  }
  
  return descriptionMap[tool.toolName] || t('chat.toolConfirmationDialog.executeOperation', { toolName: tool.toolName })
}

const getParameterType = (value) => {
  if (value === null || value === undefined) return t('chat.toolConfirmationDialog.null')
  if (Array.isArray(value)) return t('chat.toolConfirmationDialog.array')
  const typeMap = {
    'string': t('chat.toolConfirmationDialog.string'),
    'number': t('chat.toolConfirmationDialog.number'),
    'boolean': t('chat.toolConfirmationDialog.boolean'),
    'object': t('chat.toolConfirmationDialog.object')
  }
  return typeMap[typeof value] || typeof value
}

const formatParameterValue = (value) => {
  if (value === null || value === undefined) return t('chat.toolConfirmationDialog.null')
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }
  return String(value)
}

const getSecurityWarning = (tool) => {
  const warningMap = {
    'executeCommand': t('chat.toolConfirmationDialog.securityWarningExecuteCommand'),
    'writeFile': t('chat.toolConfirmationDialog.securityWarningWriteFile'),
    'deleteFile': t('chat.toolConfirmationDialog.securityWarningDeleteFile'),
    'apiRequest': t('chat.toolConfirmationDialog.securityWarningApiRequest'),
    'gitOperations': t('chat.toolConfirmationDialog.securityWarningGitOperations')
  }
  
  if (tool.parameters) {
    // Check for dangerous parameters
    const dangerousParams = ['rm', 'delete', 'drop', 'truncate', 'format']
    const paramString = JSON.stringify(tool.parameters).toLowerCase()
    if (dangerousParams.some(param => paramString.includes(param))) {
      return t('chat.toolConfirmationDialog.dangerousOperationDetected')
    }
  }
  
  return warningMap[tool.toolName] || null
}

const handleConfirm = () => {
  let toolsToExecute
  
  if (props.allowBatchConfirmation) {
    if (selectedTools.value.length === 0) return
    toolsToExecute = selectedTools.value.map(index => ({
      ...props.pendingTools[index],
      parameters: isEditingParams.value ? editedParameters.value[index] : props.pendingTools[index].parameters,
      index
    }))
  } else {
    toolsToExecute = props.pendingTools.map((tool, index) => ({
      ...tool,
      parameters: isEditingParams.value ? editedParameters.value[index] : tool.parameters,
      index
    }))
  }
  
  clearTimeout()
  emit('confirm', toolsToExecute)
}

const handleReject = () => {
  clearTimeout()
  emit('reject')
}

const handleTimeout = () => {
  emit('timeout')
}

const startCountdown = () => {
  if (timeoutTimer.value) clearInterval(timeoutTimer.value)
  
  timeoutTimer.value = setInterval(() => {
    timeoutSeconds.value--
    if (timeoutSeconds.value <= 0) {
      clearTimeout()
      handleTimeout()
    }
  }, 1000)
}

const clearTimeout = () => {
  if (timeoutTimer.value) {
    clearInterval(timeoutTimer.value)
    timeoutTimer.value = null
  }
}

// Watchers
watch(() => props.pendingTools, () => {
  // Reset state
  selectedTools.value = []
  expandedTools.value.clear()
  isEditingParams.value = false
  
  // If batch confirmation is not allowed, select all tools by default
  if (!props.allowBatchConfirmation) {
    selectedTools.value = props.pendingTools.map((_, index) => index)
  }
  
  // Initialize edited parameters
  initializeEditedParameters()
}, { immediate: true })

// Lifecycle
onMounted(() => {
  startCountdown()
})

onUnmounted(() => {
  clearTimeout()
})
</script>

<style scoped lang="scss">
.tool-confirmation-dialog {
  background: white;
  border-radius: 16px;
  border: 2px solid var(--el-color-warning-light-7);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  max-width: 800px;
  max-height: 70vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;

  .confirmation-header {
    padding: 20px 24px;
    background: var(--el-color-warning-light-9);
    border-bottom: 1px solid var(--el-color-warning-light-8);
    display: flex;
    justify-content: space-between;
    align-items: flex-start;

    .header-content {
      display: flex;
      gap: 12px;
      flex: 1;

      .confirmation-icon {
        font-size: 24px;
        color: var(--el-color-warning);
        margin-top: 2px;
      }

      .header-text {
        h3 {
          margin: 0 0 4px 0;
          color: var(--el-text-color-primary);
          font-size: 18px;
          font-weight: 600;
        }

        p {
          margin: 0;
          color: var(--el-text-color-regular);
          font-size: 14px;
        }
      }
    }

    .countdown {
      display: flex;
      align-items: center;
    }
  }

  .tools-list {
    flex: 1;
    overflow-y: auto;
    padding: 16px 24px;

    .tool-item {
      border: 1px solid var(--el-border-color-light);
      border-radius: 12px;
      margin-bottom: 12px;
      transition: all 0.3s ease;

      &:last-child {
        margin-bottom: 0;
      }

      &.selected {
        border-color: var(--el-color-primary-light-5);
        background: var(--el-color-primary-light-9);
      }

      &:hover {
        border-color: var(--el-color-primary-light-7);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      }

      .tool-header {
        padding: 16px 20px;
        display: flex;
        align-items: center;
        gap: 12px;

        .tool-checkbox {
          flex-shrink: 0;
        }

        .tool-info {
          flex: 1;

          .tool-name {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;

            .el-icon {
              font-size: 16px;
              color: var(--el-color-primary);
            }

            span {
              font-weight: 600;
              color: var(--el-text-color-primary);
            }
          }

          .tool-description {
            color: var(--el-text-color-regular);
            font-size: 13px;
          }
        }

        .tool-actions {
          flex-shrink: 0;
        }
      }

      .tool-details {
        padding: 0 20px 16px;
        border-top: 1px solid var(--el-border-color-lighter);

        .detail-section {
          margin-bottom: 16px;

          &:last-child {
            margin-bottom: 0;
          }

          h4 {
            margin: 0 0 8px 0;
            font-size: 14px;
            font-weight: 600;
            color: var(--el-text-color-primary);
          }

          .plan-content {
            .plan-item {
              display: flex;
              margin-bottom: 4px;

              .plan-label {
                min-width: 60px;
                color: var(--el-text-color-secondary);
                font-size: 13px;
              }

              .plan-value {
                color: var(--el-text-color-regular);
                font-size: 13px;
              }
            }
          }

          .parameters-list {
            .parameter-item {
              margin-bottom: 12px;
              padding: 12px;
              background: var(--el-fill-color-extra-light);
              border-radius: 8px;

              &:last-child {
                margin-bottom: 0;
              }

              .param-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 6px;

                .param-name {
                  font-weight: 500;
                  color: var(--el-text-color-primary);
                }

                .param-type {
                  font-size: 12px;
                  color: var(--el-text-color-secondary);
                  background: var(--el-fill-color-light);
                  padding: 2px 6px;
                  border-radius: 4px;
                }
              }

              .param-value {
                .param-display {
                  margin: 0;
                  padding: 8px;
                  background: var(--el-fill-color-light);
                  border-radius: 4px;
                  font-size: 12px;
                  color: var(--el-text-color-regular);
                  white-space: pre-wrap;
                  word-break: break-all;
                  max-height: 100px;
                  overflow-y: auto;
                }
              }
            }
          }
        }
      }
    }
  }

  .confirmation-actions {
    padding: 16px 24px;
    border-top: 1px solid var(--el-border-color-light);
    background: var(--el-fill-color-extra-light);
    display: flex;
    justify-content: space-between;
    align-items: center;

    .action-left {
      // Left button styles
    }

    .action-right {
      display: flex;
      gap: 12px;
    }
  }
}
</style> 