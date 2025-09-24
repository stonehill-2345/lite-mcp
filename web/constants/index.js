// MCP related constants
export const MCP_CONSTANTS = {
  // Connection status
  CONNECTION_STATUS: {
    DISCONNECTED: 'disconnected',
    CONNECTING: 'connecting',
    CONNECTED: 'connected',
    ERROR: 'error'
  },
  
  // Message types
  MESSAGE_TYPES: {
    INITIALIZATION: 'initialization',
    TOOLS: 'tools',
    RESOURCES: 'resources',
    COMPLETION: 'completion',
    SAMPLING: 'sampling',
    LOGGING: 'logging',
    PROMPT: 'prompt',
    NOTIFICATION: 'notification'
  },
  
  // Tool status
  TOOL_STATUS: {
    IDLE: 'idle',
    RUNNING: 'running',
    SUCCESS: 'success',
    ERROR: 'error'
  }
}

// Chat related constants
export const CHAT_CONSTANTS = {
  // Message roles
  ROLES: {
    USER: 'user',
    ASSISTANT: 'assistant',
    SYSTEM: 'system',
    TOOL: 'tool'
  },
  
  // Message status
  MESSAGE_STATUS: {
    PENDING: 'pending',
    SENDING: 'sending',
    SENT: 'sent',
    ERROR: 'error'
  },
  
  // Chat modes
  CHAT_MODES: {
    NORMAL: 'normal',
    REACT: 'react',
    STREAM: 'stream'
  }
}

// Configuration related constants
export const CONFIG_CONSTANTS = {
  // Storage keys
  STORAGE_KEYS: {
    MCP_CONFIG: 'mcp_config',
    CHAT_CONFIG: 'chat_config',
    MODEL_CONFIG: 'model_config',
    PROMPT_CONFIG: 'prompt_config',
    ADVANCED_CONFIG: 'advanced_config',
    REACT_CONFIG: 'react_config'
  },
  
  // Configuration version
  CONFIG_VERSION: '1.0.0',
  
  // Default configurations
  DEFAULT_CONFIGS: {
    MCP: {
      maxRetries: 3,
      timeout: 10000,
      heartbeatInterval: 30000
    },
    CHAT: {
      maxMessages: 100,
      temperature: 0.7,
      maxTokens: 4096
    },
    DEBUG: {
      enabled: false,
      level: 'info',
      components: []
    }
  }
}

// UI related constants
export const UI_CONSTANTS = {
  // Themes
  THEMES: {
    LIGHT: 'light',
    DARK: 'dark',
    AUTO: 'auto'
  },
  
  // Layout
  LAYOUT: {
    SIDEBAR_WIDTH: 300,
    HEADER_HEIGHT: 60,
    FOOTER_HEIGHT: 40
  },
  
  // Animation duration
  ANIMATION_DURATION: {
    FAST: 200,
    NORMAL: 300,
    SLOW: 500
  }
}

// Error codes
export const ERROR_CODES = {
  // MCP errors
  MCP_CONNECTION_FAILED: 'MCP_CONNECTION_FAILED',
  MCP_TIMEOUT: 'MCP_TIMEOUT',
  MCP_INVALID_RESPONSE: 'MCP_INVALID_RESPONSE',
  
  // Chat errors
  CHAT_SEND_FAILED: 'CHAT_SEND_FAILED',
  CHAT_INVALID_MESSAGE: 'CHAT_INVALID_MESSAGE',
  
  // Configuration errors
  CONFIG_INVALID: 'CONFIG_INVALID',
  CONFIG_SAVE_FAILED: 'CONFIG_SAVE_FAILED',
  CONFIG_LOAD_FAILED: 'CONFIG_LOAD_FAILED'
}

// Regular expressions
export const REGEX_PATTERNS = {
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  URL: /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$/,
  JSON: /^[\],:{}\s]*$/,
  MCP_SERVER_NAME: /^[a-zA-Z0-9_-]+$/
}

// Default export all constants
export default {
  MCP_CONSTANTS,
  CHAT_CONSTANTS,
  CONFIG_CONSTANTS,
  UI_CONSTANTS,
  ERROR_CODES,
  REGEX_PATTERNS
}