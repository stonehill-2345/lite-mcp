import {PromptTemplates} from '@/services/config/defaultPrompts.js'
import {REACT_MODEL_CONFIGS} from '@/services/config/modelConfigs.js'
import mcpClientManager from '@/utils/mcpClient.js'
import systemToolsManager from '@/services/system-tools/index.js'
import toolResolutionService from '@/services/ToolResolutionService.js'
import DebugLogger from '@/utils/DebugLogger.js'

/**
 * ReAct Reasoning Engine
 * Implements the Reasoning-Action-Observation loop, supporting multi-step reasoning and tool calls
 */
export class ReActEngine {
  constructor(options = {}) {
    this.modelConfig = options.modelConfig || {}
    this.availableTools = options.availableTools || [] // MCP tools
    this.maxIterations = options.maxIterations || 10
    this.enabledSessions = options.enabledSessions || []
    this.debugMode = options.debugMode || false
    this.timeout = options.timeout || 30000 // 30 second timeout
    
    // System tools management
    this.systemToolsManager = systemToolsManager
    this.systemTools = [] // System tools list, obtained from manager during initialization
    
    // ChatService instance reference - used to call the actual AI model
    this.chatService = options.chatService || null
    
    // Reasoning process callbacks
    this.onReasoningUpdate = options.onReasoningUpdate || null
    this.onProgressUpdate = options.onProgressUpdate || null
    
    // Tool confirmation callback
    this.onToolConfirmationRequest = options.onToolConfirmationRequest || null
    
    // Internal state
    this.currentIteration = 0
    this.conversationHistory = []
    this.toolCallHistory = []
    this.reasoningTrace = []
    
    // Stop control
    this.shouldStop = false
    
    // Tool confirmation related
    this.requireToolConfirmation = false
    this.toolConfirmationTimeout = 60
    this.allowBatchToolConfirmation = true
    this.pendingToolConfirmation = false
    this.pendingTools = []
    this.toolConfirmationPromise = null
    
    // Context management
    this.reactContext = [] // Complete context during ReAct process (thinking, action, observation)
    this.currentSessionContext = [] // All history of current reasoning session
    
    // Bind methods
    this.think = this.think.bind(this)
    this.act = this.act.bind(this)
    this.observe = this.observe.bind(this)
    this.reason = this.reason.bind(this)
    
    // Initialize system tools
    this.initializeSystemTools()
  }

  /**
   * Stop current reasoning process
   */
  stop() {
    this.log('Received stop command, stopping reasoning process')
    this.shouldStop = true
  }

  /**
   * Reset stop state
   */
  resetStopState() {
    this.shouldStop = false
  }

  /**
   * Set tool confirmation configuration
   */
  setToolConfirmationConfig(config) {
    this.requireToolConfirmation = config.requireToolConfirmation || false
    this.toolConfirmationTimeout = config.toolConfirmationTimeout || 60
    this.allowBatchToolConfirmation = config.allowBatchToolConfirmation !== false
    this.log('Tool confirmation configuration updated:', config)
  }

  /**
   * Request tool execution confirmation
   */
  async requestToolConfirmation(tools) {
    if (!this.requireToolConfirmation) {
      return { confirmed: true, tools }
    }

    this.log('Requesting tool execution confirmation:', tools)
    
    // Set waiting for confirmation state
    this.pendingToolConfirmation = true
    this.pendingTools = tools.map(tool => ({
      ...tool,
      type: tool.sessionId === 'system' ? 'system' : 'mcp'
    }))

    // Don't show tool confirmation info in reasoning updates to avoid affecting AI model's context judgment

    // Trigger UI confirmation request callback
    if (this.onToolConfirmationRequest) {
      this.onToolConfirmationRequest({
        pendingTools: this.pendingTools,
        allowBatchConfirmation: this.allowBatchToolConfirmation,
        timeout: this.toolConfirmationTimeout,
        status: 'waiting_confirmation',
        message: `AI wants to execute ${tools.length} tool operations, please review details and confirm whether to allow`
      })
    }

    // Create confirmation Promise
    return new Promise((resolve, reject) => {
      this.toolConfirmationPromise = { resolve, reject }
      
      // Set timeout
      setTimeout(() => {
        if (this.pendingToolConfirmation) {
          this.handleToolConfirmationTimeout()
          reject(new Error('Tool confirmation timeout'))
        }
      }, this.toolConfirmationTimeout * 1000)
    })
  }

  /**
   * Handle tool confirmation result
   */
  handleToolConfirmation(confirmedTools) {
    this.log('Received tool confirmation:', confirmedTools)
    
    this.pendingToolConfirmation = false
    this.pendingTools = []
    
    if (this.toolConfirmationPromise) {
      this.toolConfirmationPromise.resolve({ confirmed: true, tools: confirmedTools })
      this.toolConfirmationPromise = null
    }

    // Don't show tool confirmation completion info in reasoning updates to avoid affecting AI model's context judgment

    // Notify UI to reset confirmation state
    if (this.onToolConfirmationRequest) {
      this.onToolConfirmationRequest({
        pendingTools: [],
        allowBatchConfirmation: this.allowBatchToolConfirmation,
        timeout: this.toolConfirmationTimeout,
        status: 'confirmed',
        message: `User confirmed execution of ${confirmedTools.length} tool operations`,
        confirmed: true
      })
    }
  }

  /**
   * Handle tool rejection
   */
  handleToolRejection() {
    this.log('User rejected tool execution')
    
    this.pendingToolConfirmation = false
    this.pendingTools = []
    
    if (this.toolConfirmationPromise) {
      this.toolConfirmationPromise.resolve({ confirmed: false, tools: [] })
      this.toolConfirmationPromise = null
    }

    // Don't show tool rejection info in reasoning updates to avoid affecting AI model's context judgment

    // Notify UI to reset confirmation state
    if (this.onToolConfirmationRequest) {
      this.onToolConfirmationRequest({
        pendingTools: [],
        allowBatchConfirmation: this.allowBatchToolConfirmation,
        timeout: this.toolConfirmationTimeout,
        status: 'rejected',
        message: 'User rejected tool execution, will look for alternative solutions',
        rejected: true
      })
    }
  }

  /**
   * Handle tool confirmation timeout
   */
  handleToolConfirmationTimeout() {
    this.log('Tool confirmation timeout')
    
    this.pendingToolConfirmation = false
    this.pendingTools = []
    
    if (this.toolConfirmationPromise) {
      this.toolConfirmationPromise.reject(new Error('Tool confirmation timeout'))
      this.toolConfirmationPromise = null
    }

    // Don't show tool confirmation timeout info in reasoning updates to avoid affecting AI model's context judgment

    // Notify UI to reset confirmation state
    if (this.onToolConfirmationRequest) {
      this.onToolConfirmationRequest({
        pendingTools: [],
        allowBatchConfirmation: this.allowBatchToolConfirmation,
        timeout: this.toolConfirmationTimeout,
        status: 'timeout',
        message: 'Confirmation timeout, automatically rejected tool execution',
        timedOut: true
      })
    }
  }

  /**
   * Initialize system tools
   */
  initializeSystemTools() {
    try {
      // Get enabled system tool definitions
      this.systemTools = this.systemToolsManager.getToolDefinitions(true)
      this.log('System tools initialization completed:', {
        systemToolsCount: this.systemTools.length,
        mcpToolsCount: this.availableTools.length
      })
    } catch (error) {
      this.log('Failed to initialize system tools:', error)
      this.systemTools = []
    }
  }

