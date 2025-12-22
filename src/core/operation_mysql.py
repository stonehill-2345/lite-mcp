import pymysql
from pymysql.cursors import DictCursor
import threading
import logging
import time
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Union, Tuple, Callable

logger = logging.getLogger(__name__)

# Default configuration constants
DEFAULT_CHARSET = 'utf8mb4'
DEFAULT_CONNECT_TIMEOUT = 10
DEFAULT_READ_TIMEOUT = 30
DEFAULT_WRITE_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_SLOW_QUERY_THRESHOLD = 1.0  # Slow query threshold (seconds)


class MySQLConnectionError(Exception):
    """MySQL connection error"""
    pass


class MySQLOperationError(Exception):
    """MySQL operation error"""
    pass


class OperationMySQL:
    """
    MySQL database operation class
    
    Features:
    - Auto-reconnect mechanism
    - Slow query logging
    - Transaction support
    - Context manager support
    """

    def __init__(
        self, 
        host: str, 
        port: int, 
        user: str, 
        password: str, 
        database: str,
        charset: str = DEFAULT_CHARSET,
        connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: int = DEFAULT_READ_TIMEOUT,
        write_timeout: int = DEFAULT_WRITE_TIMEOUT,
        slow_query_threshold: float = DEFAULT_SLOW_QUERY_THRESHOLD
    ):
        """
        Initialize MySQL connection

        Args:
            host: Database host
            port: Port number
            user: Username
            password: Password
            database: Database name
            charset: Character set, default utf8mb4
            connect_timeout: Connection timeout (seconds)
            read_timeout: Read timeout (seconds)
            write_timeout: Write timeout (seconds)
            slow_query_threshold: Slow query threshold (seconds)
        """
        self._database = database
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._slow_query_threshold = slow_query_threshold

        # Connection parameters
        self._connection_params = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'db': database,
            'charset': charset,
            'autocommit': False,
            'cursorclass': DictCursor,
            'connect_timeout': connect_timeout,
            'read_timeout': read_timeout,
            'write_timeout': write_timeout
        }

        self._connection: Optional[pymysql.Connection] = None
        self._cursor: Optional[DictCursor] = None
        self._lock = threading.Lock()

        # Initialize connection
        self._ensure_connection()

    def _ensure_connection(self) -> None:
        """Ensure database connection is valid"""
        try:
            if self._connection is None or not self._connection.open:
                self._connection = pymysql.connect(**self._connection_params)
                self._cursor = self._connection.cursor()
            else:
                # Test if connection is valid
                self._connection.ping(reconnect=True)
        except Exception as e:
            logger.error(f"MySQL connection failed: {str(e)}")
            raise MySQLConnectionError(f"Unable to connect to MySQL database: {str(e)}")

    def get_table_names(self) -> List[Dict[str, Any]]:
        """
        Get list of table names in the database

        Returns:
            List of table names and comments
        """
        sql = """
            SELECT TABLE_NAME, TABLE_COMMENT
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_NAME
        """
        
        try:
            return self.execute_query(sql, (self._database,))
        except Exception as e:
            logger.error(f"Failed to get table names: {str(e)}")
            return []

    def _execute_with_retry(
        self, 
        operation: Callable[[], Any], 
        sql: str = "",
        max_retries: int = DEFAULT_MAX_RETRIES
    ) -> Any:
        """
        Execute operation with retry mechanism and slow query logging

        Args:
            operation: Callable operation function, no parameters, returns operation result
            sql: SQL statement (for logging)
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
                        sql_preview = sql[:200] + "..." if len(sql) > 200 else sql
                        logger.warning(f"Slow query ({elapsed_time:.2f}s): {sql_preview}")
                    
                    return result
                    
            except (pymysql.Error, MySQLConnectionError) as e:
                last_error = e
                
                if attempt < max_retries - 1:
                    wait_time = 0.5 * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"MySQL operation failed, retrying in {wait_time:.1f}s ({attempt + 1}/{max_retries}): {str(e)}")
                    time.sleep(wait_time)
                    self._reconnect()
                    
        logger.error(f"MySQL operation failed after {max_retries} retries: {str(last_error)}")
        raise MySQLOperationError(f"Operation failed: {str(last_error)}")
    
    def _reconnect(self) -> None:
        """Re-establish database connection"""
        self._close_quietly()
        self._connection = None
        self._cursor = None
    
    def _close_quietly(self) -> None:
        """Close connection quietly (without raising exceptions)"""
        try:
            if self._cursor:
                self._cursor.close()
        except Exception:
            pass
        try:
            if self._connection:
                self._connection.close()
        except Exception:
            pass

    @contextmanager
    def transaction(self):
        """Transaction context manager"""
        try:
            yield self
            self._connection.commit()
            logger.debug("Transaction committed successfully")
        except Exception as e:
            self._connection.rollback()
            logger.error(f"Transaction rollback: {str(e)}")
            raise

    def execute_query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute query statement

        Args:
            sql: SQL statement
            params: Parameter tuple

        Returns:
            List of query results
        """
        def _query():
            self._cursor.execute(sql, params)
            return self._cursor.fetchall()

        return self._execute_with_retry(_query, sql)

    def execute_update(self, sql: str, params: Optional[Tuple] = None) -> int:
        """
        Execute update statement (INSERT/UPDATE/DELETE)

        Args:
            sql: SQL statement
            params: Parameter tuple

        Returns:
            Number of affected rows
        """
        def _update():
            affected_rows = self._cursor.execute(sql, params)
            self._connection.commit()
            return affected_rows

        return self._execute_with_retry(_update, sql)

    def query_sql(self, sql: str) -> Union[List[Dict[str, Any]], int]:
        """
        Execute SQL statement (supports all SQL operations)

        Args:
            sql: SQL statement

        Returns:
            Query results (for SELECT/SHOW/DESCRIBE/EXPLAIN) or affected row count (for INSERT/UPDATE/DELETE)
        """
        sql_lower = sql.lower().strip()

        if any(keyword in sql_lower for keyword in ['select', 'show', 'describe', 'explain']):
            return self.execute_query(sql)
        else:
            return self.execute_update(sql)

    def dealsql(self, select_sql: str, insert_sql: str) -> str:
        """
        Check if data exists, insert if not (legacy interface compatibility)

        Args:
            select_sql: Select SQL
            insert_sql: Insert SQL

        Returns:
            Operation result
        """
        try:
            result = self.execute_query(select_sql)
            if not result or result[0][list(result[0].keys())[0]] < 1:
                self.execute_update(insert_sql)
                logger.debug('Insert statement executed')
                return 'success'
            else:
                logger.debug('Data already exists')
                return 'exists'
        except Exception as e:
            logger.error(f"dealsql operation failed: {str(e)}")
            return 'error'

    def batch_insert(self, table_name: str, data_list: List[Dict[str, Any]],
                     batch_size: int = 1000) -> bool:
        """
        Batch insert data

        Args:
            table_name: Table name
            data_list: List of data
            batch_size: Batch size

        Returns:
            Whether successful
        """
        if not data_list:
            logger.warning("Data list is empty, cannot perform batch insert")
            return False

        try:
            # Get field names
            fields = list(data_list[0].keys())
            placeholders = ', '.join(['%s'] * len(fields))
            fields_str = ', '.join(fields)
            sql = f"INSERT INTO {table_name} ({fields_str}) VALUES ({placeholders})"

            # Process in batches
            total_inserted = 0
            for i in range(0, len(data_list), batch_size):
                batch = data_list[i:i + batch_size]
                values = [[item[field] for field in fields] for item in batch]

                def _batch_insert():
                    self._cursor.executemany(sql, values)
                    self._connection.commit()
                    return len(batch)

                inserted = self._execute_with_retry(_batch_insert, sql)
                total_inserted += inserted
                logger.debug(f'Batch insert progress: {total_inserted}/{len(data_list)}')

            logger.debug(f'Batch insert successful, {total_inserted} records inserted')
            return True

        except Exception as e:
            logger.error(f"Batch insert failed: {str(e)}")
            return False

    def execute_many(self, sql: str, params_list: List[Tuple]) -> int:
        """
        Execute batch operation

        Args:
            sql: SQL statement
            params_list: List of parameters

        Returns:
            Number of affected rows
        """
        def _execute_many():
            affected_rows = self._cursor.executemany(sql, params_list)
            self._connection.commit()
            return affected_rows

        return self._execute_with_retry(_execute_many, sql)

    def get_one(self, sql: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        """
        Get single record

        Args:
            sql: SQL statement
            params: Parameter tuple

        Returns:
            Single record or None
        """
        def _get_one():
            self._cursor.execute(sql, params)
            return self._cursor.fetchone()

        return self._execute_with_retry(_get_one, sql)

    def get_count(self, sql: str, params: Optional[Tuple] = None) -> int:
        """
        Get record count

        Args:
            sql: SQL statement
            params: Parameter tuple

        Returns:
            Record count
        """
        result = self.get_one(sql, params)
        if result:
            return list(result.values())[0]
        return 0

    def table_exists(self, table_name: str) -> bool:
        """
        Check if table exists

        Args:
            table_name: Table name

        Returns:
            Whether table exists
        """
        sql = """
              SELECT COUNT(*) as count
              FROM information_schema.tables
              WHERE table_schema = %s
                AND table_name = %s \
              """
        count = self.get_count(sql, (self._database, table_name))
        return count > 0

    def close(self) -> None:
        """Close database connection"""
        self._close_quietly()
        self._connection = None
        self._cursor = None
        logger.debug("MySQL connection closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get table schema information

        Args:
            table_name: Table name

        Returns:
            List of field info, each containing field name, type, nullable, primary key, etc.
        """
        sql = f"SHOW FULL COLUMNS FROM `{table_name}`"
        try:
            result = self.execute_query(sql)
            schema = [
                {
                    'Field': row['Field'],
                    'Type': row['Type'],
                    'Null': row['Null'],
                    'Key': row['Key'],
                    'Default': row['Default'],
                    'Extra': row['Extra'],
                    'Comment': row.get('Comment', '')
                }
                for row in result
            ]
            return schema
        except Exception as e:
            logger.error(f"Failed to get table schema: {str(e)}")
            return []
