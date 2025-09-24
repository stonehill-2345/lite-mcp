中文 | [English](README.md)


# 系统工具开发指南

## 📖 概述

系统工具是内置在应用中的工具集，无需外部 MCP 连接即可使用。它们提供基础功能，如连接管理、数据处理等，响应快速且稳定。

## 🏗️ 架构设计

```
system-tools/
├── base/
│   └── SystemTool.js          # 系统工具基类
├── tools/
│   └── McpReconnectTool.js    # MCP 重连工具示例
├── index.js                   # 系统工具管理器
└── README.md                  # 本文档
```

### 核心组件

- **SystemTool 基类**: 所有系统工具的父类，定义了标准接口
- **SystemToolsManager**: 管理器负责工具注册、启用/禁用、调用等
- **工具实现**: 继承基类的具体工具实现

## 📋 系统工具结果格式

### MCP 兼容的统一格式

系统工具的结果会自动转换为与 MCP 工具兼容的格式：

```javascript
// 你在 doExecute 中返回的格式
{
  success: true,
  message: "用户友好的结果描述", // 重要：这是 AI 看到的主要内容
  data: { /* 详细数据 */ },      // 可选：额外的结构化数据
  duration: 123
}

// 基类自动转换为 MCP 兼容格式
{
  content: [
    {
      type: "text",
      text: "用户友好的结果描述"
    }
  ],
  metadata: {
    toolType: "system",
    duration: 123,
    data: { /* 详细数据 */ }
  }
}
```

### 最佳实践

1. **message 字段是关键**：AI 主要基于 `message` 内容进行推理
2. **提供丰富的描述**：在 `message` 中包含足够的信息供 AI 分析
3. **结构化数据放在 data**：复杂数据放在 `data` 字段中
4. **错误处理要友好**：错误信息也要对用户友好

## 🛠️ 实现新的系统工具

### 1. 创建工具类

在 `tools/` 目录下创建新的工具文件，继承 `SystemTool` 基类：

```javascript
import { SystemTool } from '../base/SystemTool.js'

export class YourCustomTool extends SystemTool {
  constructor() {
    super({
      name: 'your_tool_name',           // 工具名称（唯一标识）
      description: '工具描述',          // 工具功能描述
      category: 'utility',              // 工具类别
      version: '1.0.0',                // 版本号
      author: 'your_name',              // 作者
      enabled: true,                    // 默认是否启用
      config: {                         // 工具配置
        timeout: 30000,
        retries: 3
      },
      inputSchema: {                    // 输入参数定义（JSON Schema）
        type: 'object',
        properties: {
          param1: {
            type: 'string',
            description: '参数1描述'
          },
          param2: {
            type: 'number',
            description: '参数2描述',
            minimum: 0,
            maximum: 100
          }
        },
        required: ['param1']
      }
    })
  }

  /**
   * 执行工具逻辑（必须实现）
   * @param {Object} parameters - 输入参数
   * @param {Object} context - 执行上下文
   * @returns {Promise<Object>} 执行结果
   */
  async doExecute(parameters, context) {
    try {
      // 1. 参数验证（基类会自动调用 validateParameters）
      console.log('执行工具:', this.name, '参数:', parameters)
      
      // 2. 执行具体逻辑
      const result = await this.performTask(parameters, context)
      
      // 3. 返回标准格式结果（基类会自动转换为 MCP 兼容格式）
      return {
        success: true,
        message: '执行成功，结果是：' + JSON.stringify(result), // 用户友好的描述
        data: result, // 详细数据（可选）
        duration: Date.now() - context.startTime
      }
    } catch (error) {
      // 4. 错误处理
      return {
        success: false,
        message: `执行失败: ${error.message}`,
        error: error.message,
        duration: Date.now() - context.startTime
      }
    }
  }

  /**
   * 具体任务逻辑
   */
  async performTask(parameters, context) {
    // 实现具体功能
    return { result: 'success' }
  }

  /**
   * 测试连接（可选）
   */
  async testConnection() {
    try {
      // 测试工具是否可用
      return {
        status: 'success',
        message: '工具可用'
      }
    } catch (error) {
      return {
        status: 'error',
        message: error.message
      }
    }
  }

  /**
   * 重置配置（可选）
   */
  resetConfig() {
    this.config = {
      timeout: 30000,
      retries: 3
    }
  }
}
```

### 2. 注册工具

在 `index.js` 的 `registerDefaultTools()` 方法中注册新工具：

```javascript
import { YourCustomTool } from './tools/YourCustomTool.js'

registerDefaultTools() {
  this.log('注册默认系统工具')
  
  // 注册现有工具
  this.registerTool(new McpReconnectTool())
  
  // 注册新工具
  this.registerTool(new YourCustomTool())
  
  this.log(`默认工具注册完成，共 ${this.tools.size} 个工具`)
}
```

### 3. 工具类别

推荐使用以下类别分类：

