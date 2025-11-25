# File System MCP Tools

## Overview
Comprehensive MCP tool collection for file system operations, including file and directory creation, reading, writing, deletion, copying, and moving.

## Tools List

### File Operations (7 tools)

| Tool Name | Function | Parameters | Return Value |
|-----------|----------|------------|--------------|
| `create_file` | Create a new file | `file_path: str` | Success/Error message |
| `read_file` | Read file contents | `file_path: str` | File content/Error message |
| `write_file` | Write content to file | `file_path: str`<br>`content: str` | Success/Error message |
| `delete_file` | Delete a file | `file_path: str` | Success/Error message |
| `rename_file` | Rename/Move a file | `file_path: str`<br>`new_name: str` | Success/Error message |
| `copy_file` | Copy a file | `file_path: str`<br>`new_path: str`<br>`overwrite: bool = False` | Success/Error message |
| `move_file` | Move a file | `file_path: str`<br>`new_path: str`<br>`overwrite: bool = False` | Success/Error message |

### Directory Operations (3 tools)

| Tool Name | Function | Parameters | Return Value |
|-----------|----------|------------|--------------|
| `create_directory` | Create a directory | `directory_path: str` | Success/Error message |
| `delete_directory` | Delete a directory | `directory_path: str` | Success/Error message |
| `list_files` | List directory contents | `directory: str` | List of files/directories |

### Information Query (1 tool)

| Tool Name | Function | Parameters | Return Value |
|-----------|----------|------------|--------------|
| `get_file_info` | Get file information | `file_path: str` | File metadata dictionary |

## Key Features

✅ **Auto-create Parent Directories** - Automatically creates missing parent directories when creating files or writing  
✅ **Overwrite Control** - `copy_file` and `move_file` support `overwrite` parameter (default: no overwrite)  
✅ **Cross-platform** - Consistent behavior across Windows/Linux/Mac  
✅ **UTF-8 Encoding** - Default UTF-8 encoding with Chinese character support  
✅ **Binary File Detection** - Automatically detects binary files during read operations  
✅ **Robust Error Handling** - Detailed error messages for all operations  

## Usage Examples

```python
# Create file (auto-creates multi-level parent directories)
create_file("path/to/new/file.txt")

# Read file
content = read_file("file.txt")

# Write to file
write_file("file.txt", "Hello World")

# Copy file (overwrite existing destination file)
copy_file("source.txt", "dest.txt", overwrite=True)

# Move file (no overwrite)
move_file("source.txt", "new_location/", overwrite=False)

# Create multi-level directory
create_directory("level1/level2/level3")

# List directory contents
files = list_files("./")

# Get detailed file information
info = get_file_info("file.txt")
# Returns: {path, name, size_bytes, size_readable, created_time, modified_time, ...}
```

## Important Notes

⚠️ **Directory Deletion** - `delete_directory` recursively deletes all contents, use with caution  
⚠️ **Overwrite Default** - `copy_file` and `move_file` default to no overwrite, explicitly set `overwrite=True` if needed  
⚠️ **Path Format** - Supports both relative and absolute paths  


