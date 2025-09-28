/**
 * Event Bus Utility
 * Implements inter-component communication based on mitt library
 */

import mitt from 'mitt'

// Create event bus instance
const eventBus = mitt()

// Event type definitions
export const EVENT_TYPES = {
  // Chat related events
  CHAT_MESSAGE_SEND: 'chat:message:send',
  CHAT_MESSAGE_RECEIVE: 'chat:message:receive',
  CHAT_CLEAR: 'chat:clear',
  
  // MCP related events
  MCP_CONNECT: 'mcp:connect',
  MCP_DISCONNECT: 'mcp:disconnect',
  MCP_TOOL_CALL: 'mcp:tool:call',
  MCP_STATUS_CHANGE: 'mcp:status:change',
  
  // Configuration related events
  CONFIG_CHANGE: 'config:change',
  CONFIG_SAVE: 'config:save',
  CONFIG_LOAD: 'config:load',
  
  // UI related events
  MODAL_SHOW: 'ui:modal:show',
  MODAL_HIDE: 'ui:modal:hide',
  NOTIFICATION_SHOW: 'ui:notification:show',
  
  // System events
  SYSTEM_ERROR: 'system:error',
  SYSTEM_WARNING: 'system:warning',
  SYSTEM_INFO: 'system:info'
}

/**
 * Emit event
 * @param {string} type - Event type
 * @param {any} data - Event data
 */
export const emit = (type, data) => {
  eventBus.emit(type, data)
}

/**
 * Listen to event
 * @param {string} type - Event type
 * @param {function} handler - Event handler function
 */
export const on = (type, handler) => {
  eventBus.on(type, handler)
}

/**
 * Listen to event (once only)
 * @param {string} type - Event type
 * @param {function} handler - Event handler function
 */
export const once = (type, handler) => {
  const wrappedHandler = (data) => {
    handler(data)
    eventBus.off(type, wrappedHandler)
  }
  eventBus.on(type, wrappedHandler)
}

/**
 * Remove event listener
 * @param {string} type - Event type
 * @param {function} handler - Event handler function (optional)
 */
export const off = (type, handler) => {
  eventBus.off(type, handler)
}

/**
 * Clear all event listeners
 */
export const clear = () => {
  eventBus.all.clear()
}

/**
 * Get all event listeners
 * @returns {Map} Event listener map
 */
export const getAll = () => {
  return eventBus.all
}

// Vue composition function: use event bus in components
export const useEventBus = () => {
  return {
    emit,
    on,
    once,
    off,
    clear,
    getAll,
    EVENT_TYPES
  }
}

// Default export event bus instance
export default {
  emit,
  on,
  once,
  off,
  clear,
  getAll,
  EVENT_TYPES,
  useEventBus
}