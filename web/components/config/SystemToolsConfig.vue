<template>
  <div class="system-tools-config">
    <div class="config-header">
      <div class="header-info">
        <el-icon class="header-icon"><Tools /></el-icon>
        <div class="header-text">
          <h3>{{ $t('config.systemTools.title') }}</h3>
          <p class="header-description">{{ $t('config.systemTools.description') }}</p>
        </div>
      </div>
      
      <div class="header-actions">
        <el-button
          type="primary"
          size="small"
          @click="executeAllTools"
          :loading="executingAll"
          :disabled="executeAllCooldown"
          :icon="Connection"
        >
          {{ $t('config.systemTools.executeAllTools') }}
        </el-button>
        
        <el-dropdown @command="handleMenuCommand">
          <el-button size="small" :icon="More">
            {{ $t('config.systemTools.more') }}
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="testAll">{{ $t('config.systemTools.testAllTools') }}</el-dropdown-item>
              <el-dropdown-item command="enableAll" divided>{{ $t('config.systemTools.enableAllTools') }}</el-dropdown-item>
              <el-dropdown-item command="disableAll">{{ $t('config.systemTools.disableAllTools') }}</el-dropdown-item>
              <el-dropdown-item command="reset" divided>{{ $t('config.systemTools.resetConfig') }}</el-dropdown-item>
              <el-dropdown-item command="exportConfig">{{ $t('config.systemTools.exportConfig') }}</el-dropdown-item>
              <el-dropdown-item command="importConfig">{{ $t('config.systemTools.importConfig') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- Statistics Information -->
    <div class="stats-section">
      <div class="stats-cards">
        <div class="stats-card">
          <div class="stats-icon stats-icon-total">
            <el-icon><Collection /></el-icon>
          </div>
          <div class="stats-content">
            <div class="stats-number">{{ stats.totalTools }}</div>
            <div class="stats-label">{{ $t('config.systemTools.totalTools') }}</div>
          </div>
        </div>
        
        <div class="stats-card">
          <div class="stats-icon stats-icon-enabled">
            <el-icon><Check /></el-icon>
          </div>
          <div class="stats-content">
            <div class="stats-number">{{ stats.enabledTools }}</div>
            <div class="stats-label">{{ $t('config.systemTools.enabled') }}</div>
          </div>
        </div>
        
        <div class="stats-card">
          <div class="stats-icon stats-icon-disabled">
            <el-icon><Close /></el-icon>
          </div>
          <div class="stats-content">
            <div class="stats-number">{{ stats.disabledTools }}</div>
            <div class="stats-label">{{ $t('config.systemTools.disabled') }}</div>
          </div>
        </div>
        
        <div class="stats-card">
          <div class="stats-icon stats-icon-categories">
            <el-icon><FolderOpened /></el-icon>
          </div>
          <div class="stats-content">
            <div class="stats-number">{{ stats.categories }}</div>
            <div class="stats-label">{{ $t('config.systemTools.categories') }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tools List -->
    <div class="tools-section">
      <div class="section-header">
        <h4>{{ $t('config.systemTools.toolsList') }}</h4>
        <div class="section-filters">
          <el-select
            v-model="selectedCategory"
            :placeholder="$t('config.systemTools.selectCategory')"
            size="small"
            style="width: 120px"
            @change="filterByCategory"
            clearable
          >
            <el-option
              v-for="category in categories"
              :key="category"
              :label="getCategoryDisplayName(category)"
              :value="category"
            />
          </el-select>
          
          <el-input
            v-model="searchKeyword"
            :placeholder="$t('config.systemTools.searchTools')"
            size="small"
            style="width: 200px"
            :prefix-icon="Search"
            clearable
            @input="filterTools"
          />
        </div>
      </div>

      <div class="tools-list">
        <div
          v-for="tool in filteredTools"
          :key="tool.name"
          class="tool-item"
          :class="{ 'tool-enabled': tool.enabled, 'tool-disabled': !tool.enabled }"
        >
          <div class="tool-basic-info">
            <div class="tool-header">
              <div class="tool-name-section">
                <el-switch
                  v-model="tool.enabled"
                  size="small"
                  @change="handleToolToggle(tool.name, $event)"
                />
                <div class="tool-name">{{ tool.name }}</div>
                <el-tag
                  :type="getCategoryTagType(tool.category)"
                  size="small"
                  class="tool-category"
                >
                  {{ getCategoryDisplayName(tool.category) }}
                </el-tag>
              </div>
              
              <div class="tool-actions">
                <el-button
                  size="small"
                  text
                  type="primary"
                  @click="executeTool(tool.name)"
                  :loading="executingTools.includes(tool.name)"
                  :icon="Connection"
                  :title="$t('config.systemTools.execute')"
                  :disabled="!tool.enabled || executeButtonCooldown.value"
                >
                  {{ $t('config.systemTools.execute') }}
                </el-button>
                <el-button
                  size="small"
                  text
                  type="success"
                  @click="testTool(tool.name)"
                  :loading="testingTools.includes(tool.name)"
                  :icon="View"
                  :title="$t('config.systemTools.test')"
                >
                  {{ $t('config.systemTools.test') }}
                </el-button>
                <el-button
                  size="small"
                  text
                  type="info"
                  @click="showToolDetails(tool)"
                  :icon="View"
                  :title="$t('config.systemTools.viewDetails')"
                />
                <el-button
                  size="small"
                  text
                  type="warning"
                  @click="configTool(tool)"
                  :icon="Setting"
                  :title="$t('config.systemTools.config')"
                />
              </div>
            </div>
            
            <div class="tool-description">{{ tool.description }}</div>
            
            <div class="tool-meta">
              <span class="tool-version">v{{ tool.version }}</span>
              <span class="tool-author">{{ tool.author }}</span>
              <span
                v-if="testResults[tool.name] !== undefined"
                class="tool-test-result"
                :class="{ 'test-success': testResults[tool.name], 'test-failed': !testResults[tool.name] }"
              >
                <el-icon>
                  <Check v-if="testResults[tool.name]" />
                  <Close v-else />
                </el-icon>
                {{ testResults[tool.name] ? $t('config.systemTools.connectionNormal') : $t('config.systemTools.connectionFailed') }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tool Details Dialog -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="$t('config.systemTools.toolDetails')"
      width="600px"
      :destroy-on-close="true"
    >
      <div v-if="selectedTool" class="tool-details">
        <div class="detail-section">
          <h4>{{ $t('config.systemTools.basicInfo') }}</h4>
          <div class="detail-grid">
            <div class="detail-item">
              <label>{{ $t('config.systemTools.toolName') }}:</label>
              <span>{{ selectedTool.name }}</span>
            </div>
            <div class="detail-item">
              <label>{{ $t('config.systemTools.version') }}:</label>
              <span>v{{ selectedTool.version }}</span>
            </div>
            <div class="detail-item">
              <label>{{ $t('config.systemTools.author') }}:</label>
              <span>{{ selectedTool.author }}</span>
            </div>
            <div class="detail-item">
              <label>{{ $t('config.systemTools.category') }}:</label>
              <el-tag :type="getCategoryTagType(selectedTool.category)" size="small">
                {{ getCategoryDisplayName(selectedTool.category) }}
              </el-tag>
            </div>
            <div class="detail-item detail-item-full">
              <label>{{ $t('config.systemTools.description') }}:</label>
              <span>{{ selectedTool.description }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h4>{{ $t('config.systemTools.parameterDefinition') }}</h4>
          <div class="schema-display">
            <pre class="schema-json">{{ JSON.stringify(selectedTool.inputSchema, null, 2) }}</pre>
          </div>
        </div>

        <div v-if="selectedTool.config && Object.keys(selectedTool.config).length > 0" class="detail-section">
          <h4>{{ $t('config.systemTools.toolConfig') }}</h4>
          <div class="config-display">
            <pre class="config-json">{{ JSON.stringify(selectedTool.config, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- Tool Configuration Dialog -->
    <el-dialog
      v-model="configDialogVisible"
      :title="$t('config.systemTools.toolConfiguration')"
      width="500px"
      :destroy-on-close="true"
    >
      <div v-if="currentConfigTool && configFormData" class="tool-config-form">
        <!-- Special configuration for MCP reconnect tool -->
        <div v-if="currentConfigTool.name === 'mcp_reconnect'" class="config-section">
          <h4>{{ $t('config.systemTools.mcpReconnectConfig') }}</h4>
          
          <el-form :model="configFormData" label-width="120px" size="small">
            <el-form-item :label="$t('config.systemTools.defaultReconnectType')">
              <el-select v-model="configFormData.defaultReconnectType">
                <el-option :label="$t('config.systemTools.intelligentReconnect')" value="auto" />
                <el-option :label="$t('config.systemTools.enabledOnly')" value="enabled_only" />
                <el-option :label="$t('config.systemTools.allServers')" value="all" />
              </el-select>
              <div class="form-help">
                {{ $t('config.systemTools.intelligentReconnectDesc') }}
              </div>
            </el-form-item>
            
            <el-form-item :label="$t('config.systemTools.disconnectFirst')">
              <el-switch
                v-model="configFormData.disconnectFirst"
                :active-text="$t('config.systemTools.yes')"
                :inactive-text="$t('config.systemTools.no')"
              />
              <div class="form-help">
                {{ $t('config.systemTools.disconnectFirstDesc') }}
              </div>
            </el-form-item>
            
            <el-form-item :label="$t('config.systemTools.showProgress')">
              <el-switch
                v-model="configFormData.showProgress"
                :active-text="$t('config.systemTools.yes')"
                :inactive-text="$t('config.systemTools.no')"
              />
              <div class="form-help">
                {{ $t('config.systemTools.showProgressDesc') }}
              </div>
            </el-form-item>
            
            <el-form-item :label="$t('config.systemTools.connectionTimeout')">
              <el-input-number
                v-model="configFormData.timeout"
                :min="10000"
                :max="120000"
                :step="5000"
                controls-position="right"
              />
              <span class="form-help">{{ $t('config.systemTools.milliseconds') }}</span>
            </el-form-item>
            
            <el-form-item :label="$t('config.systemTools.retryCount')">
              <el-input-number
                v-model="configFormData.maxRetries"
                :min="1"
                :max="10"
                controls-position="right"
              />
              <div class="form-help">
                {{ $t('config.systemTools.retryCountDesc') }}
              </div>
            </el-form-item>
            
            <el-form-item :label="$t('config.systemTools.retryDelay')">
              <el-input-number
                v-model="configFormData.retryDelay"
                :min="1000"
                :max="10000"
                :step="500"
                controls-position="right"
              />
              <span class="form-help">{{ $t('config.systemTools.milliseconds') }}</span>
            </el-form-item>
          </el-form>
        </div>
        
        <!-- Generic configuration -->
        <div v-else class="config-section">
          <el-alert
            :title="$t('config.systemTools.noConfigurableItems')"
            type="info"
            :closable="false"
            show-icon
          />
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="configDialogVisible = false">{{ $t('config.systemTools.cancel') }}</el-button>
          <el-button type="primary" @click="saveToolConfig">{{ $t('config.systemTools.saveConfig') }}</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- Configuration Import Dialog -->
    <el-dialog
      v-model="importDialogVisible"
      :title="$t('config.systemTools.importConfig')"
      width="400px"
    >
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :show-file-list="false"
        accept=".json"
        :on-change="handleConfigFileChange"
        drag
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          {{ $t('config.systemTools.dragDropHint') }}<em>{{ $t('config.systemTools.clickToUpload') }}</em>
        </div>
        <div class="el-upload__tip">
          {{ $t('config.systemTools.jsonFileOnly') }}
        </div>
      </el-upload>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="importDialogVisible = false">{{ $t('config.systemTools.cancel') }}</el-button>
          <el-button type="primary" @click="importConfig" :disabled="!importConfigData">{{ $t('config.systemTools.confirmImport') }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted} from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
import {
  Tools,
  Connection,
  More,
  ArrowDown,
  Collection,
  Check,
  Close,
  FolderOpened,
  Search,
  View,
  Setting,
  UploadFilled
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import systemToolsManager from '@/services/system-tools/index.js'
import DebugLogger from "@/utils/DebugLogger";

// Props
const props = defineProps({
  configData: {
    type: Object,
    default: () => ({})
  }
})

// Reactive data
const tools = ref([])
const filteredTools = ref([])
const stats = ref({
  totalTools: 0,
  enabledTools: 0,
  disabledTools: 0,
  categories: 0
})
const categories = ref([])
const selectedCategory = ref('')
const searchKeyword = ref('')
const testing = ref(false)
const executingAll = ref(false)
const testingTools = ref([])
const executingTools = ref([])
const testResults = ref({})
const executeResults = ref({})

// Add execution button cooldown mechanism
const executeButtonCooldown = ref(false)
const executeAllCooldown = ref(false)
const COOLDOWN_TIME = 3000 // 3 second cooldown time

// Dialog control
const detailDialogVisible = ref(false)
const configDialogVisible = ref(false)
const importDialogVisible = ref(false)
const selectedTool = ref(null)
const currentConfigTool = ref(null)
const configFormData = ref(null)
const importConfigData = ref(null)

const logger = DebugLogger.createLogger('SystemToolsConfig')

// Component initialization
onMounted(async () => {
  // Original initialization logic
  await loadTools()
})

// Load tool list
const loadTools = async () => {
  try {
    const allTools = systemToolsManager.getAllTools()
    tools.value = allTools.map(tool => tool.getConfig())
    
    // Update statistics
    stats.value = systemToolsManager.getStats()
    
    // Extract categories
    categories.value = [...new Set(tools.value.map(tool => tool.category))]
    
    // Initialize filter results
    filteredTools.value = [...tools.value]
    
  } catch (error) {
    console.error('Failed to load system tools:', error)
    ElMessage.error(t('config.systemTools.loadToolsFailed'))
  }
}

// Handle tool switch toggle
const handleToolToggle = (toolName, enabled) => {
  try {
    if (enabled) {
      systemToolsManager.enableTool(toolName)
      logger.log(`[SystemToolsConfig] ${t('config.systemTools.toolEnabled')}: ${toolName}`)
      ElMessage.success(`${t('config.systemTools.toolEnabled')}: ${toolName}`)
    } else {
      systemToolsManager.disableTool(toolName)
      logger.log(`[SystemToolsConfig] ${t('config.systemTools.toolDisabled')}: ${toolName}`)
      ElMessage.success(`${t('config.systemTools.toolDisabled')}: ${toolName}`)
    }
    
    // Update statistics
    stats.value = systemToolsManager.getStats()
    
    // Verify if status change will trigger system prompt rebuilding
    logger.log(`[SystemToolsConfig] Tool status change completed, current enabled tool count: ${stats.value.enabledTools}`)
    
  } catch (error) {
    console.error('Failed to toggle tool status:', error)
    ElMessage.error(t('config.systemTools.operationFailed'))
    // Rollback status
    const tool = tools.value.find(t => t.name === toolName)
    if (tool) {
      tool.enabled = !enabled
    }
  }
}

// Execute single tool
const executeTool = async (toolName) => {
  if (executingTools.value.includes(toolName) || executeButtonCooldown.value) return
  
  // Start cooldown
  executeButtonCooldown.value = true
  setTimeout(() => {
    executeButtonCooldown.value = false
  }, COOLDOWN_TIME)
  
  executingTools.value.push(toolName)
  
  try {
    ElMessage.info(`${t('config.systemTools.executingTool')}: ${toolName}...`)
    
    const result = await systemToolsManager.executeTool(toolName)
    executeResults.value[toolName] = result
    
    if (result.success) {
      ElMessage.success({
        message: `${t('config.systemTools.toolExecutionSuccess')}: ${result.data?.message || t('config.systemTools.executionCompleted')}`,
        duration: 5000
      })
      
      // If there are detailed information, output to console
      if (result.data?.details || result.data?.statistics) {
        logger.log(`[${toolName}] Execution result details:`, result.data)
      }
    } else {
      ElMessage.error({
        message: `${t('config.systemTools.toolExecutionFailed')}: ${result.error || t('config.systemTools.unknownError')}`,
        duration: 5000
      })
    }
    
  } catch (error) {
    console.error(`${t('config.systemTools.toolExecutionFailed')} ${toolName} ${t('config.systemTools.failed')}:`, error)
    executeResults.value[toolName] = { success: false, error: error.message }
    ElMessage.error({
      message: `${t('config.systemTools.toolExecutionFailed')} ${toolName} ${t('config.systemTools.failed')}: ${error.message}`,
      duration: 5000
    })
  } finally {
    const index = executingTools.value.indexOf(toolName)
    if (index > -1) {
      executingTools.value.splice(index, 1)
    }
  }
}

// Test single tool
const testTool = async (toolName) => {
  if (testingTools.value.includes(toolName)) return
  
  testingTools.value.push(toolName)
  
  try {
    const result = await systemToolsManager.testTool(toolName)
    testResults.value[toolName] = result
    
    if (result) {
      ElMessage.success(`${t('config.systemTools.tool')} ${toolName} ${t('config.systemTools.connectionNormal')}`)
    } else {
      ElMessage.warning(`${t('config.systemTools.tool')} ${toolName} ${t('config.systemTools.connectionFailed')}`)
    }
    
  } catch (error) {
    console.error(`${t('config.systemTools.testTool')} ${toolName} ${t('config.systemTools.failed')}:`, error)
    testResults.value[toolName] = false
    ElMessage.error(`${t('config.systemTools.testTool')} ${toolName} ${t('config.systemTools.failed')}`)
  } finally {
    const index = testingTools.value.indexOf(toolName)
    if (index > -1) {
      testingTools.value.splice(index, 1)
    }
  }
}

// Execute all enabled tools
const executeAllTools = async () => {
  if (executingAll.value || executeAllCooldown.value) return
  
  // Start cooldown
  executeAllCooldown.value = true
  setTimeout(() => {
    executeAllCooldown.value = false
  }, COOLDOWN_TIME)
  
  executingAll.value = true
  
  try {
    const enabledTools = tools.value.filter(tool => tool.enabled)
    
    if (enabledTools.length === 0) {
      ElMessage.warning(t('config.systemTools.noEnabledTools'))
      return
    }
    
    ElMessage.info(`${t('config.systemTools.startExecuting')} ${enabledTools.length} ${t('config.systemTools.enabledToolsCount')}...`)
    
    const results = {}
    let successCount = 0
    let errorCount = 0
    
    // Execute in sequence to avoid concurrency issues
    for (const tool of enabledTools) {
      try {
        logger.log(`[${t('config.systemTools.executeAllToolsLog')}] ${t('config.systemTools.executing')}: ${tool.name}`)
        const result = await systemToolsManager.executeTool(tool.name)
        results[tool.name] = result
        
        if (result.success) {
          successCount++
          logger.log(`[${t('config.systemTools.executeAllToolsLog')}] ${tool.name} ${t('config.systemTools.executionSuccess')}:`, result.data)
        } else {
          errorCount++
          console.error(`[${t('config.systemTools.executeAllToolsLog')}] ${tool.name} ${t('config.systemTools.executionFailed')}:`, result.error)
        }
      } catch (error) {
        errorCount++
        results[tool.name] = { success: false, error: error.message }
         console.error(`[${t('config.systemTools.executeAllToolsLog')}] ${tool.name} ${t('config.systemTools.executionException')}:`, error)
      }
    }
    
    executeResults.value = { ...executeResults.value, ...results }
    
    if (successCount === enabledTools.length) {
      ElMessage.success(`${t('config.systemTools.allToolsExecuted')} ${t('config.systemTools.successCount')}: ${successCount} ${t('config.systemTools.items')}`)
    } else if (successCount > 0) {
      ElMessage.warning(`${t('config.systemTools.toolExecutionCompleted')} ${t('config.systemTools.successCount')}: ${successCount} ${t('config.systemTools.items')} ${t('config.systemTools.failedCount')}: ${errorCount} ${t('config.systemTools.items')}`)
    } else {
      ElMessage.error(`${t('config.systemTools.allToolsExecutionFailed')} ${t('config.systemTools.failedCount')}: ${errorCount} ${t('config.systemTools.items')}`)
    }
    
  } catch (error) {
    console.error('Failed to execute all tools:', error)
    ElMessage.error(t('config.systemTools.executionFailed'))
  } finally {
    executingAll.value = false
  }
}

// Test all tools
const testAllTools = async () => {
  testing.value = true
  
  try {
    const results = await systemToolsManager.testAllTools()
    testResults.value = { ...testResults.value, ...results }
    
    const successCount = Object.values(results).filter(Boolean).length
    const totalCount = Object.keys(results).length
    
    ElMessage.success(`${t('config.systemTools.testCompleted')}: ${successCount}/${totalCount} ${t('config.systemTools.toolsConnectionNormal')}`)
    
  } catch (error) {
    console.error('Failed to test all tools:', error)
    ElMessage.error(t('config.systemTools.testFailed'))
  } finally {
    testing.value = false
  }
}

// Show tool details
const showToolDetails = (tool) => {
  selectedTool.value = tool
  detailDialogVisible.value = true
}

// Configure tool
const configTool = (tool) => {
  currentConfigTool.value = tool
  
  // Prepare configuration form data based on tool type
  if (tool.name === 'mcp_reconnect') {
    configFormData.value = {
      defaultReconnectType: tool.config.defaultReconnectType || 'auto',
      disconnectFirst: tool.config.disconnectFirst !== false,
      showProgress: tool.config.showProgress !== false,
      timeout: tool.config.timeout || 30000,
      maxRetries: tool.config.maxRetries || 3,
      retryDelay: tool.config.retryDelay || 2000
    }
  } else {
    configFormData.value = {}
  }
  
  configDialogVisible.value = true
}

// Save tool configuration
const saveToolConfig = () => {
  try {
    const toolName = currentConfigTool.value.name
    systemToolsManager.updateToolConfig(toolName, {
      config: configFormData.value
    })
    
    ElMessage.success(t('config.systemTools.configSaved'))
    configDialogVisible.value = false
    
    // Reload tool list
    loadTools()
    
  } catch (error) {
    console.error('Failed to save tool configuration:', error)
    ElMessage.error(t('config.systemTools.saveConfigFailed'))
  }
}

// Handle menu command
const handleMenuCommand = async (command) => {
  switch (command) {
    case 'testAll':
      await testAllTools()
      break
    case 'enableAll':
      await enableAllTools()
      break
    case 'disableAll':
      await disableAllTools()
      break
    case 'reset':
      await resetConfig()
      break
    case 'exportConfig':
      exportConfig()
      break
    case 'importConfig':
      importDialogVisible.value = true
      break
  }
}

// Enable all tools
const enableAllTools = async () => {
  try {
    const toolStates = {}
    tools.value.forEach(tool => {
      toolStates[tool.name] = true
    })
    
    systemToolsManager.setToolStates(toolStates)
    
    await loadTools()
    ElMessage.success(t('config.systemTools.allToolsEnabled'))
  } catch (error) {
    console.error('Failed to enable all tools:', error)
    ElMessage.error(t('config.systemTools.operationFailed'))
  }
}

// Disable all tools
const disableAllTools = async () => {
  try {
    const toolStates = {}
    tools.value.forEach(tool => {
      toolStates[tool.name] = false
    })
    
    systemToolsManager.setToolStates(toolStates)
    
    await loadTools()
    ElMessage.success(t('config.systemTools.allToolsDisabled'))
  } catch (error) {
    console.error('Failed to disable all tools:', error)
    ElMessage.error(t('config.systemTools.operationFailed'))
  }
}

// Reset configuration
const resetConfig = async () => {
  try {
    await ElMessageBox.confirm(
      t('config.systemTools.resetConfigConfirm'),
      t('config.systemTools.resetConfigTitle'),
      {
        confirmButtonText: t('config.systemTools.confirm'),
        cancelButtonText: t('config.systemTools.cancel'),
        type: 'warning'
      }
    )
    
    systemToolsManager.resetConfig()
    await loadTools()
    testResults.value = {}
    
    ElMessage.success(t('config.systemTools.configReset'))
  } catch (error) {
    // User cancelled operation
  }
}

// Export configuration
const exportConfig = () => {
  try {
    const config = systemToolsManager.exportConfig()
    const dataStr = JSON.stringify(config, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    
    const link = document.createElement('a')
    link.href = URL.createObjectURL(dataBlob)
    link.download = `system_tools_config_${new Date().toISOString().slice(0, 10)}.json`
    link.click()
    
    ElMessage.success(t('config.systemTools.configExported'))
  } catch (error) {
    console.error('Failed to export configuration:', error)
    ElMessage.error(t('config.systemTools.exportFailed'))
  }
}

// Handle configuration file change
const handleConfigFileChange = (file) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const config = JSON.parse(e.target.result)
      importConfigData.value = config
    } catch (error) {
      ElMessage.error(t('config.systemTools.invalidConfigFormat'))
      importConfigData.value = null
    }
  }
  reader.readAsText(file.raw)
}

// Import configuration
const importConfig = () => {
  try {
    if (!importConfigData.value) {
      ElMessage.error(t('config.systemTools.pleaseSelectValidConfig'))
      return
    }
    
    systemToolsManager.importConfig(importConfigData.value)
    
    loadTools()
    importDialogVisible.value = false
    importConfigData.value = null
    
    ElMessage.success(t('config.systemTools.configImported'))
  } catch (error) {
    console.error('Failed to import configuration:', error)
    ElMessage.error(t('config.systemTools.importFailed'))
  }
}

// Filter by category
const filterByCategory = () => {
  filterTools()
}

// Filter tools
const filterTools = () => {
  let filtered = [...tools.value]
  
  // Filter by category
  if (selectedCategory.value) {
    filtered = filtered.filter(tool => tool.category === selectedCategory.value)
  }
  
  // Filter by keyword
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    filtered = filtered.filter(tool =>
      tool.name.toLowerCase().includes(keyword) ||
      tool.description.toLowerCase().includes(keyword)
    )
  }
  
  filteredTools.value = filtered
}

// Get category display name
const getCategoryDisplayName = (category) => {
  const categoryNames = {
    search: t('config.systemTools.categorySearch'),
    general: t('config.systemTools.categoryGeneral'),
    utility: t('config.systemTools.categoryUtility'),
    api: t('config.systemTools.categoryApi'),
    data: t('config.systemTools.categoryData')
  }
  return categoryNames[category] || category
}

// Get category tag type
const getCategoryTagType = (category) => {
  const categoryTypes = {
    search: 'primary',
    general: 'info',
    utility: 'success',
    api: 'warning',
    data: 'danger'
  }
  return categoryTypes[category] || 'info'
}
</script>

<style scoped lang="scss">
.system-tools-config {
  .config-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding: 20px;
    background: var(--el-fill-color-extra-light);
    border-radius: 8px;
    border: 1px solid var(--el-border-color-light);

    .header-info {
      display: flex;
      align-items: center;
      gap: 12px;

      .header-icon {
        font-size: 24px;
        color: var(--el-color-primary);
      }

      .header-text {
        h3 {
          margin: 0 0 4px 0;
          color: var(--el-text-color-primary);
          font-size: 18px;
          font-weight: 600;
        }

        .header-description {
          margin: 0;
          color: var(--el-text-color-secondary);
          font-size: 14px;
        }
      }
    }

    .header-actions {
      display: flex;
      gap: 8px;
    }
  }

  .stats-section {
    margin-bottom: 24px;

    .stats-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;

      .stats-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px;
        background: white;
        border-radius: 8px;
        border: 1px solid var(--el-border-color-light);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);

        .stats-icon {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 18px;

          &.stats-icon-total {
            background: var(--el-color-primary-light-9);
            color: var(--el-color-primary);
          }

          &.stats-icon-enabled {
            background: var(--el-color-success-light-9);
            color: var(--el-color-success);
          }

          &.stats-icon-disabled {
            background: var(--el-color-danger-light-9);
            color: var(--el-color-danger);
          }

          &.stats-icon-categories {
            background: var(--el-color-warning-light-9);
            color: var(--el-color-warning);
          }
        }

        .stats-content {
          .stats-number {
            font-size: 24px;
            font-weight: 600;
            color: var(--el-text-color-primary);
            line-height: 1;
          }

          .stats-label {
            font-size: 12px;
            color: var(--el-text-color-secondary);
            margin-top: 2px;
          }
        }
      }
    }
  }

  .tools-section {
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;

      h4 {
        margin: 0;
        color: var(--el-text-color-primary);
        font-size: 16px;
        font-weight: 600;
      }

      .section-filters {
        display: flex;
        gap: 12px;
      }
    }

    .tools-list {
      .tool-item {
        background: white;
        border: 1px solid var(--el-border-color-light);
        border-radius: 8px;
        margin-bottom: 12px;
        transition: all 0.2s ease;

        &:hover {
          border-color: var(--el-color-primary-light-7);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        &.tool-enabled {
          border-left: 4px solid var(--el-color-success);
        }

        &.tool-disabled {
          border-left: 4px solid var(--el-color-info);
          opacity: 0.8;
        }

        .tool-basic-info {
          padding: 16px;

          .tool-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;

            .tool-name-section {
              display: flex;
              align-items: center;
              gap: 12px;

              .tool-name {
                font-size: 16px;
                font-weight: 600;
                color: var(--el-text-color-primary);
              }

              .tool-category {
                margin-left: 8px;
              }
            }

            .tool-actions {
              display: flex;
              gap: 4px;
            }
          }

          .tool-description {
            color: var(--el-text-color-regular);
            font-size: 14px;
            line-height: 1.5;
            margin-bottom: 12px;
          }

          .tool-meta {
            display: flex;
            align-items: center;
            gap: 16px;
            font-size: 12px;
            color: var(--el-text-color-secondary);

            .tool-version,
            .tool-author {
              padding: 2px 6px;
              background: var(--el-fill-color-light);
              border-radius: 4px;
            }

            .tool-test-result {
              display: flex;
              align-items: center;
              gap: 4px;

              &.test-success {
                color: var(--el-color-success);
              }

              &.test-failed {
                color: var(--el-color-danger);
              }
            }
          }
        }
      }
    }
  }
}

.tool-details {
  .detail-section {
    margin-bottom: 24px;

    &:last-child {
      margin-bottom: 0;
    }

    h4 {
      margin: 0 0 12px 0;
      color: var(--el-text-color-primary);
      font-size: 14px;
      font-weight: 600;
      border-bottom: 1px solid var(--el-border-color-lighter);
      padding-bottom: 8px;
    }

    .detail-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;

      .detail-item {
        display: flex;
        align-items: center;
        font-size: 14px;

        &.detail-item-full {
          grid-column: 1 / -1;
          align-items: flex-start;
        }

        label {
          color: var(--el-text-color-secondary);
          margin-right: 8px;
          min-width: 60px;
        }

        span {
          color: var(--el-text-color-primary);
        }
      }
    }

    .schema-display,
    .config-display {
      .schema-json,
      .config-json {
        background: var(--el-fill-color-light);
        border: 1px solid var(--el-border-color-lighter);
        border-radius: 4px;
        padding: 12px;
        font-size: 12px;
        line-height: 1.4;
        color: var(--el-text-color-regular);
        overflow-x: auto;
        margin: 0;
      }
    }
  }
}

.tool-config-form {
  .config-section {
    h4 {
      margin: 0 0 16px 0;
      color: var(--el-text-color-primary);
      font-size: 14px;
      font-weight: 600;
    }

    .form-help {
      margin-left: 8px;
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }
}

// Mobile adaptation
@media (max-width: 768px) {
  .system-tools-config {
    .config-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 16px;

      .header-actions {
        width: 100%;
        justify-content: flex-end;
      }
    }

    .stats-section {
      .stats-cards {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    .tools-section {
      .section-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 12px;

        .section-filters {
          width: 100%;
          justify-content: space-between;
        }
      }

      .tools-list {
        .tool-item {
          .tool-basic-info {
            .tool-header {
              flex-direction: column;
              align-items: flex-start;
              gap: 12px;

              .tool-actions {
                align-self: flex-end;
              }
            }

            .tool-meta {
              flex-wrap: wrap;
              gap: 8px;
            }
          }
        }
      }
    }
  }

  .tool-details {
    .detail-section {
      .detail-grid {
        grid-template-columns: 1fr;
      }
    }
  }
}
</style>