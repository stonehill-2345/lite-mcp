"""
Server Registry - Manage running MCP server status

Maintains information about currently active servers, including transport modes, addresses, ports, etc.,
for dynamically generating MCP client configurations.
"""

import json
import sys
import threading
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import time
import urllib.request
import urllib.error
import platform
import psutil
from src.core.utils import is_local_ip

# Cross-platform file locking support
if platform.system() == 'Windows':
    import msvcrt
    HAS_FCNTL = False
else:
    try:
        import fcntl
        HAS_FCNTL = True
    except ImportError:
        HAS_FCNTL = False

from src.core.logger import get_logger
from src.core.utils import get_project_root
from src.tools import AVAILABLE_SERVERS

@dataclass
class ServerInfo:
    """Server information data class"""
    name: str
    server_type: str  # example, calculator, etc.
    transport: str    # stdio, http, sse
    host: str
    port: int
    pid: Optional[int] = None
    started_at: str = ""
    python_path: str = ""
    server_file: str = ""
    
    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if not self.python_path:
            self.python_path = sys.executable
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class ServerRegistry:
    """Server Registry - Singleton pattern"""
    
    _instance = None
    _lock = threading.Lock()
    
    @staticmethod
    def _lock_file(file_handle):
        """Cross-platform file locking"""
        if platform.system() == 'Windows':
            # Windows uses msvcrt
            try:
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
                return True
            except IOError:
                return False
        elif HAS_FCNTL:
            # Unix/Linux 使用 fcntl
            try:
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except IOError:
                return False
        else:
            # Fallback: only use thread locks
            return True
    
    @staticmethod
    def _unlock_file(file_handle):
        """Cross-platform file unlocking"""
        if platform.system() == 'Windows':
            # Windows uses msvcrt
            try:
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            except IOError:
                pass
        elif HAS_FCNTL:
            # Unix/Linux uses fcntl
            try:
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
            except IOError:
                pass

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            # Use absolute path to avoid working directory issues
            project_root = get_project_root()
            self.registry_file = project_root / "runtime" / "registry.json"
            self.servers: Dict[str, ServerInfo] = {}
            self._lock = threading.Lock()

            # Initialize logger
            self.logger = get_logger("litemcp.registry", log_file="registry.log")

            self.load_from_file()
            self.initialized = True

    def register_server(self, server_info: ServerInfo) -> bool:
        """Register server"""
        max_retries = 5
        retry_delay = 0.5

        for attempt in range(max_retries):
            try:
                # Use file lock to ensure atomic operation
                lock_file = self.registry_file.with_suffix('.lock')

                with open(lock_file, 'w') as lock_fd:
                    # Acquire exclusive lock, wait up to 2 seconds
                    if not self._lock_file(lock_fd):
                        # If lock cannot be acquired immediately, wait and retry
                        time.sleep(retry_delay * (attempt + 1))
                        continue

                    try:
                        with self._lock:
                            # Reload file under lock protection
                            self.load_from_file()

                            # Generate unique server identifier
                            server_id = f"{server_info.name}-{server_info.transport}"
                            if server_info.transport in ["http", "sse"]:
                                server_id += f"-{server_info.port}"

                            self.servers[server_id] = server_info
                            self.save_to_file()

                            self.logger.info(f"Server registered to config API: {server_id}")
                            return True
                    finally:
                        # Release file lock
                        self._unlock_file(lock_fd)

            except Exception as e:
                self.logger.warning(f"Error registering server (attempt {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))

        self.logger.error(f"Server registration failed after {max_retries} retries")
        return False

    def unregister_server(self, server_id: str) -> bool:
        """Unregister server"""
        max_retries = 5
        retry_delay = 0.5

        for attempt in range(max_retries):
            try:
                # Use file lock to ensure atomic operation
                lock_file = self.registry_file.with_suffix('.lock')

                with open(lock_file, 'w') as lock_fd:
                    # Acquire exclusive lock, wait up to 2 seconds
                    if not self._lock_file(lock_fd):
                        # If lock cannot be acquired immediately, wait and retry
                        time.sleep(retry_delay * (attempt + 1))
                        continue

                    try:
                        with self._lock:
                            # Reload file under lock protection
                            self.load_from_file()

                            # Check and remove server
                            if server_id in self.servers:
                                del self.servers[server_id]
                                self.save_to_file()
                                self.logger.info(f"Server removed from registry: {server_id}")
                                return True
                            else:
                                self.logger.warning(f"Server not found in registry: {server_id}")
                                return False
                    finally:
                        # Release file lock
                        self._unlock_file(lock_fd)

            except Exception as e:
                self.logger.warning(f"Error unregistering server (attempt {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))

        self.logger.error(f"Failed to unregister server after {max_retries} retries")
        return False

    def get_server(self, server_id: str) -> Optional[ServerInfo]:
        """Get single server information"""
        return self.servers.get(server_id)

    def get_all_servers(self) -> Dict[str, ServerInfo]:
        """Get all server information"""
        return self.servers.copy()

    def get_servers_by_transport(self, transport: str) -> Dict[str, ServerInfo]:
        """Get servers by transport protocol"""
        return {
            server_id: info
            for server_id, info in self.servers.items()
            if info.transport == transport
        }

    def clear_dead_servers(self):
        """Clean up stopped servers (based on PID check and remote health check)"""
        with self._lock:
            dead_servers = []
            for server_id, info in self.servers.items():
                if not self._is_server_alive(info):
                    dead_servers.append(server_id)

            for server_id in dead_servers:
                del self.servers[server_id]

            if dead_servers:
                self.save_to_file()

    def batch_update_servers(self, updates: Dict[str, ServerInfo]):
        """Batch update server information

        Args:
            updates: Mapping from server ID to new server information
        """
        with self._lock:
            for server_id, new_info in updates.items():
                if server_id in self.servers:
                    self.servers[server_id] = new_info
                    self.logger.debug(f"Updated server: {server_id} -> {new_info.name}")

            if updates:
                self.save_to_file()

    def save_to_file(self):
        """Save to file"""
        try:
            data = {
                server_id: info.to_dict()
                for server_id, info in self.servers.items()
            }
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save server registry: {e}")

    def load_from_file(self):
        """Load from file"""
        if not self.registry_file.exists():
            return

        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.servers = {
                server_id: ServerInfo(**info)
                for server_id, info in data.items()
            }
        except Exception as e:
            self.logger.error(f"Failed to load server registry: {e}")
            self.servers = {}

    def generate_mcp_config(self, client_type: str = "cursor") -> Dict[str, Any]:
        """Generate MCP client configuration

        Args:
            client_type: Client type ("cursor", "claude_desktop")

        Returns:
            Detailed configuration dictionary categorized by transport protocol
        """
        # Force reload registry file (handles multi-process scenarios)
        self.load_from_file()
        self.clear_dead_servers()  # Clean up dead processes

        # Initialize result structure
        result: Dict[str, Any] = {
            "client_type": client_type,
            "stdio": [],
            "http": [],
            "sse": [],
            "servers_count": 0,
            "config_example": {"mcpServers": {}},
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Configuration examples (for three transport protocols)
        if client_type == "cursor":
            result["config_example"]["mcpServers"] = {
                "example-stdio": {
                    "command": sys.executable,
                    "args": ["/path/to/your/server.py"],
                    "env": {}
                },
                "example-http": {
                    "url": "http://localhost:8000/mcp"
                },
                "example-sse": {
                    "url": "http://localhost:8000/sse"
                }
            }
        else:  # claude_desktop
            result["config_example"]["mcpServers"] = {
                "example-stdio": {
                    "command": sys.executable,
                    "args": ["/path/to/your/server.py"],
                    "env": {}
                },
                "example-http": {
                    "transport": {
                        "type": "http",
                        "url": "http://localhost:8000/mcp"
                    }
                },
                "example-sse": {
                    "transport": {
                        "type": "sse",
                        "url": "http://localhost:8000/sse"
                    }
                }
            }

        # 1. Add STDIO mode configuration (filesystem-based, always available)
        for server_type, server_info in AVAILABLE_SERVERS.items():
            # Build server file path from module path
            module_path = server_info["module"].replace(".", "/") + ".py"
            # Fix path construction: start from project root
            project_root = get_project_root()
            server_file = project_root / module_path

            if server_file.exists():
                stdio_config: Dict[str, Any] = {
                    "command": sys.executable,
                    "args": [str(server_file)],
                    "env": {},
                    "description": server_info.get("description", "")
                }

                # Add to categorized structure
                result["stdio"].append({
                    f"{server_type}-stdio": stdio_config
                })

                result["servers_count"] += 1

        # 2. Add running network server configurations (HTTP/SSE)
        for server_id, info in self.servers.items():
            # Only include alive network servers
            if not self._is_server_alive(info):
                continue

            # Get description from AVAILABLE_SERVERS
            server_description = ""
            for server_type, server_info in AVAILABLE_SERVERS.items():
                if server_type == info.server_type or info.name.endswith(
                        server_info.get("name", "").replace("LiteMCP-", "")):
                    server_description = server_info.get("description", "")
                    break

            if info.transport == "http":
                # HTTP configuration
                if client_type == "cursor":
                    http_config: Dict[str, Any] = {
                        "url": f"http://{info.host}:{info.port}/mcp",
                        "description": server_description
                    }
                else:  # claude_desktop
                    http_config = {
                        "transport": {
                            "type": "http",
                            "url": f"http://{info.host}:{info.port}/mcp"
                        },
                        "description": server_description
                    }

                result["http"].append({
                    f"{info.name}-http": http_config
                })

                result["servers_count"] += 1

            elif info.transport == "sse":
                # SSE configuration
                if client_type == "cursor":
                    sse_config: Dict[str, Any] = {
                        "url": f"http://{info.host}:{info.port}/sse",
                        "description": server_description
                    }
                else:  # claude_desktop
                    sse_config = {
                        "transport": {
                            "type": "sse",
                            "url": f"http://{info.host}:{info.port}/sse"
                        },
                        "description": server_description
                    }

                result["sse"].append({
                    f"{info.name}-sse": sse_config
                })

                result["servers_count"] += 1

        return result

    def get_status(self) -> Dict[str, Any]:
        """Get registry status"""
        # Force reload registry file (handles multi-process scenarios)
        self.load_from_file()
        self.clear_dead_servers()

        return {
            "total_servers": len(self.servers),
            "servers_by_transport": {
                "stdio": len(self.get_servers_by_transport("stdio")),
                "http": len(self.get_servers_by_transport("http")),
                "sse": len(self.get_servers_by_transport("sse"))
            },
            "servers": {
                server_id: {
                    "name": info.name,
                    "transport": info.transport,
                    "host": info.host,
                    "port": info.port,
                    "started_at": info.started_at,
                    "alive": self._is_server_alive(info)
                }
                for server_id, info in self.servers.items()
            }
        }

    def _is_server_alive(self, info: ServerInfo) -> bool:
        """Check if server is alive (supports remote server checking)"""
        try:
            # Determine if it's a local server
            is_local_server = is_local_ip(info.host)

            if is_local_server:
                # Local server: check if process exists
                if info.pid:
                    try:
                        if not psutil.pid_exists(info.pid):
                            self.logger.debug(f"Local server {info.name} process doesn't exist (PID: {info.pid})")
                            return False
                    except ImportError:
                        self.logger.warning("psutil module not installed, cannot check local process status")

                # Local network server: additionally check if port is accessible
                if info.transport in ["http", "sse"]:
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)  # 1 second timeout
                    try:
                        result = sock.connect_ex((info.host, info.port))
                        is_port_open = result == 0
                        if not is_port_open:
                            self.logger.debug(f"Local server {info.name} port not accessible ({info.host}:{info.port})")
                        return is_port_open
                    except Exception as e:
                        self.logger.debug(f"Error checking local server {info.name} port: {e}")
                        return False
                    finally:
                        sock.close()

                # STDIO mode local server: if PID exists and process is running, consider alive
                return True
            else:
                # Remote server: check via HTTP request
                self.logger.debug(f"Checking remote server {info.name} ({info.host}:{info.port})")
                return self._check_remote_server_alive(info)

        except Exception as e:
            self.logger.warning(f"Error checking server {info.name} status: {e}")
            # Conservative handling on error: consider server alive (to avoid false deletion)
            return True

    def _check_remote_server_alive(self, info: ServerInfo) -> bool:
        """Check if remote server is alive"""
        try:
            # Build check URL based on transport protocol
            if info.transport == "http":
                url = f"http://{info.host}:{info.port}/mcp"
            elif info.transport == "sse":
                url = f"http://{info.host}:{info.port}/sse"
            else:
                # Remote STDIO server cannot be checked, assume alive
                self.logger.debug(f"Remote STDIO server {info.name} cannot be checked, assuming alive")
                return True

            # Send HTTP request to check service status
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'LiteMCP-HealthCheck/1.0')

            # Create opener that doesn't follow redirects
            class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None

            opener = urllib.request.build_opener(NoRedirectHandler)

            try:
                response = opener.open(request, timeout=5)  # 5 second timeout for remote servers
                # Status codes 200-399 indicate accessibility (including redirects)
                is_alive = 200 <= response.status < 400
                if is_alive:
                    self.logger.debug(f"Remote server {info.name} responded normally (status: {response.status})")
                else:
                    self.logger.debug(f"Remote server {info.name} responded abnormally (status: {response.status})")
                return is_alive
            except urllib.error.HTTPError as e:
                # HTTP error, but still consider alive if redirect-related status code
                is_alive = 300 <= e.code < 400
                if is_alive:
                    self.logger.debug(f"Remote server {info.name} returned redirect (status: {e.code})")
                else:
                    self.logger.debug(f"Remote server {info.name} returned error (status: {e.code})")
                return is_alive
            except Exception as e:
                self.logger.debug(f"Remote server {info.name} connection failed: {e}")
                return False

        except Exception as e:
            self.logger.warning(f"Error checking remote server {info.name}: {e}")
            # Conservative handling on error: assume server is alive (to avoid false deletion)
            return True


# Global instance
server_registry = ServerRegistry()