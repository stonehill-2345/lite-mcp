# 外部MCP服务管理器

## 概述

外部MCP服务管理器是LiteMCP框架的一个核心组件，用于统一管理和集成第三方MCP服务（如`mcp-server-time`、`jina-mcp-tools`等）。通过这个管理器，我们可以将任何支持STDIO模式的外部MCP服务包装成HTTP服务，并统一注册到LiteMCP的代理系统中。

## 设计架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    LiteMCP 代理服务器                            │
│                  (http://host:1888)                             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ HTTP请求转发
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│               外部MCP包装器服务器                                │
│            (ExternalMCPServer)                                  │
│              http://host:8714                                   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ STDIO通信
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│              外部MCP服务进程                                     │
│         (如: mcp-server-time)                                   │
│              STDIO模式                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 架构层次

```
┌─────────────────────────────────────────────────────────────────┐
│                    管理层次                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ 服务管理器      │  │ 进程管理器      │  │ 配置管理器      │ │
│  │ (高级)          │  │ (底层)          │  │ (数据)          │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ 服务协调
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    通信层次                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ 外部MCP服务器   │  │ 外部MCP客户端   │  │ HTTP/SSE/STDIO  │ │
│  │ (HTTP接口)      │  │ (STDIO通信)     │  │ (传输协议)      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ 进程通信
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    外部服务层次                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ mcp-server-time │  │ jina-mcp-tools  │  │ 其他MCP服务     │ │
│  │ (时间工具)      │  │ (AI工具)        │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件

1. **配置管理器** (`config_manager.py`)
   - 管理外部MCP服务的模板配置和实例配置
   - 支持JSON格式的配置文件存储
   - 处理实例创建、更新、删除和验证

2. **包装器服务器** (`external_mcp_server.py`)
   - 将STDIO模式的外部MCP服务包装成HTTP服务
   - 处理MCP协议的转换和通信
   - 提供ExternalMCPClient用于STDIO通信
   - 支持HTTP、SSE和STDIO传输模式

3. **进程管理器** (`process_manager.py`)
   - 外部MCP服务的底层进程管理
   - 处理子进程启动、停止和监控
   - 管理资源清理和进程生命周期
   - 提供健康检查和进程状态监控

4. **服务管理器** (`service_manager.py`)
   - 高级服务生命周期管理
   - 协调配置、进程和代理系统
   - 处理智能端口分配和服务注册
   - 提供服务操作的统一API

5. **API接口** (`../controller/external_mcp_api.py`)
   - 提供RESTful API用于管理外部MCP服务
   - 支持CRUD操作和服务控制
   - 处理模板和实例管理

## 工作流程

### 1. 配置管理

#### 实例配置 (`config/external_mcp_instances.json`)
```json
{
  "263123a5-d745-4c98-9853-042c2c8c838c": {
    "template_name": "time",
    "instance_name": "我的时间工具",
    "enabled": true,
    "transport": "http",
    "host": null,
    "port": null,
    "created": "2025-09-23T09:40:50.114300",
    "updated": "2025-09-23T09:40:50.114557"
  }
}
```

### 2. 服务启动流程

1. **读取配置**
   - `ExternalMCPConfigManager`加载模板和实例配置
   - 筛选出已启用的实例

2. **启动外部进程**
   - `ExternalMCPServiceManager`协调服务启动
   - `ExternalMCPProcessManager`处理底层进程管理
   - 使用`subprocess.Popen`启动包装器进程
   - 包装器进程内部启动外部MCP服务（STDIO模式）

3. **建立通信**
   - `ExternalMCPClient`通过STDIO与外部服务通信
   - 使用独立的读写线程处理JSON-RPC消息
   - `ExternalMCPServer`对外提供HTTP接口
   - 支持多种传输协议（HTTP、SSE、STDIO）

4. **服务注册**
   - `ExternalMCPServiceManager`处理服务注册
   - 包装器服务器注册到LiteMCP主注册表
   - 通过代理服务器统一对外提供服务
   - 支持自动代理注册和注销

### 3. 通信协议

#### STDIO通信（包装器 ↔ 外部服务）
```json
// 发送到外部服务
{"jsonrpc": "2.0", "id": "1", "method": "tools/call", "params": {"name": "get_current_time", "arguments": {}}}

// 外部服务响应
{"jsonrpc": "2.0", "id": "1", "result": {"content": [{"type": "text", "text": "2025-09-23 14:30:00"}]}}
```

#### HTTP通信（客户端 ↔ 包装器）
```bash
curl -X POST http://host:8714/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "get_current_time", "arguments": {}}, "jsonrpc": "2.0", "id": 1}'
```

## 关键特性

### 1. 动态配置
- **模板系统**：预定义常用外部MCP服务的配置模板
- **实例管理**：基于模板创建具体的服务实例
- **热更新**：支持运行时添加、删除、启用/禁用服务
- **配置验证**：内置的实例配置验证机制

### 2. 进程管理
- **独立进程**：每个外部服务运行在独立的子进程中
- **健康检查**：实时监控进程和通信线程状态
- **自动重启**：服务崩溃时自动重启
- **优雅关闭**：支持正确的进程清理
- **资源管理**：自动清理进程和资源

### 3. 服务管理
- **统一服务管理器**：高级协调所有服务操作
- **智能端口分配**：自动端口分配和冲突解决
- **代理集成**：与LiteMCP代理系统无缝集成
- **服务发现**：自动服务注册和发现

### 4. 错误处理
- **连接重试**：通信失败时自动重试
- **错误日志**：详细的错误信息和调试日志
- **降级处理**：服务不可用时返回友好的错误信息
- **健康监控**：持续的健康检查和状态报告

### 5. 集成特性
- **统一代理**：通过LiteMCP代理服务器统一访问
- **配置API**：自动出现在`/config`接口中
- **友好命名**：支持中文显示名称和英文URL路径
- **多传输支持**：HTTP、SSE和STDIO传输模式

## 🚀 快速开始

### 1. 安装依赖

首先确保系统已安装必要的工具：

```bash
# 安装uvx（用于Python MCP服务）
pip install uv

# 安装Node.js和npm（用于npx MCP服务）
# 根据你的操作系统安装Node.js

# 验证安装
uvx --version
npx --version
```

### 2. 安装外部MCP服务

```bash
# 安装时间服务器
uvx install mcp-server-time

# 安装文件系统服务器
uvx install mcp-server-filesystem

# 测试安装（可选）
uvx mcp-server-time --help
```

### 3. 配置外部服务

编辑 `config/external_mcp_servers.yaml`：

```yaml
external_mcp_servers:
  time:
    enabled: true                    # 启用时间服务器
    name: "time"
    command: "uvx"
    args: ["mcp-server-time", "--local-timezone=Asia/Shanghai"]
    env: {}
    description: "时间和日期操作工具服务器"
```

### 4. 配置LiteMCP启动

编辑 `config/servers.yaml`：

```yaml
mcp_servers:
  external_time:
    enabled: true                    # 启用外部时间服务器
    server_type: "external_time"     
    transport: "http"                
    host: null                       
    port: null                       
    auto_restart: true               
    description: "时间和日期操作工具服务器（外部uvx服务）"
```

### 5. 启动服务

```bash
# 启动所有服务
./scripts/manage.sh up

# 或者只启动外部时间服务器
./scripts/manage.sh up --name external_time

# 检查状态
./scripts/manage.sh ps
```

## 📋 内置外部服务示例

### 时间服务器 (external_time)

基于 `mcp-server-time` 的时间操作工具。

**功能特性**:
- 获取当前时间和日期
- 时区转换
- 日期格式化
- 时间计算

**配置示例**:
```yaml
time:
  enabled: true
  name: "time"
  command: "uvx"
  args: ["mcp-server-time", "--local-timezone=Asia/Shanghai"]
  env: {}
  description: "时间和日期操作工具服务器"
```

**使用示例**:
```
- "获取当前北京时间"
- "将时间转换为UTC"
- "计算两个日期之间的差异"
```

### Jina AI工具集 (external_jina)

基于 `jina-mcp-tools` 的AI驱动工具集。

**功能特性**:
- 网页内容搜索和分析
- 文本摘要和提取
- 语义搜索
- 文档理解

**配置示例**:
```yaml
jina-tools:
  enabled: true
  name: "jina-tools"
  command: "npx"
  args: ["jina-mcp-tools"]
  env:
    JINA_API_KEY: "${JINA_API_KEY}"  # 从环境变量获取
  description: "Jina AI工具集"
```

**环境变量设置**:
```bash
export JINA_API_KEY="your_actual_api_key"
```

**使用示例**:
```
- "搜索关于机器学习的最新文章"
- "总结这个网页的内容"
- "分析这段文本的关键信息"
```

### 文件系统工具 (external_filesystem)

基于 `mcp-server-filesystem` 的文件操作工具。

**功能特性**:
- 文件读取和写入
- 目录创建和删除
- 文件搜索和列表
- 文件信息查询

**配置示例**:
```yaml
filesystem:
  enabled: true
  name: "filesystem"
  command: "uvx"
  args: ["mcp-server-filesystem", "--write-to-cwd"]
  env: {}
  description: "文件系统操作工具"
```

**安全注意**:
- 默认只允许在当前工作目录下操作
- 建议在测试环境中使用
- 注意文件权限和路径安全

**使用示例**:
```
- "读取config.txt文件的内容"
- "在temp目录下创建一个新文件"
- "列出当前目录下的所有.py文件"
```

## 🔧 自定义外部服务

### 1. 添加配置

在 `config/external_mcp_servers.yaml` 中添加新服务：

```yaml
external_mcp_servers:
  my-custom-service:
    enabled: true
    name: "my-custom"
    command: "python"  # 或 uvx, npx 等
    args: ["/path/to/your/mcp_server.py"]
    env:
      CUSTOM_CONFIG: "value"
      API_KEY: "${MY_API_KEY}"
    description: "我的自定义MCP服务"
    timeout: 45
    auto_restart: true
```

### 2. 创建包装器类

创建 `src/tools/external/my_custom_server.py`：

```python
from .external_mcp_server import ExternalMCPServer, ExternalMCPConfig
from src.core.statistics import mcp_author

@mcp_author("你的名字", department="测试部", project=["TD"])
class MyCustomMCPServer(ExternalMCPServer):
    """自定义外部MCP服务包装器"""
    
    def __init__(self, name: str = "LiteMCP-MyCustom"):
        config = ExternalMCPConfig(
            name="my-custom",
            command="python",
            args=["/path/to/your/mcp_server.py"],
            env={"CUSTOM_CONFIG": "value"},
            description="我的自定义MCP服务",
            timeout=45,
            auto_restart=True
        )
        super().__init__(config, name)
```

### 3. 注册服务

在 `src/tools/__init__.py` 中添加：

```python
AVAILABLE_SERVERS = {
    # ... 其他服务
    "my_custom": {
        "description": "我的自定义MCP服务",
        "module": "src.tools.external.my_custom_server",
        "class": "MyCustomMCPServer"
    }
}
```

### 4. 配置启动

在 `config/servers.yaml` 中添加：

```yaml
mcp_servers:
  my_custom:
    enabled: true
    server_type: "my_custom"
    transport: "http"
    host: null
    port: null
    auto_restart: true
    description: "我的自定义MCP服务"
```

## 🛠️ 配置管理

### 环境变量支持

配置文件支持环境变量替换：

```yaml
external_mcp_servers:
  my-service:
    env:
      API_KEY: "${MY_API_KEY}"          # 从环境变量获取
      BASE_URL: "${BASE_URL:-http://localhost}"  # 带默认值
```

### 全局配置

```yaml
global_config:
  default_timeout: 30                 # 默认超时时间
  enable_monitoring: true             # 启用监控
  restart_policy:
    max_retries: 3                    # 最大重试次数
    retry_interval: 10                # 重试间隔
  logging:
    level: "INFO"                     # 日志级别
    include_external_output: true     # 包含外部服务输出
```

### 配置验证

使用配置管理器验证配置：

```python
from src.tools.external.config_manager import external_config_manager

# 验证配置
validation_result = external_config_manager.validate_config()
print("错误:", validation_result["errors"])
print("警告:", validation_result["warnings"])

# 获取启用的服务
enabled_servers = external_config_manager.get_enabled_servers()
print("启用的服务:", list(enabled_servers.keys()))
```

## 使用方法

### 1. 通过manage.py管理

```bash
# 启动所有服务（包括外部MCP服务）
./scripts/manage.sh up

# 停止所有服务
./scripts/manage.sh down

# 查看服务状态
./scripts/manage.sh ps
```

### 2. 通过API管理

```bash
# 获取所有模板
curl http://localhost:9000/external-mcp/templates

# 创建实例
curl -X POST http://localhost:9000/external-mcp/instances \
  -H "Content-Type: application/json" \
  -d '{"template_name": "time", "instance_name": "我的时间工具"}'

# 启用实例
curl -X POST http://localhost:9000/external-mcp/instances/{instance_id}/enable

# 启动服务
curl -X POST http://localhost:9000/external-mcp/instances/{instance_id}/start
```

### 3. 直接访问服务

```bash
# 通过代理访问（推荐）
curl http://127.0.0.1:1888/mcp/external-time

# 直接访问包装器
curl http://172.17.18.20:8714/mcp
```

## 📊 监控和调试

### 查看外部服务状态

```bash
# 查看所有服务状态
./scripts/manage.sh ps

# 查看服务日志
tail -f runtime/logs/litemcp_src_tools_external_time_server_TimeMCPServer.log

# 详细启动信息
./scripts/manage.sh up --name external_time --verbose
```

### 调试外部服务

1. **检查命令是否可用**:
   ```bash
   uvx --version
   uvx mcp-server-time --help
   ```

2. **测试外部服务独立运行**:
   ```bash
   uvx mcp-server-time --local-timezone=Asia/Shanghai
   ```

3. **检查环境变量**:
   ```bash
   echo $JINA_API_KEY
   ```

4. **查看详细错误日志**:
   ```bash
   ./scripts/manage.sh up --name external_jina --verbose
   ```

## 文件结构

```
src/tools/external/
├── README.md                    # 本文档（中文）
├── README.zh_CN.md              # 英文版本
├── __init__.py                  # 模块初始化
├── config_manager.py            # 配置管理器
├── external_mcp_server.py       # 包装器服务器
├── process_manager.py           # 进程管理器
└── service_manager.py           # 服务管理器

config/
└── external_mcp.json            # 实例配置

src/controller/
└── external_mcp_api.py          # API控制器
```

## 故障排除

### 1. 服务启动失败
- 检查外部命令是否可用（如`uvx`、`npx`）
- 查看日志文件：`runtime/logs/litemcp_src_tools_external_*.log`
- 确认端口未被占用

### 2. 通信问题
- 检查STDIO通信线程是否正常
- 验证JSON-RPC消息格式
- 查看进程状态：`ps aux | grep mcp-server`

### 3. 代理注册问题
- 确认代理服务器运行正常
- 检查服务注册状态：`curl http://host:1888/proxy/status`
- 验证配置API返回：`curl http://localhost:9000/config`

## 扩展开发

### 添加新的外部MCP服务

1. **添加模板配置**
   ```json
   {
     "new_service": {
       "name": "new-service",
       "display_name": "新服务",
       "command": "npx",
       "args": ["new-mcp-service"],
       "env": {"API_KEY": "your_key"},
       "description": "新的MCP服务",
       "category": "utility",
       "transport": "http",
       "host": null,
       "port": null
     }
   }
   ```

2. **创建实例**
   - 通过API或直接修改`external_mcp_instances.json`

3. **启动服务**
   - 使用`manage.py up`或API接口

### 自定义包装器

如果需要特殊的处理逻辑，可以继承`ExternalMCPServer`：

```python
class CustomExternalMCPServer(ExternalMCPServer):
    def _register_tools(self):
        super()._register_tools()
        # 添加自定义逻辑
```

## ⚠️ 注意事项

### 安全考虑
- 外部服务运行在独立进程中，具有相同的系统权限
- 文件系统服务需要特别注意路径安全
- API Key等敏感信息使用环境变量管理

### 性能影响
- 外部服务启动需要额外时间
- 进程间通信会增加延迟
- 建议根据实际需求启用服务

### 兼容性
- 确保外部MCP服务支持JSON-RPC 2.0协议
- 不同版本的外部服务可能有API差异
- 建议定期更新外部服务版本

### 故障排除
1. **服务启动失败**: 检查命令是否可用、权限是否足够
2. **工具调用失败**: 检查参数格式、API Key配置
3. **连接超时**: 调整timeout设置
4. **进程异常退出**: 检查外部服务的错误日志

### 开发注意事项
1. **进程管理**：外部MCP服务运行在独立进程中，确保正确的清理
2. **端口分配**：使用LiteMCP的端口管理系统避免冲突
3. **错误处理**：外部服务可能不稳定，需要健壮的错误处理
4. **资源清理**：停止服务时确保所有相关进程都被正确终止
5. **日志记录**：保持详细的日志用于问题诊断

## 📚 扩展阅读

- [MCP协议官方文档](https://modelcontextprotocol.io/)
- [可用的MCP服务器列表](https://github.com/modelcontextprotocol/servers)
- [LiteMCP框架使用文档](../../../docs/USAGE.md)
- [外部MCP服务集成指南](../../../docs/EXTERNAL_MCP_GUIDE.md)

通过外部MCP服务集成功能，LiteMCP框架可以轻松复用社区已有的MCP工具，大大扩展了框架的能力范围。

*本文档描述了LiteMCP外部MCP服务管理器的设计和使用方法。如有问题或建议，请联系开发团队或通过fork贡献代码。*