  /**
   * Main ReAct processing flow
   */
  async processUserMessage(userMessage, context = {}) {
    try {
      this.resetIteration()
      this.resetStopState() // Reset stop state
      this.log('Starting to process user message:', userMessage)
      
      // Notify start of reasoning
      if (this.onReasoningUpdate) {
        this.onReasoningUpdate(`🚀 **Starting ReAct Reasoning** Begin analyzing problem ➡️ '${userMessage.substring(0, 50)}${userMessage.length > 50 ? '...' : ''}'`)
      }
      
      // Initialize session context (if this is a new reasoning session)
      context.userMessage = userMessage // Pass user message for context selection
      this.initializeSessionContext(context)
      
      // Build initial thought
      const initialThought = await this.think(userMessage, context)
      this.reasoningTrace.push({
        type: 'thought',
        content: initialThought,
        timestamp: Date.now()
      })
      
      // Start ReAct loop
      let result = await this.reactLoop(userMessage, initialThought, context)
      
      // If no final result obtained, provide summary
      if (!result || !result.final) {
        result = await this.provideFinalSummary()
      }
      
      // Result quality assessment
      const qualityAssessment = this.evaluateResultQuality(result, userMessage)
      
      return {
        success: true,
        result,
        trace: this.reasoningTrace,
        toolCalls: this.toolCallHistory,
        iterations: this.currentIteration,
        quality: qualityAssessment
      }
      
    } catch (error) {
      this.log('Error occurred while processing message:', error)
      
      // Check if user actively stopped
      if (error.message.includes('User manually stopped the reasoning process') || error.message.includes('用户手动停止了推理过程')) {
        this.log('🛑 User actively stopped the reasoning process')
        
        // Notify reasoning process update - user-friendly stop info
        if (this.onReasoningUpdate) {
          this.onReasoningUpdate(`⏹️ **Processing Stopped** User manually stopped the AI reasoning process`)
        }
        
        return {
          success: true, // Mark as success because this is user's expected behavior
          result: {
            final: true,
            answer: 'You have manually stopped the AI processing. If needed, you can resend the message to continue the conversation.',
            thought: `User actively stopped the reasoning process at iteration ${this.currentIteration}.`,
            iterations: this.currentIteration,
            stopped: true // Mark as user actively stopped
          },
          trace: this.reasoningTrace,
          toolCalls: this.toolCallHistory,
          iterations: this.currentIteration,
          userStopped: true // Add user stop identifier
        }
      }
      
      // Handle other errors
      // Attempt error recovery
      const recovery = await this.recoverFromError(error, context)
      
      return {
        success: false,
        error: error.message,
        trace: this.reasoningTrace,
        toolCalls: this.toolCallHistory,
        iterations: this.currentIteration,
        recovery: recovery
      }
    }
  }

  /**
   * Initialize session context (optimized to use unified intelligent context management)
   */
  initializeSessionContext(context) {
    // Since we now directly use ChatService's intelligent context selection in buildMessagesWithContext
    // This method is mainly used for logging and state tracking
    if (context.conversationHistory?.length > 0) {
      this.log('📚 Session context info:', {
        totalHistoryLength: context.conversationHistory.length,
        userMessage: context.userMessage?.substring(0, 50) + '...',
        note: 'Will use intelligent context selection in buildMessagesWithContext'
      })
    }
  }



  /**
   * Error recovery mechanism - learn from failures
   */
  async recoverFromError(error, context) {
    this.log('🔄 Starting error recovery mechanism:', error)
    
    // Record error pattern
    this.reasoningTrace.push({
      type: 'error_recovery',
      error: error.message,
      context: context,
      timestamp: Date.now()
    })
    
    // Analyze error type and formulate recovery strategy
    if (error.message.includes('Tool does not exist') || error.message.includes('工具不存在')) {
      // Tool not found error - provide alternative tool suggestions
      const suggestedTools = this.suggestAlternativeTools(error.requestedTool)
      return {
        recovery: 'alternative_tools',
        suggestion: suggestedTools,
        message: `Requested tool does not exist, suggested alternatives: ${suggestedTools.join(', ')}`
      }
    }
    
    if (error.message.includes('Parameter error') || error.message.includes('参数错误')) {
      // Parameter error - provide parameter correction suggestions
      return {
        recovery: 'parameter_correction',
        message: 'Parameter format is incorrect, please check and readjust parameter format'
      }
    }
    
    if (error.message.includes('timeout') || error.message.includes('超时')) {
      // Timeout error - suggest task decomposition
      return {
        recovery: 'task_decomposition',
        message: 'Task execution timeout, suggest breaking down complex tasks into multiple steps'
      }
    }
    
    // General error recovery
    return {
      recovery: 'general',
      message: `Encountered error: ${error.message}, trying alternative methods...`
    }
  }

  /**
   * Suggest alternative tools
   */
  suggestAlternativeTools(requestedTool) {
    if (!requestedTool) return []
    
    // Recommend based on tool name similarity
    const suggestions = []
    for (const tool of this.availableTools) {
      if (tool.name.toLowerCase().includes(requestedTool.toLowerCase()) ||
          requestedTool.toLowerCase().includes(tool.name.toLowerCase())) {
        suggestions.push(tool.name)
      }
    }
    
    // If no similar tools found, return the most commonly used tools
    if (suggestions.length === 0) {
      return this.availableTools.slice(0, 3).map(t => t.name)
    }
    
    return suggestions
  }

  /**
   * Result quality assessment
   */
  evaluateResultQuality(result, originalQuestion) {
    const quality = {
      score: 0,
      issues: [],
      recommendations: []
    }
    
    // Completeness check
    if (!result || !result.answer) {
      quality.issues.push('Missing final answer')
      quality.score -= 30
    } else {
      // Answer length reasonableness
      if (result.answer.length < 10) {
        quality.issues.push('Answer too brief')
        quality.score -= 10
      } else if (result.answer.length > 2000) {
        quality.issues.push('Answer too verbose')
        quality.score -= 5
      } else {
        quality.score += 20
      }
    }
    
    // Reasoning process assessment
    if (result.iterations > 0) {
      quality.score += Math.min(result.iterations * 5, 25)
    }
    
    // Tool usage assessment
    if (this.toolCallHistory.length > 0) {
      const successRate = this.toolCallHistory.filter(call => call.success).length / this.toolCallHistory.length
      quality.score += successRate * 20
    }
    
    // Generate improvement suggestions
    if (quality.score < 50) {
      quality.recommendations.push('Consider using more tools to gather information')
      quality.recommendations.push('Increase reasoning depth')
    }
    
    return quality
  }

