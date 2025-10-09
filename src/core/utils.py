"""
LiteMCP Utility Classes - Provides various utility functions
"""
import os
import socket
import logging
from pathlib import Path
from datetime import datetime

import yaml

# Setup logging
logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """
    Get the project root directory path

    Find the project root directory using the following strategies in priority order:
    1. Search upward from current directory until finding a directory containing src and specific project markers
    2. If not found, try to get from environment variables
    3. If still not found, raise an exception

    Returns:
        Path: Path object of the project root directory

    Raises:
        RuntimeError: If unable to determine the project root directory

    Examples:
        >>> root_path = get_project_root()
        >>> print(f"Project root directory: {root_path}")
    """
    # First check environment variables
    if 'LiteMCP_ROOT' in os.environ:
        root_path = Path(os.environ['LiteMCP_ROOT'])
        if _is_valid_project_root(root_path):
            return root_path

    # Start searching upward from the current file's directory
    current_file = Path(__file__).resolve()
    for parent in [current_file, *current_file.parents]:
        if _is_valid_project_root(parent):
            return parent

    # Start searching upward from the current working directory
    current = Path.cwd().resolve()
    while current != current.parent:
        if _is_valid_project_root(current):
            return current
        current = current.parent

    raise RuntimeError(
        "Unable to determine project root directory. Please ensure:\n"
        "1. Current directory is within the project structure, or\n"
        "2. Set LiteMCP_ROOT environment variable to point to the project root directory"
    )


def _is_valid_project_root(path: Path) -> bool:
    """
    Validate whether the given path is a valid project root directory

    Check criteria:
    1. Must contain src directory
    2. src directory must contain core and tools subdirectories
    3. Optional: Check for other project-specific files

    Args:
        path: Path to validate

    Returns:
        bool: Whether it is a valid project root directory
    """
    if not path.is_dir():
        return False

    # Required directory structure
    required_paths = [
        path / 'src',
        path / 'src' / 'core',
        path / 'src' / 'tools'
    ]

    # Check required directory structure
    if not all(p.is_dir() for p in required_paths):
        return False

    # Optional: Check for other project-specific files
    # More project-specific checks can be added here
    optional_indicators = [
        path / 'config',  # Configuration directory
        path / 'runtime',  # Runtime directory
        path / '.git',    # Git repository
        path / 'README.md'  # Project documentation file
    ]

    # At least one optional indicator must exist
    if not any(p.exists() for p in optional_indicators):
        return False

    return True


