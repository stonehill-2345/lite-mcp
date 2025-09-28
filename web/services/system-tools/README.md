English | [中文](README.zh_CN.md)

# System Tools Development Guide

## 📖 Overview

System tools are a set of built-in tools in the application that can be used without external MCP connections. They provide basic functions such as connection management and data processing, with fast and stable responses.

## 🏗️ Architecture Design

```
system-tools/
├── base/
│   └── SystemTool.js          # System tool base class
├── tools/
│   └── McpReconnectTool.js    # MCP reconnect tool example
├── index.js                   # System tools manager
└── README.md                  # This document
```

### Core Components

- **SystemTool Base Class**: Parent class for all system tools, defining standard interfaces
- **SystemToolsManager**: Manager responsible for tool registration, enabling/disabling, and calling
- **Tool Implementation**: Specific tool implementations inheriting from the base class

## 📋 System Tools Result Format

### MCP-Compatible Unified Format

System tool results are automatically converted to MCP tool-compatible format:

```javascript
// Format you return in doExecute
{
  success: true,
  message: "User-friendly result description", // Important: This is the main content AI sees
  data: { /* Detailed data */ },               // Optional: Additional structured data
  duration: 123
}

// Base class automatically converts to MCP-compatible format
{
  content: [
    {
      type: "text",
      text: "User-friendly result description"
    }
  ],
  metadata: {
    toolType: "system",
    duration: 123,
    data: { /* Detailed data */ }
  }
}
```

### Best Practices

1. **message field is key**: AI primarily reasons based on `message` content
2. **Provide rich descriptions**: Include sufficient information in `message` for AI analysis
3. **Put structured data in data**: Complex data goes in the `data` field
4. **Friendly error handling**: Error messages should also be user-friendly

## 🛠️ Implementing New System Tools

### 1. Create Tool Class

Create a new tool file in the `tools/` directory, inheriting from the `SystemTool` base class:

```javascript
import { SystemTool } from '../base/SystemTool.js'

export class YourCustomTool extends SystemTool {
  constructor() {
    super({
      name: 'your_tool_name',           // Tool name (unique identifier)
      description: 'Tool description',  // Tool function description
      category: 'utility',              // Tool category
      version: '1.0.0',                 // Version number
      author: 'your_name',              // Author
      enabled: true,                    // Whether enabled by default
      config: {                         // Tool configuration
        timeout: 30000,
        retries: 3
      },
      inputSchema: {                    // Input parameter definition (JSON Schema)
        type: 'object',
        properties: {
          param1: {
            type: 'string',
            description: 'Parameter 1 description'
          },
          param2: {
            type: 'number',
            description: 'Parameter 2 description',
            minimum: 0,
            maximum: 100
          }
        },
        required: ['param1']
      }
    })
  }

  /**
   * Execute tool logic (must implement)
   * @param {Object} parameters - Input parameters
   * @param {Object} context - Execution context
   * @returns {Promise<Object>} Execution result
   */
  async doExecute(parameters, context) {
    try {
      // 1. Parameter validation (base class automatically calls validateParameters)
      console.log('Executing tool:', this.name, 'Parameters:', parameters)
      
      // 2. Execute specific logic
      const result = await this.performTask(parameters, context)
      
      // 3. Return standard format result (base class automatically converts to MCP-compatible format)
      return {
        success: true,
        message: 'Execution successful, result is: ' + JSON.stringify(result), // User-friendly description
        data: result, // Detailed data (optional)
        duration: Date.now() - context.startTime
      }
    } catch (error) {
      // 4. Error handling
      return {
        success: false,
        message: `Execution failed: ${error.message}`,
        error: error.message,
        duration: Date.now() - context.startTime
      }
    }
  }

  /**
   * Specific task logic
   */
  async performTask(parameters, context) {
    // Implement specific functionality
    return { result: 'success' }
  }

  /**
   * Test connection (optional)
   */
  async testConnection() {
    try {
      // Test if tool is available
      return {
        status: 'success',
        message: 'Tool is available'
      }
    } catch (error) {
      return {
        status: 'error',
        message: error.message
      }
    }
  }

  /**
   * Reset configuration (optional)
   */
  resetConfig() {
    this.config = {
      timeout: 30000,
      retries: 3
    }
  }
}
```

### 2. Register Tool

Register the new tool in the `registerDefaultTools()` method in `index.js`:

```javascript
import { YourCustomTool } from './tools/YourCustomTool.js'

registerDefaultTools() {
  this.log('Registering default system tools')
  
  // Register existing tools
  this.registerTool(new McpReconnectTool())
  
  // Register new tool
  this.registerTool(new YourCustomTool())
  
  this.log(`Default tools registration completed, total ${this.tools.size} tools`)
}
```

### 3. Tool Categories

Recommended category classifications:

