# LiteMCP 统计系统设计文档

## 概述

LiteMCP 统计系统提供了完整的作者信息和工具统计功能，支持装饰器标记、统计数据收集和报表生成。
**使用场景**：
- 服务器初始化时的标准流程
- 收集完整的服务器和工具信息
- 使用单一的@mcp_author装饰器标记所有作者信息

## 统计维度

### 1. 作者维度
- **姓名**：作者姓名（必填）
- **邮箱**：邮箱地址（可选）
- **部门**：所属部门（可选）
- **项目**：所属项目列表（可选），支持多个项目

### 2. 服务器维度
- 服务器数量、描述、工具数量
- 按作者、部门、项目分组统计

### 3. 工具维度
- 工具数量、描述、参数信息
- 按作者、部门、项目分组统计

### 4. 部门维度
- 部门贡献统计（服务器数量 + 工具数量）
- 部门内的作者统计

### 5. 项目维度
- 项目贡献统计（服务器数量 + 工具数量）
- 项目内的作者统计

## 使用示例

### 基础用法

```python
from src.core.statistics import statistics_manager, AuthorInfo

# 创建作者信息
author = AuthorInfo(name="张三", email="zhangsan@example.com", department="测试部", project="LiteMCP")

# 方式1：分步操作（推荐用于批量操作）
statistics_manager.register_server("MyServer", "MyServerClass", "my.module", "我的服务器", author)
statistics_manager.register_tool("MyServer", "my_tool", "我的工具", "my_tool", "my.module", ["param: str"], "str", author)
statistics_manager.save_statistics()  # 最后统一保存

# 方式2：立即保存（推荐用于单个操作）
statistics_manager.register_server_and_save("MyServer2", "MyServerClass2", "my.module2", "我的服务器2", author)
```

### 装饰器用法

```python
from src.core.statistics import mcp_author, collect_server_statistics

@mcp_author("张三", "zhangsan@example.com", department="测试部", project="LiteMCP")
class MyMCPServer(BaseMCPServer):
    def _register_tools(self):
        @self.mcp.tool()
        @mcp_author("李四", "lisi@example.com", department="开发部", project="LiteMCP")
        def my_tool(param: str) -> str:
            return f"处理: {param}"
        
        @self.mcp.tool()
        @mcp_author("王五", department="测试部", project="LiteMCP")
        def another_tool(param: int) -> int:
            return param * 2

        @self.mcp.tool()
        def inherited_tool(param: str) -> str:
            """这个工具会继承服务器的作者信息"""
            return f"继承: {param}"

# 在服务器初始化时自动收集统计信息
server = MyMCPServer()
# collect_server_statistics(server)  # 在BaseMCPServer中自动调用
```

### 装饰器参数说明

#### 统一作者装饰器
```python
@mcp_author(name, email=None, department=None, project=None)
```

**参数说明**：
- `name`: 作者姓名（必填）
- `email`: 邮箱地址（可选）
- `department`: 所属部门（可选）
- `project`: 所属项目列表（可选），支持字符串列表

**使用示例**：
```python
# 只指定姓名
@mcp_author("张三")

# 指定姓名和邮箱
@mcp_author("张三", "zhangsan@example.com")

# 指定姓名和部门
@mcp_author("张三", department="测试部")

# 指定单个项目
@mcp_author("张三", project=["LiteMCP"])

# 指定多个项目
@mcp_author("张三", project=["LiteMCP", "ProjectA"])

# 完整信息
@mcp_author("张三", "zhangsan@example.com", department="测试部", project=["LiteMCP", "ProjectA"])
```

### 作者信息继承规则

1. **工具级别装饰器优先**：如果工具函数有@mcp_author装饰器，使用工具的作者信息
2. **服务器级别继承**：如果工具函数没有@mcp_author装饰器，自动继承class层级的作者信息
3. **自动发现机制**：系统通过@self.mcp.tool()装饰器自动发现所有工具

**继承示例**：
```python
@mcp_author("张三", department="测试部", project="LiteMCP")
class MyServer(BaseMCPServer):
    def _register_tools(self):
        @self.mcp.tool()
        @mcp_author("李四", department="开发部")  # 工具使用自己的作者信息
        def tool_with_author(param: str) -> str:
            return param
        
        @self.mcp.tool()  # 工具继承服务器的作者信息（张三）
        def tool_inherit_author(param: str) -> str:
            return param
```

## API接口

### 基础统计查询
- `GET /api/v1/statistics/` - 获取统计概览
- `GET /api/v1/statistics/full` - 获取完整统计信息
- `GET /api/v1/statistics/servers` - 获取服务器统计
- `GET /api/v1/statistics/tools` - 获取工具统计
- `GET /api/v1/statistics/authors` - 获取作者统计

### 部门统计
- `GET /api/v1/statistics/departments` - 获取部门统计
- `GET /api/v1/statistics/departments/{department_name}` - 获取特定部门统计

### 项目统计
- `GET /api/v1/statistics/projects` - 获取项目统计
- `GET /api/v1/statistics/projects/{project_name}` - 获取特定项目统计
- `GET /api/v1/statistics/projects/{project_name}/servers` - 获取项目下的服务器
- `GET /api/v1/statistics/projects/{project_name}/tools` - 获取项目下的工具

### 详细查询
- `GET /api/v1/statistics/servers/{server_name}` - 获取特定服务器统计
- `POST /api/v1/statistics/servers/batch` - 批量获取服务器统计
- `GET /api/v1/statistics/tools/{tool_name}` - 获取特定工具统计
- `POST /api/v1/statistics/tools/batch` - 批量获取工具统计
- `GET /api/v1/statistics/authors/{author_name}` - 获取特定作者统计
- `POST /api/v1/statistics/authors/batch` - 批量获取作者统计

### 批量查询示例

#### 批量查询服务器
```bash
curl -X 'POST' \
  'http://localhost:9000/api/v1/statistics/servers/batch' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["LiteMCP-Example", "LiteMCP-School", "NonExistentServer"]'
```

#### 批量查询工具
```bash
curl -X 'POST' \
  'http://localhost:9000/api/v1/statistics/tools/batch' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["school_name", "students_number", "nonexistent_tool"]'
```

#### 批量查询作者
```bash
curl -X 'POST' \
  'http://localhost:9000/api/v1/statistics/authors/batch' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["魏兵cs", "周顺", "不存在的作者"]'
```

### 报表和管理
- `GET /api/v1/statistics/report` - 生成统计报表
- `POST /api/v1/statistics/refresh` - 刷新统计数据
- `POST /api/v1/statistics/rebuild` - 重建统计数据

## 数据持久化

### 文件位置
- 统计数据文件：`runtime/statistics.json`
- 日志文件：`runtime/logs/statistics.log`

### 数据结构
```json
{
  "servers": {
    "服务器名称": {
      "name": "服务器名称",
      "class_name": "服务器类名",
      "module": "模块名",
      "description": "描述",
      "author": {
        "name": "作者姓名",
        "email": "邮箱",
        "department": "部门",
        "project": "项目"
      },
      "tools": [...],
      "create_time": "创建时间",
      "last_update": "最后更新时间"
    }
  },
  "summary": {
    "total_servers": 5,
    "total_tools": 12,
    "total_authors": 3,
    "total_departments": 2,
    "total_projects": 2,
    "top_authors": [...],
    "departments": [...],
    "projects": [...]
  }
}
```

**注意**：统计系统采用统一的@mcp_author装饰器设计，支持服务器和工具的作者信息标记，工具可以继承服务器的作者信息，也可以使用自己的作者信息。 