def get_local_ip() -> str | None:
    """
    Get the host's local area network IPv4 address
    Supports multiple environments:
    1. Regular physical/virtual machine network environments
    2. Docker container environment
    3. Kubernetes Pod environment

    Return strategy (by priority):
    1. Get local IP through UDP connection
    2. Iterate through network interfaces to get non-loopback IP
    3. Get IP through hostname resolution
    4. Get IP through command line tools (mainly for container environments)
    5. Get IP from environment variables

    Returns:
        str | None: Local area network IPv4 address, returns None if failed to obtain
    """
    # Method 1: Get through UDP connection (most commonly used method)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Connect to an external address (no actual connection required)
            s.connect(('8.8.8.8', 80))
            # Get the assigned IP
            local_ip = s.getsockname()[0]
            if local_ip and not local_ip.startswith('127.'):
                logger.debug(f"IP obtained through UDP connection: {local_ip}")
                return local_ip
        except Exception as e:
            logger.warning(f"Failed to get IP by connecting to external address: {str(e)}")
        finally:
            s.close()
    except Exception as e:
        logger.warning(f"Failed to get IP through UDP socket: {str(e)}")

    # Method 2: Try to iterate through all network interfaces
    try:
        import netifaces
        # Iterate through all network interfaces
        for interface in netifaces.interfaces():
            # Get IPv4 addresses
            addresses = netifaces.ifaddresses(interface).get(netifaces.AF_INET, [])
            for addr_info in addresses:
                ip = addr_info.get('addr')
                # Exclude loopback addresses and invalid addresses
                if ip and not ip.startswith('127.') and ip != '0.0.0.0':
                    logger.debug(f"IP obtained through network interface {interface}: {ip}")
                    return ip
    except ImportError:
        logger.warning("netifaces module not installed, unable to get IP through network interfaces")
    except Exception as e:
        logger.warning(f"Failed to get IP by iterating network interfaces: {str(e)}")

    # Method 3: Get the address corresponding to hostname
    try:
        host_name = socket.gethostname()
        host_ip = socket.gethostbyname(host_name)
        if host_ip and not host_ip.startswith('127.'):
            logger.debug(f"IP obtained through hostname: {host_ip}")
            return host_ip
    except Exception as e:
        logger.warning(f"Failed to get IP through hostname: {str(e)}")

    # Method 4: If in container environment, try to find through specific network interface
    try:
        import subprocess
        # Try to find IP address in container environment
        cmd = "ip -4 addr show eth0 | grep -oP '(?<=inet\\s)\\d+(\\.\\d+){3}'"
        result = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
        if result and not result.startswith('127.'):
            logger.debug(f"IP obtained through command line: {result}")
            return result
    except ImportError:
        logger.debug("subprocess module not installed, unable to get IP through command line")
    except Exception as e:
        logger.debug(f"Failed to get IP through command line: {str(e)}")

    # Method 5: Get IP address from environment variables (fallback solution)
    try:
        import os
        # Common environment variable names list, sorted by priority
        env_var_names = [
            'EXTERNAL_IP',           # Custom environment variable
            'POD_IP',                # Kubernetes Pod IP
            'NODE_IP',               # Kubernetes Node IP
            'HOSTNAME',              # Container hostname (might be IP)
            'DOCKER_HOST_IP',        # Docker host IP
            'HOST_IP',               # Generic host IP variable
            'PUBLIC_IP',             # Public IP
            'VIRTUAL_HOST',          # Virtual host
            'SERVER_IP'              # Server IP
        ]

        # Iterate through environment variables to find the first valid IP address
        for var_name in env_var_names:
            env_ip = os.environ.get(var_name)
            if env_ip and env_ip != '0.0.0.0' and env_ip != '127.0.0.1':
                logger.debug(f"IP address obtained from environment variable {var_name}: {env_ip}")
                return env_ip
    except Exception as e:
        logger.warning(f"Failed to get IP from environment variables: {str(e)}")

    # All methods failed, return default value
    logger.error("Unable to get valid local area network IP address")
    return None


def is_local_ip(ip: str) -> bool:
    """
    Determine whether the given IP is a local IP
    :param ip: IP to be determined
    :return:
    """
    local_ip = get_local_ip()
    local_ips = {'localhost', '127.0.0.1', '0.0.0.0'}
    if local_ip:
        local_ips.add(local_ip)

    # Determine if it's a local server
    return ip in local_ips


