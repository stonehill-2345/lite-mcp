"""
LiteMCP Unified Logging Management System

Provides project-level log management with support for:
- Level-based logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Dual output to both file and console
- Colored console output
- Automatic log rotation
- Module-level loggers
- Performance monitoring logs
- Differentiated logging configurations for different tools
"""

import logging
import logging.handlers
import os
import sys
import threading
from typing import Optional, Dict, Tuple
from src.core.utils import get_project_root

class ColoredFormatter(logging.Formatter):
    """Colored log formatter"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Purple
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        # Get base formatted message
        formatted = super().format(record)

        # Only add color when outputting to terminal
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            color = self.COLORS.get(record.levelname, '')
            reset = self.COLORS['RESET']
            return f"{color}{formatted}{reset}"

        return formatted


class LiteMCPLogger:
    """LiteMCP Unified Log Manager"""

    _instance = None
    _lock = threading.Lock()
    _loggers: Dict[str, logging.Logger] = {}

    # Log configuration strategies for different tools
    LOG_CONFIGS = {
        # High-volume tools configuration (e.g., fastbot, sonic)
        "high_volume": {
            "max_bytes": 30 * 1024 * 1024,  # 30MB per file
            "backup_count": 3,  # Keep 3 backups
            "description": "High-volume tools (30MB per file, 3 backups, total 120MB)"
        },
        # Medium-volume tools configuration (e.g., devops tools)
        "medium_volume": {
            "max_bytes": 20 * 1024 * 1024,  # 20MB per file
            "backup_count": 2,  # Keep 2 backups
            "description": "Medium-volume tools (20MB per file, 2 backups, total 60MB)"
        },
        # Low-volume tools configuration (e.g., examples, school projects)
        "low_volume": {
            "max_bytes": 5 * 1024 * 1024,  # 5MB per file
            "backup_count": 2,  # Keep 2 backups
            "description": "Low-volume tools (5MB per file, 2 backups, total 15MB)"
        },
        # Default configuration
        "default": {
            "max_bytes": 10 * 1024 * 1024,  # 10MB per file
            "backup_count": 5,  # Keep 5 backups
            "description": "Default configuration (10MB per file, 5 backups, total 60MB)"
        }
    }

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            # Get project root directory
            self.project_root = get_project_root()
            self.log_dir = self.project_root / "runtime" / "logs"

            # Ensure log directory exists
            self.log_dir.mkdir(parents=True, exist_ok=True)

            # Log level mapping
            self.log_levels = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR,
                'CRITICAL': logging.CRITICAL
            }

            # Default configurations
            self.default_level = logging.INFO
            self.console_level = logging.INFO
            self.file_level = logging.DEBUG

            # Get log level from environment variable
            env_level = os.getenv('LiteMCP_LOG_LEVEL', 'INFO').upper()
            if env_level in self.log_levels:
                self.default_level = self.log_levels[env_level]
                self.console_level = self.log_levels[env_level]

            self.initialized = True

    def _get_log_config(self, config_type: str = "default") -> Tuple[int, int, str]:
        """Get the specified type of log configuration

        Args:
            config_type: Configuration type (high_volume, medium_volume, low_volume, default)

        Returns:
            A tuple containing (max_bytes, backup_count, description)
        """
        if config_type not in self.LOG_CONFIGS:
            config_type = "default"

        config = self.LOG_CONFIGS[config_type]
        return config["max_bytes"], config["backup_count"], config["description"]

    def get_logger(self, name: str = "litemcp",
                   log_file: Optional[str] = None,
                   console_output: bool = True,
                   file_output: bool = True,
                   log_config_type: str = "default") -> logging.Logger:
        """Get or create a logger

        Args:
            name: Logger name, typically the module name
            log_file: Log file name, defaults to name.log
            console_output: Whether to output to console
            file_output: Whether to output to file
            log_config_type: Log configuration type (high_volume, medium_volume, low_volume, default)

        Returns:
            Configured logger instance
        """

        # Use logger name as primary cache key to avoid duplicate creation
        if name in self._loggers:
            return self._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(self.default_level)

        # Important: Disable propagation to avoid duplicate output to parent loggers
        logger.propagate = False

        # Clear existing handlers (prevent duplicate addition)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.console_level)

            # Console format (simplified)
            console_format = ColoredFormatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_format)
            logger.addHandler(console_handler)

        # File handler
        if file_output:
            if not log_file:
                log_file = f"{name.replace('.', '_')}.log"

            log_file_path = self.log_dir / log_file

            # Get corresponding log configuration based on specified type
            max_bytes, backup_count, config_desc = self._get_log_config(log_config_type)

            # Use rotating file handler (dynamically configured based on tool type)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self.file_level)

            # File format (detailed)
            file_format = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(funcName)s(): %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)

            # Log configuration info (only when first created)
            logger.info(f"Logger created - {config_desc}")

        # Cache the logger (using name as key)
        self._loggers[name] = logger
        return logger

    def get_log_config_info(self) -> Dict[str, Dict]:
        """Get detailed information of all log configurations"""
        config_info = {}

        for config_type, config in self.LOG_CONFIGS.items():
            max_mb = config["max_bytes"] / (1024 * 1024)
            total_mb = max_mb * (config["backup_count"] + 1)

            config_info[config_type] = {
                "max_size_per_file_mb": max_mb,
                "backup_count": config["backup_count"],
                "total_max_size_mb": total_mb,
                "description": config["description"]
            }

        # Add usage instructions
        config_info["usage"] = {
            "default_config": "default",
            "description": "By default all tools use 'default' configuration",
            "custom_config": "Tools with special requirements can specify log_config_type parameter when calling get_logger",
            "example": "get_logger('fastbot.test', log_config_type='high_volume')"
        }

        return config_info

    def set_level(self, level: str):
        """Set global log level"""
        if level.upper() in self.log_levels:
            new_level = self.log_levels[level.upper()]
            self.default_level = new_level
            self.console_level = new_level

            # Update all existing loggers
            for logger in self._loggers.values():
                logger.setLevel(new_level)
                for handler in logger.handlers:
                    if isinstance(handler, logging.StreamHandler) and not isinstance(handler,
                                                                                     logging.handlers.RotatingFileHandler):
                        handler.setLevel(new_level)

    def clear_loggers(self):
        """Clear all loggers (for testing or resetting)"""
        for logger in self._loggers.values():
            # Remove all handlers
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        self._loggers.clear()

    def get_logger_info(self) -> Dict[str, Dict]:
        """Get information about all loggers (for debugging)"""
        info = {}
        for name, logger in self._loggers.items():
            info[name] = {
                "level": logging.getLevelName(logger.level),
                "handlers": len(logger.handlers),
                "propagate": logger.propagate,
                "handler_types": [type(h).__name__ for h in logger.handlers]
            }
        return info


class LoggerMixin:
    """Logger mixin class

    Provides convenient logging capabilities for other classes
    Supports specifying log configuration type via _log_config_type attribute
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = None
        # Subclasses can set this attribute to specify log configuration type
        if not hasattr(self, '_log_config_type'):
            self._log_config_type = "default"

    @property
    def logger(self) -> logging.Logger:
        """Lazy-loaded logger property"""
        if self._logger is None:
            # Use class name as logger name
            logger_name = f"litemcp.{self.__class__.__module__}.{self.__class__.__name__}"
            self._logger = get_logger(logger_name, log_config_type=self._log_config_type)
        return self._logger


