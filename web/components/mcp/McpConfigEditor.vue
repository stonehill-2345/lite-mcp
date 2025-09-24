<template>
  <div class="mcp-enhanced-config-editor">
    <!-- Editor header -->
    <div class="editor-header">
      <div class="header-left">
        <p class="connection-types">
          <span class="type-badge sse">SSE</span>{{ t('mcp.configCenter.serverTypes.sseDesc') }}
          <span class="type-badge streamable-http">Streamable HTTP</span>{{ t('mcp.configCenter.serverTypes.streamableDesc') }}
        </p>
      </div>
      <div class="header-actions">
        <el-button
            @click="refreshServerTools"
            :icon="Refresh"
            :loading="refreshing"
            size="default"
        >
          {{ t('mcp.configCenter.refreshConfig') }}
        </el-button>
        <el-button
            @click="showConfigCenter"
            :icon="Setting"
            size="default"
        >
          {{ t('mcp.configCenter.title') }}
        </el-button>
        <el-button
            @click="handleSaveBtn"
            :icon="showJsonEditor ? 'View' : 'EditPen'"
            size="default"
        >
          {{ showJsonEditor ? t('common.save') : t('common.edit') }}
        </el-button>
      </div>
    </div>

    <!-- Tools statistics -->
    <div class="tools-stats">
      <div class="stats-left">
        <div class="stats-item">
          <span class="label">{{ t('mcp.configCenter.stats.totalServers') }}：</span>
          <span class="value">{{ serverConfigs.length }}</span>
        </div>
        <div class="stats-item enabled">
          <span class="label">{{ t('mcp.configCenter.stats.totalServers') }}：</span>
          <span class="value">{{ enabledServersCount }}</span>
        </div>
        <div class="stats-item tools">
          <span class="label">{{ t('mcp.configCenter.stats.totalTools') }}：</span>
          <span class="value" :class="{ 'warning': enabledToolsCount > 40, 'optimal': enabledToolsCount <= 40 }">
            {{ enabledToolsCount }}
            <span class="suggestion">({{ t('mcp.configCenter.stats.suggestion') }})</span>
          </span>
        </div>

        <!-- Search filter box -->
        <div v-if="!showJsonEditor && serverConfigs.length > 0" class="stats-item search-filter">
          <span class="label">{{ t('common.search') }}：</span>
          <el-input
              v-model="searchKeyword"
              :placeholder="t('mcp.configCenter.searchPlaceholder')"
              size="small"
              style="width: 220px"
              clearable
              @input="handleSearchInput"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>

        <!-- Pagination control -->
        <div v-if="!showJsonEditor && filteredServers.length > 0" class="stats-right">
          <div class="stats-item filter-info" v-if="searchKeyword">
            <span class="label">{{ t('mcp.configCenter.filterResults') }}：</span>
            <span class="value">{{ filteredServers.length }} / {{ serverConfigs.length }}</span>
          </div>
          <div class="stats-item pagination-control">
            <span class="label">{{ t('mcp.configCenter.itemsPerPage') }}：</span>
            <el-select v-model="pageSize" size="small" style="width: 100px">
              <el-option :label="t('mcp.configCenter.items3')" :value="3" />
              <el-option :label="t('mcp.configCenter.items5')" :value="5" />
              <el-option :label="t('mcp.configCenter.items10')" :value="10" />
              <el-option :label="t('mcp.configCenter.items20')" :value="20" />
              <el-option :label="t('common.all')" :value="totalFilteredServers" />
            </el-select>
          </div>
        </div>
      </div>
    </div>

    <!-- JSON editor view -->
    <div v-if="showJsonEditor" class="json-editor-section">
      <div class="json-editor-header">
        <div class="editor-title">
          <el-icon><EditPen /></el-icon>
          <span>{{ t('mcp.configCenter.jsonEditor') }}</span>
        </div>
        <div class="editor-actions">
          <el-button @click="validateConfig" size="small">{{ t('mcp.configCenter.validateConfig') }}</el-button>
          <el-button @click="formatJson" size="small">{{ t('mcp.configCenter.formatJson') }}</el-button>
          <el-button @click="() => loadExample()" size="small">{{ t('mcp.configCenter.loadExample') }}</el-button>
        </div>
      </div>

      <div class="json-editor-wrapper">
        <el-input
            v-model="configJson"
            type="textarea"
            :rows="15"
            :placeholder="t('mcp.configCenter.jsonPlaceholder')"
            class="json-textarea"
            @input="handleJsonChange"
        />

        <!-- Error prompt -->
        <div v-if="jsonError" class="json-error">
          <el-icon><WarningFilled /></el-icon>
          {{ jsonError }}
        </div>

        <!-- Validation result -->
        <div v-if="validationResult && !jsonError" class="validation-success">
          <el-icon><CircleCheckFilled /></el-icon>
          {{ t('mcp.configCenter.validationSuccess', { count: validationResult.serverCount }) }}
        </div>
      </div>
    </div>

    <!-- Visual editor view -->
    <div v-else class="visual-editor-section">
      <div v-if="filteredServers.length > 0" class="servers-container">
        <!-- Simplified pagination info -->
        <div v-if="totalPages > 1" class="pagination-info-simple">
          {{ t('mcp.configCenter.paginationInfo', { 
            start: (currentPage - 1) * pageSize + 1, 
            end: Math.min(currentPage * pageSize, totalFilteredServers),
            total: totalFilteredServers
          }) }}
          <span v-if="searchKeyword" class="search-info">（{{ t('mcp.configCenter.filteredFrom', { total: totalServers }) }}）</span>
        </div>

        <div class="servers-list">
          <div
              v-for="(server, serverIndex) in paginatedServers"
              :key="server.id"
              class="server-item"
              :class="{
              'server-disabled': !server.enabled,
              'server-error': server.hasError
            }"
          >
            <!-- Server header -->
            <div class="server-header">
              <div class="server-status">
                <!-- Server enable/disable switch -->
                <el-switch
                    v-model="server.enabled"
                    size="default"
                    @change="handleServerToggle(server)"
                />

                <!-- Connection status indicator -->
                <el-tag
                    :type="server.connected ? 'success' : (server.connecting ? 'warning' : 'info')"
                    size="small"
                    class="status-tag"
                >
                  <template v-if="server.connecting">
                    <el-icon class="is-loading"><Refresh /></el-icon>
                    {{ t('mcp.connection.connecting') }}
                  </template>
                  <template v-else-if="server.connected">
                    ✓ {{ t('mcp.connection.connected') }}
                  </template>
                  <template v-else-if="server.hasError">
                    <span style="color: red">x {{ t('mcp.connection.failed') }}</span>
                  </template>
                  <template v-else>
                    ● {{ t('mcp.connection.disconnected') }}
                  </template>
                </el-tag>
              </div>

              <div class="server-info">
                <div class="server-name">
                  <div class="name-badge" :class="server.type">
                    {{ server.name.charAt(0).toUpperCase() }}
                  </div>
                  <div class="name-content">
                    <h4>{{ server.name }}</h4>
                    <div class="server-tags">
                      <el-tag
                          :type="getServerTagType(server.type)"
                          size="small"
                      >
                        {{ server.type.toUpperCase() }}
                      </el-tag>
                      <!-- Show new config tag (added within 24 hours) -->
                      <el-tag
                          v-if="isNewServer(server)"
                          type="danger"
                          size="small"
                          effect="dark"
                      >
                        {{ t('mcp.configCenter.newConfig') }}
                      </el-tag>
                    </div>
                  </div>
                </div>

                <div class="server-meta">
                <span class="meta-item">
                  <el-icon><Tools /></el-icon>
                  {{ getServerEnabledToolsCount(server) }} / {{ server.tools?.length || 0 }} {{ t('mcp.configCenter.tools') }}
                </span>
                  <span class="meta-item">
                  <el-icon><Link /></el-icon>
                  {{ server.url }}{{ server.apiPath ? server.apiPath : '' }}
                  <el-tooltip
                      :content="getServerTypeTooltip(server)"
                      placement="top"
                  >
                    <el-icon class="info-icon"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
                </div>

                <div class="server-description">
                  {{ server.description || t('mcp.configCenter.noDescription') }}
                </div>
              </div>

              <div class="server-actions">
                <el-button
                    :icon="server.toolsExpanded ? 'ArrowUp' : 'ArrowDown'"
                    size="small"
                    @click="toggleServerTools(server)"
                    :disabled="!server.connected || !server.tools || server.tools.length === 0"
                >
                  {{ server.toolsExpanded ? t('mcp.configCenter.collapseTools') : t('mcp.configCenter.expandTools') }}
                  <span v-if="server.connected">({{ server.tools?.length || 0 }})</span>
                </el-button>
              </div>
            </div>

            <!-- Tools list -->
            <div v-if="server.toolsExpanded && server.tools?.length > 0" class="tools-list">
              <div class="tools-header">
                <h5>{{ t('mcp.configCenter.availableToolsList', { count: server.tools.length }) }}</h5>
                <div class="tools-actions">
                  <el-button
                      size="small"
                      @click="enableAllServerTools(server)"
                      :disabled="!server.connected"
                  >
                    {{ t('mcp.configCenter.enableAll') }}
                  </el-button>
                  <el-button
                      size="small"
                      @click="disableAllServerTools(server)"
                      :disabled="!server.connected"
                  >
                    {{ t('mcp.configCenter.disableAll') }}
                  </el-button>
                </div>
              </div>

              <div class="tools-grid">
                <div
                    v-for="(tool, toolIndex) in server.tools"
                    :key="tool.name"
                    class="tool-item"
                    :class="{ 'tool-disabled': !tool.enabled }"
                >
                  <div class="tool-toggle">
                    <el-switch
                        v-model="tool.enabled"
                        size="small"
                        @change="handleToolToggle(server, tool)"
                        :disabled="!server.connected"
                    />
                  </div>

                  <div class="tool-info">
                    <div class="tool-name">{{ tool.name }}</div>
                    <div class="tool-description">{{ tool.description || t('mcp.configCenter.noDescription') }}</div>
                  </div>

                  <div class="tool-actions">
                    <el-button
                        :icon="QuestionFilled"
                        size="small"
                        @click="showToolDetails(tool)"
                        :title="t('mcp.configCenter.viewDetails')"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Pagination component -->
        <div v-if="totalPages > 1" class="pagination-wrapper">
          <el-pagination
              v-model:current-page="currentPage"
              :page-size="pageSize"
              :total="totalFilteredServers"
              layout="prev, pager, next, jumper"
              :pager-count="5"
          />
        </div>
      </div>

      <div v-else class="empty-state">
        <el-empty
            :description="searchKeyword ? t('mcp.configCenter.noSearchResults', { keyword: searchKeyword }) : t('mcp.configCenter.addServerConfig')"
        >
          <el-button
              v-if="!searchKeyword"
              type="primary"
              @click="loadExampleConfig"
          >
            {{ t('mcp.configCenter.loadExampleConfig') }}
          </el-button>
          <el-button
              v-else
              @click="searchKeyword = ''"
              type="primary"
          >
            {{ t('mcp.configCenter.clearSearch') }}
          </el-button>
        </el-empty>
      </div>
    </div>

    <!-- Tool detail dialog -->
    <ToolDetailDialog
        v-model:visible="toolDetailVisible"
        :tool="currentTool"
    />

    <!-- Config center dialog -->
    <el-dialog
        v-model="configCenterVisible"
        :title="t('mcp.configCenter.title')"
        width="100%"
        class="config-center"
        :fullscreen="false"
        destroy-on-close
    >
      <div 
        class="config-center-content" 
        v-loading="configCenterLoading" 
        :element-loading-text="t('common.loading')"
      >
        <div v-if="configCenterLoading" class="loading-placeholder">
          <div class="loading-text">{{ t('mcp.configCenter.loadingConfigCenter') }}</div>
          <div class="loading-description">{{ t('mcp.configCenter.loadingDescription') }}</div>
        </div>

        <LiteMCPConfig
            ref="liteMcpConfigRef"
            v-show="!configCenterLoading"
            :embedded="true"
            @add-to-editor="handleAddServerFromCenter"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import {
  Refresh,
  EditPen,
  Tools,
  Link,
  WarningFilled,
  CircleCheckFilled,
  QuestionFilled,
  Setting,
  Search
} from '@element-plus/icons-vue'
import mcpClientManager from '@/utils/mcpClient'
import mcpConnectionService from '@/services/mcp/McpConnectionService.js'
import mcpStateManager from '@/services/mcp/McpStateManager.js'
import { setCache, getCacheByKey } from '@/utils/storage'
import DebugLogger from "@/utils/DebugLogger"
import LiteMCPConfig from '@/LiteMCPConfig.vue'
import ToolDetailDialog from '@/components/dialog/ToolDetailDialog.vue'

