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
    "fastbot": {
        "description": "Fastbot Android stability testing server, supporting device management, APK installation, stability testing, and log analysis features",
        "module": "src.tools.monkey_testing.fastbot_server",
        "class": "FastbotMCPServer"
    },
    "android": {
        "description": "Android device interaction MCP server providing mobile device control tools",
        "module": "src.tools.android_tools.android_server",
        "class": "AndroidMCPServer"
    },
    "check": {
        "description": "Common detection tools",
        "module": "src.tools.common_tools.check_server",
        "class": "CheckMCPServer"
    },
    "mouse_tools": {
        "description": "Mouse interaction MCP server providing mouse control tools",
        "module": "src.tools.mouse_tools.mouse_server",
        "class": "MouseMCPServer"
    },
}

# Export all server classes (optional, for direct import)
__all__ = ["AVAILABLE_SERVERS"]
