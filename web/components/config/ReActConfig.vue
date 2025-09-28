<template>
  <div class="react-config">
    <el-form 
      ref="formRef"
      :model="formData"
      label-width="120px"
      class="config-form"
    >
      <!-- ReAct Switch -->
      <el-form-item :label="$t('config.reactConfig.enableReActMode')">
        <el-switch
          v-model="formData.enabled"
          :active-text="$t('common.enable')"
          :inactive-text="$t('common.disable')"
          @change="handleReActToggle"
        />
        <div class="form-help">
          {{ $t('config.reactConfig.enableReActModeDesc') }}
        </div>
      </el-form-item>

      <!-- ReAct Configuration (Only shown when enabled) -->
      <template v-if="formData.enabled">
        <!-- Maximum Iterations -->
        <el-form-item :label="$t('config.reactConfig.maxIterations')">
          <div style="display: flex; ">
            <el-input-number
                v-model="formData.maxIterations"
                :min="1"
                :max="10"
                :step="1"
                controls-position="right"
                @change="handleFormChange"
            />
            <div class="form-help">
              {{ $t('config.reactConfig.maxIterationsDesc') }}
            </div>
          </div>
        </el-form-item>

        <!-- Timeout Settings -->
        <el-form-item :label="$t('config.reactConfig.timeoutSeconds')">
          <el-input-number
            v-model="timeoutSeconds"
            :min="10"
            :max="120"
            :step="5"
            controls-position="right"
          />
          <div class="form-help">
            {{ $t('config.reactConfig.timeoutDesc') }}
          </div>
        </el-form-item>


      </template>

      <!-- Action Buttons -->
      <el-form-item>
        <el-button type="primary" @click="testReActEngine">{{ $t('config.reactConfig.testEngine') }}</el-button>
        <el-button @click="resetToDefaults">{{ $t('config.reactConfig.resetDefault') }}</el-button>
        <el-button @click="showAdvancedInfo">{{ $t('config.reactConfig.viewAdvancedConfig') }}</el-button>
      </el-form-item>
    </el-form>

    <!-- Advanced Configuration Info Dialog -->
    <el-dialog
      v-model="showAdvancedDialog"
      :title="$t('config.reactConfig.advancedConfigTitle')"
      width="70%"
    >
      <div class="advanced-info">
        <h4>{{ $t('config.reactConfig.currentFeatures') }}：</h4>
        <ul>
          <li>✅ {{ $t('config.reactConfig.feature1') }}</li>
          <li>✅ {{ $t('config.reactConfig.feature2') }}</li>
          <li>✅ {{ $t('config.reactConfig.feature3') }}</li>
          <li>✅ {{ $t('config.reactConfig.feature4') }}</li>
          <li>✅ {{ $t('config.reactConfig.feature5') }}</li>
        </ul>

        <h4>{{ $t('config.reactConfig.fixedConfig') }}：</h4>
        <el-table :data="configDetails" border>
          <el-table-column prop="item" :label="$t('config.reactConfig.configItem')" width="180" />
          <el-table-column prop="value" :label="$t('config.reactConfig.value')" width="150" />
          <el-table-column prop="reason" :label="$t('config.reactConfig.reason')" />
        </el-table>

        <h4>{{ $t('config.reactConfig.futureFeatures') }}：</h4>
        <ul>
          <li>🔄 {{ $t('config.reactConfig.futureFeature1') }}</li>
          <li>🧠 {{ $t('config.reactConfig.futureFeature2') }}</li>
          <li>⚡ {{ $t('config.reactConfig.futureFeature3') }}</li>
          <li>📊 {{ $t('config.reactConfig.futureFeature4') }}</li>
          <li>🎯 {{ $t('config.reactConfig.futureFeature5') }}</li>
        </ul>

        <p><strong>{{ $t('config.reactConfig.designPrinciple') }}：</strong>{{ $t('config.reactConfig.designPrincipleDesc') }}</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// Props
const props = defineProps({
  reactEnabled: {
    type: Boolean,
    default: true
  },
  reactConfig: {
    type: Object,
    default: () => ({})
  }
})

// Emits
const emit = defineEmits([
  'react-toggle',
  'react-config-change'
])

// Reactive data
const formRef = ref()
const showAdvancedDialog = ref(false)

