"""
LiteMCP Example Server - Complete Development Example

This is a complete MCP server example demonstrating how to quickly develop tools using BaseMCPServer.
Testers can copy this file as a starting point for new tools.
"""

from src.tools.base import BaseMCPServer


class ExampleMCPServer(BaseMCPServer):
    """Example MCP Server - Complete Development Example

    This example demonstrates:
    1. How to inherit from BaseMCPServer
    2. How to register multiple tools
    3. How to handle parameters and errors
    4. How to write docstrings
    5. New simplified author information usage

    When developing new tools, copy this file and modify:
    1. Class name: ExampleMCPServer → YourToolMCPServer
    2. Server name: LiteMCP-Example → LiteMCP-YourTool
    3. Tool functions: add_numbers, multiply_numbers → your_functions
    """

    def __init__(self, name: str = "LiteMCP-Example"):
        # Call parent class initialization to automatically get all transport mode support
        super().__init__(name)

    def _register_tools(self):
        """Register tools - Demonstrating different author information usage methods"""

        @self.mcp.tool()
        def add_numbers(a: float, b: float) -> str:
            """
            Number addition tool - Inherits server author information

            Args:
                a: First number
                b: Second number

            Returns:
                String representation of the calculation result
            """
            try:
                result = a + b
                return f"{a} + {b} = {result}"
            except Exception as e:
                return f"Calculation error: {str(e)}"

        @self.mcp.tool()
        def multiply_numbers(a: float, b: float) -> str:
            """
            Number multiplication tool - Uses @mcp_author decorator (new method)

            Args:
                a: First number
                b: Second number

            Returns:
                String representation of the calculation result
            """
            try:
                result = a * b
                return f"{a} × {b} = {result}"
            except Exception as e:
                return f"Calculation error: {str(e)}"

        @self.mcp.tool()
        def divide_numbers(a: float, b: float) -> str:
            """
            Number division tool - Uses @mcp_author decorator

            Args:
                a: Dividend
                b: Divisor

            Returns:
                String representation of the calculation result
            """
            try:
                if b == 0:
                    return "Error: Divisor cannot be zero"
                result = a / b
                return f"{a} ÷ {b} = {result}"
            except Exception as e:
                return f"Calculation error: {str(e)}"

        @self.mcp.tool()
        def subtract_numbers(a: float, b: float) -> str:
            """
            Number subtraction tool - Uses @mcp_author decorator with partial override

            Args:
                a: Minuend
                b: Subtrahend

            Returns:
                String representation of the calculation result
            """
            try:
                result = a - b
                return f"{a} - {b} = {result}"
            except Exception as e:
                return f"Calculation error: {str(e)}"

# Create global instance for framework use
example_server = ExampleMCPServer()

if __name__ == "__main__":
    example_server.run()
