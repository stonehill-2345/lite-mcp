<template>
  <el-dialog
    v-model="visible"
    :title="t('mcp.externalManager.title')"
    width="90%"
    :before-close="handleClose"
    destroy-on-close
    class="external-mcp-dialog"
  >
    <div class="external-mcp-manager">
      <!-- Top toolbar -->
      <div class="toolbar">
        <div class="toolbar-left">
          <el-button
            type="primary"
            :icon="Plus"
            @click="showCreateDialog"
          >
            {{ t('mcp.externalManager.createInstance') }}
          </el-button>
          <el-button
            :icon="Refresh"
            @click="refreshData"
            :loading="loading"
          >
            {{ t('common.refresh') }}
          </el-button>
          <el-button
            :icon="Operation"
            @click="showBatchOperations = !showBatchOperations"
          >
            {{ t('mcp.externalManager.batchOperations') }}
          </el-button>
        </div>
        <div class="toolbar-right">
          <el-input
            v-model="searchKeyword"
            :placeholder="t('mcp.externalManager.searchPlaceholder')"
            :prefix-icon="Search"
            style="width: 300px"
            clearable
          />
          <el-select
            v-model="statusFilter"
            :placeholder="t('mcp.externalManager.allStatus')"
            style="width: 120px"
            clearable
          >
            <el-option :label="t('mcp.externalManager.enabled')" value="enabled" />
            <el-option :label="t('mcp.externalManager.disabled')" value="disabled" />
          </el-select>
        </div>
      </div>

      <!-- Batch operations panel -->
      <transition name="el-collapse-transition">
        <div v-show="showBatchOperations" class="batch-operations">
          <div class="batch-toolbar">
            <span class="batch-title">{{ t('mcp.externalManager.selectedCount', { count: selectedInstances.length }) }}</span>
            <div class="batch-buttons">
              <el-button
                size="small"
                :disabled="selectedInstances.length === 0"
                @click="batchEnable"
              >
                {{ t('mcp.externalManager.batchEnable') }}
              </el-button>
              <el-button
                size="small"
                :disabled="selectedInstances.length === 0"
                @click="batchDisable"
              >
                {{ t('mcp.externalManager.batchDisable') }}
              </el-button>
              <el-button
                size="small"
                type="danger"
                :disabled="selectedInstances.length === 0"
                @click="batchDelete"
              >
                {{ t('mcp.externalManager.batchDelete') }}
              </el-button>
            </div>
          </div>
        </div>
      </transition>

      <!-- Statistics -->
      <div class="stats-bar">
        <el-tag>{{ t('mcp.externalManager.totalInstances') }}: {{ statusData.total_instances }}</el-tag>
        <el-tag type="success">{{ t('mcp.externalManager.enabledInstances') }}: {{ statusData.enabled_instances }}</el-tag>
        <el-tag type="info">{{ t('mcp.externalManager.disabledInstances') }}: {{ statusData.disabled_instances }}</el-tag>
        <el-tag v-if="hasChanges" type="warning" class="refresh-pending">
          <el-icon><Loading /></el-icon>
          {{ t('mcp.externalManager.refreshPending') }}
        </el-tag>
      </div>

      <!-- Instance list table -->
      <div class="table-container">
        <el-table
          ref="tableRef"
          v-loading="loading"
          :data="paginatedInstances"
          @selection-change="handleSelectionChange"
          :row-key="'instance_id'"
          stripe
          height="500"
        >
          <el-table-column
            v-if="showBatchOperations"
            type="selection"
            width="55"
          />
          
          <el-table-column
            prop="instance_name"
            :label="t('mcp.externalManager.instanceName')"
            width="180"
            show-overflow-tooltip
          >
            <template #default="{ row }">
              <div class="instance-name">
                <el-icon class="instance-icon">
                  <Connection />
                </el-icon>
                <span>{{ row.instance_name }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column
            prop="template_name"
            :label="t('mcp.externalManager.templateName')"
            width="150"
            show-overflow-tooltip
          />

          <el-table-column
            :label="t('mcp.externalManager.status')"
            width="100"
          >
            <template #default="{ row }">
              <el-tag
                :type="row.enabled ? 'success' : 'info'"
                size="small"
              >
                {{ row.enabled ? t('mcp.externalManager.enabled') : t('mcp.externalManager.disabled') }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column
            prop="description"
            :label="t('mcp.externalManager.description')"
            min-width="200"
            show-overflow-tooltip
          />

          <el-table-column
            :label="t('mcp.externalManager.command')"
            min-width="250"
            show-overflow-tooltip
          >
            <template #default="{ row }">
              <el-text class="command-text" truncated>
                <code>{{ row.command }} {{ (row.args || []).join(' ') }}</code>
              </el-text>
            </template>
          </el-table-column>

          <el-table-column
            :label="t('mcp.externalManager.environment')"
            width="120"
          >
            <template #default="{ row }">
              <el-tag
                v-if="Object.keys(row.env || {}).length > 0"
                size="small"
                type="warning"
              >
                {{ Object.keys(row.env || {}).length }} {{ t('mcp.externalManager.envVars') }}
              </el-tag>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>

          <el-table-column
            :label="t('common.actions')"
            width="220"
            fixed="right"
          >
            <template #default="{ row }">
              <div class="action-buttons">
                <el-switch
                  v-model="row.enabled"
                  size="small"
                  :loading="row._toggling"
                  @change="toggleInstanceStatus(row)"
                />
                <el-button
                  size="small"
                  :icon="Edit"
                  @click="editInstance(row)"
                >
                  {{ t('common.edit') }}
                </el-button>
                <el-button
                  size="small"
                  type="danger"
                  :icon="Delete"
                  :disabled="row.enabled"
                  @click="deleteInstance(row)"
                  :title="row.enabled ? t('mcp.externalManager.cannotDeleteEnabledTooltip') : ''"
                >
                  {{ t('common.delete') }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
        
        <!-- Pagination component -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="pageSizes"
            :total="total"
            layout="total, sizes, prev, pager, next, jumper"
            background
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </div>

    <!-- Create/Edit instance dialog -->
    <InstanceForm
      v-model:visible="formDialogVisible"
      :instance="currentInstance"
      :is-edit-mode="isEditMode"
      @success="handleFormSuccess"
    />
  </el-dialog>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Refresh,
  Search,
  Edit,
  Delete,
  Connection,
  Operation,
  Loading
} from '@element-plus/icons-vue'

import {
  getExternalMcpInstances,
  getExternalMcpStatus,
  deleteExternalMcpInstance,
  enableExternalMcpInstance,
  disableExternalMcpInstance
} from '@/api/mcp/mcpApi'
import InstanceForm from './InstanceForm.vue'

// Multi-language support
const { t } = useI18n()

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits(['update:visible', 'refresh'])

// Reactive data
const loading = ref(false)
const instances = ref({})
const statusData = ref({
  total_instances: 0,
  enabled_instances: 0,
  disabled_instances: 0
})

// Search and filtering
const searchKeyword = ref('')
const statusFilter = ref('')

// Pagination
const currentPage = ref(1)
const pageSize = ref(10)
const pageSizes = [10, 20, 50, 100]

// Batch operations
const showBatchOperations = ref(false)
const selectedInstances = ref([])
const tableRef = ref()

// Form dialog
const formDialogVisible = ref(false)
const currentInstance = ref(null)
const isEditMode = ref(false)

// Refresh status tracking
const hasChanges = ref(false) // Whether there are changes that need refresh

// Computed properties
const visible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

// Filtered instance list (not paginated)
const filteredInstances = computed(() => {
  let result = Object.entries(instances.value).map(([id, instance]) => ({
    instance_id: id,
    ...instance
  }))

  // Search filtering
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(instance => 
      instance.instance_name.toLowerCase().includes(keyword) ||
      instance.template_name.toLowerCase().includes(keyword) ||
      (instance.description || '').toLowerCase().includes(keyword) ||
      instance.command.toLowerCase().includes(keyword)
    )
  }

  // Status filtering
  if (statusFilter.value === 'enabled') {
    result = result.filter(instance => instance.enabled)
  } else if (statusFilter.value === 'disabled') {
    result = result.filter(instance => !instance.enabled)
  }

  return result
})

// Paginated instance list
const paginatedInstances = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredInstances.value.slice(start, end)
})

