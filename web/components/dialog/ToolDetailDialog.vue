<template>
  <el-dialog
      v-model="visible"
      :title="t('mcp.dialogs.toolDetail.title')"
      width="800px"
      :close-on-click-modal="false"
  >
    <div v-if="tool" class="tool-details" v-loading="loading" :element-loading-text="t('mcp.dialogs.toolDetail.loading')">
      <!-- Basic information -->
      <div class="detail-section">
        <h4 class="section-title">
          <el-icon><InfoFilled /></el-icon>
          {{ t('mcp.dialogs.toolDetail.basicInfo') }}
        </h4>
        <div class="detail-grid">
          <div class="detail-item">
            <label>{{ t('mcp.dialogs.toolDetail.toolName') }}：</label>
            <span class="tool-name">{{ tool.name }}</span>
          </div>
          <div class="detail-item" v-if="detailData?.module">
            <label>{{ t('mcp.dialogs.toolDetail.modulePath') }}：</label>
            <span class="module-path">{{ detailData.module }}</span>
          </div>
          <div class="detail-item" v-if="detailData?.return_type">
            <label>{{ t('mcp.dialogs.toolDetail.returnType') }}：</label>
            <span class="return-type">{{ detailData.return_type }}</span>
          </div>
          <div class="detail-item" v-if="detailData?.create_time">
            <label>{{ t('mcp.dialogs.toolDetail.createTime') }}：</label>
            <span class="create-time">{{ detailData.create_time }}</span>
          </div>
          <div class="detail-item">
            <label>{{ t('mcp.dialogs.toolDetail.author') }}：</label>
            <span class="common_detail_col">
              <el-tooltip
                  class="box-item"
                  effect="dark"
                  :content="t('mcp.dialogs.toolDetail.authorTooltip', { 
                    department: detailData?.author.department, 
                    email: detailData?.author.email ?? t('mcp.dialogs.toolDetail.noEmail') 
                  })"
                  placement="top-start"
              >
                {{ detailData?.author.name || t('mcp.dialogs.toolDetail.unknownAuthor') }}
              </el-tooltip>
            </span>
          </div>
          <div class="detail-item">
            <label>{{ t('mcp.dialogs.toolDetail.relatedProjects') }}：</label>
            <span class="common_detail_col">
              <el-tag
                  v-for="project in detailData?.author.project"
                  :key="project"
                  type="success"
                  size="small"
                  class="project-tag"
              >
                  {{ project }}
                </el-tag>
            </span>
          </div>
        </div>
      </div>

      <!-- Parameter information -->
      <div class="detail-section" v-if="hasParameterInfo()">
        <h4 class="section-title">
          <el-icon><Setting /></el-icon>
          {{ t('mcp.dialogs.toolDetail.parameterInfo') }}
        </h4>
        <el-tabs v-model="paramTabActive" type="border-card" class="param-tabs">
          <el-tab-pane v-if="detailData?.params?.length" :label="t('mcp.dialogs.toolDetail.parameterList')" name="params">
            <div class="params-list">
              <div
                  v-for="(param, index) in detailData.params"
                  :key="index"
                  class="param-item"
              >
                <el-tag type="info" size="small">{{ param }}</el-tag>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane v-if="tool.inputSchema && Object.keys(tool.inputSchema).length" :label="t('mcp.dialogs.toolDetail.inputSchema')" name="schema">
            <pre class="schema-display">{{ JSON.stringify(tool.inputSchema, null, 2) }}</pre>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- Load failure prompt -->
      <div v-if="error" class="error-section">
        <el-alert
            :title="t('mcp.dialogs.toolDetail.loadFailed')"
            :description="error"
            type="warning"
            show-icon
            :closable="false"
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">{{ t('common.close') }}</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  InfoFilled,
  Setting,
} from '@element-plus/icons-vue'
import { getToolDetail } from '@/api/mcp/mcpApi'

// Multi-language support
const { t } = useI18n()

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  tool: {
    type: Object,
    default: null
  }
})

// Emits
const emit = defineEmits(['update:visible'])

// Reactive data
const loading = ref(false)
const detailData = ref(null)
const error = ref('')
const paramTabActive = ref('params')

// Computed properties
const visible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

// Get tool description (prioritize detailed description from API)
const getToolDescription = () => {
  if (detailData.value?.description) {
    return detailData.value.description
  }
  if (props.tool?.description) {
    return props.tool.description
  }
  return t('mcp.dialogs.toolDetail.noDescription')
}

// Check if there is parameter information
const hasParameterInfo = () => {
  return (detailData.value?.params?.length > 0) ||
      (props.tool?.inputSchema && Object.keys(props.tool.inputSchema).length > 0)
}

// Get tool detail data
const fetchToolDetail = async (toolName) => {
  if (!toolName) return

  try {
    loading.value = true
    error.value = ''

    const response = await getToolDetail(toolName)

    if (response?.success && response?.data) {
      detailData.value = response.data
    } else {
      error.value = t('mcp.dialogs.toolDetail.notFound')
      console.warn(`⚠️ Tool detail response exception: ${toolName}`, response)
    }
  } catch (err) {
    console.error(`❌ Failed to get tool details: ${toolName}`, err)
    error.value = t('mcp.dialogs.toolDetail.fetchFailed', { error: err.message || t('mcp.dialogs.toolDetail.networkError') })
  } finally {
    loading.value = false
  }
}

// Handle close
const handleClose = () => {
  visible.value = false
}

// Watch dialog visibility
watch(() => props.visible, (newValue) => {
  if (newValue && props.tool) {
    // Reset state
    detailData.value = null
    error.value = ''
    paramTabActive.value = 'params'

    // Asynchronously get tool details
    fetchToolDetail(props.tool.name)
  }
})
</script>

<style scoped lang="scss">
.tool-details {
  .detail-section {
    margin-bottom: 24px;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    overflow: hidden;

    .section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0;
      padding: 12px 16px;
      background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
      border-bottom: 1px solid #e9ecef;
      font-size: 14px;
      font-weight: 600;
      color: #333;
    }

    .detail-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 16px;
      padding: 16px;
    }

    .detail-item {
      display: flex;
      flex-direction: column;
      gap: 4px;

      label {
        font-weight: 600;
        color: #666;
        font-size: 13px;
      }

      .common_detail_col, .tool-name, .function-name, .module-path, .return-type, .create-time {
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        background: #f8f9fa;
        padding: 6px 8px;
        border-radius: 4px;
        font-size: 12px;
        color: #333;
        border: 1px solid #e9ecef;
        word-break: break-all;
      }

      .tool-name {
        color: #409eff;
        font-weight: 600;
      }

      .function-name {
        color: #67c23a;
      }

      .module-path {
        color: #e6a23c;
      }

      .return-type {
        color: #f56c6c;
      }

      .create-time {
        color: #909399;
      }
    }

    .param-tabs {
      margin: 16px;

      .params-list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding: 16px;

        .param-item {
          .el-tag {
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 12px;
          }
        }
      }

      .schema-display {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 6px;
        padding: 12px;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        font-size: 12px;
        line-height: 1.5;
        overflow-x: auto;
        margin: 16px;
        color: #333;
      }
    }
  }

  .error-section {
    margin-top: 16px;
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}
</style>