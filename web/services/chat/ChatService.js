import { ReActEngine } from '@/services/chat/ReActEngine.js'
import { PromptTemplates } from '@/services/config/defaultPrompts.js'
import { ModelUtils, DEFAULT_MODEL_CONFIG, MODEL_CACHE_KEYS } from '@/services/config/modelConfigs.js'
import mcpClientManager from '@/utils/mcpClient.js'
import systemToolsManager from '@/services/system-tools/index.js'
import toolResolutionService from '@/services/ToolResolutionService.js'
import { setCache, getCacheByKey } from '@/utils/storage.js'
import axios from 'axios'
import DebugLogger from '@/utils/DebugLogger.js'

/**
 * MCP Chat Service
 * Integrates ReAct engine, MCP tool calls and model reasoning
 */
export class ChatService {
  constructor(options = {}) {
    // Basic configuration
    this.sessionId = options.sessionId || `chat_${Date.now()}`
    this.debugMode = options.debugMode || false
    this.enableReAct = options.enableReAct !== false // Enable ReAct by default

    // Model configuration
    this.modelConfig = { ...DEFAULT_MODEL_CONFIG, ...(options.modelConfig || {}) }
    this.customPrompts = options.customPrompts || {}

    // MCP related
    this.availableTools = [] // MCP tools
    this.enabledSessions = []
    this.mcpClient = mcpClientManager

    // System tools related
    this.systemToolsManager = systemToolsManager
    this.systemTools = [] // System tool definitions

    // ReAct engine
    this.reactEngine = null
    this.initializeReActEngine()

    // Conversation state
    this.conversationHistory = []
    this.isProcessing = false
    this.lastResponseTime = null

    // Interrupt control
    this.abortController = null
    this.shouldStop = false

    // Statistics
    this.stats = {
      totalMessages: 0,
      totalTokensUsed: 0,
      totalCost: 0,
      toolCallsCount: 0,
      averageResponseTime: 0
    }

    // Event callbacks
    this.onMessage = options.onMessage || null
    this.onToolCall = options.onToolCall || null
    this.onError = options.onError || null
    this.onProgress = options.onProgress || null
    this.onStreamChunk = options.onStreamChunk || null // Streaming data chunk callback
    this.onReasoningUpdate = options.onReasoningUpdate || null // Reasoning process update callback
    this.onToolConfirmationRequest = options.onToolConfirmationRequest || null // Tool confirmation request callback

    // Listen to system tools state changes
    this.systemToolsStateChangeListener = this.handleSystemToolsStateChange.bind(this)
    this.systemToolsManager.addStateChangeListener(this.systemToolsStateChangeListener)
  }

  /**
   * Initialize ReAct engine
   */
  initializeReActEngine() {
    if (!this.enableReAct) return

    // Refresh system tools list
    this.updateSystemTools()

    this.reactEngine = new ReActEngine({
      modelConfig: this.modelConfig,
      availableTools: this.availableTools, // MCP tools
      enabledSessions: this.enabledSessions,
      debugMode: this.debugMode,
      maxIterations: 5,
      chatService: this,  // Pass ChatService instance reference
      // Pass reasoning process callbacks
      onReasoningUpdate: (reasoning) => {
        if (this.onReasoningUpdate) {
          this.onReasoningUpdate(reasoning)
        }
      },
      onProgressUpdate: (progress) => {
        if (this.onProgress) {
          this.onProgress(progress)
        }
      },
      onToolConfirmationRequest: (data) => {
        if (this.onToolConfirmationRequest) {
          this.onToolConfirmationRequest(data)
        }
      }
    })
  }

  /**
   * Update system tools list
   */
  updateSystemTools() {
    try {
      this.systemTools = this.systemToolsManager.getToolDefinitions(true)
      this.log('[ChatService] 🔄 Update system tools list:', {
        systemToolsCount: this.systemTools.length,
        systemToolNames: this.systemTools.map(t => t.function.name),
        systemToolsDetail: this.systemTools.map(t => ({
          name: t.function.name,
          enabled: t.enabled,
          description: t.function.description?.substring(0, 50)
        }))
      })

      // If ReAct engine is initialized, update its system tools
      if (this.reactEngine) {
        this.reactEngine.initializeSystemTools()
        this.log('[ChatService] ✅ ReAct engine system tools updated')
      }
    } catch (error) {
      console.error('[ChatService] ❌ Failed to update system tools list:', error)
      this.systemTools = []
    }
  }

  /**
   * Handle system tools state changes
   */
  handleSystemToolsStateChange(changeEvent) {
    this.log('Received system tools state change notification:', changeEvent)

    try {
      // Update system tools list
      this.updateSystemTools()

      this.log('System tools state change processing completed', {
        changeType: changeEvent.type,
        enabledToolsCount: changeEvent.enabledTools?.length || 0,
        enabledToolNames: changeEvent.enabledTools?.map(t => t.name) || []
      })
    } catch (error) {
      console.error('[ChatService] ❌ Failed to handle system tools state change:', error)
      this.log('Failed to handle system tools state change:', error)
    }
  }

  /**
   * Send message and get response
   */
  async sendMessage(message, options = {}) {
    if (this.isProcessing) {
      throw new Error('Processing previous message, please wait')
    }

    this.isProcessing = true
    this.shouldStop = false
    this.abortController = new AbortController()
    const startTime = Date.now()

    try {
      this.log('Start processing user message:', message)

      // Check if need to stop
      if (this.shouldStop) {
        throw new Error('User manually stopped the processing')
      }

      // Add user message to history
      const userMessage = {
        role: 'user',
        content: message,
        timestamp: Date.now(),
        id: `msg_${Date.now()}`
      }

      this.conversationHistory.push(userMessage)
      this.notifyProgress('Start processing message...')

      // Choose processing method based on configuration
      const totalToolsCount = this.availableTools.length + (this.systemTools?.length || 0)
      
      let response
      if (this.enableReAct && totalToolsCount > 0) {
        response = await this.processWithReAct(message, options)
      } else {
        response = await this.processWithDirectModel(message, options)
      }

      // Calculate total conversation duration
      const totalDuration = Date.now() - startTime

      // Add assistant response to history
      const assistantMessage = {
        role: 'assistant',
        content: response.content,
        timestamp: Date.now(),
        id: `msg_${Date.now()}`,
        toolCalls: response.toolCalls || [],
        reasoning: response.reasoning ? {
          ...response.reasoning,
          duration: totalDuration // Use total conversation duration
        } : null,
        reasoningContent: response.reasoningContent || null, // Add reasoning content field
        cost: response.cost || null,
        totalDuration: totalDuration // Save total duration separately
      }

      this.conversationHistory.push(assistantMessage)

      // Update statistics
      this.updateStats(startTime, response)

      // Save conversation history
      this.saveConversationHistory()

      // Trigger callback
      if (this.onMessage) {
        this.onMessage(assistantMessage)
      }

      // Clear progress state
      this.notifyProgress('')

      this.log('Message processing completed')
      return assistantMessage

    } catch (error) {
      this.log('Error occurred while processing message:', error)

      // Calculate total duration when error occurs
      const errorDuration = Date.now() - startTime

      // Check if it's user-initiated stop
      const isUserStop = error.message.includes('User manually stopped the processing')

      let errorMessage
      if (isUserStop) {
        // User-initiated stop - create friendly stop message
        errorMessage = {
          role: 'assistant',
          content: 'You have manually stopped the AI processing. You can resend a message to continue the conversation if needed.',
          timestamp: Date.now(),
          id: `msg_${Date.now()}`,
          error: false, // Don't mark as error since this is expected user behavior
          toolCalls: [],
          reasoning: {
            final: true,
            iterations: this.reactEngine?.currentIteration || 0,
            stopped: true,
            content: `User manually stopped processing during reasoning. Total iterations: ${this.reactEngine?.currentIteration || 0}.`
          },
          reasoningContent: `⏹️ **Processing Stopped** \nUser manually stopped the AI reasoning process.`,
          cost: null,
          totalDuration: errorDuration,
          stopped: true // Add stop identifier
        }

        this.log('✅ User stop - created friendly stop message')
      } else {
        // Other errors - create error message
        errorMessage = {
          role: 'assistant',
          content: `Sorry, an error occurred while processing your message: ${error.message}`,
          timestamp: Date.now(),
          id: `msg_${Date.now()}`,
          error: true,
          toolCalls: [],
          reasoning: null,
          reasoningContent: null,
          cost: null,
          totalDuration: errorDuration
        }

        // Only non-user-stop errors trigger error callback
        if (this.onError) {
          this.onError(error)
        }
      }

      this.conversationHistory.push(errorMessage)
      return errorMessage

    } finally {
      this.isProcessing = false
      this.shouldStop = false
      this.abortController = null
      this.lastResponseTime = Date.now()
    }
  }

