"""
LiteMCP Base Utility Class - Provides common functions and methods

The base class for all MCP servers, containing common startup methods and error handling.
When developing new tools, testers only need to inherit from this base class and focus on business logic implementation.
"""

import sys
import os
import threading
import time
import atexit
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from abc import ABC, abstractmethod
from src.core.registry import server_registry, ServerInfo
from src.core.utils import get_project_root
from src.core.logger import LoggerMixin
from fastmcp.server.dependencies import get_http_headers

# Automatically ensure project root is in Python path
project_root = get_project_root()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class BaseMCPServer(LoggerMixin, ABC):
    """Base class for MCP servers

    Provides common functionality for all MCP servers:
    - Standard startup methods (STDIO, HTTP, SSE)
    - Unified error handling
    - Automatic server registration
    - Abstract tool registration interface
    - Unified logging
    - CORS support

    Subclasses only need to:
    1. Implement the _register_tools() method
    2. Call the parent class's initialization method
    """

    def __init__(self, name: str, enable_cors: bool = True):
        """Initialize MCP server

        Args:
            name: Server name, used for MCP protocol identification
            enable_cors: Whether to enable CORS support (enabled by default)
        """
        super().__init__()
        self.name = name
        self.enable_cors = enable_cors
        self.mcp = FastMCP(name=self.name)
        self._server_id = None  # Server ID after registration

        # Subclasses must implement tool registration
        self._register_tools()

    def _create_cors_middleware(self):
        """Create CORS middleware"""
        if not self.enable_cors:
            return []
        try:
            cors_middleware = Middleware(
                CORSMiddleware,
                allow_origins=["*"],  # Allow all origins
                allow_credentials=True,
                allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
                allow_headers=["*"],  # Allow all request headers
                expose_headers=["*"],  # Expose all response headers
            )

            self.logger.info("[OK] CORS support enabled")
            return [cors_middleware]

        except ImportError as e:
            self.logger.warning(f"[!] Failed to import CORS middleware: {e}")
            self.logger.warning("[!] Please ensure starlette is installed")
            return []
        except Exception as e:
            self.logger.error(f"[!] Failed to create CORS middleware: {e}")
            return []

    @abstractmethod
    def _register_tools(self):
        """Tool registration method - must be implemented by subclasses

        Use the @self.mcp.tool() decorator within this method to register specific tool functions.

        Example:
            @self.mcp.tool()
            def my_tool(param: str) -> str:
                return f"Processed: {param}"
        """
        pass

    def get_tool_names(self) -> list[str]:
        """Get the list of registered tool names

        Returns:
            list[str]: List of tool names
        """
        try:
            # FastMCP tools are stored in _tool_manager._tools
            if hasattr(self.mcp, '_tool_manager') and hasattr(self.mcp._tool_manager, '_tools'):
                tools_dict = self.mcp._tool_manager._tools
                if tools_dict:
                    return list(tools_dict.keys())
            return []
        except Exception:
            return []

    def _register_to_registry(self, transport: str, host: str = "localhost", port: int = 8000):
        """Register server to registry"""
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                server_info = ServerInfo(
                    name=self.name.replace("LiteMCP-", "").lower(),
                    server_type=self.name.replace("LiteMCP-", "").lower(),
                    transport=transport,
                    host=host,
                    port=port,
                    pid=os.getpid(),
                    python_path=sys.executable,
                    server_file=__file__
                )

                if server_registry.register_server(server_info):
                    self._server_id = f"{server_info.name}-{transport}"
                    if transport in ["http", "sse"]:
                        self._server_id += f"-{port}"

                    # Register cleanup on exit
                    atexit.register(self._unregister_from_registry)
                    self.logger.info(f"[OK] Server registered to config API: {self._server_id}")
                    return True
                else:
                    self.logger.warning(f"[!] Registration failed, attempt {attempt + 1}/{max_retries}")

            except Exception as e:
                self.logger.error(f"[!] Error registering server (attempt {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                time.sleep(retry_delay)

        self.logger.error(f"[X] Server registration failed after {max_retries} attempts")
        return False

    def _unregister_from_registry(self):
        """Unregister server from registry"""
        if self._server_id:
            try:
                from src.core.registry import server_registry
                server_registry.unregister_server(self._server_id)
                self.logger.info(f"[OK] Server unregistered from config API: {self._server_id}")
            except Exception as e:
                self.logger.error(f"[!] Error unregistering server: {e}")

    def run(self):
        """Run MCP server - STDIO mode

        Standard input/output mode, suitable for:
        - Local development and testing
        - Claude Desktop integration
        - Cursor IDE integration
        """
        try:
            # Register STDIO server (no port needed)
            self._register_to_registry("stdio")
            self.mcp.run()
        except Exception as e:
            self.logger.error(f"Server runtime error: {e}")
            raise

    def run_http(self, host: str = "localhost", port: int = 8000):
        """Run MCP server - HTTP mode (Streamable HTTP)

        HTTP transport mode, suitable for:
        - Network deployment
        - Remote access
        - Containerized environments
        - Microservice architectures

        Args:
            host: Host address to listen on
            port: Port to listen on
        """
        try:
            # Register HTTP server
            self._register_to_registry("http", host, port)

            # Create middleware (including possible CORS middleware)
            middleware = self._create_cors_middleware()

            self.mcp.run(
                transport="streamable-http",
                host=host,
                port=port,
                middleware=middleware
            )
        except Exception as e:
            self.logger.error(f"HTTP server runtime error: {e}")
            raise

    def run_sse(self, host: str = "localhost", port: int = 8000):
        """Run MCP server - SSE mode

        Server-Sent Events mode, suitable for:
        - Web integration
        - Browser direct connection
        - Real-time communication scenarios
        - Event-driven architectures

        Args:
            host: Host address to listen on
            port: Port to listen on
        """
        try:
            # Delayed registration in separate thread to ensure server is started
            def delayed_register():
                # Fixed 3-second delay to ensure full server startup
                delay = 3.0
                self.logger.info(f" {self.name} delayed registration thread started, waiting {delay} seconds...")
                time.sleep(delay)
                self.logger.info(f"> {self.name} starting registration to config API...")
                self._register_to_registry("sse", host, port)
                self.logger.info(f"[OK] {self.name} registration thread completed")

            registration_thread = threading.Thread(target=delayed_register, daemon=True)
            registration_thread.start()

            # Create middleware (including possible CORS middleware)
            middleware = self._create_cors_middleware()

            self.mcp.run(
                transport="sse",
                host=host,
                port=port,
                middleware=middleware
            )
        except Exception as e:
            self.logger.error(f"SSE server runtime error: {e}")
            raise

    def get_server_info(self) -> dict:
        """Get server information

        Returns:
            dict: Dictionary containing server name, description and other info
        """
        return {
            "name": self.name,
            "class": self.__class__.__name__,
            "transport_modes": ["stdio", "http", "sse"],
            "server_id": self._server_id,
            "cors_enabled": self.enable_cors
        }

    @staticmethod
    def get_current_request():
        """Get current HTTP request object"""
        return get_http_headers()
