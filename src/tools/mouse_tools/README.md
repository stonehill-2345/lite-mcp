### Mouse MCP Server

Mouse MCP Server provides a complete set of tools to control mouse and keyboard operations on Windows devices: move, click, double-click, drag, scroll, press/release, and keyboard shortcuts.

### Feature Overview

- **Mouse movement**: `move_mouse` - move cursor to specified coordinates
- **Mouse clicking**: `click_mouse` - single click, double-click, right-click, middle-click
- **Mouse press/release**: `mouse_press`, `mouse_release` - low-level mouse button control
- **Mouse dragging**: `mouse_drag` - drag from one point to another
- **Mouse scrolling**: `mouse_scroll` - scroll up, down, left, or right
- **Keyboard control**: `press_key` - press single keys or keyboard shortcuts

### Dependencies & Environment

- Python package: `pyautogui`
- Supports Windows devices
- Requires appropriate permissions for mouse/keyboard control

Install dependencies:
```bash
uv sync
```

### How to Run

```bash
# Start Mouse server only
uv run python .\scripts\manage.py up --name mouse_tools
```

### Tools and Usage

#### move_mouse(x, y)
Move the mouse cursor to specified coordinates.

**Parameters:**
- `x` (int): The x coordinate to move to
- `y` (int): The y coordinate to move to

**Example:**
```python
move_mouse(x=500, y=300)
```

#### click_mouse(x, y, button="left")
Click the mouse at specified coordinates.

**Parameters:**
- `x` (int): The x coordinate to click at
- `y` (int): The y coordinate to click at
- `button` (str): Button type - `"left"`, `"right"`, `"middle"`, or `"double_left"` for double-click

**Examples:**
```python
# Single left click
click_mouse(x=100, y=200)

# Right click
click_mouse(x=100, y=200, button="right")

# Double click
click_mouse(x=100, y=200, button="double_left")

# Middle click
click_mouse(x=100, y=200, button="middle")
```

**Note:** When using `button="double_left"`, the function automatically performs a double-click with 0.1 second interval between clicks.

#### mouse_press(x, y, button="left")
Press (hold down) the mouse button at specified coordinates without releasing.

**Parameters:**
- `x` (int): The x coordinate to press at
- `y` (int): The y coordinate to press at
- `button` (str): Button type - `"left"`, `"right"`, or `"middle"`

**Example:**
```python
mouse_press(x=100, y=200, button="left")
```

#### mouse_release(x, y, button="left")
Release the mouse button at specified coordinates.

**Parameters:**
- `x` (int): The x coordinate to release at
- `y` (int): The y coordinate to release at
- `button` (str): Button type - `"left"`, `"right"`, or `"middle"`

**Example:**
```python
mouse_release(x=100, y=200, button="left")
```

#### mouse_drag(start_x, start_y, end_x, end_y, duration=0.5)
Drag the mouse from source coordinates to target coordinates.

**Parameters:**
- `start_x` (int): Starting x coordinate
- `start_y` (int): Starting y coordinate
- `end_x` (int): Ending x coordinate
- `end_y` (int): Ending y coordinate
- `duration` (float): Duration of the drag in seconds (default: 0.5)

**Example:**
```python
# Drag from (100, 100) to (300, 300)
mouse_drag(start_x=100, start_y=100, end_x=300, end_y=300, duration=1.0)
```

#### mouse_scroll(x, y, scroll_amount=30, scroll_type="up")
Scroll the mouse at specified coordinates.

**Parameters:**
- `x` (int): The x coordinate to scroll at
- `y` (int): The y coordinate to scroll at
- `scroll_amount` (int): Amount to scroll (default: 30)
- `scroll_type` (str): Scroll direction - `"up"`, `"down"`, `"left"`, or `"right"`

**Examples:**
```python
# Scroll up
mouse_scroll(x=500, y=500, scroll_amount=50, scroll_type="up")

# Scroll down
mouse_scroll(x=500, y=500, scroll_amount=50, scroll_type="down")

# Scroll left
mouse_scroll(x=500, y=500, scroll_amount=30, scroll_type="left")

# Scroll right
mouse_scroll(x=500, y=500, scroll_amount=30, scroll_type="right")
```

#### press_key(key)
Press a keyboard key or key combination (hotkey/shortcut).

**Parameters:**
- `key` (str): Key name or combination separated by `+` (e.g., `"ctrl+c"`, `"alt+tab"`)

**Examples:**
```python
# Single key
press_key(key="enter")
press_key(key="escape")

# Key combinations (shortcuts)
press_key(key="ctrl+c")      # Copy
press_key(key="ctrl+v")      # Paste
press_key(key="alt+tab")     # Switch window
press_key(key="win+d")       # Show desktop
press_key(key="ctrl+shift+esc")  # Task manager
```

### Complete Usage Example

```python
# Move mouse to coordinates
move_mouse(x=100, y=100)

# Single click
click_mouse(x=100, y=100, button="left")

# Double click to select
click_mouse(x=200, y=200, button="double_left")

# Right click to open context menu
click_mouse(x=300, y=300, button="right")

# Drag to select text or move item
mouse_drag(start_x=100, start_y=100, end_x=300, end_y=300, duration=1.0)

# Scroll down to view more content
mouse_scroll(x=500, y=500, scroll_amount=100, scroll_type="down")

# Use keyboard shortcuts
press_key(key="ctrl+c")      # Copy
press_key(key="ctrl+v")      # Paste

# Custom press and release sequence
mouse_press(x=100, y=100, button="left")
# ... do something ...
mouse_release(x=200, y=200, button="left")
```

### Supported Mouse Buttons

| Button | Description |
|--------|-------------|
| left | Left mouse button |
| right | Right mouse button |
| middle | Middle mouse button (scroll wheel click) |
| double_left | Double-click with left button (0.1s interval) |

### Supported Scroll Directions

| Direction | Description |
|-----------|-------------|
| up | Scroll up (positive vertical scroll) |
| down | Scroll down (negative vertical scroll) |
| left | Scroll left (horizontal scroll) |
| right | Scroll right (negative horizontal scroll) |

