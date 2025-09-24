// Export all modules
export * from './components/index.js'
export * from './services/index.js'
export * from './utils/index.js'
export * from './i18n/index.js'

// Export modules by category
export { default as components } from './components/index.js'
export { default as services } from './services/index.js'
export { default as utils } from './utils/index.js'

// Version information
export const version = '1.0.0'

// Default export
export { default } from './main.js'