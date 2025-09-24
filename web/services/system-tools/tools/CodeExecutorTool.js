import { SystemTool } from '@/services/system-tools/base/SystemTool.js'
import DebugLogger from "@/utils/DebugLogger"

const logger = DebugLogger.createLogger('CodeExecutorTool')

/**
 * Code Execution Tool
 * Execute JavaScript code in a secure sandbox environment, supporting mathematical calculations, string processing, data conversion, etc.
 */
export class CodeExecutorTool extends SystemTool {
  constructor(config = {}) {
    super({
      name: 'execute_code',
      description: 'Execute JavaScript code in a secure sandbox environment, supporting common programming tasks such as mathematical calculations, string processing, JSON operations, and array processing',
      category: 'utility',
      version: '1.0.0',
      author: 'system',
      inputSchema: {
        type: 'object',
        properties: {
          code: {
            type: 'string',
            description: 'JavaScript code to execute'
          },
          timeout: {
            type: 'number',
            description: 'Execution timeout (milliseconds)',
            minimum: 100,
            maximum: 10000,
            default: 5000
          },
          returnType: {
            type: 'string',
            description: 'Expected return type',
            enum: ['auto', 'string', 'number', 'object', 'array'],
            default: 'auto'
          },
          includeHelpers: {
            type: 'boolean',
            description: 'Whether to include helper functions (Math, Date, JSON, etc.)',
            default: true
          }
        },
        required: ['code']
      },
      config: {
        timeout: 10000,
        maxCodeLength: 5000,
        allowedGlobals: ['Math', 'Date', 'JSON', 'parseInt', 'parseFloat', 'isNaN', 'isFinite']
      },
      ...config
    })
  }

  /**
   * Execute code
   */
  async doExecute(parameters, context) {
    logger.log(`[CodeExecutorTool] Starting code execution`)
    logger.log(`[CodeExecutorTool] Received parameters:`, parameters)

    try {
      const {
        code,
        timeout = 5000,
        returnType = 'auto',
        includeHelpers = true
      } = parameters

      // Parameter validation
      if (!code || typeof code !== 'string') {
        throw new Error('Code parameter cannot be empty and must be a string')
      }

      if (code.length > this.config.maxCodeLength) {
        throw new Error(`Code length cannot exceed ${this.config.maxCodeLength} characters`)
      }

      // Security check
      const securityCheck = this.performSecurityCheck(code)
      if (!securityCheck.safe) {
        throw new Error(`Code security check failed: ${securityCheck.reason}`)
      }

      logger.log(`[CodeExecutorTool] Security check passed, starting code execution`)

      // Create secure execution environment
      const result = await this.executeInSandbox(code, {
        timeout,
        includeHelpers,
        returnType
      })

      logger.log(`[CodeExecutorTool] ✅ Code execution successful:`, result)

      // Build user-friendly execution result description
      let executionDescription = `Code execution successful!`
      executionDescription += `\nExecution result: ${result.value}`
      executionDescription += `\nResult type: ${typeof result.value}`
      executionDescription += `\nExecution time: ${result.executionTime}ms`
      
      if (result.output) {
        executionDescription += `\nConsole output: ${result.output}`
      }

      return {
        success: true,
        message: executionDescription,
        data: {
          result: result.value,
          type: typeof result.value,
          executionTime: result.executionTime,
          codeLength: code.length,
          returnType: returnType,
          output: result.output || null
        },
        duration: Date.now() - context.startTime
      }

    } catch (error) {
      logger.error(`[CodeExecutorTool] ❌ Code execution failed:`, error)
      return {
        success: false,
        message: `Code execution failed: ${error.message}`,
        error: error.message,
        data: {
          codeLength: parameters.code?.length || 0,
          errorType: error.name || 'Error'
        },
        duration: Date.now() - context.startTime
      }
    }
  }