// Multi-language support
const { t } = useI18n()

// Props
const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },

})

const emit = defineEmits(['update:modelValue', 'config-change', 'connect-servers'])
const logger = DebugLogger.createLogger('McpConfigEditor')

// MCP client instance
const mcpClient = mcpClientManager

// Cache key names
const CONFIG_CACHE_KEY = 'mcp_config_cache'
const USER_STATE_CACHE_KEY = 'mcp_user_state_cache'

// New reactive data - user state cache
const userStateCache = ref({
  enabledServers: {}, // Server enable state { serverName: boolean }
  enabledTools: {}, // Tool enable state { "serverName.toolName": boolean }
  expandedServers: {}, // Server expand state { serverName: boolean }

  lastConnectedTime: null, // Last connection time
  autoConnectOnLoad: true, // Whether to auto-connect on load
  isConnected: false,
})

// Reactive data
const showJsonEditor = ref(false)
const refreshing = ref(false)
const configJson = ref('')
const jsonError = ref('')
const validationResult = ref(null)
const serverConfigs = ref([])
const toolDetailVisible = ref(false)
const currentTool = ref(null)
const connectionSessions = ref(new Map()) // Store server connection sessions
const configCenterVisible = ref(false) // Config center dialog visibility
const liteMcpConfigRef = ref(null) // LiteMCPConfig component
// Pagination related
const currentPage = ref(1)
const pageSize = ref(3) // Show 5 servers per page