  /**
   * ReAct main loop
   */
  async reactLoop(userMessage, initialThought, context) {
    let currentThought = initialThought
    
    // First check if initial thought already contains final answer
    if (this.hasFinalAnswer(currentThought)) {
      this.log('Initial thought already contains final answer, no need to enter loop')
      return {
        final: true,
        answer: this.extractFinalAnswer(currentThought),
        thought: currentThought,
        iterations: 0
      }
    }
    
    let needsAction = this.identifyActionNeeded(currentThought)
    
    while (needsAction && this.currentIteration < this.maxIterations && !this.shouldStop) {
      this.currentIteration++
      this.log(`Starting iteration ${this.currentIteration}`)
      
      // Check if need to stop
      if (this.shouldStop) {
        this.log('Detected stop signal, ending reasoning loop')
        if (this.onReasoningUpdate) {
          this.onReasoningUpdate(`⏹️ **Reasoning Stopped**: User manually stopped the processing`)
        }
        throw new Error('User manually stopped the reasoning process')
      }
      
      // Notify iteration start
      if (this.onReasoningUpdate) {
        this.onReasoningUpdate(`🔄 **Iteration ${this.currentIteration} Started**`)
      }
      
      // Action phase
      const actionResult = await this.act(currentThought, context)
      
      if (!actionResult) {
        // Notify loop end reason
        if (this.onReasoningUpdate) {
          this.onReasoningUpdate(`🔚 **Loop Ended**: No more actions needed`)
        }
        break // Cannot execute action, end loop
      }
      
      // Observation phase
      const observation = await this.observe(actionResult)
      
      // Reasoning phase
      // Update state
      currentThought = await this.reason(userMessage, currentThought, actionResult, observation, context)
      needsAction = this.identifyActionNeeded(currentThought)
      
      // Check if final answer has been obtained
      if (this.hasFinalAnswer(currentThought)) {
        // Notify final answer found
        if (this.onReasoningUpdate) {
          this.onReasoningUpdate(`✅ **Final Answer Obtained** Reasoning completed with ${this.currentIteration} iterations`)
        }
        
        return {
          final: true,
          answer: this.extractFinalAnswer(currentThought),
          thought: currentThought,
          iterations: this.currentIteration
        }
      }
    }
    
    // If loop ended but no final answer obtained
    const endReason = this.currentIteration >= this.maxIterations ? 'max_iterations_reached' : 'no_more_actions'
    
    // Notify loop ended but no final answer obtained
    if (this.onReasoningUpdate) {
      const reasonText = endReason === 'max_iterations_reached' 
        ? `Reached maximum iterations (${this.maxIterations})` 
        : 'No more actions needed'
      this.onReasoningUpdate(`⚠️ **Reasoning Loop Ended** ${reasonText}, will provide answer based on current information`)
    }
    
    return {
      final: false,
      thought: currentThought,
      iterations: this.currentIteration,
      reason: endReason
    }
  }

  /**
   * Thinking phase - analyze user request
   */
  async think(userMessage, context = {}) {
    this.log('Thinking phase: analyzing user request')
    
    // Notify progress update
    if (this.onProgressUpdate) {
      this.onProgressUpdate('🤔 Thinking and analyzing user request...')
    }
    
    try {
      // Build thinking prompt
      const thinkingPrompt = this.buildThinkingPrompt(userMessage, context)
      
      // Use reasoning-optimized model configuration
      const thinkingConfig = {
        ...this.modelConfig,
        ...REACT_MODEL_CONFIGS.reasoning
      }
      
      // Call model for thinking
      const response = await this.callLanguageModel(thinkingPrompt, thinkingConfig)
      
      this.log('Thinking result:', response)
      
      // Notify reasoning process update
      if (this.onReasoningUpdate) {
        this.onReasoningUpdate(`🤔 **Thinking Phase** \n${response.substring(0, 500)}${response.length > 500 ? '...' : ''}`)
      }
      
      return response
      
    } catch (error) {
      this.log('Thinking phase error:', error)
      const errorResponse = `Error analyzing user request: ${error.message}`
      
      // Notify error
      if (this.onReasoningUpdate) {
        this.onReasoningUpdate(`❌ **Thinking Phase Error** \n${errorResponse}`)
      }
      
      return errorResponse
    }
  }

  /**
   * Action phase - execute specific operations
   */
  async act(thought, context = {}) {
    this.log('Action phase: determine and execute operations')
    
    // Check if need to stop
    if (this.shouldStop) {
      this.log('Detected stop signal, terminating action phase')
      throw new Error('User manually stopped the reasoning process')
    }
    
    // Notify progress update
    if (this.onProgressUpdate) {
      this.onProgressUpdate('🛠️ Formulating and executing action plan...')
    }
    
    try {
      // Identify required action type
      const actionPlan = this.identifyActionPlan(thought)
      
      if (!actionPlan) {
        this.log('No specific action needed')
        
        // Notify reasoning process update
        if (this.onReasoningUpdate) {
          this.onReasoningUpdate(`🛠️ **Action Phase** \nNo specific action needed, can directly answer user question`)
        }
        
        return null
      }
      
      this.reasoningTrace.push({
        type: 'action_plan',
        content: actionPlan,
        timestamp: Date.now()
      })
      
      // Notify action plan
      if (this.onReasoningUpdate) {
        const planDescription = actionPlan.type === 'tool_call' 
          ? `Calling tool ${actionPlan.toolName}` 
          : `Executing ${actionPlan.type} type action`
        this.onReasoningUpdate(`🛠️ **Action Plan** \n${planDescription}`)
      }
      
      // Execute action
      let actionResult
      
      if (actionPlan.type === 'tool_error') {
        // Handle tool not found error
        actionResult = {
          success: false,
          type: 'tool_error',
          error: actionPlan.error,
          requestedTool: actionPlan.requestedTool,
          availableTools: actionPlan.availableTools
        }
        this.log('❌ Tool error:', actionResult)
      } else if (actionPlan.type === 'multi_tool_call') {
        // Handle multi-tool call
        actionResult = await this.executeMultiToolCall(actionPlan)
      } else if (actionPlan.type === 'tool_call') {
        actionResult = await this.executeToolCall(actionPlan)
      } else if (actionPlan.type === 'information_gathering') {
        actionResult = await this.gatherInformation(actionPlan)
      } else if (actionPlan.type === 'analysis') {
        actionResult = await this.performAnalysis(actionPlan)
      } else {
        actionResult = await this.executeGenericAction(actionPlan)
      }
      
      this.reasoningTrace.push({
        type: 'action_result',
        content: actionResult,
        timestamp: Date.now()
      })
      
      // Notify action result
      if (this.onReasoningUpdate) {
        const resultDescription = actionResult?.success 
          ? `✅ Action executed successfully` 
          : `❌ Action execution failed: ${actionResult?.error || 'Unknown error'}`
        this.onReasoningUpdate(`📊 **Action Result** \n${resultDescription}`)
      }
      
      return actionResult
      
    } catch (error) {
      this.log('Action phase error:', error)
      const errorResult = {
        success: false,
        error: error.message,
        type: 'action_error'
      }
      
      // Notify error
      if (this.onReasoningUpdate) {
        this.onReasoningUpdate(`❌ **Action Phase Error** \n${error.message}`)
      }
      
      return errorResult
    }
  }

  /**
   * Observation phase - analyze action results
   */
  async observe(actionResult) {
    this.log('Observation phase: analyzing action results')
    
    // Notify progress update
    if (this.onProgressUpdate) {
      this.onProgressUpdate('👀 Observing and analyzing action results...')
    }
    
    try {
      let observation
      
      if (!actionResult) {
        observation = 'No action was executed'
      } else if (actionResult.type === 'tool_error') {
        observation = `⚠️ Tool call error: ${actionResult.error}`
      } else if (actionResult.type === 'multi_tool_call') {
        observation = this.analyzeMultiToolCallResult(actionResult)
      } else if (actionResult.success === false) {
        observation = `Action execution failed: ${actionResult.error}`
      } else if (actionResult.type === 'tool_call') {
        observation = this.analyzeToolCallResult(actionResult)
      } else {
        observation = this.analyzeGenericResult(actionResult)
      }
      
      this.reasoningTrace.push({
        type: 'observation',
        content: observation,
        timestamp: Date.now()
      })
      
      this.log('Observation result:', observation)
      
      // Notify reasoning process update
      if (this.onReasoningUpdate) {
        this.onReasoningUpdate(`👀 **Observation Phase** \n${observation.substring(0, 300)}${observation.length > 300 ? '...' : ''}`)
      }
      
      return observation
      
    } catch (error) {
      this.log('Observation phase error:', error)
      const errorObservation = `Error during observation: ${error.message}`
      
      // Notify error
      if (this.onReasoningUpdate) {
        this.onReasoningUpdate(`❌ **Observation Phase Error** \n${errorObservation}`)
      }
      
      return errorObservation
    }
  }

