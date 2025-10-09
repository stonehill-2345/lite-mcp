"""
External MCP Service Management API

Provides REST API interfaces for managing external MCP services, including:
- Query templates and instances
- Create, update, delete instances
- Enable, disable services
- Dynamic service management
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.tools.external.config_manager import external_config_manager
from src.tools.external.process_manager import external_process_manager
from src.tools.external.service_manager import external_service_manager
from src.core.logger import get_logger
from src.core.statistics import async_update_statistics

# API router
external_mcp_router = APIRouter(prefix="/api/v1/external-mcp", tags=["External MCP Service Management"])
logger = get_logger(__name__)


# Data models
class MCPTemplate(BaseModel):
    """MCP template data model"""
    name: str = Field(..., description="Template name")
    display_name: str = Field(..., description="Display name")
    command: str = Field(..., description="Startup command")
    args: List[str] = Field(..., description="Command arguments")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    description: str = Field("", description="Service description")
    category: str = Field("utility", description="Service category")
    requirements: Dict[str, Any] = Field(default_factory=dict, description="Dependency requirements")
    timeout: int = Field(30, description="Startup timeout")
    auto_restart: bool = Field(True, description="Auto restart")


class MCPInstance(BaseModel):
    """MCP instance data model"""
    instance_id: Optional[str] = Field(None, description="Instance ID (auto-generated when created)")
    instance_name: str = Field(..., description="Instance name")
    template_name: Optional[str] = Field("custom", description="Template name")
    enabled: bool = Field(False, description="Whether enabled")
    command: str = Field(..., description="Startup command")
    args: List[str] = Field(..., description="Command arguments")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    description: str = Field("", description="Service description")
    timeout: int = Field(30, description="Startup timeout")
    auto_restart: bool = Field(True, description="Auto restart")


class CreateInstanceRequest(BaseModel):
    """Create instance request model"""
    instance_name: str = Field(..., description="Instance name")
    command: str = Field(..., description="Startup command")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    description: str = Field("", description="Service description")
    timeout: int = Field(30, description="Timeout (seconds)")
    auto_restart: bool = Field(True, description="Auto restart")
    enabled: bool = Field(False, description="Whether enabled")


class UpdateInstanceRequest(BaseModel):
    """Update instance request model"""
    instance_name: Optional[str] = Field(None, description="Instance name")
    command: Optional[str] = Field(None, description="Startup command")
    args: Optional[List[str]] = Field(None, description="Command arguments")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    description: Optional[str] = Field(None, description="Service description")
    timeout: Optional[int] = Field(None, description="Startup timeout")
    auto_restart: Optional[bool] = Field(None, description="Auto restart")


# API endpoints

@external_mcp_router.get("/instances", response_model=Dict[str, Dict])
def get_instances(enabled_only: bool = Query(False, description="Only return enabled instances")):
    """Get all external MCP instances"""
    try:
        if enabled_only:
            instances = external_config_manager.get_enabled_instances()
        else:
            instances = external_config_manager.get_instances()
        return instances
    except Exception as e:
        logger.error(f"Failed to get instance list: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get instance list: {str(e)}")


@external_mcp_router.get("/instances/{instance_id}", response_model=Dict)
def get_instance(instance_id: str):
    """Get specified external MCP instance"""
    try:
        instance = external_config_manager.get_instance(instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail=f"Instance not found: {instance_id}")
        return instance
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get instance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get instance: {str(e)}")


@external_mcp_router.post("/instances", response_model=Dict[str, str])
def create_instance(request: CreateInstanceRequest):
    """Create new external MCP instance"""
    try:
        # Create instance directly without relying on templates
        instance_config = {
            "instance_name": request.instance_name,
            "command": request.command,
            "args": request.args,
            "env": request.env,
            "description": request.description,
            "timeout": request.timeout,
            "auto_restart": request.auto_restart,
            "enabled": request.enabled
        }
        
        # Create instance
        instance_id = external_config_manager.create_instance_direct(
            instance_name=request.instance_name,
            config=instance_config
        )
        
        logger.info(f"Created external MCP instance: {instance_id}")
        return {"instance_id": instance_id, "message": "Instance created successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create instance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create instance: {str(e)}")


@external_mcp_router.put("/instances/{instance_id}", response_model=Dict[str, str])
def update_instance(instance_id: str, request: UpdateInstanceRequest):
    """Update external MCP instance configuration"""
    try:
        # Check if instance exists
        instance = external_config_manager.get_instance(instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail=f"Instance not found: {instance_id}")
        
        # Prepare update configuration
        update_config = {}
        for field, value in request.dict(exclude_unset=True).items():
            if value is not None:
                update_config[field] = value
        
        # Update instance
        success = external_config_manager.update_instance(instance_id, update_config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update instance")
        
        logger.info(f"Updated external MCP instance: {instance_id}")
        return {"message": "Instance updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update instance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update instance: {str(e)}")


@external_mcp_router.delete("/instances/{instance_id}", response_model=Dict[str, str])
def delete_instance(instance_id: str):
    """Delete external MCP instance"""
    try:
        # Check if instance exists
        instance = external_config_manager.get_instance(instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail=f"Instance not found: {instance_id}")

        # Check if instance is enabled, enabled instances cannot be deleted
        if instance.get("enabled", False):
            raise HTTPException(status_code=400, detail=f"Cannot delete enabled instance: {instance.get('instance_name', instance_id)}, please disable it first")

        # Delete instance
        success = external_config_manager.delete_instance(instance_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete instance")

        logger.info(f"Deleted external MCP instance: {instance_id}")

        # Async update statistics (avoid blocking API response)
        try:
            async_update_statistics(delay_seconds=1, context="after deleting external MCP service")
        except Exception as e:
            logger.warning(f"Failed to start statistics update: {e}")

        return {"message": "Instance deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete instance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete instance: {str(e)}")


@external_mcp_router.post("/instances/{instance_id}/enable", response_model=Dict[str, str])
def enable_instance(instance_id: str, proxy_url: Optional[str] = Query(None, description="Proxy server URL")):
    """Enable external MCP instance (actually start service and register to proxy)"""
    try:
        logger.info(f"Enabling external MCP instance: {instance_id}")

        # Use unified service manager
        success, details = external_service_manager.start_service(instance_id, proxy_url)

        if not success:
            error_msg = details.get('error', 'Unknown error')
            logger.error(f"Failed to enable instance: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)

        # Build return result
        result = {
            "message": f"Instance enabled successfully: {details['instance_name']}",
            "instance_name": details['instance_name'],
            "host": details['host'],
            "port": str(details['port']),  # Convert to string
            "transport": details['transport']
        }

        logger.info(f"External MCP instance enabled successfully: {details['instance_name']} -> {details['host']}:{details['port']}")

        # Async update statistics (avoid blocking API response)
        try:
            async_update_statistics(delay_seconds=3, context="after enabling external MCP service")
        except Exception as e:
            logger.warning(f"Failed to start statistics update: {e}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable instance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enable instance: {str(e)}")


@external_mcp_router.post("/instances/{instance_id}/disable", response_model=Dict[str, str])
def disable_instance(instance_id: str, proxy_url: Optional[str] = Query(None, description="Proxy server URL")):
    """Disable external MCP instance (actually stop service and unregister from proxy)"""
    try:
        logger.info(f"Disabling external MCP instance: {instance_id}")

        # Use unified service manager
        success, details = external_service_manager.stop_service(instance_id, proxy_url, disable_config=True)

        if not success:
            error_msg = details.get('error', 'Unknown error')
            logger.error(f"Failed to disable instance: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)

        # Build return result
        result = {
            "message": f"Instance disabled successfully: {details['instance_name']}",
            "instance_name": details['instance_name'],
            "service_stopped": "true" if details['service_stopped'] else "false",
            "config_updated": "true" if details['config_updated'] else "false"
        }

        if proxy_url and 'proxy_unregistered' in details:
            result["proxy_unregistered"] = "true" if details['proxy_unregistered'] else "false"

        logger.info(f"External MCP instance disabled successfully: {details['instance_name']}")

        # Async update statistics (avoid blocking API response)
        try:
            async_update_statistics(delay_seconds=2, context="after disabling external MCP service")
        except Exception as e:
            logger.warning(f"Failed to start statistics update: {e}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable instance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to disable instance: {str(e)}")


@external_mcp_router.get("/instances/{instance_id}/validate", response_model=Dict[str, Any])
def validate_instance(instance_id: str):
    """Validate external MCP instance configuration"""
    try:
        # Check if instance exists
        instance = external_config_manager.get_instance(instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail=f"Instance not found: {instance_id}")

        # Validate configuration
        errors = external_config_manager.validate_instance(instance)

        return {
            "instance_id": instance_id,
            "valid": len(errors) == 0,
            "errors": errors
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate instance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to validate instance: {str(e)}")


@external_mcp_router.post("/reload", response_model=Dict[str, str])
def reload_config():
    """Reload configuration file"""
    try:
        external_config_manager.reload_config()
        logger.info("Reloaded external MCP configuration file")
        return {"message": "Configuration file reloaded successfully"}

    except Exception as e:
        logger.error(f"Failed to reload configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reload configuration: {str(e)}")


@external_mcp_router.get("/status", response_model=Dict[str, Any])
def get_status():
    """Get external MCP service status"""
    try:
        instances = external_config_manager.get_instances()
        enabled_instances = external_config_manager.get_enabled_instances()

        return {
            "total_instances": len(instances),
            "enabled_instances": len(enabled_instances),
            "disabled_instances": len(instances) - len(enabled_instances),
            "enabled_instance_ids": list(enabled_instances.keys())
        }

    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


# Dynamic service management endpoints
@external_mcp_router.get("/services/running", response_model=Dict[str, Dict])
def get_running_services():
    """Get all running external MCP services"""
    try:
        running_services = external_process_manager.get_running_services()
        return running_services
    except Exception as e:
        logger.error(f"Failed to get running services: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get running services: {str(e)}")


@external_mcp_router.get("/services/{instance_id}/status", response_model=Dict[str, Any])
def get_service_status(instance_id: str):
    """Get running status of specified service"""
    try:
        status = external_process_manager.get_service_status(instance_id)
        return status
    except Exception as e:
        logger.error(f"Failed to get service status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get service status: {str(e)}")


@external_mcp_router.post("/services/{instance_id}/start", response_model=Dict[str, str])
def start_service(
    instance_id: str,
    transport: str = Query("http", description="Transport protocol (stdio/http/sse)"),
    host: str = Query(None, description="Listen host"),
    port: int = Query(None, description="Listen port")
):
    """Start specified external MCP service"""
    try:
        # Check if instance exists
        instance = external_config_manager.get_instance(instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail=f"Instance not found: {instance_id}")

        # Start service
        # Get instance configuration for starting process
        instance_config = external_config_manager.get_instance(instance_id)
        if not instance_config:
            raise HTTPException(status_code=404, detail=f"Instance not found: {instance_id}")
        success = external_process_manager.start_process(instance_id, instance_config, transport, host, port)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to start service")

        logger.info(f"Started external MCP service: {instance_id}")
        return {"message": f"Service started successfully: {instance_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start service: {str(e)}")


@external_mcp_router.post("/services/{instance_id}/stop", response_model=Dict[str, str])
def stop_service(instance_id: str):
    """Stop specified external MCP service"""
    try:
        # Check if instance exists
        instance = external_config_manager.get_instance(instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail=f"Instance not found: {instance_id}")

        # Stop service
        success = external_process_manager.stop_process(instance_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to stop service")

        logger.info(f"Stopped external MCP service: {instance_id}")
        return {"message": f"Service stopped successfully: {instance_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop service: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop service: {str(e)}")


@external_mcp_router.post("/services/{instance_id}/restart", response_model=Dict[str, str])
def restart_service(
    instance_id: str,
    transport: str = Query("http", description="Transport protocol (stdio/http/sse)"),
    host: str = Query(None, description="Listen host"),
    port: int = Query(None, description="Listen port")
):
    """Restart specified external MCP service"""
    try:
        # Check if instance exists
        instance = external_config_manager.get_instance(instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail=f"Instance not found: {instance_id}")

        # Restart service
        # Get instance configuration for restarting process
        instance_config = external_config_manager.get_instance(instance_id)
        if not instance_config:
            raise HTTPException(status_code=404, detail=f"Instance not found: {instance_id}")
        success = external_process_manager.restart_process(instance_id, instance_config, transport, host, port)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to restart service")

        logger.info(f"Restarted external MCP service: {instance_id}")
        return {"message": f"Service restarted successfully: {instance_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restart service: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to restart service: {str(e)}")


@external_mcp_router.post("/services/start-all", response_model=Dict[str, Any])
def start_all_services(
    transport: str = Query("http", description="Transport protocol (stdio/http/sse)"),
    host: str = Query(None, description="Listen host")
):
    """Start all enabled external MCP services"""
    try:
        # Use unified service manager to start all services
        results = external_service_manager.start_all_enabled_services()

        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        logger.info(f"Batch started external MCP services: {success_count}/{total_count} successful")

        # Async update statistics (avoid blocking API response)
        if success_count > 0:
            try:
                async_update_statistics(delay_seconds=5, context="after batch starting external MCP services")
            except Exception as e:
                logger.warning(f"Failed to start statistics update: {e}")

        return {
            "message": f"Batch start completed: {success_count}/{total_count} successful",
            "results": results,
            "success_count": success_count,
            "total_count": total_count
        }

    except Exception as e:
        logger.error(f"Failed to batch start services: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to batch start services: {str(e)}")


@external_mcp_router.post("/services/stop-all", response_model=Dict[str, Any])
def stop_all_services():
    """Stop all running external MCP services"""
    try:
        # Use unified service manager to stop all services
        results = external_service_manager.stop_all_services()

        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        logger.info(f"Batch stopped external MCP services: {success_count}/{total_count} successful")

        # Async update statistics (avoid blocking API response)
        if success_count > 0:
            try:
                async_update_statistics(delay_seconds=3, context="after batch stopping external MCP services")
            except Exception as e:
                logger.warning(f"Failed to start statistics update: {e}")
        
        return {
            "message": f"Batch stop completed: {success_count}/{total_count} successful",
            "results": results,
            "success_count": success_count,
            "total_count": total_count
        }
        
    except Exception as e:
        logger.error(f"Failed to batch stop services: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to batch stop services: {str(e)}")
