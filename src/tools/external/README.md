# External MCP Service Manager

## Overview

The External MCP Service Manager is a core component of the LiteMCP framework, used to uniformly manage and integrate third-party MCP services (such as `mcp-server-time`, `jina-mcp-tools`, etc.). Through this manager, we can wrap any external MCP service that supports STDIO mode into HTTP services and uniformly register them in LiteMCP's proxy system.

## Design Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LiteMCP Proxy Server                         │
│                  (http://host:1888)                             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ HTTP Request Forwarding
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│               External MCP Wrapper Server                       │
│            (ExternalMCPServer)                                  │
│              http://host:8714                                   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ STDIO Communication
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│              External MCP Service Process                       │
│         (e.g.: mcp-server-time)                                 │
│              STDIO Mode                                          │
└─────────────────────────────────────────────────────────────────┘
```

### Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    Management Layer                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Service Manager │  │ Process Manager │  │ Config Manager  │ │
│  │ (High-level)    │  │ (Low-level)     │  │ (Data)          │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ Service Coordination
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    Communication Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ External MCP    │  │ External MCP    │  │ HTTP/SSE/STDIO  │ │
│  │ Server          │  │ Client          │  │ Transport       │ │
│  │ (HTTP Interface)│  │ (STDIO Comm)    │  │ (Protocols)     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ Process Communication
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    External Service Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ mcp-server-time │  │ jina-mcp-tools  │  │ Other MCP       │ │
│  │ (Time Tools)    │  │ (AI Tools)      │  │ Services        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

1. **Configuration Manager** (`config_manager.py`)
   - Manages template configurations and instance configurations for external MCP services
   - Supports JSON format configuration file storage
   - Handles instance creation, update, deletion, and validation

2. **Wrapper Server** (`external_mcp_server.py`)
   - Wraps STDIO mode external MCP services into HTTP services
   - Handles MCP protocol conversion and communication
   - Provides ExternalMCPClient for STDIO communication
   - Supports HTTP, SSE, and STDIO transport modes

3. **Process Manager** (`process_manager.py`)
   - Low-level process management for external MCP services
   - Handles subprocess start, stop, and monitoring
   - Manages resource cleanup and process lifecycle
   - Provides health checks and process status monitoring

4. **Service Manager** (`service_manager.py`)
   - High-level service lifecycle management
   - Coordinates between configuration, process, and proxy systems
   - Handles intelligent port allocation and service registration
   - Provides unified API for service operations

5. **API Interface** (`../controller/external_mcp_api.py`)
   - Provides RESTful API for managing external MCP services
   - Supports CRUD operations and service control
   - Handles template and instance management

## Workflow

### 1. Configuration Management

#### Instance Configuration (`config/external_mcp.json`)
```json
{
  "263123a5-d745-4c98-9853-042c2c8c838c": {
    "template_name": "time",
    "instance_name": "My Time Tool",
    "enabled": true,
    "transport": "http",
    "host": null,
    "port": null,
    "created": "2025-09-23T09:40:50.114300",
    "updated": "2025-09-23T09:40:50.114557"
  }
}
```

### 2. Service Startup Process

1. **Read Configuration**
   - `ExternalMCPConfigManager` loads template and instance configurations
   - Filters out enabled instances

2. **Start External Processes**
   - `ExternalMCPServiceManager` coordinates service startup
   - `ExternalMCPProcessManager` handles low-level process management
   - Uses `subprocess.Popen` to start wrapper processes
   - Wrapper processes internally start external MCP services (STDIO mode)

3. **Establish Communication**
   - `ExternalMCPClient` communicates with external services through STDIO
   - Uses independent read/write threads to handle JSON-RPC messages
   - `ExternalMCPServer` provides HTTP interface externally
   - Supports multiple transport protocols (HTTP, SSE, STDIO)

4. **Service Registration**
   - `ExternalMCPServiceManager` handles service registration
   - Wrapper servers register to LiteMCP main registry
   - Provides unified external services through proxy server
   - Supports automatic proxy registration and unregistration

### 3. Communication Protocol

#### STDIO Communication (Wrapper ↔ External Service)
```json
// Send to external service
{"jsonrpc": "2.0", "id": "1", "method": "tools/call", "params": {"name": "get_current_time", "arguments": {}}}

// External service response
{"jsonrpc": "2.0", "id": "1", "result": {"content": [{"type": "text", "text": "2025-09-23 14:30:00"}]}}
```

#### HTTP Communication (Client ↔ Wrapper)
```bash
curl -X POST http://host:8714/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "get_current_time", "arguments": {}}, "jsonrpc": "2.0", "id": 1}'
```

## Key Features

### 1. Dynamic Configuration
- **Template System**: Pre-define configuration templates for common external MCP services
- **Instance Management**: Create specific service instances based on templates
- **Hot Updates**: Support runtime addition, deletion, enable/disable services
- **Configuration Validation**: Built-in validation for instance configurations

### 2. Process Management
- **Independent Processes**: Each external service runs in an independent subprocess
- **Health Checks**: Real-time monitoring of process and communication thread status
- **Auto Restart**: Automatically restart when services crash
- **Graceful Shutdown**: Support proper process cleanup
- **Resource Management**: Automatic cleanup of processes and resources

### 3. Service Management
- **Unified Service Manager**: High-level coordination of all service operations
- **Intelligent Port Allocation**: Automatic port assignment and conflict resolution
- **Proxy Integration**: Seamless integration with LiteMCP proxy system
- **Service Discovery**: Automatic service registration and discovery

### 4. Error Handling
- **Connection Retry**: Automatic retry on communication failures
- **Error Logging**: Detailed error information and debug logs
- **Degradation Handling**: Return friendly error messages when services are unavailable
- **Health Monitoring**: Continuous health checks and status reporting

### 5. Integration Features
- **Unified Proxy**: Unified access through LiteMCP proxy server
- **Configuration API**: Automatically appears in `/config` interface
- **Friendly Naming**: Support Chinese display names and English URL paths
- **Multi-Transport Support**: HTTP, SSE, and STDIO transport modes

## 🚀 Quick Start

### 1. Install Dependencies

First ensure the necessary tools are installed on your system:

```bash
# Install uvx (for Python MCP services)
pip install uv

# Install Node.js and npm (for npx MCP services)
# Install Node.js according to your operating system

# Verify installation
uvx --version
npx --version
```

### 2. Install External MCP Services

```bash
# Install time server
uvx install mcp-server-time

# Install filesystem server
uvx install mcp-server-filesystem

# Test installation (optional)
uvx mcp-server-time --help
```

### 3. Configure External Services

Edit `config/external_mcp_servers.yaml`:

```yaml
external_mcp_servers:
  time:
    enabled: true                    # Enable time server
    name: "time"
    command: "uvx"
    args: ["mcp-server-time", "--local-timezone=Asia/Shanghai"]
    env: {}
    description: "Time and date operation tool server"
```

### 4. Configure LiteMCP Startup

Edit `config/servers.yaml`:

```yaml
mcp_servers:
  external_time:
    enabled: true                    # Enable external time server
    server_type: "external_time"     
    transport: "http"                
    host: null                       
    port: null                       
    auto_restart: true               
    description: "Time and date operation tool server (external uvx service)"
```

### 5. Start Services

```bash
# Start all services
./scripts/manage.sh up

# Or start only external time server
./scripts/manage.sh up --name external_time

# Check status
./scripts/manage.sh ps
```

## 📋 Built-in External Service Examples

### Time Server (external_time)

Time operation tools based on `mcp-server-time`.

**Features**:
- Get current time and date
- Timezone conversion
- Date formatting
- Time calculation

**Configuration Example**:
```yaml
time:
  enabled: true
  name: "time"
  command: "uvx"
  args: ["mcp-server-time", "--local-timezone=Asia/Shanghai"]
  env: {}
  description: "Time and date operation tool server"
```

**Usage Examples**:
```
- "Get current Beijing time"
- "Convert time to UTC"
- "Calculate difference between two dates"
```

### Jina AI Toolkit (external_jina)

AI-driven toolkit based on `jina-mcp-tools`.

**Features**:
- Web content search and analysis
- Text summarization and extraction
- Semantic search
- Document understanding

**Configuration Example**:
```yaml
jina-tools:
  enabled: true
  name: "jina-tools"
  command: "npx"
  args: ["jina-mcp-tools"]
  env:
    JINA_API_KEY: "${JINA_API_KEY}"  # Get from environment variable
  description: "Jina AI toolkit"
```

**Environment Variable Setup**:
```bash
export JINA_API_KEY="your_actual_api_key"
```

**Usage Examples**:
```
- "Search for latest articles about machine learning"
- "Summarize the content of this webpage"
- "Analyze key information in this text"
```

### Filesystem Tools (external_filesystem)

File operation tools based on `mcp-server-filesystem`.

**Features**:
- File reading and writing
- Directory creation and deletion
- File search and listing
- File information query

**Configuration Example**:
```yaml
filesystem:
  enabled: true
  name: "filesystem"
  command: "uvx"
  args: ["mcp-server-filesystem", "--write-to-cwd"]
  env: {}
  description: "Filesystem operation tools"
```

**Security Notes**:
- By default, only allows operations in current working directory
- Recommended for use in test environments
- Pay attention to file permissions and path security

**Usage Examples**:
```
- "Read the content of config.txt file"
- "Create a new file in temp directory"
- "List all .py files in current directory"
```

## 🔧 Custom External Services

### 1. Add Configuration

Add new service in `config/external_mcp_servers.yaml`:

```yaml
external_mcp_servers:
  my-custom-service:
    enabled: true
    name: "my-custom"
    command: "python"  # or uvx, npx, etc.
    args: ["/path/to/your/mcp_server.py"]
    env:
      CUSTOM_CONFIG: "value"
      API_KEY: "${MY_API_KEY}"
    description: "My custom MCP service"
    timeout: 45
    auto_restart: true
```

### 2. Create Wrapper Class

Create `src/tools/external/my_custom_server.py`:

```python
from .external_mcp_server import ExternalMCPServer, ExternalMCPConfig
from src.core.statistics import mcp_author

@mcp_author("Your Name", department="Test Department", project=["TD"])
class MyCustomMCPServer(ExternalMCPServer):
    """Custom external MCP service wrapper"""
    
    def __init__(self, name: str = "LiteMCP-MyCustom"):
        config = ExternalMCPConfig(
            name="my-custom",
            command="python",
            args=["/path/to/your/mcp_server.py"],
            env={"CUSTOM_CONFIG": "value"},
            description="My custom MCP service",
            timeout=45,
            auto_restart=True
        )
        super().__init__(config, name)
```

### 3. Register Service

Add in `src/tools/__init__.py`:

```python
AVAILABLE_SERVERS = {
    # ... other services
    "my_custom": {
        "description": "My custom MCP service",
        "module": "src.tools.external.my_custom_server",
        "class": "MyCustomMCPServer"
    }
}
```

### 4. Configure Startup

Add in `config/servers.yaml`:

```yaml
mcp_servers:
  my_custom:
    enabled: true
    server_type: "my_custom"
    transport: "http"
    host: null
    port: null
    auto_restart: true
    description: "My custom MCP service"
```

## 🛠️ Configuration Management

### Environment Variable Support

Configuration files support environment variable substitution:

```yaml
external_mcp_servers:
  my-service:
    env:
      API_KEY: "${MY_API_KEY}"          # Get from environment variable
      BASE_URL: "${BASE_URL:-http://localhost}"  # With default value
```

### Global Configuration

```yaml
global_config:
  default_timeout: 30                 # Default timeout
  enable_monitoring: true             # Enable monitoring
  restart_policy:
    max_retries: 3                    # Maximum retry count
    retry_interval: 10                # Retry interval
  logging:
    level: "INFO"                     # Log level
    include_external_output: true     # Include external service output
```

### Configuration Validation

Use configuration manager to validate configuration:

```python
from src.tools.external.config_manager import external_config_manager

# Validate configuration
validation_result = external_config_manager.validate_config()
print("Errors:", validation_result["errors"])
print("Warnings:", validation_result["warnings"])

# Get enabled services
enabled_servers = external_config_manager.get_enabled_servers()
print("Enabled services:", list(enabled_servers.keys()))
```

## Usage Methods

### 1. Management via manage.py

```bash
# Start all services (including external MCP services)
./scripts/manage.sh up

# Stop all services
./scripts/manage.sh down

# View service status
./scripts/manage.sh ps
```

### 2. Management via API

```bash
# Get all templates
curl http://localhost:9000/external-mcp/templates

# Create instance
curl -X POST http://localhost:9000/external-mcp/instances \
  -H "Content-Type: application/json" \
  -d '{"template_name": "time", "instance_name": "My Time Tool"}'

# Enable instance
curl -X POST http://localhost:9000/external-mcp/instances/{instance_id}/enable

# Start service
curl -X POST http://localhost:9000/external-mcp/instances/{instance_id}/start
```

### 3. Direct Service Access

```bash
# Access via proxy (recommended)
curl http://127.0.0.1:1888/mcp/external-time

# Direct wrapper access
curl http://172.17.18.20:8714/mcp
```

## 📊 Monitoring and Debugging

### View External Service Status

```bash
# View all service status
./scripts/manage.sh ps

# View service logs
tail -f runtime/logs/litemcp_src_tools_external_time_server_TimeMCPServer.log

# Detailed startup information
./scripts/manage.sh up --name external_time --verbose
```

### Debug External Services

1. **Check if commands are available**:
   ```bash
   uvx --version
   uvx mcp-server-time --help
   ```

2. **Test external service running independently**:
   ```bash
   uvx mcp-server-time --local-timezone=Asia/Shanghai
   ```

3. **Check environment variables**:
   ```bash
   echo $JINA_API_KEY
   ```

4. **View detailed error logs**:
   ```bash
   ./scripts/manage.sh up --name external_jina --verbose
   ```

## File Structure

```
src/tools/external/
├── README.md                    # This document (English)
├── README.zh_CN.md              # Chinese version
├── __init__.py                  # Module initialization
├── config_manager.py            # Configuration manager
├── external_mcp_server.py       # Wrapper server
├── process_manager.py           # Process manager
└── service_manager.py           # Service manager

config/
└── external_mcp.json            # Instance configuration

src/controller/
└── external_mcp_api.py          # API controller
```

## Troubleshooting

### 1. Service Startup Failure
- Check if external commands are available (e.g., `uvx`, `npx`)
- View log files: `runtime/logs/litemcp_src_tools_external_*.log`
- Confirm ports are not occupied

### 2. Communication Issues
- Check if STDIO communication threads are normal
- Verify JSON-RPC message format
- View process status: `ps aux | grep mcp-server`

### 3. Proxy Registration Issues
- Confirm proxy server is running normally
- Check service registration status: `curl http://host:1888/proxy/status`
- Verify configuration API returns: `curl http://localhost:9000/config`

## Extension Development

### Adding New External MCP Services

1. **Add Template Configuration**
   ```json
   {
     "new_service": {
       "name": "new-service",
       "display_name": "New Service",
       "command": "npx",
       "args": ["new-mcp-service"],
       "env": {"API_KEY": "your_key"},
       "description": "New MCP service",
       "category": "utility",
       "transport": "http",
       "host": null,
       "port": null
     }
   }
   ```

2. **Create Instance**
   - Via API or directly modify `external_mcp_instances.json`

3. **Start Service**
   - Use `manage.py up` or API interface

### Custom Wrapper

If special processing logic is needed, you can inherit `ExternalMCPServer`:

```python
class CustomExternalMCPServer(ExternalMCPServer):
    def _register_tools(self):
        super()._register_tools()
        # Add custom logic
```

## ⚠️ Important Notes

### Security Considerations
- External services run in independent processes with the same system permissions
- Filesystem services require special attention to path security
- Sensitive information like API Keys should be managed using environment variables

### Performance Impact
- External services require additional startup time
- Inter-process communication adds latency
- Recommend enabling services based on actual needs

### Compatibility
- Ensure external MCP services support JSON-RPC 2.0 protocol
- Different versions of external services may have API differences
- Recommend regularly updating external service versions

### Troubleshooting
1. **Service startup failure**: Check if commands are available and permissions are sufficient
2. **Tool call failure**: Check parameter format and API Key configuration
3. **Connection timeout**: Adjust timeout settings
4. **Process abnormal exit**: Check external service error logs

### Development Notes
1. **Process Management**: External MCP services run in independent processes, ensure proper cleanup
2. **Port Allocation**: Use LiteMCP's port management system to avoid conflicts
3. **Error Handling**: External services may be unstable, need robust error handling
4. **Resource Cleanup**: Ensure all related processes are properly terminated when stopping services
5. **Logging**: Maintain detailed logs for problem diagnosis

## 📚 Further Reading

- [MCP Protocol Official Documentation](https://modelcontextprotocol.io/)
- [Available MCP Server List](https://github.com/modelcontextprotocol/servers)
- [LiteMCP Framework Usage Documentation](../../../docs/USAGE.md)
- [External MCP Service Integration Guide](../../../docs/EXTERNAL_MCP_GUIDE_EN.md)

Through the external MCP service integration feature, the LiteMCP framework can easily reuse existing MCP tools from the community, greatly expanding the framework's capabilities.

*This document describes the design and usage of the LiteMCP External MCP Service Manager. For questions or suggestions, please contact the development team or contribute via fork.*
