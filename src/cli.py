#!/usr/bin/env python3
"""
LiteMCP Framework CLI - MCP Server Framework for Testers


Supports multiple server types and transport modes:
- stdio: Standard I/O mode (for Claude Desktop etc.)
- http: HTTP mode (for network deployment)
- sse: SSE mode (for web integration)
"""

import argparse
import sys
import requests
import socket
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from src.core.utils import get_local_ip
from src.tools import AVAILABLE_SERVERS
from src.core.logger import init_logging, get_logger
from src.core.proxy_server import get_proxy_server

console = Console()


def get_server_info(server_type: str) -> dict:
    """Get server information"""
    return AVAILABLE_SERVERS.get(server_type, {})


def auto_allocate_port() -> int:
    """Automatically allocate available port"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def print_server_panel(server_info: dict, server_type: str, transport: str, host: str, port: int):
    """Print server startup information panel"""
    transport_configs = {
        "http": {
            "name": "HTTP",
            "local_url": f"http://localhost:{port}",
            "external_url": f"http://{get_local_ip() or host}:{port}",
            "description": "HTTP mode provides RESTful API interfaces, suitable for network access and API integration."
        },
        "sse": {
            "name": "SSE (Server-Sent Events)",
            "local_url": f"http://localhost:{port}/sse",
            "external_url": f"http://{get_local_ip() or host}:{port}/sse",
            "description": "SSE mode provides real-time communication via event streams, suitable for web integration and browser clients."
        }
    }

    config = transport_configs.get(transport)
    if not config:
        return

    panel_content = f"""Starting {server_info.get('description', server_type)} server
Transport Protocol: {config['name']}
Listening Address: {host}:{port}
Local Access: {config['local_url']}
External Access: {config['external_url']}
Description: {server_info.get('description', 'No description')}


{config['description']}
"""

    console.print(Panel(panel_content, title=f"LiteMCP {server_type.title()} Server"))


def register_to_proxy(server_name: str, host: str, port: int, transport: str = "sse"):
    """Register server to proxy"""
    import os
    from src.core.utils import read_proxy_config_from_yaml

    # Read proxy server address from config file instead of hardcoding
    proxy_host, proxy_port = read_proxy_config_from_yaml()
    proxy_url = f"http://{proxy_host}:{proxy_port}/proxy/register"

    data = {
        "server_name": server_name,
        "host": host,
        "port": port,
        "transport": transport,
        "pid": os.getpid()  # Add current process PID
    }

    try:
        response = requests.post(proxy_url, json=data, timeout=5)
        if response.status_code == 200:
            console.print(
                f"[green][OK] Registered to proxy server: {server_name} -> {host}:{port} (PID: {os.getpid()}, Transport: {transport})[/green]")
        else:
            console.print(f"[yellow][!]  Proxy registration failed: {response.status_code}[/yellow]")
    except requests.exceptions.ConnectionError:
        console.print(
            f"[yellow][!]  Proxy server({proxy_host}:{proxy_port}) not running, skipping registration[/yellow]")
    except Exception as e:
        console.print(f"[yellow][!]  Proxy registration failed: {e}[/yellow]")


def try_register_to_proxy(server_type: str, host: str, port: int, transport: str, auto_register_proxy: bool, logger):
    """Attempt to register to proxy server"""
    if auto_register_proxy:
        try:
            register_to_proxy(server_type, get_local_ip() or host, port, transport)
        except Exception as e:
            logger.warning(f"Failed to register to proxy server: {e}")


def list_servers():
    """List all available servers"""
    if not AVAILABLE_SERVERS:
        console.print("[yellow]No available servers found[/yellow]")
        return

    table = Table(title="LiteMCP Framework Available Servers")
    table.add_column("Server", style="cyan", no_wrap=True)
    table.add_column("Description", style="magenta")
    table.add_column("Example Tools", style="green")

    for server_type, info in AVAILABLE_SERVERS.items():
        # Dynamically get tools list
        tools_list = []
        try:
            # Dynamically import and instantiate server to get tools
            module_name = info.get("module", "")
            class_name = info.get("class", "")

            if module_name and class_name:
                module = __import__(module_name, fromlist=[class_name])
                server_class = getattr(module, class_name)
                server_instance = server_class()

                # Get tools list
                if hasattr(server_instance, 'mcp') and hasattr(server_instance.mcp, 'list_tools'):
                    tools = server_instance.mcp.list_tools()
                    tools_list = [tool.name for tool in tools]
        except Exception:
            # If dynamic retrieval fails, use tools list from config
            tools_list = info.get("tools", [])

        tools_str = ", ".join(tools_list) if tools_list else "None"

        table.add_row(
            server_type,
            info.get("description", "No description"),
            tools_str
        )

    console.print(table)
    console.print(f"\n[green]Total {len(AVAILABLE_SERVERS)} available servers[/green]")


def serve_server(server_type: str, transport: str = "stdio", host: str = "localhost", port: int = None,
                 auto_register_proxy: bool = True):
    """Start MCP server"""
    logger = get_logger("litemcp.cli.serve")

    if server_type not in AVAILABLE_SERVERS:
        console.print(f"[red]Error: Unknown server type '{server_type}'[/red]")
        console.print(f"[yellow]Available servers: {', '.join(AVAILABLE_SERVERS.keys())}[/yellow]")
        return False

    server_info = AVAILABLE_SERVERS[server_type]

    try:
        # Dynamically import server class
        module_name = server_info["module"]
        class_name = server_info["class"]

        module = __import__(module_name, fromlist=[class_name])
        server_class = getattr(module, class_name)

        # Create server instance
        server = server_class()

        # Start server based on transport protocol
        if transport == "stdio":
            console.print(Panel(f"""Starting {server_info.get('description', server_type)} server
