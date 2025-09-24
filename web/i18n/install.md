# 国际化系统安装和使用指南

## 安装步骤

### 1. 安装依赖

在 web 目录下运行：

```bash
npm install vue-i18n@^11.1.12
```

或者如果使用 yarn：

```bash
yarn add vue-i18n@^11.1.12
```

> **注意**：项目现使用 vue-i18n v11，相比 v9 版本有更好的性能和 TypeScript 支持。

### 2. 已完成的文件

以下文件已经创建并配置完成：

- ✅ `package.json` - 已添加 vue-i18n 依赖
- ✅ `main.js` - 已集成 i18n 系统和 Element Plus 语言包
- ✅ `i18n/index.js` - 国际化系统入口文件
- ✅ `i18n/locales/zh-CN.js` - 中文语言包
- ✅ `i18n/locales/en-US.js` - 英文语言包
- ✅ `components/config/AdvancedConfig.vue` - 已添加语言切换功能
- ✅ `components/mcp/McpServerCard.vue` - 已完成国际化

### 3. 测试语言切换

1. 启动应用
2. 进入设置页面
3. 打开"高级设置"
4. 在"语言设置"中选择语言
5. 页面将自动刷新并应用新语言

## 快速使用模板

### 为组件添加国际化的标准流程：

#### 1. 在 `<script setup>` 中添加导入：

```javascript
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
```

#### 2. 在模板中替换硬编码文本：

```vue
<!-- 替换前 -->
<el-button>保存</el-button>
<div title="这是提示">内容</div>

<!-- 替换后 -->
<el-button>{{ $t('common.save') }}</el-button>
<div :title="$t('common.tooltip')">{{ $t('common.content') }}</div>
```

#### 3. 在脚本中替换消息文本：

```javascript
// 替换前
ElMessage.success('保存成功')

// 替换后  
ElMessage.success(t('messages.saveSuccess'))
```

#### 4. 在语言包中添加对应翻译：

**zh-CN.js:**
```javascript
{
  common: {
    save: '保存',
    tooltip: '这是提示',
    content: '内容'
  },
  messages: {
    saveSuccess: '保存成功'
  }
}
```

**en-US.js:**
```javascript
{
  common: {
    save: 'Save',
    tooltip: 'This is a tooltip', 
    content: 'Content'
  },
  messages: {
    saveSuccess: 'Save successful'
  }
}
```

## 已提供的翻译分类

### 通用术语 (common)
- 基础操作：save, cancel, edit, delete, add, copy 等
- 状态：enabled, disabled, loading, success, failed 等
- 通用词汇：name, type, description, settings 等

### 页面标题 (pages)
- home, chat, config, tools, logs, statistics 等

### 聊天界面 (chat)
- 界面文本：title, welcome, quickStart 等
- 操作按钮：sendButton, stopButton, clearHistory 等
- 工具相关：toolsAvailable, toolConfirmation 等
- 配置提示：configHint (完整的提示信息)

### MCP 配置 (mcp)
- 服务器管理：serverManagement, configEditor 等
- 服务器卡片：serverCard (addToAssistant, copyConfig 等)
- 连接状态：connection (connected, disconnected 等)

### 配置页面 (config)
- 模型配置：model (apiKey, temperature, systemPrompt 等)
- 提示词配置：prompt (addPrompt, promptName 等)
- 高级配置：advanced (完整的设置选项)

### 统计和对话框 (statistics, toolDetail)
- 统计数据：totalMessages, apiCalls, successRate 等
- 工具详情：toolName, parameters, executionHistory 等

### 消息通知 (messages)
- 网络错误：networkError, serverError 等
- 操作结果：saveSuccess, copyFailed 等

### 日志相关 (logs)
- 日志级别：debug, info, warn, error
- 操作：clearLogs, downloadLogs, refreshLogs

## 批量更新工具

为了快速更新所有组件，可以使用以下正则表达式进行批量替换：

### 查找常见中文文本模式：
```regex
"([^"]*[\u4e00-\u9fa5]+[^"]*)"
'([^']*[\u4e00-\u9fa5]+[^']*)'
>([^<]*[\u4e00-\u9fa5]+[^<]*)<
```

### 替换建议：
1. 模板中的文本：`{{ $t('category.key') }}`
2. 属性绑定：`:title="$t('category.key')"`
3. 脚本中的文本：`t('category.key')`

## 注意事项

1. **Element Plus 语言包**：切换语言时会自动刷新页面以更新组件语言
2. **动态内容**：API 返回的动态内容无需翻译
3. **日志文本**：技术日志建议使用英文，用户界面的日志标签已翻译
4. **占位符**：支持参数化翻译，如 `$t('message.welcome', { name: 'John' })`

## 待更新组件优先级

### 高优先级（用户最常接触）：
1. ChatInterface.vue - 主聊天界面
2. ChatInput.vue - 聊天输入
3. ModelConfig.vue - 模型配置
4. McpChatInterface.vue - MCP聊天界面

### 中优先级（设置和配置）：
1. PromptConfig.vue - 提示词配置
2. SystemToolsConfig.vue - 系统工具配置
3. McpConfigEditor.vue - MCP配置编辑器
4. ChatSettings.vue - 聊天设置

### 低优先级（对话框和辅助组件）：
1. StatisticsDialog.vue - 统计对话框
2. ToolDetailDialog.vue - 工具详情对话框
3. 其他工具显示组件

## 验证清单

更新组件后，请检查：

- [ ] 导入了 `useI18n`
- [ ] 在 setup 中声明了 `const { t } = useI18n()`
- [ ] 所有硬编码中文文本已替换为 `$t()` 调用
- [ ] 在两个语言包中都添加了对应翻译
- [ ] 切换语言功能正常工作
- [ ] 没有控制台错误

---

**提示**：建议先完成高优先级组件的国际化，确保核心功能的多语言支持，然后逐步完善其他组件。
