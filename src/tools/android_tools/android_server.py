"""
Android MCP Server - Android Device Interaction Tools

Provides tools for direct Android device interaction:
- Click, long press, swipe, drag
- Text input and key operations
- Notification shade access, waiting
- Get UI interactive elements tree with optional screenshots (PNG bytes)
"""

import argparse
import time
from src.tools.base import BaseMCPServer
from src.tools.android_tools.mobile import Mobile, MobileState
from src.core.statistics import mcp_author
# FastMCP 2.x recommends using Image from utilities.types to avoid deprecation warnings
from fastmcp.utilities.types import Image


@mcp_author("Racks", email="zhuoqr@2345.com", department="TestingDepartment", project=["TD"])
class AndroidMCPServer(BaseMCPServer):
    """Android MCP Server - Android Device Interaction Tools

    Provides a complete toolkit for direct Android device interaction, including:
    1. Device click operations (Click, Long Click)
    2. Device swipe operations (Swipe, Drag)
    3. Text input operations (Type)
    4. Device state retrieval (State with optional screenshot)
    5. Device key operations (Press)
    6. Notification operations (Notification)
    7. Wait operations (Wait)

    Supports physical devices and emulators, communicates via ADB.
    """

    def __init__(self, name: str = "LiteMCP-Android", use_emulator: bool = False):
        """Initialize Android MCP server
        
        Args:
            name: server name
            use_emulator: whether to use emulator (default uses physical device)
        """
        super().__init__(name)
        
        # Initialize Android device connection (uiautomator2)
        self.mobile = Mobile(device='emulator-5554' if use_emulator else None)
        self.device = self.mobile.get_device()
        
        self.logger.info(f"Android MCP Server initialized - Device: {'emulator-5554' if use_emulator else 'default'}")

    def _register_tools(self):
        """Register Android device interaction tools"""

        @self.mcp.tool()
        def click_tool(x: int, y: int) -> str:
            """
            Click tool - execute click operation at specified coordinates
            
            Args:
                x: X coordinate
                y: Y coordinate
                
            Returns:
                operation result description
            """
            try:
                self.device.click(x, y)
                return f"Successfully clicked coordinates ({x}, {y})"
            except Exception as e:
                return f"Click operation error: {str(e)}"

        @self.mcp.tool()
        def long_click_tool(x: int, y: int) -> str:
            """
            Long click tool - execute long press operation at specified coordinates
            
            Args:
                x: X coordinate
                y: Y coordinate
                
            Returns:
                operation result description
            """
            try:
                # Use uiautomator2: long_click(x, y, duration=1.0)
                self.device.long_click(x, y, 1.0)
                return f"Successfully long pressed coordinates ({x}, {y})"
            except Exception as e:
                return f"Long press operation error: {str(e)}"

        @self.mcp.tool()
        def swipe_tool(x1: int, y1: int, x2: int, y2: int) -> str:
            """
            Swipe tool - swipe from start coordinates to end coordinates
            
            Args:
                x1: start X coordinate
                y1: start Y coordinate
                x2: end X coordinate
                y2: end Y coordinate
                
            Returns:
                operation result description
            """
            try:
                # Use uiautomator2: swipe(x1, y1, x2, y2, duration=0.2)
                self.device.swipe(x1, y1, x2, y2, 0.2)
                return f"Successfully swiped from ({x1}, {y1}) to ({x2}, {y2})"
            except Exception as e:
                return f"Swipe operation error: {str(e)}"

        @self.mcp.tool()
        def drag_tool(x1: int, y1: int, x2: int, y2: int) -> str:
            """
            Drag tool - drag from start position to end position
            
            Args:
                x1: start X coordinate
                y1: start Y coordinate
                x2: end X coordinate
                y2: end Y coordinate
                
            Returns:
                operation result description
            """
            try:
                # Use uiautomator2: drag(x1, y1, x2, y2, duration=0.5)
                self.device.drag(x1, y1, x2, y2, 0.5)
                return f"Successfully dragged from ({x1}, {y1}) to ({x2}, {y2})"
            except Exception as e:
                return f"Drag operation error: {str(e)}"

        @self.mcp.tool()
        def type_tool(text: str, x: int = 0, y: int = 0, clear: bool = False) -> str:
            """
            Input tool - input text at specified position
            
            Args:
                text: text to input
                x: X coordinate (optional, for positioning)
                y: Y coordinate (optional, for positioning)
                clear: whether to clear existing text first
                
            Returns:
                operation result description
            """
            try:
                # Enable fast input method (provided by uiautomator2)
                try:
                    self.device.set_fastinput_ime(True)
                except Exception:
                    pass
                
                # If positioning click is needed first
                if x > 0 and y > 0:
                    self.device.click(x, y)
                
                # Send text (uiautomator2)
                if clear:
                    # Try to clear current focused edit field
                    try:
                        self.device.clear_text()
                    except Exception:
                        pass
                self.device.send_keys(text)
                return f"Successfully input text: \"{text}\" at coordinates ({x}, {y})"
            except Exception as e:
                return f"Text input error: {str(e)}"

        # Disable automatic output mode structured serialization to avoid Image object serialization errors
        @self.mcp.tool(output_schema=None)
        def state_tool(use_vision: bool = False) -> list:
            """
            State tool - get device current state
            
            Args:
                use_vision: whether to include visual screenshot
                
            Returns:
                device state information list, containing UI tree structure and optional screenshot
            """
            try:
                mobile_state: MobileState = self.mobile.get_state(use_vision=use_vision)
                result = [mobile_state.tree_state.to_string()]

                if use_vision and mobile_state.screenshot:
                    # Return FastMCP Image type; can be passed through directly after disabling automatic serialization in output mode
                    result.append(Image(data=mobile_state.screenshot, format='PNG'))

                return result
            except Exception as e:
                return [f"Failed to get device state: {str(e)}"]

        @self.mcp.tool()
        def press_tool(button: str) -> str:
            """
            Key tool - press specific key on device
            
            Args:
                button: key name (home, back, menu, power, volume_up, volume_down, enter, delete, space)
                
            Returns:
                operation result description
            """
            try:
                # uiautomator2: press('home'|'back'|...)
                self.device.press(button)
                return f"Successfully pressed key: {button}"
            except Exception as e:
                return f"Key operation error: {str(e)}"

        @self.mcp.tool()
        def notification_tool() -> str:
            """
            Notification tool - access device notification shade
            
            Returns:
                operation result description
            """
            try:
                self.device.open_notification()
                return "Successfully opened notification shade"
            except Exception as e:
                return f"Notification operation error: {str(e)}"

        @self.mcp.tool()
        def wait_tool(duration: int) -> str:
            """
            Wait tool - wait for specified time
            
            Args:
                duration: wait time (seconds)
                
            Returns:
                operation result description
            """
            try:
                time.sleep(duration)
                return f"Successfully waited {duration} seconds"
            except Exception as e:
                return f"Wait operation error: {str(e)}"

        @self.mcp.tool()
        def device_info_tool() -> str:
            """
            Device info tool - get connected Android device information
            
            Returns:
                device information description
            """
            try:
                import subprocess
                
                # Get device list
                cmd = ["adb", "devices"]
                # Windows default console encoding is GBK, using text=True directly may cause decoding errors
                # Use byte capture with UTF-8 priority and ignore errors for robustness
                result = subprocess.run(cmd, capture_output=True)
                
                if result.returncode == 0:
                    stdout = result.stdout.decode('utf-8', errors='ignore') if isinstance(result.stdout, (bytes, bytearray)) else str(result.stdout)
                    devices = stdout.strip().split('\n')[1:]  # Skip header line
                    device_list = [line for line in devices if line.strip() and 'device' in line]
                    
                    if device_list:
                        return f"Connected devices: {len(device_list)} devices\n" + "\n".join(device_list)
                    else:
                        return "No connected Android devices detected"
                else:
                    stderr = result.stderr.decode('utf-8', errors='ignore') if isinstance(result.stderr, (bytes, bytearray)) else str(result.stderr)
                    return f"Failed to get device information: {stderr}"
            except Exception as e:
                return f"Device information retrieval error: {str(e)}"


# Create global instance for framework use
android_server = AndroidMCPServer()

if __name__ == "__main__":
    # Support command line arguments
    parser = argparse.ArgumentParser(description="Android MCP Server")
    parser.add_argument('--emulator', action='store_true', help='Use emulator')
    args = parser.parse_args()
    
    # Create server instance based on arguments
    if args.emulator:
        android_server = AndroidMCPServer(use_emulator=True)
    
    # Run server
    android_server.run()
