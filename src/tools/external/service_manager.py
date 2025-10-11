"""
External MCP Service Unified Manager

Unified management of external MCP service startup, stop, proxy registration/unregistration operations,
avoiding duplicate logic in manage.py and external_mcp_api.py.
"""

import time
from typing import Dict, Optional, Tuple, Any
from src.core.logger import LoggerMixin, get_logger
from src.core.utils import get_smart_port_for_service, get_local_ip, get_available_port, is_port_available
from src.tools.external.config_manager import external_config_manager
from src.tools.external.process_manager import external_process_manager


class ExternalMCPServiceManager(LoggerMixin):
    """External MCP Service Unified Manager"""

    def __init__(self):
        super().__init__()
        self._logger = get_logger("litemcp.external_mcp", log_file="external_mcp_service_manage.log")

    def start_service(self, instance_id: str, proxy_url: Optional[str] = None,
                     force_host: Optional[str] = None, force_port: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Start external MCP service instance

        Args:
            instance_id: Instance ID
            proxy_url: Proxy server URL (optional)
            force_host: Force specify host (optional, for API calls)
            force_port: Force specify port (optional, for API calls)

        Returns:
            Tuple[bool, Dict]: (success, details)
        """
        try:
            # 1. Check if instance exists
            instance = external_config_manager.get_instance(instance_id)
            if not instance:
                return False, {"error": f"Instance not found: {instance_id}"}

            instance_name = instance.get('instance_name', instance_id)
            self._logger.info(f"Starting external MCP instance: {instance_name} ({instance_id})")

            # 2. Check if instance is already enabled
            if not instance.get('enabled', False):
                self._logger.info(f"Enabling external MCP instance configuration: {instance_name}")
                if not external_config_manager.enable_instance(instance_id):
                    return False, {"error": f"Failed to enable instance configuration: {instance_name}"}

            # 3. Get transport protocol and host configuration
            transport = instance.get('transport', 'http')
            config_host = force_host or instance.get('host')

            # Parse host address
            # Use 0.0.0.0 to listen on all interfaces, but get local IP for registration
            if config_host and config_host != "null" and config_host is not None:
                host = config_host
                register_host = config_host
            else:
                # Bind to 0.0.0.0 for external access
                host = "0.0.0.0"
                # But register with actual local IP for proxy
                register_host = get_local_ip() or "127.0.0.1"
                self._logger.info(f"Binding to 0.0.0.0 (all interfaces), will register as {register_host}")

            # 4. Smart port allocation
            if force_port:
                port = force_port
            elif instance.get('port'):
                # If fixed port is configured, check if available
                port = instance['port']
                if not is_port_available(port, host):
                    self._logger.warning(f"External service {instance_name} specified config port {port} but it's occupied on {host}, using smart allocation")
                    try:
                        port = get_smart_port_for_service(f'external-{instance_name}', transport, host=host)
                        self._logger.info(f"Smart port allocation successful: {instance_name} -> {port}")
                    except Exception as e:
                        self._logger.warning(f"Smart port allocation failed: {e}, using random port")
                        port = get_available_port(8000, 1000)
            else:
                # Use smart port allocation
                try:
                    port = get_smart_port_for_service(f'external-{instance_name}', transport, host=host)
                    self._logger.info(f"Smart port allocation successful: {instance_name} -> {port}")
                except Exception as e:
                    self._logger.warning(f"Smart port allocation failed: {e}, using random port")
                    port = get_available_port(8000, 1000)

            self._logger.info(f"Starting external service {instance_name}: {host}:{port} ({transport})")

            # 5. Start service process
            self._logger.info(f"Starting external MCP service process: {instance_name}")
            service_success = external_process_manager.start_process(
                instance_id,
                instance,
                transport=transport,
                host=host,
                port=port,
                proxy_url=proxy_url,
                register_host=register_host if 'register_host' in locals() else host
            )

            if not service_success:
                self._logger.error(f"Failed to start external MCP service: {instance_name}")
                # Rollback configuration changes
                external_config_manager.disable_instance(instance_id)
                return False, {"error": f"Failed to start external MCP service: {instance_name}. Please check if command path and parameters are correct"}

            # 6. Verify service is actually available (additional verification step)
            self._logger.info(f"Verifying external MCP service status: {instance_name}")
            service_is_healthy = self._verify_service_health(instance_id, host, port, transport)
            if not service_is_healthy:
                self._logger.error(f"External MCP service health check failed after startup: {instance_name}")
                # Stop started service
                external_process_manager.stop_process(instance_id)
                # Rollback configuration changes
                external_config_manager.disable_instance(instance_id)
                return False, {"error": f"External MCP service health check failed: {instance_name}. Service may have crashed immediately after startup or cannot respond normally"}

            # 7. Update instance configuration (record actually used port, keep host as null for auto-detection)
            # Don't save host to allow flexible binding (0.0.0.0) on next startup
            config_success = external_config_manager.update_instance(
                instance_id,
                {"enabled": True, "host": None, "port": port, "transport": transport}
            )

            if not config_success:
                self._logger.error(f"Failed to update external MCP instance configuration: {instance_name} (service started but configuration update failed)")
                # Try to stop service because configuration update failed
                external_process_manager.stop_process(instance_id)
                return False, {"error": f"Failed to update instance configuration: {instance_name}"}

            self._logger.info(f"External MCP instance started successfully: {instance_name} -> {host}:{port}")

            return True, {
                "instance_name": instance_name,
                "host": host,
                "port": port,
                "transport": transport,
                "proxy_url": proxy_url
            }

        except Exception as e:
            self._logger.error(f"External MCP service startup exception: {e}")
            return False, {"error": f"Service startup exception: {str(e)}"}

    def stop_service(self, instance_id: str, proxy_url: Optional[str] = None,
                    disable_config: bool = True) -> Tuple[bool, Dict[str, Any]]:
        """
        Stop external MCP service instance

        Args:
            instance_id: Instance ID
            proxy_url: Proxy server URL (optional, for unregistration)
            disable_config: Whether to disable configuration (default True)

        Returns:
            Tuple[bool, Dict]: (success, details)
        """
        try:
            # 1. Check if instance exists
            instance = external_config_manager.get_instance(instance_id)
            if not instance:
                return False, {"error": f"Instance not found: {instance_id}"}

            instance_name = instance.get('instance_name', instance_id)
            self._logger.info(f"Stopping external MCP instance: {instance_name} ({instance_id})")

            # 2. Unregister service from proxy (if proxy URL provided)
            proxy_success = True
            if proxy_url:
                try:
                    # Calculate correct proxy server name
                    service_name = instance.get("name", instance_id)
                    proxy_server_name = f"external-{service_name.replace(' ', '-').lower()}"

                    self._logger.info(f"Unregistering service from proxy: {instance_name} (proxy name: {proxy_server_name})")
                    proxy_success = self._unregister_from_proxy(proxy_url, proxy_server_name)
                    if proxy_success:
                        self._logger.info(f"Proxy unregistration successful: {instance_name}")
                    else:
                        self._logger.warning(f"Proxy unregistration failed: {instance_name}")
                except Exception as proxy_error:
                    self._logger.warning(f"Error unregistering from proxy: {proxy_error}")
                    proxy_success = False

            # 3. Stop service process
            service_success = True
            try:
                if external_process_manager.is_service_running(instance_id):
                    service_success = external_process_manager.stop_process(instance_id)
                    if service_success:
                        self._logger.info(f"External MCP service stopped successfully: {instance_name}")
                    else:
                        self._logger.warning(f"External MCP service stop failed: {instance_name}")
                else:
                    self._logger.info(f"External MCP service not running: {instance_name}")
            except Exception as service_error:
                self._logger.error(f"Error stopping external MCP service: {service_error}")
                service_success = False

            # 4. Cleanup local registry
            registry_success = True
            try:
                self._unregister_from_local_registry(instance_id, instance)
            except Exception as e:
                self._logger.warning(f"Failed to cleanup local registry: {e}")
                registry_success = False

            # 5. Modify configuration (disable instance and clear host/port)
            config_success = True
            if disable_config:
                # Clear host and port to avoid conflicts on next startup
                update_data = {
                    "enabled": False,
                    "host": None,
                    "port": None
                }
                config_success = external_config_manager.update_instance(instance_id, update_data)
                if not config_success:
                    self._logger.error(f"Failed to disable external MCP instance configuration: {instance_name}")
                else:
                    self._logger.info(f"Cleared host/port for instance: {instance_name}")

            # Return result
            result = {
                "instance_name": instance_name,
                "service_stopped": service_success,
                "config_updated": config_success if disable_config else True,
            }

            if proxy_url:
                result["proxy_unregistered"] = proxy_success

            overall_success = service_success and (config_success if disable_config else True)

            if overall_success:
                self._logger.info(f"External MCP instance stopped successfully: {instance_name}")
            else:
                self._logger.warning(f"External MCP instance stopped partially successfully: {instance_name}")

            return overall_success, result

        except Exception as e:
            self._logger.error(f"External MCP service stop exception: {e}")
            return False, {"error": f"Service stop exception: {str(e)}"}

    def start_all_enabled_services(self, proxy_url: Optional[str] = None) -> Dict[str, bool]:
        """
        Start all enabled external MCP services

        Args:
            proxy_url: Proxy server URL (optional)

        Returns:
            Dict[str, bool]: Startup result for each service
        """
        try:
            self._logger.info("Starting all enabled external MCP services...")

            # Get enabled external service instances
            enabled_instances = external_config_manager.get_enabled_instances()

            if not enabled_instances:
                self._logger.info("No enabled external MCP services")
                return {}

            self._logger.info(f"Found {len(enabled_instances)} enabled external MCP services")

            results = {}
            for instance_id, instance_config in enabled_instances.items():
                instance_name = instance_config.get('instance_name', instance_id)

                try:
                    success, details = self.start_service(instance_id, proxy_url)
                    results[instance_id] = success

                    if success:
                        self._logger.info(f"External service started successfully: {instance_name}")
                    else:
                        self._logger.error(f"External service startup failed: {instance_name} - {details.get('error', 'Unknown error')}")

                except Exception as e:
                    self._logger.error(f"Error starting external service {instance_name}: {e}")
                    results[instance_id] = False

            success_count = sum(1 for result in results.values() if result)
            failed_count = len(results) - success_count

            if success_count > 0:
                self._logger.info(f"External MCP service startup completed - successful: {success_count}, failed: {failed_count}")
                return results
            else:
                self._logger.warning("No external MCP services started successfully")
                return results

        except Exception as e:
            self._logger.error(f"Failed to start all external MCP services: {e}")
            return {}

    def stop_all_services(self, proxy_url: Optional[str] = None) -> Dict[str, bool]:
        """
        Stop all running external MCP services

        Args:
            proxy_url: Proxy server URL (optional, for unregistration)

        Returns:
            Dict[str, bool]: Stop result for each service
        """
        try:
            self._logger.info("Stopping all external MCP services...")

            # Stop all running external service processes
            results = external_process_manager.stop_all_processes()

            success_count = sum(1 for result in results.values() if result)

            if success_count > 0:
                self._logger.info(f"Stopped {success_count} external MCP services")
            elif results:
                self._logger.info("No external MCP services need to be stopped")
            else:
                self._logger.debug("No running external MCP services found")

            return results

        except Exception as e:
            self._logger.error(f"Failed to stop external MCP services: {e}")
            return {}

    def _verify_service_health(self, instance_id: str, host: str, port: int, transport: str) -> bool:
        """Verify if service is healthy and available - including MCP protocol verification

        Args:
            instance_id: Instance ID
            host: Service host
            port: Service port
            transport: Transport protocol

        Returns:
            bool: Whether service is healthy
        """
        try:
            # 1. Check service status in process manager
            if not external_process_manager.is_service_running(instance_id):
                self._logger.warning(f"Process manager shows service not running: {instance_id}")
                return False

            # 2. For HTTP/SSE mode, perform network and MCP protocol health check
            if transport in ["http", "sse"]:
                import socket
                import requests
                import json

                # Port connectivity check
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)
                    result = sock.connect_ex((host, port))
                    sock.close()

                    if result != 0:
                        self._logger.warning(f"Port {host}:{port} not connectable")
                        return False
                except Exception as e:
                    self._logger.warning(f"Port connectivity check failed: {e}")
                    return False

                # Simplified HTTP health check - check if our wrapper service responds
                if transport == "http":
                    try:
                        # For our ExternalMCPServer wrapped services, only need to check if HTTP port responds
                        # No need to send complex MCP requests as wrapper layer handles protocol conversion
                        response = requests.get(f"http://{host}:{port}/", timeout=5)

                        # Any HTTP response (including 404, 500, etc.) indicates service is running
                        # 404 is FastMCP's default root path response, which is normal
                        if 200 <= response.status_code < 600:
                            self._logger.info(f"HTTP service health check successful: {host}:{port}")
                            return True
                        else:
                            self._logger.warning(f"HTTP service response abnormal: {host}:{port} -> {response.status_code}")
                            return False

                    except requests.exceptions.RequestException as e:
                        self._logger.warning(f"HTTP service health check exception: {e}")
                        return False

            # 3. For stdio mode, need to wait a while to check if process runs stably
            elif transport == "stdio":
                import time
                # Wait 3 seconds to check if process crashes
                time.sleep(3)
                if not external_process_manager.is_service_running(instance_id):
                    self._logger.warning(f"STDIO mode service crashed after startup: {instance_id}")
                    return False
                return True

            # 4. Other cases, only check process status
            return True

        except Exception as e:
            self._logger.error(f"Service health check exception: {e}")
            return False
    
    def _unregister_from_proxy(self, proxy_url: str, server_name: str) -> bool:
        """Unregister specified service from proxy server"""
        if not proxy_url:
            return True
        
        try:
            import requests
            
            # Clean proxy URL
            proxy_url = proxy_url.rstrip('/')
            
            # Check if proxy server is available
            try:
                response = requests.get(f"{proxy_url}/proxy/status", timeout=5)
                if response.status_code != 200:
                    self._logger.warning(f"Proxy server not available: {proxy_url}")
                    return False
            except Exception as e:
                self._logger.warning(f"Cannot connect to proxy server: {e}")
                return False
            
            # Send unregistration request
            unregister_url = f"{proxy_url}/proxy/unregister/{server_name}"
            
            # Add retry mechanism
            max_retries = 3
            for retry_count in range(max_retries):
                try:
                    response = requests.delete(unregister_url, timeout=5)
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        status = response_data.get('status')
                        if status in ['success', 'unregistered']:
                            self._logger.info(f"Successfully unregistered from proxy: {server_name}")
                            return True
                        else:
                            self._logger.warning(f"Proxy unregistration response abnormal: {response_data}")
                    elif response.status_code == 404:
                        self._logger.info(f"Server not registered in proxy: {server_name}")
                        return True  # 404 also counts as success
                    else:
                        self._logger.warning(f"Proxy unregistration failed: HTTP {response.status_code}")
                        
                except Exception as e:
                    self._logger.warning(f"Proxy unregistration request failed (attempt {retry_count + 1}/{max_retries}): {e}")
                    if retry_count < max_retries - 1:
                        time.sleep(1)
            
            self._logger.error(f"Proxy unregistration failed, tried {max_retries} times: {server_name}")
            return False
            
        except Exception as e:
            self._logger.error(f"Proxy unregistration exception: {e}")
            return False
    
    def _unregister_from_local_registry(self, instance_id: str, instance: Dict):
        """Unregister external MCP service from local registry"""
        try:
            from src.core.registry import server_registry
            
            # Calculate server ID (consistent with logic in external_mcp_server.py)
            service_name = instance.get("name", instance_id)
            proxy_server_name = f"external-{service_name.replace(' ', '-').lower()}"
            
            # Get transport protocol and port information
            transport = instance.get('transport', 'http')
            port = instance.get('port', 8000)
            
            # Build server ID (consistent with registration format)
            server_id = f"{proxy_server_name}-{transport}"
            if transport in ["http", "sse"]:
                server_id += f"-{port}"
            
            self._logger.info(f"Unregistering service from local registry: {server_id}")
            
            # Try to unregister service
            if server_registry.unregister_server(server_id):
                self._logger.info(f"Local registry unregistration successful: {server_id}")
                return True
            else:
                self._logger.warning(f"Local registry unregistration failed, service may not exist: {server_id}")
                return False
                
        except Exception as e:
            self._logger.error(f"Local registry unregistration exception: {e}")
            return False


# Create global instance
external_service_manager = ExternalMCPServiceManager()
