import json
from typing import Any, Callable, Dict, Optional, List, Union
from contextlib import contextmanager
from src.core.statistics import mcp_author
from src.tools.base import BaseMCPServer
from operation_redis import OperationRedis


def make_response(code: int = 0, msg: str = "success", data: Any = None) -> dict:
    """Create standard response structure"""
    return {"code": code, "msg": msg, "data": data}



def json_response(result: dict) -> str:
    """Convert response result to JSON string"""
    return json.dumps(result, ensure_ascii=False, default=str)



def parse_keys(keys: Union[str, List[str]]) -> List[str]:
    """
    Parse keys parameter, supports multiple formats
    
    Args:
        keys: Keys parameter, supports following formats:
            - Comma-separated string: 'key1,key2,key3'
            - JSON array string: '["key1", "key2"]'
            - List: ['key1', 'key2']
    
    Returns:
        List of keys
    """
    if isinstance(keys, list):
        return [key.strip() for key in keys if key and key.strip()]
    
    if isinstance(keys, str):
        keys = keys.strip()
        if not keys:
            return []
        
        # Try to parse as JSON array
        if keys.startswith('['):
            try:
                parsed = json.loads(keys)
                if isinstance(parsed, list):
                    return [key.strip() for key in parsed if key and key.strip()]
            except json.JSONDecodeError:
                pass
        
        # Split by comma
        return [key.strip() for key in keys.split(',') if key.strip()]
    
    return []