// Total count
const total = computed(() => filteredInstances.value.length)

// Methods
const loadData = async () => {
  loading.value = true
  try {
    const [instancesData, statusDataRes] = await Promise.all([
      getExternalMcpInstances(),
      getExternalMcpStatus()
    ])

    instances.value = instancesData
    statusData.value = statusDataRes
  } catch (error) {
    ElMessage.error(t('mcp.externalManager.loadDataError') + ': ' + error.message)
    console.error('Failed to load external MCP data:', error)
  } finally {
    loading.value = false
  }
}

const refreshData = async () => {
  await loadData()
  ElMessage.success(t('mcp.externalManager.refreshSuccess'))
}

const showCreateDialog = () => {
  currentInstance.value = null
  isEditMode.value = false
  formDialogVisible.value = true
}

const editInstance = (instance) => {
  currentInstance.value = { ...instance }
  isEditMode.value = true
  formDialogVisible.value = true
}

const deleteInstance = async (instance) => {
  try {
    // Check if instance is enabled
    if (instance.enabled) {
      ElMessage.warning(t('mcp.externalManager.cannotDeleteEnabled', { name: instance.instance_name }))
      return
    }

    await ElMessageBox.confirm(
      t('mcp.externalManager.deleteConfirm', { name: instance.instance_name }),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    await deleteExternalMcpInstance(instance.instance_id)
    ElMessage.success(t('mcp.externalManager.deleteSuccess'))
    hasChanges.value = true
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('mcp.externalManager.deleteError') + ': ' + error.message)
      console.error('Failed to delete instance:', error)
    }
  }
}