// Search related
const searchKeyword = ref('')
const filteredServers = computed(() => {
  if (!searchKeyword.value) {
    return serverConfigs.value
  }
  const keyword = searchKeyword.value.toLowerCase()
  return serverConfigs.value.filter(server =>
      server.name.toLowerCase().includes(keyword) ||
      server.description?.toLowerCase().includes(keyword) ||
      server.tools?.some(tool => tool.name.toLowerCase().includes(keyword))
  )
})
const totalFilteredServers = computed(() => filteredServers.value.length)

// Example configuration (supports SSE and Streamable HTTP modes)
const exampleConfigs = {
  cursor: {
    mcpServers: {
      "example-mock-http": {
        "type": "streamable-http",
        "url": "http://127.0.0.1:8933/mcp",
        "description": "Example MCP server (mock HTTP endpoint for testing connection logic)"
      },
      "school-sse-test": {
        "type": "streamable-http",
        "url": "http://127.0.0.1:1888/mcp/school",
        "description": "School management MCP server (SSE mode test, may require special configuration)"
      },
    }
  }
}

// Computed properties
const enabledServersCount = computed(() => {
  return serverConfigs.value.filter(server => server.enabled).length
})

const enabledToolsCount = computed(() => {
  return serverConfigs.value.reduce((total, server) => {
    if (!server.enabled || !server.tools) return total
    return total + server.tools.filter(tool => tool.enabled).length
  }, 0)
})

// Pagination related computed properties
const totalServers = computed(() => serverConfigs.value.length)
const totalPages = computed(() => Math.ceil(totalFilteredServers.value / pageSize.value))
const paginatedServers = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredServers.value.slice(start, end)
})

// Config center loading state computed property
const configCenterLoading = computed(() => {
  return liteMcpConfigRef.value?.loading || false
})

// Search input handling
const handleSearchInput = () => {
  // Reset to first page when searching
  currentPage.value = 1
}

// Methods
const handleJsonChange = () => {
  emit('update:modelValue', configJson.value)
  parseJsonConfig()

  // Save configuration to cache
  if (configJson.value.trim()) {
    try {
      JSON.parse(configJson.value) // Validate JSON format
      setCache(CONFIG_CACHE_KEY, configJson.value)
    } catch (error) {
      console.warn('JSON format error, not saving to cache')
    }
  }

  emitConfigChange()
}

const handleSaveBtn = () => {
  showJsonEditor.value = !showJsonEditor.value
  autoConnectEnabledServers()
}

const parseJsonConfig = () => {
  if (!configJson.value.trim()) {
    serverConfigs.value = []
    jsonError.value = ''
    validationResult.value = null
    return
  }

  try {
    jsonError.value = ''
    const config = JSON.parse(configJson.value)

    if (!config.mcpServers) {
      jsonError.value = t('mcp.configCenter.configFormatError')
      serverConfigs.value = []
      return
    }

    const servers = []
    let originalIndex = 0 // Used to maintain original order

    for (const [name, serverConfig] of Object.entries(config.mcpServers)) {
      // Determine server type based on configuration
      let serverType = 'sse' // Default type
      if (serverConfig.type) {
        serverType = serverConfig.type
      }

      const server = {
        id: `server_${Date.now()}_${Math.random()}`,
        name,
        type: serverType,
        url: serverConfig.url || '',
        apiPath: serverConfig.apiPath || '', // Streamable HTTP type specific

        description: serverConfig.description || '',
        enabled: false, // Will be restored from user state
        connected: false,
        connecting: false,
        tools: [],
        toolsExpanded: false, // Will be restored from user state
        hasError: false,
        sessionId: null,
        addedAt: serverConfig.addedAt || null, // Keep null to distinguish manual config from auto-added config
        originalIndex: originalIndex++ // Record original order
      }
      servers.push(server)
    }

    // Smart sorting: configs added through config center (with addedAt) come first, manual configs maintain original order
    servers.sort((a, b) => {
      // Configs with addedAt come first, sorted by timestamp in descending order
      if (a.addedAt && b.addedAt) {
        return b.addedAt - a.addedAt
      }
      // Configs with addedAt come before those without
      if (a.addedAt && !b.addedAt) return -1
      if (!a.addedAt && b.addedAt) return 1
      // Neither has addedAt, maintain original order from JSON
      return a.originalIndex - b.originalIndex
    })

    serverConfigs.value = servers

    // Apply user state to newly parsed server configurations
    applyUserStateToServers()

    const serverCount = servers.length
    const toolCount = servers.reduce((sum, server) => sum + (server.tools?.length || 0), 0)

    validationResult.value = { serverCount, toolCount }

  } catch (error) {
    jsonError.value = t('mcp.configCenter.jsonSyntaxError', { error: error.message })
    serverConfigs.value = []
  }
}

// Connect to MCP server
const connectToServer = async (server, skipStateUpdate = false) => {
  if (server.connecting || server.connected) {
    return false
  }

  server.connecting = true
  server.hasError = false

  try {
    logger.log(`🔌 Starting server connection: ${server.name} (type: ${server.type})`)

    // Build connection configuration, supports both SSE and Streamable HTTP types
    const config = {
      serverName: server.name,
      serverType: server.type,
      serverConfig: {
        command: server.command,
        args: server.args,
        env: server.env,
        url: server.url,
        description: server.description
      }
    }

    // If Streamable HTTP type, add apiPath configuration
    if (server.type === 'streamable-http' && server.apiPath) {
      config.serverConfig.apiPath = server.apiPath
    }

    logger.log(`🔗 Connection configuration:`, {
      serverName: server.name,
      type: server.type,
      url: server.url,
      apiPath: server.apiPath || 'none',
      hasApiPath: !!(server.type === 'streamable-http' && server.apiPath)
    })

    const sessionId = await mcpClient.connect(config)
    server.sessionId = sessionId
    server.connected = true
    server.enabled = true
    server.hasError = false

    logger.log(`🔗 Server ${server.name} connected successfully, session ID: ${sessionId}`)

    // Get real tool list
    const tools = await mcpClient.getSessionTools(sessionId)
    logger.log(`🔧 Server ${server.name} obtained ${tools.length} tools`)

    server.tools = tools.map(tool => {
      const toolKey = `${server.name}.${tool.name}`
      // Prioritize cached enable state, default to enabling all tools for newly connected servers
      const enabledFromCache = userStateCache.value.enabledTools.hasOwnProperty(toolKey)
          ? userStateCache.value.enabledTools[toolKey]
          : true // Newly connected servers default to enabling all tools

      logger.log(`🔧 Tool ${tool.name} enable state: ${enabledFromCache} (from cache: ${userStateCache.value.enabledTools.hasOwnProperty(toolKey)})`)

      return {
        name: tool.name,
        description: tool.description || '',
        inputSchema: tool.inputSchema || {},
        enabled: enabledFromCache
      }
    })

    connectionSessions.value.set(server.name, sessionId)

    // Count auto-enabled tools
    const autoEnabledCount = server.tools.filter(tool => {
      const toolKey = `${server.name}.${tool.name}`
      return tool.enabled && !userStateCache.value.enabledTools.hasOwnProperty(toolKey)
    }).length

    // Only save state when not skipping state update (avoid state race conditions during parallel connections)
    if (!skipStateUpdate) {
      saveUserState()
      emitConfigChange()
    }

    logger.log(`✅ Server ${server.name} fully initialized, ${server.tools.length} tools total, auto-enabled ${autoEnabledCount} new tools`)

    if (autoEnabledCount > 0) {
      // Calculate current total enabled tools (need to recalculate because new tools were just enabled)
      const currentTotalEnabled = serverConfigs.value.reduce((total, srv) => {
        if (!srv.enabled || !srv.tools) return total
        return total + srv.tools.filter(tool => tool.enabled).length
      }, 0)

      if (currentTotalEnabled > 40) {
        ElMessage({
          message: `Server ${server.name} connected successfully, auto-enabled ${autoEnabledCount} new tools. Current total ${currentTotalEnabled} tools, recommend keeping under 40 for better performance`,
          type: 'warning',
          duration: 6000
        })
      } else {
        ElMessage.success(`Server ${server.name} connected successfully, auto-enabled ${autoEnabledCount} new tools`)
      }
    }

    return true
  } catch (error) {
    server.hasError = true
    server.connected = false
    server.enabled = false

    console.error(`❌ Failed to connect to server ${server.name}:`, error)
    ElMessage.error(`Failed to connect to server ${server.name}: ${error.message}`)

    return false
  } finally {
    server.connecting = false
  }
}

