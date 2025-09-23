"""
Android Mobile Device Interaction (uiautomator2)

Encapsulates mobile interaction logic and state views within the androidTools directory.
Provides:
- Mobile: device connection, screenshots, MobileState generation
- MobileState: contains TreeState and optional PNG byte screenshot
"""

from dataclasses import dataclass
from typing import Optional
from io import BytesIO
import uiautomator2 as u2
from PIL import Image as PILImage

# Tree-related types imported from uiTree package
from src.tools.androidTools.uiTree import Tree, TreeState


@dataclass
class MobileState:
    tree_state: TreeState
    screenshot: Optional[bytes] = None


class Mobile:
    """Mobile device wrapper based on uiautomator2"""

    def __init__(self, device: Optional[str] = None):
        try:
            self.device = u2.connect(device)
            # Probe to ensure connection is working
            _ = self.device.info
        except u2.ConnectError as e:
            raise ConnectionError(f"Failed to connect to device {device}: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error connecting to device {device}: {e}")

    def get_device(self):
        return self.device

    def get_state(self, use_vision: bool = False) -> MobileState:
        try:
            tree = Tree(self)
            tree_state = tree.get_state()
            if use_vision:
                nodes = tree_state.interactive_elements
                annotated = tree.annotated_screenshot(nodes=nodes, scale=1.0)
                screenshot = self._image_to_png_bytes(annotated)
            else:
                screenshot = None
            return MobileState(tree_state=tree_state, screenshot=screenshot)
        except Exception as e:
            raise RuntimeError(f"Failed to get device state: {e}")

    def get_screenshot(self, scale: float = 0.7) -> PILImage:
        try:
            screenshot = self.device.screenshot()
            if screenshot is None:
                raise ValueError("Screenshot capture returned None.")
            size = (int(screenshot.width * scale), int(screenshot.height * scale))
            screenshot.thumbnail(size=size, resample=PILImage.Resampling.LANCZOS)
            return screenshot
        except Exception as e:
            raise RuntimeError(f"Failed to get screenshot: {e}")

    def _image_to_png_bytes(self, screenshot: PILImage) -> bytes:
        try:
            if screenshot is None:
                raise ValueError("Screenshot is None")
            io_buf = BytesIO()
            screenshot.save(io_buf, format='PNG')
            data = io_buf.getvalue()
            if not data:
                raise ValueError("Screenshot conversion resulted in empty bytes.")
            return data
        except Exception as e:
            raise RuntimeError(f"Failed to convert screenshot to bytes: {e}")
