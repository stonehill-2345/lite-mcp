# 多语言国际化系统使用说明

## 概述

本项目现已支持中英文双语切换。国际化系统基于 Vue I18n v11 实现，提供了完整的多语言支持。

## 目录结构

```
web/i18n/
├── index.js              # 国际化系统入口文件
├── locales/
│   ├── zh-CN.js         # 中文语言包
│   ├── en-US.js         # 英文语言包
└── README.md            # 本说明文档
```

## 功能特性

1. **中英文切换**：支持简体中文和英文（美国）
2. **持久化存储**：语言选择自动保存到本地存储
3. **Element Plus 集成**：自动切换 Element Plus 组件的语言包
4. **全局访问**：在任何组件中都可以使用 `$t()` 函数
5. **统一管理**：所有文本集中在语言包文件中管理

## 使用方法

### 1. 语言切换

在高级配置页面（AdvancedConfig.vue）中可以切换语言：
- 设置 → 高级设置 → 语言设置 → 界面语言

### 2. 在组件中使用国际化文本

```vue
<template>
  <div>
    <!-- 使用模板中的 $t 函数 -->
    <h1>{{ $t('chat.title') }}</h1>
    
    <!-- 绑定属性 -->
    <el-button :title="$t('common.save')">
      {{ $t('common.save') }}
    </el-button>
    
    <!-- 在 v-if 等指令中使用 -->
    <div v-if="showMessage">
      {{ $t('messages.success') }}
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

// 在脚本中使用
const { t } = useI18n()

// 在方法中使用
const handleSuccess = () => {
  ElMessage.success(t('messages.saveSuccess'))
}
</script>
```

### 3. 添加新的翻译文本

#### 在中文语言包（zh-CN.js）中添加：
```javascript
export default {
  // 在合适的分类下添加
  common: {
    newButton: '新按钮'
  },
  
  // 或创建新的分类
  newFeature: {
    title: '新功能',
    description: '这是一个新功能的描述'
  }
}
```

#### 在英文语言包（en-US.js）中添加对应翻译：
```javascript
export default {
  common: {
    newButton: 'New Button'
  },
  
  newFeature: {
    title: 'New Feature',
    description: 'This is a description of the new feature'
  }
}
```

## 语言包结构

语言包采用嵌套对象结构，便于组织和管理：

```javascript
{
  // 通用术语
  common: {
    save: '保存',
    cancel: '取消'
    // ...
  },
  
  // 聊天相关
  chat: {
    title: 'AI智能助手',
    welcome: '欢迎使用AI智能助手！'
    // ...
  },
  
  // 配置相关
  config: {
    model: {
      title: '模型配置'
      // ...
    }
  }
}
```

## 已完成国际化的组件

- ✅ AdvancedConfig.vue - 高级配置页面（包含语言切换功能）
- ✅ McpServerCard.vue - MCP服务器卡片组件
- 🔄 其他组件正在逐步更新中...

## 待更新的组件列表

以下组件需要进行国际化更新：

### 聊天相关组件
- [ ] ChatInterface.vue - 主聊天界面
- [ ] ChatInput.vue - 聊天输入框
- [ ] ChatMessages.vue - 聊天消息列表
- [ ] ChatSettings.vue - 聊天设置
- [ ] ToolCallDisplay.vue - 工具调用显示
- [ ] ToolConfirmationDialog.vue - 工具确认对话框

### 配置相关组件
- [ ] ModelConfig.vue - 模型配置
- [ ] PromptConfig.vue - 提示词配置
- [ ] ReActConfig.vue - ReAct配置
- [ ] SystemToolsConfig.vue - 系统工具配置

### MCP相关组件
- [ ] McpChatInterface.vue - MCP聊天界面
- [ ] McpConfigEditor.vue - MCP配置编辑器
- [ ] McpServerSection.vue - MCP服务器区段
- [ ] McpToolsPanel.vue - MCP工具面板

### 对话框组件
- [ ] StatisticsDialog.vue - 统计对话框
- [ ] ToolDetailDialog.vue - 工具详情对话框

### 主要页面
- [ ] LiteMCPIndex.vue - 主页面
- [ ] LiteMCPConfig.vue - 配置页面

## 更新组件的步骤

### 1. 导入 useI18n
```javascript
import { useI18n } from 'vue-i18n'
```

### 2. 在 setup 中使用
```javascript
const { t } = useI18n()
```

### 3. 替换模板中的硬编码文本
```vue
<!-- 替换前 -->
<el-button>保存</el-button>

<!-- 替换后 -->
<el-button>{{ $t('common.save') }}</el-button>
```

### 4. 替换脚本中的硬编码文本
```javascript
// 替换前
ElMessage.success('保存成功')

// 替换后
ElMessage.success(t('messages.saveSuccess'))
```

### 5. 确保语言包中有对应的翻译

## 最佳实践

1. **分类管理**：按功能模块组织翻译文本
2. **命名规范**：使用清晰的层级命名，如 `config.model.apiKey`
3. **同步更新**：添加新文本时，确保中英文语言包都有对应翻译
4. **占位符支持**：Vue I18n 支持参数占位符，如 `$t('message.welcome', { name: 'John' })`
5. **复数形式**：可以处理复数形式，如 `$tc('message.items', count)`

## 开发工具

### 检查缺失翻译
可以编写脚本检查语言包中缺失的翻译：

```javascript
// 检查中英文语言包的一致性
const zhKeys = Object.keys(flatten(zhCN))
const enKeys = Object.keys(flatten(enUS))

const missingInEn = zhKeys.filter(key => !enKeys.includes(key))
const missingInZh = enKeys.filter(key => !zhKeys.includes(key))
```

## 注意事项

1. **Element Plus 语言包**：切换语言时需要刷新页面以更新 Element Plus 组件的语言包
2. **动态内容**：服务器返回的动态内容不需要翻译，保持原始内容
3. **日志内容**：代码中的日志可以直接使用英文，动态输出的内容保持原样
4. **性能考虑**：避免在循环中频繁调用 `$t()` 函数

## 扩展支持

如需添加更多语言支持：

1. 在 `locales/` 目录下创建新的语言包文件
2. 在 `index.js` 中导入并注册新语言
3. 在 `getAvailableLocales()` 函数中添加语言选项
4. 导入对应的 Element Plus 语言包

## 贡献指南

更新组件国际化时，请遵循以下原则：

1. 保持翻译准确性和专业性
2. 遵循现有的命名规范
3. 测试切换语言功能
4. 更新此文档的完成状态

---

**注意**：本国际化系统已完成基础架构和核心功能，其他组件的更新正在进行中。如需帮助或发现问题，请查阅相关文档或联系开发团队。
