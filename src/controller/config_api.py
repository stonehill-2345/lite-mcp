"""
LiteMCP Configuration API - Provides MCP Client Configuration Generation Service

Dynamically generates MCP client configurations through HTTP interfaces, supporting Cursor and Claude Desktop.
"""

import os
from typing import Dict, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.registry import server_registry
from src.tools import AVAILABLE_SERVERS
from src.controller.statistics_api import router as statistics_router
from src.controller.external_mcp_api import external_mcp_router


def get_proxy_host_port(proxy_host: str = "auto", proxy_port: int = 0) -> tuple[str, int]:
    """
    Get proxy server host and port configuration

    Args:
        proxy_host: Proxy host address, "auto" for automatic detection
        proxy_port: Proxy port, 0 means read from config file

    Returns:
        tuple: (host, port) Proxy server host and port
    """
    # If port is 0, read from config file
    if proxy_port == 0:
        from src.core.utils import read_proxy_config_from_yaml
        config_host, config_port = read_proxy_config_from_yaml()
        proxy_port = config_port
        # If host is also auto, use host from config file
        if proxy_host == "auto":
            proxy_host = config_host

    # Automatically detect proxy host address
    if proxy_host == "auto":
        from src.core.utils import get_local_ip
        detected_ip = get_local_ip()
        proxy_host = detected_ip if detected_ip else "localhost"

    return proxy_host, proxy_port


class ConfigResponse(BaseModel):
    """Configuration response model"""
    client_type: str
    config: Dict[str, Any]
    servers_count: int
    generated_at: str


class StatusResponse(BaseModel):
    """Status response model"""
    status: str
    registry_info: Dict[str, Any]


app = FastAPI(
    title="LiteMCP Configuration API",
    description="API service for dynamically generating MCP client configurations",
    version="1.0.0"
)


