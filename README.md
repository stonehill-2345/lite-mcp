# LiteMCP Framework

English | [中文](docs/README.zh_CN.md)

A simple Model Context Protocol (MCP) server framework designed to solve issues like scattered nodes, management chaos, and inconsistent access points in current MCP server clusters, providing a concise and efficient tool development and management solution.

LiteMCP Framework fully supports Windows, macOS, and Linux operating systems, ensuring a consistent experience across platforms. Key advantages include:
- Rapid creation of custom testing tools, reducing development costs in multi-server scenarios
- Standardized MCP protocol implementation, resolving protocol compatibility issues between distributed nodes
- Flexible support for multiple deployment modes, adapting to server clusters of different scales
- Simple and extensible architecture, easily handling dynamically growing server counts
- Built-in intelligent proxy server that integrates distributed nodes into a unified access point, eliminating the complexity of managing multiple servers


## 🚀 Quick Start

- **Python 3.12+** - For multiple Python versions, consider using tools like [pyenv](https://github.com/pyenv/pyenv)
- **pip** or **[Poetry](https://python-poetry.org/)** (recommended)
- **Git** (for version control)

### Install Dependencies

```bash
# Clone the project
git clone https://github.com/hlw-tech/lite-mcp
cd lite-mcp

# Install dependencies (automatically detects Poetry or pip)
./scripts/manage.sh setup

# Verify installation
./scripts/manage.sh check
```

### Management Script Instructions
| OS | Recommended Script	 | Python Version |
|-------------|-----------------------|-----------|
| **Linux**   | `./scripts/manage.sh` | Python 3.12+ |
| **macOS**   | `./scripts/manage.sh` | Python 3.12+ |
| **Windows** | `scripts\manage.bat`  | Python 3.12+ |
| **Cross-platform**   | `./scripts/manage.py` | Python 3.12+ |

Get usage parameters:
```bash
python ./scripts/manage.py help
./scripts/manage.sh help  # or
./scripts/manage.bat help  # or

# The core of the management script is cli.py, you can even use cli.py directly
python src/cli.py serve --server example --transport sse --port 8000
```

### Basic Usage
> **Note**: Choose the appropriate management script for your system or use `manage.py` directly. The following examples are completed using `manage.sh` on Mac OS.

```bash
# Install dependencies
./scripts/manage.sh setup

# Start all services (enabled mcp server, mcp api, mcp proxy), automatically starts services with enabled=true according to the configuration in [servers.yaml](config/servers.yaml)
./scripts/manage.sh up

# View startup status and access addresses
./scripts/manage.sh ps

# Stop all services
./scripts/manage.sh down

# Restart all services, same effect as up parameter
./scripts/manage.sh restart
```

### Advanced Usage
```bash
# Start only mcp api
./scripts/manage.sh api

# Start only mcp proxy
./scripts/manage.sh proxy

# Start specified service (service name depends on configuration in [__init__.py](src/tools/__init__.py))
./scripts/manage.sh up --name <server name>

# Stop specified service
./scripts/manage.sh down --name <server name>

# Output detailed debug logs, add --verbose parameter after any management operation to view debug logs generated during the process
./scripts/manage.sh down --name <server name> --verbose

# Restart specified service
./scripts/manage.sh restart --name <server name>

# Register mcp server to specified mcp proxy and provide external services through the proxy
./scripts/manage.sh start --name example --proxy-url https://test-mcp.2345.cn  # Start specified service and register to proxy

# Unregister all services
./scripts/manage.sh unregister --proxy-url https://test-mcp.2345.cn
```
> Note: Registering to a remote proxy service is mainly suitable for Jenkins-like multi-slave, one-master mode. When registering to a remote proxy, if the remote proxy also starts this service, it will overwrite the registered service information.
!![RemoteServer.png](docs/RemoteServer.png)

> For remaining non-core parameters, you can explore using `./scripts/manage.sh help`.

### 💡 Platform-Specific Notes

#### Windows User Notes
1. **Python Environment**: Ensure Python 3.12+ is installed and added to PATH environment variable
   ```cmd
   python --version
   ```

2. **Wrapper Script**: Now you can use `scripts\manage.bat` to get the same experience as Linux/macOS

3. **Multiple Python Commands**: The wrapper will automatically detect `python`, `python3` or `py` commands

#### macOS/Linux User Notes
1. **Execution Permission**: Ensure the script has execution permission
   ```bash
   chmod +x scripts/manage.sh
   ```
2. **System Commands**: The script will automatically detect the operating system and use corresponding commands


## 🎯 Configure MCP Client Example

### 📱 Client Configuration

#### Get Client Configuration

**⚠️Important:** You must start the API server before calling the interface to get the configuration (affects configuration retrieval but not stdio mode usage), otherwise you cannot directly call the interface to get configuration information
* Method 1: Run directly: [api_server.py](src/core/api_server.py). Note: This method only works for stdio mode; sse http mcp servers are not started.
* Method 2: Start via cli: `python src/cli.py api`. Note: This method only works for stdio mode; sse http mcp servers are not started.
* Method 3: Start api server using management script: `./scripts/manage.sh api`. Note: This method only works for stdio mode; sse http mcp servers are not started.
* Method 4: Directly execute the previously mentioned `./scripts/manage.sh up`. Note: This method starts all enabled `mcp server`, `api server`, and `proxy server`.
* Method 5:
  * python ./scripts/manage.py api  # Start API
  * python ./scripts/manage.py proxy  # Start proxy
  * python ./scripts/manage.py up --name xxx  # Start specified service

**Method 1:** Get configuration directly through API
```curl
curl -X 'GET' \
  'http://{mcp api ip}:9000/config?client_type=cursor&format=json' \
  -H 'accept: application/json'
```

**Method 2:** Get through swagger page provided by fast api (or)
Open in browser: http://{machine IP where service is started}:9000/docs#/default/get_mcp_config_config_get

**Method 3:** Directly view the startup log, which will display the proxy address, MCP server startup address, and port number

#### clientConfiguration Content Description
```json
{
    "sse-proxy": {
        "url": "https://{proxy ip}:1888/sse/pm",
        "description": "[Using proxy, SSE mode] Proxy automatically forwards requests based on path"
    },
   "http-proxy": {
        "url": "https://{proxy ip}:1888/mcp/pm",
        "description": "[Using proxy, Streamable HTTP mode] Proxy automatically forwards requests based on path"
    },
   "sse": {
        "url": "https://{mcp server ip}:8765/sse",
        "description": "[Without proxy, SSE mode] Requests are processed by the specific MCP SSE server without proxy forwarding"
    },
    "mcp": {
        "url": "https://{mcp server ip}:8765/mcp",
        "description": "[Without proxy, Streamable HTTP mode] Requests are processed by the specific MCP HTTP server without proxy forwarding"
    },
    "school-stdio": {
        "command": "/bab/.cache/pypoetry/virtualenvs/litemcp-bQXDpGYe-py3.12/bin/python3",
        "args": [
            "/home/bab/Code/litemcp/src/tools/demo/school_server.py"
        ],
        "env": {},
        "description": "[Local command line mode] Maintained by MCP client"
    }
}
```
> Note: When not using a proxy service, the port may change each time the service is restarted and needs to be adjusted accordingly. The default proxy port is 1888.

#### Configure Cursor Example
Configure tool path example:
![CursorSettings.png](docs/CursorSettings.png)
Configure content example:
![CursorMCPJson.png](docs/CursorMCPJSON.png)
Enable tool example:
![CursorEnableTools.png](docs/CursorEnableTools.png)
Use tool example:
![CursorUseTools.png](docs/CursorUseTools.png)

### Server Configuration File

> This configuration affects which services are started by startup scripts like [manage.sh](scripts/manage.sh) and [manage.py](scripts/manage.py), as well as service-specific configuration parameters.
> Non-universal parameters are recommended to be hard-coded directly, while more universal necessary configurations can be placed in environment files.

`config/servers.yaml` configuration example:

```yaml
# LiteMCP Server Startup Configuration
mcp_servers:
  example:
    enabled: true                    # Whether to enable this server
    server_type: "example"           # Server type
    transport: "sse"                 # Transport protocol: stdio/http/sse  
    host: null                       # Automatically gets current machine IP, externally accessible
    port: null                       # Port number, null for automatic assignment
    auto_restart: true               # Whether to auto-restart
    description: "Example server"

  school:
    enabled: true
    server_type: "school"
    transport: "sse"
    host: null                       # Automatically gets current machine IP, externally accessible
    port: null                       # Port number, null for automatic assignment
    auto_restart: true
    description: "School management server"

# API Server Configuration  
api_server:
  enabled: true                      # Whether to enable API server
  host: null                         # Automatically gets current machine IP, externally accessible
  port: 9000                         # API server port
  auto_restart: true                 # Whether to auto-restart
  description: "Configuration API server"
```

## 🏗️ Project Structure
- [Project Structure](docs/USAGE.md#project-structure)

## 🔧 Development Guide

### Create New Tool Server

Now it only takes 5 steps, no need to modify CLI code!

#### 1. Create Server File
Create a new server file in the `tools/` directory

#### 2. Register to Framework
Register the new server in `tools/__init__.py`

#### 3. Configure Startup Parameters
Add server configuration in `config/servers.yaml`

#### 4. Test Tool
Use `./scripts/manage.sh up` to start batch testing or refer to the "[Advanced Usage](README.md#advanced-usage)" section to start individually

#### 5. Verify Functionality
Verify tool functionality in MCP client through proxy address

### Example Implementation

```python
"""
My Test Tool - Concise Development Mode
"""

from src.tools.base import BaseMCPServer
    

class MyTestServer(BaseMCPServer):
    """My Test Server - Inherits Base Class"""
    
    def __init__(self):
        # Call parent class initialization to automatically get transport mode support
        super().__init__("My-Test-Server")
    
    def _register_tools(self):
        """Implement tool registration - focus on business logic"""
        
        @self.mcp.tool()
        def my_tool(param: str) -> str:
            """My Test Tool"""
            return f"Processed: {param}"

# Create Instance
my_server = MyTestServer()

if __name__ == "__main__":
    # Automatically supports all transport modes:
    # my_server.run()       # STDIO mode
    # my_server.run_http()  # HTTP mode  
    # my_server.run_sse()   # SSE mode
    my_server.run()
```

## 🚨 Troubleshooting

### Common Issues

```bash
# Port Conflict
./scripts/manage.sh down --force  # Force stop all servers
./scripts/manage.sh up            # Restart

# View Logs
./scripts/manage.sh log           # View all log files
tail -f logs/example.log  # View specific logs in real-time

# System Check
./scripts/manage.sh check         # Health check
./scripts/manage.sh setup         # Reinstall dependencies

# Detailed Debugging
./scripts/manage.sh up --verbose  # Show detailed startup information
./scripts/manage.sh diagnose      # Run system diagnosis
```

🔧 **Detailed Troubleshooting Guide**: Check [USAGE.md](docs/USAGE.md#troubleshooting) for complete diagnosis methods and solutions

## 📚 Complete Documentation Navigation

### 🚀 Quick Start Documentation
- **[5-Minute Quick Start](docs/USAGE.md#5-minute-quick-start)** - Environment preparation to tool invocation
- **[Proxy Server Details](docs/USAGE.md#detailed-explanation-of-proxy-server)** - Architecture and usage of intelligent proxy

### 🛠️ Developer Documentation
- **[Develop New Tools](docs/USAGE.md#develop-new-tools)** - Create custom tools in 5 steps
- **[Transport Modes Details](docs/USAGE.md#detailed-explanation-of-transport-modes)** - STDIO, HTTP, SSE, Proxy Mode
- **[Project Structure](docs/USAGE.md#project-structure-description)** - Complete directory structure and file description

### 🔧 Operations and Maintenance Documentation
- **[Command List](docs/USAGE.md#complete-command-list)** - Detailed explanation of all management commands
- **[Configuration File Details](docs/USAGE.md#detailed-configuration-file-explanation)** - Complete configuration explanation for servers.yaml
- **[Troubleshooting Guide](docs/USAGE.md#troubleshooting)** - Common issues and solutions

### 📖 Core Functionality Documentation
- **[Intelligent Proxy Server](docs/USAGE.md#detailed-explanation-of-proxy-server)** - Architecture principles, configuration, and diagnosis
- **[Common Operation Scenarios](docs/USAGE.md#common-operation-scenarios)** - Development, production, and maintenance scenarios
- **[Frequently Asked Questions (FAQ)](docs/USAGE.md#frequently-asked-questions-faq)** - Detailed Q&A collection

💡 **Usage Suggestions**:
 - New users: First read this README, then check [5-Minute Quick Start](docs/USAGE.md#5-minute-quick-start)
 - Developers: Focus on the [Develop New Tools](docs/USAGE.md#develop-new-tools) section
 - Operations personnel: Refer to the [Troubleshooting Guide](docs/USAGE.md#troubleshooting) and command list

### Built-in Example Services

| Server Type | Description | Purpose |
|-----------|------|------|
| `example` | Example tool server | Development mode demonstration, standardized implementation |
| `school` | School management server | Student information management, data operation example |

### Transport Protocol Support

- **STDIO**: Standard input/output mode, suitable for local development managed by specific MCP client
- **HTTP**: RESTful API mode, suitable for network deployment (automatically displays local and external access addresses)
- **SSE**: Server-Sent Events mode, suitable for Web integration (automatically displays local and external access addresses)
- **Proxy Mode**: Unified access entry that masks dynamically changing ports of specific MCP servers with automatic path matching forwarding, **highly recommended**

## 🤝 Community Integrations

LiteMCP Framework integrates with the following open-source projects and libraries to provide a comprehensive MCP server development experience:

### Core Dependencies
- **[fastmcp](https://github.com/jlowin/fastmcp)** - Fast Model Context Protocol implementation for Python
- **[fastapi](https://fastapi.tiangolo.com/)** - Modern, fast web framework for building APIs with Python
- **[uvicorn](https://www.uvicorn.org/)** - Lightning-fast ASGI server implementation
- **[click](https://click.palletsprojects.com/)** - Python package for creating beautiful command line interfaces
- **[rich](https://rich.readthedocs.io/)** - Rich library for beautiful terminal output

### System & Network
- **[psutil](https://psutil.readthedocs.io/)** - Cross-platform library for retrieving information on running processes and system utilization
- **[httpx](https://www.python-httpx.org/)** - A fully featured HTTP client for Python, with both sync and async APIs
- **[requests](https://requests.readthedocs.io/)** - HTTP library for Python, built for human beings

### Data Processing & Security
- **[PyYAML](https://pyyaml.org/)** - YAML parser and emitter for Python
- **[pycryptodome](https://pycryptodome.readthedocs.io/)** - Cryptographic library for Python
- **[chardet](https://chardet.readthedocs.io/)** - Universal character encoding detector

### Database & Utilities
- **[pymysql](https://pymysql.readthedocs.io/)** - Pure Python MySQL Client Library
- **[apkutils2](https://github.com/avast/apkutils)** - Android APK file parser and utilities

### Development & Testing
- **[pytest](https://docs.pytest.org/)** - Framework for writing and running tests in Python
- **[pytest-asyncio](https://pytest-asyncio.readthedocs.io/)** - Pytest plugin for testing async code

### Contributing
We welcome contributions from the community! If you'd like to contribute to LiteMCP Framework:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request


### License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


