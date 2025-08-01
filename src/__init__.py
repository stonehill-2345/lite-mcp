#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LiteMCP Framework Core Package

This is the core package of the LiteMCP framework, containing all core functional modules:
- core: Core functional modules (proxy server, registry, configuration management, etc.)
- tools: MCP tool servers
- controller: API controllers
- cli: Command line interface
"""

__version__ = "1.0.0"
__author__ = "Stonehill-tech Open SourceTeam"
__description__ = "LiteMCP Framework - MCP server framework designed specifically for testers"

# Export core components
from .core import *
from .tools import *
from .controller import *

__all__ = [
    "__version__",
    "__author__", 
    "__description__"
]