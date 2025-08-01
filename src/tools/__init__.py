
"""
LiteMCP Toolkit - Server Registry Center

Dynamically registers all available MCP servers, supporting auto-discovery and configuration generation.
"""

# Registry of available MCP servers
AVAILABLE_SERVERS = {
    "example": {
        "description": "Example MCP server demonstrating basic functionality",
        "module": "src.tools.demo.example_server",
        "class": "ExampleMCPServer"
    },
    "school": {
        "description": "School management MCP server providing student and course management features",
        "module": "src.tools.demo.school_server",
        "class": "SchoolMCPServer"
    },
}

# Export all server classes (optional, for direct import)
__all__ = ["AVAILABLE_SERVERS"]