def get_available_port(start_port: int = 8000, max_attempts: int = 100) -> int:
    """
    Get an available port number

    Starting from the specified starting port, try one by one to find the first available port.
    This is very useful for automatic port allocation, avoiding port conflicts.

    Args:
        start_port: Starting port number, defaults to starting from 8000
        max_attempts: Maximum number of attempts, defaults to 100

    Returns:
        int: Available port number

    Raises:
        OSError: If no available port can be found within the specified range

    Examples:
        >>> port = get_available_port()  # Start searching from 8000
        >>> port = get_available_port(9000)  # Start searching from 9000
        >>> port = get_available_port(8000, 50)  # Limit to maximum 50 attempts
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            # Try to bind port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # Set port reuse option
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('localhost', port))
                logger.debug(f"Port {port} is available")
                return port
        except OSError as e:
            # Port is occupied or other error
            logger.debug(f"Port {port} is not available: {e}")
            continue

    # If no available port is found, raise an exception
    raise OSError(f"No available port found in port range {start_port}-{start_port + max_attempts - 1}")


def get_available_port_for_service(service_name: str = None, start_port: int = 8000, max_attempts: int = 1000) -> int:
    """
    Get an available port for a service (generic version)

    This version no longer relies on hard-coded service port mappings, but adopts a more flexible approach:
    1. Start searching from the specified starting port
    2. Support large-range port search (default 1000 ports)
    3. Service name is only used for logging and does not affect port allocation logic

    Args:
        service_name: Service name (optional, only for logging)
        start_port: Starting port number, defaults to 8000
        max_attempts: Maximum number of attempts, defaults to 1000

    Returns:
        int: Available port number

    Raises:
        OSError: If no available port can be found within the specified range

    Examples:
        >>> port = get_available_port_for_service("example")
        >>> port = get_available_port_for_service("school", start_port=9000)
        >>> port = get_available_port_for_service(start_port=8500, max_attempts=500)
    """
    try:
        port = get_available_port(start_port, max_attempts)
        service_info = f"service '{service_name}'" if service_name else "service"
        logger.info(f"Allocated port for {service_info}: {port}")
        return port
    except OSError as e:
        service_info = f"service '{service_name}'" if service_name else "service"
        logger.error(f"Unable to find available port for {service_info}: {e}")
        raise


def get_smart_port_for_service(service_name: str, transport: str = "sse", start_port: int = 8000, max_attempts: int = 1000, host: str = 'localhost') -> int:
    """
    Smart port allocation - prioritize using historical ports from registry (simplified version)

    Allocation strategy:
    1. First check if there are existing records for the server in the registry
    2. If record exists and port is available, use the historical port
    3. If record exists but port is occupied, allocate new port (let caller handle port cleanup)
    4. If no record exists, allocate new available port, avoiding ports already used in registry

    Args:
        service_name: Service name
        transport: Transport mode (sse, http, stdio)
        start_port: Starting port number (used when allocating new port)
        max_attempts: Maximum number of attempts
        host: Host to check, passed in order when not localhost

    Returns:
        int: Allocated port number

    Raises:
        OSError: If unable to find available port

    Examples:
        >>> port = get_smart_port_for_service("pm", "sse")
        >>> port = get_smart_port_for_service("example", "http", start_port=9000)
    """
    try:
        # Import registry class (avoid circular import)
        from src.core.registry import ServerRegistry

        registry = ServerRegistry()
        registry.load_from_file()

        # Find historical records for this server in the registry
        existing_server = None
        existing_port = None
        latest_timestamp = None

        for server_id, server_info in registry.get_all_servers().items():
            if (server_info.name == service_name or
                server_info.server_type == service_name) and server_info.transport == transport:

                # Parse timestamp
                try:
                    current_timestamp = datetime.fromisoformat(server_info.started_at.replace('Z', '+00:00'))

                    # If this is the first record found, or timestamp is more recent
                    if latest_timestamp is None or current_timestamp > latest_timestamp:
                        existing_server = server_info
                        existing_port = server_info.port
                        latest_timestamp = current_timestamp
                        logger.debug(f"Found server '{service_name}' record (port: {existing_port}, time: {server_info.started_at})")
                except Exception as e:
                    # If timestamp parsing fails, still use this record (fallback handling)
                    logger.warning(f"Failed to parse timestamp {server_info.started_at}: {e}")
                    if existing_server is None:
                        existing_server = server_info
                        existing_port = server_info.port

        if existing_port:
            logger.info(f"Found latest record for server '{service_name}' in registry (port: {existing_port})")
        else:
            logger.info(f"No record found for server '{service_name}' in registry")

        if existing_port:
            # Check if historical port is available
            if is_port_available(existing_port, host):
                logger.info(f"Server '{service_name}' using historical port: {existing_port}")
                return existing_port
            else:
                # Port is occupied, need to allocate new port
                logger.warning(f"Historical port {existing_port} for server '{service_name}' is occupied on {host}, will allocate new port")
                # Continue with new port allocation logic below

        # No historical record, allocate new port
        logger.info(f"Server '{service_name}' has no historical record, allocating new port...")

        # To avoid conflicts with existing servers, we need to get all used ports
        used_ports = set()
        for server_info in registry.get_all_servers().values():
            if server_info.port:
                used_ports.add(server_info.port)

        logger.debug(f"Ports already used in registry: {list(used_ports)}")

        # Start searching from start_port, skip already used ports
        for port in range(start_port, start_port + max_attempts):
            if port not in used_ports and is_port_available(port, host):
                logger.info(f"Allocated new port for server '{service_name}' on {host}: {port}")
                return port

        # If the above strategy fails, use original port allocation logic as fallback
        logger.warning(f"Smart port allocation failed, using standard port allocation for server '{service_name}'")
        return get_available_port(start_port, max_attempts)

    except Exception as e:
        logger.warning(f"Smart port allocation error: {e}, using standard port allocation")
        return get_available_port(start_port, max_attempts)


def get_available_ports(count: int, start_port: int = 8000, gap: int = 1) -> list[int]:
    """
    Batch obtain multiple available ports

    Applicable to scenarios where multiple services need to be started simultaneously.

    Args:
        count: Number of ports needed
        start_port: Starting port number
        gap: Port interval, defaults to 1 (consecutive ports)

    Returns:
        list[int]: List of available ports

    Raises:
        OSError: If unable to obtain sufficient number of ports

    Examples:
        >>> ports = get_available_ports(3)  # Get 3 consecutive available ports
        >>> ports = get_available_ports(3, gap=10)  # Get 3 ports with interval of 10
    """
    ports = []
    current_port = start_port
    max_attempts = 10000  # Prevent infinite loop
    attempts = 0

    while len(ports) < count and attempts < max_attempts:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('localhost', current_port))
                ports.append(current_port)
                logger.debug(f"Port {current_port} is available")
                current_port += gap
        except OSError:
            logger.debug(f"Port {current_port} is not available")
            current_port += 1

        attempts += 1

    if len(ports) < count:
        raise OSError(f"Unable to obtain {count} available ports, only found {len(ports)}")

    logger.info(f"Batch allocated ports: {ports}")
    return ports


def is_port_available(port: int, host: str = 'localhost') -> bool:
    """
    Check if the specified port is available

    Args:
        port: Port number to check (1-65535)
        host: Host address, defaults to localhost

    Returns:
        bool: Whether the port is available

    Examples:
        >>> if is_port_available(8080):
        ...     print("Port 8080 is available")
    """
    # Validate port number range
    if not (1 <= port <= 65535):
        logger.warning(f"Port number {port} exceeds valid range (1-65535)")
        return False

    try:
        # Use connect_ex to check if port is actually in use
        # This is more accurate than bind() method
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex((host, port))
        s.close()
        
        # If connection succeeds (result == 0), port is occupied
        if result == 0:
            return False
        return True
    except Exception:
        # If any exception occurs, consider port unavailable for safety
        return False


def read_proxy_config_from_yaml() -> tuple[str, int]:
    """
    Read proxy server configuration from YAML configuration file

    Returns:
        tuple: (host, port) Host and port of proxy server
    """
    config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                               "config", "servers.yaml")

    if not os.path.exists(config_file):
        return "localhost", 1888  # Default value

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        proxy_config = config.get('proxy_server', {})

        # Read host configuration
        host = proxy_config.get('host', 'localhost')
        if host == '0.0.0.0':
            # If configured as 0.0.0.0, return local IP
            host = get_local_ip() or 'localhost'
        elif host == 'null' or host is None:
            host = get_local_ip() or 'localhost'

        # Read port configuration
        port = proxy_config.get('port', 1888)
        if port == 'null' or port is None:
            port = 1888

        return host, int(port)

    except Exception as e:
        print(f"Failed to read proxy configuration: {e}")
        return "localhost", 1888  # Return default value
