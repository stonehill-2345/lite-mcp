"""
External MCP Service Wrapper - Universal External MCP Client

Supports integrating third-party MCP services (such as those started with uvx, npx) into the TestMCP framework,
providing unified services through proxy services, masking differences between external MCP services.

Supported external command types:
- uvx mcp-server-time
- npx jina-mcp-tools  
- Other stdio mode MCP services
"""

import time
import json
import subprocess
import threading
import queue
import os
import atexit
import traceback
from typing import Dict, List, Optional
from dataclasses import dataclass

import requests
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from src.tools.base import BaseMCPServer
from src.core.statistics import mcp_author, collect_server_statistics
from src.core.logger import LoggerMixin, get_logger
from fastmcp import FastMCP
from src.core.registry import server_registry, ServerInfo
from src.core.utils import get_local_ip, terminate_process_tree, create_process_with_group

logger = get_logger("litemcp.external_mcp", log_file="external_mcp.log")


# Global state manager to prevent duplicate external MCP service instances
class GlobalExternalMCPStateManager:
    """
    Global singleton state manager for external MCP services.
    Prevents duplicate service instances across multiple ExternalMCPServer instances.
    Thread-safe implementation using locks.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        # Use file-based state storage for cross-process communication
        from pathlib import Path

        # Store state in a file in runtime directory
        runtime_dir = Path(os.getcwd()) / "runtime" / "external_mcp"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = runtime_dir / "instances.json"

        # Initialize state file if not exists
        if not self._state_file.exists():
            self._write_state({})

        logger.info(f"Global external MCP state manager initialized (file: {self._state_file})")

    def register_instance(self, instance_id: str, external_client=None) -> bool:
        """
        Register an external MCP instance.
        Returns True if successfully registered, False if already exists.
        Note: external_client is not stored (only instance_id is tracked for cross-process)
        """
        try:
            state = self._read_state()

            if instance_id in state:
                logger.debug(f"Instance already registered in file: {instance_id}")
                return False

            state[instance_id] = {
                "registered_at": time.time(),
                "pid": os.getpid()
            }
            self._write_state(state)
            logger.info(f"Registered external MCP instance in file: {instance_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register instance: {e}")
            return False

    def get_instance(self, instance_id: str):
        """
        Check if instance is registered (returns True if registered, None otherwise)
        Note: We cannot return the actual client object across processes
        """
        state = self._read_state()
        if instance_id in state:
            return True  # Return True to indicate it's registered
        return None

    def unregister_instance(self, instance_id: str):
        """Unregister an external MCP instance"""
        try:
            state = self._read_state()
            if instance_id in state:
                del state[instance_id]
                self._write_state(state)
                logger.info(f"Unregistered external MCP instance from file: {instance_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to unregister instance: {e}")
            return False

    def is_registered(self, instance_id: str) -> bool:
        """Check if instance is registered"""
        state = self._read_state()
        return instance_id in state

    def _read_state(self) -> Dict:
        """Read state from file"""
        try:
            if hasattr(self, '_state_file') and self._state_file.exists():
                with open(self._state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read state file: {e}")
        return {}

    def _write_state(self, state: Dict):
        """Write state to file"""
        try:
            if hasattr(self, '_state_file'):
                with open(self._state_file, 'w') as f:
                    json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write state file: {e}")


# Global state manager singleton instance
_global_state_manager = GlobalExternalMCPStateManager()


@dataclass
class ExternalMCPConfig:
    """External MCP service configuration"""
    name: str                    # Service name
    command: str                 # Startup command (e.g. "uvx", "npx")
    args: List[str]             # Command arguments
    env: Dict[str, str] = None  # Environment variables
    description: str = ""        # Service description
    timeout: int = 30           # Startup timeout (seconds)
    auto_restart: bool = True   # Whether to auto restart


class ExternalMCPClient(LoggerMixin):
    """External MCP service client

    Responsible for communicating with external MCP service processes, handling JSON-RPC protocol
    """

    def __init__(self, config: ExternalMCPConfig):
        super().__init__()
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.request_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.request_id_counter = 0
        self.pending_requests: Dict[str, queue.Queue] = {}
        self.tools: List[Dict] = []
        self.resources: List[Dict] = []
        self.running = False
        self.reader_thread: Optional[threading.Thread] = None
        self.writer_thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """Start external MCP service process"""
        try:
            # Prepare startup command
            cmd = [self.config.command] + self.config.args
            env = None
            if self.config.env:
                env = os.environ.copy()
                env.update(self.config.env)

            # Start process with process group
            self.process = create_process_with_group(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=0  # No buffering
            )

            self.running = True

            # Start read/write threads - not using daemon mode to ensure stable communication
            self.reader_thread = threading.Thread(target=self._read_responses, daemon=False)
            self.writer_thread = threading.Thread(target=self._write_requests, daemon=False)

            self.reader_thread.start()
            self.writer_thread.start()

            # Initialize MCP connection
            if self._initialize_connection():
                return True
            else:
                self.cleanup()
                return False

        except Exception as e:
            logger.error(f"Failed to start external MCP service: {e}")
            self.cleanup()
            return False

    def _initialize_connection(self) -> bool:
        """Initialize MCP connection, get tools and resources list"""
        try:
            # Send initialization request
            init_response = self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "TestMCP-External-Wrapper",
                    "version": "1.0.0"
                }
            })

            if not init_response or "result" not in init_response:
                return False

            # Send initialized notification
            self._send_notification("notifications/initialized", {})

            # Get tools list
            tools_response = self._send_request("tools/list", {})
            if tools_response and "result" in tools_response:
                self.tools = tools_response["result"].get("tools", [])

            # Get resources list (optional)
            try:
                resources_response = self._send_request("resources/list", {})
                if resources_response and "result" in resources_response:
                    self.resources = resources_response["result"].get("resources", [])
            except:
                pass  # Resources list is optional

            return True

        except Exception as e:
            logger.error(f"Failed to initialize MCP connection: {e}")
            return False

    def _read_responses(self):
        """Read responses from external service"""
        while self.running and self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if not line:
                    logger.warning(f"External MCP service {self.config.name} output stream ended")
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    response = json.loads(line)
                    self._handle_response(response)
                except json.JSONDecodeError as e:
                    logger.error(f"External MCP service {self.config.name} JSON parsing failed: {line}, error: {e}")

            except Exception as e:
                if self.running:
                    logger.error(f"External MCP service {self.config.name} error reading response: {e}")
                break

        # Mark service unavailable when thread exits
        if self.running:
            logger.error(f"External MCP service {self.config.name} read thread exited, service may have crashed")
            self.running = False

    def _write_requests(self):
        """Send requests to external service"""
        while self.running:
            try:
                request = self.request_queue.get(timeout=1)
                if request is None:  # Exit signal
                    break

                request_line = json.dumps(request) + "\n"
                if self.process and self.process.stdin:
                    self.process.stdin.write(request_line)
                    self.process.stdin.flush()
                else:
                    logger.error(f"External MCP service {self.config.name} process stdin unavailable")
                    break

            except queue.Empty:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"External MCP service {self.config.name} error sending request: {e}")
                break

        # Mark service unavailable when thread exits
        if self.running:
            logger.error(f"External MCP service {self.config.name} write thread exited, service may have crashed")
            self.running = False

    def _handle_response(self, response: Dict):
        """Handle external service response"""
        if "id" in response:
            # This is a request response
            request_id = str(response["id"])
            if request_id in self.pending_requests:
                self.pending_requests[request_id].put(response)
        else:
            # This is a notification, ignore for now
            pass

    def _send_request(self, method: str, params: Dict, timeout: int = 30) -> Optional[Dict]:
        """Send request to external service and wait for response"""
        self.request_id_counter += 1
        request_id = str(self.request_id_counter)

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }

        # Create response queue
        response_queue = queue.Queue()
        self.pending_requests[request_id] = response_queue

        try:
            # Send request
            self.request_queue.put(request)

            # Wait for response
            response = response_queue.get(timeout=timeout)
            return response

        except queue.Empty:
            logger.error(f"Request timeout: {method}")
            return None
        finally:
            # Cleanup
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]

    def _send_notification(self, method: str, params: Dict):
        """Send notification to external service"""
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        self.request_queue.put(request)

    def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Call external service tool"""
        try:
            response = self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })

            if response and "result" in response:
                return response["result"]
            elif response and "error" in response:
                # Tool call error should not make the entire service unavailable, just return error info
                error_info = response['error']
                self._logger.warning(f"External tool {tool_name} call returned error: {error_info}")
                # Return a standard error result instead of throwing exception
                return {
                    "content": [{"type": "text", "text": f"Tool call error: {error_info}"}],
                    "isError": True
                }
            else:
                self._logger.warning(f"External tool {tool_name} call no response")
                return {
                    "content": [{"type": "text", "text": "Tool call failed: no response"}],
                    "isError": True
                }
        except Exception as e:
            self._logger.error(f"External tool {tool_name} call exception: {e}")
            # Even if exception occurs, should not make entire service unavailable
            return {
                "content": [{"type": "text", "text": f"Tool call exception: {str(e)}"}],
                "isError": True
            }

    def get_tools(self) -> List[Dict]:
        """Get tools list"""
        return self.tools

    def cleanup(self):
        """Cleanup resources"""
        self.running = False

        # Stop queue
        try:
            self.request_queue.put(None)  # Exit signal
        except:
            pass

        # Wait for threads to end
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=2)
        if self.writer_thread and self.writer_thread.is_alive():
            self.writer_thread.join(timeout=2)

        # Terminate process and its children
        if self.process:
            try:
                terminate_process_tree(self.process)
            except:
                pass
            finally:
                self.process = None

    def is_alive(self) -> bool:
        """Check if external service is running"""
        if not self.running or self.process is None:
            return False

        # Check if process is still running
        poll_result = self.process.poll()
        if poll_result is not None:
            logger.warning(f"External MCP service {self.config.name} process exited, exit code: {poll_result}")
            self.running = False
            return False

        # Check if threads are still running
        if (self.reader_thread and not self.reader_thread.is_alive()) or \
           (self.writer_thread and not self.writer_thread.is_alive()):
            logger.warning(f"External MCP service {self.config.name} communication threads stopped")
            self.running = False
            return False

        return True

    def restart(self) -> bool:
        """Restart external MCP service"""
        logger.info(f"Restarting external MCP service: {self.config.name}")
        self.cleanup()
        time.sleep(1)  # Wait for cleanup to complete
        return self.start()


