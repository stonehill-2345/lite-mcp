"""
External MCP Service Configuration Manager

Responsible for reading and managing external MCP service configurations, supporting loading template and instance settings from JSON configuration files.
Provides dynamic external MCP service management functionality.
"""

import os
import json
import uuid
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from .external_mcp_server import create_external_mcp_server
from src.core.utils import get_project_root
from src.core.logger import get_logger


class ExternalMCPConfigManager:
    """External MCP Service Configuration Manager
    
    Manages instance configurations for external MCP services:
    - instances.json: Stores service instances created by users
    """
    
    def __init__(self, instances_path: str = None):
        """Initialize configuration manager
        
        Args:
            instances_path: Instance configuration file path
        """
        self.logger = get_logger(__name__)
        
        project_root = get_project_root()
        
        if instances_path is None:
            instances_path = project_root / "config" / "external_mcp.json"
        
        self.instances_path = Path(instances_path)
        self.instances_data: Dict = {}
        
        self._load_instances()
    
    
    def _load_instances(self):
        """Load instance configuration file"""
        try:
            if not self.instances_path.exists():
                self.logger.info(f"External MCP instance configuration file does not exist, creating new file: {self.instances_path}")
                self.instances_data = {"instances": {}, "meta": {"version": "1.0.0", "created": datetime.now().isoformat()}}
                self._save_instances()
                return
            
            with open(self.instances_path, 'r', encoding='utf-8') as f:
                self.instances_data = json.load(f)
                
            self.logger.info(f"Loaded external MCP instance configuration: {self.instances_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load external MCP instance configuration: {e}")
            self.instances_data = {"instances": {}, "meta": {"version": "1.0.0", "created": datetime.now().isoformat()}}
    
    def _save_instances(self):
        """Save instance configuration to file"""
        try:
            # Ensure directory exists
            self.instances_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Update metadata
            self.instances_data.setdefault("meta", {})
            self.instances_data["meta"]["last_updated"] = datetime.now().isoformat()
            
            with open(self.instances_path, 'w', encoding='utf-8') as f:
                json.dump(self.instances_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Saved external MCP instance configuration: {self.instances_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save external MCP instance configuration: {e}")
            raise
    
    
    def get_instances(self) -> Dict[str, Dict]:
        """Get all instance configurations
        
        Returns:
            Dict[str, Dict]: Instance configuration dictionary
        """
        return self.instances_data.get("instances", {})
    
    def get_instance(self, instance_id: str) -> Optional[Dict]:
        """Get specified instance configuration
        
        Args:
            instance_id: Instance ID
            
        Returns:
            Optional[Dict]: Instance configuration, returns None if not found
        """
        return self.instances_data.get("instances", {}).get(instance_id)
    
    
    def create_instance_direct(self, instance_name: str, config: Dict) -> str:
        """Create instance directly without relying on templates
        
        Args:
            instance_name: Instance name
            config: Instance configuration
            
        Returns:
            str: Newly created instance ID
        """
        # Generate instance ID
        instance_id = str(uuid.uuid4())
        
        # Create instance configuration
        instance_config = {
            "instance_id": instance_id,
            "instance_name": instance_name,
            "name": instance_name,  # Add name field for validation
            "template_name": "custom",  # Use fixed template name
            "enabled": config.get("enabled", False),
            "command": config["command"],
            "args": config.get("args", []),
            "env": config.get("env", {}),
            "description": config.get("description", ""),
            "timeout": config.get("timeout", 30),
            "auto_restart": config.get("auto_restart", True),
            "transport": "http",
            "host": None,
            "port": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Validate configuration
        validation_errors = self.validate_instance(instance_config)
        if validation_errors:
            raise ValueError(f"Instance configuration validation failed: {', '.join(validation_errors)}")
        
        # Save instance
        if "instances" not in self.instances_data:
            self.instances_data["instances"] = {}
        
        self.instances_data["instances"][instance_id] = instance_config
        self._save_instances()
        
        self.logger.info(f"Directly created external MCP instance: {instance_name} (ID: {instance_id})")
        return instance_id
    
    def update_instance(self, instance_id: str, config: Dict) -> bool:
        """Update instance configuration
        
        Args:
            instance_id: Instance ID
            config: Configuration to update
            
        Returns:
            bool: Whether update was successful
        """
        if instance_id not in self.instances_data.get("instances", {}):
            return False
        
        # Update configuration
        self.instances_data["instances"][instance_id].update(config)
        self.instances_data["instances"][instance_id]["updated"] = datetime.now().isoformat()
        
        # Process environment variables
        self._process_env_vars(self.instances_data["instances"][instance_id])
        
        self._save_instances()
        
        instance_name = self.instances_data["instances"][instance_id].get("instance_name", instance_id)
        self.logger.info(f"Updated external MCP service instance: {instance_name} (ID: {instance_id})")
        return True
    
    def delete_instance(self, instance_id: str) -> bool:
        """Delete instance
        
        Args:
            instance_id: Instance ID
            
        Returns:
            bool: Whether deletion was successful
        """
        if instance_id not in self.instances_data.get("instances", {}):
            return False
        
        instance_name = self.instances_data["instances"][instance_id].get("instance_name", instance_id)
        del self.instances_data["instances"][instance_id]
        self._save_instances()
        
        self.logger.info(f"Deleted external MCP service instance: {instance_name} (ID: {instance_id})")
        return True
    
    def enable_instance(self, instance_id: str) -> bool:
        """Enable instance
        
        Args:
            instance_id: Instance ID
            
        Returns:
            bool: Whether operation was successful
        """
        return self.update_instance(instance_id, {"enabled": True})
    
    def disable_instance(self, instance_id: str) -> bool:
        """Disable instance
        
        Args:
            instance_id: Instance ID
            
        Returns:
            bool: Whether operation was successful
        """
        return self.update_instance(instance_id, {"enabled": False})
    
    def get_enabled_instances(self) -> Dict[str, Dict]:
        """Get all enabled instances
        
        Returns:
            Dict[str, Dict]: Enabled instance configuration dictionary
        """
        enabled_instances = {}
        instances = self.get_instances()
        
        for instance_id, instance_config in instances.items():
            if instance_config.get("enabled", False):
                enabled_instances[instance_id] = instance_config
        
        return enabled_instances

    @staticmethod
    def _process_env_vars(config: Dict):
        """Process environment variables in configuration
        
        Args:
            config: Configuration dictionary to process
        """
        env = config.get("env", {})
        processed_env = {}
        
        for key, value in env.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var_name = value[2:-1]
                # Support default value syntax: ${VAR_NAME:-default_value}
                if ":-" in env_var_name:
                    var_name, default_value = env_var_name.split(":-", 1)
                    processed_env[key] = os.getenv(var_name, default_value)
                else:
                    processed_env[key] = os.getenv(env_var_name, value)
            else:
                processed_env[key] = value
        
        config["env"] = processed_env
    
    def create_server_instances(self) -> Dict[str, object]:
        """Create all enabled external MCP server instances
        
        Returns:
            Dict[str, object]: Server instance dictionary
        """
        instances = {}
        enabled_instances = self.get_enabled_instances()
        
        for instance_id, config in enabled_instances.items():
            try:
                instance = create_external_mcp_server(instance_id, config)
                instances[instance_id] = instance
                self.logger.info(f"Created external MCP server instance: {config.get('instance_name', instance_id)}")
            except Exception as e:
                self.logger.error(f"Failed to create server instance {instance_id}: {e}")
        
        return instances

    @staticmethod
    def validate_template(template_config: Dict) -> List[str]:
        """Validate template configuration validity
        
        Args:
            template_config: Template configuration
            
        Returns:
            List[str]: Validation error list
        """
        errors = []
        
        # Check required fields
        required_fields = ["name", "command", "args", "description"]
        for field in required_fields:
            if field not in template_config:
                errors.append(f"Missing required field: {field}")
        
        # Check if command exists
        command = template_config.get("command")
        if command:
            import shutil
            if not shutil.which(command):
                errors.append(f"Command does not exist: {command}")
        
        return errors
    
    def validate_instance(self, instance_config: Dict) -> List[str]:
        """Validate instance configuration validity
        
        Args:
            instance_config: Instance configuration
            
        Returns:
            List[str]: Validation error list
        """
        errors = self.validate_template(instance_config)
        
        # Check instance-specific fields
        if "instance_id" not in instance_config:
            errors.append("Missing instance ID")
        
        return errors
    
    def reload_config(self):
        """Reload configuration file"""
        self._load_instances()


# Global configuration manager instance
external_config_manager = ExternalMCPConfigManager()