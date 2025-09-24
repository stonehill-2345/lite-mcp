<template>
  <div class="prompt-config">
    <el-form 
      ref="formRef"
      :model="formData"
      label-width="150px"
      class="config-form"
    >
      <!-- ReAct System Prompt -->
      <el-form-item :label="$t('config.promptConfig.reactSystemPrompt')">
        <el-input
          v-model="formData.reactSystemPrompt"
          type="textarea"
          :rows="12"
          :placeholder="$t('config.promptConfig.reactSystemPromptPlaceholder')"
          show-word-limit
          maxlength="8000"
          @input="handleFormChange"
        />
        <div class="form-help">
          {{ $t('config.promptConfig.reactSystemPromptHelp') }}
        </div>
      </el-form-item>

      <!-- Preset Templates -->
      <el-form-item :label="$t('config.promptConfig.presetTemplates')">
        <el-select 
          v-model="selectedTemplate"
          :placeholder="$t('config.promptConfig.selectPresetTemplate')"
          @change="loadTemplate"
          clearable
        >
          <el-option 
            v-for="template in availableTemplates"
            :key="template.key"
            :label="template.name"
            :value="template.key"
          >
            <span>{{ template.name }}</span>
            <span class="template-description">{{ template.description }}</span>
          </el-option>
        </el-select>
        <div class="form-help">
          {{ $t('config.promptConfig.selectPresetTemplateHelp') }}
        </div>
      </el-form-item>

      <!-- Template Variables -->
      <el-collapse class="template-variables">
        <el-collapse-item :title="$t('config.promptConfig.availableVariables')">
          <div class="variables-section">
            <h4>{{ $t('config.promptConfig.availableVariablesTitle') }}</h4>
            <div class="variables-list">
              <div class="variable-item">
                <code>{{`{mcpTools}`}}</code>
                <span>{{ $t('config.promptConfig.mcpToolsVariable') }}</span>
              </div>
            </div>
            
            <h4>{{ $t('config.promptConfig.requiredReactFormatTags') }}</h4>
            <div class="format-list">
              <div class="format-item">
                <code>&lt;REASONING&gt;</code>
                <span>{{ $t('config.promptConfig.reasoningTag') }}</span>
              </div>
              <div class="format-item">
                <code>&lt;ACTION&gt;</code>
                <span>{{ $t('config.promptConfig.actionTag') }}</span>
              </div>
              <div class="format-item">
                <code>&lt;FINAL_ANSWER&gt;</code>
                <span>{{ $t('config.promptConfig.finalAnswerTag') }}</span>
              </div>
            </div>
            
            <h4>{{ $t('config.promptConfig.actionFormatExample') }}</h4>
            <pre class="action-example"><code>{
  "tools": [
    {
      "tool": t('config.promptConfig.toolNameExample'),
      "parameters": {
        "parameterName": t('config.promptConfig.parameterValueExample')
      }
    }
  ]
}</code></pre>
          </div>
        </el-collapse-item>
      </el-collapse>

      <!-- Action Buttons -->
      <el-form-item>
        <el-button type="primary" @click="validatePrompts">{{ $t('config.promptConfig.validatePrompts') }}</el-button>
        <el-button @click="resetToDefaults">{{ $t('config.promptConfig.resetToDefaults') }}</el-button>
        <el-button @click="exportPrompts">{{ $t('config.promptConfig.exportConfig') }}</el-button>
        <el-button @click="importPrompts">{{ $t('config.promptConfig.importConfig') }}</el-button>
      </el-form-item>
    </el-form>

    <!-- Import Dialog -->
    <el-dialog 
      v-model="importDialogVisible" 
      :title="$t('config.promptConfig.importPromptConfig')"
      width="50%"
    >
      <el-input
        v-model="importText"
        type="textarea"
        :rows="10"
        :placeholder="$t('config.promptConfig.pasteJsonConfig')"
      />
      <template #footer>
        <el-button @click="importDialogVisible = false">{{ $t('config.promptConfig.cancel') }}</el-button>
        <el-button type="primary" @click="handleImport">{{ $t('config.promptConfig.import') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { PromptTemplates } from '@/services/config/defaultPrompts.js'

// Internationalization
const { t } = useI18n()

// Props
const props = defineProps({
  customPrompts: {
    type: Object,
    default: () => ({})
  }
})

// Emits
const emit = defineEmits(['prompts-change'])

// Reactive data
const formRef = ref()
const selectedTemplate = ref('')
const importDialogVisible = ref(false)
const importText = ref('')

// Initialize form data, ensure default values are displayed correctly
const initFormData = () => {
  const defaultPrompts = {
    reactSystemPrompt: PromptTemplates.buildReActSystemPrompt([], [], false) || ''
  }
  
  // Merge default values and custom values
  return {
    ...defaultPrompts,
    ...props.customPrompts
  }
}

const formData = ref(initFormData())

// Available templates
const availableTemplates = [
  {
    key: 'default',
    name: t('config.promptConfig.defaultReactAssistant'),
    description: t('config.promptConfig.defaultReactAssistantDesc'),
    prompts: {
      reactSystemPrompt: PromptTemplates.buildReActSystemPrompt([], [], false)
    }
  },

  {
    key: 'developer',
    name: t('config.promptConfig.developerReactAssistant'),
    description: t('config.promptConfig.developerReactAssistantDesc'),
    prompts: {
      reactSystemPrompt: PromptTemplates.buildReActDeveloperPrompt([], [], false)
    }
  },

  {
    key: 'tester',
    name: t('config.promptConfig.testerReactAssistant'),
    description: t('config.promptConfig.testerReactAssistantDesc'),
    prompts: {
      reactSystemPrompt: PromptTemplates.buildReActTesterPrompt([], [], false)
    }
  },

]

// Methods
const loadTemplate = (templateKey) => {
  const template = availableTemplates.find(t => t.key === templateKey)
  if (template) {
    formData.value = { ...formData.value, ...template.prompts }
    ElMessage.success(t('config.promptConfig.templateLoaded', { name: template.name }))
    handleFormChange()
  }
}

const validatePrompts = () => {
  const issues = []
  
  if (!formData.value.reactSystemPrompt.trim()) {
    issues.push(t('config.promptConfig.reactSystemPromptCannotBeEmpty'))
  }
  
  // Check required tags in ReAct prompt
  const content = formData.value.reactSystemPrompt
  if (!content.includes('<REASONING>')) {
    issues.push(t('config.promptConfig.missingReasoningTag'))
  }
  if (!content.includes('<ACTION>')) {
    issues.push(t('config.promptConfig.missingActionTag'))
  }
  if (!content.includes('<FINAL_ANSWER>')) {
    issues.push(t('config.promptConfig.missingFinalAnswerTag'))
  }
  if (!content.includes('{mcpTools}')) {
    issues.push(t('config.promptConfig.missingMcpToolsVariable'))
  }
  
  if (issues.length > 0) {
    ElMessage.error(t('config.promptConfig.promptValidationFailed', { issues: issues.join('\n') }))
  } else {
    ElMessage.success(t('config.promptConfig.reactSystemPromptValidationPassed'))
  }
}

const resetToDefaults = async () => {
  try {
    await ElMessageBox.confirm(
      t('config.promptConfig.confirmReset'),
      t('config.promptConfig.resetConfirmation'),
      {
        confirmButtonText: t('config.promptConfig.confirm'),
        cancelButtonText: t('config.promptConfig.cancel'),
        type: 'warning'
      }
    )
    
    formData.value = {
      reactSystemPrompt: PromptTemplates.buildReActSystemPrompt([], [], false) || ''
    }
    
    selectedTemplate.value = 'default'
    ElMessage.success(t('config.promptConfig.hasResetToDefaults'))
    handleFormChange()
    
  } catch (error) {
    // User cancelled operation
  }
}

const exportPrompts = () => {
  const config = {
    prompts: formData.value,
    exportTime: new Date().toISOString(),
    version: '1.0'
  }
  
  const blob = new Blob([JSON.stringify(config, null, 2)], { 
    type: 'application/json' 
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `prompt-config-${Date.now()}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  
  ElMessage.success(t('config.promptConfig.promptConfigExported'))
}

const importPrompts = () => {
  importText.value = ''
  importDialogVisible.value = true
}

const handleImport = () => {
  try {
    const config = JSON.parse(importText.value)
    
    if (config.prompts) {
      formData.value = { ...formData.value, ...config.prompts }
      ElMessage.success(t('config.promptConfig.promptConfigImported'))
      handleFormChange()
    } else {
      ElMessage.error(t('config.promptConfig.invalidConfigFormat'))
    }
    
    importDialogVisible.value = false
    
  } catch (error) {
    ElMessage.error(t('config.promptConfig.importFailed', { error: error.message }))
  }
}

const emitChange = () => {
  const prompts = { ...formData.value }
  emit('prompts-change', prompts)
}

// Flag to prevent recursive updates
let isUpdatingFromProps = false

// Watch external changes - only update when props actually change
watch(() => props.customPrompts, (newPrompts) => {
  if (!isUpdatingFromProps && newPrompts) {
    isUpdatingFromProps = true
    // Only update properties with values, keep default values
    const updatedData = { ...formData.value }
    if (newPrompts.reactSystemPrompt !== undefined && 
        newPrompts.reactSystemPrompt !== formData.value.reactSystemPrompt) {
      updatedData.reactSystemPrompt = newPrompts.reactSystemPrompt
    }
    formData.value = updatedData
    setTimeout(() => {
      isUpdatingFromProps = false
    }, 50)
  }
}, { deep: true, immediate: true }) // Changed to immediate: true to respond to initial values immediately

// Method to manually trigger change events
const handleFormChange = () => {
  if (!isUpdatingFromProps) {
    emitChange()
  }
}
</script>

<style scoped lang="scss">
.prompt-config {
  .config-form {
    max-width: 800px;
    
    .form-help {
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-top: 4px;
      line-height: 1.4;
    }
    
    .template-description {
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-left: 8px;
    }
    
    .template-variables {
      margin-top: 16px;
      
      .variables-section {
        h4 {
          margin: 16px 0 8px 0;
          color: var(--el-text-color-primary);
          font-size: 14px;
          font-weight: 600;
          
          &:first-child {
            margin-top: 0;
          }
        }
        
        .variables-list,
        .format-list {
          .variable-item,
          .format-item {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
            
            code {
              background: var(--el-fill-color-light);
              padding: 2px 6px;
              border-radius: 4px;
              font-size: 12px;
              margin-right: 8px;
              min-width: 150px;
              font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            }
            
            span {
              color: var(--el-text-color-secondary);
              font-size: 12px;
            }
          }
        }
        
        .action-example {
          background: var(--el-fill-color-extra-light);
          border: 1px solid var(--el-border-color-light);
          border-radius: 6px;
          padding: 12px;
          margin: 8px 0;
          
          code {
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 12px;
            line-height: 1.4;
            color: var(--el-text-color-primary);
          }
        }
      }
    }
  }
}
</style> 