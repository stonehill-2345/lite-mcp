"""
External MCP Service Wrapper Module

Provides functionality for integrating third-party MCP services into the LiteMCP framework.
Supports dynamic management of external MCP services without hardcoding any specific services.
"""

from .external_mcp_server import ExternalMCPServer, ExternalMCPConfig, create_external_mcp_server
from .config_manager import ExternalMCPConfigManager, external_config_manager

__all__ = [
    "ExternalMCPServer",
    "ExternalMCPConfig", 
    "create_external_mcp_server",
    "ExternalMCPConfigManager",
    "external_config_manager"
]
