<template>
  <div class="mcp-config-container" :class="{ 'embedded-mode': embedded }">
    <!-- Page Header -->
    <div v-if="!embedded" class="page-header">
      <div class="header-content">
        <div class="title-section">
          <h1 class="page-title">{{ $t('mcp.configCenter.title') }}</h1>
          <p class="page-subtitle">
            {{ $t('mcp.configCenter.subtitle') }}
          </p>
        </div>
        <div class="header-actions">
          <!-- API Address Display and Edit -->
          <div class="api-url-section">
            <div class="api-url-label">{{ $t('mcp.configCenter.apiAddress') }}</div>
            <div class="api-url-input-group" v-if="isEditingApiUrl">
              <el-input
                v-model="tempApiUrl"
                :placeholder="defaultMcpApiUrl"
                size="default"
                class="api-url-input"
                @keyup.enter="confirmEditApiUrl"
                @keyup.esc="cancelEditApiUrl"
              />
              <el-button
                :icon="Check"
                type="success"
                size="default"
                @click="confirmEditApiUrl"
              />
              <el-button
                :icon="Close"
                size="default"
                @click="cancelEditApiUrl"
              />
            </div>
            <div class="api-url-display-group" v-else>
              <code class="api-url-text">{{ currentApiUrl }}</code>
              <el-button
                :icon="Edit"
                size="small"
                text
                @click="startEditApiUrl"
                :title="$t('mcp.configCenter.editApiAddress')"
              />
              <el-button
                size="small"
                text
                @click="resetToDefaultApiUrl"
                :title="$t('mcp.configCenter.resetToDefault')"
                v-if="currentApiUrl !== getMcpApiUrl()"
              >
                {{ $t('common.reset') }}
              </el-button>
            </div>
          </div>

          <el-button
            type="primary"
            :icon="Refresh"
            @click="refreshConfig"
            :loading="loading"
            size="large"
          >
            {{ $t('mcp.configCenter.refreshConfig') }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- Statistics Information -->
    <div v-if="!embedded && configData" class="stats-section">
      <div class="stats-grid">
        <div class="stat-card total" style="cursor: default">
          <div class="stat-icon">
            <el-icon><DataBoard /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">
              {{ configData?.servers_count || 0 }}
            </div>
            <div class="stat-label">{{ $t('mcp.configCenter.stats.totalServers') }}</div>
          </div>
        </div>
        <div
          class="stat-card stdio"
          :class="{ active: activeServerType === 'stdio' }"
          @click="handleStatCardClick('stdio')"
        >
          <div class="stat-icon">
            <el-icon><Monitor /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">
              {{ (configData?.stdio || []).length }}
            </div>
            <div class="stat-label">{{ $t('mcp.configCenter.stats.stdioServers') }}</div>
          </div>
        </div>
        <div
          class="stat-card sse"
          :class="{ active: activeServerType === 'sse' }"
          @click="handleStatCardClick('sse')"
        >
          <div class="stat-icon">
            <el-icon><Connection /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">
              {{ (configData?.sse || []).length }}
            </div>
            <div class="stat-label">{{ $t('mcp.configCenter.stats.sseServers') }}</div>
          </div>
        </div>

        <div
          class="stat-card streamable"
          :class="{ active: activeServerType === 'streamable' }"
          @click="handleStatCardClick('streamable')"
        >
          <div class="stat-icon">
            <el-icon><Link /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">
              {{ (configData?.streamable || []).length }}
            </div>
            <div class="stat-label">{{ $t('mcp.configCenter.stats.streamableServers') }}</div>
          </div>
        </div>

        <div
          class="stat-card tools clickable"
          @click="handleToolsStatClick"
          v-loading="statisticsLoading"
          :class="{ 'has-data': statisticsData?.total_tools }"
        >
          <div class="stat-icon">
            <el-icon><Tools /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number" :class="{ 'clickable-number': statisticsData?.total_tools }">
              {{ statisticsData?.total_tools || 0 }}
            </div>
            <div class="stat-label">{{ $t('mcp.configCenter.stats.totalTools') }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Server Configuration List -->
    <div class="config-content" v-loading="loading">
      <el-empty
        v-if="!loading && (!configData || totalServers === 0)"
        :description="$t('mcp.configCenter.emptyState')"
        :image-size="200"
      />

      <div v-else class="server-sections">
        <!-- SSE Servers -->
        <McpServerSection
            v-if="configData?.sse && configData.sse.length"
            ref="sseSectionRef"
            server-type="sse"
            :servers="configData.sse"
            :section-title="$t('mcp.configCenter.serverTypes.sse')"
            :section-description="$t('mcp.configCenter.serverTypes.sseDesc')"
            :section-icon="Connection"
            :embedded="embedded"
            @add-to-editor="handleAddToEditor"
        />

        <!-- Streamable HTTP Servers -->
        <McpServerSection
            v-if="configData?.streamable && configData.streamable.length"
            ref="streamableSectionRef"
            server-type="streamable-http"
            :servers="configData.streamable"
            :section-title="$t('mcp.configCenter.serverTypes.streamable')"
            :section-description="$t('mcp.configCenter.serverTypes.streamableDesc')"
            :section-icon="Link"
            :embedded="embedded"
            @add-to-editor="handleAddToEditor"
        />

        <!-- STDIO Servers -->
        <McpServerSection
            v-if="configData?.stdio && configData.stdio.length"
            ref="stdioSectionRef"
            server-type="stdio"
            :servers="configData.stdio"
            :section-title="$t('mcp.configCenter.serverTypes.stdio')"
            :section-description="$t('mcp.configCenter.serverTypes.stdioDesc')"
            :section-icon="Monitor"
            :embedded="embedded"
            @add-to-editor="handleAddToEditor"
        />

      </div>
    </div>

    <!-- Proxy Information -->
    <div class="proxy-info" v-if="configData?.proxy_info">
      <el-card class="info-card">
        <template #header>
          <div class="card-header">
            <span>{{ $t('mcp.configCenter.proxy.title') }}</span>
            <el-tag type="success">{{ configData?.mode }}</el-tag>
          </div>
        </template>
        <div class="proxy-details">
          <div class="detail-item">
            <span class="label">{{ $t('mcp.configCenter.proxy.host') }}</span>
            <code>{{ configData?.proxy_info?.host }}</code>
          </div>
          <div class="detail-item">
            <span class="label">{{ $t('mcp.configCenter.proxy.port') }}</span>
            <code>{{ configData?.proxy_info?.port }}</code>
          </div>
          <div class="detail-item">
            <span class="label">{{ $t('mcp.configCenter.proxy.baseUrl') }}</span>
            <code>{{ configData?.proxy_info?.base_url }}</code>
          </div>
          <div class="detail-item">
            <span class="label">{{ $t('mcp.configCenter.proxy.generatedAt') }}</span>
            <code>{{ configData?.generated_at }}</code>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Statistics Details Dialog -->
    <StatisticsDialog
      v-model:visible="showStatisticsDialog"
      :statistics-data="statisticsData"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import {
  Check,
  Close,
  Connection,
  DataBoard,
  Edit,
  Link,
  Monitor,
  Refresh,
  Tools
} from '@element-plus/icons-vue'
import McpServerSection from '@/components/mcp/McpServerSection.vue'
import StatisticsDialog from '@/components/dialog/StatisticsDialog.vue'

import {
  getMcpApiUrl,
  getMcpConfig,
  getMcpConfigWithUrl,
  getMcpStatistics
} from '@/api/mcp/mcpApi'

// Props
const props = defineProps({
  embedded: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits(['add-to-editor'])

// Internationalization
const { t } = useI18n()

// Reactive data
const loading = ref(false)
const configData = ref(null)

// Current API address related
const currentApiUrl = ref(getMcpApiUrl())
const isEditingApiUrl = ref(false)
const tempApiUrl = ref('')

// Statistics related
const activeServerType = ref('sse')

// Tool statistics data
const statisticsData = ref(null)
const statisticsLoading = ref(false)

// Dialog control
const showStatisticsDialog = ref(false)

// Server section references
const stdioSectionRef = ref(null)
const sseSectionRef = ref(null)
const streamableSectionRef = ref(null)

// Computed properties
const totalServers = computed(() => {
  if (!configData.value) return 0
  return (
    (configData.value?.stdio?.length || 0) +
    (configData.value?.sse?.length || 0) +
    (configData.value?.streamable?.length || 0)
  )
})

// Fetch configuration data
const fetchConfig = async (customUrl = null) => {
  try {
    loading.value = true
    let response
    if (customUrl && customUrl !== getMcpApiUrl()) {
      response = await getMcpConfigWithUrl(customUrl)
    } else {
      response = await getMcpConfig()
    }
    configData.value = response
  } catch (error) {
    console.error('Failed to fetch MCP configuration:', error)
    ElMessage.error(`${t('mcp.configCenter.messages.fetchConfigFailed')}: ${error.message || error}`)
  } finally {
    loading.value = false
  }
}

// Fetch statistics data
const fetchStatistics = async (customUrl = null) => {
  try {
    statisticsLoading.value = true
    const apiUrl = customUrl || currentApiUrl.value
    const response = await getMcpStatistics(apiUrl)
    statisticsData.value = response?.data || response
  } catch (error) {
    console.error('Failed to fetch statistics data:', error)
    ElMessage.error(`${t('mcp.configCenter.messages.fetchStatsFailed')}: ${error.message || error}`)
  } finally {
    statisticsLoading.value = false
  }
}

// Refresh configuration
const refreshConfig = async () => {
  const customUrl = currentApiUrl.value !== getMcpApiUrl() ? currentApiUrl.value : null
  await Promise.all([
    fetchConfig(customUrl),
    fetchStatistics(customUrl)
  ])
  // Reset filter status after configuration is loaded
  resetFilters()
}

// API address editing related methods
const startEditApiUrl = () => {
  tempApiUrl.value = currentApiUrl.value
  isEditingApiUrl.value = true
}

const confirmEditApiUrl = () => {
  if (tempApiUrl.value.trim()) {
    currentApiUrl.value = tempApiUrl.value.trim()
    isEditingApiUrl.value = false
    ElMessage.success(t('mcp.configCenter.messages.apiUrlUpdated'))
  } else {
    ElMessage.warning(t('mcp.configCenter.messages.apiUrlInvalid'))
  }
}

const cancelEditApiUrl = () => {
  tempApiUrl.value = ''
  isEditingApiUrl.value = false
}

const resetToDefaultApiUrl = () => {
  currentApiUrl.value = getMcpApiUrl()
  tempApiUrl.value = ''
  isEditingApiUrl.value = false
  ElMessage.success(t('mcp.configCenter.messages.apiUrlReset'))
}

// Handle statistics card click
const handleStatCardClick = (serverType) => {
  activeServerType.value = serverType
}

// Handle tool statistics card click
const handleToolsStatClick = () => {
  if (statisticsData.value) {
    showStatisticsDialog.value = true
  }
}

// Handle add to editor
const handleAddToEditor = (serverData) => {
  emit('add-to-editor', serverData)
}

// Reset all search and pagination status
const resetFilters = () => {
  stdioSectionRef.value?.resetFilters()
  sseSectionRef.value?.resetFilters()
  streamableSectionRef.value?.resetFilters()
}

const defaultMcpApiUrl = `Please enter the complete API address, e.g.: http://127.0.0.1:9000/api/config?client_type=cursor&proxy_host=auto&proxy_port=0`

// Page initialization
onMounted(() => {
  fetchConfig()
  fetchStatistics()
})

// Expose component methods and state to parent component
defineExpose({
  loading: loading,
  fetchConfig,
  refreshConfig
})
</script>

<style scoped lang="scss">
.mcp-config-container {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  min-height: 100vh;
  padding: 20px;

  .page-header {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    color: white;
    padding: 32px 24px;
    margin-bottom: 24px;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);

    .header-content {
      margin: 0;
      display: flex;
      justify-content: space-between;
      align-items: center;

      .title-section {
        .page-title {
          display: flex;
          align-items: center;
          gap: 12px;
          font-size: 32px;
          font-weight: 700;
          margin: 0 0 8px 0;
          background: linear-gradient(135deg, #f093fb 0%, #f5576c 30%, #4facfe 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;

          .title-icon {
            font-size: 36px;
          }
        }

        .page-subtitle {
          font-size: 16px;
          opacity: 0.9;
          margin: 0;
        }
      }

      .header-actions {
        display: flex;
        align-items: center;
        gap: 16px;

        .api-url-section {
          display: flex;
          align-items: center;
          gap: 8px;

          .api-url-label {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.9);
            white-space: nowrap;
          }

          .api-url-input-group {
            display: flex;
            align-items: center;
            gap: 4px;

            .api-url-input {
              width: 500px;

              :deep(.el-input__wrapper) {
                background: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.3);
                backdrop-filter: blur(10px);

                .el-input__inner {
                  color: #fff;

                  &::placeholder {
                    color: rgba(255, 255, 255, 0.6);
                  }
                }
              }
            }
          }

          .api-url-display-group {
            display: flex;
            align-items: center;
            gap: 4px;

            .api-url-text {
              background: rgba(255, 255, 255, 0.15);
              color: #fff;
              padding: 6px 12px;
              border-radius: 6px;
              font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
              font-size: 13px;
              max-width: 500px;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
              backdrop-filter: blur(10px);
            }
          }
        }

        .el-button {
          --el-button-bg-color: rgba(255, 255, 255, 0.2);
          --el-button-border-color: rgba(255, 255, 255, 0.3);
          --el-button-text-color: #fff;
          --el-button-hover-bg-color: rgba(255, 255, 255, 0.3);
          backdrop-filter: blur(10px);
        }
      }
    }
  }

  .stats-section {
    margin: 0 0 32px 0;
    padding: 0;

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 20px;

      .stat-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        display: flex;
        align-items: center;
        gap: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        cursor: pointer;

        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }

        &.active:not(.total) {
          transform: translateY(-3px);
          box-shadow: 0 12px 30px rgba(0, 0, 0, 0.15);
          border: 2px solid #3b82f6;

          .stat-content .stat-number {
            color: #3b82f6;
          }
        }

        .stat-icon {
          width: 48px;
          height: 48px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;

          .el-icon {
            font-size: 24px;
            color: white;
          }
        }

        .stat-content {
          .stat-number {
            font-size: 28px;
            font-weight: 700;
            line-height: 1;
            margin-bottom: 4px;
          }

          .stat-label {
            font-size: 14px;
            color: #666;
          }
        }

        &.total .stat-icon {
          background: linear-gradient(135deg, #64748b 0%, #475569 100%);
        }

        &.stdio .stat-icon {
          background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        }

        &.sse .stat-icon {
          background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }



        &.streamable .stat-icon {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }

        &.tools .stat-icon {
          background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }

        &.clickable {
          position: relative;
          
          &.has-data {
            cursor: pointer;
            
            &:hover {
              transform: translateY(-4px);
              box-shadow: 0 12px 35px rgba(0, 0, 0, 0.2);
            }
            
            &:active {
              transform: translateY(-2px);
            }
          }
          
          .stat-content {
            .clickable-number {
              color: #409eff;
              cursor: pointer;
              transition: all 0.3s ease;
              
              &:hover {
                color: #66b1ff;
                text-decoration-thickness: 2px;
              }
            }
          }
        }
      }
    }
  }

  .config-content {
    margin: 0;
    padding: 0;

    .server-sections {
      margin: 0;
      padding: 0;
    }
  }

  .proxy-info {
    margin: 40px 0 0 0;
    padding: 0;

    .info-card {
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);

      :deep(.el-card__header) {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        color: white;

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;

          .el-tag {
            --el-tag-bg-color: rgba(255, 255, 255, 0.2);
            --el-tag-text-color: #fff;
            --el-tag-border-color: rgba(255, 255, 255, 0.3);
          }
        }
      }

      .proxy-details {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;

        .detail-item {
          display: flex;
          flex-direction: column;
          gap: 4px;

          .label {
            font-weight: 600;
            color: #333;
            font-size: 13px;
          }

          code {
            background: #f5f5f5;
            padding: 4px 8px;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 12px;
            color: #e74c3c;
          }
        }
      }
    }
  }
}

// Embedded mode styles
.mcp-config-container.embedded-mode {
  background: transparent;
  min-height: auto;
  padding: 0;

  .config-content {
    margin: 0;
  }
  
  .proxy-info {
    margin: 20px 0 0 0;
  }
}

// Responsive design
@media (max-width: 768px) {
  .mcp-config-container {
    padding: 16px;

    .page-header .header-content {
      flex-direction: column;
      gap: 20px;
      text-align: center;

      .header-actions {
        flex-direction: column;
        gap: 12px;
        width: 100%;

        .api-url-section {
          flex-direction: column;
          gap: 8px;
          width: 100%;

          .api-url-input-group {
            width: 100%;

            .api-url-input {
              width: 100%;
            }
          }

          .api-url-display-group {
            width: 100%;
            justify-content: center;

            .api-url-text {
              max-width: 280px;
              font-size: 12px;
            }
          }
        }
      }
    }

    .stats-section .stats-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
}
</style>