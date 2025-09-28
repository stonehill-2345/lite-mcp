// Named exports for modules
// Chat services
export { ChatService } from '@/services/chat/ChatService'
export { ReActEngine } from '@/services/chat/ReActEngine'

// Configuration services
export { default as ConfigStorage } from '@/services/config/ConfigStorage'
export { DEFAULT_PROMPTS, PromptTemplates } from '@/services/config/defaultPrompts'
export { DEFAULT_MODEL_CONFIG, MODEL_PROVIDERS, ModelUtils, MODEL_CONTEXT_LIMITS } from '@/services/config/modelConfigs'

// Unified export
export default {
  chat: {
    ChatService: () => import('@/services/chat/ChatService'),
    ReActEngine: () => import('@/services/chat/ReActEngine')
  },
  config: {
    ConfigStorage: () => import('@/services/config/ConfigStorage'),
    defaultPrompts: () => import('@/services/config/defaultPrompts'),
    modelConfigs: () => import('@/services/config/modelConfigs')
  }
}