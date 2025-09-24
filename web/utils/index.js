// Import modules for default export
import DebugLoggerModule from '@/utils/DebugLogger'
import validationModule from '@/utils/validation'
import formatModule from '@/utils/format'

// Export all utility functions
export * from '@/utils/DebugLogger'
export * from '@/utils/validation'
export * from '@/utils/format'

// Default exports for each module
export { default as DebugLogger } from '@/utils/DebugLogger'
export { default as validation } from '@/utils/validation'
export { default as format } from '@/utils/format'

// Unified default export
export default {
    DebugLogger: DebugLoggerModule,
    validation: validationModule,
    format: formatModule
}