// Disconnect from server
const disconnectFromServer = async (server) => {
  if (!server.connected || server.connecting) {
    return
  }

  try {
    if (server.sessionId) {
      await mcpClient.disconnect(server.sessionId)
      connectionSessions.value.delete(server.name)
    }

    server.connected = false
    server.sessionId = null
    server.tools = []
    server.hasError = false

    ElMessage.success(t('mcp.configCenter.serverDisconnected', { name: server.name }))
    emitConfigChange()
  } catch (error) {
    ElMessage.error(t('mcp.configCenter.serverDisconnectFailed', { name: server.name, error: error.message }))
  }
}

// Handle server enable/disable toggle
const handleServerToggle = async (server) => {
  logger.log(`🔄 User toggled server ${server.name} state:`, server.enabled ? 'enabled' : 'disabled')

  if (server.enabled) {
    // When enabling server, try auto-connect
    if (!server.connected && !server.connecting) {
      // Don't skip state update for individual connections
      const success = await connectToServer(server, false)
      if (success) {
        logger.log(`✅ Server ${server.name} manually connected successfully`)
      }
    }
  } else {
    // When disabling server, disconnect
    if (server.connected) {
      await disconnectFromServer(server)
    }
    server.hasError = false

    // Save user state
    saveUserState()
    emitConfigChange()
  }
}

const validateConfig = () => {
  parseJsonConfig()
  if (!jsonError.value && validationResult.value) {
    ElMessage.success(`Configuration validation passed! Detected ${validationResult.value.serverCount} servers`)
  }
}

const formatJson = () => {
  try {
    const parsed = JSON.parse(configJson.value)
    configJson.value = JSON.stringify(parsed, null, 2)
    ElMessage.success('JSON formatting completed')
    emit('update:modelValue', configJson.value)

    // Save to cache
    setCache(CONFIG_CACHE_KEY, configJson.value)
  } catch (error) {
    ElMessage.error('JSON format error, unable to format')
  }
}

const loadExample = async (skipConfirm = false) => {
  try {
    // If not skipping confirmation, show confirmation dialog (except for first initialization)
    if (!skipConfirm) {
      await ElMessageBox.confirm('Loading example configuration will overwrite all current configuration content. This operation cannot be undone.', 'Confirm Load Example', {
        confirmButtonText: 'Confirm Load',
        cancelButtonText: 'Cancel',
        type: 'warning',
        customClass: 'mcp-confirm-dialog',
        center: true,
      })
    }

    configJson.value = JSON.stringify(exampleConfigs.cursor, null, 2)
    emit('update:modelValue', configJson.value)
    parseJsonConfig()

    // Save to cache
    setCache(CONFIG_CACHE_KEY, configJson.value)

    if (!skipConfirm) {
      ElMessage.success('Example configuration loaded')
    }
  } catch (error) {
    // User cancelled operation, no need to prompt
    if (error === 'cancel' || error === 'close') {
      return
    }
    ElMessage.error('Failed to load example configuration')
  }
}

const loadExampleConfig = () => {
  loadExample(false) // Don't skip confirmation, show dialog
  showJsonEditor.value = true
}

const refreshServerTools = async () => {
  refreshing.value = true
  try {
    const connectedServers = serverConfigs.value.filter(server => server.connected && server.sessionId)

    if (connectedServers.length === 0) {
      ElMessage.warning('No connected servers')
      return
    }

    for (const server of connectedServers) {
      try {
        // Use refresh tools method
        const tools = await mcpClient.refreshTools(server.sessionId)
        server.tools = tools.map(tool => ({
          name: tool.name,
          description: tool.description || '',
          inputSchema: tool.inputSchema || {},
          enabled: server.tools.find(t => t.name === tool.name)?.enabled || false
        }))
      } catch (error) {
        console.error(`❌ Failed to refresh server ${server.name} tools:`, error)
        server.hasError = true
        ElMessage.error(`Failed to refresh server ${server.name}: ${error.message}`)
        server.enabled = false
      }
    }

    ElMessage.success('Tool list refresh completed')
    emitConfigChange()
  } catch (error) {
    ElMessage.error('Failed to refresh tools')
  } finally {
    refreshing.value = false
  }
}

const toggleServerTools = (server) => {
  server.toolsExpanded = !server.toolsExpanded
  saveUserState() // Save expand state
}

const enableAllServerTools = (server) => {
  if (!server.connected) {
    ElMessage.warning('Please connect to server first')
    return
  }

  if (!server.tools || server.tools.length === 0) {
    ElMessage.warning('This server has no available tools')
    return
  }

  let enabledCount = 0
  server.tools.forEach(tool => {
    if (!tool.enabled) {
      tool.enabled = true
      enabledCount++
    }
  })

  if (enabledCount > 0) {
    // Save user state
    saveUserState()
    emitConfigChange()

    // If enabled count exceeds recommended amount, give friendly warning
    const totalEnabled = enabledToolsCount.value
    if (totalEnabled > 40) {
      ElMessage({
        message: `Enabled ${enabledCount} tools for server ${server.name}. Current total ${totalEnabled} tools, recommend keeping under 40 for better performance`,
        type: 'warning',
        duration: 5000
      })
    } else {
      ElMessage.success(`Enabled ${enabledCount} tools for server ${server.name}`)
    }
  } else {
    ElMessage.info(`All tools for server ${server.name} are already enabled`)
  }
}

const disableAllServerTools = (server) => {
  if (!server.connected) {
    ElMessage.warning('Please connect to server first')
    return
  }

  if (!server.tools || server.tools.length === 0) {
    ElMessage.warning('This server has no available tools')
    return
  }

  let disabledCount = 0
  server.tools.forEach(tool => {
    if (tool.enabled) {
      tool.enabled = false
      disabledCount++
    }
  })

  if (disabledCount > 0) {
    // Save user state
    saveUserState()
    emitConfigChange()
    ElMessage.success(`Disabled ${disabledCount} tools for server ${server.name}`)
  } else {
    ElMessage.info(`All tools for server ${server.name} are already disabled`)
  }
}