@mcp_author("qianp", department="TestingDepartment", project=["DB"])
class RedisMCPServer(BaseMCPServer):
    """Redis database operation MCP server

    Features:
    - Get Redis keys and values
    - Execute Redis commands
    - Support for various Redis data types operations
    - Transaction support
    """

    def __init__(self, name: str = "LiteMCP-Redis"):
        super().__init__(name)

    @contextmanager
    def _get_redis_connection(self):
        """
        Get Redis connection instance (context manager)
        
        Usage:
            with self._get_redis_connection() as redis:
                result = redis.get(key)
        """
        headers = self.get_current_request()
        redis = None
        try:
            redis = OperationRedis(
                host=headers.get("redis-host", "localhost"),
                port=int(headers.get("redis-port", 9001)),
                db=int(headers.get("redis-db", 0)),
                password=headers.get("redis-password", None)
            )
            yield redis
        finally:
            if redis:
                redis.close()
    
    def _execute_with_response(
        self, 
        operation: Callable[[OperationRedis], Any],
        success_log: Optional[str] = None
    ) -> str:
        """
        Execute Redis operation and return standard response
        
        Args:
            operation: Operation function that receives Redis connection
            success_log: Log message on success
        
        Returns:
            JSON formatted response string
        """
        try:
            with self._get_redis_connection() as redis:
                data = operation(redis)
                result = make_response(data=data)
                if success_log:
                    self.logger.info(success_log)
                return json_response(result)
        except Exception as e:
            result = make_response(code=500, msg=f"Execution failed: {str(e)}")
            self.logger.error(f"Redis operation failed: {e}")
            return json_response(result)
    
    def _register_tools(self):
        """Register all tool functions"""

        @self.mcp.tool()
        def redis_get(key: str) -> str:
            """
            Get Redis string value
            
            Args:
                key: Redis key
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": value        # String value or null if key doesn't exist
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.get(key),
                f"get {key}"
            )

        @self.mcp.tool()
        def redis_set(key: str, value: Any, ex: Optional[int] = None) -> str:
            """
            Set Redis string value
            
            Args:
                key: Redis key
                value: Value to set
                ex: Expiration time in seconds (optional)
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": True         # Whether set was successful
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.set(key, value, ex=ex),
                f"set {key} {value}"
            )

        @self.mcp.tool()
        def redis_delete(key: str) -> str:
            """
            Delete Redis key
            
            Args:
                key: Redis key
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": count        # Number of keys deleted
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.delete(key),
                f"delete {key}"
            )

        @self.mcp.tool()
        def redis_exists(key: str) -> str:
            """
            Check if Redis key exists
            
            Args:
                key: Redis key
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": True         # Whether key exists
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.exists(key),
                f"exists {key}"
            )

        @self.mcp.tool()
        def redis_keys(pattern: str = "*") -> str:
            """
            Get all Redis keys matching pattern
            
            Args:
                pattern: Pattern to match (default: *)
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": [keys]       # List of matching keys
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.keys(pattern),
                f"keys {pattern}"
            )

        @self.mcp.tool()
        def redis_type(key: str) -> str:
            """
            Get Redis key type
            
            Args:
                key: Redis key
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": type         # Key type (string, hash, list, set, zset, etc.)
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.type(key),
                f"type {key}"
            )

        @self.mcp.tool()
        def redis_expire(key: str, seconds: int) -> str:
            """
            Set Redis key expiration time
            
            Args:
                key: Redis key
                seconds: Expiration time in seconds
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": True         # Whether expire was set successfully
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.expire(key, seconds),
                f"expire {key} {seconds}"
            )

        @self.mcp.tool()
        def redis_ttl(key: str) -> str:
            """
            Get Redis key remaining time to live
            
            Args:
                key: Redis key
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": ttl          # Remaining time in seconds, -1 if no expiration, -2 if key doesn't exist
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.ttl(key),
                f"ttl {key}"
            )

        @self.mcp.tool()
        def redis_incr(key: str, amount: int = 1) -> str:
            """
            Increment Redis integer value
            
            Args:
                key: Redis key
                amount: Amount to increment by (default: 1)
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": value        # New value after increment
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.incr(key, amount),
                f"incr {key} {amount}"
            )

        @self.mcp.tool()
        def redis_decr(key: str, amount: int = 1) -> str:
            """
            Decrement Redis integer value
            
            Args:
                key: Redis key
                amount: Amount to decrement by (default: 1)
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": value        # New value after decrement
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.decr(key, amount),
                f"decr {key} {amount}"
            )

        @self.mcp.tool()
        def redis_hget(name: str, key: str) -> str:
            """
            Get Redis hash field value
            
            Args:
                name: Hash name
                key: Field name
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": value        # Field value or null if field doesn't exist
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.hget(name, key),
                f"hget {name} {key}"
            )

        @self.mcp.tool()
        def redis_hgetall(name: str) -> str:
            """
            Get all Redis hash fields and values
            
            Args:
                name: Hash name
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": {fields}     # Dict of field-value pairs
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.hgetall(name),
                f"hgetall {name}"
            )

        @self.mcp.tool()
        def redis_hset(name: str, key: str, value: Any) -> str:
            """
            Set Redis hash field value
            
            Args:
                name: Hash name
                key: Field name
                value: Value to set
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": count        # Number of fields set
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.hset(name, key, value),
                f"hset {name} {key} {value}"
            )

        @self.mcp.tool()
        def redis_hkeys(name: str) -> str:
            """
            Get all Redis hash field names
            
            Args:
                name: Hash name
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": [keys]       # List of field names
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.hkeys(name),
                f"hkeys {name}"
            )

        @self.mcp.tool()
        def redis_lpush(name: str, values: List[Any]) -> str:
            """
            Push values to left of Redis list
            
            Args:
                name: List name
                values: List of values to push
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": length       # New length of list
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.lpush(name, *values),
                f"lpush {name} {values}"
            )

        @self.mcp.tool()
        def redis_rpush(name: str, values: List[Any]) -> str:
            """
            Push values to right of Redis list
            
            Args:
                name: List name
                values: List of values to push
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": length       # New length of list
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.rpush(name, *values),
                f"rpush {name} {values}"
            )

        @self.mcp.tool()
        def redis_lrange(name: str, start: int, end: int) -> str:
            """
            Get range of elements from Redis list
            
            Args:
                name: List name
                start: Start index
                end: End index
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": [elements]   # List of elements in range
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.lrange(name, start, end),
                f"lrange {name} {start} {end}"
            )

        @self.mcp.tool()
        def redis_sadd(name: str, values: List[Any]) -> str:
            """
            Add members to Redis set
            
            Args:
                name: Set name
                values: List of members to add
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": count        # Number of members added
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.sadd(name, *values),
                f"sadd {name} {values}"
            )

        @self.mcp.tool()
        def redis_smembers(name: str) -> str:
            """
            Get all members of Redis set
            
            Args:
                name: Set name
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": [members]    # List of set members
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.smembers(name),
                f"smembers {name}"
            )

        @self.mcp.tool()
        def redis_zadd(name: str, mapping: Dict[str, float]) -> str:
            """
            Add members to Redis sorted set with scores
            
            Args:
                name: Sorted set name
                mapping: Dict of member-score pairs
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": count        # Number of members added
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.zadd(name, mapping),
                f"zadd {name} {mapping}"
            )

        @self.mcp.tool()
        def redis_zrange(name: str, start: int, end: int, withscores: bool = False) -> str:
            """
            Get range of members from Redis sorted set by rank
            
            Args:
                name: Sorted set name
                start: Start rank
                end: End rank
                withscores: Whether to include scores (default: False)
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": [members]    # List of members or (member, score) tuples
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.zrange(name, start, end, withscores=withscores),
                f"zrange {name} {start} {end}"
            )

        @self.mcp.tool()
        def redis_execute_command(command: str, args: List[Any]) -> str:
            """
            Execute arbitrary Redis command
            
            Args:
                command: Redis command
                args: List of command arguments
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": result       # Command result
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.execute_command(command, *args),
                f"execute_command {command} {args}"
            )

        @self.mcp.tool()
        def redis_flushdb() -> str:
            """
            Flush current Redis database
            
            Returns:
                str: JSON string with structure:
                    {
                        "code": 0,           # 0 for success, non-zero for error
                        "msg": "success",    # Error or success message
                        "data": "OK"         # Result message
                    }
            """
            return self._execute_with_response(
                lambda redis: redis.flushdb(),
                "flushdb"
            )


redis_server = RedisMCPServer()

# 如果直接运行此文件，启动服务器
if __name__ == "__main__":
    # 支持所有传输模式：
    # example_server.run()
    server = redis_server
    server.run_http("0.0.0.0", 8087)  # HTTP模式
