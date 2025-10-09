"""
External MCP Service Process Manager

Responsible for low-level process management of external MCP services:
- Start and stop subprocesses
- Process status monitoring
- Resource cleanup
- Process lifecycle management

This is a low-level process executor that does not contain business logic.
"""

import threading
import time
import subprocess
import sys
import os
from typing import Dict, Union, Optional
from concurrent.futures import ThreadPoolExecutor

# Optional dependencies
try:
    import psutil
except ImportError:
    psutil = None

from .config_manager import external_config_manager
from .external_mcp_server import ExternalMCPServer
from src.core.logger import get_logger
from src.core.registry import server_registry


class ExternalMCPProcessManager:
    """External MCP Service Process Manager
    
    Specifically responsible for process-level management of external MCP services:
    - Subprocess start and stop
    - Process status monitoring
    - Resource cleanup and recovery
    - Process health checks
    
    Note: This is a low-level process manager that does not contain business logic such as intelligent port allocation,
    proxy registration, etc. These are handled by the upper-level ServiceManager.
    """
    
    def __init__(self):
        """Initialize process manager"""
        self.logger = get_logger(__name__)
        self.running_services: Dict[str, ExternalMCPServer] = {}
        self.service_processes: Dict[str, Union[subprocess.Popen, threading.Thread]] = {}
        self.service_ports: Dict[str, int] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self._shutdown_event = threading.Event()
    
    def get_running_services(self) -> Dict[str, Dict]:
        """Get all running service information
        
        Returns:
            Dict[str, Dict]: Running service information
        """
        services_info = {}
        
        # First get from in-memory service list
        for instance_id, server in self.running_services.items():
            instance_config = external_config_manager.get_instance(instance_id)
            if instance_config:
                services_info[instance_id] = {
                    "instance_id": instance_id,
                    "instance_name": instance_config.get("instance_name", instance_id),
                    "template_name": instance_config.get("template_name", "unknown"),
                    "status": "running" if self.is_service_running(instance_id) else "stopped",
                    "port": self.service_ports.get(instance_id),
                    "description": instance_config.get("description", "")
                }
        
        # If no services in memory, try to rebuild state from registry
        if not services_info:
            services_info = self._rebuild_services_from_registry()
        
        return services_info
    
    def _rebuild_services_from_registry(self) -> Dict[str, Dict]:
        """Rebuild running service state from registry
        
        Returns:
            Dict[str, Dict]: Rebuilt service information
        """
        services_info = {}
        
        try:
            # Get all external MCP services from registry
            all_servers = server_registry.get_all_servers()
            external_servers = {
                server_id: server_info 
                for server_id, server_info in all_servers.items() 
                if (server_info.server_type == "external_mcp" or 
                    "external-" in server_id or 
                    "External MCP service:" in str(getattr(server_info, 'server_file', '')))
            }
            
            # Rebuild state information for each external service
            for server_id, server_info in external_servers.items():
                # Try to extract instance_id from server_file
                instance_id = None
                if hasattr(server_info, 'server_file') and "External MCP service:" in str(server_info.server_file):
                    # Find matching from all instances
                    all_instances = external_config_manager.get_instances()
                    for inst_id, inst_config in all_instances.items():
                        if inst_config.get("name") in server_info.name:
                            instance_id = inst_id
                            break
                
                if instance_id:
                    instance_config = external_config_manager.get_instance(instance_id)
                    if instance_config and instance_config.get("enabled", False):
                        services_info[instance_id] = {
                            "instance_id": instance_id,
                            "instance_name": instance_config.get("instance_name", instance_id),
                            "template_name": instance_config.get("template_name", "unknown"),
                            "status": "running",  # Assume services in registry are running
                            "port": server_info.port,
                            "description": instance_config.get("description", "")
                        }
                        
                        # Update port mapping
                        self.service_ports[instance_id] = server_info.port
                        
                        self.logger.debug(f"Rebuilt service state from registry: {instance_id} -> {server_info.name}:{server_info.port}")
            
            if services_info:
                self.logger.info(f"Rebuilt state for {len(services_info)} external MCP services from registry")
                
        except Exception as e:
            self.logger.error(f"Failed to rebuild service state from registry: {e}")
        
        return services_info
    
    def is_service_running(self, instance_id: str) -> bool:
        """Check if service is running
        
        Args:
            instance_id: Instance ID
            
        Returns:
            bool: Whether running
        """
        if instance_id not in self.running_services:
            return False
        
        # Check if process is still running
        if instance_id in self.service_processes:
            process = self.service_processes[instance_id]
            if hasattr(process, 'poll'):  # subprocess.Popen object
                return process.poll() is None
            elif hasattr(process, 'is_alive'):  # Thread object
                return process.is_alive()
        
        # Fallback check: through external client
        server = self.running_services[instance_id]
        if hasattr(server, 'external_client') and server.external_client:
            return server.external_client.is_alive()
        
        return False
    
    def start_process(self, instance_id: str, instance_config: Dict, 
                     transport: str, host: str, port: int, proxy_url: Optional[str] = None) -> bool:
        """Start external MCP service process
        
        Args:
            instance_id: Instance ID
            instance_config: Instance configuration
            transport: Transport protocol (stdio/http/sse)
            host: Listen host
            port: Listen port
            proxy_url: Proxy server URL
            
        Returns:
            bool: Whether startup was successful
        """
        try:
            # Check if service is already running
            if self.is_service_running(instance_id):
                self.logger.warning(f"External MCP service already running: {instance_id}")
                return True

            # Create a temporary server instance for saving information (not registered)
            # Actual server instance will be created and registered in subprocess
            temp_server = type('TempServer', (), {
                'instance_id': instance_id,
                'external_config': type('Config', (), {
                    'name': instance_config.get('name', instance_id)
                })()
            })()
            
            # Save service information
            self.running_services[instance_id] = temp_server
            self.service_ports[instance_id] = port
            
            # Use process instead of thread to start external MCP service, avoid blocking main process
            # Create startup script
            script_content = f'''
import sys
sys.path.insert(0, "{os.getcwd()}")

# Directly use create_external_mcp_server to create server
from src.tools.external.external_mcp_server import create_external_mcp_server
import json
import time

# Recreate server instance
instance_config = {repr(instance_config)}
server = create_external_mcp_server("{instance_id}", instance_config, proxy_url={repr(proxy_url)})

# Start service in background thread and then register
import threading

def start_service():
    if "{transport}" == "stdio":
        server.run()
    elif "{transport}" == "http":
        server.run_http("{host}", {port})
    elif "{transport}" == "sse":
        server.run_sse("{host}", {port})
    else:
        raise ValueError(f"Unsupported transport protocol: {transport}")

# Start service in background thread
service_thread = threading.Thread(target=start_service, daemon=True)
service_thread.start()

# Wait for service to be ready
time.sleep(3)

# Register the service (this will use the correct subprocess PID)
try:
    success = server.register_service("{transport}", "{host}", {port})
    if success:
        print(f"[OK] External MCP service registered: {instance_config.get('name', '{instance_id}')}")
    else:
        print(f"[ERROR] Failed to register external MCP service: {instance_config.get('name', '{instance_id}')}")
except Exception as e:
    print(f"[ERROR] Registration exception: {{e}}")

# Keep the main thread alive
service_thread.join()
'''

            # Start subprocess
            try:
                process = subprocess.Popen(
                    [sys.executable, "-c", script_content],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # Save process information
                self.service_processes[instance_id] = process

                self.logger.info(f"External MCP service process started: PID {process.pid}")

            except Exception as e:
                self.logger.error(f"Failed to start external MCP service process: {e}")
                self._cleanup_service(instance_id)
                return False

            # Startup validation
            instance_name = instance_config.get("instance_name", instance_id)

            # 1. First check if process started normally
            time.sleep(1)  # Give process some time to start
            if process.poll() is not None:
                # Process has exited, check error information
                stdout, stderr = process.communicate()
                error_msg = f"External MCP process exited immediately after startup: {stderr.strip() if stderr else stdout.strip()}"
                self.logger.error(error_msg)
                self._cleanup_service(instance_id)
                return False

            # 2. For HTTP/SSE mode, check if port is accessible
            if transport in ["http", "sse"]:
                # Wait for service to listen on port
                max_wait_time = 10  # Maximum wait 10 seconds
                wait_step = 0.5  # Wait 0.5 seconds each time

                service_ready = False
                for i in range(int(max_wait_time / wait_step)):
                    time.sleep(wait_step)

                    # Check if process is still running
                    if process.poll() is not None:
                        stdout, stderr = process.communicate()
                        error_msg = f"External MCP process exited during startup: {stderr.strip() if stderr else stdout.strip()}"
                        self.logger.error(error_msg)
                        self._cleanup_service(instance_id)
                        return False

                    # Check if port is accessible
                    if self._check_mcp_service_health(host, port, transport):
                        service_ready = True
                        break

                if not service_ready:
                    # Check process status and error output
                    if process.poll() is not None:
                        stdout, stderr = process.communicate()
                        error_msg = f"External MCP service startup failed, process exited: {stderr.strip() if stderr else stdout.strip()}"
                    else:
                        error_msg = f"External MCP service startup timeout, port {host}:{port} not accessible"

                    self.logger.error(error_msg)
                    self._cleanup_service(instance_id)
                    return False

            # Service started successfully, subprocess will automatically register
            self.logger.info(f"External MCP service process started successfully: {instance_name} ({transport}://{host}:{port if port else 'stdio'})")
            self.logger.info(f"Service will auto-register with correct PID in subprocess")

            return True

        except Exception as e:
            self.logger.error(f"Failed to start external MCP service process {instance_id}: {e}")
            self._cleanup_service(instance_id)
            return False

    def stop_process(self, instance_id: str) -> bool:
        """Stop external MCP service process

        Args:
            instance_id: Instance ID

        Returns:
            bool: Whether stop was successful
        """
        try:
            if instance_id not in self.running_services:
                self.logger.warning(f"External MCP service not running: {instance_id}")
                return True

            # Stop process
            if instance_id in self.service_processes:
                process = self.service_processes[instance_id]
                if hasattr(process, 'terminate'):  # subprocess.Popen object
                    try:
                        process.terminate()
                        process.wait(timeout=5)
                    except:
                        try:
                            process.kill()
                        except:
                            pass

            # Stop service
            server = self.running_services[instance_id]

            # Cleanup external client
            if hasattr(server, 'external_client') and server.external_client:
                server.external_client.cleanup()

            # Cleanup service records
            self._cleanup_service(instance_id)

            instance_config = external_config_manager.get_instance(instance_id)
            instance_name = instance_config.get("instance_name", instance_id) if instance_config else instance_id

            self.logger.info(f"External MCP service process stopped: {instance_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop external MCP service process {instance_id}: {e}")
            return False

    def restart_process(self, instance_id: str, instance_config: Dict,
                       transport: str = "http", host: str = None, port: int = None) -> bool:
        """Restart external MCP service process

        Args:
            instance_id: Instance ID
            instance_config: Instance configuration
            transport: Transport protocol
            host: Listen host
            port: Listen port

        Returns:
            bool: Whether restart was successful
        """
        self.logger.info(f"Restarting external MCP service process: {instance_id}")

        # First stop service
        self.stop_process(instance_id)

        # Wait for cleanup to complete
        time.sleep(1)

        # Restart service
        return self.start_process(instance_id, instance_config, transport, host, port)

    def stop_all_processes(self) -> Dict[str, bool]:
        """Stop all running external MCP service processes

        Returns:
            Dict[str, bool]: Stop result for each service
        """
        results = {}
        running_services = list(self.running_services.keys())

        self.logger.info(f"Stopping {len(running_services)} external MCP service processes")

        for instance_id in running_services:
            results[instance_id] = self.stop_process(instance_id)

        # Additional cleanup: force stop any remaining external MCP processes
        self._force_cleanup_external_processes()

        return results

    def _force_cleanup_external_processes(self):
        """Force cleanup external MCP processes"""
        try:
            if psutil is None:
                raise ImportError("psutil not available")

            # Find all possible external MCP processes
            external_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and len(cmdline) > 0:
                        # Check if it's an external MCP related process
                        cmdline_str = ' '.join(cmdline)
                        is_external_mcp = False

                        # Method 1: Match by command line arguments
                        if ('mcp-server-time' in cmdline_str or
                            'LiteMCP-External' in cmdline_str or
                            ('uvx' in cmdline_str and 'mcp' in cmdline_str)):
                            is_external_mcp = True

                        # Method 2: Match by port usage (check if using 8714 etc external MCP ports)
                        if not is_external_mcp:
                            try:
                                proc_obj = psutil.Process(proc.info['pid'])
                                connections = proc_obj.net_connections()
                                for conn in connections:
                                    if (conn.status == 'LISTEN' and
                                            8000 <= conn.laddr.port < 9000 and
                                        'manage.py' in cmdline_str):
                                        # This might be a manage.py process running external MCP service
                                        is_external_mcp = True
                                        break
                            except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
                                pass

                        if is_external_mcp:
                            external_processes.append(proc.info['pid'])

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Force stop found processes
            for pid in external_processes:
                try:
                    os.kill(pid, 9)  # SIGKILL
                    self.logger.info(f"Force stopped external MCP process: {pid}")
                except (OSError, ProcessLookupError):
                    pass

        except ImportError:
            # If no psutil, use system commands
            try:
                # Find and stop external MCP processes
                result = subprocess.run(['pgrep', '-f', 'mcp-server-time'],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            try:
                                subprocess.run(['kill', '-9', pid])
                                self.logger.info(f"Force stopped external MCP process: {pid}")
                            except:
                                pass
            except:
                pass

    def _check_mcp_service_health(self, host: str, port: int, transport: str) -> bool:
        """Check if external MCP service is healthy and available

        Args:
            host: Service host
            port: Service port
            transport: Transport protocol

        Returns:
            bool: Whether service is healthy
        """
        try:
            import socket
            import requests

            # 1. First check if port is connectable
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()

            if result != 0:
                return False  # Port not connectable

            # 2. For HTTP transport, check if our wrapper service responds
            if transport == "http":
                try:
                    # Simple HTTP response check
                    response = requests.get(f"http://{host}:{port}/", timeout=3)

                    # Any normal HTTP response indicates our wrapper service is working
                    # Including 404 (FastMCP's default root path response)
                    if 200 <= response.status_code < 600:
                        return True
                    else:
                        self.logger.warning(f"HTTP response status abnormal: {response.status_code}")
                        return False

                except requests.exceptions.RequestException as e:
                    self.logger.warning(f"HTTP health check failed: {e}")
                    return False

            # 3. If port is connectable, consider service normal
            return True

        except Exception as e:
            self.logger.debug(f"Health check failed: {e}")
            return False

    def _cleanup_service(self, instance_id: str):
        """Cleanup service related resources
        
        Args:
            instance_id: Instance ID
        """
        # Remove service records
        self.running_services.pop(instance_id, None)
        self.service_ports.pop(instance_id, None)
        
        # Cleanup process/thread
        process_or_thread = self.service_processes.pop(instance_id, None)
        if process_or_thread:
            if hasattr(process_or_thread, 'terminate'):  # subprocess.Popen object
                try:
                    if process_or_thread.poll() is None:  # Process still running
                        process_or_thread.terminate()
                        process_or_thread.wait(timeout=3)
                except:
                    try:
                        process_or_thread.kill()
                    except:
                        pass
            elif hasattr(process_or_thread, 'is_alive'):  # Thread object
                # Thread will exit automatically
                pass
    
    def get_service_status(self, instance_id: str) -> Dict[str, any]:
        """Get service process status information
        
        Args:
            instance_id: Instance ID
            
        Returns:
            Dict: Service status information
        """
        instance_config = external_config_manager.get_instance(instance_id)
        if not instance_config:
            return {"status": "not_found", "message": "Instance not found"}
        
        is_running = self.is_service_running(instance_id)
        port = self.service_ports.get(instance_id)
        
        status_info = {
            "instance_id": instance_id,
            "instance_name": instance_config.get("instance_name", instance_id),
            "template_name": instance_config.get("template_name", "unknown"),
            "enabled": instance_config.get("enabled", False),
            "status": "running" if is_running else "stopped",
            "port": port,
            "description": instance_config.get("description", "")
        }
        
        if is_running and instance_id in self.running_services:
            server = self.running_services[instance_id]
            if hasattr(server, 'external_client') and server.external_client:
                external_config = server.external_client.config
                status_info.update({
                    "command": external_config.command,
                    "args": external_config.args,
                    "timeout": external_config.timeout
                })
        
        return status_info
    
    def shutdown(self):
        """Shutdown process manager"""
        self.logger.info("Shutting down external MCP service process manager")
        self._shutdown_event.set()
        
        # Stop all services
        self.stop_all_processes()
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True)


# Global process manager instance
external_process_manager = ExternalMCPProcessManager()
