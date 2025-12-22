import json
from typing import Any, Callable, Optional, List, Union
from contextlib import contextmanager
from src.core.statistics import mcp_author
from src.tools.base import BaseMCPServer
from operation_mysql import OperationMySQL


def make_response(code: int = 0, msg: str = "success", data: Any = None) -> dict:
    """Create standard response structure"""
    return {"code": code, "msg": msg, "data": data}


def json_response(result: dict) -> str:
    """Convert response result to JSON string"""
    return json.dumps(result, ensure_ascii=False, default=str)


def parse_table_names(table_names: Union[str, List[str]]) -> List[str]:
    """
    Parse table names parameter, supports multiple formats
    
    Args:
        table_names: Table names parameter, supports following formats:
            - Comma-separated string: 'user,order,log'
            - JSON array string: '["user", "order"]'
            - List: ['user', 'order']
    
    Returns:
        List of table names
    """
    if isinstance(table_names, list):
        return [name.strip() for name in table_names if name and name.strip()]
    
    if isinstance(table_names, str):
        table_names = table_names.strip()
        if not table_names:
            return []
        
        # Try to parse as JSON array
        if table_names.startswith('['):
            try:
                parsed = json.loads(table_names)
                if isinstance(parsed, list):
                    return [name.strip() for name in parsed if name and name.strip()]
            except json.JSONDecodeError:
                pass
        
        # Split by comma
        return [name.strip() for name in table_names.split(',') if name.strip()]
    
    return []


@mcp_author("qianp", department="TestingDepartment", project=["DB"])
class Server(BaseMCPServer):
    """Database operation MCP server

    Features:
    - Get database table schema information
    - Query database table data
    - Execute SQL queries
    """

    def __init__(self, name: str = "LiteMCP-Db"):
        super().__init__(name)

    @contextmanager
    def _get_db_connection(self):
        """
        Get database connection instance (context manager)
        
        Usage:
            with self._get_db_connection() as db:
                result = db.execute_query(sql)
        """
        headers = self.get_current_request()
        db = None
        try:
            db = OperationMySQL(
                host=headers.get("db-host"),
                port=int(headers.get("db-port", 3306)),
                user=headers.get("db-user"),
                password=headers.get("db-password"),
                database=headers.get("db-database")
            )
            yield db
        finally:
            if db:
                db.close()
    
    def _execute_with_response(
        self, 
        operation: Callable[[OperationMySQL], Any],
        success_log: Optional[str] = None
    ) -> str:
        """
        Execute database operation and return standard response
        
        Args:
            operation: Operation function that receives db connection
            success_log: Log message on success
        
        Returns:
            JSON formatted response string
        """
        try:
            with self._get_db_connection() as db:
                data = operation(db)
                result = make_response(data=data)
                if success_log:
                    self._logger.info(success_log)
                return json_response(result)
        except Exception as e:
            result = make_response(code=500, msg=f"Execution failed: {str(e)}")
            self._logger.error(f"Database operation failed: {e}")
            return json_response(result)
    
    def _register_tools(self):
        """Register all tool functions"""

        @self.mcp.tool()
        def operation_mysql(sql: str) -> str:
            """
            Execute SQL statement (supports all SQL operations including SELECT, INSERT, UPDATE, DELETE, etc.)
            
            Args:
                sql (str): SQL statement
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": result       # Query results or affected row count
                    }
            """
            sql_preview = sql[:100] + "..." if len(sql) > 100 else sql
            return self._execute_with_response(
                lambda db: db.query_sql(sql),
                f"SQL executed successfully: {sql_preview}"
            )

        @self.mcp.tool()
        def get_table_names() -> str:
            """
            Get list of table names in the database
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": [            # Table name list
                            {"TABLE_NAME": "table_name", "TABLE_COMMENT": "comment"},
                            ...
                        ]
                    }
            """
            def _get_tables(db: OperationMySQL):
                tables = db.get_table_names()
                self._logger.info(f"Successfully retrieved {len(tables)} tables")
                return tables
            
            return self._execute_with_response(_get_tables)

        @self.mcp.tool()
        def get_table_schema(table_names: str) -> str:
            """
            Get schema information for specified tables
            
            Args:
                table_names (str): Table names, supports following formats:
                    - Comma-separated string, e.g. 'user,order,log'
                    - JSON array string, e.g. '["user", "order"]'
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": [            # Table schema list
                            {
                                "table_name": "name",
                                "schema": [field info list]
                            },
                            ...
                        ]
                    }
                Error codes:
                    1 - No valid table names provided
                    2 - Failed to query schema for a table
                    500 - System error
            """
            # Pre-parse table names
            table_list = parse_table_names(table_names)
            
            if not table_list:
                result = make_response(code=1, msg="No valid table names provided")
                return json_response(result)
            
            def _get_schemas(db: OperationMySQL):
                tables_info = []
                for table_name in table_list:
                    schema = db.get_table_schema(table_name)
                    if not schema:
                        raise ValueError(f"Table {table_name} does not exist or query failed")
                    tables_info.append({"table_name": table_name, "schema": schema})
                    self._logger.info(f"Successfully retrieved schema for: {table_name}")
                
                self._logger.info(f"Schema retrieval complete, processed {len(tables_info)} tables")
                return tables_info
            
            return self._execute_with_response(_get_schemas)

mouse_server = Server()

if __name__ == "__main__":
    mouse_server.run()