
"""
Configuration Management - Unified config reading from servers.yaml
"""

import yaml
from typing import Optional
from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class ProxyServerConfig(BaseModel):
    """Proxy server configuration"""
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 1888
    auto_restart: bool = True
    auto_register: bool = True
    description: str = "MCP reverse proxy server"

    # Path prefix configuration
    mcp_prefix: str = "mcp"
    sse_prefix: str = "sse"
    status_prefix: str = "proxy"

    # Timeout configuration (seconds)
    timeout: int = 30                        # Overall timeout
    connect_timeout: int = 5                 # Connection timeout

class APIServerConfig(BaseModel):
    """API server configuration"""
    enabled: bool = True
    host: Optional[str] = None
    port: int = 9000
    auto_restart: bool = True
    description: str = "Configuration API server"


class Settings(BaseSettings):
    """Main configuration class - reads from servers.yaml"""

    proxy_server: ProxyServerConfig = Field(default_factory=ProxyServerConfig)
    api_server: APIServerConfig = Field(default_factory=APIServerConfig)

    model_config = {
        "extra": "ignore"
    }

    @classmethod
    def load_from_yaml(cls, config_file: Optional[Path] = None) -> "Settings":
        """Load configuration from YAML file"""
        if config_file is None:
            # Get project root directory
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            config_file = project_root / "config" / "servers.yaml"

        if not config_file.exists():
            # Return default configuration
            return cls()

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f) or {}

            # Extract relevant configuration sections
            config_data = {}

            if 'proxy_server' in yaml_config:
                config_data['proxy_server'] = yaml_config['proxy_server']

            if 'api_server' in yaml_config:
                config_data['api_server'] = yaml_config['api_server']

            return cls(**config_data)

        except Exception as e:
            print(f"Warning: Failed to load config from {config_file}: {e}")
            return cls()

    @property
    def proxy_host(self) -> str:
        """Get proxy server host"""
        return self.proxy_server.host

    @property
    def proxy_port(self) -> int:
        """Get proxy server port"""
        return self.proxy_server.port

    @property
    def api_host(self) -> Optional[str]:
        """Get API server host"""
        return self.api_server.host

    @property
    def api_port(self) -> int:
        """Get API server port"""
        return self.api_server.port


# Create global configuration instance
settings = Settings.load_from_yaml()