  /**
   * Reasoning phase - continue reasoning based on observation results
   */
  async reason(userMessage, previousThought, actionResult, observation, context = {}) {
    this.log('Reasoning phase: continuing reasoning based on observation results')
    
    // Notify progress update
    if (this.onProgressUpdate) {
      this.onProgressUpdate('💭 Conducting deep reasoning based on observation results...')
    }
    
    try {
      // Build reasoning prompt
      const reasoningPrompt = this.buildReasoningPrompt(
        userMessage, 
        previousThought, 
        actionResult, 
        observation, 
        context
      )
      
      // Use reasoning-optimized model configuration
      const reasoningConfig = {
        ...this.modelConfig,
        ...REACT_MODEL_CONFIGS.reasoning
      }
      
      // Call model for reasoning
      const newThought = await this.callLanguageModel(reasoningPrompt, reasoningConfig)
      
      this.reasoningTrace.push({
        type: 'reasoning',
        content: newThought,
        timestamp: Date.now()
      })
      
      this.log('Reasoning result:', newThought)
      
      // Notify reasoning process update
      if (this.onReasoningUpdate) {
        this.onReasoningUpdate(`💭 **Reasoning Phase** \n${newThought.substring(0, 400)}${newThought.length > 400 ? '...' : ''}`)
      }
      
      return newThought
      
    } catch (error) {
      this.log('Reasoning phase error:', error)
      const errorReasoning = `Error during reasoning: ${error.message}. Based on current information, I think: ${observation}`
      
      // Notify error
      if (this.onReasoningUpdate) {
        this.onReasoningUpdate(`❌ **Reasoning Phase Error** \n${errorReasoning}`)
      }
      
      return errorReasoning
    }
  }

  /**
   * Execute system tool
   */
  async executeSystemTool(toolName, parameters) {
    this.log('🛠️ Starting system tool execution:', toolName)
    
    try {
      const startTime = Date.now()
      
      // Call system tool manager
      const result = await this.systemToolsManager.callTool(toolName, parameters, {
        startTime,
        sessionId: 'system_tools',
        reactEngine: this
      })
      
      const endTime = Date.now()
      const duration = endTime - startTime
      
      this.log('✅ System tool call successful:', {
        toolName,
        success: result.success,
        duration: duration,
        resultType: typeof result.data
      })
      
      
      // Format tool call record - ensure consistency with UI display format
      const toolCallRecord = {
        id: `tool_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        toolName,
        parameters,
        result: result.data || result, // Actual result data from system tool
        sessionId: 'system',
        serverType: 'system',
        startTime,
        endTime,
        duration: result.duration || duration,
        success: result.success !== false, // Ensure boolean value
        error: result.error || null,
        timestamp: endTime
      }
      
      this.toolCallHistory.push(toolCallRecord)
      
      // Return standardized action result format
      return {
        success: result.success !== false,
        type: 'tool_call',
        toolName,
        parameters,
        result: result.content || result, // Use MCP compatible content format
        serverType: 'system',
        duration: toolCallRecord.duration,
        error: result.error || null
      }
      
    } catch (error) {
      this.log('❌ System tool call failed:', {
        toolName,
        error: error.message
      })
      
      const errorRecord = {
        id: `tool_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        toolName,
        parameters,
        error: error.message,
        sessionId: 'system',
        serverType: 'system',
        startTime: Date.now(),
        endTime: Date.now(),
        duration: 0,
        success: false,
        result: null,
        timestamp: Date.now()
      }
      
      this.toolCallHistory.push(errorRecord)
      
      return {
        success: false,
        type: 'tool_call',
        error: error.message,
        toolName,
        parameters,
        result: null,
        serverType: 'system',
        duration: 0
      }
    }
  }

  /**
   * Execute multi-tool call
   */
  async executeMultiToolCall(actionPlan) {
    this.log('🔧 Starting multi-tool call execution:', {
      totalTools: actionPlan.totalTools,
      tools: actionPlan.tools.map(t => t.toolName)
    })
    
    const results = []
    const errors = []
    let totalStartTime = Date.now()
    
    // Determine confirmation strategy based on configuration
    let toolsToExecute = actionPlan.tools
    let skipIndividualConfirmation = false
    
    if (this.requireToolConfirmation && this.allowBatchToolConfirmation) {
      // Batch confirmation mode: request user to confirm all tools at once
      const confirmationResult = await this.requestToolConfirmation(actionPlan.tools)
      
      if (!confirmationResult.confirmed) {
        // User rejected execution of all tools
        return {
          success: false,
          type: 'multi_tool_call',
          totalTools: actionPlan.totalTools,
          successCount: 0,
          failureCount: actionPlan.totalTools,
          results: actionPlan.tools.map((tool, index) => ({
            toolName: tool.toolName,
            originalName: tool.originalName,
            parameters: tool.parameters,
            result: null,
            success: false,
            error: 'User rejected execution of this tool operation',
            userRejected: true,
            index: index + 1
          })),
          errors: actionPlan.tools.map((tool, index) => ({
            toolName: tool.toolName,
            originalName: tool.originalName,
            error: 'User rejected execution of this tool operation',
            index: index + 1
          })),
          duration: Date.now() - totalStartTime,
          summary: `User rejected all ${actionPlan.totalTools} tool calls`
        }
      }
      
      // After user confirmation, use confirmed tool list (may contain modified parameters)
      toolsToExecute = confirmationResult.tools || actionPlan.tools
      skipIndividualConfirmation = true // Already batch confirmed, skip individual confirmation
    }
    // If individual confirmation mode, don't confirm here, let each tool confirm individually
    
    // Execute each tool call sequentially
    for (let i = 0; i < toolsToExecute.length; i++) {
      const tool = toolsToExecute[i]
      this.log(`🔧 Executing tool [${i+1}/${toolsToExecute.length}]:`, tool.toolName)
      
      try {
        // Create separate action plan for each tool call
        const singleToolPlan = {
          type: 'tool_call',
          toolName: tool.toolName,
          parameters: tool.parameters,
          sessionId: tool.sessionId
        }
        
        // Decide whether to skip confirmation based on confirmation mode
        const result = await this.executeToolCall(singleToolPlan, skipIndividualConfirmation)
        results.push({
          toolName: tool.toolName,
          originalName: tool.originalName,
          parameters: tool.parameters,
          result: result,
          success: result.success,
          index: i + 1
        })
        
        this.log(`✅ Tool [${i+1}] execution completed:`, {
          toolName: tool.toolName,
          success: result.success
        })
        
      } catch (error) {
        this.log(`❌ Tool [${i+1}] execution failed:`, {
          toolName: tool.toolName,
          error: error.message
        })
        
        errors.push({
          toolName: tool.toolName,
          originalName: tool.originalName,
          error: error.message,
          index: i + 1
        })
        
        results.push({
          toolName: tool.toolName,
          originalName: tool.originalName,
          parameters: tool.parameters,
          result: null,
          success: false,
          error: error.message,
          index: i + 1
        })
      }
    }
    
    const totalEndTime = Date.now()
    const totalDuration = totalEndTime - totalStartTime
    
    // Build comprehensive result
    const successCount = results.filter(r => r.success).length
    const failureCount = results.filter(r => !r.success).length
    
    this.log('🎯 Multi-tool call completed:', {
      totalTools: actionPlan.totalTools,
      successCount,
      failureCount,
      totalDuration
    })
    
    return {
      success: successCount > 0, // Success if at least one succeeds
      type: 'multi_tool_call',
      totalTools: actionPlan.totalTools,
      successCount,
      failureCount,
      results: results,
      errors: errors,
      duration: totalDuration,
      summary: `Executed ${actionPlan.totalTools} tool calls, ${successCount} successful, ${failureCount} failed`
    }
  }