- `general`: 通用工具
- `utility`: 实用工具
- `search`: 搜索工具
- `api`: API 工具
- `data`: 数据处理工具

## 🎯 使用系统工具

### 在界面中管理

1. 打开"聊天设置" → "系统工具"标签页
2. 查看所有已注册的系统工具
3. 启用/禁用需要的工具
4. 执行工具测试
5. 配置工具参数

### 在代码中调用

```javascript
// 获取系统工具管理器
import systemToolsManager from './index.js'

// 调用工具
const result = await systemToolsManager.callTool('your_tool_name', {
  param1: 'value1',
  param2: 42
}, {
  sessionId: 'chat_session',
  chatService: chatServiceInstance
})

console.log('工具执行结果:', result)
```

### 在 AI 对话中使用

启用的系统工具会自动出现在 AI 的工具列表中，AI 可以根据需要自动调用：

```
用户: 请帮我重连 MCP 服务器
AI: 我来帮您重连 MCP 服务器...
[调用 mcp_reconnect 工具]
AI: 重连完成！成功连接了 3 个服务器。
```

## ⚠️ 注意事项

### 1. 工具命名规范

- 使用小写字母和下划线：`my_tool_name`
- 避免与 MCP 工具重名
- 名称要有意义，便于理解

### 2. 参数验证

- 必须定义 `inputSchema` 用于参数验证
- 在 `doExecute` 中可以添加额外的业务验证
- 对用户输入要进行安全检查

### 3. 错误处理

```javascript
async doExecute(parameters, context) {
  try {
    // 业务逻辑
  } catch (error) {
    // 记录错误日志
    console.error(`[${this.name}] 执行失败:`, error)
    
    // 返回标准错误格式
    return {
      success: false,
      message: '执行失败：' + error.message,
      error: error.message,
      duration: Date.now() - context.startTime
    }
  }
}
```

### 4. 性能考虑

- 避免长时间阻塞操作
- 使用合理的超时时间
- 大文件处理要考虑内存占用
- 适当添加进度反馈

### 5. 安全性

- 验证所有输入参数
- 避免执行危险的系统命令
- 不要泄露敏感信息
- 限制资源访问权限

### 6. 状态管理

- 工具应该是无状态的
- 配置通过 `config` 属性管理
- 避免全局变量依赖

## 🔧 高级功能

### 自定义配置界面

如果工具需要复杂配置，可以在 `SystemToolsConfig.vue` 中添加自定义配置UI：

```javascript
// 在 configTool 方法中添加判断
if (tool.name === 'your_tool_name') {
  configFormData.value = {
    customParam1: tool.config.customParam1 || 'default',
    customParam2: tool.config.customParam2 || 100
  }
}
```

### 工具间通信

```javascript
async doExecute(parameters, context) {
  // 获取其他工具
  const otherTool = context.manager.getTool('other_tool_name')
  
  if (otherTool && otherTool.isAvailable()) {
    // 调用其他工具
    const otherResult = await context.manager.callTool('other_tool_name', {
      // 参数
    }, context)
  }
}
```

### 工具依赖

```javascript
constructor() {
  super({
    // ... 其他配置
    dependencies: ['required_tool_name'] // 声明依赖的工具
  })
}
```

## 🧪 测试工具

### 单元测试示例

```javascript
import { YourCustomTool } from './YourCustomTool.js'

describe('YourCustomTool', () => {
  let tool

  beforeEach(() => {
    tool = new YourCustomTool()
  })

  test('应该正确执行基本功能', async () => {
    const result = await tool.execute({
      param1: 'test'
    }, {
      startTime: Date.now()
    })

    expect(result.success).toBe(true)
    expect(result.data).toBeDefined()
  })

  test('应该正确验证参数', () => {
    const validation = tool.validateParameters({})
    expect(validation.valid).toBe(false)
    expect(validation.error).toContain('param1')
  })
})
```

### 集成测试

在浏览器控制台中测试：

```javascript
// 获取工具管理器
const manager = window.systemToolsManager

// 测试工具
const result = await manager.testTool('your_tool_name')
console.log('测试结果:', result)

// 执行工具
const executeResult = await manager.executeTool('your_tool_name', {
  param1: 'test_value'
})
console.log('执行结果:', executeResult)
```

## 📚 示例参考

参考现有的 `McpReconnectTool` 实现：

- 完整的参数验证
- 详细的错误处理
- 进度反馈机制
- 配置管理
- 与外部服务交互

## 🚀 最佳实践

1. **保持简单**: 每个工具专注于单一功能
2. **文档齐全**: 详细的描述和参数说明
3. **错误友好**: 提供有意义的错误信息
4. **测试充分**: 覆盖正常和异常情况
5. **性能优化**: 避免不必要的计算和网络请求
6. **用户体验**: 提供清晰的执行反馈

---

如有问题，请参考现有工具实现或查看系统工具管理器源码。