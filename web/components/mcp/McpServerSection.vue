<template>
  <div class="server-section">
    <div class="section-header">
      <div class="section-title-row">
        <h2 class="section-title">
          <el-icon>
            <component :is="sectionIcon" />
          </el-icon>
          {{ sectionTitle }} ({{ serverStats.total }})
        </h2>
        <div class="section-controls">
          <el-input
            v-model="searchKeyword"
            :placeholder="searchPlaceholder || t('mcp.configCenter.searchPlaceholder')"
            :prefix-icon="'Search'"
            size="default"
            style="width: 280px"
            clearable
            @input="handleSearchChange"
          />
          <el-select
            :model-value="currentPageSize"
            @change="handlePageSizeChange"
            size="default"
            style="width: 120px"
          >
            <el-option :label="t('mcp.configCenter.items6')" :value="6" />
            <el-option :label="t('mcp.configCenter.items8')" :value="8" />
            <el-option :label="t('mcp.configCenter.items12')" :value="12" />
            <el-option :label="t('mcp.configCenter.items18')" :value="18" />
            <el-option :label="t('common.all')" :value="serverStats.total" />
          </el-select>
        </div>
      </div>
      <div class="section-meta">
        <p class="section-description">
          {{ sectionDescription }}
        </p>
        <div class="filter-info" v-if="searchKeyword || serverStats.totalPages > 1">
          <span v-if="searchKeyword" class="search-result">
            {{ t('mcp.configCenter.foundResults', { count: serverStats.filtered }) }}
          </span>
          <span v-if="serverStats.totalPages > 1" class="page-info">
            {{ t('mcp.configCenter.pageInfo', { start: serverStats.start, end: serverStats.end }) }}
          </span>
        </div>
      </div>
    </div>
    
    <div class="server-grid">
      <McpServerCard
        v-for="(serverObj, index) in paginatedServers"
        :key="`${serverType}-${index}`"
        :server-name="Object.keys(serverObj)[0]"
        :server-config="Object.values(serverObj)[0]"
        :server-type="serverType"
        :embedded="embedded"
        @edit="$emit('edit', $event)"
        @add-to-editor="$emit('add-to-editor', $event)"
      />
    </div>
    
    <!-- Pagination controls -->
    <div class="section-pagination" v-if="serverStats.totalPages > 1">
      <el-pagination
        :current-page="currentPage"
        :page-size="currentPageSize"
        :total="serverStats.filtered"
        layout="prev, pager, next, jumper"
        :pager-count="5"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import McpServerCard from '@/components/mcp/McpServerCard.vue'

// Multi-language support
const { t } = useI18n()

// Props
const props = defineProps({
  serverType: {
    type: String,
    required: true
  },
  servers: {
    type: Array,
    default: () => []
  },
  sectionTitle: {
    type: String,
    required: true
  },
  sectionDescription: {
    type: String,
    required: true
  },
  sectionIcon: {
    type: [String, Object],
    required: true
  },
  embedded: {
    type: Boolean,
    default: false
  },
  searchPlaceholder: {
    type: String,
    default: ''
  }
})

// Emits
const emit = defineEmits(['edit', 'add-to-editor'])

// Reactive data
const searchKeyword = ref('')
const currentPage = ref(1)
const currentPageSize = ref(8)

// Filter servers function
const filteredServers = computed(() => {
  if (!props.servers || !props.servers.length) return []
  const keyword = searchKeyword.value.toLowerCase().trim()
  if (!keyword) return props.servers
  
  return props.servers.filter(serverObj => {
    const serverName = Object.keys(serverObj)[0].toLowerCase()
    const serverConfig = Object.values(serverObj)[0]
    const description = (serverConfig.description || '').toLowerCase()
    const url = (serverConfig.url || '').toLowerCase()
    
    return serverName.includes(keyword) || 
           description.includes(keyword) || 
           url.includes(keyword)
  })
})

// Paginated server list
const paginatedServers = computed(() => {
  const start = (currentPage.value - 1) * currentPageSize.value
  const end = start + currentPageSize.value
  return filteredServers.value.slice(start, end)
})