const handleToolToggle = (server, tool) => {
  if (!server.connected) {
    ElMessage.warning('Please connect to server first')
    tool.enabled = false // Force to disabled state
    return
  }

  // If enabling tool and exceeding recommended amount, give friendly warning but don't block
  if (tool.enabled && enabledToolsCount.value > 40) {
    ElMessage({
      message: `Currently enabled ${enabledToolsCount.value} tools, recommend keeping under 40 for better performance`,
      type: 'warning',
      duration: 4000
    })
  }

  // Immediately save user state
  saveUserState()
  emitConfigChange()

  const statusText = tool.enabled ? 'enabled' : 'disabled'
  ElMessage.success(`Tool ${tool.name} has been ${statusText}`)
}

const getServerEnabledToolsCount = (server) => {
  return server.tools?.filter(tool => tool.enabled).length || 0
}

const getServerTypeTooltip = (server) => {
  switch (server.type) {
    case 'sse':
      return 'SSE type connects directly to specified URL, suitable for web browser environment'
    case 'streamable-http':
      return 'Streamable HTTP type supports streaming responses, suitable for modern MCP servers like FastMCP'

    default:
      return 'Unknown type'
  }
}

const getServerTagType = (serverType) => {
  switch (serverType) {
    case 'sse':
      return 'success'
    case 'streamable-http':
      return 'primary'

    default:
      return 'info'
  }
}

// Determine if it's a new configuration (added through config center within 24 hours)
const isNewServer = (server) => {
  // Only configs added through config center have addedAt field
  if (!server.addedAt || typeof server.addedAt !== 'number') return false
  const now = Date.now()
  const oneDayMs = 24 * 60 * 60 * 1000 // 24 hours in milliseconds
  return (now - server.addedAt) < oneDayMs
}

const showToolDetails = (tool) => {
  currentTool.value = tool
  toolDetailVisible.value = true
}

// Show config center
const showConfigCenter = () => {
  configCenterVisible.value = true
}

// Add server configuration from config center
const handleAddServerFromCenter = (serverData) => {
  try {
    logger.log('🔄 Config center add server request:', {
      serverName: serverData.serverName,
      serverType: serverData.serverType,
      serverConfig: serverData.serverConfig
    })

    // Check if server type is supported
    if (!['sse', 'streamable-http'].includes(serverData.serverType)) {
      logger.warn(`❌ Unsupported server type: ${serverData.serverType}`)
      ElMessage.warning(`Unsupported server type: ${serverData.serverType}, currently only supports SSE, Streamable HTTP`)
      return
    }

    // Parse current configuration
    let currentConfig = {}
    if (configJson.value.trim()) {
      try {
        currentConfig = JSON.parse(configJson.value)
      } catch (error) {
        console.warn('Current config JSON format error, will create new config')
      }
    }

    // Ensure mcpServers object exists
    if (!currentConfig.mcpServers) {
      currentConfig.mcpServers = {}
    }

    // Check if server with same name already exists
    if (currentConfig.mcpServers[serverData.serverName]) {
      logger.warn(`⚠️ Server ${serverData.serverName} already exists, will overwrite existing config`)
      ElMessage.warning(`Server ${serverData.serverName} already exists, will overwrite existing config`)
    }

    // Build new server configuration
    const newServerConfig = {
      type: serverData.serverType,
      description: serverData.serverConfig.description || serverData.serverName,
      addedAt: Date.now() // Add timestamp for sorting
    }

    // Add corresponding configuration based on server type
    newServerConfig.url = serverData.serverConfig.url

    // If Streamable HTTP type, add apiPath
    if (serverData.serverType === 'streamable-http' && serverData.serverConfig.apiPath) {
      newServerConfig.apiPath = serverData.serverConfig.apiPath
    }

    // Create new mcpServers object, put new config at the front
    currentConfig.mcpServers = {
      [serverData.serverName]: newServerConfig,
      ...currentConfig.mcpServers
    }

    // Update configuration JSON
    configJson.value = JSON.stringify(currentConfig, null, 2)
    emit('update:modelValue', configJson.value)

    // Re-parse configuration
    parseJsonConfig()

    // Save to cache
    setCache(CONFIG_CACHE_KEY, configJson.value)

    // Close config center dialog
    configCenterVisible.value = false

    // Reset to first page to ensure user can see newly added config
    currentPage.value = 1

    logger.log(`✅ Server ${serverData.serverName} successfully added to configuration`)
    ElMessage.success(`${serverData.serverType.toUpperCase()} server ${serverData.serverName} added to top of configuration`)

    autoConnectEnabledServers()
  } catch (error) {
    logger.error('Failed to add server configuration:', error)
    console.error('Failed to add server configuration:', error)
    ElMessage.error('Failed to add server configuration: ' + error.message)
  }
}

const emitConfigChange = () => {
  const enabledServers = serverConfigs.value.filter(server => server.enabled)
  const enabledTools = []

  enabledServers.forEach(server => {
    server.tools?.forEach(tool => {
      if (tool.enabled) {
        enabledTools.push({
          ...tool,
          serverName: server.name
        })
      }
    })
  })

  // Build enabled session list
  const connectedServers = enabledServers.filter(server => server.connected && server.sessionId)
  const enabledSessions = connectedServers.map(server => ({
    id: server.sessionId,
    name: server.name,
    url: server.url,
    toolCount: server.tools ? server.tools.filter(t => t.enabled).length : 0
  }))

  emit('config-change', {
    configJson: configJson.value,
    servers: enabledServers,
    enabledTools,
    enabledSessions // New: includes session information
  })
}

// Save user state to cache
const saveUserState = () => {
  const currentState = {
    enabledServers: {},
    enabledTools: {},
    expandedServers: {},
    lastConnectedTime: Date.now(),
    autoConnectOnLoad: userStateCache.value.autoConnectOnLoad
  }

  let totalEnabledTools = 0

  // Collect server enable states
  serverConfigs.value.forEach(server => {
    currentState.enabledServers[server.name] = server.enabled
    currentState.expandedServers[server.name] = server.toolsExpanded

    // Collect tool enable states
    if (server.tools) {
      let serverEnabledTools = 0
      server.tools.forEach(tool => {
        const toolKey = `${server.name}.${tool.name}`
        currentState.enabledTools[toolKey] = tool.enabled
        if (tool.enabled) {
          serverEnabledTools++
          totalEnabledTools++
        }
      })
      logger.log(`💾 Save state - Server ${server.name}: ${serverEnabledTools}/${server.tools.length} tools enabled`)
    }
  })

  logger.log(`💾 Save user state:`, {
    enabledServers: Object.values(currentState.enabledServers).filter(Boolean).length,
    enabledTools: totalEnabledTools,
    toolCount: Object.keys(currentState.enabledTools).length
  })

  userStateCache.value = currentState
  setCache(USER_STATE_CACHE_KEY, currentState)
}