@mcp_author("External MCP", department="Testing Department", project=["TD"])
class ExternalMCPServer(BaseMCPServer):
    """External MCP service wrapper server

    Universal external MCP service wrapper supporting dynamic configuration and management.
    No hardcoded specific external services, completely configuration-driven.
    """

    def __init__(self, instance_id: str, config: Dict, name: str = None, proxy_url: str = None, external_client=None):
        """Initialize external MCP service wrapper

        Args:
            instance_id: Instance ID for identifying specific external service instance
            config: External MCP service configuration dictionary
            name: Server name, defaults to TestMCP-External-{instance_name}
            proxy_url: Proxy server URL for registering to specified proxy server
            external_client: Pre-configured external client (optional)
        """
        self.instance_id = instance_id
        self.proxy_url = proxy_url  # Store proxy server URL
        instance_name = config.get("instance_name", config.get("name", instance_id))

        if name is None:
            # Use more friendly name format for proxy identification
            name = f"TestMCP-External-{instance_name}"

        # Store server name for proxy (using English name field, suitable for URL paths)
        service_name = config.get("name", instance_id)  # Use English name field
        self.proxy_server_name = f"external-{service_name.replace(' ', '-').lower()}"

        self.external_config = ExternalMCPConfig(
            name=config.get("name", instance_id),
            command=config["command"],
            args=config["args"],
            env=config.get("env", {}),
            description=config.get("description", ""),
            timeout=config.get("timeout", 30),
            auto_restart=config.get("auto_restart", True)
        )
        self.external_client: Optional[ExternalMCPClient] = None
        self._atexit_registered = False  # Avoid duplicate atexit registration

        # Delay base class initialization to avoid premature registration
        LoggerMixin.__init__(self)
        self.name = name
        self.enable_cors = True
        self.mcp = FastMCP(name=self.name)
        self._server_id = None
        self._auto_register = False  # Disable auto registration

        # Set pre-configured external client if provided
        if external_client:
            self.external_client = external_client

        # Manually call tool registration (this will use our overridden _register_to_registry method)
        self._register_tools()

        # Collect statistics
        collect_server_statistics(self)

    def register_service(self, transport: str, host: str = "localhost", port: int = 8000, pid: int = None):
        """Public method to register service (called by process manager)

        Args:
            transport: Transport protocol
            host: Service host
            port: Service port
            pid: Process PID (optional, defaults to current process PID)

        Returns:
            bool: Whether registration was successful
        """
        # Directly call proxy registration, simplify call chain
        try:
            self._server_id = f"{self.proxy_server_name}-{transport}"
            if transport in ["http", "sse"]:
                self._server_id += f"-{port}"

            # Only register once for exit cleanup
            if not self._atexit_registered:
                atexit.register(self._unregister_from_registry)
                self._atexit_registered = True

            # registered to proxy
            if self._register_to_proxy(host, port, transport):
                self.logger.info(f"[OK] External MCP service registered to proxy server: {self._server_id}")
                return True
            else:
                self.logger.warning(f"[!] External MCP service failed to register to proxy server")
                return False

        except Exception as e:
            self.logger.error(f"[!] Error registering external MCP service: {e}")
            return False

    def _register_to_proxy(self, host: str, port: int, transport: str):
        """Register to proxy server via HTTP interface"""
        try:
            # Prioritize using specified proxy URL
            proxy_urls = []

            if self.proxy_url:
                # If proxy URL is specified, use it first
                proxy_urls.append(self.proxy_url.rstrip('/'))
                self.logger.info(f"Using specified proxy server: {self.proxy_url}")
            else:
                # Otherwise try local proxy server addresses
                proxy_urls = [
                    "http://localhost:1888",
                    "http://127.0.0.1:1888"
                ]

                # If local IP can be obtained, also try local IP
                try:
                    local_ip = get_local_ip()
                    if local_ip:
                        proxy_urls.append(f"http://{local_ip}:1888")
                except:
                    pass

            register_data = {
                "server_name": self.proxy_server_name,
                "host": host,
                "port": port,
                "transport": transport,
                "pid": os.getpid()
            }

            success = False
            for proxy_url in proxy_urls:
                try:
                    response = requests.post(
                        f"{proxy_url}/proxy/register",
                        json=register_data,
                        timeout=5,
                        headers={'Content-Type': 'application/json'}
                    )

                    if response.status_code == 200:
                        self.logger.info(f"[OK] External MCP service registered to proxy: {proxy_url}")
                        success = True
                        break
                    else:
                        self.logger.debug(f"Proxy registration failed {proxy_url}: HTTP {response.status_code}")

                except Exception as e:
                    self.logger.debug(f"Cannot connect to proxy {proxy_url}: {e}")
                    continue

            if not success:
                self.logger.warning(f"[!] Cannot register to proxy server, service still accessible via local registry")

        except Exception as e:
            self.logger.error(f"Error registering to proxy server: {e}")

    def _unregister_from_registry(self):
        """Unregister server from registry"""
        if self._server_id:
            try:
                server_registry.unregister_server(self._server_id)
                self.logger.info(f"[OK] External MCP service unregistered from config API: {self._server_id}")
                self._server_id = None  # Clear ID to avoid duplicate unregistration
            except Exception as e:
                self.logger.error(f"[!] Error unregistering external MCP service: {e}")

    def _create_cors_middleware(self):
        """Create CORS middleware"""
        if not self.enable_cors:
            return []

        middleware = [
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        ]
        return middleware

    def run(self):
        """Run MCP server - STDIO mode"""
        try:
            self.mcp.run()
        except Exception as e:
            self.logger.error(f"Server run error: {e}")
            raise

    def run_http(self, host: str = "localhost", port: int = 8000):
        """Run MCP server - HTTP mode"""
        try:
            middleware = self._create_cors_middleware()
            self.mcp.run(
                transport="streamable-http",
                host=host,
                port=port,
                middleware=middleware
            )
        except Exception as e:
            self.logger.error(f"HTTP server run error: {e}")
            raise

    def _register_tools(self):
        """Dynamically register external service tools"""
        try:
            # Prevent duplicate registration for this instance
            if hasattr(self, '_tools_registered') and self._tools_registered:
                self.logger.debug(f"Tools already registered for this instance: {self.external_config.name}, skipping")
                return

            self.logger.info(f"Registering tools for external MCP service: {self.external_config.name}")
            self.logger.info(f"Service command: {self.external_config.command} {' '.join(self.external_config.args)}")

            # Step 1: Check if external client is already set up by wrapper script
            has_client = hasattr(self, 'external_client')
            client_exists = has_client and self.external_client is not None
            client_running = client_exists and hasattr(self.external_client, 'running') and self.external_client.running
            self.logger.debug(f"External client status: has_attr={has_client}, exists={client_exists}, running={client_running}")

            if has_client and self.external_client and client_running:
                self.logger.info(f"External MCP client already running in this instance, skipping startup")

                # Try to register this client globally
                registration_success = _global_state_manager.register_instance(self.instance_id, self.external_client)
                self.logger.info(f"Registration result for {self.instance_id}: {registration_success}")
                if registration_success:
                    self.logger.info(f"Successfully registered instance globally: {self.instance_id}")
                    # Verify registration
                    verify = _global_state_manager.is_registered(self.instance_id)
                    self.logger.info(f"Verification after registration: {verify}")
                else:
                    self.logger.warning(f"Failed to register instance globally (may already exist): {self.instance_id}")

                # Get external service tools list (with retry logic)
                external_tools = []
                max_retries = 3
                retry_delay = 1  # seconds

                for attempt in range(max_retries):
                    external_tools = self.external_client.get_tools()
                    if len(external_tools) > 0:
                        break

                    if attempt < max_retries - 1:
                        self.logger.warning(f"External client running but no tools found yet (attempt {attempt + 1}/{max_retries}), waiting {retry_delay}s...")
                        import time
                        time.sleep(retry_delay)

                self.logger.info(f"Found {len(external_tools)} external tools: {[tool.get('name', 'unknown') for tool in external_tools]}")

                # If still no tools found after retries, keep registered globally for retry
                if len(external_tools) == 0:
                    self.logger.error(f"External client running but failed to get tools after {max_retries} attempts")
                    self.logger.warning(f"Will keep instance registered globally for future retry")
                    # Do NOT set _tools_registered, so next call will retry
                    return

                # Dynamically register each tool
                for tool_info in external_tools:
                    self._register_external_tool(tool_info)

                # Mark as registered
                self._tools_registered = True
            else:
                # No external client provided - this means we're not in the wrapper process
                # This should not happen in normal operation, as external MCP services should always use wrapper
                self.logger.error(f"No external client found for {self.instance_id}, cannot register tools")
                self.logger.error(f"External MCP services must be started via the wrapper process")
                return

        except Exception as e:
            self.logger.error(f"Failed to register external tools: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def _register_external_tool(self, tool_info: Dict):
        """Register single external tool, completely preserve original tool parameters and return value info"""
        tool_name = tool_info.get("name")
        if not tool_name:
            return

        # Get original tool input and output schema
        input_schema = tool_info.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        # Dynamically create tool function using original tool parameter structure
        def create_dynamic_tool_func(name: str, info: Dict, props: Dict, req: List):
            # Build parameter list
            param_names = list(props.keys())

            # If no parameters, create parameterless function
            if not param_names:
                def tool_func() -> str:
                    return self._call_external_tool(name, {})
                return tool_func

            # To avoid FastMCP **kwargs limitation, we use dynamic function generation
            # Build function parameter strings
            param_strs = []
            for param_name in param_names:
                param_info = props[param_name]
                param_type = param_info.get("type", "string")

                # Set default values based on whether required
                if param_name in req:
                    # Required parameter, no default value
                    param_strs.append(f"{param_name}")
                else:
                    # Optional parameter, set default value
                    if param_type == "string":
                        param_strs.append(f'{param_name}: str = ""')
                    elif param_type == "number":
                        param_strs.append(f'{param_name}: float = 0.0')
                    elif param_type == "integer":
                        param_strs.append(f'{param_name}: int = 0')
                    elif param_type == "boolean":
                        param_strs.append(f'{param_name}: bool = False')
                    elif param_type == "array":
                        param_strs.append(f'{param_name}: list = None')
                    elif param_type == "object":
                        param_strs.append(f'{param_name}: dict = None')
                    else:
                        param_strs.append(f'{param_name}: str = ""')

            # Build function body
            func_params = ", ".join(param_strs)

            # Create local variables to capture external variables
            call_external_tool = self._call_external_tool

            # Dynamically create function
            param_checks = '\n'.join([f'    if {param} is not None: args["{param}"] = {param}' for param in param_names])

            func_code = f"""def tool_func({func_params}) -> str:
    # Build parameter dictionary
    args = {{}}
{param_checks}
    
    # Validate required parameters
    required_params = {req}
    for req_param in required_params:
        if req_param not in args:
            return f"Error: missing required parameter '{{req_param}}'"
    
    return call_external_tool("{name}", args)
"""

            # Execute dynamic code, ensure call_external_tool is available in both global and local scope
            global_vars = {"__builtins__": __builtins__, "call_external_tool": call_external_tool}
            local_vars = {"call_external_tool": call_external_tool}
            exec(func_code, global_vars, local_vars)
            return local_vars["tool_func"]

        # Create tool function
        tool_func = create_dynamic_tool_func(tool_name, tool_info, properties, required)
        tool_func.__name__ = tool_name

        # Directly use original tool docstring without any modification
        tool_func.__doc__ = tool_info.get("description", "")

        # Build parameter annotations using original tool parameter types
        annotations = {}
        for prop_name, prop_info in properties.items():
            prop_type = prop_info.get("type", "string")
            if prop_type == "string":
                annotations[prop_name] = str
            elif prop_type == "number":
                annotations[prop_name] = float
            elif prop_type == "integer":
                annotations[prop_name] = int
            elif prop_type == "boolean":
                annotations[prop_name] = bool
            elif prop_type == "array":
                annotations[prop_name] = list
            elif prop_type == "object":
                annotations[prop_name] = dict
            else:
                annotations[prop_name] = str

        annotations["return"] = str
        tool_func.__annotations__ = annotations

        # Register tool to FastMCP using simple decorator approach
        try:
            # Use standard FastMCP tool registration approach
            self.mcp.tool()(tool_func)

            self.logger.info(f"Registered external tool: {tool_name} (parameters: {list(properties.keys())})")

        except Exception as e:
            self.logger.error(f"Failed to register tool {tool_name}: {e}")

    def _call_external_tool(self, tool_name: str, arguments: Dict) -> str:
        """Unified method for calling external tools"""
        try:
            self.logger.info(f"[TOOL_CALL] ===== External tool call started =====")
            self.logger.info(f"[TOOL_CALL] Service: {self.external_config.name}")
            self.logger.info(f"[TOOL_CALL] Tool: {tool_name}")
            self.logger.info(f"[TOOL_CALL] Parameters: {arguments}")

            # Check external service status, try restart if unavailable
            if not self.external_client:
                error_msg = f"External MCP client not initialized: {self.external_config.name}"
                self.logger.error(f"[TOOL_CALL] {error_msg}")
                return f"Error: {error_msg}"

            is_alive = self.external_client.is_alive()
            self.logger.info(f"[TOOL_CALL] Service status check: {self.external_config.name} is_alive={is_alive}")

            if not is_alive:
                self.logger.warning(f"[TOOL_CALL] External MCP service {self.external_config.name} unavailable, trying restart...")

                # Try to restart service
                if hasattr(self.external_client, 'restart'):
                    if self.external_client.restart():
                        self.logger.info(f"[TOOL_CALL] External MCP service {self.external_config.name} restarted successfully")
                    else:
                        error_msg = f"External MCP service {self.external_config.name} restart failed"
                        self.logger.error(f"[TOOL_CALL] {error_msg}")
                        return f"Error: {error_msg}"
                else:
                    error_msg = f"External MCP service {self.external_config.name} not running and cannot restart"
                    self.logger.error(f"[TOOL_CALL] {error_msg}")
                    return f"Error: {error_msg}"

            # Call external tool
            self.logger.info(f"[TOOL_CALL] Starting external tool call: {tool_name}")
            result = self.external_client.call_tool(tool_name, arguments)

            # Check if it's an error result
            if isinstance(result, dict) and result.get("isError"):
                # This is an error result but not an exception, directly return error info
                if "content" in result:
                    content = result["content"]
                    if isinstance(content, list) and len(content) > 0:
                        error_text = content[0].get("text", str(result))
                        self.logger.warning(f"[TOOL_CALL] External tool returned error: {error_text}")
                        return error_text
                    error_text = str(content)
                    self.logger.warning(f"[TOOL_CALL] External tool returned error: {error_text}")
                    return error_text
                error_text = str(result)
                self.logger.warning(f"[TOOL_CALL] External tool returned error: {error_text}")
                return error_text

            # Normal result processing
            self.logger.info(f"[TOOL_CALL] External tool call successful, result type: {type(result)}")
            self.logger.debug(f"[TOOL_CALL] External tool call result details: {result}")

            # Process normal result
            if isinstance(result, dict):
                if "content" in result:
                    content = result["content"]
                    if isinstance(content, list) and len(content) > 0:
                        final_result = content[0].get("text", str(result))
                        self.logger.info(f"[TOOL_CALL] Return result: {final_result[:200]}...")
                        return final_result
                    final_result = str(content)
                    self.logger.info(f"[TOOL_CALL] Return result: {final_result[:200]}...")
                    return final_result
                final_result = str(result)
                self.logger.info(f"[TOOL_CALL] Return result: {final_result[:200]}...")
                return final_result

            final_result = str(result)
            self.logger.info(f"[TOOL_CALL] Return result: {final_result[:200]}...")
            return final_result

        except Exception as e:
            self.logger.error(f"[TOOL_CALL] Failed to call external tool {tool_name}: {e}")
            self.logger.error(f"[TOOL_CALL] Exception stack: {traceback.format_exc()}")
            return f"Tool call failed: {str(e)}"

    def cleanup(self):
        """Cleanup resources"""
        if self.external_client:
            self.external_client.cleanup()

        # Unregister from global state manager
        if hasattr(self, 'instance_id') and self.instance_id:
            _global_state_manager.unregister_instance(self.instance_id)

    def __del__(self):
        """Destructor"""
        try:
            self.cleanup()
        except:
            pass


def create_external_mcp_server(instance_id: str, config_dict: Dict, proxy_url: str = None) -> ExternalMCPServer:
    """Create external MCP server from configuration dictionary
    
    Args:
        instance_id: Instance ID
        config_dict: Configuration dictionary, format as follows:
        {
            "name": "time",
            "command": "uvx", 
            "args": ["mcp-server-time", "--local-timezone=America/New_York"],
            "env": {},
            "description": "Time server"
        }
        proxy_url: Proxy server URL for registering to specified proxy server
    
    Returns:
        ExternalMCPServer: External MCP server instance
    """
    return ExternalMCPServer(instance_id, config_dict, proxy_url=proxy_url)
