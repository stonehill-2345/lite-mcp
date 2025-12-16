# MySQL Operation MCP Server

A Model Context Protocol (MCP) server for database operations, providing tools to execute SQL queries and retrieve database schema information.

## Features

- **Execute SQL Statements**: Support all SQL operations including SELECT, INSERT, UPDATE, DELETE, etc.
- **Get Table Names**: Retrieve list of all tables in the connected database
- **Get Table Schema**: Fetch detailed schema information for specified tables

## Tools

### 1. `operation_mysql`

Execute SQL statements on the connected database.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `sql` | string | Yes | SQL statement to execute |

**Response:**
```json
{
    "code": 0,
    "msg": "success",
    "data": "Query results or affected row count"
}
```

**Example:**
```sql
SELECT * FROM users WHERE status = 'active' LIMIT 10
```

---

### 2. `get_table_names`

Get a list of all table names in the database.

**Parameters:** None

**Response:**
```json
{
    "code": 0,
    "msg": "success",
    "data": [
        {"TABLE_NAME": "users", "TABLE_COMMENT": "User information"},
        {"TABLE_NAME": "orders", "TABLE_COMMENT": "Order records"}
    ]
}
```

---

### 3. `get_table_schema`

Get schema information for specified tables.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `table_names` | string | Yes | Table names in one of the following formats:<br>- Comma-separated: `'user,order,log'`<br>- JSON array: `'["user", "order"]'` |

**Response:**
```json
{
    "code": 0,
    "msg": "success",
    "data": [
        {
            "table_name": "users",
            "schema": [
                {"Field": "id", "Type": "int", "Null": "NO", "Key": "PRI", ...},
                {"Field": "name", "Type": "varchar(255)", "Null": "YES", ...}
            ]
        }
    ]
}
```

**Error Codes:**
| Code | Description |
|------|-------------|
| 1 | No valid table names provided |
| 2 | Failed to query schema for a table |
| 500 | System error |

## Configuration

Database connection is configured via HTTP headers:

| Header | Required | Default | Description |
|--------|----------|---------|-------------|
| `db-host` | Yes | - | Database host address |
| `db-port` | No | 3306 | Database port |
| `db-user` | Yes | - | Database username |
| `db-password` | Yes | - | Database password |
| `db-database` | Yes | - | Database name |

## Usage

### Running the Server

```python
from src.tools.operate_mysql.opmysql_server import Server

# Create server instance
server = Server(name="MyDBServer")

# Run in HTTP mode
server.run_http("0.0.0.0", 8087)
```

### Integration with LiteMCP

Add to your `servers.yaml` configuration:

```yaml
my_db_server:
  module: src.tools.operate_mysql.opmysql_server
  class: Server
  name: "MySQL-Server"
  transport: http
  host: "0.0.0.0"
  port: 8087
```

### Cursor MCP Configuration

Add to your Cursor `mcp.json` file (usually located at `~/.cursor/mcp.json`):

```json
{
  "my-db-server": {
    "url": "http://127.0.0.1:8087/mcp",
    "description": "MySQL Database Operations",
    "headers": {
      "db-host": "your-mysql-host.example.com",
      "db-port": "3306",
      "db-user": "your_username",
      "db-password": "your_password",
      "db-database": "your_database_name"
    }
  }
}
```

> **Note:** Replace the placeholder values with your actual database credentials.

## Response Format

All tools return a JSON string with the following structure:

```json
{
    "code": 0,           // 0 for success, non-zero for error
    "msg": "success",    // Error or success message
    "data": null         // Query results or null on error
}
```

## Author

- **Author**: qianp
- **Department**: TestingDepartment
- **Project**: DB

## License

This module is part of the LiteMCP project.

