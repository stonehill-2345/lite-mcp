"""
LiteMCP Core Module

Contains core functionalities including configuration management, logging system, 
exception handling, abstract base classes and utility functions
"""

try:
    from .config import settings
    __all__ = ["settings"]
except ImportError:
    __all__ = []

try:
    from .utils import get_local_ip
    __all__.extend(["get_local_ip"])
except ImportError:
    pass 