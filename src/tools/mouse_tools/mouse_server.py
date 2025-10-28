"""
Mouse MCP Server - Provide common operations of the mouse
"""
from src.tools.base import BaseMCPServer
from src.core.statistics import mcp_author
import pyautogui
import time


@mcp_author("liefeng", email="lhyhr@vip.qq.com", department="TestingDepartment", project=["TD"])
class MouseMCPServer(BaseMCPServer):
    """
    Provide common operations of the mouse:
    1. Mouse move operations.
    2. Mouse click operations.
    3. Mouse scroll operations.
    4. Mouse drag operations.
    5. Mouse press operations.
    6. Mouse release operations.
    7. Mouse shortcut key and hotkey operations.

    Supports Windows devices.
    """

    def __init__(self, name: str = "LiteMCP-Mouse"):
        """Initialize Mouse MCP server"""
        super().__init__(name)

    def _register_tools(self):
        """Register tools - supports multiple MCP tools"""
        @self.mcp.tool()
        async def move_mouse(x: int, y: int):
            """Move the mouse to the specified coordinates

            Args:
                x: The x coordinate to move the mouse to
                y: The y coordinate to move the mouse to

            Returns:
                True if the mouse has been moved, False otherwise
            """
            pyautogui.moveTo(x, y)
        
        @self.mcp.tool()
        async def click_mouse(x: int, y: int, button: str = "left"):
            """Click the mouse at the specified coordinates

            Args:
                x: The x coordinate to click the mouse at
                y: The y coordinate to click the mouse at
                button: The button to click the mouse with (left, right, middle, double_left)
            """
            clicks = 1
            actual_button = button.lower()
            if actual_button == "double_left":
                clicks = 2
                actual_button = "left"
            pyautogui.click(x, y, clicks=clicks, interval=0.1, button=actual_button)
            
        @self.mcp.tool()
        async def mouse_press(x: int, y: int, button: str = "left"):
            """Press the mouse at the specified coordinates
            Args:
                x: The x coordinate to press the mouse at
                y: The y coordinate to press the mouse at
                button: The button to press the mouse with (left, right, middle)
            """
            pyautogui.mouseDown(x, y, button=button.lower())

        @self.mcp.tool()
        async def mouse_release(x: int, y: int, button: str = "left"):
            """Release the mouse at the specified coordinates
            Args:
                x: The x coordinate to release the mouse at
                y: The y coordinate to release the mouse at
                button: The button to release the mouse with (left, right, middle)
            """
            pyautogui.mouseUp(x, y, button=button.lower())

        @self.mcp.tool()
        async def mouse_scroll(x: int, y: int, scroll_amount: int = 30, scroll_type: str = "up"):
            """Scroll the mouse at the specified coordinates
            Args:
                x: The x coordinate to scroll the mouse at
                y: The y coordinate to scroll the mouse at
                scroll_amount: The amount to scroll
                scroll_type: The type of scroll (up, down, left, right)
            """
            if scroll_type.lower() == "up":
                scroll=pyautogui.vscroll
            elif scroll_type.lower() == "down":
                scroll_amount=-scroll_amount
                scroll=pyautogui.vscroll
            elif scroll_type.lower() == "left":
                scroll=pyautogui.hscroll
            elif scroll_type.lower() == "right":
                scroll_amount=-scroll_amount
                scroll=pyautogui.hscroll
            else:
                raise ValueError(f"Invalid scroll type: {scroll_type}")
            
            scroll(scroll_amount, x, y)

        @self.mcp.tool()
        async def press_key(key: str):
            """Press the specified key
            Args:
                key: The key to press，combination key like "ctrl+c"
            """
            keys = [x for x in key.split("+") if x]
            if len(keys) == 1:
                pyautogui.press(key)
            else:
                pyautogui.hotkey(*keys)        

        @self.mcp.tool()
        async def mouse_drag(start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5):
            """Drag the mouse from the source coordinates to the target coordinates
            Args:
                start_x: The x coordinate to drag the mouse from
                start_y: The y coordinate to drag the mouse from
                end_x: The x coordinate to drag the mouse to
                end_y: The y coordinate to drag the mouse to                
                duration: The duration of the drag in seconds
            """
            try:
                pyautogui.moveTo(start_x, start_y)
                pyautogui.mouseDown()
                time.sleep(0.2)
                pyautogui.moveTo(end_x, end_y, duration=1.5)
                pyautogui.mouseUp()
            except pyautogui.FailSafeException:
                raise ValueError("Failed to drag the mouse")


mouse_server = MouseMCPServer()

if __name__ == "__main__":
    mouse_server.run()