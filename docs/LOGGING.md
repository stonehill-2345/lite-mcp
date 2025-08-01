# TestMCP 日志系统使用指南

## 🎯 概览

TestMCP 采用统一的日志管理系统，提供结构化、可配置的日志记录功能。系统支持分级日志、文件轮转、彩色输出等特性。

## 📋 特性

- ✅ **分级日志输出**：DEBUG, INFO, WARNING, ERROR, CRITICAL
- ✅ **双重输出**：同时输出到控制台和文件
- ✅ **彩色控制台**：不同级别使用不同颜色，便于快速识别
- ✅ **自动轮转**：日志文件达到 10MB 自动轮转，保留 5 个历史文件
- ✅ **模块化记录器**：每个模块可使用独立的日志记录器
- ✅ **性能监控**：支持函数执行时间监控
- ✅ **环境变量配置**：通过 `TESTMCP_LOG_LEVEL` 控制日志级别

## 🚀 基础使用

### 1. 简单日志记录

```python
from src.core.logger import get_logger

# 获取记录器
logger = get_logger("my_module")

# 记录不同级别的日志
logger.debug("这是调试信息")
logger.info("这是信息日志")
logger.warning("这是警告日志")
logger.error("这是错误日志")
logger.critical("这是严重错误日志")

# 记录异常（包含堆栈跟踪）
try:
    # 一些操作
    pass
except Exception as e:
    logger.exception("操作失败")
```

### 2. 使用 LoggerMixin

```python
from src.core.logger import LoggerMixin

class MyClass(LoggerMixin):
    def __init__(self):
        super().__init__()
    
    def my_method(self):
        self.logger.info("执行我的方法")
        try:
            # 一些操作
            self.logger.debug("操作成功")
        except Exception as e:
            self.logger.error(f"操作失败: {e}")
```

### 3. 便捷函数

```python
from src.core.logger import info, warning, error, debug, critical

# 直接使用便捷函数
info("这是信息日志")
warning("这是警告日志")
error("这是错误日志")
```

## ⚙️ 高级功能

### 1. 自定义日志记录器

```python
from src.core.logger import get_logger

# 创建专用记录器
logger = get_logger(
    name="my_custom_logger",
    log_file="custom.log",          # 自定义日志文件名
    console_output=True,            # 是否输出到控制台
    file_output=True                # 是否输出到文件
)
```

### 2. 性能监控装饰器

```python
from src.core.logger import log_performance

@log_performance
def time_consuming_function():
    import time
    time.sleep(1)
    return "完成"

# 自动记录执行时间
result = time_consuming_function()
```

### 3. 临时日志级别

```python
from src.core.logger import TemporaryLogLevel, get_logger

logger = get_logger()

# 正常日志级别
logger.info("这会显示")

# 临时提高日志级别
with TemporaryLogLevel("ERROR"):
    logger.info("这不会显示")
    logger.error("这会显示")

# 恢复正常日志级别
logger.info("这又会显示了")
```

### 4. 日志系统初始化

```python
from src.core.logger import init_logging

# 初始化日志系统
logger = init_logging(
    level="DEBUG",              # 日志级别
    console_output=True,        # 控制台输出
    file_output=True           # 文件输出
)
```

## 📁 日志文件组织

日志文件存储在 `runtime/logs/` 目录下：

```
runtime/logs/
├── testmcp.log                    # 主日志文件
├── testmcp.cli.log               # CLI 日志
├── registry.log                  # 注册表日志
├── api_server.log                # API 服务器日志
├── example_server.log            # Example 服务器日志
├── school_server.log             # School 服务器日志
└── performance.*.log             # 性能监控日志
```

## 🎨 日志格式

### 控制台格式（简洁）
```
14:33:46 [INFO] testmcp.cli: TestMCP CLI 启动，日志级别: DEBUG
14:33:46 [DEBUG] testmcp.cli: 列出可用的服务器
```

### 文件格式（详细）
```
2025-06-13 14:33:46 [INFO] testmcp.cli:322 - main(): TestMCP CLI 启动，日志级别: DEBUG
2025-06-13 14:33:46 [DEBUG] testmcp.cli:38 - list_servers(): 列出可用的服务器
```

