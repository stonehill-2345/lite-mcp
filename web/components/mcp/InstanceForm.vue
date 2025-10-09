<template>
  <el-dialog
    v-model="visible"
    :title="isEditMode ? t('mcp.instanceForm.editTitle') : t('mcp.instanceForm.createTitle')"
    width="90%"
    :before-close="handleClose"
    destroy-on-close
    class="instance-form-dialog"
  >
    <div class="form-container">
      <!-- Configuration input area -->
      <div class="config-input-section">
        <div class="section-header">
          <div class="header-content">
            <h3>{{ t('mcp.instanceForm.mcpConfigTitle') }}</h3>
            <p class="header-desc">{{ t('mcp.instanceForm.pasteConfigHint') }}</p>
          </div>
          <div class="support-info">
            <el-tag type="success" size="small" effect="light">
              <el-icon><Check /></el-icon>
              {{ t('mcp.instanceForm.supportedCommands') }}
            </el-tag>
          </div>
        </div>
        
        <div class="config-input-wrapper">
          <div class="input-label">
            <label>{{ t('mcp.instanceForm.pasteConfig') }}</label>
            <span class="label-hint">{{ t('mcp.instanceForm.jsonFormatRequired') }}</span>
          </div>
          <el-input
            v-model="configInput"
            type="textarea"
            :rows="10"
            :placeholder="configPlaceholderText"
            class="config-textarea"
            @input="handleConfigInput"
          />
          <div class="config-actions">
            <el-button 
              type="primary" 
              size="default"
              @click="parseConfig"
              :disabled="!configInput.trim()"
              :loading="parsing"
            >
              <el-icon><Tools /></el-icon>
              {{ t('mcp.instanceForm.parseConfig') }}
            </el-button>
            <el-button 
              type="info"
              size="default"
              @click="fillExample"
            >
              <el-icon><DocumentCopy /></el-icon>
              {{ t('mcp.instanceForm.fillExample') }}
            </el-button>
            <el-button 
              size="default"
              @click="clearConfig"
            >
              <el-icon><Delete /></el-icon>
              {{ t('mcp.instanceForm.clearConfig') }}
            </el-button>
          </div>
        </div>
      </div>

      <!-- Parsed results and personalized configuration -->
      <div class="parsed-config-section" v-if="parsedConfig">
        <el-form
          ref="formRef"
          :model="form"
          :rules="formRules"
          label-width="140px"
          label-position="left"
        >
          <div class="section-header">
            <div class="header-content">
              <h3>{{ t('mcp.instanceForm.parsedConfigTitle') }}</h3>
              <p class="header-desc">{{ t('mcp.instanceForm.configParseSuccess') }}</p>
            </div>
            <el-tag type="success" size="default" effect="dark">
              <el-icon><SuccessFilled /></el-icon>
              {{ t('mcp.instanceForm.configParsed') }}
            </el-tag>
          </div>

          <!-- Parsed configuration preview -->
          <div class="parsed-preview">
            <div class="preview-grid">
              <!-- Command information -->
              <div class="preview-card">
                <div class="card-header">
                  <el-icon class="card-icon"><Operation /></el-icon>
                  <span class="card-title">{{ t('mcp.instanceForm.detectedCommand') }}</span>
                </div>
                <div class="card-content">
                  <el-tag type="primary" size="large" effect="light">
                    <code>{{ parsedConfig.command }}</code>
                  </el-tag>
                </div>
              </div>

              <!-- Arguments information -->
              <div class="preview-card">
                <div class="card-header">
                  <el-icon class="card-icon"><Menu /></el-icon>
                  <span class="card-title">{{ t('mcp.instanceForm.detectedArgs') }}</span>
                </div>
                <div class="card-content">
                  <div v-if="parsedConfig.args.length > 0" class="args-list">
                    <el-tag 
                      v-for="(arg, index) in parsedConfig.args" 
                      :key="index" 
                      size="default" 
                      type="info"
                      effect="light"
                      class="arg-tag"
                    >
                      {{ arg }}
                    </el-tag>
                  </div>
                  <span v-else class="empty-text">{{ t('mcp.instanceForm.noArgs') }}</span>
                </div>
              </div>

              <!-- Environment variables information -->
              <div class="preview-card full-width">
                <div class="card-header">
                  <el-icon class="card-icon"><Setting /></el-icon>
                  <span class="card-title">{{ t('mcp.instanceForm.detectedEnvVars') }}</span>
                  <el-tag v-if="requiredEnvCount > 0" type="warning" size="small" effect="light">
                    {{ t('mcp.instanceForm.requiredEnvCount', { count: requiredEnvCount }) }}
                  </el-tag>
                </div>
                <div class="card-content">
                  <div v-if="Object.keys(parsedConfig.env).length > 0" class="env-list">
                    <div 
                      v-for="(value, key) in parsedConfig.env" 
                      :key="key" 
                      class="env-item-preview"
                      :class="{ 'required': value.includes('YOUR_') || value.includes('TOKEN') }"
                    >
                      <span class="env-key">{{ key }}</span>
                      <span class="env-separator">=</span>
                      <span class="env-value">{{ value }}</span>
                      <el-icon v-if="value.includes('YOUR_') || value.includes('TOKEN')" class="required-icon">
                        <Warning />
                      </el-icon>
                    </div>
                  </div>
                  <span v-else class="empty-text">{{ t('mcp.instanceForm.noEnvVars') }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Personalized configuration form -->
          <div class="personalized-config">
            <h4>{{ t('mcp.instanceForm.personalizedConfig') }}</h4>
            
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item :label="t('mcp.instanceForm.instanceName')" prop="instance_name">
                  <el-input
                    v-model="form.instance_name"
                    :placeholder="t('mcp.instanceForm.instanceNamePlaceholder')"
                    maxlength="50"
                    show-word-limit
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item :label="t('mcp.instanceForm.enabled')" prop="enabled">
                  <el-switch
                    v-model="form.enabled"
                    :active-text="t('mcp.instanceForm.enabledText')"
                    :inactive-text="t('mcp.instanceForm.disabledText')"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item :label="t('mcp.instanceForm.description')" prop="description">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="2"
                :placeholder="t('mcp.instanceForm.descriptionPlaceholder')"
                maxlength="200"
                show-word-limit
              />
            </el-form-item>

            <!-- Environment variables configuration -->
            <div class="env-config-section" v-if="Object.keys(parsedConfig.env).length > 0">
              <h5>{{ t('mcp.instanceForm.configureEnvVars') }}</h5>
              <div class="env-grid">
                <div 
                  v-for="(value, key) in parsedConfig.env" 
                  :key="key" 
                  class="env-config-item"
                >
                  <label class="env-label">{{ key }}</label>
                  <el-input
                    v-model="form.env[key]"
                    :placeholder="value"
                    size="small"
                    :class="{ 'required-env': value.includes('YOUR_') || value.includes('TOKEN') }"
                  >
                    <template #suffix v-if="value.includes('YOUR_') || value.includes('TOKEN')">
                      <el-icon class="required-icon"><Warning /></el-icon>
                    </template>
                  </el-input>
                  <div class="env-hint" v-if="value.includes('YOUR_') || value.includes('TOKEN')">
                    {{ t('mcp.instanceForm.requiredField') }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Advanced configuration (collapsible) -->
            <el-collapse v-model="advancedConfigOpen" class="advanced-config">
              <el-collapse-item :title="t('mcp.instanceForm.advancedConfig')" name="advanced">
                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item :label="t('mcp.instanceForm.timeout')" prop="timeout">
                      <el-input-number
                        v-model="form.timeout"
                        :min="1"
                        :max="300"
                        :step="1"
                        size="small"
                        style="width: 100%"
                      />
                      <div class="form-hint">{{ t('mcp.instanceForm.timeoutHint') }}</div>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item :label="t('mcp.instanceForm.autoRestart')" prop="auto_restart">
                      <el-switch
                        v-model="form.auto_restart"
                        :active-text="t('mcp.instanceForm.autoRestartEnabled')"
                        :inactive-text="t('mcp.instanceForm.autoRestartDisabled')"
                        size="small"
                      />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-form>
      </div>

      <!-- Empty state prompt -->
      <div class="empty-state" v-else>
        <el-empty 
          :description="t('mcp.instanceForm.pasteConfigHint')" 
          :image-size="120"
        >
          <template #image>
            <el-icon size="120" color="#409eff"><DocumentCopy /></el-icon>
          </template>
        </el-empty>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">
          {{ t('common.cancel') }}
        </el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="handleSubmit"
        >
          {{ isEditMode ? t('common.update') : t('common.create') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Delete, Warning, DocumentCopy, Check, Tools, SuccessFilled, Operation, Menu, Setting } from '@element-plus/icons-vue'

import {
  createExternalMcpInstance,
  updateExternalMcpInstance
} from '@/api/mcp/mcpApi'

// Multi-language support
const { t } = useI18n()

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  instance: {
    type: Object,
    default: null
  },
  templates: {
    type: Object,
    default: () => ({})
  },
  isEditMode: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits(['update:visible', 'success'])

// Reactive data
const formRef = ref()
const submitting = ref(false)
const parsing = ref(false)
const configInput = ref('')
const parsedConfig = ref(null)
const advancedConfigOpen = ref([])

// Form data
const form = ref({
  instance_name: '',
  description: '',
  command: '',
  args: [],
  env: {},
  timeout: 30,
  auto_restart: true,
  enabled: false
})

// Form validation rules
const formRules = {
  instance_name: [
    { required: true, message: t('mcp.instanceForm.instanceNameRequired'), trigger: 'blur' },
    { min: 2, max: 50, message: t('mcp.instanceForm.instanceNameLength'), trigger: 'blur' },
    { 
      pattern: /^[a-zA-Z0-9_-]+$/, 
      message: t('mcp.instanceForm.instanceNameFormat'), 
      trigger: 'blur' 
    }
  ],
  timeout: [
    { required: true, message: t('mcp.instanceForm.timeoutRequired'), trigger: 'blur' },
    { type: 'number', min: 1, max: 300, message: t('mcp.instanceForm.timeoutRange'), trigger: 'blur' }
  ]
}

// Computed properties
const visible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

// Calculate required environment variables count
const requiredEnvCount = computed(() => {
  if (!parsedConfig.value) return 0
  return Object.values(parsedConfig.value.env).filter(value => 
    value.includes('YOUR_') || value.includes('TOKEN')
  ).length
})

// Simplified placeholder text
const configPlaceholderText = computed(() => {
  return t('mcp.instanceForm.configPlaceholder')
})

// Methods
const initializeForm = () => {
  if (props.isEditMode && props.instance) {
    // Edit mode: populate existing instance data
    form.value = {
      instance_name: props.instance.instance_name || '',
      description: props.instance.description || '',
      command: props.instance.command || '',
      args: [...(props.instance.args || [])],
      env: { ...(props.instance.env || {}) },
      timeout: props.instance.timeout || 30,
      auto_restart: props.instance.auto_restart !== false,
      enabled: props.instance.enabled || false
    }
    
    // In edit mode, rebuild parsed configuration for display
    parsedConfig.value = {
      command: form.value.command,
      args: form.value.args,
      env: form.value.env
    }
  } else {
    // Create mode: reset form
    form.value = {
      instance_name: '',
      description: '',
      command: '',
      args: [],
      env: {},
      timeout: 30,
      auto_restart: true,
      enabled: false
    }
    configInput.value = ''
    parsedConfig.value = null
  }
}

// Configuration parsing related methods
const handleConfigInput = () => {
  // Real-time detection of configuration changes, but no auto-parsing
}

const parseConfig = async () => {
  parsing.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 300)) // Add brief delay to show loading state
    const config = JSON.parse(configInput.value.trim())
    
    // Check if it's a valid MCP configuration format
    if (!config.mcpServers && !config.command) {
      throw new Error(t('mcp.instanceForm.invalidConfigFormat'))
    }
    
    let mcpConfig = null
    
    // Handle complete mcpServers format
    if (config.mcpServers) {
      const serverKeys = Object.keys(config.mcpServers)
      if (serverKeys.length === 0) {
        throw new Error(t('mcp.instanceForm.noServersFound'))
      }
      
      // Take the first server configuration
      const firstServerKey = serverKeys[0]
      mcpConfig = config.mcpServers[firstServerKey]
      
      // If instance name is not set, use server key name
      if (!form.value.instance_name) {
        form.value.instance_name = firstServerKey
      }
    } else {
      // Handle direct server configuration format
      mcpConfig = config
    }
    
    // Validate required fields
    if (!mcpConfig.command) {
      throw new Error(t('mcp.instanceForm.missingCommand'))
    }
    
    // Validate supported commands
    const supportedCommands = ['npx', 'uvx', 'node', 'python', 'python3']
    if (!supportedCommands.includes(mcpConfig.command)) {
      ElMessage.warning(t('mcp.instanceForm.unsupportedCommand', { command: mcpConfig.command }))
    }
    
    // Parse configuration
    parsedConfig.value = {
      command: mcpConfig.command,
      args: mcpConfig.args || [],
      env: mcpConfig.env || {}
    }
    
    // Update form data
    form.value.command = mcpConfig.command
    form.value.args = [...(mcpConfig.args || [])]
    form.value.env = { ...(mcpConfig.env || {}) }
    
    // Generate default instance name (if not already set)
    if (!form.value.instance_name && mcpConfig.args && mcpConfig.args.length > 0) {
      const lastArg = mcpConfig.args[mcpConfig.args.length - 1]
      if (lastArg.includes('/')) {
        const packageName = lastArg.split('/').pop()
        form.value.instance_name = packageName.replace(/^server-/, '').replace(/-/g, '_')
      } else {
        form.value.instance_name = lastArg.replace(/^server-/, '').replace(/-/g, '_')
      }
    }
    
    ElMessage.success(t('mcp.instanceForm.configParsedSuccess'))
    
  } catch (error) {
    console.error('Configuration parsing failed:', error)
    ElMessage.error(t('mcp.instanceForm.configParseError') + ': ' + error.message)
  } finally {
    parsing.value = false
  }
}

