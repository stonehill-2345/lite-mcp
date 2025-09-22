"""
LiteMCP Statistics API Controller

Provides statistics data query interfaces, supporting queries for server, tool, author, and other statistical information.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime

from src.core.statistics import statistics_manager
from src.core.logger import get_logger

# Create API router
router = APIRouter(prefix="/api/v1/statistics", tags=["Statistics"])

# Create logger
logger = get_logger("litemcp.api.statistics")


@router.get("/", summary="Get Statistics Overview", description="Get overall statistics information overview")
async def get_statistics_overview():
    """Get statistics overview information
    
    Returns:
        Dictionary containing overall statistics information
    """
    try:
        summary = statistics_manager.get_summary()
        logger.info("Successfully retrieved statistics overview")
        return {
            "success": True,
            "data": summary,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Failed to get statistics overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics overview: {str(e)}")


@router.get("/full", summary="Get Complete Statistics Information", description="Get complete statistics information including servers, tools, authors, etc.")
async def get_full_statistics():
    """Get complete statistics information
    
    Returns:
        Dictionary containing all statistics information
    """
    try:
        statistics = statistics_manager.get_statistics()
        logger.info("Successfully retrieved complete statistics information")
        return {
            "success": True,
            "data": statistics,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Failed to get complete statistics information: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get complete statistics information: {str(e)}")


@router.get("/servers", summary="Get Server Statistics", description="Get statistics information for all MCP servers")
async def get_server_statistics():
    """Get server statistics information
    
    Returns:
        List of server statistics information
    """
    try:
        servers = statistics_manager.get_server_statistics()
        logger.info(f"Successfully retrieved server statistics: {len(servers)} servers")
        return {
            "success": True,
            "data": servers,
            "count": len(servers),
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Failed to get server statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get server statistics: {str(e)}")


def _get_item_detail(item_name: str, item_type: str, items_dict: dict, item_display_name: str):
    """Common method to get detailed statistics information for a specific item
    
    Args:
        item_name: Item name
        item_type: Item type (for logging and error messages)
        items_dict: Item dictionary
        item_display_name: Item display name (for error messages)
        
    Returns:
        Detailed statistics information for the specified item
    """
    try:
        if item_name not in items_dict:
            raise HTTPException(status_code=404, detail=f"{item_display_name} '{item_name}' not found")
        
        item_info = items_dict[item_name].to_dict()
        logger.info(f"Successfully retrieved {item_display_name} '{item_name}' statistics")
        return {
            "success": True,
            "data": item_info,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get {item_display_name} '{item_name}' statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get {item_type} statistics: {str(e)}")


@router.get("/servers/{server_name}", summary="Get Specific Server Statistics", description="Get detailed statistics information for a specified server")
async def get_server_detail(server_name: str):
    """Get detailed statistics information for a specific server
    
    Args:
        server_name: Server name
        
    Returns:
        Detailed statistics information for the specified server
    """
    return _get_item_detail(server_name, "server", statistics_manager.servers, "Server")


@router.post("/servers/batch", summary="Batch Get Server Statistics", description="Batch get detailed statistics information for multiple servers")
async def get_servers_batch(server_names: list[str]):
    """Batch get detailed statistics information for servers
    
    Args:
        server_names: List of server names
        
    Returns:
        List of server statistics information, including successful and failed results
    """
    try:
        results = []
        success_count = 0
        
        for server_name in server_names:
            if server_name in statistics_manager.servers:
                server_info = statistics_manager.servers[server_name].to_dict()
                results.append({
                    "server_name": server_name,
                    "success": True,
                    "data": server_info
                })
                success_count += 1
            else:
                results.append({
                    "server_name": server_name,
                    "success": False,
                    "error": f"Server '{server_name}' not found"
                })
        
        logger.info(f"Batch server statistics retrieval completed: {success_count}/{len(server_names)} successful")
        return {
            "success": True,
            "data": results,
            "total": len(server_names),
            "success_count": success_count,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Failed to batch get server statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to batch get server statistics: {str(e)}")


@router.get("/tools", summary="Get Tool Statistics", description="Get statistics information for all MCP tools")
async def get_tool_statistics():
    """Get tool statistics information
    
    Returns:
        List of tool statistics information
    """
    try:
        tools = statistics_manager.get_tool_statistics()
        logger.info(f"Successfully retrieved tool statistics: {len(tools)} tools")
        return {
            "success": True,
            "data": tools,
            "count": len(tools),
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Failed to get tool statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tool statistics: {str(e)}")


@router.get("/tools/{tool_name}", summary="Get Specific Tool Statistics", description="Get detailed statistics information for a specified tool")
async def get_tool_detail(tool_name: str):
    """Get detailed statistics information for a specific tool
    
    Args:
        tool_name: Tool name
        
    Returns:
        Detailed statistics information for the specified tool
    """
    return _get_item_detail(tool_name, "tool", statistics_manager.tools, "Tool")


@router.post("/tools/batch", summary="Batch Get Tool Statistics", description="Batch get detailed statistics information for multiple tools")
async def get_tools_batch(tool_names: list[str]):
    """Batch get detailed statistics information for tools
    
    Args:
        tool_names: List of tool names
        
    Returns:
        List of tool statistics information, including successful and failed results
    """
    try:
        results = []
        success_count = 0
        
        for tool_name in tool_names:
            if tool_name in statistics_manager.tools:
                tool_info = statistics_manager.tools[tool_name].to_dict()
                results.append({
                    "tool_name": tool_name,
                    "success": True,
                    "data": tool_info
                })
                success_count += 1
            else:
                results.append({
                    "tool_name": tool_name,
                    "success": False,
                    "error": f"Tool '{tool_name}' not found"
                })
        
        logger.info(f"Batch tool statistics retrieval completed: {success_count}/{len(tool_names)} successful")
        return {
            "success": True,
            "data": results,
            "total": len(tool_names),
            "success_count": success_count,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Failed to batch get tool statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to batch get tool statistics: {str(e)}")


@router.get("/authors", summary="Get Author Statistics", description="Get statistics information for all authors")
async def get_author_statistics():
    """Get author statistics information
    
    Returns:
        List of author statistics information
    """
    try:
        authors = statistics_manager.get_author_statistics()
        logger.info(f"Successfully retrieved author statistics: {len(authors)} authors")
        return {
            "success": True,
            "data": authors,
            "count": len(authors),
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Failed to get author statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get author statistics: {str(e)}")


@router.get("/authors/{author_name}", summary="Get Specific Author Statistics", description="Get detailed statistics information for a specified author")
async def get_author_detail(author_name: str):
    """Get detailed statistics information for a specific author
    
    Args:
        author_name: Author name
        
    Returns:
        Detailed statistics information for the specified author
    """
    try:
        authors = statistics_manager.get_author_statistics()
        author_info = None
        
        for author in authors:
            if author["name"] == author_name:
                author_info = author
                break
        
        if author_info is None:
            raise HTTPException(status_code=404, detail=f"Author '{author_name}' not found")
        
        logger.info(f"Successfully retrieved author '{author_name}' statistics")
        return {
            "success": True,
            "data": author_info,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get author '{author_name}' statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get author statistics: {str(e)}")


@router.post("/authors/batch", summary="Batch Get Author Statistics", description="Batch get detailed statistics information for multiple authors")
async def get_authors_batch(author_names: list[str]):
    """Batch get detailed statistics information for authors
    
    Args:
        author_names: List of author names
        
    Returns:
        List of author statistics information, including successful and failed results
    """
    try:
        authors = statistics_manager.get_author_statistics()
        authors_dict = {author["name"]: author for author in authors}
        
        results = []
        success_count = 0
        
        for author_name in author_names:
            if author_name in authors_dict:
                results.append({
                    "author_name": author_name,
                    "success": True,
                    "data": authors_dict[author_name]
                })
                success_count += 1
            else:
                results.append({
                    "author_name": author_name,
                    "success": False,
                    "error": f"Author '{author_name}' not found"
                })
        
        logger.info(f"Batch author statistics retrieval completed: {success_count}/{len(author_names)} successful")
        return {
            "success": True,
            "data": results,
            "total": len(author_names),
            "success_count": success_count,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Failed to batch get author statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to batch get author statistics: {str(e)}")


@router.get("/projects", summary="Get Project Statistics", description="Get statistics information grouped by project")
async def get_project_statistics():
    """Get project statistics information
    
    Returns:
        Statistics information grouped by project, including detailed contribution statistics for each project
    """
    try:
        # Get project statistics directly from summary
        summary = statistics_manager.get_summary()
        projects = summary.get("projects", [])
        
        logger.info(f"Successfully retrieved project statistics: {len(projects)} projects")
        return {
            "success": True,
            "data": projects,
            "count": len(projects),
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Failed to get project statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get project statistics: {str(e)}")


@router.get("/projects/{project_name}", summary="Get Specific Project Statistics", description="Get detailed statistics information for a specified project")
async def get_project_detail(project_name: str):
    """Get detailed statistics information for a specific project
    
    Args:
        project_name: Project name
        
    Returns:
        Detailed statistics information for the specified project
    """
    try:
        summary = statistics_manager.get_summary()
        projects = summary.get("projects", [])
        
        project_info = None
        for project in projects:
            if project["name"] == project_name:
                project_info = project
                break
        
        if project_info is None:
            raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")
        
        logger.info(f"Successfully retrieved project '{project_name}' statistics")
        return {
            "success": True,
            "data": project_info,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project '{project_name}' statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get project statistics: {str(e)}")


@router.get("/projects/{project_name}/servers", summary="Get Servers Under Project", description="Get all servers under a specified project")
async def get_project_servers(project_name: str):
    """Get all servers under a specified project
    
    Args:
        project_name: Project name
        
    Returns:
        List of servers under the project
    """
    try:
        servers = []
        for server in statistics_manager.servers.values():
            if server.author.project and project_name in server.author.project:
                servers.append(server.to_dict())
        
        logger.info(f"Successfully retrieved servers under project '{project_name}': {len(servers)} servers")
        return {
            "success": True,
            "data": servers,
            "count": len(servers),
            "project": project_name,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Failed to get servers under project '{project_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get project servers: {str(e)}")


@router.get("/projects/{project_name}/tools", summary="Get Tools Under Project", description="Get all tools under a specified project")
async def get_project_tools(project_name: str):
    """Get all tools under a specified project
    
    Args:
        project_name: Project name
        
    Returns:
        List of tools under the project
    """
    try:
        tools = []
        for tool in statistics_manager.tools.values():
            if tool.author.project and project_name in tool.author.project:
                tools.append(tool.to_dict())
        
        logger.info(f"Successfully retrieved tools under project '{project_name}': {len(tools)} tools")
        return {
            "success": True,
            "data": tools,
            "count": len(tools),
            "project": project_name,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Failed to get tools under project '{project_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get project tools: {str(e)}")


@router.get("/departments", summary="Get Department Statistics", description="Get statistics information grouped by department")
async def get_department_statistics():
    """Get department statistics information
    
    Returns:
        Statistics information grouped by department, including detailed contribution statistics for each department
    """
    try:
        # Get department statistics directly from summary
        summary = statistics_manager.get_summary()
        departments = summary.get("departments", [])
        
        logger.info(f"Successfully retrieved department statistics: {len(departments)} departments")
        return {
            "success": True,
            "data": departments,
            "count": len(departments),
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Failed to get department statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get department statistics: {str(e)}")


@router.get("/report", summary="Generate Statistics Report", description="Generate statistics report containing various dimensions")
async def generate_statistics_report():
    """Generate statistics report
    
    Returns:
        Report containing statistics information from various dimensions
    """
    try:
        # Get basic statistics information
        summary = statistics_manager.get_summary()
        servers = statistics_manager.get_server_statistics()
        tools = statistics_manager.get_tool_statistics()
        authors = statistics_manager.get_author_statistics()
        
        # Generate report data
        report = {
            "summary": summary,
            "details": {
                "servers": servers,
                "tools": tools,
                "authors": authors
            },
            "analytics": {
                "top_authors": summary.get("top_authors", [])[:10],  # Use already sorted data from summary
                "tool_distribution": {
                    "servers_with_tools": len([s for s in servers if s["tool_count"] > 0]),
                    "servers_without_tools": len([s for s in servers if s["tool_count"] == 0]),
                    "avg_tools_per_server": sum(s["tool_count"] for s in servers) / len(servers) if servers else 0
                },
                "recent_updates": sorted(servers, key=lambda x: x["last_update"], reverse=True)[:5],
                "department_rankings": summary.get("departments", [])[:5],  # Department rankings
                "project_rankings": summary.get("projects", [])[:5]        # Project rankings
            }
        }
        
        logger.info("Successfully generated statistics report")
        return {
            "success": True,
            "data": report,
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Failed to generate statistics report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate statistics report: {str(e)}")


@router.post("/rebuild", summary="Rebuild Statistics Data", description="Clear existing data and re-collect all statistics information")
async def rebuild_statistics():
    """Rebuild statistics data
    
    Clear existing data and re-collect statistics information from all active servers.
    Used for handling data inconsistencies or when complete regeneration of statistics data is needed.
    
    Returns:
        Result of the rebuild operation
    """
    try:
        # Import rebuild function
        from src.core.statistics import rebuild_all_statistics
        
        # Execute rebuild
        rebuild_all_statistics()
        
        # Get summary after rebuild
        summary = statistics_manager.get_summary()
        
        logger.info("Successfully rebuilt statistics data")
        return {
            "success": True,
            "message": "Statistics data rebuild successful",
            "summary": summary,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Failed to rebuild statistics data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to rebuild statistics data: {str(e)}")


@router.post("/refresh", summary="Refresh Statistics Data", description="Re-collect and refresh statistics data")
async def refresh_statistics():
    """Refresh statistics data
    
    Returns:
        Result of the refresh operation
    """
    try:
        # Reload statistics data
        statistics_manager.load_statistics()
        
        summary = statistics_manager.get_summary()
        
        logger.info("Successfully refreshed statistics data")
        return {
            "success": True,
            "message": "Statistics data refresh successful",
            "summary": summary,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Failed to refresh statistics data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh statistics data: {str(e)}")


# Export router
__all__ = ["router"] 