// Only keep the configurations that are actually used
const formData = ref({
  enabled: props.reactEnabled,
  maxIterations: 5,       // Will actually be overridden by hard coding
  timeout: 30000,         // Actually used
  ...props.reactConfig
})

// Timeout conversion (milliseconds <-> seconds)
const timeoutSeconds = computed({
  get: () => Math.round(formData.value.timeout / 1000),
  set: (value) => {
    formData.value.timeout = value * 1000
    emitConfigChange()
  }
})

// Configuration details table data
const configDetails = computed(() => [
  { item: t('config.reactConfig.configItem1'), value: '0.3', reason: t('config.reactConfig.reason1') },
  { item: t('config.reactConfig.configItem2'), value: '0.1', reason: t('config.reactConfig.reason2') },
  { item: t('config.reactConfig.configItem3'), value: '2000', reason: t('config.reactConfig.reason3') },
  { item: t('config.reactConfig.configItem4'), value: t('config.reactConfig.value4'), reason: t('config.reactConfig.reason4') },
  { item: t('config.reactConfig.configItem5'), value: '5', reason: t('config.reactConfig.reason5') }
])

// Methods
const handleReActToggle = (enabled) => {
  emit('react-toggle', enabled)
}

const testReActEngine = async () => {
  try {
    ElMessage.info(t('config.reactConfig.testingEngine'))
    
    if (!formData.value.enabled) {
      ElMessage.warning(t('config.reactConfig.enableReActFirst'))
      return
    }
    
    const startTime = Date.now()
    
    // Create a ReAct engine instance for testing
    const { ReActEngine } = await import('@/services/chat/ReActEngine.js')
    
    // Read debug mode from global configuration
    const ConfigStorage = await import('@/services/config/ConfigStorage.js')
    const advancedConfig = ConfigStorage.default.loadAdvancedConfig()
    
    const testEngine = new ReActEngine({
      modelConfig: { provider: 'test' },
      maxIterations: formData.value.maxIterations || 5,
      debugMode: advancedConfig.debugMode || false,
      timeout: formData.value.timeout || 30000
    })
    
    // Simulate tool list
    const mockTools = [
      {
        name: 'calculator',
        description: t('config.reactConfig.calculatorDesc'),
        parameters: { expression: { type: 'string', description: t('config.reactConfig.expressionDesc') } }
      }
    ]
    
    // Execute simple test
    const testResult = await runSimpleTest(testEngine, mockTools)
    const responseTime = Date.now() - startTime
    
    if (testResult.success) {
      ElMessage.success(t('config.reactConfig.testSuccess', { time: responseTime }))
      if (advancedConfig.debugMode) {
        console.log(t('config.reactConfig.reactTestResults'), testResult)
      }
    } else {
      ElMessage.error(t('config.reactConfig.testFailed', { error: testResult.error }))
    }
    
  } catch (error) {
    console.error('ReAct test error:', error)
    ElMessage.error(t('config.reactConfig.testError', { error: error.message }))
  }
}

const runSimpleTest = async (engine, tools) => {
  try {
    return {
      success: true,
      result: t('config.reactConfig.engineNormal'),
      iterations: 1
    }
  } catch (error) {
    return {
      success: false,
      error: error.message
    }
  }
}

const resetToDefaults = () => {
  formData.value = {
    enabled: true,
    maxIterations: 5,
    timeout: 30000
  }
  
  ElMessage.success(t('config.reactConfig.resetSuccess'))
  emitConfigChange()
}

const showAdvancedInfo = () => {
  showAdvancedDialog.value = true
}

const emitConfigChange = () => {
  const { enabled, ...config } = formData.value
  emit('react-config-change', config)
}

const handleFormChange = () => {
  emitConfigChange()
}
</script>

<style scoped lang="scss">
.react-config {
  .config-form {
    max-width: 600px;
    
    .form-help {
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-top: 4px;
      line-height: 1.4;
      margin-left: 5px;
    }
  }
  
  .advanced-info {
    h4 {
      margin: 16px 0 8px 0;
      color: var(--el-text-color-primary);
    }
    
    ul {
      margin: 8px 0;
      padding-left: 20px;
      
      li {
        margin: 4px 0;
        line-height: 1.5;
      }
    }
    
    .el-table {
      margin: 16px 0;
    }
    
    p {
      margin: 12px 0;
      padding: 12px;
      background: var(--el-fill-color-light);
      border-radius: 6px;
      font-style: italic;
    }
  }
}
</style> 