  /**
   * Gather information
   */
  async gatherInformation(actionPlan) {
    this.log('📚 Starting information gathering:', actionPlan)
    
    try {
      // Information gathering is typically a fallback when no specific tool is identified
      // We can try to use available tools to gather relevant information
      const availableToolNames = [...this.systemTools.map(t => t.function.name), ...this.availableTools.map(t => t.name)]
      
      return {
        success: true,
        type: 'information_gathering',
        message: `Information gathering completed. Available tools for further analysis: ${availableToolNames.join(', ')}`,
        availableTools: availableToolNames,
        suggestion: 'Consider using specific tools to gather more detailed information'
      }
    } catch (error) {
      this.log('❌ Information gathering failed:', error)
      return {
        success: false,
        type: 'information_gathering',
        error: error.message
      }
    }
  }

  /**
   * Perform analysis
   */
  async performAnalysis(actionPlan) {
    this.log('🔍 Starting analysis:', actionPlan)
    
    try {
      // Analysis is typically a reasoning-heavy task that doesn't require external tools
      // We can provide a structured analysis based on available information
      return {
        success: true,
        type: 'analysis',
        message: 'Analysis completed based on available information and context',
        analysisResult: {
          status: 'completed',
          method: 'contextual_analysis',
          recommendation: 'Analysis has been performed using available context and reasoning capabilities'
        }
      }
    } catch (error) {
      this.log('❌ Analysis failed:', error)
      return {
        success: false,
        type: 'analysis',
        error: error.message
      }
    }
  }

  /**
   * Execute generic action
   */
  async executeGenericAction(actionPlan) {
    this.log('⚙️ Starting generic action execution:', actionPlan)
    
    try {
      // Generic action handler for unspecified action types
      // This is a fallback that provides basic action execution
      const actionType = actionPlan.type || 'unknown'
      
      return {
        success: true,
        type: 'generic_action',
        actionType: actionType,
        message: `Generic action of type '${actionType}' has been processed`,
        result: {
          processed: true,
          actionPlan: actionPlan,
          timestamp: Date.now()
        }
      }
    } catch (error) {
      this.log('❌ Generic action execution failed:', error)
      return {
        success: false,
        type: 'generic_action',
        error: error.message
      }
    }
  }

  /**
   * Execute tool call
   */
  async executeToolCall(actionPlan, skipConfirmation = false) {
    this.log('🔧 Starting tool call execution:', actionPlan)
    
    // Debug: show current state during execution
    this.debugCurrentState()
    
    try {
      const { toolName, parameters, sessionId } = actionPlan
      
      // If confirmation required and not skipped, request user confirmation first
      if (this.requireToolConfirmation && !skipConfirmation) {
        const confirmationResult = await this.requestToolConfirmation([actionPlan])
        
        if (!confirmationResult.confirmed) {
          // User rejected execution
          return {
            success: false,
            type: 'tool_call',
            toolName,
            error: 'User rejected execution of this tool operation',
            userRejected: true
          }
        }
        
        // After user confirmation, parameters may have been modified
        if (confirmationResult.tools && confirmationResult.tools.length > 0) {
          const confirmedTool = confirmationResult.tools[0]
          if (confirmedTool.parameters) {
            actionPlan.parameters = confirmedTool.parameters
          }
        }
      }
      
      this.log('🔧 Tool call details:', {
        toolName,
        parameters,
        sessionId,
        systemToolsCount: this.systemTools.length,
        mcpToolsCount: this.availableTools.length,
        enabledSessionsCount: this.enabledSessions.length
      })

      // If system tool, call system tool manager directly
      if (sessionId === 'system') {
        return await this.executeSystemTool(toolName, parameters)
      }
      
      // Verify tool availability
      const tool = this.availableTools.find(t => t.name === toolName)
      if (!tool) {
        const availableToolNames = this.availableTools.map(t => t.name).join(', ')
        throw new Error(`Tool ${toolName} is not available. Available tools: ${availableToolNames}`)
      }
      
      this.log('✅ Tool verification passed:', tool.name)
      
      // Verify session exists
      const sessionExists = this.enabledSessions.find(s => {
        // Compatible with both formats: object and string
        const sessionIdToCheck = s.id || s
        return sessionIdToCheck === sessionId
      })
      
      if (!sessionExists) {
        const availableSessionIds = this.enabledSessions.map(s => s.id || s).join(', ')
        throw new Error(`Session ${sessionId} is not enabled. Enabled sessions: ${availableSessionIds}`)
      }
      
      this.log('✅ Session verification passed:', sessionId)
      
      // Get session info to determine connection type
      const sessionInfo = sessionExists
      const serverType = sessionInfo.serverType || 'unknown'
      
      this.log('🔗 Session info:', {
        sessionId,
        serverType,
        serverName: sessionInfo.name
      })
      
      // Execute tool call (supports both SSE and HTTP types)
      this.log('🚀 Calling MCP tool...')
      const startTime = Date.now()
      const result = await mcpClientManager.callTool(sessionId, toolName, parameters)
      const endTime = Date.now()
      
      this.log('✅ MCP tool call successful:', {
        toolName,
        serverType,
        duration: endTime - startTime,
        resultType: typeof result,
        resultKeys: result && typeof result === 'object' ? Object.keys(result) : 'N/A'
      })
      
      const toolCallRecord = {
        toolName,
        parameters,
        result,
        sessionId,
        serverType,
        startTime,
        endTime,
        duration: endTime - startTime,
        success: true
      }
      
      this.toolCallHistory.push(toolCallRecord)
      
      return {
        success: true,
        type: 'tool_call',
        toolName,
        parameters,
        result,
        serverType,
        duration: toolCallRecord.duration
      }
      
    } catch (error) {
      this.log('❌ Tool call failed:', {
        toolName: actionPlan.toolName,
        error: error.message,
        stack: error.stack
      })
      
      const toolCallRecord = {
        toolName: actionPlan.toolName,
        parameters: actionPlan.parameters,
        error: error.message,
        sessionId: actionPlan.sessionId,
        startTime: Date.now(),
        success: false
      }
      
      this.toolCallHistory.push(toolCallRecord)
      
      return {
        success: false,
        type: 'tool_call',
        error: error.message,
        toolName: actionPlan.toolName
      }
    }
  }

  /**
   * Build thinking prompt
   */
  buildThinkingPrompt(userMessage, context) {
    let prompt = `User request: ${userMessage}\n\n`
    
    if (context.conversationHistory?.length > 0) {
      prompt += `Conversation history:\n${this.formatConversationHistory(context.conversationHistory)}\n\n`
    }
    
    prompt += `Please analyze this request and respond in the specified format. Remember:\n`
    prompt += `1. First analyze user needs in detail in <REASONING>\n`
    prompt += `2. If tool call is needed, output <ACTION> to specify tool and parameters\n`
    prompt += `3. If you can answer directly, output <FINAL_ANSWER>\n\n`
    prompt += `Please start your analysis and response.`
    
    return prompt
  }