# Configure CORS middleware to support cross-origin requests
app.add_middleware(
    CORSMiddleware,  # type: ignore
    allow_origins=["*"],  # Allow all origins (should specify domains in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

app.include_router(statistics_router)
app.include_router(external_mcp_router)


@app.get("/api/v1/", summary="API root path")
async def root():
    """API root endpoint returning basic information"""
    return {
        "name": "LiteMCP Configuration API",
        "version": "1.0.0",
        "description": "Dynamically generates MCP client configurations",
        "endpoints": {
            "config": "/api/v1/config - Get detailed categorized configuration structure (default proxy mode)",
            "config_cursor": "/api/v1/config/cursor - Get Cursor available configuration (direct connection mode)",
            "config_claude": "/api/v1/config/claude - Get Claude Desktop available configuration (direct connection mode)",
            "config_proxy": "/api/v1/config/proxy - Get proxy mode configuration",
            "config_explain": "/api/v1/config/explain - Configuration mode explanation",
            "status": "/api/v1/status - Get server status",
            "health": "/api/v1/health - Health check",
            "debug": "/api/v1/debug - Debug information",
            "statistics": "/api/v1/statistics - Statistics API",
            "external_mcp": "/api/v1/external-mcp - External MCP Service Management API"
        },
        "config_structure": {
            "detailed": {
                "description": "GET /config returns proxy mode configuration by default, with detailed structure categorized by transport mode",
                "parameters": {
                    "client_type": "cursor or claude_desktop",
                    "format": "json (detailed structure) or raw (available configuration)",
                    "use_proxy": "true (default) enables proxy mode, false for direct connection",
                    "proxy_host": "Proxy server host address (default 'auto' for automatic detection)",
                    "proxy_port": "Proxy server port (default 8080)"
                },
                "sections": {
                    "stdio": "STDIO mode configuration (currently empty)",
                    "http": "Proxy HTTP server configuration",
                    "sse": "Proxy SSE server configuration",
                    "config_example": "Ready-to-use configuration example"
                }
            },
            "quick_access": {
                "description": "Quick access endpoints returning available configurations directly",
                "cursor": "/config/cursor (direct connection mode)",
                "claude_desktop": "/config/claude (direct connection mode)",
                "proxy": "/config/proxy (proxy mode)"
            }
        },
        "supported_modes": {
            "proxy": "Reverse proxy mode (default recommended) - Fixed client configuration",
            "stdio": "Standard I/O mode (always available)",
            "http": "HTTP mode (requires running server)",
            "sse": "Server-Sent Events mode (requires running server)"
        },
        "proxy_benefits": {
            "description": "Advantages of reverse proxy mode (now default)",
            "advantages": [
                "Fixed client configuration, no frequent modifications needed",
                "Automatic service discovery and load balancing",
                "Unified access point for easier management",
                "Supports dynamic port allocation",
                "Automatic server IP address detection"
            ],
            "usage": "Proxy mode enabled by default, add ?use_proxy=false for direct connection mode"
        }
    }


@app.get("/api/v1/config", response_model=ConfigResponse, summary="Get MCP client configuration")
async def get_mcp_config(
        client_type: str = Query(
            default="cursor",
            description="Client type",
            pattern="^(cursor|claude_desktop)$"
        ),
        format: str = Query(
            default="json",
            description="Response format",
            pattern="^(json|raw)$"
        ),
        use_proxy: bool = Query(
            default=True,  # Proxy mode by default
            description="Whether to use proxy mode"
        ),
        proxy_host: str = Query(
            default="auto",  # Auto detection
            description="Proxy server host address, 'auto' for automatic detection"
        ),
        proxy_port: int = Query(
            default=0,  # 0 means read from config file
            description="Proxy server port, 0 means read from config file"
        )
):
    """
    Get MCP client configuration

    Args:
        client_type: Client type (cursor or claude_desktop)
        format: Response format (json or raw)
        use_proxy: Whether to use proxy mode (default true)
        proxy_host: Proxy server host address, 'auto' for automatic detection
        proxy_port: Proxy server port, 0 means read from config file

    Returns:
        MCP client configuration
    """
    try:
        if use_proxy:
            # Get proxy configuration using common method
            proxy_host, proxy_port = get_proxy_host_port(proxy_host, proxy_port)

            # Return proxy mode configuration
            config_data = generate_proxy_config(client_type, proxy_host, proxy_port)
        else:
            # Return direct connection mode configuration
            config_data = server_registry.generate_mcp_config(client_type)

        if format == "raw":
            # Return config example directly for copy-paste
            return JSONResponse(content=config_data["config_example"])

        # Return detailed categorized structure
        return JSONResponse(content=config_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration generation failed: {str(e)}")


def generate_proxy_config(client_type: str, proxy_host: str = "localhost", proxy_port: int = 1888) -> Dict[str, Any]:
    """
    Generate proxy-based MCP client configuration

    Args:
        client_type: Client type (cursor|claude_desktop)
        proxy_host: Proxy server host
        proxy_port: Proxy server port

    Returns:
        Proxy configuration data
    """

    # Get MCP server host from environment variable, fallback to default
    mcp_server_host = os.getenv("MCP_SERVER_HOST", f"http://{proxy_host}:{proxy_port}")

    result = {
        "client_type": client_type,
        "mode": "proxy",
        "proxy_info": {
            "host": proxy_host,
            "port": proxy_port,
            "base_url": f"{mcp_server_host}"
        },
        "stdio": [],
        "streamable": [],
        "sse": [],
        "servers_count": 0,
        "config_example": {"mcpServers": {}},
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": "Access MCP servers through reverse proxy, based on actual running server configurations"
    }

    # First generate stdio configuration (always available)
    stdio_config_data = server_registry.generate_mcp_config(client_type)
    result["stdio"] = stdio_config_data["stdio"]

    # Get list of actually running servers
    running_servers = server_registry.get_all_servers()

    # Generate proxy configuration based on actually running servers
    for server_key, server_info in running_servers.items():
        server_name = server_info.name
        server_type = server_info.server_type
        transport = server_info.transport

        # Skip system servers (proxy server, API server)
        if server_type.endswith("_server"):
            continue

        # Get server description
        server_description = ""
        if server_type in AVAILABLE_SERVERS:
            server_description = AVAILABLE_SERVERS[server_type].get("description", "")
        elif server_type == "external_mcp":
            # For external MCP services, use more friendly description
            if hasattr(server_info, 'server_file') and "External MCP service:" in str(server_info.server_file):
                external_service_name = server_info.server_file.split("External MCP service:")[1].strip()
                server_description = f"External MCP service: {external_service_name}"
            else:
                server_description = f"External MCP service: {server_name}"

        if not server_description:
            server_description = f"{server_type} server"

        # For external MCP services, use server_name instead of server_type as route and config key
        config_key = server_name if server_type == "external_mcp" else server_type

        # Generate corresponding proxy configuration based on actual transport mode
        if transport == "http":
            # HTTP proxy configuration
            if client_type == "cursor":
                http_config = {
                    "type": "streamable-http",
                    "url": f"{mcp_server_host}/mcp/{config_key}",
                    "description": f"{server_description} (accessed via proxy HTTP)"
                }
            else:  # claude_desktop
                http_config = {
                    "transport": {
                        "type": "streamable-http",
                        "url": f"{mcp_server_host}/mcp/{config_key}"
                    },
                    "description": f"{server_description} (accessed via proxy HTTP)"
                }

            result["streamable"].append({
                f"{config_key}-proxy-http": http_config
            })
            result["servers_count"] += 1

        elif transport == "sse":
            # SSE proxy configuration
            if client_type == "cursor":
                sse_config = {
                    "type": "sse",
                    "url": f"{mcp_server_host}/sse/{config_key}",
                    "description": f"{server_description} (accessed via proxy SSE)"
                }
            else:  # claude_desktop
                sse_config = {
                    "transport": {
                        "type": "sse",
                        "url": f"{mcp_server_host}/sse/{config_key}"
                    },
                    "description": f"{server_description} (accessed via proxy SSE)"
                }

            result["sse"].append({
                f"{config_key}-proxy-sse": sse_config
            })
            result["servers_count"] += 1

    # Calculate total server count (including stdio)
    result["servers_count"] += len(result["stdio"])

    # Generate configuration example - include all actually running servers
    config_example_servers = {}

    # Add all SSE configurations
    if result["sse"]:
        config_example_servers.update(result["sse"][0])

    # Add all HTTP configurations
    if result["streamable"]:
        config_example_servers.update(result["streamable"][0])

    # If no proxy configuration, add stdio configuration
    if result["stdio"]:
        config_example_servers.update(result["stdio"][0])

    result["config_example"]["mcpServers"] = config_example_servers

    return result


@app.get("/api/v1/config/proxy", summary="Get proxy mode configuration (shortcut)")
async def get_proxy_config(
        client_type: str = Query(
            default="cursor",
            description="Client type",
            pattern="^(cursor|claude_desktop)$"
        ),
        proxy_host: str = Query(
            default="auto",
            description="Proxy server host address, 'auto' for automatic detection"
        ),
        proxy_port: int = Query(
            default=0,
            description="Proxy server port, 0 means read from config file"
        )
):
    """Shortcut: Directly get proxy mode configuration"""
    # Get proxy configuration using common method
    proxy_host, proxy_port = get_proxy_host_port(proxy_host, proxy_port)

    config_data = generate_proxy_config(client_type, proxy_host, proxy_port)
    return JSONResponse(content=config_data)


@app.get("/api/v1/status", response_model=StatusResponse, summary="Get server status")
async def get_status():
    """
    Get current registered server status

    Returns:
        Server status information
    """
    try:
        status_info = server_registry.get_status()

        return StatusResponse(
            status="ok",
            registry_info=status_info
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@app.get("/api/v1/health", summary="Health check")
async def health_check():
    """
    API health check

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "api_version": "1.0.0",
        "registry_file_exists": server_registry.registry_file.exists(),
        "registry_file_path": str(server_registry.registry_file),
        "current_working_directory": os.getcwd(),
        "total_servers": len(server_registry.get_all_servers()),
        "registry_servers_before_load": len(server_registry.servers),
    }


def _build_actual_config(config_data: dict) -> dict:
    """Build actual usable configuration

    Args:
        config_data: Raw configuration data

    Returns:
        Built actual usable configuration
    """
    actual_config = {"mcpServers": {}}

    # Add STDIO configuration
    for stdio_item in config_data["stdio"]:
        actual_config["mcpServers"].update(stdio_item)

    # Add HTTP configuration
    for http_item in config_data["http"]:
        actual_config["mcpServers"].update(http_item)

    # Add SSE configuration
    for sse_item in config_data["sse"]:
        actual_config["mcpServers"].update(sse_item)

    return actual_config


@app.get("/api/v1/config/cursor", summary="Get Cursor configuration (shortcut)")
async def get_cursor_config():
    """Shortcut to get Cursor client configuration"""
    config_data = server_registry.generate_mcp_config("cursor")
    return JSONResponse(content=_build_actual_config(config_data))

@app.get("/api/v1/config/claude", summary="Get Claude Desktop configuration (shortcut)")
async def get_claude_config():
    """Shortcut to get Claude Desktop client configuration"""
    config_data = server_registry.generate_mcp_config("claude_desktop")
    return JSONResponse(content=_build_actual_config(config_data))


@app.get("/api/v1/config/explain", summary="Configuration Explanation")
async def explain_config():
    """
    Detailed explanation of different MCP configuration modes

    Returns:
        Configuration description and examples
    """
    return {
        "description": "LiteMCP supports multiple transport modes for different usage scenarios",
        "modes": {
            "stdio": {
                "description": "Standard I/O mode - Launches server process via command line",
                "advantages": [
                    "No need to pre-start server",
                    "Process isolation for better security",
                    "Suitable for production environment"
                ],
                "configuration": {
                    "command": "Python interpreter path",
                    "args": ["Server script file path"],
                    "env": {
                        "description": "Environment variable settings",
                        "examples": {
                            "LiteMCP_LOG_LEVEL": "Set log level (DEBUG, INFO, WARNING, ERROR)",
                            "LiteMCP_CONFIG_PATH": "Specify config file path",
                            "API_KEY": "Set API key (if server requires)",
                            "TIMEOUT": "Set timeout duration"
                        }
                    }
                }
            },
            "http": {
                "description": "HTTP mode - Communication via HTTP protocol",
                "advantages": [
                    "Supports cross-network access",
                    "Easy debugging and monitoring",
                    "Supports load balancing"
                ],
                "configuration": {
                    "url": "HTTP endpoint address, format: http://host:port/mcp"
                }
            },
            "sse": {
                "description": "Server-Sent Events mode - Real-time communication based on SSE",
                "advantages": [
                    "Real-time bidirectional communication",
                    "Better performance",
                    "Supports streaming responses"
                ],
                "configuration": {
                    "url": "SSE endpoint address, format: http://host:port/sse"
                }
            }
        },
        "usage_recommendations": {
            "development": "Recommended to use STDIO mode for simplicity and reliability",
            "testing": "Recommended to use HTTP/SSE mode for easier debugging",
            "production": "Recommended to use STDIO mode for better security",
            "remote_access": "Use HTTP/SSE mode for network access support"
        }
    }


@app.get("/api/v1/debug", summary="Debug Information")
async def debug_info():
    """Debug information"""
    # Force reload
    server_registry.load_from_file()

    return {
        "registry_file_path": str(server_registry.registry_file),
        "registry_file_exists": server_registry.registry_file.exists(),
        "current_working_directory": os.getcwd(),
        "servers_in_memory": len(server_registry.servers),
        "servers_detail": {k: v.to_dict() for k, v in server_registry.servers.items()},
        "file_content_exists": server_registry.registry_file.exists() and server_registry.registry_file.stat().st_size > 0
    }


@app.post("/api/v1/registry/cleanup", summary="Clean up dead processes")
async def cleanup_dead_servers():
    """
    Clean up stopped server processes

    Returns:
        Cleanup results
    """
    try:
        before_count = len(server_registry.get_all_servers())
        server_registry.clear_dead_servers()
        after_count = len(server_registry.get_all_servers())

        return {
            "status": "success",
            "cleaned_servers": before_count - after_count,
            "remaining_servers": after_count
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
