<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="handleClose"
    :title="t('mcp.dialogs.statistics.title')"
    width="800px"
    :close-on-click-modal="false"
  >
    <div class="statistics-dialog">
      <el-tabs v-model="activeTab" type="border-card" class="statistics-tabs">
        <!-- Project statistics -->
        <el-tab-pane :label="t('mcp.dialogs.statistics.projectStats')" name="projects">
          <div class="tab-content">
            <div class="stats-summary">
              <div class="summary-item">
                <span class="label">{{ t('mcp.dialogs.statistics.totalProjects') }}:</span>
                <span class="value">{{ statisticsData?.projects?.length || 0 }}</span>
              </div>
              <div class="summary-item">
                <span class="label">
                  {{ t('mcp.dialogs.statistics.totalTools') }}<el-tooltip
                      :content="t('mcp.dialogs.statistics.toolsTooltip')"
                      placement="top"
                      effect="dark"
                  >
                    <el-icon class="help-icon">
                      <QuestionFilled />
                    </el-icon>
                  </el-tooltip>:
                </span>
                <span class="value">{{ projectTotalTools }}</span>
              </div>
            </div>
            
            <el-table
              :data="paginatedProjects"
              border
              stripe
              class="statistics-table"
            >
              <el-table-column
                prop="name"
                :label="t('mcp.dialogs.statistics.projectName')"
                width="120"
                align="center"
              />
              <el-table-column
                prop="server_count"
                :label="t('mcp.dialogs.statistics.serverCount')"
                width="120"
                align="center"
              />
              <el-table-column
                prop="tool_count"
                :label="t('mcp.dialogs.statistics.toolCount')"
                width="120"
                align="center"
              />
              <el-table-column
                prop="author_count"
                :label="t('mcp.dialogs.statistics.authorCount')"
                width="120"
                align="center"
              />
              <el-table-column
                prop="authors"
                :label="t('mcp.dialogs.statistics.authorList')"
                min-width="200"
                align="center"
              >
                <template #default="{ row }">
                  <div class="authors-list">
                    <el-tag
                      v-for="author in row.authors"
                      :key="author"
                      type="info"
                      size="small"
                      class="author-tag"
                    >
                      {{ author }}
                    </el-tag>
                  </div>
                </template>
              </el-table-column>
            </el-table>
            
            <div class="pagination-container">
              <el-pagination
                v-model:current-page="projectsCurrentPage"
                v-model:page-size="projectsPageSize"
                :page-sizes="[5, 10, 15, 20]"
                :total="statisticsData?.projects?.length || 0"
                layout="total, sizes, prev, pager, next, jumper"
                :small="false"
                background
              />
            </div>
          </div>
        </el-tab-pane>

        <!-- Author statistics -->
        <el-tab-pane :label="t('mcp.dialogs.statistics.authorStats')" name="authors">
          <div class="tab-content">
            <div class="stats-summary">
              <div class="summary-item">
                <span class="label">{{ t('mcp.dialogs.statistics.totalAuthors') }}:</span>
                <span class="value">{{ statisticsData?.author_summary?.length || 0 }}</span>
              </div>
              <div class="summary-item">
                <span class="label">{{ t('mcp.dialogs.statistics.totalTools') }}:</span>
                <span class="value">{{ authorTotalTools }}</span>
              </div>
            </div>
            
            <el-table
              :data="paginatedAuthors"
              border
              stripe
              class="statistics-table"
              :default-sort="{ prop: 'tool_count', order: 'descending' }"
            >
              <el-table-column
                prop="name"
                :label="t('mcp.dialogs.statistics.authorName')"
                min-width="150"
                align="center"
              />
              <el-table-column
                prop="sever_count"
                :label="t('mcp.dialogs.statistics.serverCount')"
                min-width="120"
                align="center"
              />
              <el-table-column
                prop="tool_count"
                :label="t('mcp.dialogs.statistics.toolCount')"
                min-width="120"
                align="center"
                sortable
              />
              <el-table-column
                :label="t('mcp.dialogs.statistics.toolPercentage')"
                min-width="120"
                align="center"
              >
                <template #default="{ row }">
                  <span class="percentage">
                    {{ ((row.tool_count / authorTotalTools) * 100).toFixed(1) }}%
                  </span>
                </template>
              </el-table-column>
            </el-table>
            
            <div class="pagination-container">
              <el-pagination
                v-model:current-page="authorsCurrentPage"
                v-model:page-size="authorsPageSize"
                :page-sizes="[5, 10, 15, 20]"
                :total="statisticsData?.author_summary?.length || 0"
                layout="total, sizes, prev, pager, next, jumper"
                :small="false"
                background
              />
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
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
import { QuestionFilled } from '@element-plus/icons-vue'

// Multi-language support
const { t } = useI18n()

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  statisticsData: {
    type: Object,
    default: () => ({})
  }
})

// Emits
const emit = defineEmits(['update:visible'])

// Reactive data
const activeTab = ref('projects')

// Pagination related data
const projectsCurrentPage = ref(1)
const projectsPageSize = ref(10)
const authorsCurrentPage = ref(1)
const authorsPageSize = ref(10)

// Computed properties
const projectTotalTools = computed(() => {
  return props.statisticsData?.projects?.reduce((total, project) => total + project.tool_count, 0) || 0
})

const authorTotalTools = computed(() => {
  return props.statisticsData?.author_summary?.reduce((total, author) => total + author.tool_count, 0) || 0
})

// Paginated data
const paginatedProjects = computed(() => {
  const projects = props.statisticsData?.projects || []
  const start = (projectsCurrentPage.value - 1) * projectsPageSize.value
  const end = start + projectsPageSize.value
  return projects.slice(start, end)
})

const paginatedAuthors = computed(() => {
  const authors = props.statisticsData?.author_summary || []
  const start = (authorsCurrentPage.value - 1) * authorsPageSize.value
  const end = start + authorsPageSize.value
  return authors.slice(start, end)
})

// Handle dialog close
const handleClose = (value) => {
  emit('update:visible', value || false)
}

// Watch dialog visibility, reset tabs and pagination
watch(() => props.visible, (newValue) => {
  if (newValue) {
    activeTab.value = 'projects'
    projectsCurrentPage.value = 1
    authorsCurrentPage.value = 1
  }
})
</script>

<style scoped lang="scss">
.statistics-dialog {
  .statistics-tabs {
    :deep(.el-tabs__content) {
      padding: 20px;
    }
  }

  .tab-content {
    .stats-summary {
      display: flex;
      justify-content: center;
      gap: 40px;
      margin-bottom: 20px;
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
          display: flex;
          align-items: center;
          gap: 4px;
          
          .help-icon {
            font-size: 14px;
            color: #909399;
            cursor: help;
            transition: color 0.3s ease;
            
            &:hover {
              color: #409eff;
            }
          }
        }

        .value {
          font-size: 18px;
          font-weight: 700;
          color: #333;
        }
      }
    }

    .statistics-table {
      margin-top: 16px;

      .authors-list {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        justify-content: center;

        .author-tag {
          margin: 0;
        }
      }

      .percentage {
        font-weight: 600;
        color: #409eff;
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

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}
</style> 