  /**
   * Build reasoning prompt
   */
  buildReasoningPrompt(userMessage, previousThought, actionResult, observation, context) {
    let prompt = `User request: ${userMessage}\n\n`
    
    prompt += `Your previous reasoning and actions:\n`
    prompt += `${previousThought}\n\n`
    
    prompt += `Tool execution results (observation):\n`
    if (actionResult && actionResult.type === 'multi_tool_call') {
      // Handle multi-tool call results
      prompt += `🎯 Multi-tool call completed (total: ${actionResult.totalTools}, successful: ${actionResult.successCount}, failed: ${actionResult.failureCount})\n\n`
      
      actionResult.results.forEach((result, index) => {
        prompt += `${index + 1}. **${result.toolName}**:\n`
        if (result.success && result.result) {
          prompt += `   ✅ Execution successful\n`
          // Extract actual text content
          let actualData = result.result
          if (result.result.content && Array.isArray(result.result.content)) {
            // If MCP format, extract text content
            const textContent = result.result.content
              .filter(item => item.type === 'text')
              .map(item => item.text)
              .join(' ')
            if (textContent) {
              actualData = textContent
            }
          }
          prompt += `   📊 Returned data: ${typeof actualData === 'string' ? actualData : JSON.stringify(actualData, null, 2)}\n`
        } else {
          const errorMessage = result.error || (result.result && result.result.error) || 'Unknown error'
          prompt += `   ❌ Execution failed: ${errorMessage}\n`
        }
        prompt += '\n'
      })
    } else if (actionResult && actionResult.success) {
      // Handle single tool call results - unified handling for system tools and MCP tools
      prompt += `✅ Tool "${actionResult.toolName}" executed successfully\n`
      
      // Use unified MCP compatible format for result processing
      if (actionResult.result && Array.isArray(actionResult.result) && actionResult.result[0]?.type === 'text') {
        // MCP format: content array
        const textContent = actionResult.result
          .filter(item => item.type === 'text')
          .map(item => item.text)
          .join('\n')
        prompt += `📊 Returned result: ${textContent}\n\n`
      } else if (typeof actionResult.result === 'string') {
        // String format
        prompt += `📊 Returned result: ${actionResult.result}\n\n`
      } else {
        // Other formats, convert to JSON
        prompt += `📊 Returned data: ${JSON.stringify(actionResult.result, null, 2)}\n\n`
      }
    } else if (actionResult && !actionResult.success) {
      prompt += `❌ Tool execution failed\n`
      prompt += `Error message: ${actionResult.error}\n\n`
    } else {
      prompt += `⚠️ No tools executed\n\n`
    }
    
    prompt += `Please continue reasoning based on the above observation results:\n`
    prompt += `1. If you need to call other tools to get more information, please output <REASONING> and <ACTION>\n`
    prompt += `2. If you have enough information to answer the user's question, please output <REASONING> and <FINAL_ANSWER>\n\n`
    prompt += `Please strictly follow the format described earlier.`
    
    return prompt
  }

  /**
   * Identify if action is needed
   */
  identifyActionNeeded(thought) {
    if (!thought) {
      this.log('🚫 Thought is empty, no action needed')
      return false
    }
    
    this.log('🔍 Identifying if action is needed (based on AI decision tags):', {
      thought: thought.substring(0, 200) + '...'
    })

    // Check if contains ACTION tag - this is a clear indication that AI decided to execute tool calls
    if (thought.includes('<ACTION>')) {
      this.log('✅ Found <ACTION> tag, AI decided to execute tool calls')
      return true
    }
    
    // If contains final answer tag, it means AI thinks it's completed, no further action needed
    if (thought.includes('<FINAL_ANSWER>')) {
      this.log('🚫 Found <FINAL_ANSWER> tag, AI thinks task is completed')
      return false
    }
    
    this.log('🚫 No <ACTION> tag found, AI thinks no tool calls needed for now')
    return false
  }

