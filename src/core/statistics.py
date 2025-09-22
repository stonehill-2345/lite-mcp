"""
LiteMCP Statistics Module - Statistics Report System

Provides decorator system for collecting author information and statistics data, supporting statistics report generation.
"""
import json
import inspect
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from src.core.logger import get_logger, LoggerMixin
from src.core.utils import get_project_root


@dataclass
class AuthorInfo:
    """Author information"""
    name: str
    email: Optional[str] = None
    department: Optional[str] = None
    project: Optional[List[str]] = None
    create_time: Optional[str] = None

    def __post_init__(self):
        if self.create_time is None:
            self.create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Ensure project is in list format
        if self.project is not None and not isinstance(self.project, list):
            self.project = [self.project]


@dataclass
class ToolInfo:
    """Tool information"""
    name: str
    description: str
    function_name: str
    module: str
    params: List[str]
    return_type: str
    create_time: str
    author: AuthorInfo

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "function_name": self.function_name,
            "module": self.module,
            "params": self.params,
            "return_type": self.return_type,
            "create_time": self.create_time,
            "author": asdict(self.author)
        }


@dataclass
class ServerInfo:
    """Server information"""
    name: str
    class_name: str
    module: str
    description: str
    tools: List[ToolInfo]
    author: AuthorInfo
    create_time: str
    last_update: str

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "class_name": self.class_name,
            "module": self.module,
            "description": self.description,
            "tools": [tool.to_dict() for tool in self.tools],
            "author": asdict(self.author),
            "create_time": self.create_time,
            "last_update": self.last_update,
            "tool_count": len(self.tools)
        }


