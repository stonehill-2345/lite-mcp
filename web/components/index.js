// MCP Components
export { default as McpConfigEditor } from '@/components/mcp/McpConfigEditor.vue'
export { default as McpChatInterface } from '@/components/mcp/McpChatInterface.vue'
export { default as McpToolsPanel } from '@/components/mcp/McpToolsPanel.vue'
export { default as McpServerCard } from '@/components/mcp/McpServerCard.vue'

// Chat Components
export { default as ChatInterface } from '@/components/chat/ChatInterface.vue'
export { default as ChatMessages } from '@/components/chat/ChatMessages.vue'
export { default as ChatInput } from '@/components/chat/ChatInput.vue'
export { default as ChatSettings } from '@/components/chat/ChatSettings.vue'
export { default as ReasoningTrace } from '@/components/chat/ReasoningTrace.vue'
export { default as ToolCallDisplay } from '@/components/chat/ToolCallDisplay.vue'

// Configuration Components
export { default as ModelConfig } from '@/components/config/ModelConfig.vue'
export { default as PromptConfig } from '@/components/config/PromptConfig.vue'
export { default as AdvancedConfig } from '@/components/config/AdvancedConfig.vue'
export { default as ReActConfig } from '@/components/config/ReActConfig.vue'

// Grouped Exports
export const McpComponents = {
  McpConfigEditor: () => import('@/components/mcp/McpConfigEditor.vue'),
  McpChatInterface: () => import('@/components/mcp/McpChatInterface.vue'),
  McpToolsPanel: () => import('@/components/mcp/McpToolsPanel.vue'),
  McpServerCard: () => import('@/components/mcp/McpServerCard.vue')
}

export const ChatComponents = {
  ChatInterface: () => import('@/components/chat/ChatInterface.vue'),
  ChatMessages: () => import('@/components/chat/ChatMessages.vue'),
  ChatInput: () => import('@/components/chat/ChatInput.vue'),
  ChatSettings: () => import('@/components/chat/ChatSettings.vue'),
  ReasoningTrace: () => import('@/components/chat/ReasoningTrace.vue'),
  ToolCallDisplay: () => import('@/components/chat/ToolCallDisplay.vue')
}

export const ConfigComponents = {
  ModelConfig: () => import('@/components/config/ModelConfig.vue'),
  PromptConfig: () => import('@/components/config/PromptConfig.vue'),
  AdvancedConfig: () => import('@/components/config/AdvancedConfig.vue'),
  ReActConfig: () => import('@/components/config/ReActConfig.vue')
}

// Default Export
export default {
  mcp: McpComponents,
  chat: ChatComponents,
  config: ConfigComponents
}