// Load user state from cache
const loadUserState = () => {
  const cached = getCacheByKey(USER_STATE_CACHE_KEY)
  if (cached) {
    userStateCache.value = {
      enabledServers: cached.enabledServers || {},
      enabledTools: cached.enabledTools || {},
      expandedServers: cached.expandedServers || {},
      lastConnectedTime: cached.lastConnectedTime,
      autoConnectOnLoad: cached.autoConnectOnLoad !== false // Default true
    }

    const enabledServersCount = Object.values(cached.enabledServers || {}).filter(Boolean).length
    const enabledToolsCount = Object.values(cached.enabledTools || {}).filter(Boolean).length
    const totalToolsCount = Object.keys(cached.enabledTools || {}).length

    logger.log(`🔄 Load user state cache:`, {
      enabledServers: enabledServersCount,
      enabledTools: enabledToolsCount,
      toolCount: totalToolsCount,
      lastConnectedTime: cached.lastConnectedTime ? new Date(cached.lastConnectedTime).toLocaleString() : 'unknown'
    })

    // Show detailed tool states
    Object.entries(cached.enabledTools || {}).forEach(([toolKey, enabled]) => {
      if (enabled) {
        logger.log(`🔧 Enabled tool in cache: ${toolKey}`)
      }
    })

    return true
  }

  logger.log('ℹ️ No user state cache found, using default settings')
  return false
}

// Apply user state to server configurations
const applyUserStateToServers = () => {
  serverConfigs.value.forEach(server => {
    // Restore server enable state
    if (userStateCache.value.enabledServers.hasOwnProperty(server.name)) {
      server.enabled = userStateCache.value.enabledServers[server.name]
    }

    // Restore server expand state
    if (userStateCache.value.expandedServers.hasOwnProperty(server.name)) {
      server.toolsExpanded = userStateCache.value.expandedServers[server.name]
    }

    // Restore tool enable state
    if (server.tools) {
      server.tools.forEach(tool => {
        const toolKey = `${server.name}.${tool.name}`
        if (userStateCache.value.enabledTools.hasOwnProperty(toolKey)) {
          tool.enabled = userStateCache.value.enabledTools[toolKey]
        }
      })
    }
  })
}

// Auto-connect enabled servers
const autoConnectEnabledServers = async () => {
  try {
    // Use shared MCP connection service to perform auto-connect
    const result = await mcpConnectionService.autoConnectEnabledServers(serverConfigs.value, {
      autoConnectOnLoad: userStateCache.value.autoConnectOnLoad,
      enabledStateCheck: (server) => server.enabled, // Custom enable state check
      onProgress: (progressInfo) => {
        logger.log(`🔄 Connection progress: ${progressInfo.phase} (${progressInfo.current}/${progressInfo.total}) - ${progressInfo.serverName} - ${progressInfo.status}`)
      },
      onComplete: (stats) => {
        logger.log(`📊 Auto-connect statistics:`, stats)

        // Apply tool states (ensure correct restoration from cache)
        if (stats.connected && stats.connected.length > 0) {
          logger.log(`🔧 Start applying tool states to ${stats.connected.length} connected servers`)

          stats.connected.forEach(server => {
            if (server.tools && server.tools.length > 0) {
              let appliedCount = 0
              server.tools.forEach(tool => {
                const toolKey = `${server.name}.${tool.name}`
                if (userStateCache.value.enabledTools.hasOwnProperty(toolKey)) {
                  const cachedEnabled = userStateCache.value.enabledTools[toolKey]
                  if (tool.enabled !== cachedEnabled) {
                    logger.log(`🔄 Correct tool state: ${toolKey} ${tool.enabled} -> ${cachedEnabled}`)
                    tool.enabled = cachedEnabled
                    appliedCount++
                  }
                }
              })
              logger.log(`✅ Server ${server.name} applied ${appliedCount} tool states`)
            }
          })

          // Unified save state
          saveUserState()
          emitConfigChange()

          logger.log('💾 Auto-connect completed, state saved')
        }
      }
    })

    // Show user message
    if (result.success > 0) {
      const message = result.failed > 0 ?
          `Auto-connect completed, successfully connected ${result.success} servers, ${result.failed} connections failed` :
          `Auto-connect completed, successfully connected ${result.success} servers`
      ElMessage.success(message)
    } else if (result.total > 0) {
      ElMessage.warning('Auto-connect completed, but all server connections failed')
    }

    return result
  } catch (error) {
    logger.error('❌ Error occurred during auto-connect:', error)
    ElMessage.error('Error occurred during auto-connect')
    throw error
  }
}

// Validate tool state consistency (for debugging)
const validateToolStates = () => {
  const inconsistencies = []

  serverConfigs.value.forEach(server => {
    if (server.connected && server.tools) {
      server.tools.forEach(tool => {
        const toolKey = `${server.name}.${tool.name}`
        const cachedEnabled = userStateCache.value.enabledTools[toolKey]

        if (cachedEnabled !== undefined && tool.enabled !== cachedEnabled) {
          inconsistencies.push({
            toolKey,
            current: tool.enabled,
            cached: cachedEnabled,
            serverName: server.name
          })
        }
      })
    }
  })

  if (inconsistencies.length > 0) {
    console.warn('🚨 Found tool state inconsistencies:', inconsistencies)
    return inconsistencies
  }

  logger.log('✅ Tool state consistency check passed')
  return []
}

// Watch props changes
watch(() => props.modelValue, (newValue) => {
  if (newValue !== configJson.value) {
    configJson.value = newValue
    parseJsonConfig()
  }
}, { immediate: true })

// Watch pageSize changes, reset current page
watch(pageSize, () => {
  currentPage.value = 1
})

// Watch search keyword changes, reset current page
watch(searchKeyword, () => {
  currentPage.value = 1
})

// Component initialization
onMounted(async () => {
  // 1. Load user state cache
  loadUserState()

  // 2. Load configuration cache
  const cachedConfig = getCacheByKey(CONFIG_CACHE_KEY)
  if (cachedConfig) {
    configJson.value = cachedConfig
    emit('update:modelValue', cachedConfig)
    parseJsonConfig() // This will apply user state
  } else if (!props.modelValue?.trim()) {
    // 3. If no cache and no passed configuration, load example configuration
    await loadExample(true)
  } else {
    // 4. Use passed configuration
    parseJsonConfig()
  }

  // 5. Listen to state manager events
  mcpStateManager.on('servers-reconnected', handleServersReconnected)
  mcpStateManager.on('state-refreshed', handleStateRefreshed)

  // 6. If there are enabled servers, auto-connect
  await nextTick() // Ensure component is fully initialized
  if (userStateCache.value.autoConnectOnLoad) {
    logger.info('🔄 Auto-connecting enabled MCP servers...')
    setTimeout(async () => {
      await autoConnectEnabledServers()

      // After auto-connect completion, validate state consistency
      setTimeout(() => {
        const inconsistencies = validateToolStates()
        if (inconsistencies.length > 0) {
          console.warn('🚨 Found state inconsistencies after auto-connect, attempting to fix...')

          // Try to fix inconsistent states
          inconsistencies.forEach(({ toolKey, cached, serverName }) => {
            const server = serverConfigs.value.find(s => s.name === serverName)
            if (server && server.tools) {
              const tool = server.tools.find(t => `${serverName}.${t.name}` === toolKey)
              if (tool) {
                logger.log(`🔧 Fix tool state: ${toolKey} ${tool.enabled} -> ${cached}`)
                tool.enabled = cached
              }
            }
          })

          // Re-save state
          saveUserState()
          emitConfigChange()
          logger.log('✅ State inconsistency issues fixed')
        }
      }, 2000) // Wait 2 seconds for connections to fully stabilize
    }, 500) // Delay 500ms to execute auto-connect
  }
})