const toggleInstanceStatus = async (instance) => {
  instance._toggling = true
  try {
    if (instance.enabled) {
      await enableExternalMcpInstance(instance.instance_id)
      ElMessage.success(t('mcp.externalManager.enableSuccess', { name: instance.instance_name }))
    } else {
      await disableExternalMcpInstance(instance.instance_id)
      ElMessage.success(t('mcp.externalManager.disableSuccess', { name: instance.instance_name }))
    }
    
    // Mark changes, refresh uniformly when closing dialog
    hasChanges.value = true
    
    // Immediately refresh local data
    await loadData()
    
  } catch (error) {
    console.log(error)
    // Rollback status
    instance.enabled = !instance.enabled
    ElMessage.error(
      (instance.enabled ? t('mcp.externalManager.enableError') : t('mcp.externalManager.disableError')) + 
      ': ' + error.message
    )
  } finally {
    instance._toggling = false
  }
}

const handleSelectionChange = (selection) => {
  selectedInstances.value = selection
}

const batchEnable = async () => {
  const disabledInstances = selectedInstances.value.filter(instance => !instance.enabled)
  if (disabledInstances.length === 0) {
    ElMessage.warning(t('mcp.externalManager.noDisabledSelected'))
    return
  }

  try {
    await Promise.all(
      disabledInstances.map(instance => 
        enableExternalMcpInstance(instance.instance_id)
      )
    )
    ElMessage.success(t('mcp.externalManager.batchEnableSuccess', { count: disabledInstances.length }))
    hasChanges.value = true
    await loadData()
  } catch (error) {
    ElMessage.error(t('mcp.externalManager.batchEnableError') + ': ' + error.message)
    console.error('Batch enable failed:', error)
  }
}

const batchDisable = async () => {
  const enabledInstances = selectedInstances.value.filter(instance => instance.enabled)
  if (enabledInstances.length === 0) {
    ElMessage.warning(t('mcp.externalManager.noEnabledSelected'))
    return
  }

  try {
    await Promise.all(
      enabledInstances.map(instance => 
        disableExternalMcpInstance(instance.instance_id)
      )
    )
    ElMessage.success(t('mcp.externalManager.batchDisableSuccess', { count: enabledInstances.length }))
    hasChanges.value = true
    await loadData()
  } catch (error) {
    ElMessage.error(t('mcp.externalManager.batchDisableError') + ': ' + error.message)
    console.error('Batch disable failed:', error)
  }
}

const batchDelete = async () => {
  if (selectedInstances.value.length === 0) {
    ElMessage.warning(t('mcp.externalManager.noInstancesSelected'))
    return
  }

  // Check if there are enabled instances
  const enabledInstances = selectedInstances.value.filter(instance => instance.enabled)
  if (enabledInstances.length > 0) {
    ElMessage.warning(t('mcp.externalManager.cannotDeleteEnabledBatch', { 
      count: enabledInstances.length,
      names: enabledInstances.map(i => i.instance_name).join(', ')
    }))
    return
  }

  try {
    await ElMessageBox.confirm(
      t('mcp.externalManager.batchDeleteConfirm', { count: selectedInstances.value.length }),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    await Promise.all(
      selectedInstances.value.map(instance => 
        deleteExternalMcpInstance(instance.instance_id)
      )
    )
    ElMessage.success(t('mcp.externalManager.batchDeleteSuccess', { count: selectedInstances.value.length }))
    hasChanges.value = true
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('mcp.externalManager.batchDeleteError') + ': ' + error.message)
      console.error('Batch delete failed:', error)
    }
  }
}

