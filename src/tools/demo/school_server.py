from src.tools.base import BaseMCPServer


class SchoolMCPServer(BaseMCPServer):
    """Example MCP Server - Complete Development Example

    This example demonstrates:
    1. How to inherit from BaseMCPServer
    2. How to register multiple tools
    3. How to handle parameters and errors
    4. How to write docstrings

    When developing new tools, copy this file and modify:
    1. Class name: ExampleMCPServer → YourToolMCPServer
    2. Server name: LiteMCP-Example → LiteMCP-YourTool
    3. Tool functions: add_numbers, multiply_numbers → your_functions
    """

    def __init__(self, name: str = "LiteMCP-School"):
        # Call parent class initialization to automatically get all transport mode support
        super().__init__(name)

    def _register_tools(self):
        """Register tools - Example showing how to implement multiple tools"""

        @self.mcp.tool()
        def school_name() -> str:
            """
            Get school name

            Returns:
                School name
            """
            return "LiteMCP School"

        @self.mcp.tool()
        def students_number() -> int:
            """
            Get number of students

            Returns:
                Number of students
            """
            return 20

        @self.mcp.tool()
        def teachers_number() -> int:
            """
            Get number of teachers

            Returns:
                Number of teachers
            """
            return 5

        @self.mcp.tool()
        def opening_date(semester: str) -> str:
            """
            Get school opening date

            Args:
                semester: Semester to query, options: 'spring' (first half) or 'autumn' (second half)

            Returns:
                String representation of the result
            """
            semester = semester.lower()
            if semester == "spring":
                return "2024-02-20"
            else:
                return "2024-09-01"


# Create global instance for framework use
school_server = SchoolMCPServer()

# If running this file directly, start the server
if __name__ == "__main__":
    # Supports all transport modes:
    # school_server.run()       # STDIO mode
    # school_server.run_http()  # HTTP mode
    # school_server.run_sse()   # SSE mode
    school_server.run()