  /**
   * Security check
   */
  performSecurityCheck(code) {
    // Forbidden keywords and patterns
    const forbiddenPatterns = [
      /\beval\b/i,
      /\bFunction\b/i,
      /\bsetTimeout\b/i,
      /\bsetInterval\b/i,
      /\bimport\b/i,
      /\brequire\b/i,
      /\bprocess\b/i,
      /\bglobal\b/i,
      /\bwindow\b/i,
      /\bdocument\b/i,
      /\blocalStorage\b/i,
      /\bsessionStorage\b/i,
      /\bfetch\b/i,
      /\bXMLHttpRequest\b/i,
      /\bWebSocket\b/i,
      /\b__proto__\b/i,
      /\bconstructor\b/i,
      /\bprototype\b/i,
      /\bdelete\b/i,
      /\bwith\b/i,
      /\btry\s*{\s*}\s*catch\s*\([^)]*\)\s*{\s*}/i // Empty try-catch may be used to hide errors
    ]

    for (const pattern of forbiddenPatterns) {
      if (pattern.test(code)) {
        return {
          safe: false,
          reason: `Contains forbidden keywords or patterns: ${pattern.source}`
        }
      }
    }

    // Check code length
    if (code.length > this.config.maxCodeLength) {
      return {
        safe: false,
        reason: `Code length exceeds limit (${this.config.maxCodeLength} characters)`
      }
    }

    // Check nesting depth (prevent overly complex code)
    const maxNestingDepth = 10
    let depth = 0
    let maxDepth = 0
    for (const char of code) {
      if (char === '{' || char === '(' || char === '[') {
        depth++
        maxDepth = Math.max(maxDepth, depth)
      } else if (char === '}' || char === ')' || char === ']') {
        depth--
      }
    }

    if (maxDepth > maxNestingDepth) {
      return {
        safe: false,
        reason: `Code nesting depth too deep (maximum allowed ${maxNestingDepth} levels)`
      }
    }

