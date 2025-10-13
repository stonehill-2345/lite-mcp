<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="handleClose"
    :title="dialogTitle"
    width="90%"
    :close-on-click-modal="false"
    class="tools-detail-dialog"
  >
    <div class="tools-detail-content" v-loading="loading">
      <!-- Statistics Summary -->
      <div class="summary-section" v-if="!loading">
        <div class="summary-card">
          <div class="summary-item">
            <span class="label">{{ t('mcp.dialogs.toolsDetail.totalTools') }}:</span>
            <span class="value">{{ toolsList.length }}</span>
          </div>
          <div class="summary-item" v-if="targetType === 'project'">
            <span class="label">{{ t('mcp.dialogs.toolsDetail.project') }}:</span>
            <span class="value">{{ targetName }}</span>
          </div>
          <div class="summary-item" v-if="targetType === 'author'">
            <span class="label">{{ t('mcp.dialogs.toolsDetail.author') }}:</span>
            <span class="value">{{ targetName }}</span>
          </div>
        </div>
      </div>

      <!-- Tools List -->
      <div class="tools-list-section" v-if="!loading">
        <el-table
          :data="paginatedTools"
          border
          stripe
          class="tools-table"
          :empty-text="t('mcp.dialogs.toolsDetail.noTools')"
        >
          <el-table-column
            prop="name"
            :label="t('mcp.dialogs.toolsDetail.toolName')"
            min-width="150"
            align="center"
          >
            <template #default="{ row }">
              <el-tag type="primary" size="small">{{ row.name }}</el-tag>
            </template>
          </el-table-column>
          
          <el-table-column
            prop="description"
            :label="t('mcp.dialogs.toolsDetail.description')"
            min-width="200"
            show-overflow-tooltip
          />
          
          <el-table-column
            prop="server_name"
            :label="t('mcp.dialogs.toolsDetail.serverName')"
            min-width="150"
            align="center"
          >
            <template #default="{ row }">
              <el-tag type="info" size="small">{{ row.server_name }}</el-tag>
            </template>
          </el-table-column>
          
          <el-table-column
            prop="author.name"
            :label="t('mcp.dialogs.toolsDetail.authorName')"
            min-width="120"
            align="center"
          />
          
          <el-table-column
            prop="author.department"
            :label="t('mcp.dialogs.toolsDetail.department')"
            min-width="120"
            align="center"
          />
          
          <el-table-column
            :label="t('mcp.dialogs.toolsDetail.parameters')"
            min-width="200"
            align="center"
          >
            <template #default="{ row }">
              <div class="parameters-list">
                <el-tag
                  v-for="param in row.parameters"
                  :key="param"
                  type="warning"
                  size="small"
                  class="param-tag"
                >
                  {{ param }}
                </el-tag>
                <span v-if="!row.parameters || row.parameters.length === 0" class="no-params">
                  {{ t('mcp.dialogs.toolsDetail.noParameters') }}
                </span>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column
            prop="return_type"
            :label="t('mcp.dialogs.toolsDetail.returnType')"
            min-width="120"
            align="center"
          >
            <template #default="{ row }">
              <el-tag type="success" size="small" v-if="row.return_type">
                {{ row.return_type }}
              </el-tag>
              <span v-else class="no-return-type">-</span>
            </template>
          </el-table-column>
        </el-table>
        
        <!-- Pagination -->
        <div class="pagination-container" v-if="toolsList.length > pageSize">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="toolsList.length"
            layout="total, sizes, prev, pager, next, jumper"
            background
          />
        </div>
      </div>
      
      <!-- Empty State -->
      <el-empty
        v-if="!loading && toolsList.length === 0"
        :description="t('mcp.dialogs.toolsDetail.noTools')"
        :image-size="120"
      />
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleCloseClick">{{ t('common.close') }}</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getProjectTools, getAuthorTools } from '@/api/mcp/mcpApi'

// Multi-language support
const { t } = useI18n()

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  targetType: {
    type: String,
    default: 'project', // 'project' or 'author'
    validator: (value) => ['project', 'author'].includes(value)
  },
  targetName: {
    type: String,
    default: ''
  }
})

// Emits
const emit = defineEmits(['update:visible'])