class StatisticsManager(LoggerMixin):
    """Statistics Manager"""
    
    def __init__(self):
        super().__init__()
        self.project_root = get_project_root()
        self.stats_file = self.project_root / "runtime" / "statistics.json"
        self.servers: Dict[str, ServerInfo] = {}
        self.tools: Dict[str, ToolInfo] = {}
        # Initialize logger
        self._logger = get_logger("litemcp.statistics", log_file="statistics.log")
        self.load_statistics()
    
    def load_statistics(self):
        """Load statistics data"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Reconstruct server data
                for server_name, server_data in data.get('servers', {}).items():
                    # Rebuild author information
                    author_data = server_data.get('author', {})
                    author = AuthorInfo(**author_data)
                    
                    # Rebuild tool information
                    tools = []
                    for tool_data in server_data.get('tools', []):
                        tool_author_data = tool_data.get('author', {})
                        tool_author = AuthorInfo(**tool_author_data)
                        tool = ToolInfo(
                            name=tool_data['name'],
                            description=tool_data['description'],
                            function_name=tool_data['function_name'],
                            module=tool_data['module'],
                            params=tool_data['params'],
                            return_type=tool_data['return_type'],
                            create_time=tool_data['create_time'],
                            author=tool_author
                        )
                        tools.append(tool)
                        self.tools[tool.name] = tool
                    
                    # Rebuild server information
                    server = ServerInfo(
                        name=server_data['name'],
                        class_name=server_data['class_name'],
                        module=server_data['module'],
                        description=server_data['description'],
                        tools=tools,
                        author=author,
                        create_time=server_data['create_time'],
                        last_update=server_data['last_update']
                    )
                    self.servers[server_name] = server
                    
                self._logger.info(f"Statistics data loading completed: {len(self.servers)} servers, {len(self.tools)} tools")
                
            except Exception as e:
                self._logger.error(f"Failed to load statistics data: {e}")
                self.servers = {}
                self.tools = {}
    
    def save_statistics(self):
        """Save statistics data"""
        try:
            # Ensure directory exists
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "servers": {name: server.to_dict() for name, server in self.servers.items()},
                "summary": self.get_summary(),
                "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self._logger.info(f"Statistics data saved successfully: {self.stats_file}")
            
        except Exception as e:
            self._logger.error(f"Failed to save statistics data: {e}")
    
    def register_server(self, name: str, class_name: str, module: str, description: str, author: AuthorInfo):
        """Register server
        
        Args:
            name: Server name
            class_name: Server class name
            module: Module name
            description: Server description
            author: Author information
        
        Note:
            This method only updates data in memory and does not automatically save to file.
            You need to call save_statistics() method to save to file.
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if name in self.servers:
            # Update existing server
            self.servers[name].description = description
            self.servers[name].author = author
            self.servers[name].last_update = current_time
            self._logger.info(f"Updated server statistics: {name}")
        else:
            # Create new server
            server = ServerInfo(
                name=name,
                class_name=class_name,
                module=module,
                description=description,
                tools=[],
                author=author,
                create_time=current_time,
                last_update=current_time
            )
            self.servers[name] = server
            self._logger.info(f"Registered server statistics: {name}")
        
        # Don't auto-save, let caller explicitly control
    
    def clear_outdated_data(self, active_servers: set = None, active_tools: set = None):
        """Clear outdated data
        
        Args:
            active_servers: Set of currently active server names, if provided, clears servers not in this set
            active_tools: Set of currently active tool names, if provided, clears tools not in this set
        """
        if active_servers is not None:
            # Clear servers that no longer exist
            outdated_servers = set(self.servers.keys()) - active_servers
            for server_name in outdated_servers:
                del self.servers[server_name]
                self._logger.info(f"Cleared outdated server: {server_name}")
        
        if active_tools is not None:
            # Clear tools that no longer exist
            outdated_tools = set(self.tools.keys()) - active_tools
            for tool_name in outdated_tools:
                del self.tools[tool_name]
                self._logger.info(f"Cleared outdated tool: {tool_name}")
            
            # Clear outdated tools in servers
            for server in self.servers.values():
                server.tools = [tool for tool in server.tools if tool.name in active_tools]
    
    def rebuild_statistics(self):
        """Rebuild statistics data
        
        Clear all statistics data and start collecting again.
        This is a thorough cleanup method for handling data inconsistency issues.
        """
        self.servers.clear()
        self.tools.clear()
        self._logger.info("Cleared all statistics data, ready to re-collect")
    
    def register_server_and_save(self, name: str, class_name: str, module: str, description: str, author: AuthorInfo):
        """Register server and save to file immediately
        
        This is a convenience method for register_server + save_statistics
        """
        self.register_server(name, class_name, module, description, author)
        self.save_statistics()
    
    def register_tool(self, server_name: str, tool_name: str, description: str, function_name: str, 
                     module: str, params: List[str], return_type: str, author: AuthorInfo):
        """Register tool
        
        Args:
            server_name: Server name
            tool_name: Tool name
            description: Tool description
            function_name: Function name
            module: Module name
            params: Parameter list
            return_type: Return type
            author: Author information
        
        Note:
            This method only updates data in memory and does not automatically save to file.
            You need to call save_statistics() method to save to file.
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        tool = ToolInfo(
            name=tool_name,
            description=description,
            function_name=function_name,
            module=module,
            params=params,
            return_type=return_type,
            create_time=current_time,
            author=author
        )
        
        # Add to global tools dictionary
        self.tools[tool_name] = tool
        
        # Add to server's tools list
        if server_name in self.servers:
            # Check if tool with same name already exists
            existing_tool_index = None
            for i, existing_tool in enumerate(self.servers[server_name].tools):
                if existing_tool.name == tool_name:
                    existing_tool_index = i
                    break
            
            if existing_tool_index is not None:
                # Update existing tool
                self.servers[server_name].tools[existing_tool_index] = tool
                self._logger.info(f"Updated tool statistics: {server_name}.{tool_name}")
            else:
                # Add new tool
                self.servers[server_name].tools.append(tool)
                self._logger.info(f"Registered tool statistics: {server_name}.{tool_name}")
            
            # Update server's last update time
            self.servers[server_name].last_update = current_time
        
        # Don't auto-save, let caller explicitly control
    
    def register_tool_and_save(self, server_name: str, tool_name: str, description: str, function_name: str, 
                              module: str, params: List[str], return_type: str, author: AuthorInfo):
        """Register tool and save to file immediately
        
        This is a convenience method for register_tool + save_statistics
        """
        self.register_tool(server_name, tool_name, description, function_name, module, params, return_type, author)
        self.save_statistics()

    @staticmethod
    def _init_stats_dict(name: str) -> Dict:
        """Common method to initialize statistics dictionary"""
        return {
            "name": name,
            "server_count": 0,
            "tool_count": 0,
            "author_count": 0,
            "authors": set()
        }

    @staticmethod
    def _init_author_stats(author: AuthorInfo) -> Dict:
        """Initialize author statistics dictionary"""
        return {
            "name": author.name,
            "email": author.email,
            "department": author.department,
            "server_count": 0,
            "tool_count": 0
        }
    
    def _update_stats_for_author(self, author: AuthorInfo, author_stats: Dict, 
                                department_stats: Dict, project_stats: Dict, 
                                is_server: bool = True):
        """Update author-related statistics
        
        Args:
            author: Author information
            author_stats: Author statistics dictionary
            department_stats: Department statistics dictionary
            project_stats: Project statistics dictionary
            is_server: Whether it's server statistics (True) or tool statistics (False)
        """
        author_name = author.name
        
        # Update author statistics
        if author_name not in author_stats:
            author_stats[author_name] = self._init_author_stats(author)
        
        if is_server:
            author_stats[author_name]["server_count"] += 1
        else:
            author_stats[author_name]["tool_count"] += 1
        
        # Update department statistics
        dept = author.department or "Unknown Department"
        if dept not in department_stats:
            department_stats[dept] = self._init_stats_dict(dept)
        
        if is_server:
            department_stats[dept]["server_count"] += 1
        else:
            department_stats[dept]["tool_count"] += 1
        department_stats[dept]["authors"].add(author_name)
        
        # Update project statistics (support multiple projects)
        projects = author.project or ["Unknown Project"]
        for proj in projects:
            if proj not in project_stats:
                project_stats[proj] = self._init_stats_dict(proj)
            
            if is_server:
                project_stats[proj]["server_count"] += 1
            else:
                project_stats[proj]["tool_count"] += 1
            project_stats[proj]["authors"].add(author_name)
    
    def get_summary(self) -> Dict:
        """Get statistics summary"""
        author_stats = {}
        department_stats = {}
        project_stats = {}
        
        # Count servers
        for server in self.servers.values():
            self._update_stats_for_author(
                server.author, author_stats, department_stats, project_stats, is_server=True
            )
            
            # Count tools
            for tool in server.tools:
                self._update_stats_for_author(
                    tool.author, author_stats, department_stats, project_stats, is_server=False
                )
        
        # Calculate final author counts and convert sets to lists
        for dept in department_stats.values():
            dept["author_count"] = len(dept["authors"])
            dept["authors"] = list(dept["authors"])
        
        for proj in project_stats.values():
            proj["author_count"] = len(proj["authors"])
            proj["authors"] = list(proj["authors"])
        
        # Sort by contribution
        sorted_authors = sorted(
            author_stats.values(), 
            key=lambda x: x["server_count"] + x["tool_count"], 
            reverse=True
        )
        
        sorted_departments = sorted(
            department_stats.values(),
            key=lambda x: x["server_count"] + x["tool_count"],
            reverse=True
        )
        
        sorted_projects = sorted(
            project_stats.values(),
            key=lambda x: x["server_count"] + x["tool_count"],
            reverse=True
        )
        
        return {
            "total_servers": len(self.servers),
            "total_tools": len(self.tools),
            "total_authors": len(author_stats),
            "total_departments": len(department_stats),
            "total_projects": len(project_stats),
            "top_authors": sorted_authors[:10],
            "departments": sorted_departments,
            "projects": sorted_projects,
            "author_summary": [
                {
                    "name": author["name"],
                    "sever_count": author["server_count"],
                    "tool_count": author["tool_count"]
                }
                for author in sorted_authors
            ]
        }
    
    def get_statistics(self) -> Dict:
        """Get complete statistics information"""
        return {
            "servers": {name: server.to_dict() for name, server in self.servers.items()},
            "tools": {name: tool.to_dict() for name, tool in self.tools.items()},
            "summary": self.get_summary(),
            "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_server_statistics(self) -> List[Dict]:
        """Get server statistics information"""
        return [server.to_dict() for server in self.servers.values()]
    
    def get_tool_statistics(self) -> List[Dict]:
        """Get tool statistics information"""
        return [tool.to_dict() for tool in self.tools.values()]
    
    def get_author_statistics(self) -> List[Dict]:
        """Get author statistics information"""
        author_stats = {}
        
        for server in self.servers.values():
            author_name = server.author.name
            if author_name not in author_stats:
                author_stats[author_name] = {
                    "name": author_name,
                    "email": server.author.email,
                    "department": server.author.department,
                    "servers": [],
                    "tools": [],
                    "server_count": 0,
                    "tool_count": 0
                }
            
            author_stats[author_name]["servers"].append(server.name)
            author_stats[author_name]["server_count"] += 1
            
            for tool in server.tools:
                tool_author_name = tool.author.name
                if tool_author_name not in author_stats:
                    author_stats[tool_author_name] = {
                        "name": tool_author_name,
                        "email": tool.author.email,
                        "department": tool.author.department,
                        "servers": [],
                        "tools": [],
                        "server_count": 0,
                        "tool_count": 0
                    }
                
                author_stats[tool_author_name]["tools"].append(tool.name)
                author_stats[tool_author_name]["tool_count"] += 1
        
        return list(author_stats.values())


# Global statistics manager instance
statistics_manager = StatisticsManager()


def mcp_author(name: str, email: Optional[str] = None, department: Optional[str] = None, project: Optional[List[str]] = None):
    """MCP Author Decorator
    
    Unified author information decorator that can be used for both MCP server classes and MCP tool functions.
    
    Args:
        name: Author name (required)
        email: Email address (optional)
        department: Department affiliation (optional)
        project: Project list (optional), supports string or string list
    
    Example:
        # For server classes
        @mcp_author("John Doe")  # Simplest usage
        @mcp_author("John Doe", "johndoe@example.com")  # With email
        @mcp_author("John Doe", department="Testing")  # With department
        @mcp_author("John Doe", project=["TD"])  # With single project
        @mcp_author("John Doe", project=["TD", "ProjectA"])  # With multiple projects
        @mcp_author("John Doe", "johndoe@example.com", "Testing", ["TD", "ProjectA"])  # Complete information
        class MyMCPServer(BaseMCPServer):
            pass
            
        # For tool functions
        @self.mcp.tool()
        @mcp_author("Jane Smith", project=["ProjectA", "ProjectB"])
        def my_tool(param: str) -> str:
            return f"Processed result: {param}"
    """
    def decorator(cls_or_func):
        author_info = AuthorInfo(
            name=name,
            email=email,
            department=department,
            project=project
        )
        
        # Store author information in class or function attributes
        cls_or_func._mcp_author_info = author_info
        
        return cls_or_func
    
    return decorator


def extract_function_info(func) -> Dict:
    """Extract function information"""
    sig = inspect.signature(func)
    params = []
    return_type = "Any"
    
    for param_name, param in sig.parameters.items():
        param_info = param_name
        if param.annotation != inspect.Parameter.empty:
            param_info += f": {param.annotation.__name__ if hasattr(param.annotation, '__name__') else str(param.annotation)}"
        params.append(param_info)
    
    if sig.return_annotation != inspect.Signature.empty:
        return_type = sig.return_annotation.__name__ if hasattr(sig.return_annotation, '__name__') else str(sig.return_annotation)
    
    return {
        "params": params,
        "return_type": return_type,
        "description": func.__doc__.strip() if func.__doc__ else "No description"
    }


def collect_all_statistics(server_instances: list):
    """Re-collect statistics information for all servers
    
    Args:
        server_instances: List of all active server instances
    
    Note:
        This function will clear outdated data and only keep statistics information for currently active servers and tools.
        This is the recommended method for handling data inconsistency issues.
    """
    try:
        # Collect currently active servers and tools
        active_servers = set()
        active_tools = set()
        
        for server_instance in server_instances:
            active_servers.add(server_instance.name)
            
            # Collect tool information
            if hasattr(server_instance, 'mcp') and hasattr(server_instance.mcp, '_tool_manager') and hasattr(server_instance.mcp._tool_manager, '_tools'):
                tools_dict = server_instance.mcp._tool_manager._tools
                if tools_dict:
                    active_tools.update(tools_dict.keys())
        
        # Clear outdated data
        statistics_manager.clear_outdated_data(active_servers, active_tools)
        
        # Re-collect statistics information for all servers
        for server_instance in server_instances:
            collect_server_statistics(server_instance)
        
        statistics_manager._logger.info(f"Re-collection of statistics completed: {len(active_servers)} servers, {len(active_tools)} tools")
        
    except Exception as e:
        statistics_manager._logger.error(f"Failed to re-collect statistics: {e}")


def rebuild_all_statistics():
    """Rebuild all statistics data
    
    Clear existing data and re-collect statistics information for all active servers.
    This is the ultimate method for handling severe data inconsistency issues.
    """
    try:
        # Clear all data
        statistics_manager.rebuild_statistics()
        
        # Re-collect statistics information for active servers
        from src.tools import AVAILABLE_SERVERS
        import importlib
        
        server_instances = []
        for server_name, server_config in AVAILABLE_SERVERS.items():
            try:
                # Dynamically import module
                module = importlib.import_module(server_config['module'])
                # Get server class
                server_class = getattr(module, server_config['class'])
                # Create server instance
                server_instance = server_class()
                server_instances.append(server_instance)
                statistics_manager._logger.info(f"Successfully loaded server: {server_name}")
            except Exception as e:
                statistics_manager._logger.warning(f"Unable to load server {server_name}: {e}")
        
        # Collect statistics information
        if server_instances:
            collect_all_statistics(server_instances)
        else:
            statistics_manager._logger.warning("No available server instances")
        
    except Exception as e:
        statistics_manager._logger.error(f"Failed to rebuild statistics data: {e}")


# Modified tool author information collection logic
def collect_server_statistics(server_instance):
    """Collect server statistics information
    
    Args:
        server_instance: Server instance
    
    Note:
        This function will collect server and tool statistics information and save to file at the end.
        This is the recommended way for batch collection of statistics information.
        
        Unified author information management mechanism:
        1. @mcp_author information on server class serves as default author information
        2. Tools can use @mcp_author decorator to override specific fields
        3. Unified use of @mcp_author decorator to simplify development
    """
    try:
        server_class = server_instance.__class__
        module_name = server_class.__module__
        
        # Get server author information
        server_author = getattr(server_class, '_mcp_author_info', None)
        if server_author is None:
            # If no decorator, use default author information
            server_author = AuthorInfo(name="Unknown Author")
        
        # Get server description
        server_description = server_class.__doc__.strip() if server_class.__doc__ else "No description"
        
        # Register server
        statistics_manager.register_server(
            name=server_instance.name,
            class_name=server_class.__name__,
            module=module_name,
            description=server_description,
            author=server_author
        )
        
        # Collect tool information
        if hasattr(server_instance, 'mcp') and hasattr(server_instance.mcp, '_tool_manager') and hasattr(server_instance.mcp._tool_manager, '_tools'):
            tools_dict = server_instance.mcp._tool_manager._tools
            if tools_dict:
                for tool_name, tool_obj in tools_dict.items():
                    # Get actual function object
                    tool_func = tool_obj.fn if hasattr(tool_obj, 'fn') else tool_obj
                    
                    # Optimized author information retrieval logic
                    tool_author = _get_tool_author_info(tool_func, server_author)
                    
                    # Extract function information, use tool object description as priority
                    func_info = extract_function_info(tool_func)
                    if hasattr(tool_obj, 'description') and tool_obj.description:
                        func_info["description"] = tool_obj.description
                    
                    # Register tool
                    statistics_manager.register_tool(
                        server_name=server_instance.name,
                        tool_name=tool_name,
                        description=func_info["description"],
                        function_name=tool_func.__name__,
                        module=module_name,
                        params=func_info["params"],
                        return_type=func_info["return_type"],
                        author=tool_author
                    )
        
        # Save statistics data uniformly
        statistics_manager.save_statistics()
        
    except Exception as e:
        statistics_manager._logger.error(f"Failed to collect server statistics: {e}")


def _get_tool_author_info(tool_func, server_author):
    """Get tool author information
    
    Priority:
    1. @mcp_author decorator information (tool level)
    2. Server author information (inheritance)
    
    Args:
        tool_func: Tool function object
        server_author: Server author information
        
    Returns:
        AuthorInfo: Tool author information
    """
    # Check @mcp_author decorator
    tool_author = getattr(tool_func, '_mcp_author_info', None)
    if tool_author is not None:
        return tool_author
    
    # If tool has no author information, use server author information
    return server_author


# Export main classes and functions
__all__ = [
    "AuthorInfo",
    "ToolInfo", 
    "ServerInfo",
    "StatisticsManager",
    "statistics_manager",
    "mcp_author",
    "collect_server_statistics",
    "collect_all_statistics",
    "rebuild_all_statistics"
] 