# Global logger manager instance
_log_manager = LiteMCPLogger()


# Convenience functions
def get_logger(name: str = "litemcp", log_config_type: str = "default", **kwargs) -> logging.Logger:
    """Convenience function to get a logger

    Args:
        name: Logger name
        log_config_type: Log configuration type (high_volume, medium_volume, low_volume, default)
        **kwargs: Additional arguments
    """
    return _log_manager.get_logger(name, log_config_type=log_config_type, **kwargs)


def set_log_level(level: str):
    """Convenience function to set global log level"""
    _log_manager.set_level(level)


def get_log_config_info() -> Dict[str, Dict]:
    """Convenience function to get log configuration info"""
    return _log_manager.get_log_config_info()


# Lazy-loaded default logger
def _get_default_logger() -> logging.Logger:
    """Get default logger (lazy-loaded)"""
    return get_logger("litemcp")


# Convenience logging functions
def debug(msg: str, *args, **kwargs):
    """Debug level log"""
    _get_default_logger().debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """Info level log"""
    _get_default_logger().info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """Warning level log"""
    _get_default_logger().warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """Error level log"""
    _get_default_logger().error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """Critical level log"""
    _get_default_logger().critical(msg, *args, **kwargs)


def exception(msg: str, *args, **kwargs):
    """Exception log (includes stack trace)"""
    _get_default_logger().exception(msg, *args, **kwargs)