Transport Protocol: STDIO
Description: {server_info.get('description', 'No description')}


STDIO mode communicates directly through standard I/O, suitable for direct integration with MCP clients.
Server will keep running until receiving stop signal...
""", title=f"LiteMCP {server_type.title()} Server"))

            logger.info(f"Starting {server_type} server (STDIO mode)")
            server.run()

        elif transport in ["http", "sse"]:
            # Auto-allocate port if not specified
            if port is None:
                port = auto_allocate_port()

            # Print server info panel
            print_server_panel(server_info, server_type, transport, host, port)

            # Log information
            transport_name = "HTTP" if transport == "http" else "SSE"
            logger.info(f"Starting {server_type} server ({transport_name} mode) at {host}:{port}")

            # Register to proxy server
            try_register_to_proxy(server_type, host, port, transport, auto_register_proxy, logger)

            # Start corresponding server
            if transport == "http":
                server.run_http(host=host, port=port)
            else:  # sse
                server.run_sse(host=host, port=port)

        else:
            console.print(f"[red]Error: Unsupported transport protocol '{transport}'[/red]")
            return False

    except ImportError as e:
        console.print(f"[red]Error: Failed to import server '{server_type}': {e}[/red]")
        logger.error(f"Server import failed: {e}")
        return False
    except Exception as e:
        logger.exception(f"Server startup failed: {e}")
        console.print(f"[red]Startup failed: {e}[/red]")
        return False

    return True


def start_api_server(host: str = "localhost", port: int = 9000, log_level: str = "INFO"):
    """Start configuration API server"""
    try:
        from src.core.api_server import APIServer

        console.print(Panel(f"""Starting LiteMCP Configuration API Server
Local access: http://localhost:{port}
External access: http://{get_local_ip() or 'localhost'}:{port}


