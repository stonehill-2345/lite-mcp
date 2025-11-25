"""
file system MCP Server - Provide basic operations of the file system
"""

from src.tools.base import BaseMCPServer
from src.core.statistics import mcp_author
import os
import shutil
from typing import Dict, List, Any

@mcp_author("liefeng", email="lhyhr@vip.qq.com", department="TestingDepartment", project=["TD"])
class FileSystemMCPServer(BaseMCPServer):
    """
    File System MCP Server - Provides comprehensive file system operations.
    
    This server provides 10 essential file system tools:
    
    File Operations:
    1. create_file - Create a new empty file
    2. read_file - Read file contents (with binary file support)
    3. write_file - Write/overwrite content to a file
    4. delete_file - Delete a specific file
    5. rename_file - Rename or move a file
    6. copy_file - Copy a file to a new location
    7. move_file - Move a file to a new location
    
    Directory Operations:
    8. create_directory - Create a new directory (with parent directories)
    9. delete_directory - Delete a directory recursively
    10. list_files - List all files and directories in a directory
    
    Information:
    11. get_file_info - Get detailed file/directory metadata
    
    Features:
    - Automatic parent directory creation when needed
    - Comprehensive error handling and validation
    - Support for both absolute and relative paths
    - Binary file detection for read operations
    - Human-readable file size formatting
    - UTF-8 encoding by default
    """
    def __init__(self, name: str = "LiteMCP-FileSystem"):
        super().__init__(name)

    def _register_tools(self):
        """Register tools - supports multiple MCP tools"""
        @self.mcp.tool()
        async def create_file(file_path: str, create_mode: str = "w", encoding: str = "utf-8") -> str:
            """
            Create a new file at the specified path.
            
            Args:
                file_path (str): The path where the new file should be created.
                                 Can be absolute or relative path.
                create_mode (str): The mode to create the file. Can be "w" for write, "w+" for write binary, "a+" for write and read.
                encoding (str): The encoding to use for text files. Default is "utf-8".
            Returns:
                str: Success message indicating the file was created successfully.
            
            Raises:
                OSError: If the file cannot be created (e.g., permission denied).
                FileExistsError: If the file already exists.
            """
            try:
                if os.path.exists(file_path):
                    return f"Error: File {file_path} already exists"
                
                # Ensure parent directory exists
                parent_dir = os.path.dirname(file_path)
                if parent_dir and not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('')
                return f"File {file_path} created successfully"
            except Exception as e:
                return f"Error creating file {file_path}: {str(e)}"
        
        @self.mcp.tool()
        async def read_file(file_path: str, read_mode: str = "r", encoding: str = "utf-8") -> str:
            """
            Read the contents of a file.
            
            Args:
                file_path (str): The path to the file to be read.
                                 Can be absolute or relative path.
                read_mode (str): The mode to read the file. Can be "r" for read, "rb" for read binary.
                encoding (str): The encoding to use for text files. Default is "utf-8".
            Returns:
                str: The contents of the file as a string, or error message if failed.
            
            Raises:
                FileNotFoundError: If the file does not exist.
                PermissionError: If read permission is denied.
                UnicodeDecodeError: If the file cannot be decoded as text.
            """
            try:
                if not os.path.exists(file_path):
                    return f"Error: File {file_path} does not exist"
                
                if not os.path.isfile(file_path):
                    return f"Error: {file_path} is not a file"
                
                with open(file_path, read_mode, encoding=encoding) as f:
                    return f.read()            
            except Exception as e:
                return f"Error reading file {file_path}: {str(e)}"

        @self.mcp.tool()
        async def write_file(file_path: str, content: str, write_mode: str = "w", encoding: str = "utf-8") -> str:
            """
            Write content to a file (overwrites existing content).
            
            Args:
                file_path (str): The path to the file to write to.
                                 Can be absolute or relative path.
                content (str): The content to write to the file.
                write_mode (str): The mode to write to the file. Can be "w" for write, "wb" for write binary, "a" for append, "a+" for append and read.
                encoding (str): The encoding to use for text files. Default is "utf-8".
            Returns:
                str: Success message indicating the file was written successfully,
                     or error message if failed.
            
            Raises:
                PermissionError: If write permission is denied.
                OSError: If the file cannot be written.
            """
            try:
                # Ensure parent directory exists
                parent_dir = os.path.dirname(file_path)
                if parent_dir and not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)
                
                with open(file_path, write_mode, encoding=encoding) as f:
                    f.write(content)
                return f"File {file_path} written successfully"
            except Exception as e:
                return f"Error writing to file {file_path}: {str(e)}"

        @self.mcp.tool()
        async def delete_file(file_path: str) -> str:
            """
            Delete a file from the file system.
            
            Args:
                file_path (str): The path to the file to be deleted.
                                 Can be absolute or relative path.
            
            Returns:
                str: Success message indicating the file was deleted successfully,
                     or error message if failed.
            
            Raises:
                FileNotFoundError: If the file does not exist.
                PermissionError: If delete permission is denied.
                IsADirectoryError: If the path is a directory, not a file.
            """
            try:
                if not os.path.exists(file_path):
                    return f"Error: File {file_path} does not exist"
                
                if not os.path.isfile(file_path):
                    return f"Error: {file_path} is not a file. Use delete_directory for directories."
                
                os.remove(file_path)
                return f"File {file_path} deleted successfully"
            except Exception as e:
                return f"Error deleting file {file_path}: {str(e)}"

        @self.mcp.tool()
        async def rename_file(file_path: str, new_name: str) -> str:
            """
            Rename or move a file to a new name or path.
            
            Args:
                file_path (str): The current path to the file.
                                 Can be absolute or relative path.
                new_name (str): The new name or path for the file.
                                Can be just a filename or a full path.
            
            Returns:
                str: Success message indicating the file was renamed successfully,
                     or error message if failed.
            
            Raises:
                FileNotFoundError: If the source file does not exist.
                FileExistsError: If the destination file already exists.
                PermissionError: If rename permission is denied.
            """
            try:
                if not os.path.exists(file_path):
                    return f"Error: File {file_path} does not exist"
                
                if os.path.exists(new_name):
                    return f"Error: Destination {new_name} already exists"
                
                os.rename(file_path, new_name)
                return f"File {file_path} renamed to {new_name} successfully"
            except Exception as e:
                return f"Error renaming file {file_path}: {str(e)}"

        @self.mcp.tool()
        async def copy_file(file_path: str, new_path: str, overwrite: bool = False) -> str:
            """
            Copy a file to a new location.
            
            Args:
                file_path (str): The path to the source file to be copied.
                                 Can be absolute or relative path.
                new_path (str): The destination path where the file should be copied to.
                                Can be a directory or a full file path.
                overwrite (bool): Whether to overwrite the destination file if it exists.
                                  Default is False (do not overwrite).
                                  If False and destination exists, returns an error.
                                  If True, will overwrite existing file.
            
            Returns:
                str: Success message indicating the file was copied successfully,
                     or error message if failed.
            
            Raises:
                FileNotFoundError: If the source file does not exist.
                PermissionError: If copy permission is denied.
                shutil.SameFileError: If source and destination are the same file.
                FileExistsError: If destination exists and overwrite is False.
            """
            try:
                if not os.path.exists(file_path):
                    return f"Error: Source file {file_path} does not exist"
                
                if not os.path.isfile(file_path):
                    return f"Error: {file_path} is not a file"

                # Determine the actual destination path
                if os.path.isdir(new_path):
                    # If new_path is a directory, use the same filename
                    dest_file = os.path.join(new_path, os.path.basename(file_path))
                else:
                    dest_file = new_path
                
                # Check if destination file exists and overwrite is False
                if os.path.exists(dest_file) and not overwrite:
                    return f"Error: Destination file {dest_file} already exists. Set overwrite=True to replace it."
                
                # Ensure destination directory exists
                dest_dir = os.path.dirname(dest_file)
                if dest_dir and not os.path.exists(dest_dir):
                    os.makedirs(dest_dir, exist_ok=True)
                
                shutil.copy2(file_path, dest_file)  # copy2 preserves metadata
                action = "overwrote" if overwrite and os.path.exists(dest_file) else "copied"
                return f"File {file_path} {action} to {dest_file} successfully"
            except shutil.SameFileError:
                return f"Error: Source and destination are the same file"
            except Exception as e:
                return f"Error copying file {file_path}: {str(e)}"

        @self.mcp.tool()
        async def move_file(file_path: str, new_path: str, overwrite: bool = False) -> str:
            """
            Move a file to a new location.
            
            Args:
                file_path (str): The path to the source file to be moved.
                                 Can be absolute or relative path.
                new_path (str): The destination path where the file should be moved to.
                                Can be a directory or a full file path.
                overwrite (bool): Whether to overwrite the destination file if it exists.
                                  Default is False (do not overwrite).
                                  If False and destination exists, returns an error.
                                  If True, will replace existing file.
            
            Returns:
                str: Success message indicating the file was moved successfully,
                     or error message if failed.
            
            Raises:
                FileNotFoundError: If the source file does not exist.
                PermissionError: If move permission is denied.
                shutil.Error: If the move operation fails.
                FileExistsError: If destination exists and overwrite is False.
            """
            try:
                if not os.path.exists(file_path):
                    return f"Error: Source file {file_path} does not exist"
                
                if not os.path.isfile(file_path):
                    return f"Error: {file_path} is not a file"
                
                # Determine the actual destination path
                if os.path.isdir(new_path):
                    # If new_path is a directory, use the same filename
                    dest_file = os.path.join(new_path, os.path.basename(file_path))
                else:
                    dest_file = new_path
                
                # Check if destination file exists and overwrite is False
                if os.path.exists(dest_file) and not overwrite:
                    return f"Error: Destination file {dest_file} already exists. Set overwrite=True to replace it."
                
                # Ensure destination directory exists
                dest_dir = os.path.dirname(dest_file)
                if dest_dir and not os.path.exists(dest_dir):
                    os.makedirs(dest_dir, exist_ok=True)
                
                # If overwrite is True and destination exists, remove it first
                if overwrite and os.path.exists(dest_file):
                    os.remove(dest_file)
                
                shutil.move(file_path, dest_file)
                action = "moved and replaced" if overwrite else "moved"
                return f"File {file_path} {action} to {dest_file} successfully"
            except Exception as e:
                return f"Error moving file {file_path}: {str(e)}"

        @self.mcp.tool()
        async def list_files(directory: str) -> List[str]:
            """
            List all files and directories in a specified directory.
            
            Args:
                directory (str): The path to the directory to list.
                                 Can be absolute or relative path.
            
            Returns:
                List[str]: A list of filenames and directory names in the specified directory,
                          or error message if failed.
            
            Raises:
                FileNotFoundError: If the directory does not exist.
                NotADirectoryError: If the path is not a directory.
                PermissionError: If read permission is denied.
            """
            try:
                if not os.path.exists(directory):
                    return f"Error: Directory {directory} does not exist"
                
                if not os.path.isdir(directory):
                    return f"Error: {directory} is not a directory"
                
                items = os.listdir(directory)
                return items if items else []
            except Exception as e:
                return f"Error listing directory {directory}: {str(e)}"

        @self.mcp.tool()
        async def get_file_info(file_path: str) -> Dict[str, Any]:
            """
            Get detailed information about a file or directory.
            
            Args:
                file_path (str): The path to the file or directory.
                                 Can be absolute or relative path.
            
            Returns:
                Dict[str, Any]: A dictionary containing file information including:
                    - size: File size in bytes
                    - created: Creation time
                    - modified: Last modification time
                    - accessed: Last access time
                    - is_file: Whether it's a file
                    - is_dir: Whether it's a directory
                    - permissions: File permissions (on Unix systems)
                Or error message if failed.
            
            Raises:
                FileNotFoundError: If the file does not exist.
                PermissionError: If stat permission is denied.
            """
            try:
                if not os.path.exists(file_path):
                    return {"error": f"File {file_path} does not exist"}
                
                stat_info = os.stat(file_path)
                file_info = {
                    "path": os.path.abspath(file_path),
                    "name": os.path.basename(file_path),
                    "size_bytes": stat_info.st_size,
                    "size_readable": self._format_size(stat_info.st_size),
                    "created_time": stat_info.st_ctime,
                    "modified_time": stat_info.st_mtime,
                    "accessed_time": stat_info.st_atime,
                    "is_file": os.path.isfile(file_path),
                    "is_directory": os.path.isdir(file_path),
                    "is_symlink": os.path.islink(file_path),
                }
                
                # Add permissions info (Unix-like systems)
                if hasattr(stat_info, 'st_mode'):
                    import stat
                    file_info["permissions"] = oct(stat_info.st_mode)[-3:]
                
                return file_info
            except Exception as e:
                return {"error": f"Error getting file info for {file_path}: {str(e)}"}

        @self.mcp.tool()
        async def create_directory(directory_path: str) -> str:
            """
            Create a new directory (including parent directories if needed).
            
            Args:
                directory_path (str): The path where the new directory should be created.
                                      Can be absolute or relative path.
                                      Parent directories will be created automatically if they don't exist.
            
            Returns:
                str: Success message indicating the directory was created successfully,
                     or error message if failed.
            
            Raises:
                PermissionError: If create permission is denied.
                FileExistsError: If a file (not directory) already exists at the path.
            """
            try:
                if os.path.exists(directory_path):
                    if os.path.isdir(directory_path):
                        return f"Directory {directory_path} already exists"
                    else:
                        return f"Error: A file already exists at {directory_path}"
                
                os.makedirs(directory_path, exist_ok=True)
                return f"Directory {directory_path} created successfully"
            except Exception as e:
                return f"Error creating directory {directory_path}: {str(e)}"

        @self.mcp.tool()
        async def delete_directory(directory_path: str) -> str:
            """
            Delete a directory and all its contents recursively.
            
            Args:
                directory_path (str): The path to the directory to be deleted.
                                      Can be absolute or relative path.
                                      WARNING: This will delete all contents recursively.
            
            Returns:
                str: Success message indicating the directory was deleted successfully,
                     or error message if failed.
            
            Raises:
                FileNotFoundError: If the directory does not exist.
                NotADirectoryError: If the path is not a directory.
                PermissionError: If delete permission is denied.
            """
            try:
                if not os.path.exists(directory_path):
                    return f"Error: Directory {directory_path} does not exist"
                
                if not os.path.isdir(directory_path):
                    return f"Error: {directory_path} is not a directory. Use delete_file for files."
                
                shutil.rmtree(directory_path)
                return f"Directory {directory_path} deleted successfully"
            except Exception as e:
                return f"Error deleting directory {directory_path}: {str(e)}"
    
    def _format_size(self, size_bytes: int) -> str:
        """
        Convert bytes to human-readable format.
        
        Args:
            size_bytes (int): Size in bytes
            
        Returns:
            str: Human-readable size string (e.g., "1.5 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

file_system_server = FileSystemMCPServer()

if __name__ == "__main__":
    file_system_server.run()