const fillExample = () => {
  const exampleConfig = {
    "mcpServers": {
      "gitlab": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-gitlab"],
        "env": {
          "GITLAB_PERSONAL_ACCESS_TOKEN": "YOUR_TOKEN_HERE",
          "GITLAB_API_URL": "https://gitlab.com/api/v4"
        }
      }
    }
  }
  
  configInput.value = JSON.stringify(exampleConfig, null, 2)
  ElMessage.success(t('mcp.instanceForm.exampleFilled'))
}

const clearConfig = () => {
  configInput.value = ''
  parsedConfig.value = null
  form.value = {
    instance_name: '',
    description: '',
    command: '',
    args: [],
    env: {},
    timeout: 30,
    auto_restart: true,
    enabled: false
  }
}

const handleSubmit = async () => {
  try {
    // Validate if configuration has been parsed
    if (!parsedConfig.value) {
      ElMessage.error(t('mcp.instanceForm.pleaseParseConfig'))
      return
    }
    
    await formRef.value.validate()
    
    submitting.value = true
    
    // Filter empty arguments
    const filteredArgs = form.value.args.filter(arg => arg && arg.trim())
    
    const submitData = {
      ...form.value,
      args: filteredArgs
    }
    
    if (props.isEditMode) {
      // Update instance
      await updateExternalMcpInstance(props.instance.instance_id, submitData)
    } else {
      // Create instance - directly pass configuration, no template dependency
      await createExternalMcpInstance({
        instance_name: submitData.instance_name,
        command: submitData.command,
        args: submitData.args,
        env: submitData.env,
        description: submitData.description,
        timeout: submitData.timeout,
        auto_restart: submitData.auto_restart,
        enabled: submitData.enabled
      })
    }
    
    emit('success')
    handleClose()
  } catch (error) {
    console.error('Form submission failed:', error)
    ElMessage.error(
      (props.isEditMode ? t('mcp.instanceForm.updateError') : t('mcp.instanceForm.createError')) + 
      ': ' + error.message
    )
  } finally {
    submitting.value = false
  }
}