// Reactive data
const loading = ref(false)
const toolsList = ref([])
const currentPage = ref(1)
const pageSize = ref(20)

// Computed properties
const dialogTitle = computed(() => {
  if (props.targetType === 'project') {
    return t('mcp.dialogs.toolsDetail.projectToolsTitle', { name: props.targetName })
  } else {
    return t('mcp.dialogs.toolsDetail.authorToolsTitle', { name: props.targetName })
  }
})

const paginatedTools = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return toolsList.value.slice(start, end)
})

// Methods
const fetchToolsList = async () => {
  if (!props.targetName) return
  
  try {
    loading.value = true
    let response
    
    if (props.targetType === 'project') {
      response = await getProjectTools(props.targetName)
    } else {
      response = await getAuthorTools(props.targetName)
    }
    
    if (response.success) {
      toolsList.value = response.data || []
    } else {
      throw new Error(response.message || 'Failed to fetch tools')
    }
  } catch (error) {
    console.error('Failed to fetch tools list:', error)
    ElMessage.error(t('mcp.dialogs.toolsDetail.fetchError') + ': ' + error.message)
    toolsList.value = []
  } finally {
    loading.value = false
  }
}

// Handle dialog close from el-dialog's update:model-value event
const handleClose = (value) => {
  emit('update:visible', value || false)
}

// Handle close button click
const handleCloseClick = () => {
  emit('update:visible', false)
}

// Watch dialog visibility and target changes
watch(() => props.visible, (newValue) => {
  if (newValue) {
    currentPage.value = 1
    fetchToolsList()
  } else {
    toolsList.value = []
  }
})

watch(() => [props.targetType, props.targetName], () => {
  if (props.visible) {
    currentPage.value = 1
    fetchToolsList()
  }
})
</script>

<style scoped lang="scss">
.tools-detail-dialog {
  .tools-detail-content {
    .summary-section {
      margin-bottom: 20px;
      
      .summary-card {
        display: flex;
        justify-content: center;
        gap: 40px;
        padding: 16px;
        background: #f5f7fa;
        border-radius: 8px;
        
        .summary-item {
          display: flex;
          align-items: center;
          gap: 8px;
          
          .label {
            font-weight: 600;
            color: #666;
          }
          
          .value {
            font-size: 18px;
            font-weight: 700;
            color: #333;
          }
        }
      }
    }
    
    .tools-list-section {
      .tools-table {
        .parameters-list {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          justify-content: center;
          
          .param-tag {
            margin: 0;
          }
          
          .no-params {
            color: #999;
            font-style: italic;
          }
        }
        
        .no-return-type {
          color: #999;
        }
      }
      
      .pagination-container {
        display: flex;
        justify-content: center;
        margin-top: 20px;
        padding: 16px 0;
      }
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}

// Responsive Design
.tools-detail-dialog {
  // Ensure dialog has maximum width limit on large screens
  :deep(.el-dialog) {
    max-width: 1400px;
    margin: 5vh auto;
  }
}

@media (max-width: 1200px) {
  .tools-detail-dialog {
    :deep(.el-dialog) {
      width: 95% !important;
    }
  }
}

@media (max-width: 768px) {
  .tools-detail-dialog {
    :deep(.el-dialog) {
      width: 98% !important;
      margin: 2vh auto;
    }
    
    .tools-detail-content {
      .summary-section .summary-card {
        flex-direction: column;
        gap: 16px;
        text-align: center;
      }
      
      .tools-list-section .tools-table {
        :deep(.el-table__body-wrapper) {
          overflow-x: auto;
        }
        
        // Hide some less important columns on small screens
        :deep(.el-table__header th:nth-child(5)),
        :deep(.el-table__body td:nth-child(5)) {
          display: none; // Hide department column
        }
      }
    }
  }
}

@media (max-width: 480px) {
  .tools-detail-dialog {
    :deep(.el-dialog) {
      width: 100% !important;
      margin: 0;
      height: 100vh;
      border-radius: 0;
    }
    
    .tools-detail-content {
      .tools-list-section .tools-table {
        // Further simplify table on extra small screens
        :deep(.el-table__header th:nth-child(4)),
        :deep(.el-table__body td:nth-child(4)) {
          display: none; // Hide author column
        }
      }
    }
  }
}
</style>