// Clean up connections when component is destroyed
onUnmounted(async () => {
  try {
    // Remove state manager event listeners
    mcpStateManager.off('servers-reconnected', handleServersReconnected)
    mcpStateManager.off('state-refreshed', handleStateRefreshed)

    await mcpClient.cleanup()
  } catch (error) {
    console.error('Failed to clean up MCP connections:', error)
  }
})

// Handle server reconnection events
const handleServersReconnected = async (result) => {
  logger.log('🔔 Received server reconnection event:', result)

  try {
    await refreshServerTools()

    if (result.success > 0) {
      ElMessage.success(`System tools reconnected ${result.success} MCP servers`)
    }
  } catch (error) {
    logger.error('❌ Failed to handle reconnection event:', error)
  }
}

// Handle state refresh events
const handleStateRefreshed = (data) => {
  logger.log('🔔 Received state refresh event:', data)

  // Can add other state synchronization logic here
}

// Expose methods and properties for parent component use
defineExpose({
  getEnabledToolsCount: () => enabledToolsCount.value,
  getConnectedServersCount: () => enabledServersCount.value,
  serverConfigs: serverConfigs, // Expose server configurations
  autoConnectEnabledServers,
  refreshServerTools,
  validateToolStates, // Expose state validation method
  // Get connected tools list
  getConnectedTools: () => {
    const connectedTools = []
    serverConfigs.value.forEach(server => {
      if (server.connected && server.enabled && server.tools) {
        server.tools.forEach(tool => {
          if (tool.enabled) {
            connectedTools.push({
              name: tool.name,
              description: tool.description,
              inputSchema: tool.inputSchema,
              serverName: server.name,
              sessionId: server.sessionId,
              enabled: true
            })
          }
        })
      }
    })
    return connectedTools
  },
  // Debug method: get detailed state information
  getDebugState: () => {
    return {
      userStateCache: userStateCache.value,
      serverStates: serverConfigs.value.map(server => ({
        name: server.name,
        enabled: server.enabled,
        connected: server.connected,
        toolsCount: server.tools?.length || 0,
        enabledToolsCount: server.tools?.filter(t => t.enabled).length || 0,
        tools: server.tools?.map(t => ({ name: t.name, enabled: t.enabled })) || []
      }))
    }
  }
})
</script>

<style scoped lang="scss">
.mcp-enhanced-config-editor {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;

  .editor-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-left {
      h3 {
        margin: 0 0 4px 0;
        font-size: 18px;
        font-weight: 600;
      }

      p {
        margin: 0 0 6px 0;
        opacity: 0.9;
        font-size: 14px;

        &:last-child {
          margin-bottom: 0;
        }

        &.sorting-note {
          font-size: 12px;
          opacity: 0.8;
          font-style: italic;
        }

        &.connection-types {
          display: flex;
          align-items: center;
          gap: 5px;
          margin-top: 8px;
          font-size: 13px;

          .type-badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            color: white;
            margin-right: 6px;

            &.sse {
              background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            }

            &.streamable-http {
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
          }
        }
      }
    }

    .header-actions {
      display: flex;
      gap: 12px;

      .el-button {
        --el-button-bg-color: rgba(255, 255, 255, 0.2);
        --el-button-border-color: rgba(255, 255, 255, 0.3);
        --el-button-text-color: #fff;
        --el-button-hover-bg-color: rgba(255, 255, 255, 0.3);
        backdrop-filter: blur(10px);
      }
    }
  }

  .tools-stats {
    background: #f8f9fa;
    padding: 16px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e9ecef;
    flex-wrap: wrap;
    gap: 16px;

    .stats-left {
      display: flex;
      gap: 24px;
      flex-wrap: wrap;
    }

    .stats-right {
      display: flex;
      gap: 16px;
      align-items: center;
    }

    .stats-item {
      display: flex;
      align-items: center;
      gap: 8px;

      .label {
        color: #666;
        font-size: 14px;
      }

      .value {
        font-weight: 600;
        color: #333;

        &.warning {
          color: #f56565;
        }

        &.optimal {
          color: #67c23a;
        }

        .suggestion {
          font-size: 12px;
          color: #909399;
          font-weight: normal;
          margin-left: 4px;
        }
      }

      &.enabled .value {
        color: #38a169;
      }

      &.tools .value {
        color: #3182ce;
      }

      &.search-filter {
        .el-input {
          .el-input__inner {
            border-radius: 8px;
            font-size: 13px;
            background: white;
            border: 1px solid #e9ecef;
            transition: all 0.3s ease;

            &:focus {
              border-color: #409eff;
              box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
            }
          }

          .el-input__prefix {
            color: #909399;
          }
        }
      }

      &.filter-info .value {
        color: #f56c6c;
        font-weight: 600;
      }

      &.pagination-control {
        .el-select {
          .el-input__inner {
            border-radius: 6px;
            font-size: 13px;
          }
        }
      }
    }
  }

  .json-editor-section {
    padding: 24px;

    .json-editor-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;

      .editor-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
        color: #333;
      }

      .editor-actions {
        display: flex;
        gap: 8px;
      }
    }

    .json-editor-wrapper {
      position: relative;

      .json-textarea {
        :deep(.el-textarea__inner) {
          font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
          font-size: 13px;
          line-height: 1.6;
          background: #f8f9fa;
          border: 1px solid #e9ecef;
          border-radius: 8px;
          resize: vertical;
        }
      }

      .json-error {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #f56565;
        font-size: 14px;
        margin-top: 8px;
        padding: 8px 12px;
        background: #fed7d7;
        border-radius: 6px;
      }

      .validation-success {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #38a169;
        font-size: 14px;
        margin-top: 8px;
        padding: 8px 12px;
        background: #c6f6d5;
        border-radius: 6px;
      }
    }
  }

  .visual-editor-section {
    padding: 24px;

    .servers-container {
      .pagination-info-simple {
        font-size: 13px;
        color: #666;
        margin-bottom: 16px;
        padding: 8px 16px;
        background: #f8f9fa;
        border-radius: 6px;
        border: 1px solid #e9ecef;
        text-align: center;

        .search-info {
          color: #409eff;
          font-weight: 500;
          margin-left: 4px;
        }
      }

      .pagination-wrapper {
        display: flex;
        justify-content: center;
        margin-top: 24px;
        padding: 20px 0;

        .el-pagination {
          .el-pager {
            .number {
              border-radius: 6px;
              margin: 0 2px;
            }
          }

          .btn-prev,
          .btn-next {
            border-radius: 6px;
          }
        }
      }
    }

    .servers-list {
      display: flex;
      flex-direction: column;
      gap: 20px;

      .server-item {
        border: 1px solid #e9ecef;
        border-radius: 12px;
        overflow: hidden;
        transition: all 0.3s ease;

        &:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        &.server-disabled {
          opacity: 0.6;
          background: #f8f9fa;
        }

        &.server-error {
          border-color: #f56c6c;
          background: #fef0f0;
        }

        .server-header {
          padding: 20px;
          display: flex;
          align-items: center;
          gap: 16px;
          background: #fff;

          .server-status {
            flex-shrink: 0;
            display: flex;
            align-items: center;
            gap: 12px;

            .status-tag {
              display: flex;
              align-items: center;
              gap: 4px;

              .is-loading {
                animation: rotating 2s linear infinite;
              }
            }
          }

          .server-info {
            flex: 1;

            .server-name {
              display: flex;
              align-items: center;
              gap: 12px;
              margin-bottom: 8px;

              .name-badge {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                font-size: 16px;

                &.sse {
                  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                }

                &.streamable-http {
                  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }


              }

              .name-content {
                h4 {
                  margin: 0 0 4px 0;
                  color: #333;
                  font-size: 16px;
                  font-weight: 600;
                }

                .server-tags {
                  display: flex;
                  gap: 6px;
                  align-items: center;
                  flex-wrap: wrap;
                }
              }
            }

            .server-meta {
              display: flex;
              flex-wrap: wrap;
              gap: 16px;
              margin-bottom: 8px;

              .meta-item {
                display: flex;
                align-items: center;
                gap: 4px;
                font-size: 13px;
                color: #666;
                background: #f8f9fa;
                padding: 4px 8px;
                border-radius: 6px;

                .info-icon {
                  color: #909399;
                  font-size: 12px;
                  cursor: help;
                  margin-left: 4px;

                  &:hover {
                    color: #409eff;
                  }
                }
              }
            }

            .server-description {
              color: #666;
              font-size: 13px;
              line-height: 1.5;
            }
          }

          .server-actions {
            flex-shrink: 0;
          }
        }

        .tools-list {
          background: #f8f9fa;
          padding: 20px;
          border-top: 1px solid #e9ecef;

          .tools-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;

            h5 {
              margin: 0;
              color: #333;
              font-size: 14px;
              font-weight: 600;
            }

            .tools-actions {
              display: flex;
              gap: 8px;
            }
          }

          .tools-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 12px;

            .tool-item {
              background: white;
              border: 1px solid #e9ecef;
              border-radius: 8px;
              padding: 12px;
              display: flex;
              align-items: center;
              gap: 12px;
              transition: all 0.2s ease;

              &:hover {
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
              }

              &.tool-disabled {
                opacity: 0.5;
                background: #f8f9fa;
              }

              .tool-toggle {
                flex-shrink: 0;
              }

              .tool-info {
                flex: 1;
                min-width: 0;

                .tool-name {
                  font-weight: 600;
                  color: #333;
                  font-size: 13px;
                  margin-bottom: 2px;
                  word-break: break-word;
                }

                .tool-description {
                  color: #666;
                  font-size: 12px;
                  line-height: 1.3;
                  word-break: break-word;
                }
              }

              .tool-actions {
                flex-shrink: 0;
              }
            }
          }
        }
      }
    }

    .empty-state {
      text-align: center;
      padding: 40px 20px;
    }
  }
}