def debug_logging_system():
    """Debug logging system status"""
    print("=== LiteMCP Logging System Status ===")

    # Display global manager info
    print(f"Log directory: {_log_manager.log_dir}")
    print(f"Default level: {logging.getLevelName(_log_manager.default_level)}")
    print(f"Console level: {logging.getLevelName(_log_manager.console_level)}")
    print(f"File level: {logging.getLevelName(_log_manager.file_level)}")

    # Display log configuration strategies
    print("\n=== Log Configuration Strategies ===")
    config_info = _log_manager.get_log_config_info()

    for config_type, config in config_info.items():
        if config_type == "usage":
            continue
        print(f"\n{config_type.upper()}:")
        print(f"  Max size per file: {config['max_size_per_file_mb']}MB")
        print(f"  Backup count: {config['backup_count']}")
        print(f"  Total max size: {config['total_max_size_mb']}MB")
        print(f"  Description: {config['description']}")

    # Display usage instructions
    print("\n=== Usage Instructions ===")
    usage = config_info["usage"]
    print(f"Default config: {usage['default_config']}")
    print(f"Description: {usage['description']}")
    print(f"Custom config: {usage['custom_config']}")
    print(f"Example: {usage['example']}")

    # Display all logger information
    logger_info = _log_manager.get_logger_info()
    print(f"\n=== Registered Loggers ({len(logger_info)}) ===")

    for name, info in logger_info.items():
        print(f"\nLogger: {name}")
        print(f"  Level: {info['level']}")
        print(f"  Handler count: {info['handlers']}")
        print(f"  Propagate: {info['propagate']}")
        print(f"  Handler types: {info['handler_types']}")

    print("\n=== End ===")


def reset_logging_system():
    """Reset logging system (clean up all loggers)"""
    print("Resetting logging system...")
    _log_manager.clear_loggers()
    print("Logging system has been reset")


# Performance monitoring decorator
def log_performance(func):
    """Performance monitoring decorator"""
    import functools
    import time

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger = get_logger(f"performance.{func.__module__}.{func.__name__}")

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Execution completed, time taken: {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Execution failed, time taken: {execution_time:.3f}s, error: {e}")
            raise

    return wrapper


# Context manager for temporarily changing log level
class TemporaryLogLevel:
    """Temporary log level context manager"""

    def __init__(self, level: str):
        self.new_level = level
        self.old_level = None

    def __enter__(self):
        self.old_level = _log_manager.default_level
        _log_manager.set_level(self.new_level)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        level_name = logging.getLevelName(self.old_level)
        _log_manager.set_level(level_name)


# Initialize logging system
def init_logging(level: str = "INFO",
                 console_output: bool = True,
                 file_output: bool = True):
    """Initialize logging system

    Args:
        level: Log level
        console_output: Whether to output to console
        file_output: Whether to output to file
    """
    set_log_level(level)

    # Create main logger
    main_logger = get_logger(
        "litemcp",
        console_output=console_output,
        file_output=file_output
    )

    main_logger.info("LiteMCP logging system initialized")
    main_logger.info(f"Log level: {level}")
    main_logger.info(f"Log directory: {_log_manager.log_dir}")

    return main_logger


if __name__ == "__main__":
    # Test logging system
    init_logging("DEBUG")

    logger = get_logger("test")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical error message")


    # Test performance monitoring
    @log_performance
    def test_function():
        import time
        time.sleep(0.1)
        return "Test completed"


    test_function()

    # Test temporary log level
    with TemporaryLogLevel("ERROR"):
        logger.info("This message won't be displayed")
        logger.error("This error will be displayed")

    logger.info("Log level restored to normal")
