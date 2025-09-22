"""
Fastbot Android Stability Testing Server

MCP server based on Fastbot Android tool, providing Android application stability testing functionality.
Supports device management, APK installation, stability testing, log analysis, and more.

Note: Before using this tool, ensure that the device running this MCP has set up the ADB environment and connected to an Android device or emulator with debugging mode enabled (in sse/http mode, the MCP server needs to have this environment)
"""

import os
import json
import uuid
import shutil
import re
import subprocess
import threading
from apkutils2 import APK
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

from src.core.statistics import mcp_author
from src.tools.base import BaseMCPServer
from src.core.utils import get_project_root


@mcp_author("Bab", email="bab@2345.com", department="TestingDepartment", project=["TD"])
class FastbotMCPServer(BaseMCPServer):
    """Fastbot Android Stability Testing Server

    Provides complete functionality for Android application stability testing:
    - Device management and detection
    - APK installation and management
    - Stability test execution
    - Log collection and analysis
    - Exception detection and reporting

    Usage examples:
    - Run a 5-minute stability test for "com.weatherday"
    - Install /Users/bab/Downloads/sc-tq_fr_xyl.apk and perform a 5-minute stability test
    - Get the package name of /Users/bab/Downloads/sc-tq_fr_xyl.apk
    """

    def __init__(self, name: str = "LiteMCP-Fastbot"):
        # Set log configuration type to high volume
        self._log_config_type = "high_volume"
        super().__init__(name)
        # Get project root directory
        self.project_root = get_project_root()
        self.fastbot_dir = Path(__file__).parent / "fastbot_android"
        self.logs_dir = self.project_root / "runtime/logs/fastbot"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Fastbot JAR file paths
        self.monkeyq_jar = self.fastbot_dir / "monkeyq.jar"
        self.framework_jar = self.fastbot_dir / "framework.jar"
        self.thirdpart_jar = self.fastbot_dir / "fastbot-thirdpart.jar"

        # Multi-client protection mechanism
        self._device_locks = {}  # device_id -> threading.Lock
        self._active_sessions = {}  # device_id -> session_id
        self._global_lock = threading.Lock()

        # Verify required files exist
        self._verify_fastbot_files()

    def _verify_fastbot_files(self):
        """Verify Fastbot required files exist"""
        required_files = [self.monkeyq_jar, self.framework_jar, self.thirdpart_jar]
        missing_files = [f for f in required_files if not f.exists()]

        if missing_files:
            print(f"Warning: Missing Fastbot files: {[str(f) for f in missing_files]}")

    def _acquire_device_lock(self, device_id: str, session_id: str) -> bool:
        """Attempt to acquire device lock"""
        with self._global_lock:
            # Initialize device lock
            if device_id not in self._device_locks:
                self._device_locks[device_id] = threading.Lock()
            
            # Check if device is occupied
            if device_id in self._active_sessions:
                return False
            
            # Try to acquire lock
            if self._device_locks[device_id].acquire(blocking=False):
                self._active_sessions[device_id] = session_id
                return True
            
            return False

    def _release_device_lock(self, device_id: str, session_id: str) -> bool:
        """Release device lock"""
        with self._global_lock:
            if (device_id in self._active_sessions and 
                self._active_sessions[device_id] == session_id):
                
                del self._active_sessions[device_id]
                if device_id in self._device_locks:
                    self._device_locks[device_id].release()
                return True
            
            return False

    def _get_device_lock_status(self, device_id: str) -> Dict:
        """Get device lock status"""
        with self._global_lock:
            return {
                "device_id": device_id,
                "is_locked": device_id in self._active_sessions,
                "current_session": self._active_sessions.get(device_id),
                "available": device_id not in self._active_sessions
            }

    @staticmethod
    def _run_adb_command(cmd: List[str], device_id: Optional[str] = None) -> Tuple[bool, str]:
        """Execute ADB command"""
        try:
            full_cmd = ["adb"]
            if device_id:
                full_cmd.extend(["-s", device_id])
            full_cmd.extend(cmd)

            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()

        except subprocess.TimeoutExpired:
            return False, "ADB command execution timed out"
        except FileNotFoundError:
            return False, "ADB command not found, please ensure Android SDK is installed and PATH is configured"
        except Exception as e:
            return False, f"Error executing ADB command: {str(e)}"

    @staticmethod
    def _generate_session_id() -> str:
        """Generate unique session identifier"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"fastbot_{timestamp}_{unique_id}"

    @staticmethod
    def _parse_crash_log( log_content: str) -> List[Dict]:
        """Parse crash logs"""
        crashes = []

        # Match Java crashes
        java_crash_pattern = r'FATAL EXCEPTION: (.*?)\n(.*?)at (.*?)\n(.*?)(?=\n\n|\Z)'
        for match in re.finditer(java_crash_pattern, log_content, re.DOTALL):
            crashes.append({
                "type": "java_crash",
                "thread": match.group(1).strip(),
                "exception": match.group(2).strip(),
                "location": match.group(3).strip(),
                "stack_trace": match.group(4).strip()[:1000]  # Limit length
            })

        # Match ANR
        anr_pattern = r'ANR in (.*?)\n.*?Reason: (.*?)\n'
        for match in re.finditer(anr_pattern, log_content, re.DOTALL):
            crashes.append({
                "type": "anr",
                "process": match.group(1).strip(),
                "reason": match.group(2).strip()
            })

        # Match Native crashes
        native_crash_pattern = r'signal \d+ \(SIG.*?\).*?backtrace:(.*?)(?=\n\n|\Z)'
        for match in re.finditer(native_crash_pattern, log_content, re.DOTALL):
            crashes.append({
                "type": "native_crash",
                "signal": "Native crash detected",
                "backtrace": match.group(1).strip()[:1000]
            })

        return crashes

    def _get_storage_info_internal(self) -> Dict:
        """Internal method: Get storage information"""
        try:
            if not self.logs_dir.exists():
                return {
                    "status": "success",
                    "storage_info": {
                        "total_size_bytes": 0,
                        "total_size_mb": 0,
                        "total_sessions": 0,
                        "total_files": 0,
                        "disk_usage": {"disk_usage_percentage": 0}
                    }
                }

            total_size = 0
            total_files = 0
            session_count = 0

            for session_dir in self.logs_dir.iterdir():
                if session_dir.is_dir():
                    session_count += 1
                    for file_path in session_dir.rglob('*'):
                        if file_path.is_file():
                            total_size += file_path.stat().st_size
                            total_files += 1

            total_disk, used_disk, free_disk = shutil.disk_usage(self.logs_dir)

            return {
                "status": "success",
                "storage_info": {
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "total_sessions": session_count,
                    "total_files": total_files,
                    "disk_usage": {
                        "disk_usage_percentage": round((used_disk / total_disk) * 100, 2)
                    }
                }
            }
        except Exception:
            return {"status": "error"}

    def _list_sessions_internal(self) -> Dict:
        """Internal method: List test sessions"""
        try:
            if not self.logs_dir.exists():
                return {"status": "success", "total_sessions": 0, "sessions": []}

            sessions = []
            session_dirs = [d for d in self.logs_dir.iterdir() if d.is_dir()]

            for session_dir in session_dirs:
                session_info = {
                    "session_id": session_dir.name,
                    "modified_time": datetime.fromtimestamp(session_dir.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                }

                total_size = sum(f.stat().st_size for f in session_dir.rglob('*') if f.is_file())
                session_info["size_mb"] = round(total_size / (1024 * 1024), 2)

                sessions.append(session_info)

            return {"status": "success", "total_sessions": len(sessions), "sessions": sessions}
        except Exception:
            return {"status": "error", "total_sessions": 0, "sessions": []}

    def _read_session_config(self, session_id: str) -> Tuple[Dict, Path]:
        """Internal method: Read test session configuration file
        
        Args:
            session_id: Test session ID
            
        Returns:
            Tuple[Configuration dictionary, Session directory path]
        """
        session_log_dir = self.logs_dir / session_id
        config_file = session_log_dir / "test_config.json"
        config = {}
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception as e:
                config = {"error": f"Failed to read configuration file: {str(e)}"}
        
        return config, session_log_dir

    @staticmethod
    def _get_log_file_info(session_log_dir: Path) -> Dict:
        """Internal method: Get log file information
        
        Args:
            session_log_dir: Session log directory
            
        Returns:
            Log file information dictionary
        """
        log_file = session_log_dir / "fastbot_test.log"
        log_info = {
            "exists": log_file.exists(),
            "size_bytes": 0,
            "last_modified": None,
            "lines_count": 0,
            "size_mb": 0
        }

        if log_file.exists():
            try:
                stat = log_file.stat()
                log_info.update({
                    "size_bytes": stat.st_size,
                    "last_modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2)
                })
                
                # Count log lines (optional)
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    log_info["lines_count"] = len(lines)
                    log_info["recent_lines"] = [line.strip() for line in lines[-3:]] if lines else []
            except Exception:
                # If reading fails, keep default values
                pass
        
        return log_info

    def _extract_session_crashes(self, session_log_dir: Path) -> List[Dict]:
        """Internal method: Extract crash information from session logs
        
        Args:
            session_log_dir: Session log directory
            
        Returns:
            List of crash information
        """
        crashes = []
        
        if session_log_dir.exists():
            log_files = list(session_log_dir.glob("*.log"))
            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        file_crashes = self._parse_crash_log(content)
                        for crash in file_crashes:
                            crash["source"] = log_file.name
                            crashes.append(crash)
                except Exception:
                    continue
        
        return crashes

    @staticmethod
    def _get_session_logs_content(session_log_dir: Path, max_content_length: int = 2000) -> Dict:
        """Internal method: Get session log content
        
        Args:
            session_log_dir: Session log directory
            max_content_length: Maximum content length
            
        Returns:
            Log content dictionary
        """
        logs_info = {"logs": {}}
        log_file = session_log_dir / "fastbot_test.log"
        
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logs_info["logs"]["fastbot_test.log"] = {
                        "content": content[-max_content_length:] if len(content) > max_content_length else content,
                        "size": len(content),
                        "lines": len(content.split('\n'))
                    }
            except Exception:
                logs_info["logs"]["fastbot_test.log"] = {"error": "Failed to read log file"}
        
        return logs_info

    def _cleanup_old_logs_internal(self, days_threshold: int = 7, confirm: bool = False) -> Dict:
        """Internal method: Clean up old logs"""
        try:
            if not self.logs_dir.exists():
                return {"status": "success", "cleaned_sessions": 0, "freed_space_mb": 0}

            cutoff_time = datetime.now() - timedelta(days=days_threshold)
            sessions_to_delete = []
            total_size_to_delete = 0

            for session_dir in self.logs_dir.iterdir():
                if session_dir.is_dir():
                    modified_time = datetime.fromtimestamp(session_dir.stat().st_mtime)
                    if modified_time < cutoff_time:
                        session_size = sum(f.stat().st_size for f in session_dir.rglob('*') if f.is_file())
                        sessions_to_delete.append({"path": session_dir, "size": session_size})
                        total_size_to_delete += session_size

            if not confirm or not sessions_to_delete:
                return {"status": "success", "cleaned_sessions": 0, "freed_space_mb": 0}

            deleted_sessions = []
            for session_info in sessions_to_delete:
                try:
                    shutil.rmtree(session_info["path"])
                    deleted_sessions.append(session_info["path"].name)
                except Exception:
                    continue

            return {
                "status": "success",
                "cleaned_sessions": len(deleted_sessions),
                "freed_space_mb": round(total_size_to_delete / (1024 * 1024), 2)
            }
        except Exception:
            return {"status": "error", "cleaned_sessions": 0, "freed_space_mb": 0}

    def _register_tools(self):
        """Register tools"""

        @self.mcp.tool()
        def get_available_devices() -> str:
            """
            Get list of currently available Android devices

            Returns:
                Detailed information of available devices, including device ID, status, model, etc.
            """
            success, output = self._run_adb_command(["devices", "-l"])

            if not success:
                return json.dumps({
                    "status": "error",
                    "message": "Failed to get device list",
                    "error": output
                }, ensure_ascii=False, indent=2)

            devices = []
            lines = output.split('\n')[1:]  # Skip first line header

            for line in lines:
                if line.strip() and not line.startswith('*'):
                    parts = line.split()
                    if len(parts) >= 2:
                        device_id = parts[0]
                        status = parts[1]

                        # Get device detailed information
                        if status == "device":
                            # Get device properties
                            model_success, model = self._run_adb_command(
                                ["shell", "getprop", "ro.product.model"], device_id
                            )
                            brand_success, brand = self._run_adb_command(
                                ["shell", "getprop", "ro.product.brand"], device_id
                            )
                            version_success, version = self._run_adb_command(
                                ["shell", "getprop", "ro.build.version.release"], device_id
                            )

                            devices.append({
                                "device_id": device_id,
                                "status": status,
                                "model": model if model_success else "Unknown",
                                "brand": brand if brand_success else "Unknown",
                                "android_version": version if version_success else "Unknown"
                            })
                        else:
                            devices.append({
                                "device_id": device_id,
                                "status": status,
                                "model": "N/A",
                                "brand": "N/A",
                                "android_version": "N/A"
                            })

            return json.dumps({
                "status": "success",
                "message": f"Found {len(devices)} devices",
                "devices": devices
            }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def get_apk_package_info(apk_path: str) -> str:
            """
            Get APK package name and basic information from APK file

            Args:
                apk_path: APK file path

            Returns:
                APK package name and related information
            """
            # Verify APK file exists
            if not os.path.exists(apk_path):
                return json.dumps({
                    "status": "error",
                    "message": "APK file does not exist",
                    "apk_path": apk_path
                }, ensure_ascii=False, indent=2)

            try:
                # Parse APK file using apkutils2 library
                apk = APK(apk_path)
                manifest = apk.get_manifest()
                
                # Get basic APK information
                apk_info = {
                    "apk_path": apk_path,
                    "file_size_mb": round(os.path.getsize(apk_path) / (1024 * 1024), 2)
                }
                
                if not isinstance(manifest, dict):
                    return json.dumps({
                        "status": "error",
                        "message": "Failed to parse APK Manifest file",
                        "apk_path": apk_path
                    }, ensure_ascii=False, indent=2)
                
                # Get package name
                package_name = manifest.get('@package')
                if package_name:
                    apk_info["package_name"] = package_name
                else:
                    return json.dumps({
                        "status": "error",
                        "message": "Failed to extract package name from APK file",
                        "apk_path": apk_path
                    }, ensure_ascii=False, indent=2)
                
                # Get version information
                version_name = manifest.get('@android:versionName')
                if version_name:
                    apk_info["version_name"] = version_name
                
                version_code = manifest.get('@android:versionCode')
                if version_code:
                    apk_info["version_code"] = str(version_code)
                
                # Get compile SDK version
                compile_sdk = manifest.get('@android:compileSdkVersion')
                if compile_sdk:
                    apk_info["compile_sdk_version"] = str(compile_sdk)
                
                # Get uses-sdk information
                uses_sdk = manifest.get('uses-sdk', {})
                if isinstance(uses_sdk, dict):
                    min_sdk = uses_sdk.get('@android:minSdkVersion')
                    target_sdk = uses_sdk.get('@android:targetSdkVersion')
                    if min_sdk:
                        apk_info["min_sdk_version"] = str(min_sdk)
                    if target_sdk:
                        apk_info["target_sdk_version"] = str(target_sdk)
                
                # Get application information
                application = manifest.get('application', {})
                if isinstance(application, dict):
                    app_label = application.get('@android:label')
                    if app_label:
                        apk_info["app_label"] = app_label
                    
                    app_name = application.get('@android:name')
                    if app_name:
                        apk_info["app_name"] = app_name
                    
                    # Get main Activity
                    activities = application.get('activity', [])
                    if not isinstance(activities, list):
                        activities = [activities]
                    
                    main_activity = None
                    for activity in activities:
                        if isinstance(activity, dict):
                            intent_filters = activity.get('intent-filter', [])
                            if not isinstance(intent_filters, list):
                                intent_filters = [intent_filters]
                            
                            for intent_filter in intent_filters:
                                if isinstance(intent_filter, dict):
                                    action = intent_filter.get('action', {})
                                    category = intent_filter.get('category', {})
                                    
                                    # Check if it's MAIN action and LAUNCHER category
                                    if (isinstance(action, dict) and 
                                        action.get('@android:name') == 'android.intent.action.MAIN' and
                                        isinstance(category, dict) and
                                        category.get('@android:name') == 'android.intent.category.LAUNCHER'):
                                        main_activity = activity.get('@android:name')
                                        break
                            
                            if main_activity:
                                break
                    
                    if main_activity:
                        apk_info["main_activity"] = main_activity
                
                # Get permission list (limit to first 10)
                permissions = manifest.get('uses-permission', [])
                if not isinstance(permissions, list):
                    permissions = [permissions]
                
                permission_list = []
                for perm in permissions[:10]:
                    if isinstance(perm, dict):
                        perm_name = perm.get('@android:name')
                        if perm_name:
                            permission_list.append(perm_name)
                
                if permission_list:
                    apk_info["permissions"] = permission_list
                    apk_info["total_permissions"] = len(permissions)
                
                return json.dumps({
                    "status": "success",
                    "message": "Successfully obtained APK package name information",
                    "apk_info": apk_info
                }, ensure_ascii=False, indent=2)
                
            except ImportError:
                return json.dumps({
                    "status": "error",
                    "message": "Missing apkutils2 library, please install: pip install apkutils2",
                    "apk_path": apk_path
                }, ensure_ascii=False, indent=2)
            except Exception as e:
                # If apkutils2 fails, try fallback methods
                try:
                    # Fallback method 1: Use aapt tool (if available)
                    result = subprocess.run([
                        "aapt", "dump", "badging", apk_path
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        aapt_output = result.stdout
                        
                        # Parse aapt output
                        import re
                        name_match = re.search(r"package: name='([^']+)'", aapt_output)
                        if name_match:
                            package_name = name_match.group(1)
                            
                            # Extract other information
                            apk_info = {
                                "apk_path": apk_path,
                                "package_name": package_name,
                                "file_size_mb": round(os.path.getsize(apk_path) / (1024 * 1024), 2),
                                "extraction_method": "aapt_fallback"
                            }
                            
                            # Try to extract version information
                            version_code_match = re.search(r"versionCode='([^']+)'", aapt_output)
                            version_name_match = re.search(r"versionName='([^']+)'", aapt_output)
                            
                            if version_code_match:
                                apk_info["version_code"] = version_code_match.group(1)
                            if version_name_match:
                                apk_info["version_name"] = version_name_match.group(1)
                            
                            return json.dumps({
                                "status": "success",
                                "message": "Successfully obtained APK package name using aapt fallback method",
                                "apk_info": apk_info
                            }, ensure_ascii=False, indent=2)
                
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass
                
                # Fallback method 2: Try using adb install dry-run
                try:
                    success, install_output = self._run_adb_command([
                        "install", "-t", "--dry-run", apk_path
                    ])
                    
                    if success and "Success" in install_output:
                        return json.dumps({
                            "status": "partial_success",
                            "message": "APK file is valid, but detailed package name information cannot be extracted",
                            "apk_path": apk_path,
                            "file_size_mb": round(os.path.getsize(apk_path) / (1024 * 1024), 2),
                            "suggestion": "APK file format is correct, can query package name through device after installation",
                            "error_details": f"Primary parsing method failed: {str(e)}"
                        }, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to get APK package name: {str(e)}",
                    "apk_path": apk_path,
                    "file_size_mb": round(os.path.getsize(apk_path) / (1024 * 1024), 2),
                    "suggestions": [
                        "Ensure APK file is complete and not corrupted",
                        "Try installing apkutils2 library: pip install apkutils2",
                        "Or install APK first and query package name through device"
                    ]
                }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def install_apk(device_id: str, apk_path: str, force_install: bool = True) -> str:
            """
            Install APK to specified device

            Args:
                device_id: Target device ID
                apk_path: APK file path
                force_install: Whether to force installation (supports overwrite and downgrade), default True

            Returns:
                Installation result information
            """
            # Verify APK file exists
            if not os.path.exists(apk_path):
                return json.dumps({
                    "status": "error",
                    "message": "APK file does not exist",
                    "apk_path": apk_path
                }, ensure_ascii=False, indent=2)

            # Verify device is available
            success, output = self._run_adb_command(["get-state"], device_id)
            if not success or output != "device":
                return json.dumps({
                    "status": "error",
                    "message": "Device is unavailable or not connected",
                    "device_id": device_id,
                    "device_state": output
                }, ensure_ascii=False, indent=2)

            # Build installation command parameters
            install_args = ["install"]
            if force_install:
                install_args.extend(["-r", "-d"])  # -r: Replace existing app, -d: Allow downgrade installation
                install_args.append("-t")  # -t: Allow installing test APK
            
            install_args.append(apk_path)

            # Install APK
            success, output = self._run_adb_command(install_args, device_id)

            if success and "Success" in output:
                # Try to get package name (optional, for installation confirmation)
                try:
                    # Look for package from recently installed packages
                    package_success, package_list = self._run_adb_command([
                        "shell", "pm", "list", "packages", "-f"
                    ], device_id)
                    
                    installed_package = "Unknown"
                    if package_success:
                        # Simple parsing to get recently installed package name
                        lines = package_list.split('\n')
                        for line in lines:
                            if apk_path.split('/')[-1].replace('.apk', '') in line:
                                if 'package:' in line and '=' in line:
                                    installed_package = line.split('=')[-1]
                                    break
                except Exception as e:
                    installed_package = f"Unknown exception: {str(e)}"

                return json.dumps({
                    "status": "success",
                    "message": "APK installation successful",
                    "device_id": device_id,
                    "apk_path": apk_path,
                    "force_install": force_install,
                    "installed_package": installed_package,
                    "install_output": output,
                    "install_flags": "Force overwrite installation (supports downgrade)" if force_install else "Standard installation"
                }, ensure_ascii=False, indent=2)
            else:
                # Provide more detailed error information and suggestions when installation fails
                error_suggestions = []
                
                if "INSTALL_FAILED_VERSION_DOWNGRADE" in output:
                    error_suggestions.append("Version downgrade failed, suggest setting force_install=True")
                elif "INSTALL_FAILED_ALREADY_EXISTS" in output:
                    error_suggestions.append("App already exists, suggest setting force_install=True for overwrite installation")
                elif "INSTALL_FAILED_INSUFFICIENT_STORAGE" in output:
                    error_suggestions.append("Insufficient storage space, please clean device storage space")
                elif "INSTALL_FAILED_INVALID_APK" in output:
                    error_suggestions.append("Invalid APK file, please check APK file integrity")
                elif "INSTALL_FAILED_INCOMPATIBLE_SDK" in output:
                    error_suggestions.append("SDK version incompatible, please check app's minimum SDK requirements")
                else:
                    error_suggestions.append("Please check APK file and device status")
                
                return json.dumps({
                    "status": "error",
                    "message": "APK installation failed",
                    "device_id": device_id,
                    "apk_path": apk_path,
                    "force_install": force_install,
                    "error": output,
                    "error_suggestions": error_suggestions,
                    "retry_suggestion": "If it's a version issue, try setting force_install=True"
                }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def generate_test_session_id() -> str:
            """
            Generate unique identifier for test session

            Returns:
                Unique test session ID
            """
            session_id = self._generate_session_id()
            return json.dumps({
                "status": "success",
                "session_id": session_id,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "message": "Test session ID generated successfully"
            }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def start_stability_test(
            device_id: str,
            package_name: str,
            session_id: str,
            duration_minutes: int = 30,
            throttle_ms: int = 300,
            output_directory: Optional[str] = None
        ) -> str:
            """
            Start Android app stability testing

            Args:
                device_id: Target device ID
                package_name: Package name of app to test
                session_id: Test session ID
                duration_minutes: Test duration (minutes), default 30 minutes
                throttle_ms: Operation interval time (milliseconds), default 300ms
                output_directory: Output directory path, default to session-specific directory

            Returns:
                Test start result information
            """
            try:
                # [LOCK] Multi-client protection: Try to acquire device lock
                if not self._acquire_device_lock(device_id, session_id):
                    device_status = self._get_device_lock_status(device_id)
                    return json.dumps({
                        "status": "error",
                        "error_code": "DEVICE_BUSY",
                        "message": f"Device {device_id} is currently occupied by another test",
                        "device_status": device_status,
                        "suggestion": "Please wait for current test to complete or select another device"
                    }, ensure_ascii=False, indent=2)

                # Verify device status
                success, output = self._run_adb_command(["get-state"], device_id)
                if not success or output != "device":
                    # Release device lock (because device is unavailable)
                    self._release_device_lock(device_id, session_id)
                    return json.dumps({
                        "status": "error",
                        "message": "Device unavailable",
                        "device_id": device_id
                    }, ensure_ascii=False, indent=2)

                # Set output directory
                if not output_directory:
                    output_directory = f"/sdcard/fastbot_{session_id}"

                # Create session log directory
                session_log_dir = self.logs_dir / session_id
                session_log_dir.mkdir(exist_ok=True)

                # Push Fastbot files to device
                push_commands = [
                    (str(self.monkeyq_jar), "/sdcard/monkeyq.jar"),
                    (str(self.framework_jar), "/sdcard/framework.jar"),
                    (str(self.thirdpart_jar), "/sdcard/fastbot-thirdpart.jar")
                ]

                for local_path, remote_path in push_commands:
                    if os.path.exists(local_path):
                        push_success, push_output = self._run_adb_command([
                            "push", local_path, remote_path
                        ], device_id)

                        if not push_success:
                            return json.dumps({
                                "status": "error",
                                "message": f"Failed to push file: {remote_path}",
                                "error": push_output
                            }, ensure_ascii=False, indent=2)

                # Push libs directory (if exists)
                libs_dir = self.fastbot_dir / "libs"
                if libs_dir.exists():
                    for lib_file in libs_dir.glob("*"):
                        if lib_file.is_file():
                            push_success, push_output = self._run_adb_command([
                                "push", str(lib_file), f"/data/local/tmp/{lib_file.name}"
                            ], device_id)

                # Build Fastbot test command
                fastbot_cmd = [
                    "shell",
                    "CLASSPATH=/sdcard/monkeyq.jar:/sdcard/framework.jar:/sdcard/fastbot-thirdpart.jar",
                    "exec", "app_process", "/system/bin",
                    "com.android.commands.monkey.Monkey",
                    "-p", package_name,
                    "--agent", "reuseq",
                    "--running-minutes", str(duration_minutes),
                    "--throttle", str(throttle_ms),
                    "--output-directory", output_directory,
                    "--bugreport",
                    "-v", "-v"
                ]

                # Record test configuration
                test_config = {
                    "session_id": session_id,
                    "device_id": device_id,
                    "package_name": package_name,
                    "duration_minutes": duration_minutes,
                    "throttle_ms": throttle_ms,
                    "output_directory": output_directory,
                    "start_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "log_file": str(session_log_dir / "fastbot_test.log"),
                    "command": " ".join(fastbot_cmd)
                }

                config_file = session_log_dir / "test_config.json"
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(test_config, f, ensure_ascii=False, indent=2)  # type: ignore

                # Actually start test (asynchronous execution)
                def run_test():
                    """Run test in background thread"""
                    try:
                        log_file = session_log_dir / "fastbot_test.log"

                        # Build complete adb command
                        full_cmd = ["adb", "-s", device_id] + fastbot_cmd

                        # Start process and redirect output to log file
                        with open(log_file, 'w', encoding='utf-8') as f:
                            process = subprocess.Popen(
                                full_cmd,
                                stdout=f,
                                stderr=subprocess.STDOUT,
                                text=True
                            )

                            # Record process ID to configuration
                            test_config["process_id"] = process.pid
                            test_config["process_started"] = True

                            # Update configuration file
                            with open(config_file, 'w', encoding='utf-8') as config_f:
                                json.dump(test_config, config_f, ensure_ascii=False, indent=2)  # type: ignore

                            # Wait for process to complete
                            process.wait()

                            # Record completion status
                            test_config["end_time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            test_config["exit_code"] = process.returncode
                            test_config["process_completed"] = True

                            with open(config_file, 'w', encoding='utf-8') as config_f:
                                json.dump(test_config, config_f, ensure_ascii=False, indent=2)  # type: ignore

                    except Exception as e:
                        # Record error
                        error_log = session_log_dir / "error.log"
                        with open(error_log, 'w', encoding='utf-8') as f:
                            f.write(f"Test execution error: {str(e)}\n")
                            f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    
                    finally:
                        # [UNLOCK] Release device lock after test completion
                        self._release_device_lock(device_id, session_id)

                # Start background test thread
                test_thread = threading.Thread(target=run_test, daemon=True)
                test_thread.start()

                return json.dumps({
                    "status": "success",
                    "message": "Fastbot stability test started",
                    "session_id": session_id,
                    "device_id": device_id,
                    "package_name": package_name,
                    "duration_minutes": duration_minutes,
                    "throttle_ms": throttle_ms,
                    "output_directory": output_directory,
                    "log_directory": str(session_log_dir),
                    "config": test_config
                }, ensure_ascii=False, indent=2)

            except Exception as e:
                # [UNLOCK] Release device lock when startup fails
                self._release_device_lock(device_id, session_id)
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to start stability test: {str(e)}",
                    "session_id": session_id
                }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def get_test_logs(session_id: str) -> str:
            """
            Get test logs for specified session

            Args:
                session_id: Test session ID

            Returns:
                Test log content and summary information
            """
            # Use common method to read configuration
            config, session_log_dir = self._read_session_config(session_id)

            if not session_log_dir.exists():
                return json.dumps({
                    "status": "error",
                    "message": "Test session does not exist",
                    "session_id": session_id
                }, ensure_ascii=False, indent=2)

            logs = {}
            log_files = list(session_log_dir.glob("*.log"))

            for log_file in log_files[:5]:  # Limit to maximum 5 log files
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        logs[log_file.name] = {
                            "size": len(content),
                            "lines": len(content.split('\n')),
                            "content": content[-2000:] if len(content) > 2000 else content  # Only return last 2000 characters
                        }
                except Exception as e:
                    logs[log_file.name] = {
                        "error": f"Failed to read log file: {str(e)}"
                    }

            return json.dumps({
                "status": "success",
                "session_id": session_id,
                "log_directory": str(session_log_dir),
                "config": config,
                "log_files": list(logs.keys()),
                "logs": logs
            }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def extract_crash_logs(session_id: str, device_id: Optional[str] = None) -> str:
            """
            Extract and analyze crash logs (ANR, Crash, and other exceptions)

            Args:
                session_id: Test session ID
                device_id: Device ID (optional, for getting real-time logs)

            Returns:
                Crash log analysis results
            """
            session_log_dir = self.logs_dir / session_id
            crashes = []

            # Extract crash information from local log files
            if session_log_dir.exists():
                log_files = list(session_log_dir.glob("*.log"))

                for log_file in log_files:
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            file_crashes = self._parse_crash_log(content)
                            for crash in file_crashes:
                                crash["source"] = log_file.name
                                crashes.append(crash)
                    except Exception as e:
                        crashes.append({
                            "type": "error",
                            "source": log_file.name,
                            "message": f"Failed to parse log file: {str(e)}"
                        })

            # If device ID is provided, try to get latest crash logs from device
            if device_id:
                try:
                    # Get crash-dump.log from device
                    success, crash_content = self._run_adb_command([
                        "shell", "cat", "/sdcard/crash-dump.log"
                    ], device_id)

                    if success and crash_content.strip():
                        device_crashes = self._parse_crash_log(crash_content)
                        for crash in device_crashes:
                            crash["source"] = "device_crash_dump"
                            crash["device_id"] = device_id
                            crashes.append(crash)

                    # Get ANR traces
                    success, anr_content = self._run_adb_command([
                        "shell", "cat", "/sdcard/oom-traces.log"
                    ], device_id)

                    if success and anr_content.strip():
                        anr_crashes = self._parse_crash_log(anr_content)
                        for crash in anr_crashes:
                            crash["source"] = "device_anr_traces"
                            crash["device_id"] = device_id
                            crashes.append(crash)

                except Exception as e:
                    crashes.append({
                        "type": "error",
                        "source": "device_extraction",
                        "message": f"Failed to extract logs from device: {str(e)}"
                    })

            # Count crash types
            crash_summary = {}
            for crash in crashes:
                crash_type = crash.get("type", "unknown")
                crash_summary[crash_type] = crash_summary.get(crash_type, 0) + 1

            return json.dumps({
                "status": "success",
                "session_id": session_id,
                "device_id": device_id,
                "total_crashes": len(crashes),
                "crash_summary": crash_summary,
                "crashes": crashes[:20]  # Limit to first 20 crashes
            }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def get_device_system_info(device_id: str) -> str:
            """
            Get device system information

            Args:
                device_id: Device ID

            Returns:
                Detailed device system information
            """
            try:
                # Collect device information
                info_commands = {
                    "model": ["shell", "getprop", "ro.product.model"],
                    "brand": ["shell", "getprop", "ro.product.brand"],
                    "manufacturer": ["shell", "getprop", "ro.product.manufacturer"],
                    "android_version": ["shell", "getprop", "ro.build.version.release"],
                    "api_level": ["shell", "getprop", "ro.build.version.sdk"],
                    "build_id": ["shell", "getprop", "ro.build.id"],
                    "serial": ["shell", "getprop", "ro.serialno"],
                    "cpu_abi": ["shell", "getprop", "ro.product.cpu.abi"],
                    "density": ["shell", "wm", "density"],
                    "size": ["shell", "wm", "size"]
                }

                device_info = {"device_id": device_id}

                for key, cmd in info_commands.items():
                    success, output = self._run_adb_command(cmd, device_id)
                    device_info[key] = output if success else "Unknown"

                # Get list of installed apps (first 20)
                success, packages = self._run_adb_command([
                    "shell", "pm", "list", "packages", "-3"
                ], device_id)

                if success:
                    package_list = packages.split('\n')[:20]
                    device_info["installed_packages"] = [
                        pkg.replace("package:", "") for pkg in package_list if pkg.startswith("package:")
                    ]
                else:
                    device_info["installed_packages"] = []

                return json.dumps({
                    "status": "success",
                    "device_info": device_info
                }, ensure_ascii=False, indent=2)

            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to get device information: {str(e)}",
                    "device_id": device_id
                }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def stop_test_session(device_id: str, session_id: str) -> str:
            """
            Stop test session on specified device

            Args:
                device_id: Device ID
                session_id: Test session ID

            Returns:
                Stop operation result
            """
            try:
                # Find and stop monkey process
                success, processes = self._run_adb_command([
                    "shell", "ps", "|", "grep", "monkey"
                ], device_id)

                if success and processes:
                    # Try to kill monkey process
                    kill_success, kill_output = self._run_adb_command([
                        "shell", "pkill", "-f", "monkey"
                    ], device_id)

                    # Record stop time
                    session_log_dir = self.logs_dir / session_id
                    if session_log_dir.exists():
                        stop_info = {
                            "session_id": session_id,
                            "device_id": device_id,
                            "stop_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "stop_method": "manual",
                            "processes_found": processes,
                            "kill_result": kill_output if kill_success else "Failed"
                        }

                        stop_file = session_log_dir / "stop_info.json"
                        with open(stop_file, 'w', encoding='utf-8') as f:
                            json.dump(stop_info, f, ensure_ascii=False, indent=2)  # type: ignore

                    # [UNLOCK] Release device lock when manually stopping
                    self._release_device_lock(device_id, session_id)

                    return json.dumps({
                        "status": "success",
                        "message": "Test session stopped",
                        "session_id": session_id,
                        "device_id": device_id,
                        "processes_killed": processes
                    }, ensure_ascii=False, indent=2)
                else:
                    # [UNLOCK] Try to release device lock even if no process is found
                    self._release_device_lock(device_id, session_id)
                    
                    return json.dumps({
                        "status": "info",
                        "message": "No running monkey process found",
                        "session_id": session_id,
                        "device_id": device_id
                    }, ensure_ascii=False, indent=2)

            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to stop test session: {str(e)}",
                    "session_id": session_id,
                    "device_id": device_id
                }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def get_test_coverage(device_id: str, package_name: str) -> str:
            """
            Get application test coverage information

            Args:
                device_id: Device ID
                package_name: Application package name

            Returns:
                Test coverage information
            """
            try:
                # Get application Activity list
                success, activities = self._run_adb_command([
                    "shell", "dumpsys", "package", package_name, "|", "grep", "Activity"
                ], device_id)

                if not success:
                    return json.dumps({
                        "status": "error",
                        "message": "Failed to get application Activity information",
                        "package_name": package_name,
                        "device_id": device_id
                    }, ensure_ascii=False, indent=2)

                # Parse Activity information
                activity_lines = [line.strip() for line in activities.split('\n') if 'Activity' in line]
                total_activities = len(activity_lines)

                # Get currently running Activity
                success, current_activity = self._run_adb_command([
                    "shell", "dumpsys", "activity", "activities", "|", "grep", "mResumedActivity"
                ], device_id)

                coverage_info = {
                    "package_name": package_name,
                    "device_id": device_id,
                    "total_activities": total_activities,
                    "activities": activity_lines[:10],  # Limit to first 10
                    "current_activity": current_activity if success else "Unknown",
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                return json.dumps({
                    "status": "success",
                    "coverage_info": coverage_info
                }, ensure_ascii=False, indent=2)

            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to get test coverage: {str(e)}",
                    "package_name": package_name,
                    "device_id": device_id
                }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def list_test_sessions() -> str:
            """
            List all test sessions

            Returns:
                List and basic information of all test sessions
            """
            try:
                if not self.logs_dir.exists():
                    return json.dumps({
                        "status": "success",
                        "message": "Log directory does not exist",
                        "sessions": [],
                        "total_sessions": 0
                    }, ensure_ascii=False, indent=2)

                sessions = []
                session_dirs = [d for d in self.logs_dir.iterdir() if d.is_dir()]

                for session_dir in session_dirs:
                    session_info = {
                        "session_id": session_dir.name,
                        "created_time": datetime.fromtimestamp(session_dir.stat().st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                        "modified_time": datetime.fromtimestamp(session_dir.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    }

                    # Read configuration file information
                    config_file = session_dir / "test_config.json"
                    if config_file.exists():
                        try:
                            with open(config_file, 'r', encoding='utf-8') as f:
                                config = json.load(f)
                                session_info.update({
                                    "device_id": config.get("device_id"),
                                    "package_name": config.get("package_name"),
                                    "duration_minutes": config.get("duration_minutes"),
                                    "start_time": config.get("start_time")
                                })
                        except Exception:
                            pass

                    # Calculate directory size
                    total_size = sum(f.stat().st_size for f in session_dir.rglob('*') if f.is_file())
                    session_info["size_bytes"] = total_size
                    session_info["size_mb"] = round(total_size / (1024 * 1024), 2)

                    # Calculate file count
                    file_count = len([f for f in session_dir.rglob('*') if f.is_file()])
                    session_info["file_count"] = file_count

                    sessions.append(session_info)

                # Sort by creation time (newest first)
                sessions.sort(key=lambda x: x["created_time"], reverse=True)

                return json.dumps({
                    "status": "success",
                    "total_sessions": len(sessions),
                    "sessions": sessions
                }, ensure_ascii=False, indent=2)

            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to list test sessions: {str(e)}"
                }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def get_logs_storage_info() -> str:
            """
            Get log storage usage statistics

            Returns:
                Detailed storage statistics for logs
            """
            try:
                if not self.logs_dir.exists():
                    return json.dumps({
                        "status": "success",
                        "message": "Log directory does not exist",
                        "storage_info": {
                            "total_size_bytes": 0,
                            "total_size_mb": 0,
                            "total_sessions": 0,
                            "total_files": 0
                        }
                    }, ensure_ascii=False, indent=2)

                total_size = 0
                total_files = 0
                session_count = 0

                # Count all session directories
                for session_dir in self.logs_dir.iterdir():
                    if session_dir.is_dir():
                        session_count += 1
                        for file_path in session_dir.rglob('*'):
                            if file_path.is_file():
                                total_size += file_path.stat().st_size
                                total_files += 1

                # Get disk usage information
                total_disk, used_disk, free_disk = shutil.disk_usage(self.logs_dir)

                storage_info = {
                    "logs_directory": str(self.logs_dir),
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "total_size_gb": round(total_size / (1024 * 1024 * 1024), 3),
                    "total_sessions": session_count,
                    "total_files": total_files,
                    "average_session_size_mb": round(total_size / (1024 * 1024 * session_count), 2) if session_count > 0 else 0,
                    "disk_usage": {
                        "total_disk_gb": round(total_disk / (1024 * 1024 * 1024), 2),
                        "used_disk_gb": round(used_disk / (1024 * 1024 * 1024), 2),
                        "free_disk_gb": round(free_disk / (1024 * 1024 * 1024), 2),
                        "disk_usage_percentage": round((used_disk / total_disk) * 100, 2)
                    }
                }

                # Add suggestions
                suggestions = []
                if storage_info["total_size_mb"] > 100:
                    suggestions.append("Log files occupy over 100MB, suggest cleaning up old test sessions")
                if storage_info["total_sessions"] > 20:
                    suggestions.append("Too many test sessions, suggest deleting unnecessary sessions")
                if storage_info["disk_usage"]["disk_usage_percentage"] > 90:
                    suggestions.append("Disk usage exceeds 90%, strongly suggest cleaning up log files")

                return json.dumps({
                    "status": "success",
                    "storage_info": storage_info,
                    "suggestions": suggestions
                }, ensure_ascii=False, indent=2)

            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to get storage information: {str(e)}"
                }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def delete_session_logs(session_id: str, confirm: bool = False) -> str:
            """
            Delete log files for specified session

            Args:
                session_id: Test session ID to delete
                confirm: Confirm delete operation, default False (for safety)

            Returns:
                Delete operation result
            """
            try:
                session_dir = self.logs_dir / session_id

                if not session_dir.exists():
                    return json.dumps({
                        "status": "error",
                        "message": "Specified test session does not exist",
                        "session_id": session_id
                    }, ensure_ascii=False, indent=2)

                # Calculate file size and count to be deleted
                total_size = 0
                file_count = 0
                for file_path in session_dir.rglob('*'):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
                        file_count += 1

                if not confirm:
                    return json.dumps({
                        "status": "warning",
                        "message": "Delete operation requires confirmation",
                        "session_id": session_id,
                        "files_to_delete": file_count,
                        "size_to_delete_mb": round(total_size / (1024 * 1024), 2),
                        "instruction": "Please set confirm=True to confirm delete operation"
                    }, ensure_ascii=False, indent=2)

                # Execute deletion
                shutil.rmtree(session_dir)

                return json.dumps({
                    "status": "success",
                    "message": f"Successfully deleted test session {session_id}",
                    "session_id": session_id,
                    "deleted_files": file_count,
                    "freed_space_mb": round(total_size / (1024 * 1024), 2)
                }, ensure_ascii=False, indent=2)

            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to delete session logs: {str(e)}",
                    "session_id": session_id
                }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def cleanup_old_logs(days_threshold: int = 7, confirm: bool = False) -> str:
            """
            Clean up old log files before specified number of days

            Args:
                days_threshold: Retention days threshold, delete logs older than this number of days, default 7 days
                confirm: Confirm delete operation, default False (for safety)

            Returns:
                Cleanup operation result
            """
            try:
                if not self.logs_dir.exists():
                    return json.dumps({
                        "status": "success",
                        "message": "Log directory does not exist, no cleanup needed",
                        "cleaned_sessions": 0,
                        "freed_space_mb": 0
                    }, ensure_ascii=False, indent=2)

                cutoff_time = datetime.now() - timedelta(days=days_threshold)

                # Find sessions that need to be deleted
                sessions_to_delete = []
                total_size_to_delete = 0
                total_files_to_delete = 0

                for session_dir in self.logs_dir.iterdir():
                    if session_dir.is_dir():
                        # Check directory modification time
                        modified_time = datetime.fromtimestamp(session_dir.stat().st_mtime)
                        if modified_time < cutoff_time:
                            # Calculate size of this session
                            session_size = 0
                            session_files = 0
                            for file_path in session_dir.rglob('*'):
                                if file_path.is_file():
                                    session_size += file_path.stat().st_size
                                    session_files += 1

                            sessions_to_delete.append({
                                "session_id": session_dir.name,
                                "modified_time": modified_time.strftime('%Y-%m-%d %H:%M:%S'),
                                "size_mb": round(session_size / (1024 * 1024), 2),
                                "file_count": session_files,
                                "path": session_dir
                            })

                            total_size_to_delete += session_size
                            total_files_to_delete += session_files

                if not sessions_to_delete:
                    return json.dumps({
                        "status": "success",
                        "message": f"No old log files found older than {days_threshold} days",
                        "days_threshold": days_threshold,
                        "cleaned_sessions": 0,
                        "freed_space_mb": 0
                    }, ensure_ascii=False, indent=2)

                if not confirm:
                    return json.dumps({
                        "status": "warning",
                        "message": "Cleanup operation requires confirmation",
                        "days_threshold": days_threshold,
                        "sessions_to_delete": len(sessions_to_delete),
                        "total_files_to_delete": total_files_to_delete,
                        "total_size_to_delete_mb": round(total_size_to_delete / (1024 * 1024), 2),
                        "sessions": [
                            {
                                "session_id": s["session_id"],
                                "modified_time": s["modified_time"],
                                "size_mb": s["size_mb"]
                            } for s in sessions_to_delete
                        ],
                        "instruction": "Please set confirm=True to confirm cleanup operation"
                    }, ensure_ascii=False, indent=2)

                # Execute deletion
                deleted_sessions = []
                for session_info in sessions_to_delete:
                    try:
                        shutil.rmtree(session_info["path"])
                        deleted_sessions.append(session_info["session_id"])
                    except Exception as e:
                        print(f"Failed to delete session {session_info['session_id']}: {e}")

                return json.dumps({
                    "status": "success",
                    "message": f"Successfully cleaned up {len(deleted_sessions)} test sessions older than {days_threshold} days",
                    "days_threshold": days_threshold,
                    "cleaned_sessions": len(deleted_sessions),
                    "freed_space_mb": round(total_size_to_delete / (1024 * 1024), 2),
                    "deleted_session_ids": deleted_sessions
                }, ensure_ascii=False, indent=2)

            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to clean up old logs: {str(e)}",
                    "days_threshold": days_threshold
                }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def get_test_status(device_id: str, session_id: str) -> str:
            """
            Get real-time status of test session (fix status determination issues)

            Args:
                device_id: Device ID
                session_id: Test session ID

            Returns:
                Accurate test status information
            """
            try:
                # Use common method to read configuration and log information
                config, session_log_dir = self._read_session_config(session_id)
                
                if not session_log_dir.exists():
                    return json.dumps({
                        "status": "error",
                        "message": "Test session does not exist",
                        "session_id": session_id
                    }, ensure_ascii=False, indent=2)

                # Use common method to get log file information
                log_info = self._get_log_file_info(session_log_dir)

                # Multiple status determination
                test_status = "unknown"
                status_reason = ""
                confidence = 0

                # 1. Check completion flag in configuration file
                if config.get("process_completed"):
                    test_status = "completed"
                    exit_code = config.get("exit_code", -1)
                    status_reason = f"Test completed, exit code: {exit_code}"
                    confidence = 95
                elif config.get("process_started"):
                    # 2. Check monkey process on device
                    success, processes = self._run_adb_command([
                        "shell", "ps", "|", "grep", "monkey"
                    ], device_id)
                    
                    if success and processes.strip():
                        test_status = "running"
                        status_reason = "monkey process is running"
                        confidence = 90
                    else:
                        # 3. Determine based on log file activity
                        if log_info["last_modified"]:
                            last_modified = datetime.fromisoformat(log_info["last_modified"])
                            seconds_since_update = (datetime.now() - last_modified).total_seconds()
                            
                            if seconds_since_update < 120:  # Updated within 2 minutes
                                test_status = "running"
                                status_reason = f"Log file updated {int(seconds_since_update)} seconds ago, may still be running"
                                confidence = 70
                            else:
                                test_status = "stopped"
                                status_reason = f"Log file stopped updating {int(seconds_since_update/60)} minutes ago, process may have ended"
                                confidence = 85
                        else:
                            test_status = "stopped"
                            status_reason = "No log file or process"
                            confidence = 60
                else:
                    test_status = "not_started"
                    status_reason = "Test not started or startup failed"
                    confidence = 80

                # Calculate runtime
                runtime_info = {}
                if config.get("start_time"):
                    start_time = datetime.fromisoformat(config["start_time"])
                    if config.get("end_time"):
                        end_time = datetime.fromisoformat(config["end_time"])
                        runtime_info["total_runtime_minutes"] = round((end_time - start_time).total_seconds() / 60, 2)
                        runtime_info["status"] = "completed"
                    else:
                        runtime_info["current_runtime_minutes"] = round((datetime.now() - start_time).total_seconds() / 60, 2)
                        runtime_info["expected_duration_minutes"] = config.get("duration_minutes", 30)
                        runtime_info["progress_percentage"] = min(100.0, round(
                            runtime_info["current_runtime_minutes"] / runtime_info["expected_duration_minutes"] * 100, 1
                        ))

                return json.dumps({
                    "status": "success",
                    "session_id": session_id,
                    "device_id": device_id,
                    "test_status": test_status,
                    "status_reason": status_reason,
                    "confidence_percentage": confidence,
                    "config": config,
                    "log_info": log_info,
                    "runtime_info": runtime_info,
                    "check_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }, ensure_ascii=False, indent=2)

            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to get test status: {str(e)}",
                    "session_id": session_id
                }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def pre_test_check(device_id: str, package_name: str, auto_cleanup: bool = False) -> str:
            """
            Smart pre-check and environment preparation before testing

            Args:
                device_id: Device ID
                package_name: Package name of app to test
                auto_cleanup: Whether to automatically clean up old logs older than 7 days

            Returns:
                Pre-check results and suggestions
            """
            try:
                checks = []
                warnings = []
                errors = []
                actions_taken = []

                # 1. Check device status
                success, device_state = self._run_adb_command(["get-state"], device_id)
                if success and device_state == "device":
                    checks.append("[OK] Device connection normal")
                else:
                    errors.append(f"[X] Device status abnormal: {device_state}")

                # 2. Check if app is installed
                success, packages = self._run_adb_command([
                    "shell", "pm", "list", "packages", package_name
                ], device_id)

                if success and package_name in packages:
                    checks.append("[OK] Target app installed")
                    
                    # Check if app is running
                    success, running_apps = self._run_adb_command([
                        "shell", "ps", "|", "grep", package_name
                    ], device_id)
                    
                    if success and running_apps.strip():
                        warnings.append(f"[!] App {package_name} is running, may affect testing")
                else:
                    errors.append(f"[X] App {package_name} not installed")

                # 3. Check storage space
                storage_info = self._get_storage_info_internal()
                if storage_info.get("status") == "success":
                    disk_usage = storage_info["storage_info"]["disk_usage"]["disk_usage_percentage"]
                    total_size_mb = storage_info["storage_info"]["total_size_mb"]
                    
                    if disk_usage > 90:
                        errors.append(f"[X] Disk usage {disk_usage}%, severely insufficient")
                    elif disk_usage > 80:
                        warnings.append(f"[!] Disk usage {disk_usage}%, suggest cleanup")
                    else:
                        checks.append(f"[OK] Sufficient disk space ({disk_usage}%)")
                    
                    if total_size_mb > 100:
                        warnings.append(f"[!] Test logs occupy {total_size_mb}MB space")

                # 4. Check old log count and auto cleanup
                sessions_info = self._list_sessions_internal()
                if sessions_info.get("status") == "success":
                    total_sessions = sessions_info.get("total_sessions", 0)
                    if total_sessions > 10:
                        warnings.append(f"[!] Found {total_sessions} test sessions")
                        
                        if auto_cleanup:
                            cleanup_result = self._cleanup_old_logs_internal(days_threshold=7, confirm=True)
                            if cleanup_result.get("status") == "success":
                                cleaned = cleanup_result.get("cleaned_sessions", 0)
                                freed_mb = cleanup_result.get("freed_space_mb", 0)
                                if cleaned > 0:
                                    actions_taken.append(f"[CLEAN] Automatically cleaned {cleaned} old sessions, freed {freed_mb}MB space")
                                    checks.append("[OK] Auto cleanup completed")
                                else:
                                    checks.append("[OK] No old logs to clean up")

                # 5. Check monkey process conflicts
                success, processes = self._run_adb_command([
                    "shell", "ps", "|", "grep", "monkey"
                ], device_id)

                if success and processes.strip():
                    warnings.append("[!] Found running monkey process, may affect testing")
                    # Try to stop conflicting process
                    kill_success, kill_output = self._run_adb_command([
                        "shell", "pkill", "-f", "monkey"
                    ], device_id)
                    if kill_success:
                        actions_taken.append("[TOOL] Stopped conflicting monkey process")
                else:
                    checks.append("[OK] No conflicting monkey processes")

                # 6. Check device performance status
                success, cpu_info = self._run_adb_command([
                    "shell", "cat", "/proc/loadavg"
                ], device_id)
                
                if success:
                    load_avg = float(cpu_info.split()[0])
                    if load_avg > 2.0:
                        warnings.append(f"[!] High device load: {load_avg}")
                    else:
                        checks.append(f"[OK] Normal device load: {load_avg}")

                # Summarize results
                overall_status = "ready" if not errors else "not_ready"
                recommendation = "Ready to start testing" if overall_status == "ready" else "Please resolve the above errors first"
                
                if warnings and overall_status == "ready":
                    recommendation += ", but please note the warning messages"

                return json.dumps({
                    "status": "success",
                    "overall_status": overall_status,
                    "device_id": device_id,
                    "package_name": package_name,
                    "summary": {
                        "checks_passed": len(checks),
                        "warnings_count": len(warnings),
                        "errors_count": len(errors),
                        "actions_taken": len(actions_taken)
                    },
                    "details": {
                        "checks": checks,
                        "warnings": warnings,
                        "errors": errors,
                        "actions_taken": actions_taken
                    },
                    "recommendation": recommendation,
                    "auto_cleanup_enabled": auto_cleanup
                }, ensure_ascii=False, indent=2)

            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Pre-check failed: {str(e)}",
                    "device_id": device_id,
                    "package_name": package_name
                }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def generate_comprehensive_report(session_id: str, suggest_cleanup: bool = True) -> str:
            """
            Generate comprehensive test analysis report

            Args:
                session_id: Test session ID
                suggest_cleanup: Whether to provide cleanup suggestions

            Returns:
                Detailed test analysis report
            """
            try:
                # Use common methods to get various data
                config, session_log_dir = self._read_session_config(session_id)
                log_info = self._get_log_file_info(session_log_dir)
                crashes = self._extract_session_crashes(session_log_dir)
                logs_info = self._get_session_logs_content(session_log_dir)

                # Calculate stability score
                base_score = 100
                deductions = []

                # Deduct points for crashes
                total_crashes = len(crashes)
                if total_crashes > 0:
                    crash_deduction = min(total_crashes * 10, 50)
                    base_score -= crash_deduction
                    deductions.append(f"Found {total_crashes} crashes, deduct {crash_deduction} points")

                # Deduct points for test completion status
                if config.get("exit_code") and config.get("exit_code") != 0:
                    base_score -= 20
                    deductions.append("Test ended abnormally, deduct 20 points")

                # Check runtime duration
                runtime_info = {}
                if config.get("start_time"):
                    start_time = datetime.fromisoformat(config["start_time"])
                    if config.get("end_time"):
                        end_time = datetime.fromisoformat(config["end_time"])
                        runtime_info["total_runtime_minutes"] = round((end_time - start_time).total_seconds() / 60, 2)
                        actual_duration = runtime_info["total_runtime_minutes"]
                        expected_duration = config.get("duration_minutes", 30)
                        if actual_duration < expected_duration * 0.8:
                            base_score -= 15
                            deductions.append("Test ended prematurely, deduct 15 points")

                # Grading system
                if base_score >= 95:
                    grade = "A+"
                elif base_score >= 90:
                    grade = "A"
                elif base_score >= 85:
                    grade = "B+"
                elif base_score >= 80:
                    grade = "B"
                elif base_score >= 70:
                    grade = "C"
                elif base_score >= 60:
                    grade = "D"
                else:
                    grade = "F"

                # Analyze test events
                test_events = 0
                error_events = 0
                for log_name, log_data in logs_info.get("logs", {}).items():
                    if "content" in log_data:
                        content = log_data["content"]
                        test_events += content.count("Sending") + content.count("Event")
                        error_events += content.count("ERROR") + content.count("Exception")

                success_rate = ((test_events - error_events) / test_events * 100) if test_events > 0 else 0

                # Get coverage information (simplified version)
                coverage_info = None
                if config.get("device_id") and config.get("package_name"):
                    coverage_info = {
                        "package_name": config.get("package_name"),
                        "device_id": config.get("device_id"),
                        "note": "Coverage analysis available via get_test_coverage tool"
                    }

                # Generate recommendations
                recommendations = []
                cleanup_suggestions = []

                if base_score >= 90:
                    recommendations.append("[DONE] App stability performance is excellent, ready for release")
                elif base_score >= 80:
                    recommendations.append("[OK] App stability is good, suggest further testing")
                elif base_score >= 60:
                    recommendations.append("[!] App stability is average, need to fix discovered issues")
                else:
                    recommendations.append("[X] App stability is poor, strongly suggest fixing and retesting")

                if total_crashes > 0:
                    recommendations.append(f"[BUG] Found {total_crashes} crashes, please check detailed logs")

                if success_rate < 90:
                    recommendations.append(f"[G] Operation success rate {success_rate:.1f}%, suggest optimizing app response performance")

                # Cleanup suggestions
                if suggest_cleanup:
                    session_size_mb = log_info.get("size_mb", 0)
                    
                    if session_size_mb > 10:
                        cleanup_suggestions.append(f"[D] Current test session occupies {session_size_mb}MB space")
                    
                    storage_info = self._get_storage_info_internal()
                    if storage_info.get("status") == "success":
                        total_sessions = storage_info["storage_info"]["total_sessions"]
                        total_size_mb = storage_info["storage_info"]["total_size_mb"]
                        
                        if total_sessions > 5:
                            cleanup_suggestions.append(f"[SAVE] Total of {total_sessions} test sessions, occupying {total_size_mb}MB")
                        
                        if total_size_mb > 100:
                            cleanup_suggestions.append("[CLEAN] Suggest cleaning up old logs older than 7 days to save space")
                            cleanup_suggestions.append("[TIP] Can use cleanup_old_logs(days_threshold=7, confirm=True) for cleanup")

                # Generate complete report
                report = {
                    "session_id": session_id,
                    "report_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "test_summary": {
                        "package_name": config.get("package_name"),
                        "device_id": config.get("device_id"),
                        "test_duration_minutes": config.get("duration_minutes"),
                        "actual_runtime_minutes": runtime_info.get("total_runtime_minutes"),
                        "test_status": "completed" if config.get("process_completed") else "unknown",
                        "exit_code": config.get("exit_code")
                    },
                    "stability_analysis": {
                        "stability_score": max(0, base_score),
                        "stability_grade": grade,
                        "total_crashes": total_crashes,
                        "crash_types": {},
                        "deductions": deductions
                    },
                    "performance_metrics": {
                        "total_test_events": test_events,
                        "error_events": error_events,
                        "success_rate_percentage": round(success_rate, 2),
                        "log_file_size_mb": log_info.get("size_mb", 0),
                        "log_lines_count": log_info.get("lines_count", 0)
                    },
                    "coverage_analysis": coverage_info,
                    "recommendations": recommendations,
                    "cleanup_suggestions": cleanup_suggestions if suggest_cleanup else []
                }

                # Save report to file
                report_file = session_log_dir / "comprehensive_report.json"
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)  # type: ignore

                return json.dumps({
                    "status": "success",
                    "message": "Comprehensive test report generated successfully",
                    "session_id": session_id,
                    "report_file": str(report_file),
                    "report": report
                }, ensure_ascii=False, indent=2)

            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to generate test report: {str(e)}",
                    "session_id": session_id
                }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def smart_cleanup_advisor() -> str:
            """
            AI-driven smart cleanup suggestions

            Returns:
                Smart cleanup suggestions and automated cleanup options
            """
            try:
                # Get storage information
                storage_info = self._get_storage_info_internal()
                if storage_info.get("status") != "success":
                    return json.dumps({
                        "status": "error",
                        "message": "Failed to get storage information"
                    }, ensure_ascii=False, indent=2)

                storage_data = storage_info["storage_info"]
                
                # Get session list
                sessions_info = self._list_sessions_internal()
                sessions = sessions_info.get("sessions", [])
                
                # Analyze cleanup suggestions
                recommendations = []
                auto_actions = []
                manual_actions = []
                
                # Disk space analysis
                disk_usage = storage_data["disk_usage"]["disk_usage_percentage"]
                total_size_mb = storage_data["total_size_mb"]
                total_sessions = storage_data["total_sessions"]
                
                if disk_usage > 90:
                    recommendations.append("[ALERT] Disk space severely insufficient, strongly suggest immediate cleanup")
                    auto_actions.append("Immediately clean up old logs older than 3 days")
                elif disk_usage > 80:
                    recommendations.append("[!] Disk space tight, suggest cleaning up old logs")
                    auto_actions.append("Clean up old logs older than 7 days")
                elif total_size_mb > 200:
                    recommendations.append("[SAVE] Test logs occupy significant space, suggest regular cleanup")
                    manual_actions.append("Consider cleaning up old logs older than 14 days")
                else:
                    recommendations.append("[OK] Sufficient storage space, no cleanup needed at the moment")
                
                # Session count analysis
                if total_sessions > 20:
                    recommendations.append(f"[G] Too many test sessions ({total_sessions}), suggest cleanup")
                    auto_actions.append("Clean up old sessions older than 30 days")
                elif total_sessions > 10:
                    recommendations.append(f"[G] Moderate number of test sessions ({total_sessions})")
                    manual_actions.append("Optional cleanup of unnecessary sessions")
                
                # Analyze sessions by time
                now = datetime.now()
                old_sessions = []
                recent_large_sessions = []
                
                for session in sessions:
                    try:
                        modified_time = datetime.fromisoformat(session["modified_time"])
                        days_old = (now - modified_time).days
                        size_mb = session.get("size_mb", 0)
                        
                        if days_old > 30:
                            old_sessions.append({
                                "session_id": session["session_id"],
                                "days_old": days_old,
                                "size_mb": size_mb,
                                "action": "auto_delete"
                            })
                        elif days_old > 7 and size_mb > 50:
                            recent_large_sessions.append({
                                "session_id": session["session_id"],
                                "days_old": days_old,
                                "size_mb": size_mb,
                                "action": "consider_delete"
                            })
                    except Exception:
                        continue
                
                # Generate specific suggestions
                cleanup_plan = {
                    "immediate_actions": [],
                    "recommended_actions": [],
                    "optional_actions": []
                }
                
                if old_sessions:
                    total_old_size = sum(s["size_mb"] for s in old_sessions)
                    cleanup_plan["immediate_actions"].append({
                        "action": "cleanup_old_logs",
                        "description": f"Automatically clean up {len(old_sessions)} sessions older than 30 days",
                        "space_to_free_mb": total_old_size,
                        "command": "cleanup_old_logs(days_threshold=30, confirm=True)"
                    })
                
                if recent_large_sessions:
                    total_large_size = sum(s["size_mb"] for s in recent_large_sessions)
                    cleanup_plan["recommended_actions"].append({
                        "action": "review_large_sessions",
                        "description": f"Review {len(recent_large_sessions)} large sessions ({total_large_size}MB)",
                        "sessions": recent_large_sessions[:5],  # Show only first 5
                        "command": "Manually review then use delete_session_logs(session_id, confirm=True)"
                    })
                
                if disk_usage < 70 and total_sessions < 10:
                    cleanup_plan["optional_actions"].append({
                        "action": "no_action_needed",
                        "description": "Current status is good, no cleanup needed",
                        "next_check": "Suggest checking again before next test"
                    })
                
                return json.dumps({
                    "status": "success",
                    "analysis": {
                        "disk_usage_percentage": disk_usage,
                        "total_size_mb": total_size_mb,
                        "total_sessions": total_sessions,
                        "old_sessions_count": len(old_sessions),
                        "large_sessions_count": len(recent_large_sessions)
                    },
                    "recommendations": recommendations,
                    "cleanup_plan": cleanup_plan,
                    "auto_cleanup_available": len(old_sessions) > 0,
                    "suggested_command": "cleanup_old_logs(days_threshold=7, confirm=True)" if auto_actions else None
                }, ensure_ascii=False, indent=2)
                
            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to generate cleanup suggestions: {str(e)}"
                }, ensure_ascii=False, indent=2)

        @self.mcp.tool()
        def get_devices_lock_status() -> str:
            """
            Get lock status and occupancy information for all devices
            
            Returns:
                Lock status information for all devices
            """
            try:
                # Get list of available devices
                success, devices_output = self._run_adb_command(["devices"])
                device_list = []
                
                if success:
                    lines = devices_output.strip().split('\n')[1:]  # Skip header line
                    for line in lines:
                        if line.strip() and '\t' in line:
                            device_id = line.split('\t')[0]
                            device_list.append(device_id)
                
                # Get lock status for each device
                devices_status = []
                for device_id in device_list:
                    status = self._get_device_lock_status(device_id)
                    devices_status.append(status)
                
                # Statistics
                total_devices = len(devices_status)
                locked_devices = len([d for d in devices_status if d["is_locked"]])
                available_devices = total_devices - locked_devices
                
                return json.dumps({
                    "status": "success",
                    "summary": {
                        "total_devices": total_devices,
                        "locked_devices": locked_devices,
                        "available_devices": available_devices
                    },
                    "devices": devices_status,
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }, ensure_ascii=False, indent=2)
                
            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to get device lock status: {str(e)}"
                }, ensure_ascii=False, indent=2)


fastbot_server = FastbotMCPServer()

if __name__ == "__main__":
    fastbot_server.run()