## 🎯 日志级别说明

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| **DEBUG** | 详细的调试信息，仅在开发时使用 | 函数调用、变量值、执行流程 |
| **INFO** | 一般信息，程序正常运行的关键节点 | 服务器启动、配置加载、操作完成 |
| **WARNING** | 警告信息，程序可以继续运行但需要注意 | 配置缺失、重试操作、非严重错误 |
| **ERROR** | 错误信息，程序遇到错误但可以继续 | 操作失败、连接错误、处理异常 |
| **CRITICAL** | 严重错误，程序可能无法继续运行 | 系统故障、资源耗尽、致命错误 |

## 🔧 配置选项

### 环境变量

```bash
# 设置全局日志级别
export TESTMCP_LOG_LEVEL=DEBUG

# 在具体命令中使用
python src/cli.py --log-level DEBUG list
```

### 命令行参数

```bash
# CLI 命令支持日志级别参数
python src/cli.py --log-level DEBUG serve --server example
python src/cli.py api --log-level INFO --host 0.0.0.0 --port 9000
```

## 📊 日志轮转

- **文件大小限制**：单个日志文件最大 10MB
- **保留文件数量**：最多保留 5 个历史文件
- **轮转规则**：
  ```
  testmcp.log          # 当前日志文件
  testmcp.log.1        # 第一个轮转文件
  testmcp.log.2        # 第二个轮转文件
  testmcp.log.3        # 第三个轮转文件
  testmcp.log.4        # 第四个轮转文件
  testmcp.log.5        # 第五个轮转文件（最老，会被删除）
  ```

## 🎨 彩色输出

控制台日志使用 ANSI 颜色代码：

- 🔵 **DEBUG**：青色
- 🟢 **INFO**：绿色  
- 🟡 **WARNING**：黄色
- 🔴 **ERROR**：红色
- 🟣 **CRITICAL**：紫色

## 📝 最佳实践

### 1. 模块级日志记录器

```python
# 每个模块创建自己的记录器
logger = get_logger(f"testmcp.{__name__}")
```

### 2. 错误处理中的日志

```python
try:
    # 危险操作
    pass
except SpecificException as e:
    logger.warning(f"特定异常: {e}")
    # 继续执行
except Exception as e:
    logger.exception("未知错误")
    # 重新抛出或处理
    raise
```

### 3. 结构化日志信息

```python
# 好的做法：包含上下文信息
logger.info(f"用户 {user_id} 执行操作 {operation} 成功")

# 避免：缺少上下文
logger.info("操作成功")
```

### 4. 合适的日志级别

```python
# 调试信息
logger.debug(f"处理参数: {params}")

# 正常流程
logger.info("服务器启动成功")

# 警告情况
logger.warning("配置文件不存在，使用默认配置")

# 错误处理
logger.error(f"连接数据库失败: {error}")

# 严重问题
logger.critical("内存不足，程序即将退出")
```

## 🔍 调试技巧

### 1. 查看实时日志

```bash
# 查看所有日志
tail -f runtime/logs/*.log

# 查看特定服务器日志
tail -f runtime/logs/example_server.log

# 查看主日志
tail -f runtime/logs/testmcp.log
```

### 2. 搜索日志

```bash
# 搜索错误日志
grep "ERROR" runtime/logs/*.log

# 搜索特定时间的日志
grep "2025-06-13 14:" runtime/logs/testmcp.log

# 搜索特定模块的日志
grep "testmcp.cli" runtime/logs/*.log
```

### 3. 临时调试

```python
# 临时启用详细日志
with TemporaryLogLevel("DEBUG"):
    # 执行需要调试的代码
    problematic_function()
```

## 🚨 注意事项

1. **避免在循环中大量日志输出**，可能影响性能
2. **敏感信息**（密码、密钥）不要记录到日志中
3. **生产环境**建议使用 INFO 或 WARNING 级别
4. **开发环境**可以使用 DEBUG 级别获取详细信息
5. **定期清理**旧的日志文件以节省磁盘空间

## 📚 API 参考

### get_logger()

```python
def get_logger(name: str = "testmcp", 
               log_file: Optional[str] = None,
               console_output: bool = True,
               file_output: bool = True) -> logging.Logger
```

### init_logging()

```python
def init_logging(level: str = "INFO", 
                console_output: bool = True,
                file_output: bool = True) -> logging.Logger
```

### log_performance()

```python
@log_performance
def my_function():
    # 自动记录执行时间
    pass
```

### TemporaryLogLevel

```python
with TemporaryLogLevel("DEBUG"):
    # 临时改变日志级别
    pass
``` 