  /**
   * Stop current processing
   */
  stopProcessing() {
    this.log('User requested to stop processing')
    this.shouldStop = true

    // Immediately notify progress update to maintain UI continuity
    this.notifyProgress('Stopping processing, please wait...')

    // Abort HTTP requests
    if (this.abortController) {
      this.abortController.abort()
    }

    // Stop ReAct engine
    if (this.reactEngine) {
      this.reactEngine.stop()
    }

    // Give reasoning process some time to handle stop signal and return friendly message
    // Don't immediately clear isProcessing state, let existing error handling flow complete
    this.log('Stop signal sent, waiting for processing to complete...')

    // Set a safe timeout mechanism in case stop process gets stuck
    setTimeout(() => {
      if (this.isProcessing && this.shouldStop) {
        this.log('⚠️ Stop timeout, force clearing state')
        this.isProcessing = false
        this.shouldStop = false
        this.abortController = null
        this.notifyProgress('')

        // Add a stop timeout message to history
        const timeoutMessage = {
          role: 'assistant',
          content: 'Processing has been force stopped. You can resend a message to continue the conversation if needed.',
          timestamp: Date.now(),
          id: `msg_${Date.now()}`,
          error: false,
          toolCalls: [],
          reasoning: null,
          reasoningContent: null,
          cost: null,
          totalDuration: 0,
          stopped: true
        }

        this.conversationHistory.push(timeoutMessage)

        // Trigger callback
        if (this.onMessage) {
          this.onMessage(timeoutMessage)
        }
      }
    }, 3000) // 3 second timeout
  }

