<template>
  <div class="mcp-server-card" :data-type="serverType">
    <div class="card-header">
      <div class="server-info">
        <div class="server-name">
          <el-icon class="server-icon">
            <component :is="getServerIcon(serverType)" />
          </el-icon>
          <span class="name" :title="serverName">{{ serverName }}</span>
          <el-tag :type="getServerTypeTag(serverType)" size="small">{{ serverType.toUpperCase() }}</el-tag>
        </div>
        <div class="server-description" :title="serverConfig.description">{{ serverConfig.description }}</div>
      </div>
      <div class="card-actions">
        <el-button 
          v-if="embedded && ['sse', 'streamable-http'].includes(serverType)"
          type="warning" 
          :icon="Plus" 
          size="small"
          @click="addToEditor"
          :title="$t('mcp.serverCard.addToAssistant')"
        >
          {{ $t('mcp.serverCard.addToAssistant') }}
        </el-button>
        <el-button 
          type="primary" 
          :icon="DocumentCopy" 
          circle 
          size="small"
          @click="handleCopyConfig"
          :title="$t('mcp.serverCard.copyConfig')"
        />
      </div>
    </div>
    
    <div class="card-content">
      <div class="config-display">
        <pre class="config-json">{{ formattedConfig }}</pre>
      </div>
      
      <div class="config-meta" v-if="serverType === 'stdio'">
        <div class="meta-item">
          <span class="meta-label">{{ $t('mcp.serverCard.command') }}:</span>
          <code class="meta-value">{{ serverConfig.command }}</code>
        </div>
        <div class="meta-item" v-if="serverConfig.args && serverConfig.args.length">
          <span class="meta-label">{{ $t('mcp.serverCard.args') }}:</span>
          <code class="meta-value">{{ serverConfig.args.join(' ') }}</code>
        </div>
      </div>
      
      <div class="config-meta" v-else-if="serverType === 'sse'">
        <div class="meta-item">
          <span class="meta-label">{{ $t('mcp.serverCard.url') }}:</span>
          <code class="meta-value">{{ serverConfig.url }}</code>
        </div>
      </div>
      

      
      <div class="config-meta" v-else-if="serverType === 'streamable-http'">
        <div class="meta-item">
          <span class="meta-label">{{ $t('mcp.serverCard.url') }}:</span>
          <code class="meta-value">{{ serverConfig.url }}</code>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { DocumentCopy, Edit, Monitor, Connection, Link, Plus } from '@element-plus/icons-vue'
import { useClipboard } from '@/utils/UseClipboardHook'

const props = defineProps({
  serverName: {
    type: String,
    required: true
  },
  serverConfig: {
    type: Object,
    required: true
  },
  serverType: {
    type: String,
    required: true,
    validator: (value) => ['stdio', 'sse', 'streamable-http'].includes(value)
  },
  embedded: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['edit', 'add-to-editor'])

const { t } = useI18n()
const { copyToClipboard } = useClipboard()

// Format configuration for display
const formattedConfig = computed(() => {
  const config = {
    [props.serverName]: props.serverConfig
  }
  return JSON.stringify(config, null, 2)
})

// Format configuration for copying (without outer braces)
const copyableConfig = computed(() => {
  const config = {
    [props.serverName]: props.serverConfig
  }
  const jsonStr = JSON.stringify(config, null, 2)
  // Remove outer braces and leading/trailing whitespace
  return jsonStr.replace(/^\{\s*/, '').replace(/\s*\}$/, '').trim()
})

// Get icon corresponding to server type
const getServerIcon = (type) => {
  const iconMap = {
    stdio: Monitor,
    sse: Connection,
    'streamable-http': Link
  }
  return iconMap[type] || Monitor
}

// Get tag type corresponding to server type
const getServerTypeTag = (type) => {
  const tagMap = {
    stdio: 'info',
    sse: 'success',
    'streamable-http': 'primary'
  }
  return tagMap[type] || 'info'
}

// Copy configuration
const handleCopyConfig = async () => {
  try {
    await copyToClipboard(copyableConfig.value, t('mcp.serverCard.configCopied'))
  } catch (error) {
    ElMessage.error(t('mcp.serverCard.copyFailed'))
  }
}

// Edit configuration
const editConfig = () => {
  emit('edit', {
    name: props.serverName,
    config: props.serverConfig,
    type: props.serverType
  })
}

// Add to editor
const addToEditor = () => {
  emit('add-to-editor', {
    serverName: props.serverName,
    serverConfig: props.serverConfig,
    serverType: props.serverType
  })
}
</script>

<style scoped lang="scss">
.mcp-server-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
  }

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    z-index: 0;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
    position: relative;
    z-index: 1;

    .server-info {
      flex: 1;
      min-width: 0;
      margin-right: 16px;

      .server-name {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;

        .server-icon {
          font-size: 18px;
          color: #fff;
          flex-shrink: 0;
        }

        .name {
          font-size: 18px;
          font-weight: 600;
          color: #fff;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          max-width: 150px;
          flex-shrink: 1;
        }

        .el-tag {
          --el-tag-bg-color: rgba(255, 255, 255, 0.2);
          --el-tag-text-color: #fff;
          --el-tag-border-color: rgba(255, 255, 255, 0.3);
          flex-shrink: 0;
        }
      }

      .server-description {
        color: rgba(255, 255, 255, 0.9);
        font-size: 14px;
        line-height: 1.5;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .card-actions {
      display: flex;
      gap: 8px;
      flex-shrink: 0;

      .el-button {
        --el-button-bg-color: rgba(255, 255, 255, 0.2);
        --el-button-border-color: rgba(255, 255, 255, 0.3);
        --el-button-text-color: #fff;
        --el-button-hover-bg-color: rgba(255, 255, 255, 0.3);
        backdrop-filter: blur(10px);
      }
    }
  }

  .card-content {
    position: relative;
    z-index: 1;

    .config-display {
      background: rgba(0, 0, 0, 0.3);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
      border: 1px solid rgba(255, 255, 255, 0.1);

      .config-json {
        color: #fff;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        font-size: 12px;
        line-height: 1.5;
        white-space: pre-wrap;
        word-break: break-all;
        margin: 0;
      }
    }

    .config-meta {
      .meta-item {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-bottom: 12px;

        .meta-label {
          font-weight: 600;
          color: #fff;
          font-size: 13px;
        }

        .meta-value {
          background: rgba(0, 0, 0, 0.2);
          padding: 6px 10px;
          border-radius: 6px;
          color: #fff;
          font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
          font-size: 12px;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .args-list, .env-list {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;

          .el-tag {
            --el-tag-bg-color: rgba(255, 255, 255, 0.15);
            --el-tag-text-color: #fff;
            --el-tag-border-color: rgba(255, 255, 255, 0.2);
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 11px;
          }
        }
      }
    }
  }
}

// Different gradient colors for different card types
.mcp-server-card {
  &[data-type="sse"] {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  }
}
</style> 