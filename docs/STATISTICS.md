# TestMCP Statistics System Design Document

## Overview

The TestMCP Statistics System provides comprehensive author information and tool statistics functionality, supporting decorator marking, statistics data collection, and report generation.
**Use Cases**:
- Standard process during server initialization
- Collect complete server and tool information
- Use a single @mcp_author decorator to mark all author information

## Statistical Dimensions

### 1. Author Dimension
- **Name**: Author name (required)
- **Email**: Email address (optional)
- **Department**: Department affiliation (optional)
- **Project**: Project list (optional), supports multiple projects

### 2. Server Dimension
- Server count, description, tool count
- Statistics grouped by author, department, project

### 3. Tool Dimension
- Tool count, description, parameter information
- Statistics grouped by author, department, project

### 4. Department Dimension
- Department contribution statistics (server count + tool count)
- Author statistics within departments

### 5. Project Dimension
- Project contribution statistics (server count + tool count)
- Author statistics within projects

## Usage Examples

### Basic Usage

```python
from src.core.statistics import statistics_manager, AuthorInfo

# Create author information
author = AuthorInfo(name="John Doe", email="johndoe@example.com", department="Testing", project="TestMCP")

# Method 1: Step-by-step operations (recommended for batch operations)
statistics_manager.register_server("MyServer", "MyServerClass", "my.module", "My Server", author)
statistics_manager.register_tool("MyServer", "my_tool", "My Tool", "my_tool", "my.module", ["param: str"], "str", author)
statistics_manager.save_statistics()  # Save all at once

# Method 2: Immediate save (recommended for single operations)
statistics_manager.register_server_and_save("MyServer2", "MyServerClass2", "my.module2", "My Server 2", author)
```

### Decorator Usage

```python
from src.core.statistics import mcp_author, collect_server_statistics

@mcp_author("John Doe", "johndoe@example.com", department="Testing", project="TestMCP")
class MyMCPServer(BaseMCPServer):
    def _register_tools(self):
        @self.mcp.tool()
        @mcp_author("Jane Smith", "janesmith@example.com", department="Development", project="TestMCP")
        def my_tool(param: str) -> str:
            return f"Processed: {param}"
        
        @self.mcp.tool()
        @mcp_author("Bob Wilson", department="Testing", project="TestMCP")
        def another_tool(param: int) -> int:
            return param * 2

        @self.mcp.tool()
        def inherited_tool(param: str) -> str:
            """This tool will inherit the server's author information"""
            return f"Inherited: {param}"

# Automatically collect statistics during server initialization
server = MyMCPServer()
# collect_server_statistics(server)  # Automatically called in BaseMCPServer
```

### Decorator Parameter Description

#### Unified Author Decorator
```python
@mcp_author(name, email=None, department=None, project=None)
```

**Parameter Description**:
- `name`: Author name (required)
- `email`: Email address (optional)
- `department`: Department affiliation (optional)
- `project`: Project list (optional), supports string list

**Usage Examples**:
```python
# Only specify name
@mcp_author("John Doe")

# Specify name and email
@mcp_author("John Doe", "johndoe@example.com")

# Specify name and department
@mcp_author("John Doe", department="Testing")

# Specify single project
@mcp_author("John Doe", project=["TestMCP"])

# Specify multiple projects
@mcp_author("John Doe", project=["TestMCP", "ProjectA"])

# Complete information
@mcp_author("John Doe", "johndoe@example.com", department="Testing", project=["TestMCP", "ProjectA"])
```

### Author Information Inheritance Rules

1. **Tool-level decorator priority**: If a tool function has @mcp_author decorator, use the tool's author information
2. **Server-level inheritance**: If a tool function doesn't have @mcp_author decorator, automatically inherit the class-level author information
3. **Auto-discovery mechanism**: System automatically discovers all tools through @self.mcp.tool() decorator

**Inheritance Example**:
```python
@mcp_author("John Doe", department="Testing", project="TestMCP")
class MyServer(BaseMCPServer):
    def _register_tools(self):
        @self.mcp.tool()
        @mcp_author("Jane Smith", department="Development")  # Tool uses its own author information
        def tool_with_author(param: str) -> str:
            return param
        
        @self.mcp.tool()  # Tool inherits server's author information (John Doe)
        def tool_inherit_author(param: str) -> str:
            return param
```

## API Interfaces

### Basic Statistics Queries
- `GET /api/v1/statistics/` - Get statistics overview
- `GET /api/v1/statistics/full` - Get complete statistics information
- `GET /api/v1/statistics/servers` - Get server statistics
- `GET /api/v1/statistics/tools` - Get tool statistics
- `GET /api/v1/statistics/authors` - Get author statistics

### Department Statistics
- `GET /api/v1/statistics/departments` - Get department statistics
- `GET /api/v1/statistics/departments/{department_name}` - Get specific department statistics

### Project Statistics
- `GET /api/v1/statistics/projects` - Get project statistics
- `GET /api/v1/statistics/projects/{project_name}` - Get specific project statistics
- `GET /api/v1/statistics/projects/{project_name}/servers` - Get servers under the project
- `GET /api/v1/statistics/projects/{project_name}/tools` - Get tools under the project

### Detailed Queries
- `GET /api/v1/statistics/servers/{server_name}` - Get specific server statistics
- `POST /api/v1/statistics/servers/batch` - Batch get server statistics
- `GET /api/v1/statistics/tools/{tool_name}` - Get specific tool statistics
- `POST /api/v1/statistics/tools/batch` - Batch get tool statistics
- `GET /api/v1/statistics/authors/{author_name}` - Get specific author statistics
- `POST /api/v1/statistics/authors/batch` - Batch get author statistics

### Batch Query Examples

#### Batch Query Servers
```bash
curl -X 'POST' \
  'http://localhost:9000/api/v1/statistics/servers/batch' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["TestMCP-Example", "TestMCP-School", "NonExistentServer"]'
```

#### Batch Query Tools
```bash
curl -X 'POST' \
  'http://localhost:9000/api/v1/statistics/tools/batch' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["school_name", "students_number", "nonexistent_tool"]'
```

#### Batch Query Authors
```bash
curl -X 'POST' \
  'http://localhost:9000/api/v1/statistics/authors/batch' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["Wei Bing", "Zhou Shun", "NonExistentAuthor"]'
```

### Reports and Management
- `GET /api/v1/statistics/report` - Generate statistics report
- `POST /api/v1/statistics/refresh` - Refresh statistics data
- `POST /api/v1/statistics/rebuild` - Rebuild statistics data

## Data Persistence

### File Locations
- Statistics data file: `runtime/statistics.json`
- Log file: `runtime/logs/statistics.log`

### Data Structure
```json
{
  "servers": {
    "ServerName": {
      "name": "Server Name",
      "class_name": "Server Class Name",
      "module": "Module Name",
      "description": "Description",
      "author": {
        "name": "Author Name",
        "email": "Email",
        "department": "Department",
        "project": "Project"
      },
      "tools": [...],
      "create_time": "Creation Time",
      "last_update": "Last Update Time"
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

**Note**: The statistics system adopts a unified @mcp_author decorator design, supporting author information marking for servers and tools. Tools can inherit server author information or use their own author information. 