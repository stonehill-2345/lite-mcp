import redis
import threading
import logging
import time
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Union, Tuple, Callable

logger = logging.getLogger(__name__)

# Default configuration constants
DEFAULT_CHARSET = 'utf-8'
DEFAULT_CONNECT_TIMEOUT = 10
DEFAULT_READ_TIMEOUT = 30
DEFAULT_WRITE_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_SLOW_QUERY_THRESHOLD = 1.0  # Slow query threshold (seconds)


class RedisConnectionError(Exception):
    """Redis connection error"""
    pass


class RedisOperationError(Exception):
    """Redis operation error"""
    pass


class OperationRedis:
    """
    Redis database operation class
    
    Features:
    - Auto-reconnect mechanism
    - Slow query logging
    - Transaction support
    - Context manager support
    - Support for common Redis operations
    """

    def __init__(
        self, 
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        charset: str = DEFAULT_CHARSET,
        connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: int = DEFAULT_READ_TIMEOUT,
        write_timeout: int = DEFAULT_WRITE_TIMEOUT,
        slow_query_threshold: float = DEFAULT_SLOW_QUERY_THRESHOLD
    ):
        """
        Initialize Redis connection

        Args:
            host: Redis host
            port: Redis port
            db: Redis database index
            password: Redis password
            charset: Character set, default utf-8
            connect_timeout: Connection timeout (seconds)
            read_timeout: Read timeout (seconds)
            write_timeout: Write timeout (seconds)
            slow_query_threshold: Slow query threshold (seconds)
        """
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._slow_query_threshold = slow_query_threshold

        # Connection parameters
        self._connection_params = {
            'host': host,
            'port': port,
            'db': db,
            'password': password,
            'decode_responses': True,
            'encoding': charset,
            'socket_connect_timeout': connect_timeout,
            'socket_timeout': max(read_timeout, write_timeout)
        }

        self._connection: Optional[redis.Redis] = None
        self._lock = threading.Lock()

        # Initialize connection
        self._ensure_connection()

    def _ensure_connection(self) -> None:
        """Ensure Redis connection is valid"""
        try:
            if self._connection is None:
                self._connection = redis.Redis(**self._connection_params)
            # Test if connection is valid
            self._connection.ping()
        except Exception as e:
            logger.error(f"Redis connection failed: {str(e)}")
            raise RedisConnectionError(f"Unable to connect to Redis server: {str(e)}")

    def _execute_with_retry(
        self, 
        operation: Callable[[], Any], 
        operation_name: str = "",
        max_retries: int = DEFAULT_MAX_RETRIES
    ) -> Any:
        """
        Execute operation with retry mechanism and slow query logging

        Args:
            operation: Callable operation function, no parameters, returns operation result
            operation_name: Operation name (for logging)
            max_retries: Maximum number of retries

        Returns:
            Operation result
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                with self._lock:
                    self._ensure_connection()
                    
                    # Record execution time
                    start_time = time.time()
                    result = operation()
                    elapsed_time = time.time() - start_time
                    
                    # Slow query logging
                    if elapsed_time > self._slow_query_threshold:
                        logger.warning(f"Slow Redis operation ({elapsed_time:.2f}s): {operation_name}")
                    
                    return result
                    
            except (redis.RedisError, RedisConnectionError) as e:
                last_error = e
                
                if attempt < max_retries - 1:
                    wait_time = 0.5 * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Redis operation failed, retrying in {wait_time:.1f}s ({attempt + 1}/{max_retries}): {str(e)}")
                    time.sleep(wait_time)
                    self._reconnect()
                    
        logger.error(f"Redis operation failed after {max_retries} retries: {str(last_error)}")
        raise RedisOperationError(f"Operation failed: {str(last_error)}")
    
    def _reconnect(self) -> None:
        """Re-establish Redis connection"""
        self._close_quietly()
        self._connection = None
    
    def _close_quietly(self) -> None:
        """Close connection quietly (without raising exceptions)"""
        try:
            if self._connection:
                self._connection.close()
        except Exception:
            pass

    @contextmanager
    def pipeline(self):
        """Pipeline context manager for Redis"""
        try:
            pipeline = self._connection.pipeline()
            yield pipeline
            result = pipeline.execute()
            logger.debug(f"Pipeline executed successfully, result: {result}")
            return result
        except Exception as e:
            logger.error(f"Pipeline execution failed: {str(e)}")
            raise

    # Key operations
    def exists(self, key: str) -> bool:
        """
        Check if key exists
        
        Args:
            key: Redis key
            
        Returns:
            Whether key exists
        """
        return bool(self._execute_with_retry(lambda: self._connection.exists(key), f"exists {key}"))

    def delete(self, key: str) -> int:
        """
        Delete key
        
        Args:
            key: Redis key
            
        Returns:
            Number of keys deleted
        """
        return int(self._execute_with_retry(lambda: self._connection.delete(key), f"delete {key}"))

    def expire(self, key: str, seconds: int) -> bool:
        """
        Set key expiration time
        
        Args:
            key: Redis key
            seconds: Expiration time in seconds
            
        Returns:
            Whether the expire was set
        """
        return bool(self._execute_with_retry(lambda: self._connection.expire(key, seconds), f"expire {key} {seconds}"))

    def ttl(self, key: str) -> int:
        """
        Get key remaining time to live
        
        Args:
            key: Redis key
            
        Returns:
            Remaining time in seconds, -1 if key exists but has no expiration, -2 if key does not exist
        """
        return int(self._execute_with_retry(lambda: self._connection.ttl(key), f"ttl {key}"))

    def keys(self, pattern: str = "*") -> List[str]:
        """
        Get all keys matching pattern
        
        Args:
            pattern: Pattern to match
            
        Returns:
            List of matching keys
        """
        return list(self._execute_with_retry(lambda: self._connection.keys(pattern), f"keys {pattern}"))

    def type(self, key: str) -> str:
        """
        Get key type
        
        Args:
            key: Redis key
            
        Returns:
            Key type
        """
        return str(self._execute_with_retry(lambda: self._connection.type(key), f"type {key}"))

    # String operations
    def get(self, key: str) -> Optional[str]:
        """
        Get string value
        
        Args:
            key: Redis key
            
        Returns:
            String value or None if key does not exist
        """
        return self._execute_with_retry(lambda: self._connection.get(key), f"get {key}")

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        Set string value
        
        Args:
            key: Redis key
            value: Value to set
            ex: Expiration time in seconds
            
        Returns:
            Whether the set was successful
        """
        return bool(self._execute_with_retry(lambda: self._connection.set(key, value, ex=ex), f"set {key} {value}"))

    def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment integer value
        
        Args:
            key: Redis key
            amount: Amount to increment by
            
        Returns:
            New value after increment
        """
        return int(self._execute_with_retry(lambda: self._connection.incr(key, amount), f"incr {key} {amount}"))

    def decr(self, key: str, amount: int = 1) -> int:
        """
        Decrement integer value
        
        Args:
            key: Redis key
            amount: Amount to decrement by
            
        Returns:
            New value after decrement
        """
        return int(self._execute_with_retry(lambda: self._connection.decr(key, amount), f"decr {key} {amount}"))

    # Hash operations
    def hget(self, name: str, key: str) -> Optional[str]:
        """
        Get hash field value
        
        Args:
            name: Hash name
            key: Field name
            
        Returns:
            Field value or None if field does not exist
        """
        return self._execute_with_retry(lambda: self._connection.hget(name, key), f"hget {name} {key}")

    def hgetall(self, name: str) -> Dict[str, str]:
        """
        Get all hash fields and values
        
        Args:
            name: Hash name
            
        Returns:
            Dict of field-value pairs
        """
        return dict(self._execute_with_retry(lambda: self._connection.hgetall(name), f"hgetall {name}"))

    def hset(self, name: str, key: str, value: Any) -> int:
        """
        Set hash field value
        
        Args:
            name: Hash name
            key: Field name
            value: Value to set
            
        Returns:
            Number of fields set
        """
        return int(self._execute_with_retry(lambda: self._connection.hset(name, key, value), f"hset {name} {key} {value}"))

    def hdel(self, name: str, *keys: str) -> int:
        """
        Delete hash fields
        
        Args:
            name: Hash name
            keys: Field names to delete
            
        Returns:
            Number of fields deleted
        """
        return int(self._execute_with_retry(lambda: self._connection.hdel(name, *keys), f"hdel {name} {keys}"))

    def hkeys(self, name: str) -> List[str]:
        """
        Get all hash field names
        
        Args:
            name: Hash name
            
        Returns:
            List of field names
        """
        return list(self._execute_with_retry(lambda: self._connection.hkeys(name), f"hkeys {name}"))

    def hvals(self, name: str) -> List[str]:
        """
        Get all hash field values
        
        Args:
            name: Hash name
            
        Returns:
            List of field values
        """
        return list(self._execute_with_retry(lambda: self._connection.hvals(name), f"hvals {name}"))

    def hexists(self, name: str, key: str) -> bool:
        """
        Check if hash field exists
        
        Args:
            name: Hash name
            key: Field name
            
        Returns:
            Whether field exists
        """
        return bool(self._execute_with_retry(lambda: self._connection.hexists(name, key), f"hexists {name} {key}"))

    # List operations
    def lpush(self, name: str, *values: Any) -> int:
        """
        Push values to left of list
        
        Args:
            name: List name
            values: Values to push
            
        Returns:
            New length of list
        """
        return int(self._execute_with_retry(lambda: self._connection.lpush(name, *values), f"lpush {name} {values}"))

    def rpush(self, name: str, *values: Any) -> int:
        """
        Push values to right of list
        
        Args:
            name: List name
            values: Values to push
            
        Returns:
            New length of list
        """
        return int(self._execute_with_retry(lambda: self._connection.rpush(name, *values), f"rpush {name} {values}"))

    def lpop(self, name: str) -> Optional[str]:
        """
        Pop value from left of list
        
        Args:
            name: List name
            
        Returns:
            Popped value or None if list is empty
        """
        return self._execute_with_retry(lambda: self._connection.lpop(name), f"lpop {name}")

    def rpop(self, name: str) -> Optional[str]:
        """
        Pop value from right of list
        
        Args:
            name: List name
            
        Returns:
            Popped value or None if list is empty
        """
        return self._execute_with_retry(lambda: self._connection.rpop(name), f"rpop {name}")

    def lrange(self, name: str, start: int, end: int) -> List[str]:
        """
        Get range of list elements
        
        Args:
            name: List name
            start: Start index
            end: End index
            
        Returns:
            List of elements in range
        """
        return list(self._execute_with_retry(lambda: self._connection.lrange(name, start, end), f"lrange {name} {start} {end}"))

    def llen(self, name: str) -> int:
        """
        Get length of list
        
        Args:
            name: List name
            
        Returns:
            Length of list
        """
        return int(self._execute_with_retry(lambda: self._connection.llen(name), f"llen {name}"))

    # Set operations
    def sadd(self, name: str, *values: Any) -> int:
        """
        Add members to set
        
        Args:
            name: Set name
            values: Members to add
            
        Returns:
            Number of members added
        """
        return int(self._execute_with_retry(lambda: self._connection.sadd(name, *values), f"sadd {name} {values}"))

    def srem(self, name: str, *values: Any) -> int:
        """
        Remove members from set
        
        Args:
            name: Set name
            values: Members to remove
            
        Returns:
            Number of members removed
        """
        return int(self._execute_with_retry(lambda: self._connection.srem(name, *values), f"srem {name} {values}"))

    def smembers(self, name: str) -> List[str]:
        """
        Get all members of set
        
        Args:
            name: Set name
            
        Returns:
            List of set members
        """
        return list(self._execute_with_retry(lambda: self._connection.smembers(name), f"smembers {name}"))

    def sismember(self, name: str, value: Any) -> bool:
        """
        Check if value is member of set
        
        Args:
            name: Set name
            value: Value to check
            
        Returns:
            Whether value is member
        """
        return bool(self._execute_with_retry(lambda: self._connection.sismember(name, value), f"sismember {name} {value}"))

    def scard(self, name: str) -> int:
        """
        Get cardinality of set
        
        Args:
            name: Set name
            
        Returns:
            Number of members in set
        """
        return int(self._execute_with_retry(lambda: self._connection.scard(name), f"scard {name}"))

    # Sorted set operations
    def zadd(self, name: str, mapping: Dict[str, float]) -> int:
        """
        Add members to sorted set with scores
        
        Args:
            name: Sorted set name
            mapping: Dict of member-score pairs
            
        Returns:
            Number of members added
        """
        return int(self._execute_with_retry(lambda: self._connection.zadd(name, mapping), f"zadd {name} {mapping}"))

    def zrem(self, name: str, *values: Any) -> int:
        """
        Remove members from sorted set
        
        Args:
            name: Sorted set name
            values: Members to remove
            
        Returns:
            Number of members removed
        """
        return int(self._execute_with_retry(lambda: self._connection.zrem(name, *values), f"zrem {name} {values}"))

    def zrange(self, name: str, start: int, end: int, withscores: bool = False) -> Union[List[str], List[Tuple[str, float]]]:
        """
        Get range of members from sorted set by rank
        
        Args:
            name: Sorted set name
            start: Start rank
            end: End rank
            withscores: Whether to include scores
            
        Returns:
            List of members or (member, score) tuples
        """
        return list(self._execute_with_retry(lambda: self._connection.zrange(name, start, end, withscores=withscores), f"zrange {name} {start} {end}"))

    def zrank(self, name: str, value: Any) -> Optional[int]:
        """
        Get rank of member in sorted set
        
        Args:
            name: Sorted set name
            value: Member to get rank for
            
        Returns:
            Rank or None if member does not exist
        """
        return self._execute_with_retry(lambda: self._connection.zrank(name, value), f"zrank {name} {value}")

    def zcard(self, name: str) -> int:
        """
        Get cardinality of sorted set
        
        Args:
            name: Sorted set name
            
        Returns:
            Number of members in sorted set
        """
        return int(self._execute_with_retry(lambda: self._connection.zcard(name), f"zcard {name}"))

    # Generic operations
    def execute_command(self, *args: Any) -> Any:
        """
        Execute arbitrary Redis command
        
        Args:
            args: Command and arguments
            
        Returns:
            Command result
        """
        return self._execute_with_retry(lambda: self._connection.execute_command(*args), f"execute_command {args}")

    def flushdb(self) -> str:
        """
        Flush current database
        
        Returns:
            Result message
        """
        return self._execute_with_retry(lambda: self._connection.flushdb(), "flushdb")

    def flushall(self) -> str:
        """
        Flush all databases
        
        Returns:
            Result message
        """
        return self._execute_with_retry(lambda: self._connection.flushall(), "flushall")

    def close(self) -> None:
        """Close Redis connection"""
        self._close_quietly()
        self._connection = None
        logger.debug("Redis connection closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