const handleFormSuccess = async () => {
  hasChanges.value = true
  await loadData()
  ElMessage.success(isEditMode.value ? t('mcp.externalManager.updateSuccess') : t('mcp.externalManager.createSuccess'))
}

const handleClose = async () => {
  // If there are changes, perform final refresh when closing dialog
  if (hasChanges.value) {
    console.log('External MCP manager closed, waiting for service registration to complete before refreshing config...')
    
    // Give sufficient time for service registration/unregistration, then refresh config
    setTimeout(() => {
      emit('refresh')
    }, 1000) // 1 second delay to ensure service is fully registered/unregistered
    
    hasChanges.value = false
  }
  visible.value = false
}

// Pagination event handling
const handleSizeChange = (newSize) => {
  pageSize.value = newSize
  currentPage.value = 1 // Reset to first page
}

const handleCurrentChange = (newPage) => {
  currentPage.value = newPage
}

// Reset pagination when searching
const resetPagination = () => {
  currentPage.value = 1
}

// Watch dialog visibility status
watch(visible, (newVal) => {
  if (newVal) {
    loadData()
  }
})

// Watch search and filter condition changes, reset pagination
watch([searchKeyword, statusFilter], () => {
  resetPagination()
})

// When component is mounted
onMounted(() => {
  if (visible.value) {
    loadData()
  }
})
</script>

<style scoped lang="scss">
.external-mcp-dialog {
  :deep(.el-dialog) {
    border-radius: 16px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
  }

  :deep(.el-dialog__header) {
    padding: 24px 24px 0 24px;
    border-bottom: 1px solid #f0f0f0;
    
    .el-dialog__title {
      font-size: 20px;
      font-weight: 600;
      color: #303133;
    }
  }

  :deep(.el-dialog__body) {
    padding: 24px;
  }
}

.external-mcp-manager {
  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding: 16px;
    background: #f8f9fa;
    border-radius: 12px;
    flex-wrap: wrap;
    gap: 12px;

    .toolbar-left {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    .toolbar-right {
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }
  }

  .batch-operations {
    margin-bottom: 16px;
    padding: 12px 16px;
    background: linear-gradient(135deg, #e3f2fd 0%, #f0f8ff 100%);
    border: 1px solid #e1f5fe;
    border-radius: 8px;

    .batch-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .batch-title {
        font-weight: 500;
        color: #1976d2;
      }

      .batch-buttons {
        display: flex;
        gap: 8px;
      }
    }
  }

  .stats-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;

    .refresh-pending {
      animation: pulse 1.5s ease-in-out infinite;
      
      .el-icon {
        animation: spin 1s linear infinite;
      }
    }
  }

  .table-container {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);

    .pagination-container {
      padding: 16px;
      background: #fff;
      border-top: 1px solid #f0f0f0;
      display: flex;
      justify-content: center;
    }

    :deep(.el-table) {
      .instance-name {
        display: flex;
        align-items: center;
        gap: 8px;

        .instance-icon {
          color: #409eff;
        }
      }

      .command-text {
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        font-size: 12px;
        background: #f5f5f5;
        padding: 2px 6px;
        border-radius: 4px;
      }

      .action-buttons {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .text-muted {
        color: #909399;
      }
    }
  }
}

// Responsive design
@media (max-width: 1200px) {
  .external-mcp-dialog {
    :deep(.el-dialog) {
      width: 95% !important;
      margin: 20px auto;
    }
  }

  .external-mcp-manager {
    .toolbar {
      flex-direction: column;
      align-items: stretch;

      .toolbar-left,
      .toolbar-right {
        justify-content: center;
      }
    }

    .table-container {
      :deep(.el-table) {
        font-size: 13px;
      }
    }
  }
}

@media (max-width: 768px) {
  .external-mcp-manager {
    .stats-bar {
      justify-content: center;
    }

    .batch-operations {
      .batch-toolbar {
        flex-direction: column;
        gap: 12px;
        align-items: center;

        .batch-buttons {
          flex-wrap: wrap;
          justify-content: center;
        }
      }
    }
  }
}

// Animation effects
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}</style>