const handleClose = () => {
  visible.value = false
  // Reset state
  configInput.value = ''
  parsedConfig.value = null
  advancedConfigOpen.value = []
}

// Watch dialog visibility status
watch(visible, (newVal) => {
  if (newVal) {
    nextTick(() => {
      initializeForm()
    })
  }
})

// Watch instance changes
watch(() => props.instance, () => {
  if (visible.value) {
    initializeForm()
  }
}, { deep: true })
</script>

<style scoped lang="scss">
.instance-form-dialog {
  :deep(.el-dialog) {
    border-radius: 16px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
  }

  :deep(.el-dialog__header) {
    padding: 24px 24px 0 24px;
    border-bottom: 1px solid #f0f0f0;
    
    .el-dialog__title {
      font-size: 18px;
      font-weight: 600;
      color: #303133;
    }
  }

  :deep(.el-dialog__body) {
    padding: 24px;
    max-height: 80vh;
    overflow-y: auto;
  }
}

.form-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

// Configuration input area
.config-input-section {
  background: linear-gradient(135deg, #f8faff 0%, #f0f7ff 100%);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid #e1e8f0;
  
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 20px;
    
    .header-content {
      flex: 1;
      
      h3 {
        margin: 0 0 4px 0;
        font-size: 18px;
        font-weight: 600;
        color: #1a1a1a;
        display: flex;
        align-items: center;
        gap: 8px;
        
        &::before {
          content: '📋';
          font-size: 16px;
        }
      }
      
      .header-desc {
        margin: 0;
        font-size: 13px;
        color: #666;
        line-height: 1.4;
      }
    }
    
    .support-info {
      flex-shrink: 0;
      margin-left: 16px;
    }
  }
  
  .config-input-wrapper {
    .input-label {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      
      label {
        font-weight: 500;
        color: #303133;
        font-size: 14px;
      }
      
      .label-hint {
        font-size: 12px;
        color: #909399;
        font-style: italic;
      }
    }
  }
  
  .config-textarea {
    :deep(.el-textarea__inner) {
      font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
      font-size: 13px;
      line-height: 1.5;
      background: #ffffff;
      border: 2px dashed #d0d7de;
      border-radius: 12px;
      padding: 16px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
      
      &:hover {
        border-color: #409eff;
        box-shadow: 0 4px 12px rgba(64, 158, 255, 0.1);
      }
      
      &:focus {
        border-color: #409eff;
        border-style: solid;
        background: #fff;
        box-shadow: 0 4px 16px rgba(64, 158, 255, 0.15);
      }
      
      &::placeholder {
        color: #a8a8a8;
        font-size: 12px;
      }
    }
  }
  
  .config-actions {
    display: flex;
    gap: 12px;
    margin-top: 16px;
    justify-content: flex-end;
    
    .el-button {
      border-radius: 8px;
      font-weight: 500;
      
      &.el-button--primary {
        background: linear-gradient(135deg, #409eff 0%, #1890ff 100%);
        border: none;
        box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
        
        &:hover {
          box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
          transform: translateY(-1px);
        }
      }
    }
  }
}

// Parsed results area
.parsed-config-section {
  background: #ffffff;
  border-radius: 16px;
  padding: 24px;
  border: 1px solid #e1e8f0;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 20px;
    
    .header-content {
      flex: 1;
      
      h3 {
        margin: 0 0 4px 0;
        font-size: 18px;
        font-weight: 600;
        color: #1a1a1a;
        display: flex;
        align-items: center;
        gap: 8px;
        
        &::before {
          content: '✨';
          font-size: 16px;
        }
      }
      
      .header-desc {
        margin: 0;
        font-size: 13px;
        color: #666;
        line-height: 1.4;
      }
    }
  }
  
  .parsed-preview {
    margin-bottom: 32px;
    
    .preview-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      
      .preview-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        transition: all 0.2s ease;
        
        &:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
          transform: translateY(-1px);
        }
        
        &.full-width {
          grid-column: 1 / -1;
        }
        
        .card-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 12px;
          
          .card-icon {
            color: #409eff;
            font-size: 16px;
          }
          
          .card-title {
            font-weight: 500;
            color: #303133;
            font-size: 14px;
          }
        }
        
        .card-content {
          .args-list {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
          }
          
          .arg-tag {
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 12px;
          }
          
          .env-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
          }
          
          .env-item-preview {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: #ffffff;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 12px;
            
            &.required {
              border-color: #f56c6c;
              background: #fef0f0;
            }
            
            .env-key {
              font-weight: 600;
              color: #409eff;
            }
            
            .env-separator {
              color: #909399;
            }
            
            .env-value {
              color: #606266;
              flex: 1;
            }
            
            .required-icon {
              color: #f56c6c;
              font-size: 14px;
            }
          }
          
          .empty-text {
            color: #909399;
            font-style: italic;
            font-size: 13px;
          }
        }
      }
    }
  }
  
  .personalized-config {
    h4 {
      margin: 0 0 20px 0;
      font-size: 16px;
      font-weight: 600;
      color: #303133;
      display: flex;
      align-items: center;
      gap: 8px;
      
      &::before {
        content: '⚙️';
        font-size: 14px;
      }
    }
  }
}

