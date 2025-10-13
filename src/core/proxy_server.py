#!/usr/bin/env python3
"""
LiteMCP Reverse Proxy Server


A lightweight reverse proxy server that works similarly to nginx.
Solves the dynamic port allocation issue for MCP servers by providing a unified access point.
Clients can access different MCP servers through fixed domain+path combinations without needing to know specific port numbers.


Supported routing paths:
- /mcp/{server_name}/* -> Routes to corresponding server's HTTP endpoint
- /sse/{server_name}/* -> Routes to corresponding server's SSE endpoint
- /messages/* -> Routes to corresponding server's messages endpoint
"""

import asyncio
import time
import random
import re
import json
import traceback
from typing import Dict, Optional, Any
import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import Headers
import uvicorn
from contextlib import asynccontextmanager

from src.core.logger import get_logger
from src.core.utils import get_local_ip
from src.core.config import settings
from src.core.registry import server_registry
from src.core.registry import ServerInfo


class MCPProxyServer:
    """MCP Reverse Proxy Server - Simplified Version"""
    def __init__(self, host: str = None, port: int = None):
        # Use config file or provided parameters
        self.host = host or "localhost"
        self.port = port or settings.proxy_server.port
        self.logger = get_logger("litemcp.proxy")

        # Timeout configurations
        self.timeout = settings.proxy_server.timeout
        self.connect_timeout = settings.proxy_server.connect_timeout

        # Server mapping table: server_name -> {"host": host, "port": port, "status": "running"}
        self.server_mapping: Dict[str, Dict[str, Any]] = {}

        # Session mapping table: session_id -> {"server_name": str, "created_at": float}
        self.session_mapping: Dict[str, Dict[str, Any]] = {}

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

        # Async lock for registry operations
        self._registry_lock = asyncio.Lock()

        # Create FastAPI application
        self.app = self._create_app()

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Application lifecycle management - Simplified version without connection pool management"""
        # Load existing servers from registry
        self._load_servers_from_registry()

        # Start periodic cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

        self.logger.info("Proxy server initialization completed")
        self.logger.info(
            "Using independent request mode: Creates separate HTTP client per request with no connection limit")
        yield

        # Cleanup on shutdown
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Proxy server has been shut down")

    def _load_servers_from_registry(self):
        """Load server information from registry into memory mapping"""
        try:
            # Get all server information from registry
            all_servers = server_registry.get_all_servers()
            loaded_count = 0
            active_count = 0

            self.logger.info(f"Starting to load servers from registry, found {len(all_servers)} servers")

            for server_id, server_info in all_servers.items():
                self.logger.debug(
                    f"Checking server: {server_info.name} ({server_info.transport}) -> {server_info.host}:{server_info.port}")

                # Only load network servers (HTTP/SSE), skip STDIO
                if server_info.transport not in ["http", "sse"]:
                    self.logger.debug(
                        f"Skipping non-network server: {server_info.name} (transport: {server_info.transport})")
                    continue

                # Check if server is still alive
                if not self._is_server_alive(server_info):
                    self.logger.debug(
                        f"Skipping inactive server: {server_info.name} ({server_info.host}:{server_info.port})")
                    continue

                # Load into memory mapping
                self.server_mapping[server_info.name] = {
                    "host": server_info.host,
                    "port": server_info.port,
                    "status": "running",
                    "registered_at": asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0
                }

                loaded_count += 1
                active_count += 1
                self.logger.info(
                    f"Loaded server from registry: {server_info.name} -> {server_info.host}:{server_info.port}")

            if loaded_count > 0:
                self.logger.info(f"Successfully loaded {loaded_count} servers from registry into memory mapping")
                self.logger.debug(f"Current memory mapping: {list(self.server_mapping.keys())}")
            else:
                self.logger.info("No available network servers found in registry")
        except Exception as e:
            self.logger.error(f"Failed to load servers from registry: {e}")
            self.logger.error(f"Error stack trace: {traceback.format_exc()}")

    def _is_server_alive(self, server_info) -> bool:
        """Check if the server is still running"""
        try:
            # First check if the process exists
            if server_info.pid:
                import psutil
                if not psutil.pid_exists(server_info.pid):
                    return False

            # For network servers, check if the port is accessible
            if server_info.transport in ["http", "sse"]:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)  # 1 second timeout
                try:
                    result = sock.connect_ex((server_info.host, server_info.port))
                    return result == 0
                finally:
                    sock.close()
            return True
        except Exception as e:
            self.logger.debug(f"Failed to check server status: {server_info.name}, error: {e}")
            return False

    def _create_app(self) -> FastAPI:
        """Create FastAPI application"""
        app = FastAPI(
            title="LiteMCP Proxy Server",
            description="MCP server reverse proxy",
            version="1.0.0",
            lifespan=self.lifespan
        )

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
            allow_headers=["*"],
            expose_headers=["*"],
        )

        # Register routes
        self._register_routes(app)
        return app

    @staticmethod
    def _prepare_request_headers(request_headers: Headers) -> dict:
        """Prepare request headers for forwarding by removing unsuitable headers"""
        headers = dict(request_headers)
        headers_to_remove = ["host", "content-length", "connection", "keep-alive", "proxy-connection"]
        for header in headers_to_remove:
            headers.pop(header, None)
        return headers

    def _prepare_response_headers(self, response_headers: dict) -> dict:
        """Prepare response headers with CORS support"""
        headers = dict(response_headers)
        # Remove problematic response headers
        headers.pop("content-length", None)
        headers.pop("transfer-encoding", None)
        # Add CORS headers
        headers.update(self._get_cors_headers())
        return headers

    @staticmethod
    def _get_cors_headers() -> dict:
        """Get CORS response headers"""
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Expose-Headers": "*",
            "Access-Control-Max-Age": "3600"
        }

    @staticmethod
    def _should_use_sse_streaming(request: Request, accept_header: str, content_type: str) -> bool:
        """Determine whether SSE streaming should be used

        Args:
            request: FastAPI request object
            accept_header: Accept header content (converted to lowercase)
            content_type: Content-Type header content (converted to lowercase)

        Returns:
            bool: Whether SSE streaming should be used
        """
        # 1. If Accept header doesn't contain text/event-stream, definitely no SSE needed
        if "text/event-stream" not in accept_header:
            return False

        # 2. For POST/PUT/PATCH requests with JSON data, prioritize JSON response
        if request.method in ["POST", "PUT", "PATCH"]:
            if "application/json" in content_type:
                # Check if Accept header explicitly prioritizes text/event-stream
                # If Accept header is single type like "text/event-stream", use SSE
                # If Accept header has multiple types like "application/json, text/event-stream", prioritize JSON
                accept_types = [t.strip() for t in accept_header.split(',')]

                # If first Accept type is text/event-stream, or only text/event-stream exists, use SSE
                if (len(accept_types) == 1 and "text/event-stream" in accept_types[0]) or \
                        (len(accept_types) > 1 and "text/event-stream" in accept_types[0]):
                    return True

                # Otherwise for JSON requests, prioritize JSON response
                return False

        # 3. For GET requests with text/event-stream in Accept header, use SSE
        if request.method == "GET":
            return True

        # 4. Default to no SSE for other cases
        return False

    def _get_default_server_info(self) -> tuple[str, str, int]:
        """Get default server information"""
        if not self.server_mapping:
            raise HTTPException(status_code=404, detail="No available MCP servers")

        server_name = list(self.server_mapping.keys())[0]
        server_info = self.server_mapping[server_name]
        target_host = server_info["host"]
        target_port = server_info["port"]
        return server_name, target_host, target_port

    @staticmethod
    def _build_target_url(base_url: str, request: Request) -> str:
        """Construct target URL with query parameters"""
        target_url = base_url
        query_params = str(request.url.query) if request.url.query else ""
        if query_params:
            target_url += f"?{query_params}"
        return target_url

    def _cleanup_sessions_by_server(self, server_name: str, reason: str = "Server unavailable") -> None:
        """Clean up all session mappings for the specified server"""
        if not server_name:
            return

        sessions_to_remove = []
        for session_id, info in self.session_mapping.items():
            if info.get("server_name") == server_name:
                sessions_to_remove.append(session_id)

        if sessions_to_remove:
            for session_id in sessions_to_remove:
                del self.session_mapping[session_id]

            self.logger.info(f"Cleaned up {len(sessions_to_remove)} sessions for server {server_name} ({reason})")
            self.logger.debug(f"Cleaned sessions: {sessions_to_remove}")
            self.logger.debug(f"Remaining sessions count: {len(self.session_mapping)}")
        else:
            self.logger.debug(f"No associated sessions found to clean up for server {server_name}")

    def _handle_connection_error(self, request_id: str, server_name: str, error: Exception,
                                 context: str = "request") -> bool:
        """Handle connection errors and determine whether to clean up sessions

        Args:
            request_id: Request ID for logging
            server_name: Server name for session cleanup
            error: Exception that occurred
            context: Context description (e.g., "request", "SSE")

        Returns:
            bool: Whether sessions were cleaned up
        """
        # Only clean up sessions for serious network or connection issues
        # Business logic errors like tool call failures should not cause service to be considered unavailable
        error_str = str(error).lower()
        network_keywords = [
            'connection', 'network', 'timeout', 'refused', 'unreachable',
            'peer closed', 'broken pipe', 'connection reset'
        ]

        if any(keyword in error_str for keyword in network_keywords):
            self.logger.warning(
                f"[{request_id}] Detected network connection issue, cleaning up sessions for server {server_name}")
            self._cleanup_sessions_by_server(server_name, f"Network connection exception: {str(error)}")
            return True
        else:
            self.logger.info(f"[{request_id}] {context} business logic error, not cleaning up sessions: {str(error)}")
            return False

    async def _forward_request(self, request: Request, target_url: str, is_sse: bool = False,
                               server_name: str = None) -> Response:
        """Generic request forwarding method - Creates independent client for each request with no connection limit"""
        request_id = f"{int(time.time())}-{random.randint(1000, 9999)}"

        try:
            # Get request body
            body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None

            # Prepare request headers
            headers = self._prepare_request_headers(request.headers)

            # Smart SSE detection: More precise logic
            accept_header = request.headers.get("accept", "").lower()
            content_type = request.headers.get("content-type", "").lower()

            # Determine if SSE streaming should be used
            expects_sse = self._should_use_sse_streaming(request, accept_header, content_type)

            # If client expects SSE response, switch to streaming mode even if path isn't /sse/
            if expects_sse and not is_sse:
                self.logger.info(
                    f"[{request_id}] Detected SSE expected request (Accept: {accept_header}, Method: {request.method}), switching to streaming mode")
                is_sse = True

            self.logger.info(f"[{request_id}] Forwarding request: {request.method} {target_url} (SSE mode: {is_sse})")

            # For SSE requests, return streaming response
            if is_sse:
                return StreamingResponse(
                    self._stream_response(request.method, target_url, headers, body, request_id, server_name),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        **self._get_cors_headers()
                    }
                )
            else:
                # Regular HTTP request - Create independent client
                async with httpx.AsyncClient(
                        timeout=httpx.Timeout(
                            timeout=self.timeout,
                            connect=self.connect_timeout
                        ),
                        follow_redirects=True
                ) as client:
                    response = await client.request(
                        method=request.method,
                        url=target_url,
                        headers=headers,
                        content=body,
                        follow_redirects=True
                    )

                    self.logger.info(f"[{request_id}] Response status: {response.status_code}")

                    # Process response headers
                    response_headers = self._prepare_response_headers(response.headers)

                    return Response(
                        content=response.content,
                        status_code=response.status_code,
                        headers=response_headers
                    )

        except httpx.ConnectError as e:
            self.logger.error(f"[{request_id}] Connection failed: {target_url}, Error details: {str(e)}")
            # When server connection fails, clean up all sessions for this server
            self._cleanup_sessions_by_server(server_name, "Connection failed")
            raise HTTPException(status_code=503, detail="Target server unavailable")
        except httpx.TimeoutException as e:
            self.logger.error(f"[{request_id}] Request timeout: {target_url}, Error details: {str(e)}")
            # When server times out, clean up all sessions for this server
            self._cleanup_sessions_by_server(server_name, "Request timeout")
            raise HTTPException(status_code=504, detail="Request timeout")
        except Exception as e:
            self.logger.error(f"[{request_id}] Request forwarding failed: {target_url}")
            self.logger.error(f"[{request_id}] Error details: {str(e)}")
            self.logger.error(f"[{request_id}] Error stack: {traceback.format_exc()}")

            # Handle connection error and determine whether to clean up sessions
            self._handle_connection_error(request_id, server_name, e, "request")

            raise HTTPException(status_code=500, detail=f"Request forwarding failed: {str(e)}")

    async def _stream_response(self, method: str, url: str,
                               headers: dict, body: bytes, request_id: str, server_name: str = None):
        """Handle streaming response - Create independent SSE client"""
        try:
            self.logger.info(f"[{request_id}] Establishing stream connection to: {url}")

            # Create independent client for SSE with reasonable connect timeout but no read timeout
            async with httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        timeout=None,  # No read timeout since SSE is persistent
                        connect=self.connect_timeout  # Keep connect timeout
                    ),
                    follow_redirects=True
            ) as client:
                async with client.stream(method, url, headers=headers, content=body) as response:
                    self.logger.info(f"[{request_id}] Stream connection established: {response.status_code}")

                    # Check response status code
                    if response.status_code != 200:
                        self.logger.warning(f"[{request_id}] Abnormal stream response status: {response.status_code}")
                        # Still attempt to forward response content even if not 200
                        error_content = await response.aread()
                        yield error_content.decode('utf-8', errors='ignore')
                        return

                    chunk_count = 0
                    async for chunk in response.aiter_text():
                        if chunk:
                            chunk_count += 1
                            if chunk_count % 50 == 1:  # Reduce log frequency to every 50 chunks
                                self.logger.debug(f"[{request_id}] Processed {chunk_count} chunks")

                            # Attempt to parse session_id and record mapping
                            if server_name:
                                self._extract_and_record_session_id(chunk, server_name, request_id)
                            yield chunk

                    self.logger.info(f"[{request_id}] Stream connection ended, total {chunk_count} chunks processed")

        except httpx.ConnectError as e:
            self.logger.error(f"[{request_id}] SSE connection failed: {url}, Error: {str(e)}")
            self._cleanup_sessions_by_server(server_name, f"SSE connection failed: {str(e)}")
            yield f"event: error\ndata: {{\"error\": \"Connection failed: {str(e)}\"}}\n\n"
        except httpx.TimeoutException as e:
            self.logger.error(f"[{request_id}] SSE connection timeout: {url}, Error: {str(e)}")
            self._cleanup_sessions_by_server(server_name, f"SSE connection timeout: {str(e)}")
            yield f"event: error\ndata: {{\"error\": \"Connection timeout: {str(e)}\"}}\n\n"
        except Exception as e:
            self.logger.error(f"[{request_id}] Stream processing failed: {url}")
            self.logger.error(f"[{request_id}] Error details: {str(e)}")
            self.logger.error(f"[{request_id}] Error stack: {traceback.format_exc()}")

            # Handle connection error and determine whether to clean up sessions
            self._handle_connection_error(request_id, server_name, e, "SSE")

            yield f"event: error\ndata: {{\"error\": \"Stream failed: {str(e)}\"}}\n\n"

    def _register_routes(self, app: FastAPI):
        """Register routes"""

        @app.options("/{path:path}")
        async def options_handler(path: str):
            """Handle OPTIONS preflight requests"""
            return Response(status_code=204, headers=self._get_cors_headers())

        @app.get("/")
        async def root():
            """Root endpoint"""
            return {
                "service": "LiteMCP Proxy Server",
                "version": "1.0.0",
                "endpoints": {
                    "mcp": "/mcp/{server_name}/*",
                    "sse": "/sse/{server_name}/* (GET only)",
                    "messages": "/messages/*",
                    "status": "/proxy/status",
                    "mapping": "/proxy/mapping",
                    "health": "/proxy/health"
                },
                "available_servers": list(self.server_mapping.keys()),
                "usage_tips": {
                    "sse_connection": "Use GET method: GET /sse/{server_name}/",
                    "messages_request": "Use session_id for auto-routing: POST /messages/?session_id=xxx",
                    "explicit_routing": "Or specify server: POST /messages/?server_name={server_name}"
                }
            }

        @app.get("/proxy/status")
        async def proxy_status():
            """Proxy server status"""
            return {
                "proxy": {
                    "host": self.host,
                    "port": self.port,
                    "status": "running"
                },
                "servers": self.server_mapping,
                "total_servers": len(self.server_mapping),
                "sessions": {
                    "total_sessions": len(self.session_mapping),
                    "active_sessions": {
                        session_id: {
                            "server_name": info["server_name"],
                            "created_at": info["created_at"],
                            "age_seconds": int(time.time() - info["created_at"])
                        }
                        for session_id, info in self.session_mapping.items()
                    }
                }
            }

        @app.get("/proxy/mapping")
        async def server_mapping():
            """Get server mapping table"""
            return self.server_mapping

        @app.get("/proxy/health")
        async def health_check():
            """Proxy server health check"""
            health_data = {
                "proxy_status": "healthy",
                "timestamp": time.time(),
                "servers": {},
                "session_stats": {
                    "total_sessions": len(self.session_mapping),
                    "oldest_session_age": 0,
                    "newest_session_age": 0
                }
            }

            # Check connection status for each server
            for server_name, server_info in self.server_mapping.items():
                try:
                    health_url = f"http://{server_info['host']}:{server_info['port']}/sse/"
                    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout=3)) as client:
                        response = await client.get(health_url)
                        health_data["servers"][server_name] = {
                            "status": "healthy" if response.status_code == 200 else "unhealthy",
                            "response_time_ms": 0,  # Can calculate response time here
                            "last_check": time.time()
                        }
                except Exception as e:
                    health_data["servers"][server_name] = {
                        "status": "unreachable",
                        "error": str(e),
                        "last_check": time.time()
                    }

            # Calculate session statistics
            if self.session_mapping:
                current_time = time.time()
                ages = [current_time - info["created_at"] for info in self.session_mapping.values()]
                health_data["session_stats"]["oldest_session_age"] = int(max(ages))
                health_data["session_stats"]["newest_session_age"] = int(min(ages))

            return health_data

        @app.post("/proxy/reload")
        async def reload_servers():
            """Reload server configuration"""
            try:
                old_count = len(self.server_mapping)
                self.logger.info("Received reload request, starting to reload server configuration...")

                # Clear current memory mapping
                self.server_mapping.clear()

                # Reload servers from registry
                self._load_servers_from_registry()

                new_count = len(self.server_mapping)
                self.logger.info(f"Reload completed: {old_count} -> {new_count} servers")

                return {
                    "status": "success",
                    "message": f"Reload completed, server count: {old_count} -> {new_count}",
                    "servers": list(self.server_mapping.keys())
                }
            except Exception as e:
                self.logger.error(f"Reload failed: {e}")
                return {
                    "status": "error",
                    "message": f"Reload failed: {str(e)}"
                }

        @app.post("/proxy/register")
        async def register_server(request: Request):
            """Register MCP server"""
            # Add request ID and client info for debugging
            request_id = f"{int(time.time())}-{random.randint(1000, 9999)}"
            client_info = f"{request.client.host}:{request.client.port}" if request.client else "unknown"

            self.logger.info(f"[{request_id}] Received registration request from: {client_info}")

            try:
                # Parse request data
                body = await request.json()
                server_name = body.get("server_name")
                host = body.get("host", "localhost")
                port = body.get("port")
                transport = body.get("transport", "sse")  # Get transport from request
                pid = body.get("pid")  # Get PID from request

                self.logger.info(
                    f"[{request_id}] Registration params: server_name={server_name}, host={host}, port={port}, transport={transport}, pid={pid}")

                if not server_name or not port:
                    self.logger.error(f"[{request_id}] Missing required parameters")
                    return {"error": "Missing required parameters: server_name, port"}

                port = int(port)

                # Use lock to protect registry operations
                self.logger.info(f"[{request_id}] Waiting to acquire registry lock...")
                async with self._registry_lock:
                    self.logger.info(f"[{request_id}] Acquired registry lock, starting registration")

                    # Check if server with same name already registered
                    existing_key = self._find_existing_server_in_registry(server_name)
                    if existing_key:
                        self.logger.info(f"[{request_id}] Found existing server: {existing_key}")
                    else:
                        self.logger.info(f"[{request_id}] No existing server found, new registration")

                    # Update memory mapping
                    self._update_memory_mapping(server_name, host, port)
                    self.logger.info(f"[{request_id}] Memory mapping updated")

                    # Register to persistent storage (pass PID and transport)
                    self.logger.info(f"[{request_id}] Starting registration to persistent storage...")
                    success = self._register_to_registry(server_name, host, port, existing_key, transport, pid)
                    self.logger.info(f"[{request_id}] Persistent storage registration result: {success}")

                    if success:
                        message = f"Server registered: {server_name} -> {host}:{port} (transport: {transport}"
                        if pid:
                            message += f", PID: {pid}"
                        message += ")"

                        self.logger.info(f"[{request_id}] {message}")
                        return {
                            "status": "success",
                            "message": message,
                            "request_id": request_id,
                            "server_info": {
                                "name": server_name,
                                "host": host,
                                "port": port,
                                "transport": transport,
                                "pid": pid
                            }
                        }
                    else:
                        # Rollback memory mapping if registration failed
                        self._remove_from_memory_mapping(server_name)
                        error_msg = f"Registration failed: {server_name} -> {host}:{port}"
                        self.logger.error(f"[{request_id}] {error_msg}")
                        return {"error": error_msg, "request_id": request_id}

            except Exception as e:
                self.logger.error(f"[{request_id}] Server registration failed: {e}")
                import traceback
                self.logger.error(f"[{request_id}] Error stack: {traceback.format_exc()}")
                return {"error": f"Registration failed: {str(e)}", "request_id": request_id}

        @app.delete("/proxy/unregister/{server_name}")
        async def unregister_server(server_name: str):
            """Unregister server"""
            # Check if server exists in memory mapping
            if server_name not in self.server_mapping:
                raise HTTPException(status_code=404, detail=f"Server {server_name} not registered in proxy")

            try:
                # Use lock to protect registry operations
                async with self._registry_lock:
                    # Clean up all sessions related to this server
                    self._cleanup_sessions_by_server(server_name, "Server unregistration")

                    # Remove from memory mapping
                    removed_from_memory = self._remove_from_memory_mapping(server_name)

                    # Remove from registry file
                    removed_from_registry = self._unregister_from_registry(server_name)

                    # Log results
                    if removed_from_registry:
                        self.logger.info(
                            f"Fully unregistered server: {server_name} (from both memory mapping and registry file)")
                    else:
                        self.logger.warning(
                            f"Only removed server from memory mapping: {server_name} (not found in registry file)")

                    return {
                        "status": "success",
                        "server_name": server_name,
                        "removed_from_memory": removed_from_memory,
                        "removed_from_registry": removed_from_registry,
                        "message": f"Server {server_name} unregistered successfully"
                    }

            except Exception as e:
                self.logger.error(f"Failed to unregister server: {server_name}, error: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to unregister server: {str(e)}"
                )

        # MCP HTTP Proxy Route
        @app.api_route(f"/{settings.proxy_server.mcp_prefix}/{{server_name:path}}",
                       methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
        async def proxy_mcp_http(server_name: str, request: Request):
            """Proxy MCP HTTP requests"""
            return await self._proxy_request(server_name, request, settings.proxy_server.mcp_prefix)

        # SSE Proxy Route - GET method only
        @app.get(f"/{settings.proxy_server.sse_prefix}/{{server_name:path}}")
        async def proxy_sse_get(server_name: str, request: Request):
            """Proxy SSE requests - GET method"""
            return await self._proxy_request(server_name, request, settings.proxy_server.sse_prefix, is_sse=True)

        # SSE Endpoint Invalid Method Handler
        @app.api_route(f"/{settings.proxy_server.sse_prefix}/{{server_name:path}}",
                       methods=["POST", "PUT", "DELETE", "PATCH", "HEAD"])
        async def proxy_sse_invalid_method(server_name: str, request: Request):
            """SSE endpoint invalid method handler"""
            return Response(
                content=json.dumps({
                    "error": "Method Not Allowed for SSE endpoint",
                    "message": f"SSE endpoints only support GET requests, received {request.method}",
                    "correct_usage": f"GET {request.url.path}",
                    "tip": "Server-Sent Events require GET method for establishing connections"
                }, ensure_ascii=False, indent=2),
                status_code=405,
                headers={
                    "Content-Type": "application/json",
                    "Allow": "GET, OPTIONS",
                    **self._get_cors_headers()
                }
            )

        # Messages Proxy Routes
        @app.api_route("/messages", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
        @app.api_route("/messages/", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
        async def proxy_messages_root(request: Request):
            """Proxy messages root path requests"""
            return await self._proxy_messages_request("", request)

        @app.api_route("/messages/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
        async def proxy_messages_path(path: str, request: Request):
            """Proxy messages subpath requests"""
            return await self._proxy_messages_request(path, request)

        # Generic Fallback Route
        @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
        async def proxy_fallback(path: str, request: Request):
            """Proxy other requests to default server"""
            # Skip already handled paths
            if (path.startswith("proxy/") or
                    path.startswith("mcp/") or
                    path.startswith("sse/") or
                    path.startswith("messages/") or
                    path == ""):
                raise HTTPException(status_code=404, detail="Not Found")

            # Auto-forward when only one server exists
            if len(self.server_mapping) == 1:
                server_name, target_host, target_port = self._get_default_server_info()
                target_url = self._build_target_url(f"http://{target_host}:{target_port}/{path}", request)
                return await self._forward_request(request, target_url, False, server_name)
            elif len(self.server_mapping) > 1:
                available_servers = list(self.server_mapping.keys())
                return {
                    "message": "Target server must be specified in multi-server environment",
                    "available_servers": available_servers,
                    "endpoints": {
                        "mcp": f"/mcp/{{server_name}}/{path}",
                        "sse": f"/sse/{{server_name}}/{path}",
                        "messages": f"/messages/{path}?server_name={{server_name}}"
                    }
                }
            else:
                raise HTTPException(status_code=503, detail="No available MCP servers")

    @staticmethod
    def _find_existing_server_in_registry(server_name: str) -> Optional[str]:
        """Check if a server with the same name already exists in the registry

        Args:
            server_name: Name of the server to find

        Returns:
            The existing server's key if found, otherwise None
        """
        for key, server_info in server_registry.get_all_servers().items():
            if server_info.name == server_name:
                return key
        return None

    def _register_to_registry(self, server_name: str, host: str, port: int, existing_key: str = None,
                              transport: str = None, pid: int = None) -> bool:
        """Register the server to persistent registry file

        Args:
            server_name: Server name
            host: Host address
            port: Port number
            existing_key: Existing server key (if updating)
            transport: Transport protocol
            pid: Process ID

        Returns:
            Whether registration was successful
        """

        try:
            # If transport not provided, try to get from existing registry
            if not transport:
                transport = "sse"  # Default value

                # Find existing server record to get correct transport protocol
                existing_servers = server_registry.get_all_servers()
                for server_id, server_info in existing_servers.items():
                    if server_info.name == server_name:
                        transport = server_info.transport
                        self.logger.info(f"Got transport protocol from existing record: {server_name} -> {transport}")
                        break

                # If no existing record found, use default
                if transport == "sse":
                    self.logger.warning(
                        f"No existing record found for server {server_name}, using default transport: {transport}")
            else:
                self.logger.info(f"Using provided transport protocol: {server_name} -> {transport}")

            # Create server info object
            server_info = ServerInfo(
                name=server_name,
                server_type=server_name,
                transport=transport,  # Use determined transport protocol
                host=host,
                port=port,
                pid=pid  # Set PID
            )

            # If existing key exists, unregister first
            if existing_key:
                server_registry.unregister_server(existing_key)
                self.logger.info(f"Unregistering existing server first: {existing_key}")

            # Register new server
            success = server_registry.register_server(server_info)
            if success:
                message = f"Registered new server to registry: {server_name} -> {host}:{port} (transport: {transport}"
                if pid:
                    message += f", PID: {pid}"
                message += ")"
                self.logger.info(message)
            else:
                self.logger.error(f"Registry operation failed: {server_name} -> {host}:{port}")
            return success
        except Exception as e:
            self.logger.error(f"Registry operation failed: {server_name} -> {host}:{port}, error: {e}")
            return False

    def _unregister_from_registry(self, server_name: str) -> bool:
        """Remove server from registry file

        Args:
            server_name: Server name

        Returns:
            Whether the server was found and successfully removed
        """
        try:
            existing_key = self._find_existing_server_in_registry(server_name)
            if existing_key:
                server_registry.unregister_server(existing_key)
                self.logger.info(f"Removed server from registry: {server_name}")
                return True
            else:
                self.logger.warning(f"Server not found in registry: {server_name}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to remove server from registry: {server_name}, error: {e}")
            return False

    def _update_memory_mapping(self, server_name: str, host: str, port: int):
        """Update memory mapping

        Args:
            server_name: Server name
            host: Host address
            port: Port number
        """
        self.server_mapping[server_name] = {
            "host": host,
            "port": port,
            "status": "running",
            "registered_at": asyncio.get_event_loop().time()
        }

    def _remove_from_memory_mapping(self, server_name: str) -> bool:
        """Remove server from memory mapping

        Args:
            server_name: Server name

        Returns:
            Whether the removal was successful
        """
        if server_name in self.server_mapping:
            del self.server_mapping[server_name]
            return True
        return False

    async def _proxy_request(self, path: str, request: Request, endpoint_type: str, is_sse: bool = False) -> Response:
        """Proxy request to target server"""
        # Parse server name and remaining path
        path_parts = path.split("/", 1)
        server_name = path_parts[0]
        remaining_path = "/" + path_parts[1] if len(path_parts) > 1 else ""

        # Add debug logs
        client_host = request.client.host if request.client else "unknown"
        request_id = f"{int(time.time())}-{random.randint(1000, 9999)}"

        self.logger.info(
            f"[{request_id}] {endpoint_type} request from: {client_host}:{request.client.port if request.client else 'unknown'}")
        self.logger.info(f"[{request_id}] Parsed server name: {server_name}, remaining path: {remaining_path}")
        self.logger.info(f"[{request_id}] Request header Host: {request.headers.get('host', 'unknown')}")

        # Check if server is registered
        if server_name not in self.server_mapping:
            self.logger.error(
                f"[{request_id}] Server '{server_name}' not registered. Available servers: {list(self.server_mapping.keys())}")
            raise HTTPException(
                status_code=404,
                detail=f"Server '{server_name}' not registered. Available servers: {list(self.server_mapping.keys())}"
            )

        server_info = self.server_mapping[server_name]
        target_host = server_info["host"]
        target_port = server_info["port"]

        # Build target URL - ensure path ends with slash to avoid redirects
        if not remaining_path:
            # If no remaining path, ensure endpoint ends with slash
            target_url = f"http://{target_host}:{target_port}/{endpoint_type}/"
        else:
            # If there's remaining path, concatenate directly
            target_url = f"http://{target_host}:{target_port}/{endpoint_type}{remaining_path}"

        target_url = self._build_target_url(target_url, request)

        self.logger.info(f"[{request_id}] Target URL: {target_url}")

        return await self._forward_request(request, target_url, is_sse, server_name)

    async def _proxy_messages_request(self, path: str, request: Request) -> Response:
        """Proxy messages requests"""
        # Add detailed debug logs
        client_host = request.client.host if request.client else "unknown"
        request_id = f"{int(time.time())}-{random.randint(1000, 9999)}"

        self.logger.info(
            f"[{request_id}] Messages request from: {client_host}:{request.client.port if request.client else 'unknown'}")
        self.logger.info(f"[{request_id}] Request method: {request.method}, path: {path}")
        self.logger.info(f"[{request_id}] Request header Host: {request.headers.get('host', 'unknown')}")
        self.logger.info(f"[{request_id}] Query parameters: {dict(request.query_params)}")

        # First try to get target server from query params or headers
        server_name = (request.query_params.get('server_name') or
                       request.headers.get('X-MCP-Server-Name') or
                       request.headers.get('Server-Name'))

        # If server_name not specified, try to find from session_id
        if not server_name:
            session_id = request.query_params.get('session_id')
            self.logger.info(f"[{request_id}] No server_name specified, trying to find from session_id: {session_id}")
            self.logger.info(f"[{request_id}] Current session mapping count: {len(self.session_mapping)}")

            if session_id and session_id in self.session_mapping:
                server_name = self.session_mapping[session_id]["server_name"]
                self.logger.info(
                    f"[{request_id}] Found corresponding server for session_id '{session_id}': {server_name}")
            else:
                self.logger.warning(f"[{request_id}] No corresponding server found for session_id '{session_id}'")

        if not server_name:
            if len(self.server_mapping) == 1:
                server_name, target_host, target_port = self._get_default_server_info()
            else:
                available_servers = list(self.server_mapping.keys())
                session_id = request.query_params.get('session_id')
                help_msg = "Please add ?server_name=xxx in query params or X-MCP-Server-Name in headers"
                if session_id:
                    help_msg += f" (No corresponding server found for session_id '{session_id}')"

                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Target server needs to be specified",
                        "available_servers": available_servers,
                        "help": help_msg,
                        "session_info": {
                            "session_id": session_id,
                            "session_found": session_id in self.session_mapping if session_id else False,
                            "total_sessions": len(self.session_mapping)
                        }
                    }
                )
        else:
            if server_name not in self.server_mapping:
                raise HTTPException(
                    status_code=404,
                    detail=f"Server '{server_name}' not registered"
                )
            server_info = self.server_mapping[server_name]
            target_host = server_info["host"]
            target_port = server_info["port"]

        # Build target URL
        if path:
            base_url = f"http://{target_host}:{target_port}/messages/{path}"
        else:
            base_url = f"http://{target_host}:{target_port}/messages/"

        target_url = self._build_target_url(base_url, request)

        # Check if SSE response is expected
        accept_header = request.headers.get("accept", "").lower()
        content_type = request.headers.get("content-type", "").lower()
        expects_sse = self._should_use_sse_streaming(request, accept_header, content_type)

        self.logger.info(f"[{request_id}] Target server: {server_name} -> {target_host}:{target_port}")
        self.logger.info(f"[{request_id}] Target URL: {target_url}")
        if expects_sse:
            self.logger.info(f"[{request_id}] Messages request expects SSE response (Accept: {accept_header}, Method: {request.method})")
        return await self._forward_request(request, target_url, False, server_name)

    def register_server_sync(self, server_name: str, host: str, port: int, transport: str = None):
        """Synchronously register a server"""
        try:
            port = int(port)
        except (ValueError, TypeError):
            self.logger.error(f"Failed to register server: Port must be a valid integer: {port}")
            return False

        is_update = server_name in self.server_mapping
        action = "update" if is_update else "register"

        self.logger.info(f"Starting {action} server: {server_name} -> {host}:{port} (transport: {transport})")

        try:
            # Check if server already exists in registry
            existing_key = self._find_existing_server_in_registry(server_name)

            # Update memory mapping
            self._update_memory_mapping(server_name, host, port)

            # Register to persistent storage
            success = self._register_to_registry(server_name, host, port, existing_key, transport)

            if success:
                self.logger.info(f"Memory mapping updated, current server count: {len(self.server_mapping)}")
                self.logger.debug(f"Current server mapping: {list(self.server_mapping.keys())}")
                self.logger.info(f"Server {action} successful: {server_name} -> {host}:{port}")
                return True
            else:
                # Rollback memory mapping if registration fails
                self._remove_from_memory_mapping(server_name)
                self.logger.error("Registry write failed, rolled back memory mapping")
                return False

        except Exception as e:
            # Remove from memory mapping if registry write fails
            self._remove_from_memory_mapping(server_name)
            self.logger.error(f"Failed to register server: {server_name} -> {host}:{port}, error: {e}")
            return False

    def unregister_server_sync(self, server_name: str):
        """Synchronously unregister a server"""
        if server_name not in self.server_mapping:
            self.logger.warning(f"Attempting to unregister non-existent server: {server_name}")
            return False

        try:
            # Clean up all sessions related to this server
            self._cleanup_sessions_by_server(server_name, "Server unregistration")

            # Remove from memory mapping
            removed_from_memory = self._remove_from_memory_mapping(server_name)

            # Remove from registry file
            removed_from_registry = self._unregister_from_registry(server_name)

            # Log results
            if removed_from_registry:
                self.logger.info(
                    f"Fully unregistered server: {server_name} (from both memory mapping and registry file)")
            else:
                self.logger.warning(
                    f"Only removed server from memory mapping: {server_name} (not found in registry file)")

            return True

        except Exception as e:
            self.logger.error(f"Failed to unregister server: {server_name}, error: {e}")
            return False

    def _extract_and_record_session_id(self, chunk: str, server_name: str, request_id: str):
        """Extract session_id from SSE stream and record the mapping relationship"""
        try:
            # Search for session_id patterns, matching multiple possible formats
            session_patterns = [
                r'"session_id":\s*"([^"]+)"',  # JSON format
                r'session_id=([a-zA-Z0-9\-_]+)',  # URL parameter format
                r'sessionId["\']:\s*["\']([^"\']+)["\']',  # JavaScript format
                r'data:\s*.*"session_id":\s*"([^"]+)"',  # SSE data format
            ]

            for pattern in session_patterns:
                matches = re.findall(pattern, chunk, re.IGNORECASE)
                if matches:
                    session_id = matches[0]

                    # Record session mapping
                    if session_id not in self.session_mapping:
                        self.session_mapping[session_id] = {
                            "server_name": server_name,
                            "created_at": time.time(),
                            "request_id": request_id
                        }
                        self.logger.info(f"[{request_id}] Recorded session mapping: {session_id} -> {server_name}")
                        self.logger.debug(f"[{request_id}] Current session mapping count: {len(self.session_mapping)}")
                        return session_id
                    else:
                        self.logger.debug(
                            f"[{request_id}] session_id already exists: {session_id} -> {self.session_mapping[session_id]['server_name']}")
        except Exception as e:
            self.logger.debug(f"[{request_id}] Failed to parse session_id: {e}")
            self.logger.debug(f"[{request_id}] Chunk content: {chunk[:200]}...")  # Only show first 200 characters
        return None

    async def _periodic_cleanup(self):
        """Periodically clean up orphaned session mappings - only cleans sessions whose corresponding server no longer exists"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes to reduce frequency

                orphan_sessions = []

                # Find orphaned sessions (where the corresponding server is no longer in the mapping)
                for session_id, info in self.session_mapping.items():
                    server_name = info.get("server_name")
                    if server_name and server_name not in self.server_mapping:
                        orphan_sessions.append(session_id)

                # Clean up orphaned sessions
                for session_id in orphan_sessions:
                    server_name = self.session_mapping[session_id].get("server_name", "unknown")
                    del self.session_mapping[session_id]
                    self.logger.debug(
                        f"Cleaned up orphaned session: {session_id} (server {server_name} no longer exists)")

                if orphan_sessions:
                    self.logger.info(
                        f"Cleaned up {len(orphan_sessions)} orphaned sessions, {len(self.session_mapping)} remaining")
                elif len(self.session_mapping) > 0:
                    self.logger.debug(f"Currently {len(self.session_mapping)} active sessions, no cleanup needed")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error cleaning up sessions: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes after error before continuing

    def run(self, **kwargs):
        """Start the proxy server"""
        try:
            local_ip = get_local_ip()
            self.logger.info(f"Starting MCP proxy server: {self.host}:{self.port}")

            if local_ip and local_ip != "127.0.0.1":
                self.logger.info(f"\n> MCP proxy server started")
                self.logger.info(f"   Local access: http://localhost:{self.port}")
                self.logger.info(f"   External access: http://{local_ip}:{self.port}")
                self.logger.info(f"\n Proxy path rules:")
                self.logger.info(f"   MCP HTTP: /mcp/{{server_name}}/*")
                self.logger.info(f"   SSE:      /sse/{{server_name}}/*")
                self.logger.info(f"   Messages: /messages/*?server_name={{server_name}}")
                self.logger.info(f"   Status query: /proxy/status")
                self.logger.info(f"   Mapping query: /proxy/mapping")
                self.logger.info(f"\n[TIP] Simple reverse proxy, similar to nginx")
                self.logger.info(f"[OK] Full CORS support enabled\n")

            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"Failed to start proxy server: {e}")
            raise


# Global proxy server instance
_proxy_server_instance: Optional[MCPProxyServer] = None

def get_proxy_server(host: str = None, port: int = None) -> MCPProxyServer:
    """Get proxy server instance (singleton pattern)"""
    global _proxy_server_instance
    if _proxy_server_instance is None:
        _proxy_server_instance = MCPProxyServer(host=host, port=port)
    return _proxy_server_instance

def register_server_to_proxy(server_name: str, host: str, port: int, transport: str = None):
    """Register MCP server to proxy server"""
    if _proxy_server_instance:
        _proxy_server_instance.register_server_sync(server_name, host, port, transport)

def unregister_server_from_proxy(server_name: str):
    """Unregister MCP server from proxy server"""
    if _proxy_server_instance:
        _proxy_server_instance.unregister_server_sync(server_name)