// Server statistics
const serverStats = computed(() => {
  const total = props.servers.length
  const filtered = filteredServers.value.length
  const totalPages = Math.ceil(filtered / currentPageSize.value)
  
  return {
    total,
    filtered,
    currentPage: currentPage.value,
    totalPages,
    pageSize: currentPageSize.value,
    start: (currentPage.value - 1) * currentPageSize.value + 1,
    end: Math.min(currentPage.value * currentPageSize.value, filtered)
  }
})

// Event handler methods
const handleSearchChange = (value) => {
  searchKeyword.value = value
  // Reset to first page when searching
  currentPage.value = 1
}

const handlePageChange = (page) => {
  currentPage.value = page
}

const handlePageSizeChange = (pageSize) => {
  currentPageSize.value = pageSize
  currentPage.value = 1
}

// Reset filter state
const resetFilters = () => {
  searchKeyword.value = ''
  currentPage.value = 1
}

// Watch server data changes, reset filter state
watch(() => props.servers, () => {
  resetFilters()
}, { deep: true })

// Expose methods to parent component
defineExpose({
  resetFilters
})
</script>

<style scoped lang="scss">
.server-section {
  margin-bottom: 40px;
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);

  .section-header {
    margin-bottom: 24px;

    .section-title-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      flex-wrap: wrap;
      gap: 16px;

      .section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 24px;
        font-weight: 600;
        color: #333;
        margin: 0;

        .el-icon {
          font-size: 28px;
        }
      }

      .section-controls {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;

        .el-input {
          :deep(.el-input__wrapper) {
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;

            &:hover {
              box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
            }

            &.is-focus {
              box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
            }
          }
        }

        .el-select {
          :deep(.el-input__wrapper) {
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;

            &:hover {
              box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
            }
          }
        }
      }
    }

    .section-meta {
      .section-description {
        color: #666;
        font-size: 14px;
        margin: 0 0 8px 0;
      }

      .filter-info {
        display: flex;
        gap: 16px;
        align-items: center;
        flex-wrap: wrap;

        .search-result {
          color: #409eff;
          font-size: 13px;
          font-weight: 500;
          background: rgba(64, 158, 255, 0.1);
          padding: 4px 8px;
          border-radius: 4px;
        }

        .page-info {
          color: #666;
          font-size: 13px;
          background: #f5f5f5;
          padding: 4px 8px;
          border-radius: 4px;
        }
      }
    }
  }

  .server-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: 20px;
  }

  .section-pagination {
    display: flex;
    justify-content: center;
    margin-top: 24px;
    padding: 20px 0;

    .el-pagination {
      :deep(.el-pager) {
        .number {
          border-radius: 6px;
          margin: 0 2px;
          transition: all 0.3s ease;

          &:hover {
            transform: translateY(-1px);
          }
        }

        .number.is-active {
          background: linear-gradient(135deg, #409eff 0%, #1d8ce0 100%);
          color: white;
          box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
        }
      }

      :deep(.btn-prev),
      :deep(.btn-next) {
        border-radius: 6px;
        transition: all 0.3s ease;

        &:hover {
          transform: translateY(-1px);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
      }
    }
  }
}

// Responsive design
@media (max-width: 1024px) {
  .server-section {
    .section-header .section-title-row {
      .section-controls {
        .el-input {
          width: 240px;
        }
      }
    }
  }
}

@media (max-width: 768px) {
  .server-section {
    .server-grid {
      grid-template-columns: 1fr;
    }

    .section-header .section-title-row {
      flex-direction: column;
      align-items: stretch;
      gap: 12px;

      .section-title {
        justify-content: center;
        font-size: 20px;

        .el-icon {
          font-size: 24px;
        }
      }

      .section-controls {
        justify-content: center;
        gap: 8px;

        .el-input {
          width: 100% !important;
          max-width: 280px;
        }

        .el-select {
          width: 120px;
        }
      }
    }

    .section-meta {
      .filter-info {
        justify-content: center;
        gap: 12px;

        .search-result,
        .page-info {
          font-size: 12px;
          padding: 3px 6px;
        }
      }
    }

    .section-pagination {
      padding: 16px 0;

      .el-pagination {
        :deep(.el-pagination__sizes) {
          display: none;
        }

        :deep(.el-pagination__jump) {
          margin-left: 8px;
        }
      }
    }
  }
}

// Embedded mode adaptation
.server-section {
  &:last-child {
    margin-bottom: 0;
  }
}
</style> 