// Environment variables configuration
.env-config-section {
  margin-top: 20px;
  
  h5 {
    margin: 0 0 12px 0;
    font-size: 13px;
    font-weight: 500;
    color: #606266;
  }
  
  .env-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 16px;
  }
  
  .env-config-item {
    .env-label {
      display: block;
      font-size: 12px;
      font-weight: 500;
      color: #606266;
      margin-bottom: 4px;
    }
    
    .required-env {
      :deep(.el-input__inner) {
        border-color: #f56c6c;
      }
    }
    
    .required-icon {
      color: #f56c6c;
    }
    
    .env-hint {
      font-size: 11px;
      color: #f56c6c;
      margin-top: 2px;
    }
  }
}

// Advanced configuration
.advanced-config {
  margin-top: 20px;
  
  :deep(.el-collapse-item__header) {
    font-size: 13px;
    font-weight: 500;
  }
}

// Empty state
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
  
  :deep(.el-empty__description) {
    color: #909399;
  }
}

.form-hint {
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

// Responsive design
@media (max-width: 1024px) {
  .instance-form-dialog {
    :deep(.el-dialog) {
      width: 95% !important;
      margin: 20px auto;
    }
  }
  
  .env-grid {
    grid-template-columns: 1fr !important;
  }
}

@media (max-width: 768px) {
  .instance-form-dialog {
    :deep(.el-dialog__body) {
      padding: 16px;
    }
  }
  
  .form-container {
    gap: 16px;
  }
  
  .section-header {
    flex-direction: column;
    gap: 8px;
    align-items: stretch !important;
  }

  .dialog-footer {
    flex-direction: column-reverse;
    
    .el-button {
      width: 100%;
    }
  }
}</style>