    return { safe: true }
  }

  /**
   * Execute code in sandbox
   */
  async executeInSandbox(code, options) {
    const { timeout, includeHelpers, returnType } = options
    const startTime = Date.now()

    return new Promise((resolve, reject) => {
      // Set timeout
      const timeoutId = setTimeout(() => {
        reject(new Error(`Code execution timed out (${timeout}ms)`))
      }, timeout)

      try {
        // Create restricted context
        const context = this.createSandboxContext(includeHelpers)
        
        // Capture output
        const outputs = []
        context.console = {
          log: (...args) => outputs.push(args.join(' ')),
          error: (...args) => outputs.push('ERROR: ' + args.join(' ')),
          warn: (...args) => outputs.push('WARN: ' + args.join(' '))
        }

        // Wrap code to return result
        // Check if code contains return statement
        const hasReturn = /\breturn\b/.test(code)
        
        // Check if code is multi-line statement (contains semicolons, line breaks, or declaration statements)
        const isMultiStatement = /[;\n]/.test(code) || /\b(var|let|const|function|class|if|for|while|do|switch|try)\b/.test(code)
        
        let executableCode
        if (hasReturn || isMultiStatement) {
          // If code contains return statement or is multi-line statement, wrap in function for execution
          let processedCode = code
          
          if (!hasReturn && isMultiStatement) {
            // For multi-line code without return, try to intelligently process the last line
            const lines = code.trim().split('\n')
            const lastLine = lines[lines.length - 1].trim()
            
            // If last line is a variable name or simple expression, add return
            if (lastLine && !lastLine.startsWith('//')) {
              // Remove trailing semicolon (if any)
              const cleanLastLine = lastLine.replace(/;$/, '')
              
              // Check if it's a declaration statement or control structure
              const isDeclaration = /\b(var|let|const|function|class|if|for|while|do|switch|try|catch|finally)\b/.test(cleanLastLine)
              
              // Check if it's a simple variable name or expression
              const isSimpleExpression = /^[a-zA-Z_$][a-zA-Z0-9_$]*$/.test(cleanLastLine) || // Variable name
                                        /^[a-zA-Z_$][a-zA-Z0-9_$.[\]()]*$/.test(cleanLastLine) || // Property access
                                        /^[^=;{}]+$/.test(cleanLastLine) // Simple expression (no assignment, semicolons, or braces)
              
              if (!isDeclaration && (isSimpleExpression || cleanLastLine)) {
                // Change last line to return statement
                lines[lines.length - 1] = `return ${cleanLastLine};`
                processedCode = lines.join('\n')
              }
            }
          }
          
          executableCode = `
            const userFunction = function() {
              ${processedCode}
            };
            return userFunction();
          `
        } else {
          // If code is simple expression, return as expression directly
          executableCode = `
            return (${code});
          `
        }

        // Use Function constructor to execute in restricted environment
        const func = new Function(...Object.keys(context), executableCode)
        const result = func(...Object.values(context))

        clearTimeout(timeoutId)

        const executionTime = Date.now() - startTime
        let finalResult = result

        // Process result based on return type
        if (returnType !== 'auto') {
          finalResult = this.convertResultType(result, returnType)
        }

        resolve({
          value: finalResult,
          executionTime,
          output: outputs.length > 0 ? outputs.join('\n') : null
        })

      } catch (error) {
        clearTimeout(timeoutId)
        reject(new Error(`Execution error: ${error.message}`))
      }
    })
  }

  /**
   * Create sandbox context
   */
  createSandboxContext(includeHelpers) {
    const context = {}

    if (includeHelpers) {
      // Safe global objects
      context.Math = Math
      context.Date = Date
      context.JSON = JSON
      context.parseInt = parseInt
      context.parseFloat = parseFloat
      context.isNaN = isNaN
      context.isFinite = isFinite
      context.Number = Number
      context.String = String
      context.Boolean = Boolean
      context.Array = Array
      context.Object = Object

      // Common array and string methods
      context.map = (arr, fn) => Array.isArray(arr) ? arr.map(fn) : []
      context.filter = (arr, fn) => Array.isArray(arr) ? arr.filter(fn) : []
      context.reduce = (arr, fn, initial) => Array.isArray(arr) ? arr.reduce(fn, initial) : initial
      context.sort = (arr, fn) => Array.isArray(arr) ? [...arr].sort(fn) : []
      context.reverse = (arr) => Array.isArray(arr) ? [...arr].reverse() : []
      
      // String processing functions
      context.trim = (str) => String(str).trim()
      context.split = (str, sep) => String(str).split(sep)
      context.join = (arr, sep) => Array.isArray(arr) ? arr.join(sep) : ''
      context.replace = (str, search, replace) => String(str).replace(search, replace)
      context.toLowerCase = (str) => String(str).toLowerCase()
      context.toUpperCase = (str) => String(str).toUpperCase()

      // Mathematical calculation helper functions
      context.sum = (arr) => Array.isArray(arr) ? arr.reduce((a, b) => a + b, 0) : 0
      context.avg = (arr) => Array.isArray(arr) && arr.length > 0 ? arr.reduce((a, b) => a + b, 0) / arr.length : 0
      context.max = (arr) => Array.isArray(arr) ? Math.max(...arr) : 0
      context.min = (arr) => Array.isArray(arr) ? Math.min(...arr) : 0
    }

    return context
  }

  /**
   * Convert result type
   */
  convertResultType(result, targetType) {
    try {
      switch (targetType) {
        case 'string':
          return String(result)
        case 'number':
          const num = Number(result)
          return isNaN(num) ? 0 : num
        case 'object':
          if (typeof result === 'object' && result !== null) {
            return result
          }
          return { value: result }
        case 'array':
          if (Array.isArray(result)) {
            return result
          }
          return [result]
        default:
          return result
      }
    } catch (error) {
      return result
    }
  }

  /**
   * Test tool connectivity
   */
  async testConnection() {
    try {
      // Execute a simple test code
      const testCode = '2 + 2'
      const result = await this.executeInSandbox(testCode, {
        timeout: 1000,
        includeHelpers: true,
        returnType: 'auto'
      })

      if (result.value === 4) {
        return {
          status: 'success',
          message: 'Code execution tool is working properly',
          details: {
            testCode,
            result: result.value,
            executionTime: result.executionTime
          }
        }
      } else {
        return {
          status: 'error',
          message: 'Code execution result is incorrect',
          details: { expected: 4, actual: result.value }
        }
      }
    } catch (error) {
      return {
        status: 'error',
        message: `Code execution tool test failed: ${error.message}`,
        details: { error: error.message }
      }
    }
  }

  /**
   * Get tool status information
   */
  getStatus() {
    return {
      name: this.name,
      enabled: this.enabled,
      category: this.category,
      version: this.version,
      description: this.description,
      maxCodeLength: this.config.maxCodeLength,
      defaultTimeout: 5000,
      supportedTypes: ['auto', 'string', 'number', 'object', 'array'],
      availableHelpers: this.config.allowedGlobals,
      lastUsed: this.lastUsed || null
    }
  }
}