  /**
   * Process message using ReAct engine
   */
  async processWithReAct(message, options = {}) {
    this.notifyProgress('Starting ReAct reasoning engine...')

    // Build more complete context including conversation history
    const context = {
      conversationHistory: this.conversationHistory, // Pass complete history, let ReAct engine manage token truncation internally
      ...options.context
    }

    this.log('🔄 ReAct processing context:', {
      conversationHistoryLength: this.conversationHistory.length,
      availableToolsCount: this.availableTools.length,
      enabledSessionsCount: this.enabledSessions.length
    })

    // Check if need to stop
    if (this.shouldStop) {
      throw new Error('User manually stopped the processing')
    }

    const result = await this.reactEngine.processUserMessage(message, context)

    // Check again if need to stop
    if (this.shouldStop) {
      throw new Error('User manually stopped the processing')
    }

    if (!result.success) {
      throw new Error(`ReAct processing failed: ${result.error}`)
    }

    this.log('result ->>>>>> ', result)

    // Get raw response content for parsing
    // Prioritize thought as it contains complete structured response; answer is extracted short answer
    const rawResponse = result.result.thought || result.result.answer || 'Unable to generate response'
    this.log('ReAct result structure:', {
      hasAnswer: !!result.result.answer,
      hasThought: !!result.result.thought,
      answerLength: result.result.answer?.length || 0,
      thoughtLength: result.result.thought?.length || 0,
      final: result.result.final
    })
    this.log('ReAct raw response (using thought field):', rawResponse.substring(0, 500) + '...')

    // Parse response content, separate reasoning process and final answer
    const parsedResponse = this.parseStructuredResponse(rawResponse)

    // If parsed reasoning content is empty, try to build reasoning process from ReAct trace
    let reasoningContent = parsedResponse.reasoning

    if (!reasoningContent && result.trace && result.trace.length > 0) {
      // Build reasoning process description from ReAct trace
      const traceContent = result.trace.map(step => {
        switch (step.type) {
          case 'thought':
            return `🤔 **Thinking**: ${step.content}`
          case 'action_plan':
            return `🛠️ **Action Plan**: ${JSON.stringify(step.content, null, 2)}`
          case 'action_result':
            return `📊 **Action Result**: ${this.formatActionResult(step.content)}`
          case 'observation':
            return `👀 **Observation**: ${step.content}`
          case 'reasoning':
            return `💭 **Reasoning**: ${step.content}`
          default:
            return `📝 **${step.type}**: ${step.content}`
        }
      }).join('\n\n')

      reasoningContent = `ReAct Reasoning Process (${result.iterations} iterations):\n\n${traceContent}`
      this.log('Reasoning content built from trace:', reasoningContent.substring(0, 300) + '...')
    }

    // Process tool call history - Note: ReAct engine has already processed tool calls, just format records here
    const formattedToolCalls = result.toolCalls ? result.toolCalls.map(call => ({
      id: call.id || `tool_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      toolName: call.toolName,
      parameters: call.parameters,
      result: call.result,
      sessionId: call.sessionId,
      serverType: call.serverType,
      duration: call.duration,
      success: call.success,
      error: call.error
    })) : []

    this.log('ReAct tool call history:', {
      toolCallsCount: formattedToolCalls.length,
      systemToolCalls: formattedToolCalls.filter(call => call.serverType === 'system').length,
      mcpToolCalls: formattedToolCalls.filter(call => call.serverType === 'mcp').length
    })

    // Trigger tool call callbacks (notify UI updates)
    formattedToolCalls.forEach(call => {
      if (this.onToolCall) {
        this.onToolCall(call)
      }
    })

    const response = {
      content: parsedResponse.finalAnswer, // Only show final answer
      reasoningContent: reasoningContent, // Reasoning process content
      toolCalls: formattedToolCalls, // Formatted tool call records
      reasoning: {
        trace: result.trace,
        iterations: result.iterations,
        final: result.result.final,
        content: reasoningContent // Add reasoning process content
      },
      reactEnabled: true
    }

    this.log('ReAct processing completed:', {
      hasReasoning: !!response.reasoningContent,
      hasAnswer: !!response.content,
      reasoningLength: response.reasoningContent?.length || 0,
      answerLength: response.content?.length || 0,
      iterations: result.iterations,
      toolCallsCount: response.toolCalls.length
    })

    // Estimate cost
    if (this.modelConfig.provider && this.modelConfig.modelId) {
      const inputTokens = this.estimateTokens(message)
      const outputTokens = this.estimateTokens(response.content + (response.reasoningContent || ''))
      response.cost = ModelUtils.estimateCost(this.modelConfig, inputTokens, outputTokens)
    }

    return response
  }

  /**
   * Format action result
   */
  formatActionResult(actionResult) {
    if (!actionResult) return 'No result'

    if (typeof actionResult === 'string') {
      return actionResult
    }

    if (actionResult.type === 'tool_call') {
      const typeInfo = actionResult.serverType ? `(${actionResult.serverType.toUpperCase()})` : ''
      if (actionResult.success) {
        let resultText = `Tool ${actionResult.toolName} ${typeInfo} executed successfully`
        if (actionResult.duration) {
          resultText += `, took ${actionResult.duration}ms`
        }
        if (actionResult.result) {
          const resultData = typeof actionResult.result === 'string'
            ? actionResult.result
            : JSON.stringify(actionResult.result, null, 2)
          resultText += `\nReturn result: ${resultData}`
        }
        return resultText
      } else {
        return `Tool ${actionResult.toolName} ${typeInfo} execution failed: ${actionResult.error || 'Unknown error'}`
      }
    }

    if (actionResult.type === 'multi_tool_call') {
      const { totalTools, successCount, failureCount, results, duration } = actionResult
      let resultText = `Multi-tool call completed (Total: ${totalTools}, Success: ${successCount}, Failed: ${failureCount}`
      if (duration) {
        resultText += `, took ${duration}ms`
      }
      resultText += ')\n\n'

      results.forEach((result, index) => {
        const typeInfo = result.result?.serverType ? `(${result.result.serverType.toUpperCase()})` : ''
        resultText += `${index + 1}. ${result.toolName} ${typeInfo}: `
        if (result.success) {
          resultText += '✅ Success'
          if (result.result?.result) {
            const data = typeof result.result.result === 'string'
              ? result.result.result
              : JSON.stringify(result.result.result, null, 2)
            resultText += `\n   Result: ${data}`
          }
        } else {
          resultText += `❌ Failed: ${result.error || 'Unknown error'}`
        }
        resultText += '\n'
      })

      return resultText
    }

    return JSON.stringify(actionResult, null, 2)
  }

  /**
   * Process message by directly calling model
   */
  async processWithDirectModel(message, options = {}) {
    this.notifyProgress('Calling language model...')

    // If reasoning process callback is enabled, provide simple reasoning process feedback
    if (this.onReasoningUpdate) {
      this.onReasoningUpdate('🧠 **Direct Model Call** \nAnalyzing user request and generating response...')
    }

    // Build system prompt
    const systemPrompt = this.buildSystemPrompt()

    // Use intelligent context selection strategy
    const relevantHistory = this.selectIntelligentContext(this.conversationHistory, message)

    // Build message array
    const messages = [
      { role: 'system', content: systemPrompt },
      ...relevantHistory,
      { role: 'user', content: message }
    ]

    // Check if need to stop
    if (this.shouldStop) {
      throw new Error('User manually stopped the processing')
    }

    // Call model (enable streaming)
    const modelResponse = await this.callLanguageModel(messages, {
      stream: options.stream !== false, // Enable streaming by default
      signal: this.abortController?.signal, // Pass abort signal
      ...options
    })

    // Check again if need to stop
    if (this.shouldStop) {
      throw new Error('User manually stopped the processing')
    }

    // Parse structured response, separate reasoning process and final answer
    const parsedResponse = modelResponse.reasoningContent
      ? { reasoning: modelResponse.reasoningContent, finalAnswer: modelResponse.content }
      : this.parseStructuredResponse(modelResponse.content)

    // If there's reasoning content, notify update
    if (parsedResponse.reasoning && this.onReasoningUpdate) {
      this.onReasoningUpdate(`💭 **Model Reasoning Process** \n${parsedResponse.reasoning}`)
    }

    return {
      content: parsedResponse.finalAnswer,
      reasoningContent: parsedResponse.reasoning,
      toolCalls: modelResponse.toolCalls || [],
      cost: modelResponse.cost,
      reasoning: parsedResponse.reasoning ? {
        content: parsedResponse.reasoning,
        final: true,
        iterations: 0 // Non-ReAct mode iteration count is 0
      } : null,
      reactEnabled: false
    }
  }

  /**
   * Call language model
   */
  async callLanguageModel(messages, options = {}) {
    // If streaming is enabled and supported, use streaming call
    if (options.stream && this.supportsStreaming()) {
      return await this.callLanguageModelStream(messages, options)
    }

    // Otherwise use non-streaming call
    return await this.callLanguageModelNonStream(messages, options)
  }

  /**
   * Call language model and return raw response (without structured parsing)
   * Mainly used by ReAct engine to avoid duplicate parsing
   */
  async callLanguageModelRaw(messages, options = {}) {
    // Force use non-streaming call and return raw content
    const response = await this.callLanguageModelNonStream(messages, { ...options, stream: false })

    // Return raw content without structured parsing
    return {
      content: response.rawContent || response.content, // Use raw content
      toolCalls: response.toolCalls || [],
      cost: response.cost,
      usage: response.usage
    }
  }

  /**
   * Check if current model supports streaming calls
   */
  supportsStreaming() {
    // Most models currently support streaming calls
    const supportedProviders = ['openai', 'anthropic', 'azure', 'deepseek-chat', 'dashscope', 'ollama']
    return supportedProviders.includes(this.modelConfig.provider)
  }

  /**
   * Call language model with streaming
   */
  async callLanguageModelStream(messages, options = {}) {
    // Validate model configuration
    const validation = ModelUtils.validateConfig(this.modelConfig)
    if (!validation.valid) {
      throw new Error(`Invalid model configuration: ${validation.error}`)
    }

    const headers = ModelUtils.buildHeaders(this.modelConfig)
    const body = ModelUtils.buildRequestBody(this.modelConfig, messages, this.getToolSchemas())
    const url = ModelUtils.getRequestUrl(this.modelConfig)

    // Enable streaming
    body.stream = true

    if (!url) {
      throw new Error(`Unable to build request URL, please check configuration`)
    }

    this.log('Calling streaming model API:', {
      provider: this.modelConfig.provider,
      model: this.modelConfig.modelId,
      url,
      messagesCount: messages.length,
      headers: this.debugMode ? headers : '(hidden in non-debug mode)' // Show headers in debug mode
    })

    // Check if in browser environment, if so, use Fetch API
    if (typeof window !== 'undefined' && window.fetch) {
      return this.callLanguageModelStreamFetch(url, headers, body, options)
    }

    // Node.js environment streaming processing
    return new Promise((resolve, reject) => {
      let fullContent = ''
      let toolCalls = []
      let usage = null

      const axiosSource = axios.CancelToken.source()

      // Listen to external abort signal
      if (options.signal) {
        options.signal.addEventListener('abort', () => {
          axiosSource.cancel('User cancelled the request')
        })
      }

      axios({
        url,
        method: 'POST',
        headers: {
          ...headers,
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache'
        },
        data: body,
        responseType: 'stream',
        timeout: 60000,
        cancelToken: axiosSource.token
      }).then(response => {
        // Check if response.data has on method (Node.js stream)
        if (!response.data || typeof response.data.on !== 'function') {
          this.log('Response data is not a stream object, fallback to non-streaming call')
          // Fallback to non-streaming call
          this.callLanguageModelNonStream(messages, options)
            .then(resolve)
            .catch(reject)
          return
        }

        response.data.on('data', chunk => {
          const lines = chunk.toString().split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim()

              if (data === '[DONE]') {
                // Streaming ended
                const parsedResponse = this.parseStructuredResponse(fullContent)
                resolve({
                  content: parsedResponse.finalAnswer,
                  reasoningContent: parsedResponse.reasoning,
                  toolCalls,
                  usage,
                  cost: usage ? ModelUtils.estimateCost(
                    this.modelConfig,
                    usage.prompt_tokens || 0,
                    usage.completion_tokens || 0
                  ) : null
                })
                return
              }

              try {
                const jsonData = JSON.parse(data)
                let deltaContent = ''

                // Parse streaming data according to different providers
                if (this.modelConfig.provider === 'anthropic') {
                  // Anthropic streaming format
                  if (jsonData.type === 'content_block_delta') {
                    deltaContent = jsonData.delta?.text || ''
                  }
                } else if (this.modelConfig.provider === 'ollama') {
                  // Ollama streaming format
                  deltaContent = jsonData.response || ''
                  if (jsonData.done) {
                    usage = {
                      prompt_tokens: jsonData.prompt_eval_count,
                      completion_tokens: jsonData.eval_count
                    }
                  }
                } else {
                  // OpenAI compatible format
                  if (jsonData.choices && jsonData.choices[0]) {
                    const choice = jsonData.choices[0]
                    deltaContent = choice.delta?.content || ''

                    // Handle tool calls
                    if (choice.delta?.tool_calls) {
                      // Tool call processing logic
                    }
                  }

                  if (jsonData.usage) {
                    usage = jsonData.usage
                  }
                }

                if (deltaContent) {
                  fullContent += deltaContent

                  // Real-time parsing of reasoning process and final answer
                  this.parseStreamingContent(fullContent, {
                    onReasoningUpdate: (reasoning) => {
                      if (this.onReasoningUpdate) {
                        this.onReasoningUpdate(reasoning)
                      }
                    },
                    onStreamChunk: (chunk) => {
                      if (this.onStreamChunk) {
                        this.onStreamChunk(chunk)
                      }
                    }
                  })
                }

              } catch (e) {
                // Ignore JSON parsing errors, continue processing
              }
            }
          }
        })

        response.data.on('error', (error) => {
          this.log('Streaming call error:', error)
          reject(new Error(`Streaming call failed: ${error.message}`))
        })

        response.data.on('end', () => {
          // If [DONE] signal not received, manually end
          if (fullContent) {
            const parsedResponse = this.parseStructuredResponse(fullContent)
            resolve({
              content: parsedResponse.finalAnswer,
              reasoningContent: parsedResponse.reasoning,
              toolCalls,
              usage,
              cost: usage ? ModelUtils.estimateCost(
                this.modelConfig,
                usage.prompt_tokens || 0,
                usage.completion_tokens || 0
              ) : null
            })
          }
        })

      }).catch(error => {
        this.log('Streaming call failed:', error)

        // If streaming call fails, fallback to non-streaming call
        if (error.message.includes('response.data.on is not a function')) {
          this.log('Detected browser environment, fallback to non-streaming call')
          this.callLanguageModelNonStream(messages, options)
            .then(resolve)
            .catch(reject)
          return
        }

        let errorMessage = error.message
        if (error.response) {
          errorMessage = `HTTP ${error.response.status}: ${error.response.statusText}`
        }

        reject(new Error(`Streaming call failed: ${errorMessage}`))
      })
    })
  }

  /**
   * Browser environment streaming call (using Fetch API)
   */
  async callLanguageModelStreamFetch(url, headers, body, options = {}) {
    this.log('Using Fetch API for streaming call')

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          ...headers,
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache'
        },
        body: JSON.stringify(body),
        signal: options.signal // Pass abort signal
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      let fullContent = ''
      let toolCalls = []
      let usage = null

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          break
        }

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()

            if (data === '[DONE]') {
              // Streaming ended
              const parsedResponse = this.parseStructuredResponse(fullContent)
              return {
                content: parsedResponse.finalAnswer,
                reasoningContent: parsedResponse.reasoning,
                toolCalls,
                usage,
                cost: usage ? ModelUtils.estimateCost(
                  this.modelConfig,
                  usage.prompt_tokens || 0,
                  usage.completion_tokens || 0
                ) : null
              }
            }

            try {
              const jsonData = JSON.parse(data)
              let deltaContent = ''

              // Parse streaming data according to different providers
              if (this.modelConfig.provider === 'anthropic') {
                // Anthropic streaming format
                if (jsonData.type === 'content_block_delta') {
                  deltaContent = jsonData.delta?.text || ''
                }
              } else if (this.modelConfig.provider === 'ollama') {
                // Ollama streaming format
                deltaContent = jsonData.response || ''
                if (jsonData.done) {
                  usage = {
                    prompt_tokens: jsonData.prompt_eval_count,
                    completion_tokens: jsonData.eval_count
                  }
                }
              } else {
                // OpenAI compatible format
                if (jsonData.choices && jsonData.choices[0]) {
                  const choice = jsonData.choices[0]
                  deltaContent = choice.delta?.content || ''
                }

                if (jsonData.usage) {
                  usage = jsonData.usage
                }
              }

              if (deltaContent) {
                fullContent += deltaContent

                // Real-time parsing of reasoning process and final answer
                this.parseStreamingContent(fullContent, {
                  onReasoningUpdate: (reasoning) => {
                    if (this.onReasoningUpdate) {
                      this.onReasoningUpdate(reasoning)
                    }
                  },
                  onStreamChunk: (chunk) => {
                    if (this.onStreamChunk) {
                      this.onStreamChunk(chunk)
                    }
                  }
                })
              }

            } catch (e) {
              // Ignore JSON parsing errors, continue processing
            }
          }
        }
      }

      // If [DONE] signal not received, manually end
      const parsedResponse = this.parseStructuredResponse(fullContent)
      return {
        content: parsedResponse.finalAnswer,
        reasoningContent: parsedResponse.reasoning,
        toolCalls,
        usage,
        cost: usage ? ModelUtils.estimateCost(
          this.modelConfig,
          usage.prompt_tokens || 0,
          usage.completion_tokens || 0
        ) : null
      }

    } catch (error) {
      this.log('Fetch streaming call failed:', error)

      // Fallback to non-streaming call
      this.log('Fallback to non-streaming call')
      return this.callLanguageModelNonStream(messages, {})
    }
  }

  /**
   * Parse streaming content, extract reasoning process in real-time
   */
  parseStreamingContent(content, callbacks = {}) {
    // Check if contains reasoning block
    const reasoningMatch = content.match(/<REASONING>([\s\S]*?)(?:<\/REASONING>|$)/i)
    if (reasoningMatch && callbacks.onReasoningUpdate) {
      const reasoning = reasoningMatch[1].trim()
      callbacks.onReasoningUpdate(reasoning)
    }

    // Check if contains final answer
    const finalAnswerMatch = content.match(/<FINAL_ANSWER>([\s\S]*?)(?:<\/FINAL_ANSWER>|$)/i)
    if (finalAnswerMatch && callbacks.onStreamChunk) {
      const finalAnswer = finalAnswerMatch[1].trim()
      callbacks.onStreamChunk(finalAnswer)
    }
  }

  /**
   * Non-streaming call to language model
   */
  async callLanguageModelNonStream(messages, options = {}) {
    // Validate model configuration
    const validation = ModelUtils.validateConfig(this.modelConfig)
    if (!validation.valid) {
      throw new Error(`Invalid model configuration: ${validation.error}`)
    }

    const model = ModelUtils.getModelById(`${this.modelConfig.provider}:${this.modelConfig.modelId}`)
    if (!model) {
      throw new Error(`Invalid model configuration: ${this.modelConfig.provider}:${this.modelConfig.modelId}`)
    }

    // Build request
    const headers = ModelUtils.buildHeaders(this.modelConfig)
    const body = ModelUtils.buildRequestBody(this.modelConfig, messages, this.getToolSchemas())
    const url = ModelUtils.getRequestUrl(this.modelConfig)

    if (!url) {
      throw new Error(`Unable to build request URL, please check configuration`)
    }

    this.log('Calling model API:', {
      provider: this.modelConfig.provider,
      model: this.modelConfig.modelId,
      url,
      messagesCount: messages.length,
      headers: this.debugMode ? headers : '(hidden in non-debug mode)' // Show headers in debug mode
    })

    try {
      // Build request configuration
      const requestConfig = {
        url,
        method: 'POST',
        headers,
        data: body,
        timeout: 60000 // 60 second timeout
      }

      // If there's an abort signal, add cancellation support
      let cancelSource = null
      if (options.signal) {
        cancelSource = axios.CancelToken.source()
        requestConfig.cancelToken = cancelSource.token

        // Listen to abort signal
        options.signal.addEventListener('abort', () => {
          cancelSource.cancel('User cancelled the request')
        })
      }

      const axiosResponse = await axios(requestConfig)
      const response = axiosResponse.data // Extract response data

      this.log('Model API response:', {
        status: 'success',
        provider: this.modelConfig.provider,
        usage: response.usage,
        httpStatus: axiosResponse.status
      })

      // Parse response according to different providers
      let content = ''
      let toolCalls = []

      if (this.modelConfig.provider === 'anthropic') {
        // Anthropic Claude response format
        content = response.content?.[0]?.text || ''
        // Anthropic tool call handling (if supported)
        if (response.tool_calls) {
          toolCalls = await this.processToolCalls(response.tool_calls)
        }
      } else if (this.modelConfig.provider === 'ollama') {
        // Ollama response format
        content = response.response || response.message?.content || ''
      } else {
        // OpenAI compatible format (including Azure OpenAI, DeepSeek, DashScope, etc.)
        if (!response.choices || response.choices.length === 0) {
          throw new Error('Model returned invalid response format: no choices field')
        }

        const choice = response.choices[0]
        content = choice.message?.content || ''

        // Handle tool calls
        if (choice.message?.tool_calls) {
          toolCalls = await this.processToolCalls(choice.message.tool_calls)
        }
      }

      // Estimate cost
      let cost = null
      if (response.usage) {
        cost = ModelUtils.estimateCost(
          this.modelConfig,
          response.usage.prompt_tokens || 0,
          response.usage.completion_tokens || 0
        )
      }

      return {
        content,
        rawContent: content, // Save raw content
        toolCalls,
        cost,
        usage: response.usage
      }

    } catch (error) {
      this.log('Model call failed:', {
        provider: this.modelConfig.provider,
        model: this.modelConfig.modelId,
        error: error.message
      })

      // Provide more specific error information
      let errorMessage = error.message
      if (error.response) {
        // HTTP error
        errorMessage = `HTTP ${error.response.status}: ${error.response.statusText}`
        if (error.response.data) {
          const errorData = typeof error.response.data === 'string'
            ? error.response.data
            : JSON.stringify(error.response.data)
          errorMessage += ` - ${errorData}`
        }
      } else if (error.code === 'ECONNABORTED' || error.code === 'TIMEOUT') {
        errorMessage = 'Request timeout, please try again later'
      } else if (error.code === 'NETWORK_ERROR' || error.code === 'ERR_NETWORK') {
        errorMessage = 'Network connection failed, please check network settings and API address'
      } else if (axios.isCancel(error)) {
        errorMessage = 'Request has been cancelled'
      }
      
      throw new Error(`Model call failed: ${errorMessage}`)
    }
  }

  /**
   * Process tool calls
   */
  async processToolCalls(toolCalls) {
    const results = []
    
    for (const toolCall of toolCalls) {
      try {
        this.notifyProgress(`Calling tool: ${toolCall.function.name}`)
        
        const toolName = toolCall.function.name
        const parameters = JSON.parse(toolCall.function.arguments || '{}')
        
        // Check if it's a system tool
        const systemTool = this.systemTools.find(tool => tool.function.name === toolName)
        
        let result
        let sessionId
        let serverType
        const startTime = Date.now()
        
        if (systemTool) {
          // Execute system tool call
          this.log('Calling system tool:', toolName)
          result = await this.systemToolsManager.callTool(toolName, parameters, {
            startTime,
            sessionId: 'system_tools',
            chatService: this
          })
          sessionId = 'system'
          serverType = 'system'
        } else {
          // Execute MCP tool call
          sessionId = this.findToolSession(toolName)
          if (!sessionId) {
            throw new Error(`Cannot find session for tool ${toolName}`)
          }
          
          this.log('Calling MCP tool:', toolName)
          result = await this.mcpClient.callTool(sessionId, toolName, parameters)
          serverType = 'mcp'
        }
        
        const endTime = Date.now()
        
        const toolCallResult = {
          id: toolCall.id,
          toolName,
          parameters,
          result: systemTool ? (result.data || result) : result, // System tool return format adaptation
          sessionId,
          serverType,
          duration: endTime - startTime,
          success: systemTool ? result.success !== false : true, // System tools have explicit success flag
          error: systemTool ? result.error : null,
          timestamp: endTime
        }
        
        results.push(toolCallResult)
        
        // Update statistics
        this.stats.toolCallsCount++
        
        // Trigger tool call callback
        if (this.onToolCall) {
          this.onToolCall(toolCallResult)
        }
        
      } catch (error) {
        this.log('Tool call failed:', error)
        
        const toolCallResult = {
          id: toolCall.id,
          toolName: toolCall.function.name,
          parameters: JSON.parse(toolCall.function.arguments || '{}'),
          error: error.message,
          success: false,
          serverType: 'unknown',
          duration: 0,
          timestamp: Date.now()
        }
        
        results.push(toolCallResult)
      }
    }
    
    return results
  }

  /**
   * Parse structured response, separate reasoning process and final answer
   */
  parseStructuredResponse(responseText) {
    this.log('Start parsing structured response (full content):', responseText)
    
    // Check if contains tags
    const hasReasoningTag = responseText.includes('<REASONING>')
    const hasFinalAnswerTag = responseText.includes('<FINAL_ANSWER>')
    this.log('Tag check:', { hasReasoningTag, hasFinalAnswerTag })
    
    // Try to parse <REASONING> and <FINAL_ANSWER> tags
    // Prioritize matching closed tags
    let reasoningMatch = responseText.match(/<REASONING>([\s\S]*?)<\/REASONING>/i)
    let finalAnswerMatch = responseText.match(/<FINAL_ANSWER>([\s\S]*?)<\/FINAL_ANSWER>/i)
    
    // If no closed tags, try to match unclosed tags (fallback handling)
    if (!reasoningMatch && hasReasoningTag) {
      reasoningMatch = responseText.match(/<REASONING>([\s\S]*?)(?=<\/|$)/i)
      this.log('Using fallback matching for reasoning tag (unclosed)')
    }
    
    if (!finalAnswerMatch && hasFinalAnswerTag) {
      finalAnswerMatch = responseText.match(/<FINAL_ANSWER>([\s\S]*?)(?=<\/|$)/i)
      this.log('Using fallback matching for final answer tag (unclosed)')
    }
    
    this.log('Regex matching results:', {
      responseText: responseText.substring(0, 200) + '...',
      reasoningMatch: reasoningMatch ? 'matched' : 'no match',
      finalAnswerMatch: finalAnswerMatch ? 'matched' : 'no match',
      hasReasoningTag,
      hasFinalAnswerTag
    })
    
    let reasoning = ''
    let finalAnswer = ''
    
    if (reasoningMatch) {
      reasoning = reasoningMatch[1].trim()
      this.log('Parsed reasoning process from tags:', reasoning.substring(0, 200) + '...')
    }
    
    if (finalAnswerMatch) {
      finalAnswer = finalAnswerMatch[1].trim()
      this.log('Parsed final answer from tags:', finalAnswer.substring(0, 200) + '...')
    }
    
    // If no tags found, try other separation methods
    if (!reasoning && !finalAnswer) {
      this.log('No standard tags found, trying other separation methods')
      
      // Find common separators (support both Chinese and English)
      const sections = responseText.split(/(?=🤔|🛠️|📊|💭|💡|结论|答案|总结|conclusion|answer|summary)/i)
      
      if (sections.length > 1) {
        // Assume the last part is the final answer
        finalAnswer = sections[sections.length - 1].trim()
        reasoning = sections.slice(0, -1).join('\n').trim()
        this.log('Successfully separated by separators:', { 
          sectionsCount: sections.length,
          reasoning: reasoning.substring(0, 100) + '...',
          finalAnswer: finalAnswer.substring(0, 100) + '...'
        })
      } else {
        // If cannot separate, use entire content as final answer, but try to generate simple reasoning process
        finalAnswer = responseText.trim()
        reasoning = 'After 1 reasoning iteration, I have processed your request.'
        this.log('Cannot separate content, using entire response as final answer')
      }
    }
    
    // Clean up extra markers in reasoning process
    if (reasoning) {
      reasoning = reasoning
        .replace(/<\/?REASONING>/gi, '')
        .replace(/^\s*[\r\n]+|[\r\n]+\s*$/g, '') // Remove leading and trailing empty lines
        .trim()
    }
    
    // Clean up extra markers in final answer
    if (finalAnswer) {
      finalAnswer = finalAnswer
        .replace(/<\/?FINAL_ANSWER>/gi, '')
        .replace(/^\s*[\r\n]+|[\r\n]+\s*$/g, '') // Remove leading and trailing empty lines
        .trim()
    }
    
    // If final answer is empty, use default prompt
    if (!finalAnswer) {
      finalAnswer = 'Sorry, I cannot provide you with a clear answer.'
    }
    
    const result = {
      reasoning: reasoning || null,
      finalAnswer: finalAnswer
    }
    
    this.log('Structured response parsing completed:', {
      hasReasoning: !!result.reasoning,
      hasAnswer: !!result.finalAnswer,
      reasoningLength: result.reasoning?.length || 0,
      answerLength: result.finalAnswer?.length || 0
    })
    
    return result
  }

  /**
   * Build system prompt
   */
  buildSystemPrompt() {
    // Refresh system tools list
    this.updateSystemTools()
    
    this.log('[ChatService] 🔨 Building system prompt, current system tools status:', {
      systemToolsCount: this.systemTools.length,
      mcpToolsCount: this.availableTools.length,
      systemTools: this.systemTools.map(t => ({
        name: t.function.name,
        enabled: t.enabled,
        description: t.function.description?.substring(0, 50) + '...'
      }))
    })

    // Prioritize using custom ReAct system prompt
    if (this.customPrompts && this.customPrompts.reactSystemPrompt) {
      // If user customized ReAct system prompt, use it and fill in tool list
      const systemToolsList = this.systemTools.map(t => `- ${t.function.name}: ${t.function.description || 'No description'}`).join('\n')
      const mcpToolsList = this.availableTools.map(t => `- ${t.name}: ${t.description || 'No description'}`).join('\n')

      this.log('[ChatService] 🔨 System tools debug info:', {
        systemToolsArray: this.systemTools,
        systemToolsCount: this.systemTools.length,
        systemToolsList: systemToolsList,
        systemToolsListLength: systemToolsList.length,
        isEmpty: systemToolsList === '',
        finalValue: systemToolsList || 'No system tools available'
      })

      return PromptTemplates.fillTemplate(this.customPrompts.reactSystemPrompt, {
        systemTools: systemToolsList || 'No system tools available',
        mcpTools: mcpToolsList || 'No MCP tools available'
      })
    }
    
    // Use default ReAct system prompt (supports system tools and MCP tools separation)
    this.log('[ChatService] ✅ Using default system prompt, enabled system tools count:', this.systemTools.length)
    return PromptTemplates.buildReActSystemPrompt(this.availableTools, this.systemTools)
  }

  /**
   * Get tool schema definitions
   */
  getToolSchemas() {
    // Merge system tools and MCP tools definitions
    const systemToolSchemas = this.systemTools.map(tool => ({
      type: 'function',
      function: {
        name: tool.function.name,
        description: tool.function.description || '',
        parameters: tool.function.parameters || {
          type: 'object',
          properties: {},
          required: []
        }
      },
      toolType: 'system'
    }))

    const mcpToolSchemas = this.availableTools.map(tool => ({
      type: 'function',
      function: {
        name: tool.name,
        description: tool.description || '',
        parameters: tool.inputSchema || {
          type: 'object',
          properties: {},
          required: []
        }
      },
      toolType: 'mcp'
    }))

    return [...systemToolSchemas, ...mcpToolSchemas]
  }

  /**
   * Find session corresponding to tool
   */
  findToolSession(toolName) {
    return toolResolutionService.findToolSession(
      toolName,
      this.systemTools,
      this.availableTools,
      this.enabledSessions
    )
  }

  /**
   * Get session ID corresponding to tool
   */
  getToolSessionId(tool) {
    return toolResolutionService.getToolSessionId(tool, this.enabledSessions)
  }

  /**
   * Get session name
   */
  getSessionName(sessionId) {
    return toolResolutionService.getSessionName(sessionId, this.enabledSessions)
  }

  /**
   * Get tool list for specified session
   */
  getSessionTools(sessionId) {
    return toolResolutionService.getSessionTools(sessionId, this.availableTools, this.enabledSessions)
  }

  /**
   * Update available tools
   */
  updateAvailableTools(tools, sessions = []) {
    this.availableTools = tools || [] // MCP tools
    this.enabledSessions = sessions || []
    
    // Also update system tools
    this.updateSystemTools()
    
    // Update ReAct engine
    if (this.reactEngine) {
      this.reactEngine.updateAvailableTools(this.availableTools)
      this.reactEngine.updateEnabledSessions(this.enabledSessions)
    } else {
      this.log('⚠️ ReAct engine does not exist, cannot update tool information')
    }
  }

  /**
   * Update model configuration
   */
  updateModelConfig(config) {
    this.modelConfig = { ...this.modelConfig, ...config }
    
    // If model ID is updated, automatically set corresponding context length (if not explicitly set)
    if (config.modelId && !config.maxContextTokens) {
      const contextLimit = ModelUtils.getModelContextLimit(config.modelId)
      // Reserve some space for output tokens
      this.modelConfig.maxContextTokens = Math.max(contextLimit - (this.modelConfig.maxTokens || 4000), 4000)
      
      this.log('🔧 Auto-set context length based on model:', {
        modelId: config.modelId,
        contextLimit: contextLimit,
        maxContextTokens: this.modelConfig.maxContextTokens
      })
    }
    
    // Re-initialize ReAct engine
    if (this.enableReAct) {
      this.initializeReActEngine()
    }
    
    // Save configuration
    setCache(MODEL_CACHE_KEYS.CONFIG, this.modelConfig)
  }

  /**
   * Update custom prompts
   */
  updateCustomPrompts(prompts) {
    this.customPrompts = { ...this.customPrompts, ...prompts }
    this.log('Update custom prompts:', prompts)
    
    // If ReAct engine is enabled, update its available tools list to refresh system prompt
    if (this.reactEngine) {
      this.reactEngine.availableTools = this.availableTools
      this.log('Tool list synchronized to ReAct engine, system prompt will be updated on next call')
    }
  }

  /**
   * Clear conversation history
   */
  clearHistory() {
    this.conversationHistory = []
    this.stats = {
      totalMessages: 0,
      totalTokensUsed: 0,
      totalCost: 0,
      toolCallsCount: 0,
      averageResponseTime: 0
    }
    
    // Clear ReAct engine session context
    if (this.reactEngine) {
      this.reactEngine.resetSessionContext()
      this.log('✅ ReAct engine session context has been reset')
    }
    
    // Clear cache
    setCache(`chat_history_${this.sessionId}`, [])
    
    this.log('Conversation history has been cleared')
  }

  /**
   * Get conversation history
   */
  getHistory() {
    return this.conversationHistory
  }

  /**
   * Get statistics
   */
  getStats() {
    const baseStats = { ...this.stats }
    
    // Add tool statistics
    baseStats.toolStats = {
      systemTools: this.systemTools.length,
      mcpTools: this.availableTools.length,
      totalTools: this.systemTools.length + this.availableTools.length,
      enabledSessions: this.enabledSessions.length
    }
    
    return baseStats
  }

  /**
   * Save conversation history
   */
  saveConversationHistory() {
    try {
      // Only save the most recent 50 messages
      const historyToSave = this.conversationHistory.slice(-50)
      setCache(`chat_history_${this.sessionId}`, historyToSave)
    } catch (error) {
      this.log('Failed to save conversation history:', error)
    }
  }

  /**
   * Load conversation history
   */
  loadConversationHistory() {
    try {
      const savedHistory = getCacheByKey(`chat_history_${this.sessionId}`)
      if (savedHistory && Array.isArray(savedHistory)) {
        this.conversationHistory = savedHistory
        this.log('Conversation history loaded successfully')
      }
    } catch (error) {
      this.log('Failed to load conversation history:', error)
    }
  }

  /**
   * Update statistics
   */
  updateStats(startTime, response) {
    this.stats.totalMessages++
    
    const responseTime = Date.now() - startTime
    this.stats.averageResponseTime = 
      (this.stats.averageResponseTime * (this.stats.totalMessages - 1) + responseTime) / this.stats.totalMessages
    
    if (response.cost) {
      this.stats.totalCost += response.cost.totalCost || 0
    }
    
    if (response.usage) {
      this.stats.totalTokensUsed += (response.usage.prompt_tokens || 0) + (response.usage.completion_tokens || 0)
    }
  }

  /**
   * Estimate token count (improved version)
   */
  estimateTokens(text) {
    if (!text) return 0
    
    // More accurate token estimation
    // Chinese: average 1.3 characters = 1 token
    // English: average 3.5 characters = 1 token  
    // JSON/code: average 2.5 characters = 1 token
    const chineseChars = (text.match(/[\u4e00-\u9fff]/g) || []).length
    const codeChars = (text.match(/[{}[\]"':,]/g) || []).length
    const otherChars = text.length - chineseChars - codeChars
    
    return Math.ceil(chineseChars / 1.3 + codeChars / 2.5 + otherChars / 3.5)
  }

  /**
   * Estimate total token count for message list
   */
  estimateMessagesTokens(messages) {
    let totalTokens = 0
    
    for (const message of messages) {
      // Message structure overhead (role, content and other fields)
      totalTokens += 4
      
      // role field
      totalTokens += this.estimateTokens(message.role)
      
      // content field
      if (typeof message.content === 'string') {
        totalTokens += this.estimateTokens(message.content)
      } else if (Array.isArray(message.content)) {
        // Multi-modal content
        for (const part of message.content) {
          if (part.type === 'text') {
            totalTokens += this.estimateTokens(part.text)
          }
          // Images and other types are not calculated for now
        }
      }
      
      // tool_calls field
      if (message.tool_calls) {
        totalTokens += this.estimateTokens(JSON.stringify(message.tool_calls))
      }
      
      // tool_call_id field
      if (message.tool_call_id) {
        totalTokens += this.estimateTokens(message.tool_call_id)
      }
    }
    
    // Additional formatting overhead
    totalTokens += messages.length * 2
    
    return totalTokens
  }

  /**
   * Intelligent context management - select most relevant historical information
   * Unified context selection strategy, applicable to direct model calls and ReAct engine
   */
  selectIntelligentContext(conversationHistory, currentMessage, maxContextTokens = null) {
    if (!conversationHistory || conversationHistory.length === 0) {
      return []
    }
    
    const contextLimit = maxContextTokens || this.modelConfig.maxContextTokens || 120000
    
    // Reserve space for system prompt and output
    const systemTokens = this.estimateTokens(this.buildSystemPrompt())
    const outputReserve = this.modelConfig.maxTokens || 8000
    const availableTokens = contextLimit - systemTokens - outputReserve - 500 // Extra reserve 500 tokens
    
    this.log('🧠 Intelligent context selection:', {
      totalHistory: conversationHistory.length,
      contextLimit,
      availableTokens,
      systemTokens,
      outputReserve
    })
    
    if (availableTokens <= 0) {
      this.log('⚠️ Insufficient available context space')
      return []
    }
    
    // Extract keywords for relevance calculation
    const keywords = this.extractKeywords(currentMessage)
    
    // Calculate comprehensive score for each historical message
    const scoredMessages = conversationHistory.map((msg, index) => {
      let score = 0
      
      // 1. Time decay score (0-20 points)
      const age = conversationHistory.length - index - 1
      score += Math.exp(-age / 8) * 20 // 8 messages half-life
      
      // 2. Keyword relevance score (0-25 points)
      if (msg.content && typeof msg.content === 'string') {
        for (const keyword of keywords) {
          if (msg.content.toLowerCase().includes(keyword.toLowerCase())) {
            score += 3 // Each keyword match gets 3 points
          }
        }
      }
      
      // 3. Message type importance score (0-15 points)
      if (msg.role === 'assistant') {
        if (msg.toolCalls && msg.toolCalls.length > 0) {
          score += 10 // Responses with tool calls are more important
        }
        if (msg.reasoning && msg.reasoning.content) {
          score += 8 // Responses with reasoning process are more important
        }
        if (msg.content && msg.content.includes('<FINAL_ANSWER>')) {
          score += 12 // Responses with final answers are very important
        }
      } else if (msg.role === 'user') {
        if (msg.content && msg.content.length > 50) {
          score += 5 // Longer user messages may contain more information
        }
      }
      
      // 4. Conversation coherence score (0-10 points)
      if (index > 0) {
        const prevMsg = conversationHistory[index - 1]
        if (prevMsg.role !== msg.role) {
          score += 6 // Conversation turn completeness
        }
      }
      
      // 5. Error message penalty (-5 points)
      if (msg.error) {
        score -= 5
      }
      
      return { ...msg, score, originalIndex: index }
    })
    
    // Sort by score and intelligently select
    const sortedMessages = scoredMessages.sort((a, b) => b.score - a.score)
    
    // Use greedy algorithm to select best combination
    const selectedMessages = []
    let currentTokens = 0
    
    // First ensure recent messages are included (guarantee conversation coherence)
    const recentCount = Math.min(4, conversationHistory.length) // Recent 4 messages
    const recentMessages = conversationHistory.slice(-recentCount)
    
    for (const msg of recentMessages) {
      const msgTokens = this.estimateMessagesTokens([msg])
      if (currentTokens + msgTokens <= availableTokens) {
        selectedMessages.push({ ...msg, reason: 'recent' })
        currentTokens += msgTokens
      }
    }
    
    // Then add other important messages based on score (avoid duplicates)
    const recentIndexes = new Set(recentMessages.map((_, i) => conversationHistory.length - recentCount + i))
    
    for (const msg of sortedMessages) {
      if (recentIndexes.has(msg.originalIndex)) {
        continue // Skip already selected recent messages
      }
      
      const msgTokens = this.estimateMessagesTokens([msg])
      if (currentTokens + msgTokens <= availableTokens && selectedMessages.length < 20) { // Maximum 20 messages
        selectedMessages.push({ ...msg, reason: 'relevant' })
        currentTokens += msgTokens
      }
    }
    
    // Re-sort by original time order
    const finalMessages = selectedMessages
      .sort((a, b) => a.originalIndex - b.originalIndex)
      .map(msg => ({
        role: msg.role,
        content: this.summarizeMessageContent(msg.content),
        timestamp: msg.timestamp,
        id: msg.id
      }))
    
    this.log('✅ Intelligent context selection completed:', {
      originalCount: conversationHistory.length,
      selectedCount: finalMessages.length,
      finalTokens: currentTokens,
      tokenUsage: `${Math.round((currentTokens / availableTokens) * 100)}%`
    })
    
    return finalMessages
  }

  /**
   * Backward compatible context truncation method
   * Actually calls the new intelligent context selection method
   */
  truncateMessagesForContext(messages, systemPrompt = '', maxContextTokens = null) {
    // Extract user messages from message list as current message
    const userMessages = messages.filter(msg => msg.role === 'user')
    const currentMessage = userMessages.length > 0 ? userMessages[userMessages.length - 1].content : ''
    
    // Extract conversation history from message list (exclude system messages and current user message)
    const conversationHistory = messages.filter(msg => 
      msg.role !== 'system' && 
      (msg.role !== 'user' || msg !== userMessages[userMessages.length - 1])
    )
    
    // Use new intelligent context selection method
    return this.selectIntelligentContext(conversationHistory, currentMessage, maxContextTokens)
  }

  /**
   * Extract keywords (optimized version - supports Chinese and English stop word filtering)
   */
  extractKeywords(text) {
    if (!text || typeof text !== 'string') return []
    
    // Chinese keyword extraction (improved: added Chinese stop word filtering)
    const chineseKeywords = (text.match(/[\u4e00-\u9fa5]{2,}/g) || [])
      .filter(word => !this.isChineseStopWord(word))
      .filter(word => word.length >= 2 && word.length <= 8) // Reasonable Chinese word length
    
    // English keyword extraction (extended stop word list)
    const englishKeywords = text.toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(word => word.length > 2 && !this.isEnglishStopWord(word))
    
    // Technical term recognition (extended technical term list)
    const techTerms = text.match(/\b(API|HTTP|HTTPS|JSON|XML|SQL|React|Vue|Angular|Node\.js|Python|JavaScript|TypeScript|Java|Go|Rust|Git|Docker|Kubernetes|AI|ML|DL|NLP|GPT|Claude|OpenAI|测试|部署|开发|代码|函数|方法|类|接口|数据库|服务器|客户端|前端|后端|全栈|微服务|容器|云原生|DevOps|CI\/CD)\b/gi) || []
    
    // Merge and deduplicate, prioritize technical terms
    const allKeywords = [
      ...techTerms.map(t => t.toLowerCase()),
      ...chineseKeywords,
      ...englishKeywords
    ]
    
    return [...new Set(allKeywords)].slice(0, 15) // Maximum 15 keywords
  }

  /**
   * Chinese stop word detection
   */
  isChineseStopWord(word) {
    const chineseStopWords = [
      // Common particles and modal words
      '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
      '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看',
      '好', '自己', '这', '那', '什么', '这个', '那个', '可以', '但是', '因为',
      '所以', '如果', '虽然', '然后', '或者', '而且', '不过', '比如', '就是',
      '已经', '还是', '只是', '应该', '可能', '肯定', '一直', '特别', '非常',
      '怎么', '为什么', '这样', '那样', '现在', '以前', '以后', '时候', '地方',
      // Quantifiers and time words
      '第一', '第二', '第三', '今天', '昨天', '明天', '每天', '一些', '很多',
      '一点', '一下', '一起', '一般', '通常', '经常', '总是', '从来'
    ]
    return chineseStopWords.includes(word)
  }

  /**
   * English stop word detection (extended version)
   */
  isEnglishStopWord(word) {
    const englishStopWords = [
      // Original basic stop words
      'the', 'is', 'at', 'which', 'on', 'and', 'or', 'but', 'in', 'with', 'to', 
      'for', 'of', 'as', 'by', 'that', 'this', 'it', 'from', 'they', 'we', 'you', 
      'have', 'had', 'will', 'would', 'could', 'should', 'what', 'when', 'where', 
      'how', 'why', 'can', 'may', 'might', 'must', 'shall', 'do', 'does', 'did', 
      'get', 'got', 'has', 'was', 'were', 'been', 'being', 'are', 'am',
      // Extended stop words
      'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
      'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
      'can', 'will', 'just', 'now', 'then', 'here', 'there', 'once', 'during',
      'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over',
      'under', 'again', 'further', 'into', 'through', 'between', 'about', 'against',
      'around', 'because', 'while', 'until', 'although', 'unless', 'since'
    ]
    return englishStopWords.includes(word.toLowerCase())
  }

  /**
   * Intelligent message content summarization (improved version)
   */
  summarizeMessageContent(content) {
    if (!content || typeof content !== 'string') return content
    
    // If content is not long, return directly
    if (content.length <= 300) return content
    
    // Preserve key parts of structured content
    const patterns = [
      { regex: /<FINAL_ANSWER>([\s\S]*?)<\/FINAL_ANSWER>/i, prefix: '[Final Answer] ' },
      { regex: /<REASONING>([\s\S]*?)<\/REASONING>/i, prefix: '[Reasoning Process] ' },
      { regex: /<ACTION>([\s\S]*?)<\/ACTION>/i, prefix: '[Action Plan] ' },
      { regex: /```[\s\S]*?```/g, prefix: '[Code Block] ' },
      { regex: /\|.*?\|/g, prefix: '[Table] ' }
    ]
    
    for (const pattern of patterns) {
      const match = content.match(pattern.regex)
      if (match) {
        const extracted = match[1] || match[0]
        if (extracted.length > 100) {
          return pattern.prefix + extracted.substring(0, 180) + '...'
        } else {
          return pattern.prefix + extracted
        }
      }
    }
    
    // If it's a tool call result, extract key information (support both Chinese and English)
    if ((content.includes('Tool') && (content.includes('success') || content.includes('executed'))) ||
        (content.includes('工具') && (content.includes('成功') || content.includes('执行')))) {
      const lines = content.split('\n')
      const important = lines.filter(line => 
        // English keywords
        line.includes('success') || 
        line.includes('result') || 
        line.includes('return') ||
        line.includes('data') ||
        // Chinese keywords
        line.includes('成功') || 
        line.includes('结果') || 
        line.includes('返回') ||
        line.includes('数据')
      ).slice(0, 3)
      
      if (important.length > 0) {
        return '[Tool Call] ' + important.join(' ') + (content.length > 300 ? '...' : '')
      }
    }
    
    // General summary: keep first 150 characters and last 100 characters
    return content.substring(0, 150) + '...[omitted]...' + content.substring(content.length - 100)
  }

  /**
   * Progress notification
   */
  notifyProgress(message) {
    this.log('Progress:', message)
    if (this.onProgress) {
      this.onProgress(message)
    }
  }

  /**
   * Log output
   */
  log(...args) {
    // Use unified debug logging system and maintain session ID prefix
    if (DebugLogger.isDebugEnabled()) {
      console.log(DebugLogger.formatPrefix('debug', `ChatService:${this.sessionId}`), ...args)
    }
  }

  /**
   * Destroy service
   */
  destroy() {
    this.isProcessing = false
    this.conversationHistory = []
    
    // Remove system tools state change listener
    if (this.systemToolsStateChangeListener) {
      this.systemToolsManager.removeStateChangeListener(this.systemToolsStateChangeListener)
      this.systemToolsStateChangeListener = null
    }
    
    this.reactEngine = null
    this.log('Chat service has been destroyed')
  }
}

// Default export
export default ChatService 