  /**
   * Identify action plan
   */
  identifyActionPlan(thought) {
    this.log('🎯 Identifying action plan (parsing AI decision):', {
      thought: thought.substring(0, 100) + '...'
    })

    // Parse tool call instructions from AI output <ACTION> tags
    const actionMatch = thought.match(/<ACTION>([\s\S]*?)<\/ACTION>/i)
    if (actionMatch) {
      this.log('📋 Found <ACTION> tag, parsing AI tool call instructions')
      try {
        const actionContent = actionMatch[1].trim()
        this.log('📋 ACTION tag content:', actionContent)
        
        // Parse JSON format tool call instructions
        const actionData = JSON.parse(actionContent)
        
        // Support two formats: single tool call and multi-tool call
        let toolCalls = []
        
        if (actionData.tools && Array.isArray(actionData.tools)) {
          // New format: multi-tool call
          this.log('📋 Detected multi-tool call format:', actionData.tools.length)
          toolCalls = actionData.tools
        } else if (actionData.tool) {
          // Compatible with old format: single tool call
          this.log('📋 Detected single tool call format')
          toolCalls = [{
            tool: actionData.tool,
            parameters: actionData.parameters || {}
          }]
        } else {
          this.log('❌ Invalid ACTION format:', actionData)
          return {
            type: 'tool_error',
            error: `Invalid ACTION format. Please use the correct format to specify tool calls.`,
            availableTools: [...this.systemTools.map(t => t.function.name), ...this.availableTools.map(t => t.name)]
          }
        }
        
        // Process and validate all tool calls
        const processedTools = []
        const errors = []
        
        for (let i = 0; i < toolCalls.length; i++) {
          const toolCall = toolCalls[i]
          let toolName = toolCall.tool
          const parameters = toolCall.parameters || {}
          
          // Normalize tool name: remove possible prefixes (like "functions.")
          const originalToolName = toolName
          
          // 🚫 Force filter AI built-in tools and illegal tool names
          const forbiddenPatterns = [
            'multi_tool_use.parallel',
            'multi_tool_use.',
            'tool_use.',
            'parallel_tool_use',
            'batch_tools',
            'functions.'
          ]
          
          const isForbiddenTool = forbiddenPatterns.some(pattern => {
            return toolName.toLowerCase().includes(pattern.toLowerCase()) || 
                   toolName.toLowerCase().startsWith(pattern.toLowerCase())
          })
          
          if (isForbiddenTool) {
            this.log(`🚫 Detected forbidden tool [${i+1}]:`, {
              requestedTool: originalToolName,
              reason: 'This tool is an AI model built-in tool, not supported by the system'
            })
            errors.push(`Tool "${originalToolName}" is an AI model built-in tool, not supported by this system. Please use tools from the system-provided tool list`)
            continue
          }
          
          if (toolName.includes('.')) {
            toolName = toolName.split('.').pop()
            this.log(`🔧 Normalizing tool name [${i+1}]:`, {
              original: originalToolName,
              normalized: toolName
            })
          }
          
          // First check if it's a system tool
          const systemTool = this.systemTools.find(tool => tool.function.name === toolName)
          if (systemTool) {
            this.log(`✅ Found system tool [${i+1}]:`, {
              toolName,
              originalName: originalToolName
            })
            
            processedTools.push({
              toolName: toolName,
              parameters: parameters,
              sessionId: 'system', // System tools use special identifier
              originalName: originalToolName,
              toolType: 'system'
            })
            continue
          }
          
          // If not a system tool, check if it's an MCP tool
          const mcpTool = this.availableTools.find(t => t.name === toolName)
          if (!mcpTool) {
            this.log(`❌ Tool does not exist [${i+1}]:`, {
              requestedTool: originalToolName,
              normalizedTool: toolName,
              availableSystemTools: this.systemTools.map(t => t.function.name),
              availableMcpTools: this.availableTools.map(t => t.name)
            })
            errors.push(`Tool "${originalToolName}" does not exist`)
            continue
          }
          
          // Find corresponding MCP session
          const sessionId = this.findMcpToolSession(mcpTool.name)
          if (!sessionId) {
            this.log(`❌ Cannot find MCP tool session [${i+1}]:`, toolName)
            errors.push(`Cannot find session for tool "${toolName}"`)
            continue
          }
          
          processedTools.push({
            toolName: toolName,
            parameters: parameters,
            sessionId: sessionId,
            originalName: originalToolName,
            toolType: 'mcp'
          })
        }
        
        // If there are errors, return error information
        if (errors.length > 0) {
          return {
            type: 'tool_error',
            error: `Tool call errors: ${errors.join('; ')}. Available system tools: ${this.systemTools.map(t => t.function.name).join(', ')}. Available MCP tools: ${this.availableTools.map(t => t.name).join(', ')}.`,
            availableTools: [...this.systemTools.map(t => t.function.name), ...this.availableTools.map(t => t.name)]
          }
        }
        
        // If no valid tool calls
        if (processedTools.length === 0) {
          return {
            type: 'tool_error',
            error: `No valid tool calls. Available system tools: ${this.systemTools.map(t => t.function.name).join(', ')}. Available MCP tools: ${this.availableTools.map(t => t.name).join(', ')}.`,
            availableTools: [...this.systemTools.map(t => t.function.name), ...this.availableTools.map(t => t.name)]
          }
        }
        
        // If only one tool call, use simple format
        if (processedTools.length === 1) {
          const plan = {
            type: 'tool_call',
            ...processedTools[0]
          }
          
          this.log('✅ Successfully parsed AI single tool call plan:', plan)
          return plan
        }
        
        // Multi-tool call format
        const plan = {
          type: 'multi_tool_call',
          tools: processedTools,
          totalTools: processedTools.length
        }
        
        this.log('✅ Successfully parsed AI multi-tool call plan:', plan)
        return plan
        
      } catch (error) {
        this.log('❌ Failed to parse ACTION tag:', {
          error: error.message,
          actionContent: actionMatch[1]
        })
        return null
      }
    }
    
    this.log('🚫 No <ACTION> tag found, AI did not specify tool calls')
    return null
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
   * Find session corresponding to MCP tool
   */
  findMcpToolSession(toolName) {
    this.log('🔍 Finding MCP tool session:', {
      toolName,
      availableToolsCount: this.availableTools.length,
      enabledSessionsCount: this.enabledSessions.length,
      availableTools: this.availableTools.map(t => t.name),
      enabledSessions: this.enabledSessions.map(s => s.id || s)
    })
    
    const result = toolResolutionService.findMcpToolSession(
      toolName,
      this.availableTools,
      this.enabledSessions
    )
    
    this.log('🔍 Search result:', { toolName, sessionId: result })
    return result
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
   * Extract parameters from thought
   */
  extractParametersFromThought(thought, tool) {
    // Simplified parameter extraction logic
    // In actual applications, more complex NLP processing might be needed here
    const parameters = {}
    
    // Extract parameters based on tool's input schema
    if (tool.inputSchema && tool.inputSchema.properties) {
      Object.keys(tool.inputSchema.properties).forEach(paramName => {
        // Try to extract parameter values from thought
        const regex = new RegExp(`${paramName}[:\s]+([^,\n]+)`, 'i')
        const match = thought.match(regex)
        if (match) {
          parameters[paramName] = match[1].trim()
        }
      })
    }
    
    return parameters
  }

  /**
   * Check if there is a final answer
   */
  hasFinalAnswer(thought) {
    // Only check structured tags to ensure accuracy
    if (thought.includes('<FINAL_ANSWER>')) {
      this.log('✅ Found <FINAL_ANSWER> tag, confirmed final answer exists')
      return true
    }
    
    // If there's an <ACTION> tag, it means operations need to be executed, definitely not a final answer
    if (thought.includes('<ACTION>')) {
      this.log('❌ Found <ACTION> tag, need to execute tool calls, not a final answer')
      return false
    }
    
    this.log('🔍 No final answer marker found')
    return false
  }

  /**
   * Extract final answer
   */
  extractFinalAnswer(thought) {
    // Prioritize extraction from structured tags
    const finalAnswerMatch = thought.match(/<FINAL_ANSWER>([\s\S]*?)<\/FINAL_ANSWER>/i)
    if (finalAnswerMatch) {
      return finalAnswerMatch[1].trim()
    }
    
    // Fallback: extract from traditional format
    const conclusionMatch = thought.match(/💡 \*\*Conclusion\*\*:?\s*([\s\S]*?)(?=\n\n|$)/)
    if (conclusionMatch) {
      return conclusionMatch[1].trim()
    }
    
    return thought
  }

  /**
   * Analyze multi-tool call result
   */
  analyzeMultiToolCallResult(actionResult) {
    const { totalTools, successCount, failureCount, results, duration } = actionResult
    
    let observation = `🎯 Multi-tool call completed (total: ${totalTools}, successful: ${successCount}, failed: ${failureCount}, duration: ${duration}ms)\n\n`
    
    // Detailed result analysis
    results.forEach((result, index) => {
      observation += `${index + 1}. **${result.toolName}**:\n`
      if (result.success && result.result) {
        observation += `   ✅ Execution successful\n`
        observation += `   📊 Returned data: ${JSON.stringify(result.result.result || result.result, null, 2)}\n`
      } else {
        // Try to get error information from multiple places
        const errorMessage = result.error || 
                            (result.result && result.result.error) || 
                            'Unknown error'
        observation += `   ❌ Execution failed: ${errorMessage}\n`
      }
      observation += '\n'
    })
    
    return observation.trim()
  }

  /**
   * Analyze tool call result
   */
  analyzeToolCallResult(actionResult) {
    if (!actionResult) {
      return 'Tool call result is empty'
    }
    
    const typeInfo = actionResult.serverType ? `(${actionResult.serverType.toUpperCase()})` : ''
    
    if (actionResult.success) {
      let analysisText = `Tool ${actionResult.toolName} ${typeInfo} executed successfully`
      
      // Add execution time information
      if (actionResult.duration !== undefined && actionResult.duration !== null) {
        const durationText = actionResult.duration >= 1000 
          ? `${Math.round(actionResult.duration / 1000)} seconds` 
          : `${actionResult.duration} ms`
        analysisText += `, duration: ${durationText}`
      }
      
      // Handle return results
      if (actionResult.result) {
        let resultText = ''
        
        // Special handling for system tools result format
        if (actionResult.serverType === 'system') {
          if (typeof actionResult.result === 'object' && actionResult.result.message) {
            // If it's system tool standard format, prioritize displaying message
            resultText = actionResult.result.message
            
            // If there's other data, display it too
            if (actionResult.result.data) {
              resultText += `\nDetailed data: ${JSON.stringify(actionResult.result.data, null, 2)}`
            }
          } else if (typeof actionResult.result === 'string') {
            resultText = actionResult.result
          } else {
            resultText = JSON.stringify(actionResult.result, null, 2)
          }
        } else {
          // MCP tool result handling
          if (typeof actionResult.result === 'string') {
            resultText = actionResult.result
          } else {
            resultText = JSON.stringify(actionResult.result, null, 2)
          }
        }
        
        // Limit result display length to avoid being too long
        if (resultText.length > 500) {
          resultText = resultText.substring(0, 500) + '...(result too long, truncated)'
        }
        
        analysisText += `\nReturned result: ${resultText}`
      } else {
        analysisText += '\nReturned result: (empty)'
      }
      
      return analysisText
    } else {
      let errorText = `Tool ${actionResult.toolName} ${typeInfo} execution failed`
      
      if (actionResult.error) {
        errorText += `: ${actionResult.error}`
      }
      
      return errorText
    }
  }

  /**
   * Analyze generic result
   */
  analyzeGenericResult(actionResult) {
    if (!actionResult) {
      return 'Action completed with no result'
    }
    
    // Handle specific action types with more meaningful descriptions
    if (actionResult.type === 'information_gathering') {
      return `📚 Information gathering completed: ${actionResult.message || 'Information collected successfully'}`
    } else if (actionResult.type === 'analysis') {
      return `🔍 Analysis completed: ${actionResult.message || 'Analysis performed successfully'}`
    } else if (actionResult.type === 'generic_action') {
      return `⚙️ Generic action completed: ${actionResult.message || 'Action processed successfully'}`
    }
    
    // Fallback to JSON representation for unknown types
    return `Action execution completed: ${JSON.stringify(actionResult, null, 2)}`
  }

  /**
   * Call language model (with context management)
   */
  async callLanguageModel(prompt, config = {}) {
    // Check if need to stop
    if (this.shouldStop) {
      this.log('Detected stop signal, terminating language model call')
      throw new Error('User manually stopped the reasoning process')
    }
    
    if (!this.chatService) {
      // If no ChatService, fallback to simulation mode
      this.log('WARNING: No ChatService available, using simulated response')
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve(`[Simulated Response] I need to analyze your request and formulate an action plan. Based on the request: "${prompt.substring(0, 50)}...", I will try to use available tools to help you.`)
        }, 1000)
      })
    }

    try {
      // Build system prompt
      const systemPrompt = this.buildSystemPrompt()
      
      // Build message list containing historical context
      const messages = this.buildMessagesWithContext(systemPrompt, prompt)
      
      this.log('🔢 Built message context:', {
        totalMessages: messages.length,
        estimatedTokens: this.chatService.estimateMessagesTokens(messages)
      })
      
      // Merge configuration
      const modelConfig = { ...this.modelConfig, ...config }
      
      // Temporarily update ChatService model configuration
      const originalConfig = this.chatService.modelConfig
      this.chatService.modelConfig = modelConfig
      
      // Call language model raw method to get unparsed structured response
      const response = await this.chatService.callLanguageModelRaw(messages)
      
      // Restore original configuration
      this.chatService.modelConfig = originalConfig
      
      // Add current interaction to context
      this.currentSessionContext.push(
        { role: 'user', content: prompt },
        { role: 'assistant', content: response.content || 'Unable to generate response' }
      )
      
      this.log('Got raw response from language model:', response.content.substring(0, 500) + '...')
      return response.content || 'Unable to generate response'
      
    } catch (error) {
      this.log('Language model call failed:', error)
      // Return error information instead of simulated response when error occurs
      throw new Error(`Language model call failed: ${error.message}`)
    }
  }

  /**
   * Build system prompt
   */
  buildSystemPrompt() {
    // If there's a ChatService instance, prioritize using its system prompt building method
    // This ensures using user-customized prompts
    if (this.chatService && this.chatService.buildSystemPrompt) {
      return this.chatService.buildSystemPrompt()
    }
    
    // Refresh system tools list (ensure latest state)
    this.initializeSystemTools()
    
    // Fallback to default ReAct system prompt template (supports separation of system tools and MCP tools)
    return PromptTemplates.buildReActSystemPrompt(this.availableTools, this.systemTools)
  }

  /**
   * Build message list containing context
   */
  buildMessagesWithContext(systemPrompt, currentPrompt) {
    // Use ChatService's intelligent context selection strategy to get relevant history
    const relevantHistory = this.chatService.selectIntelligentContext(
      this.chatService.conversationHistory, 
      currentPrompt,
      this.modelConfig.maxContextTokens
    )
    
    // Build final message list
    const messages = [
      { role: 'system', content: systemPrompt },
      ...relevantHistory,
      { role: 'user', content: currentPrompt }
    ]
    
    this.log('🔢 ReAct built message context:', {
      systemPromptLength: systemPrompt.length,
      relevantHistoryCount: relevantHistory.length,
      totalMessages: messages.length,
      estimatedTokens: this.chatService.estimateMessagesTokens(messages)
    })
    
    return messages
  }

  /**
   * Provide final summary
   */
  async provideFinalSummary() {
    // Try to let AI provide final summary based on current state
    try {
      const summaryPrompt = `After ${this.currentIteration} reasoning iterations, please provide a final answer to the user based on the information currently available.

Reasoning trace summary:
${this.reasoningTrace.map((trace, index) => 
  `${index + 1}. ${trace.type}: ${trace.content?.substring(0, 100)}...`
).join('\n')}

Tool call history:
${this.toolCallHistory.map((call, index) => 
  `${index + 1}. ${call.toolName}: ${call.success ? 'successful' : 'failed'}`
).join('\n')}

Please directly provide <FINAL_ANSWER> tag content, summarizing the information you can provide.`

      const finalThought = await this.callLanguageModel(summaryPrompt)
      
      // Try to extract final answer from AI response
      const finalAnswer = this.extractFinalAnswer(finalThought)
      
      return {
        final: true,
        answer: finalAnswer || `After ${this.currentIteration} reasoning iterations, I have done my best to handle your request.`,
        thought: finalThought,
        iterations: this.currentIteration
      }
      
    } catch (error) {
      this.log('Failed to generate final summary:', error)
      return {
        final: true,
        answer: `After ${this.currentIteration} reasoning iterations, I have done my best to handle your request, but encountered problems when generating the final summary.`,
        iterations: this.currentIteration
      }
    }
  }

  /**
   * Reset iteration state
   */
  resetIteration() {
    this.currentIteration = 0
    this.reasoningTrace = []
    this.toolCallHistory = []
    // Note: Don't reset currentSessionContext because we need to preserve the entire conversation session context
  }

  /**
   * Reset entire session context (for new conversations)
   */
  resetSessionContext() {
    this.currentSessionContext = []
    this.reactContext = []
    this.resetIteration()
  }

  /**
   * Format conversation history
   */
  formatConversationHistory(history) {
    return history.map(msg => `${msg.role}: ${msg.content}`).join('\n')
  }

  /**
   * Log output
   */
  log(...args) {
    // Use unified debug logging system
    if (DebugLogger.isDebugEnabled()) {
      console.log(DebugLogger.formatPrefix('debug', 'ReActEngine'), ...args)
    }
  }

  /**
   * Get reasoning trace
   */
  getReasoningTrace() {
    return this.reasoningTrace
  }

  /**
   * Get tool call history
   */
  getToolCallHistory() {
    return this.toolCallHistory
  }

  /**
   * Update available tools
   */
  updateAvailableTools(tools) {
    this.availableTools = tools
    // Also refresh system tools
    this.initializeSystemTools()
  }

  /**
   * Update enabled sessions
   */
  updateEnabledSessions(sessions) {
    this.enabledSessions = sessions || []
  }

  /**
   * Debug method: display current state
   */
  debugCurrentState() {
    this.log('🔍 ReAct engine current state:', {
      systemToolsCount: this.systemTools.length,
      systemTools: this.systemTools.map(t => t.function.name),
      mcpToolsCount: this.availableTools.length,
      mcpTools: this.availableTools.map(t => t.name),
      enabledSessionsCount: this.enabledSessions.length,
      enabledSessions: this.enabledSessions.map(s => ({
        id: s.id || s,
        name: s.name || 'Unknown',
        toolCount: s.toolCount || 0
      }))
    })
  }
}