API Endpoints:
- GET /config - Get MCP client configuration
- GET /config/cursor - Get Cursor configuration
- GET /config/claude - Get Claude Desktop configuration
- GET /config/proxy - Get proxy mode configuration
- GET /status - Get server status
- GET /health - Health check""", title="LiteMCP Configuration API"))

        # Create and start API server
        api_server = APIServer(host=host, port=port, log_level=log_level)
        api_server.run()

        return True

    except ImportError:
        console.print("[red]Error: Missing FastAPI dependencies[/red]")
        console.print("[yellow]Please install: pip install fastapi uvicorn[/yellow]")
        return False
    except Exception as e:
        console.print(f"[red]Failed to start configuration API: {e}[/red]")
        return False


def start_proxy_server(host: str = "localhost", port: int = 8080):
    """Start reverse proxy server"""
    try:
        proxy_server = get_proxy_server(host=host, port=port)
        proxy_server.run()

    except Exception as e:
        console.print(f"[red]Failed to start proxy server: {e}[/red]")
        return False


def health_check():
    """System health check"""
    console.print(Panel("LiteMCP Framework Health Check", title="System Check"))

    checks = []

    # Check MCP dependencies
    try:
        from mcp.server.fastmcp import FastMCP
        checks.append(("[OK] MCP dependencies", "Normal"))
    except ImportError:
        checks.append(("[X] MCP dependencies", "Missing - Please run: pip install mcp"))

    # Check tool package structure
    tools_dir = project_root / "src" / "tools"
    if tools_dir.exists():
        checks.append(("[OK] Tool package structure", "Normal"))
    else:
        checks.append(("[X] Tool package structure", "Missing"))

    # Check server registration
    if AVAILABLE_SERVERS:
        checks.append(("[OK] Server registration", "Normal"))
        for server_type in AVAILABLE_SERVERS.keys():
            checks.append((f"  [OK] {server_type} server", "Available"))
    else:
        checks.append(("[X] Server registration", "No available servers"))

    # Check config API dependencies
    try:
        import fastapi
        import uvicorn
        checks.append(("[OK] Config API dependencies", "Normal"))
    except ImportError:
        checks.append(("[!]  Config API dependencies", "Missing - Optional feature"))

    # Check proxy server dependencies
    try:
        import aiohttp
        checks.append(("[OK] Proxy server dependencies", "Normal"))
    except ImportError:
        checks.append(("[!]  Proxy server dependencies", "Missing - Optional feature"))

    # Output check results
    for check, status in checks:
        console.print(f"{check}: {status}")

    console.print()


def main():
    """Main program entry point"""
    parser = argparse.ArgumentParser(
        description="LiteMCP Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  %(prog)s list                                # List available servers
  %(prog)s serve --server example               # Start example server (stdio)
  %(prog)s serve --server example --transport http  # HTTP mode
  %(prog)s serve --server example --transport sse   # SSE mode
  %(prog)s proxy                               # Start reverse proxy server
  %(prog)s api                                 # Start config API server
  %(prog)s health                              # System health check
        """
    )

    # Add global log level argument
    parser.add_argument("--log-level",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        default="INFO",
                        help="Log level (default: INFO)")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list command
    list_parser = subparsers.add_parser("list", help="List available servers")

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Start MCP server")
    serve_parser.add_argument("--server", "-s", required=True,
                              choices=list(AVAILABLE_SERVERS.keys()),
                              help="Server type")
    serve_parser.add_argument("--transport", "-t",
                              choices=["stdio", "http", "sse"],
                              default="stdio",
                              help="Transport protocol (default: stdio)")
    serve_parser.add_argument("--host",
                              default="localhost",
                              help="Host address to bind (default: localhost)")
    serve_parser.add_argument("--port", "-p",
                              type=int,
                              help="Port to bind (optional, auto-assigned if not specified)")
    serve_parser.add_argument("--no-proxy",
                              action="store_true",
                              help="Don't auto-register with proxy server")

    # proxy command
    proxy_parser = subparsers.add_parser("proxy", help="Start reverse proxy server")
    proxy_parser.add_argument("--host",
                              default="localhost",
                              help="Proxy server host address (default: localhost)")
    proxy_parser.add_argument("--port", "-p",
                              type=int, default=8080,
                              help="Proxy server port (default: 8080)")

    # api command (new shorter name)
    api_parser = subparsers.add_parser("api", help="Start config API server")
    api_parser.add_argument("--host",
                            default="localhost",
                            help="API server host address (default: localhost)")
    api_parser.add_argument("--port", "-p",
                            type=int, default=9000,
                            help="API server port (default: 9000)")

    # Keep config-api command for backward compatibility
    config_parser = subparsers.add_parser("config-api", help="Start config API server (deprecated, use 'api')")
    config_parser.add_argument("--host",
                               default="localhost",
                               help="API server host address (default: localhost)")
    config_parser.add_argument("--port", "-p",
                               type=int, default=9000,
                               help="API server port (default: 9000)")

    # health command
    health_parser = subparsers.add_parser("health", help="System health check")

    args = parser.parse_args()

    # Initialize logging system
    init_logging(args.log_level)
    logger = get_logger("litemcp.cli")
    logger.info(f"LiteMCP CLI started, log level: {args.log_level}")

    try:
        if args.command == "list":
            list_servers()
        elif args.command == "serve":
            success = serve_server(
                args.server,
                args.transport,
                args.host,
                args.port,
                auto_register_proxy=not args.no_proxy
            )
            if not success:
                logger.error("Failed to start server")
                sys.exit(1)
        elif args.command == "proxy":
            success = start_proxy_server(args.host, args.port)
            if not success:
                logger.error("Failed to start proxy server")
                sys.exit(1)
        elif args.command == "api" or args.command == "config-api":
            if args.command == "config-api":
                console.print("[yellow]Warning: config-api command is deprecated, please use 'api' command[/yellow]")
            success = start_api_server(args.host, args.port, args.log_level)
            if not success:
                logger.error("Failed to start config API")
                sys.exit(1)
        elif args.command == "health":
            health_check()
        else:
            parser.print_help()
    except KeyboardInterrupt:
        logger.info("Program execution interrupted by user")
        console.print("\n[yellow]Program interrupted by user[/yellow]")
    except Exception as e:
        logger.exception(f"Error during program execution: {e}")
        console.print(f"[red]Error during program execution: {e}[/red]")


if __name__ == "__main__":
    main()