### Android MCP Server

Android MCP Server provides a complete set of tools to directly interact with Android devices: tap, long‑press, swipe, drag, text input, hardware keys, notification shade, waiting, and retrieving the UI interactive elements tree with optional annotated screenshots.

### Feature Overview

- **Device actions**: `click_tool`, `long_click_tool`, `swipe_tool`, `drag_tool`
- **Text/keys**: `type_tool`, `press_tool`
- **System/utility**: `notification_tool`, `wait_tool`
- **State retrieval**: `state_tool` (list of interactive UI elements + optional annotated screenshot), `device_info_tool`

### Dependencies & Environment

- ADB installed and available in system PATH
- Python deps: `uiautomator2`, `Pillow`
- Enable Developer Options and USB debugging on device, or start an emulator (e.g., AVD)

Check ADB:
```bash
adb version
adb devices
```

### How to Run

1) Run the server directly:
```bash
# Physical device (default)
python src/tools/android_tools/android_server.py

# Use emulator
python src/tools/android_tools/android_server.py --emulator
```

2) Via project scripts:
```bash
# Start all (includes Android server)
./scripts/manage.sh up

# Start Android server only
./scripts/manage.sh up --name android
```

On Windows PowerShell, use the corresponding `.bat`/`.ps1` script or run the `python` commands directly.

### Tools and Usage

- **click_tool(x, y)**: tap at coordinates
- **long_click_tool(x, y)**: long‑press at coordinates
- **swipe_tool(x1, y1, x2, y2)**: swipe
- **drag_tool(x1, y1, x2, y2)**: drag
- **type_tool(text, x=0, y=0, clear=False)**: optionally focus by coordinates then input; `clear=True` tries to clear the focused edit field
- **press_tool(button)**: press a key; supports `home|back|menu|power|volume_up|volume_down|enter|delete|space`
- **notification_tool()**: open notification shade
- **wait_tool(duration)**: sleep for seconds
- **device_info_tool()**: return the list of connected devices (tolerant of Windows console encodings)
- **state_tool(use_vision=False)**: return a list

Example:
```python
click_tool(x=100, y=200)
long_click_tool(x=150, y=250)
swipe_tool(x1=100, y1=200, x2=300, y2=400)
drag_tool(x1=50, y1=300, x2=350, y2=600)
type_tool(text="Hello World", x=100, y=200, clear=True)
press_tool(button="home")
notification_tool()
wait_tool(duration=5)

# Get state (with annotated screenshot)
result = state_tool(use_vision=True)
text_view = result[0]              # str: textual list of interactive elements
maybe_image = result[1]            # Image: FastMCP Image object (PNG)
```

### UI Tree & Screenshot Annotation

- Parse visible and interactive nodes from `uiautomator2.dump_hierarchy()`
- Interactivity rules: `focusable=true` or `clickable=true` or class in `INTERACTIVE_CLASSES`
- `uiTree` provides:
  - Coordinate and bounding box parsing (`utils.extract_cordinates`)
  - Center coordinate calculation (`utils.get_center_cordinates`)
  - Data structures (`views.ElementNode`, `BoundingBox`, `TreeState`, `CenterCord`)
  - Screenshot annotation (random colors, indexed labels, text backgrounds)

### Return Types & Serialization Notes

- `state_tool` sets `output_schema=None` to avoid FastMCP auto‑structuring issues with `Image`; it returns `[str, Image?]` directly
- `device_info_tool` prefers UTF‑8 when decoding `adb` output on Windows console, ignoring errors for robustness

### Supported Keys

| Key | Description |
|-----|-------------|
| home | Home |
| back | Back |
| menu | Menu |
| power | Power |
| volume_up | Volume Up |
| volume_down | Volume Down |
| enter | Enter |
| delete | Delete |
| space | Space |

### Troubleshooting

- **Device not detected**: check USB, authorization, and `adb devices`
- **ADB command fails**: verify installation and PATH; try `adb kill-server && adb start-server`
- **Permission denied**: accept the USB debugging authorization prompt on device
- **Tap ineffective/wrong coordinates**: inspect with `state_tool` to confirm element coords and scaling

### Directory Structure (excerpt)
```
src/tools/android_tools/
├── __init__.py
├── android_server.py      # AndroidMCPServer; registers all tools
├── mobile.py              # Mobile / MobileState; screenshot & state aggregation
├── uiTree/
│   ├── __init__.py        # Tree / TreeState / ElementNode ...
│   ├── config.py          # Interactive class whitelist
│   ├── utils.py           # Coordinate parsing & center calculation
│   └── views.py           # Data structure definitions
└── README.md
```
