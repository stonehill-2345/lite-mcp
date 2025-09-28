<template>
  <div class="mcp-tools-panel">
    <div class="panel-header">
      <h3>{{ t('mcp.toolsPanel.availableTools', { count: tools.length }) }}</h3>
      <el-button 
        :icon="Refresh" 
        @click="$emit('refresh-tools')"
        size="small"
      >
        {{ t('mcp.toolsPanel.refreshTools') }}
      </el-button>
    </div>

    <div class="tools-grid">
      <div 
        v-for="tool in tools" 
        :key="tool.name"
        class="tool-card"
        @click="selectTool(tool)"
      >
        <div class="tool-header">
          <div class="tool-name">{{ tool.name }}</div>
          <el-button 
            :icon="VideoPlay" 
            size="small"
            type="primary"
            @click.stop="showToolDialog(tool)"
          >
            {{ t('mcp.toolsPanel.execute') }}
          </el-button>
        </div>
        
        <div class="tool-description">
          {{ tool.description || t('mcp.toolsPanel.noDescription') }}
        </div>
        
        <div class="tool-schema" v-if="tool.inputSchema">
          <div class="schema-title">{{ t('mcp.toolsPanel.parameters') }}:</div>
          <div class="schema-properties">
            <div 
              v-for="(prop, propName) in tool.inputSchema.properties" 
              :key="propName"
              class="schema-prop"
            >
              <span class="prop-name">{{ propName }}</span>
              <span class="prop-type">{{ prop.type }}</span>
              <span 
                v-if="tool.inputSchema.required?.includes(propName)" 
                class="prop-required"
              >
                {{ t('mcp.toolsPanel.required') }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="tools.length === 0" class="empty-state">
      <el-empty :description="t('mcp.toolsPanel.noTools')" />
    </div>

    <!-- Tool execution dialog -->
    <el-dialog
      v-model="toolDialogVisible"
      :title="t('mcp.toolsPanel.executeTool', { name: selectedTool?.name })"
      width="600px"
      :close-on-click-modal="false"
    >
      <div v-if="selectedTool" class="tool-execute-form">
        <div class="tool-info">
          <p><strong>{{ t('mcp.toolsPanel.description') }}:</strong> {{ selectedTool.description || t('mcp.toolsPanel.noDescription') }}</p>
        </div>

        <el-form 
          ref="toolFormRef"
          :model="toolForm"
          label-width="120px"
          @submit.prevent
        >
          <div v-if="selectedTool.inputSchema?.properties">
            <el-form-item 
              v-for="(prop, propName) in selectedTool.inputSchema.properties"
              :key="propName"
              :label="propName"
              :prop="propName"
              :rules="getFieldRules(propName, prop)"
            >
              <!-- String type -->
              <el-input
                v-if="prop.type === 'string'"
                v-model="toolForm[propName]"
                :placeholder="prop.description || `Enter ${propName}`"
                :type="prop.format === 'password' ? 'password' : 'text'"
              />
              
              <!-- Number type -->
              <el-input-number
                v-else-if="prop.type === 'number' || prop.type === 'integer'"
                v-model="toolForm[propName]"
                :placeholder="prop.description || `Enter ${propName}`"
                :min="prop.minimum"
                :max="prop.maximum"
                :step="prop.type === 'integer' ? 1 : 0.1"
                style="width: 100%"
              />
              
              <!-- Boolean type -->
              <el-switch
                v-else-if="prop.type === 'boolean'"
                v-model="toolForm[propName]"
              />
              
              <!-- Enum type -->
              <el-select
                v-else-if="prop.enum"
                v-model="toolForm[propName]"
                :placeholder="prop.description || `Select ${propName}`"
                style="width: 100%"
              >
                <el-option
                  v-for="option in prop.enum"
                  :key="option"
                  :label="option"
                  :value="option"
                />
              </el-select>
              
              <!-- Array type -->
              <div v-else-if="prop.type === 'array'" class="array-input">
                <div 
                  v-for="(item, index) in (toolForm[propName] || [])"
                  :key="index"
                  class="array-item"
                >
                  <el-input
                    v-model="toolForm[propName][index]"
                    :placeholder="`${propName}[${index}]`"
                  />
                  <el-button
                    :icon="Delete"
                    size="small"
                    type="danger"
                    @click="removeArrayItem(propName, index)"
                  />
                </div>
                <el-button
                  :icon="Plus"
                  size="small"
                  @click="addArrayItem(propName)"
                >
                  {{ t('mcp.toolsPanel.addItem', { name: propName }) }}
                </el-button>
              </div>
              
              <!-- Object type or other -->
              <el-input
                v-else
                v-model="toolForm[propName]"
                type="textarea"
                :placeholder="prop.description || `Enter ${propName} (JSON format)`"
                :rows="3"
              />
              
              <div v-if="prop.description" class="field-description">
                {{ prop.description }}
              </div>
            </el-form-item>
          </div>
          
          <div v-else class="no-params">
            {{ t('mcp.toolsPanel.noParams') }}
          </div>
        </el-form>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="toolDialogVisible = false">
            {{ t('common.cancel') }}
          </el-button>
          <el-button 
            type="primary" 
            @click="executeTool"
            :loading="executing"
          >
            {{ t('mcp.toolsPanel.executeToolButton') }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- Execution result dialog -->
    <el-dialog
      v-model="resultDialogVisible"
      :title="t('mcp.toolsPanel.executionResult')"
      width="700px"
    >
      <div class="execution-result">
        <div class="result-header">
          <span class="tool-name">{{ executionResult?.toolName }}</span>
          <el-tag 
            :type="executionResult?.success ? 'success' : 'danger'"
          >
            {{ executionResult?.success ? t('common.success') : t('common.failed') }}
          </el-tag>
        </div>
        
        <div class="result-content">
          <el-tabs>
            <el-tab-pane :label="t('mcp.toolsPanel.executionResult')" name="result">
              <pre class="result-data">{{ formatResult(executionResult?.result) }}</pre>
            </el-tab-pane>
            <el-tab-pane :label="t('mcp.toolsPanel.inputParameters')" name="input">
              <pre class="result-data">{{ JSON.stringify(executionResult?.input, null, 2) }}</pre>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>

      <template #footer>
        <el-button @click="resultDialogVisible = false">
          {{ t('common.close') }}
        </el-button>
        <el-button 
          type="primary"
          @click="copyResult"
        >
          {{ t('mcp.toolsPanel.copyResult') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { Refresh, VideoPlay, Plus, Delete } from '@element-plus/icons-vue'
import { useClipboard } from '@/utils/UseClipboardHook'

// Multi-language support
const { t } = useI18n()

// Props & Emits
const props = defineProps({
  tools: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['tool-called', 'refresh-tools'])

// Hooks
const { copyToClipboard } = useClipboard()

// Reactive data
const toolDialogVisible = ref(false)
const resultDialogVisible = ref(false)
const executing = ref(false)
const selectedTool = ref(null)
const toolForm = ref({})
const toolFormRef = ref(null)
const executionResult = ref(null)

// Methods
const selectTool = (tool) => {
  // Reserved: may be used for tool detail viewing
}

const showToolDialog = (tool) => {
  selectedTool.value = tool
  toolForm.value = {}
  
  // Initialize form default values
  if (tool.inputSchema?.properties) {
    Object.keys(tool.inputSchema.properties).forEach(propName => {
      const prop = tool.inputSchema.properties[propName]
      
      if (prop.type === 'array') {
        toolForm.value[propName] = []
      } else if (prop.type === 'boolean') {
        toolForm.value[propName] = false
      } else if (prop.default !== undefined) {
        toolForm.value[propName] = prop.default
      }
    })
  }
  
  toolDialogVisible.value = true
}

const getFieldRules = (propName, prop) => {
  const rules = []
  
  if (selectedTool.value?.inputSchema?.required?.includes(propName)) {
    rules.push({
      required: true,
      message: t('mcp.toolsPanel.fieldRequired', { field: propName }),
      trigger: 'blur'
    })
  }
  
  if (prop.type === 'string' && prop.minLength) {
    rules.push({
      min: prop.minLength,
      message: t('mcp.toolsPanel.fieldMinLength', { field: propName, min: prop.minLength }),
      trigger: 'blur'
    })
  }
  
  if (prop.type === 'string' && prop.maxLength) {
    rules.push({
      max: prop.maxLength,
      message: t('mcp.toolsPanel.fieldMaxLength', { field: propName, max: prop.maxLength }),
      trigger: 'blur'
    })
  }
  
  return rules
}

const addArrayItem = (propName) => {
  if (!toolForm.value[propName]) {
    toolForm.value[propName] = []
  }
  toolForm.value[propName].push('')
}

const removeArrayItem = (propName, index) => {
  if (toolForm.value[propName]) {
    toolForm.value[propName].splice(index, 1)
  }
}

const executeTool = async () => {
  try {
    if (toolFormRef.value) {
      await toolFormRef.value.validate()
    }
    
    executing.value = true
    
    // Process form data
    const processedForm = {}
    Object.keys(toolForm.value).forEach(key => {
      let value = toolForm.value[key]
      
      // Handle empty arrays
      if (Array.isArray(value) && value.length === 0) {
        return // Skip empty arrays
      }
      
      // Try to parse JSON strings
      if (typeof value === 'string' && value.trim()) {
        try {
          // If it's an object type field, try to parse JSON
          const prop = selectedTool.value.inputSchema?.properties?.[key]
          if (prop?.type === 'object') {
            value = JSON.parse(value)
          }
        } catch {
          // Parse failed, keep original string
        }
      }
      
      if (value !== undefined && value !== null && value !== '') {
        processedForm[key] = value
      }
    })
    
    // Simulate tool execution result
    const result = await simulateToolExecution(selectedTool.value.name, processedForm)
    
    executionResult.value = {
      toolName: selectedTool.value.name,
      input: processedForm,
      result: result,
      success: true,
      timestamp: new Date()
    }
    
    toolDialogVisible.value = false
    resultDialogVisible.value = true
    
    emit('tool-called', {
      toolName: selectedTool.value.name,
      input: processedForm,
      result: result
    })
    
    ElMessage.success(t('mcp.toolsPanel.executionSuccess'))
  } catch (error) {
    executionResult.value = {
      toolName: selectedTool.value?.name,
      input: toolForm.value,
      result: { error: error.message },
      success: false,
      timestamp: new Date()
    }
    
    toolDialogVisible.value = false
    resultDialogVisible.value = true
    
    ElMessage.error(t('mcp.toolsPanel.executionFailed', { error: error.message }))
  } finally {
    executing.value = false
  }
}

const formatResult = (result) => {
  if (typeof result === 'object') {
    return JSON.stringify(result, null, 2)
  }
  return String(result)
}

const copyResult = () => {
  const resultText = formatResult(executionResult.value?.result)
  copyToClipboard(resultText)
}

const simulateToolExecution = async (toolName, params) => {
  // Simulate tool execution delay
  await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000))
  
  // Simulate execution results for different tools
  const mockResults = {
    default: {
      success: true,
      message: `Tool ${toolName} executed successfully`,
      data: params,
      timestamp: new Date().toISOString()
    }
  }
  
  return mockResults[toolName] || mockResults.default
}
</script>

<style scoped lang="scss">
.mcp-tools-panel {
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }
  }
  
  .tools-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
    
    .tool-card {
      border: 1px solid var(--el-border-color);
      border-radius: 8px;
      padding: 16px;
      cursor: pointer;
      transition: all 0.3s ease;
      background: var(--el-bg-color);
      
      &:hover {
        border-color: var(--el-color-primary);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      }
      
      .tool-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        
        .tool-name {
          font-weight: 600;
          font-size: 14px;
          color: var(--el-text-color-primary);
        }
      }
      
      .tool-description {
        color: var(--el-text-color-regular);
        font-size: 13px;
        margin-bottom: 12px;
        line-height: 1.4;
      }
      
      .tool-schema {
        .schema-title {
          font-size: 12px;
          font-weight: 600;
          color: var(--el-text-color-regular);
          margin-bottom: 8px;
        }
        
        .schema-properties {
          .schema-prop {
            display: flex;
            gap: 8px;
            margin-bottom: 4px;
            font-size: 12px;
            
            .prop-name {
              color: var(--el-color-primary);
              font-weight: 500;
            }
            
            .prop-type {
              color: var(--el-text-color-regular);
              background: var(--el-fill-color-light);
              padding: 1px 4px;
              border-radius: 3px;
            }
            
            .prop-required {
              color: var(--el-color-danger);
              font-size: 11px;
            }
          }
        }
      }
    }
  }
  
  .empty-state {
    text-align: center;
    padding: 60px 20px;
  }
}

.tool-execute-form {
  .tool-info {
    margin-bottom: 20px;
    padding: 12px;
    background: var(--el-fill-color-light);
    border-radius: 6px;
  }
  
  .field-description {
    font-size: 12px;
    color: var(--el-text-color-regular);
    margin-top: 4px;
  }
  
  .array-input {
    .array-item {
      display: flex;
      gap: 8px;
      margin-bottom: 8px;
    }
  }
  
  .no-params {
    text-align: center;
    color: var(--el-text-color-regular);
    padding: 20px;
  }
}

.execution-result {
  .result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    
    .tool-name {
      font-weight: 600;
      font-size: 16px;
    }
  }
  
  .result-content {
    .result-data {
      background: var(--el-fill-color-light);
      padding: 12px;
      border-radius: 6px;
      font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
      font-size: 13px;
      max-height: 400px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style> 