- `general`: General tools
- `utility`: Utility tools
- `search`: Search tools
- `api`: API tools
- `data`: Data processing tools

## 🎯 Using System Tools

### Managing in Interface

1. Open "Chat Settings" → "System Tools" tab
2. View all registered system tools
3. Enable/disable required tools
4. Execute tool tests
5. Configure tool parameters

### Calling in Code

```javascript
// Get system tools manager
import systemToolsManager from './index.js'

// Call tool
const result = await systemToolsManager.callTool('your_tool_name', {
  param1: 'value1',
  param2: 42
}, {
  sessionId: 'chat_session',
  chatService: chatServiceInstance
})

console.log('Tool execution result:', result)
```

### Using in AI Conversations

Enabled system tools will automatically appear in AI's tool list, and AI can automatically call them as needed:

```
User: Please help me reconnect to the MCP server
AI: I'll help you reconnect to the MCP server...
[Calling mcp_reconnect tool]
AI: Reconnection complete! Successfully connected to 3 servers.
```

## ⚠️ Important Notes

### 1. Tool Naming Conventions

- Use lowercase letters and underscores: `my_tool_name`
- Avoid naming conflicts with MCP tools
- Names should be meaningful and easy to understand

### 2. Parameter Validation

- Must define `inputSchema` for parameter validation
- Additional business validation can be added in `doExecute`
- Security checks should be performed on user input

### 3. Error Handling

```javascript
async doExecute(parameters, context) {
  try {
    // Business logic
  } catch (error) {
    // Log error
    console.error(`[${this.name}] Execution failed:`, error)
    
    // Return standard error format
    return {
      success: false,
      message: 'Execution failed: ' + error.message,
      error: error.message,
      duration: Date.now() - context.startTime
    }
  }
}
```

### 4. Performance Considerations

- Avoid long blocking operations
- Use reasonable timeout values
- Consider memory usage when processing large files
- Add progress feedback appropriately

### 5. Security

- Validate all input parameters
- Avoid executing dangerous system commands
- Don't leak sensitive information
- Limit resource access permissions

### 6. State Management

- Tools should be stateless
- Configuration managed through `config` property
- Avoid global variable dependencies

## 🔧 Advanced Features

### Custom Configuration Interface

If a tool requires complex configuration, you can add custom configuration UI in `SystemToolsConfig.vue`:

```javascript
// Add judgment in configTool method
if (tool.name === 'your_tool_name') {
  configFormData.value = {
    customParam1: tool.config.customParam1 || 'default',
    customParam2: tool.config.customParam2 || 100
  }
}
```

### Tool Communication

```javascript
async doExecute(parameters, context) {
  // Get other tool
  const otherTool = context.manager.getTool('other_tool_name')
  
  if (otherTool && otherTool.isAvailable()) {
    // Call other tool
    const otherResult = await context.manager.callTool('other_tool_name', {
      // Parameters
    }, context)
  }
}
```

### Tool Dependencies

```javascript
constructor() {
  super({
    // ... other configurations
    dependencies: ['required_tool_name'] // Declare dependent tools
  })
}
```

## 🧪 Testing Tools

### Unit Test Example

```javascript
import { YourCustomTool } from './YourCustomTool.js'

describe('YourCustomTool', () => {
  let tool

  beforeEach(() => {
    tool = new YourCustomTool()
  })

  test('Should correctly execute basic functionality', async () => {
    const result = await tool.execute({
      param1: 'test'
    }, {
      startTime: Date.now()
    })

    expect(result.success).toBe(true)
    expect(result.data).toBeDefined()
  })

  test('Should correctly validate parameters', () => {
    const validation = tool.validateParameters({})
    expect(validation.valid).toBe(false)
    expect(validation.error).toContain('param1')
  })
})
```

### Integration Testing

Test in browser console:

```javascript
// Get tools manager
const manager = window.systemToolsManager

// Test tool
const result = await manager.testTool('your_tool_name')
console.log('Test result:', result)

// Execute tool
const executeResult = await manager.executeTool('your_tool_name', {
  param1: 'test_value'
})
console.log('Execution result:', executeResult)
```

## 📚 Example References

Refer to the existing `McpReconnectTool` implementation:

- Complete parameter validation
- Detailed error handling
- Progress feedback mechanism
- Configuration management
- Interaction with external services

## 🚀 Best Practices

1. **Keep it simple**: Each tool focuses on a single function
2. **Complete documentation**: Detailed descriptions and parameter explanations
3. **Friendly errors**: Provide meaningful error messages
4. **Thorough testing**: Cover normal and exceptional cases
5. **Performance optimization**: Avoid unnecessary computations and network requests
6. **User experience**: Provide clear execution feedback

---

If you have any questions, please refer to existing tool implementations or check the system tools manager source code.