// Responsive design
@media (max-width: 1024px) {
  .mcp-enhanced-config-editor {
    .tools-stats {
      .stats-left {
        gap: 16px;
      }

      .stats-right {
        margin-top: 8px;
      }
    }
  }
}

@media (max-width: 768px) {
  .mcp-enhanced-config-editor {
    .editor-header {
      flex-direction: column;
      gap: 12px;
      text-align: center;

      .header-actions {
        justify-content: center;
      }
    }

    .tools-stats {
      flex-direction: column;
      gap: 12px;

      .stats-left {
        justify-content: center;
        flex-wrap: wrap;

        .stats-item.search-filter {
          width: 100%;
          justify-content: center;
          margin-top: 8px;

          .el-input {
            width: 100% !important;
            max-width: 280px;
          }
        }
      }

      .stats-right {
        justify-content: center;
        flex-wrap: wrap;
      }
    }

    .servers-container {
      .pagination-header {
        flex-direction: column;
        gap: 12px;
        text-align: center;

        .pagination-controls {
          justify-content: center;
        }
      }
    }

    .visual-editor-section {
      .servers-list {
        .server-item {
          .server-header {
            flex-direction: column;
            gap: 12px;
            text-align: center;
          }

          .tools-list {
            .tools-grid {
              grid-template-columns: 1fr;
            }
          }
        }
      }
    }
  }
}

// Config center dialog styles
:deep(.config-center) {
  .el-dialog {
    border-radius: 16px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);

    .el-dialog__header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 20px 24px;
      border-radius: 16px 16px 0 0;
      border-bottom: none;

      .el-dialog__title {
        font-weight: 600;
        font-size: 18px;
      }

      .el-dialog__headerbtn {
        top: 20px;
        right: 20px;

        .el-dialog__close {
          color: rgba(255, 255, 255, 0.8);
          font-size: 18px;

          &:hover {
            color: white;
          }
        }
      }
    }

    .el-dialog__body {
      padding: 0;

      .config-center-content {
        position: relative;
        min-height: 60vh;

        .loading-placeholder {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 60vh;
          text-align: center;
          color: #666;
          animation: fadeIn 0.5s ease-in-out;

          .loading-text {
            font-size: 18px;
            font-weight: 500;
            color: #409eff;
            margin-bottom: 8px;
            animation: pulse 1.5s infinite;
          }

          .loading-description {
            font-size: 14px;
            color: #909399;
            opacity: 0.8;
            animation: fadeInDelay 0.8s ease-in-out;
          }
        }
      }
    }
  }
}

// Confirm dialog custom styles
:deep(.mcp-confirm-dialog) {
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);

  .el-message-box__header {
    background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 50%, #fecfef 100%);
    color: #333;
    padding: 20px 24px;
    border-radius: 16px 16px 0 0;
    border-bottom: none;

    .el-message-box__title {
      font-weight: 600;
      font-size: 16px;
    }

    .el-message-box__headerbtn {
      top: 20px;
      right: 20px;

      .el-message-box__close {
        color: #666;
        font-size: 18px;

        &:hover {
          color: #333;
        }
      }
    }
  }

  .el-message-box__content {
    padding: 24px;

    .el-message-box__container {
      .el-message-box__message {
        color: #333;
        font-size: 14px;
        line-height: 1.6;
        margin-left: 0;
      }

      .el-message-box__status {
        color: #f39c12;
        font-size: 20px;
        margin-right: 12px;
      }
    }
  }

  .el-message-box__btns {
    padding: 16px 24px 24px;

    .el-button {
      border-radius: 8px;
      padding: 10px 20px;
      font-weight: 500;

      &.el-button--default {
        background: #f8f9fa;
        border-color: #e9ecef;
        color: #6c757d;

        &:hover {
          background: #e9ecef;
          border-color: #dee2e6;
          color: #495057;
        }
      }

      &.el-button--primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;

        &:hover {
          background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
        }
      }
    }
  }
}

// Rotation animation
@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// Config center loading animation
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.8;
  }
}

@keyframes fadeInDelay {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 0.8;
    transform: translateY(0);
  }
}
</style>