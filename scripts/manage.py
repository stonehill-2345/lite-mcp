#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
# Third-party dependency check and import
try:
    import psutil
except ImportError:
    print("[X] Missing psutil dependency, please install: pip install psutil")
    sys.exit(1)

import os
from pathlib import Path

# Add project root directory to Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

import json
import time
import yaml
import random
import hashlib
import psutil
import platform
import subprocess
import traceback
import argparse
import threading
import requests
import socket
import urllib.request
import urllib.error
from rich.syntax import Syntax
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from src.core.utils import get_smart_port_for_service, get_local_ip, is_local_ip
from src.core.registry import ServerRegistry

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import track
    from rich.prompt import Confirm
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("[!] Recommended to install rich library for better display: pip install rich")

@dataclass
class ServerConfig:
    """Server configuration dataclass"""
    name: str
    server_type: str
    transport: str = "sse"
    host: str = "null"
    port: Optional[int] = None
    enabled: bool = True
    auto_restart: bool = True
    description: str = ""


class CrossPlatformManager:
    """Cross-platform MCP framework manager"""

    def __init__(self):
        # Project path settings
        self.project_dir = Path(__file__).parent.parent.resolve()
        self.config_file = self.project_dir / "config" / "servers.yaml"
        self.log_dir = self.project_dir / "runtime" / "logs"
        self.pid_dir = self.project_dir / "runtime" / "pids"
        self.registry_file = self.project_dir / "runtime" / "registry.json"

        # Create necessary directories
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.pid_dir.mkdir(parents=True, exist_ok=True)

        # Check Poetry environment
        self.use_poetry = self._check_poetry()

        # System information
        self.system = platform.system()
        self.is_windows = self.system == "Windows"

        # Rich console
        if RICH_AVAILABLE:
            self.console = Console()

        # Color and icon definitions
        self._setup_display()

        # Global configuration
        self.verbose = False

        self.error_count = 0
        self.warning_count = 0

        # Python command cache
        self._python_cmd = None

        # Monitor thread control
        self._monitor_stop_event = None
        self._monitor_thread = None

    @staticmethod
    def _check_poetry() -> bool:
        """Check if Poetry is available"""
        try:
            subprocess.run(["poetry", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _setup_display(self):
        """Setup display styles"""
        # Icon definitions (cross-platform compatible)
        self.icons = {
            'success': '[OK]',
            'error': '[X]',
            'warning': '[!]',
            'info': '[i]',
            'rocket': '>',
            'gear': '[#]',
            'server': '[S]',
            'network': '[N]',
            'shield': '[P]',
            'magnifying': '[?]',
            'lightning': '*',
            'clock': '[T]',
            'chart': '[G]',
            'terminal': '$',
            'fire': '[F]',
            'star': '*',
            'folder': '[D]',
            'file': '[F]',
            'summary': '[=]'
        }

        # ANSI color codes (supported by Windows Terminal and modern terminals)
        self.colors = {
            'red': '\033[0;31m',
            'green': '\033[0;32m',
            'yellow': '\033[0;33m',
            'blue': '\033[0;34m',
            'purple': '\033[0;35m',
            'cyan': '\033[0;36m',
            'white': '\033[0;37m',
            'bold': '\033[1m',
            'dim': '\033[2m',
            'reset': '\033[0m'
        }

    def log_success(self, message: str, detail: str = ""):
        """Success log"""
        if RICH_AVAILABLE:
            self.console.print(f"{self.icons['success']} {message}", style="bold green")
            if detail:
                self.console.print(f"   {detail}", style="dim green")
        else:
            print(f"{self.colors['green']}{self.colors['bold']}{self.icons['success']} {message}{self.colors['reset']}")
            if detail:
                print(f"{self.colors['dim']}{self.colors['green']}   {detail}{self.colors['reset']}")

    def log_error(self, message: str, detail: str = ""):
        """Error log"""
        # Increment error count if in health check
        if hasattr(self, 'error_count'):
            self.error_count += 1

        if RICH_AVAILABLE:
            self.console.print(f"{self.icons['error']} {message}", style="bold red")
            if detail:
                self.console.print(f"   {detail}", style="dim red")
        else:
            print(f"{self.colors['red']}{self.colors['bold']}{self.icons['error']} {message}{self.colors['reset']}")
            if detail:
                print(f"{self.colors['dim']}{self.colors['red']}   {detail}{self.colors['reset']}")

    def log_warning(self, message: str, detail: str = ""):
        """Warning log"""
        # Increment warning count if in health check
        if hasattr(self, 'warning_count'):
            self.warning_count += 1

        if RICH_AVAILABLE:
            self.console.print(f"{self.icons['warning']} {message}", style="bold yellow")
            if detail:
                self.console.print(f"   {detail}", style="dim yellow")
        else:
            print(
                f"{self.colors['yellow']}{self.colors['bold']}{self.icons['warning']} {message}{self.colors['reset']}")
            if detail:
                print(f"{self.colors['dim']}{self.colors['yellow']}   {detail}{self.colors['reset']}")

    def log_info(self, message: str, detail: str = ""):
        """Information log"""
        if RICH_AVAILABLE:
            self.console.print(f"{self.icons['info']} {message}", style="blue")
            if detail:
                self.console.print(f"   {detail}", style="dim blue")
        else:
            print(f"{self.colors['blue']}{self.icons['info']} {message}{self.colors['reset']}")
            if detail:
                print(f"{self.colors['dim']}{self.colors['blue']}   {detail}{self.colors['reset']}")

    def log_step(self, message: str, step_num: int = 0, total_steps: int = 0):
        """Step progress log"""
        if step_num and total_steps:
            prefix = f"[{step_num}/{total_steps}]"
        else:
            prefix = f"{self.icons['lightning']}"

        if RICH_AVAILABLE:
            self.console.print(f"{prefix} {message}", style="bold purple")
        else:
            print(f"{self.colors['purple']}{self.colors['bold']}{prefix} {message}{self.colors['reset']}")

    def log_debug(self, message: str):
        """Debug log"""
        if self.verbose:
            if RICH_AVAILABLE:
                self.console.print(f"[DEBUG] {message}", style="dim blue")
            else:
                print(f"{self.colors['dim']}{self.colors['blue']}[DEBUG] {message}{self.colors['reset']}")

    def show_header(self, title: str, subtitle: str = ""):
        """Display Beautified Headlines"""
        if RICH_AVAILABLE:
            panel_title = f"[bold white]{title}[/bold white]"
            if subtitle:
                panel_title += f"\n[dim]{subtitle}[/dim]"
            
            panel = Panel(
                panel_title,
                border_style="cyan",
                padding=(1, 2),
                width=80
            )
            self.console.print(panel)
        else:
            width = 80
            print()
            print(f"{self.colors['cyan']}{self.colors['bold']}{'─' * width}{self.colors['reset']}")
            print(f"{self.colors['cyan']}{self.colors['bold']}│{' ' * ((width - len(title)) // 2)}{title}{' ' * ((width - len(title)) // 2)}│{self.colors['reset']}")
            if subtitle:
                print(f"{self.colors['cyan']}│{' ' * ((width - len(subtitle)) // 2)}{subtitle}{' ' * ((width - len(subtitle)) // 2)}│{self.colors['reset']}")
            print(f"{self.colors['cyan']}{self.colors['bold']}{'─' * width}{self.colors['reset']}")
            print()
    
    def show_section(self, title: str, icon: str):
        """Display chapter titles"""
        if RICH_AVAILABLE:
            self.console.print(f"\n── {icon} {title} " + "─" * (60 - len(title)), style="bold purple")
        else:
            print(f"\n{self.colors['purple']}{self.colors['bold']}── {icon} {title} {'─' * (60 - len(title))}{self.colors['reset']}")

    def run_python(self, *args, **kwargs):
        """Execute Python command

        Args:
            *args: Command arguments
            **kwargs: Additional parameters like stdout, stderr etc.

        Returns:
            subprocess.CompletedProcess: Process execution result
        """
        # Set environment variables
        env = os.environ.copy()

        # Add project root to PYTHONPATH
        python_path = env.get("PYTHONPATH", "")
        if python_path:
            env["PYTHONPATH"] = f"{self.project_dir}:{python_path}"
        else:
            env["PYTHONPATH"] = str(self.project_dir)

        # Use Poetry's Python interpreter
        if self.use_poetry:
            python_cmd = ["poetry", "run", "python"]
        else:
            python_cmd = [sys.executable]

        # Build complete command
        cmd = python_cmd + list(args)

        # Start process
        return subprocess.Popen(
            cmd,
            cwd=self.project_dir,
            env=env,
            **kwargs
        )

    def _detect_python_command(self) -> str:
        """Detect available Python command in the system

        Returns:
            str: Available Python command ('python3', 'python' or None)
        """
        if self._python_cmd is not None:
            return self._python_cmd

        # First try python3 command
        try:
            result = subprocess.run(['python3', '--version'],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                self._python_cmd = 'python3'
                self.log_debug("Detected available python3 command")
                return self._python_cmd
        except FileNotFoundError:
            pass

        # Then try python command
        try:
            result = subprocess.run(['python', '--version'],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                # Check if it's Python 3
                version = result.stdout.strip()
                if version.startswith('Python 3'):
                    self._python_cmd = 'python'
                    self.log_debug("Detected available python command (Python 3)")
                    return self._python_cmd
                else:
                    self.log_warning(f"System default Python is not Python 3: {version}")
            else:
                self.log_warning("Python command returned non-zero status code")
        except FileNotFoundError:
            self.log_error("No available Python command found in the system")

        return None

    def run_python_script(self, script: str) -> Tuple[str, str, int]:
        """Execute Python script code

        Args:
            script: Python code to execute

        Returns:
            Tuple[str, str, int]: (stdout, stderr, returncode)

        Raises:
            RuntimeError: When no available Python command is found
        """
        if self.use_poetry:
            cmd = ["poetry", "run", "python", "-c", script]
        else:
            # Get available Python command
            python_cmd = self._detect_python_command()
            if not python_cmd:
                raise RuntimeError(
                    "No available Python command found. Please ensure Python 3 is installed "
                    "and accessible via either 'python3' or 'python' command."
                )
            cmd = [python_cmd, "-c", script]

        try:
            result = subprocess.run(cmd, cwd=self.project_dir, capture_output=True, text=True)
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            self.log_error(f"Failed to execute Python script: {e}")
            return "", str(e), 1

    def check_python_environment(self) -> bool:
        """Check Python environment"""
        self.log_info("Checking Python environment...")

        try:
            # Check Python version
            result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError("Failed to get Python version")

            version_str = result.stdout.strip()
            self.log_info(f"Current Python version: {version_str}")

            # Verify version meets requirements (Python 3.12+)
            version_parts = version_str.split()[1].split('.')
            major, minor = int(version_parts[0]), int(version_parts[1])

            if major < 3 or (major == 3 and minor < 12):
                self.log_error(f"Python version too low, requires Python 3.12+, current version: {version_str}")
                return False

            # Check Poetry environment
            if self.use_poetry:
                self.log_info("Detected Poetry environment, will use Poetry for dependency management")

                # Check Poetry project status
                result = subprocess.run(["poetry", "check"], capture_output=True)
                if result.returncode != 0:
                    self.log_warning("Potential issues with Poetry project configuration")
            else:
                self.log_info("Using pip for dependency management")

            self.log_success("Environment check passed")
            return True

        except Exception as e:
            self.log_error(f"Environment check failed: {e}")
            return False

    def load_config(self) -> Dict:
        """Load YAML configuration file"""
        if not self.config_file.exists():
            self.log_error(f"Config file does not exist: {self.config_file}")
            return {}

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            self.log_debug(f"Config file loaded successfully: {self.config_file.name}")

            # Load global configuration
            global_config = config.get('global', {})
            if global_config:
                self.log_debug(f"Global config: {global_config}")

            return config

        except Exception as e:
            self.log_error(f"Failed to read config file: {e}")
            return {}

    def get_server_configs(self) -> List[ServerConfig]:
        """Retrieve all server configurations"""
        config = self.load_config()
        mcp_servers = config.get('mcp_servers', {})

        servers = []
        for name, server_config in mcp_servers.items():
            if isinstance(server_config, dict):
                # Handle port configuration - supports string "null" and None
                port_value = server_config.get('port')
                if port_value == "null" or port_value is None:
                    port = None
                else:
                    try:
                        port = int(port_value)
                    except (ValueError, TypeError):
                        port = None

                # Handle enabled configuration - supports both string and boolean
                enabled_value = server_config.get('enabled', True)
                if isinstance(enabled_value, str):
                    enabled = enabled_value.lower() in ('true', 'yes', '1', 'on')
                else:
                    enabled = bool(enabled_value)

                # Handle auto_restart configuration
                auto_restart_value = server_config.get('auto_restart', True)
                if isinstance(auto_restart_value, str):
                    auto_restart = auto_restart_value.lower() in ('true', 'yes', '1', 'on')
                else:
                    auto_restart = bool(auto_restart_value)

                # Handle host configuration - YAML null is parsed as Python None
                host_value = server_config.get('host')
                if host_value is None:
                    host = "null"  # Convert to string "null"
                else:
                    host = str(host_value) if host_value is not None else "null"

                servers.append(ServerConfig(
                    name=name,
                    server_type=server_config.get('server_type', name),
                    transport=server_config.get('transport', 'sse'),
                    host=host,
                    port=port,
                    enabled=enabled,
                    auto_restart=auto_restart,
                    description=server_config.get('description', '')
                ))

        return servers

    @staticmethod
    def get_available_port(start_port: int = 8000, max_attempts: int = 100) -> int:
        """Find an available network port"""
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                continue

        raise RuntimeError(f"No available port found (tried range: {start_port}-{start_port + max_attempts})")

    def get_smart_port_for_service(self, service_name: str, transport: str = "sse",
                                   start_port: int = 8000, max_attempts: int = 100) -> int:
        """Smart port allocation (calls utility function)"""
        # First try to directly find an available port
        try:
            # Generate initial port based on service name hash
            hash_obj = hashlib.md5(service_name.encode())
            hash_int = int.from_bytes(hash_obj.digest()[:4], byteorder='little')
            initial_port = start_port + (hash_int % 1000)

            # Try sequential ports from initial port
            for offset in range(max_attempts):
                port = initial_port + offset
                if self._is_port_available(port):
                    self.log_debug(f"Basic port allocation succeeded: {service_name} -> {port}")
                    return port

            # Fallback to random port selection if sequential fails
            for _ in range(max_attempts):
                port = random.randint(start_port, start_port + 10000)
                if self._is_port_available(port):
                    self.log_debug(f"Random port allocation succeeded: {service_name} -> {port}")
                    return port

            raise RuntimeError(f"Failed to allocate port for service {service_name}")

        except Exception as first_error:
            self.log_debug(f"Basic port allocation failed: {first_error}")

            # Then try using utility function for port allocation
            try:
                port = get_smart_port_for_service(service_name, transport, start_port, max_attempts)
                if port > 0 and self._is_port_available(port):
                    self.log_debug(f"Smart port allocation succeeded: {service_name} -> {port}")
                    return port
                else:
                    self.log_warning(f"Smart allocated port {port} is actually unavailable, trying alternatives")
            except Exception as e:
                self.log_warning(f"Smart port allocation exception: {e}")

            # Final fallback to simplest method
            return self.get_available_port(start_port, max_attempts)

    @staticmethod
    def _is_port_available(port: int, host: str = 'localhost') -> bool:
        """Check if a port is available for use"""
        # First check if any process is using this port
        try:
            # Attempt to check for listening processes on this port
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)  # Set 1 second timeout
            result = s.connect_ex((host, port))  # Returns 0 if connection succeeds
            s.close()

            # result == 0 means connection succeeded (port is occupied)
            if result == 0:
                return False
            return True
        except Exception:
            # On error, conservatively assume port is unavailable
            return False

    def _cleanup_port_if_litemcp(self, port: int) -> bool:
        """Clean up MCP-related processes occupying the specified port"""
        try:
            # Find processes using the port
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Check if process is listening on the target port
                    connections = proc.net_connections(kind='inet')
                    for conn in connections:
                        if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                            # Verify if it's an MCP-related process
                            cmdline = ' '.join(proc.info['cmdline'] or [])
                            if any(keyword in cmdline.lower() for keyword in ['lite-mcp', 'cli.py', 'manage.py']):
                                self.log_info(
                                    f"Cleaning up LiteMCP process occupying port {port} (PID: {proc.info['pid']})")
                                proc.terminate()  # Graceful termination
                                try:
                                    proc.wait(timeout=5)  # Wait for process to exit
                                except psutil.TimeoutExpired:
                                    proc.kill()  # Force kill if not responding
                                time.sleep(1)  # Brief pause
                                return self._is_port_available(port)  # Verify cleanup
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False  # No matching process found
        except Exception as e:
            self.log_debug(f"Port cleanup failed: {e}")
            return False

    def resolve_host_address(self, config_host: str, service_name: str,
                             fallback_strategy: str = "ip") -> str:
        """Unified host address resolution"""
        # If config specifies concrete IP/domain, use it directly
        if config_host and config_host != "null" and config_host != "0.0.0.0":
            return config_host

        # Get machine IP
        machine_ip = self._get_local_ip_via_utils()

        # Determine final address based on config and fallback strategy
        if config_host == "null":
            # Config requires auto IP detection
            if machine_ip:
                self.log_debug(f"Service {service_name}: Auto-detected IP: {machine_ip}")
                return machine_ip
            else:
                # IP detection failed, handle with fallback strategy
                if fallback_strategy == "ip":
                    self.log_warning(f"Service {service_name}: Failed to get machine IP, using 127.0.0.1")
                    return "127.0.0.1"
                elif fallback_strategy == "localhost":
                    self.log_warning(f"Service {service_name}: Failed to get machine IP, using localhost")
                    return "localhost"
                elif fallback_strategy == "0.0.0.0":
                    self.log_warning(f"Service {service_name}: Failed to get machine IP, using 0.0.0.0")
                    return "0.0.0.0"
                else:
                    return "localhost"
        elif config_host == "0.0.0.0":
            # Config specifies 0.0.0.0 (listen on all interfaces)
            if machine_ip and fallback_strategy == "display":
                return machine_ip
            else:
                return "0.0.0.0"
        else:
            return config_host or "localhost"

    def _get_local_ip_via_utils(self) -> Optional[str]:
        """Get local IP through src.core.utils module"""
        try:
            ip = get_local_ip()
            if ip:
                self.log_debug(f"Obtained IP via utils.get_local_ip(): {ip}")
                return ip
            else:
                self.log_debug("utils.get_local_ip() returned empty, falling back to socket method")
                return self._get_local_ip_via_socket()
        except Exception as e:
            self.log_debug(f"Failed to get local IP: {e}")
            return self._get_local_ip_via_socket()

    def _get_local_ip_via_socket(self) -> Optional[str]:
        """Get local IP via socket connection (fallback method)"""
        try:
            # Connect to external address to get local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                machine_ip = s.getsockname()[0]
                self.log_debug(f"Obtained IP via socket connection: {machine_ip}")
                return machine_ip
        except Exception as e:
            self.log_debug(f"Failed to get IP via socket method: {e}")
            return None

    def get_running_processes(self) -> Dict[str, psutil.Process]:
        """Get all running LiteMCP processes"""
        processes = {}

        # Get from PID files
        for pid_file in self.pid_dir.glob("*.pid"):
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())

                # Use same health check as cleanup logic
                if self._is_process_alive_and_healthy(pid):
                    process = psutil.Process(pid)
                    processes[pid_file.stem] = process
                else:
                    # Clean up invalid PID file
                    pid_file.unlink()
                    self.log_debug(f"Cleaned invalid PID file: {pid_file.name}")
            except (ValueError, psutil.NoSuchProcess, FileNotFoundError):
                # Clean up invalid PID file
                if pid_file.exists():
                    pid_file.unlink()

        # Scan all processes to find LiteMCP processes that might have lost PID files
        try:
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'src/cli.py' in cmdline and any(cmd in cmdline for cmd in ['serve', 'proxy', 'api']):
                        # This is a LiteMCP process, try to identify server name
                        server_name = None

                        if 'proxy' in cmdline:
                            server_name = 'proxy_server'
                        elif 'api' in cmdline:
                            server_name = 'api_server'
                        elif '--server' in cmdline:
                            # Parse server name
                            parts = cmdline.split('--server')
                            if len(parts) > 1:
                                server_name = parts[1].strip().split()[0]

                        if server_name and server_name not in processes:
                            processes[server_name] = proc
                            self.log_debug(f"Found process without PID file: {server_name} (PID: {proc.pid})")

                            # Recreate PID file
                            pid_file = self.pid_dir / f"{server_name}.pid"
                            with open(pid_file, 'w') as f:
                                f.write(str(proc.pid))
                            self.log_debug(f"Recreated PID file: {pid_file.name}")

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.log_debug(f"Process scan failed: {e}")

        return processes

    def stop_all_servers(self, force: bool = False, stop_monitor: bool = True):
        """Stop all servers (optimized version: only cleans up local services while preserving remote service records)"""
        self.log_info("Stopping all local servers...")

        # Only stop monitor thread when needed
        if stop_monitor:
            self._stop_monitor_thread()

        processes = self.get_running_processes()
        stopped_count = 0

        for name, process in processes.items():
            stopped_count += self._stop_process_and_children(name, process, force)

        # Additional cleanup: scan for all possible LiteMCP related processes
        additional_cleaned = self._cleanup_all_litemcp_processes(force)
        if additional_cleaned > 0:
            self.log_info(f"Additional cleanup: {additional_cleaned} LiteMCP related processes")

        # Clean up local service registry records while preserving remote services
        self.log_info("Cleaning up local service registry records, preserving remote services...")
        self._cleanup_local_registry_records()

        # Clean up all PID files
        self._cleanup_all_pid_files()

        self.log_info(f"Stop completed: {stopped_count} local servers")

    def _cleanup_existing_servers_for_startup(self):
        """Clean up existing servers before startup (without stopping monitor thread)"""
        self.log_info("Cleaning up existing servers...")

        processes = self.get_running_processes()
        stopped_count = 0

        for name, process in processes.items():
            stopped_count += self._stop_process_and_children(name, process, False)

        # Additional cleanup: scan for all possible LiteMCP related processes
        additional_cleaned = self._cleanup_all_litemcp_processes(False)
        if additional_cleaned > 0:
            self.log_info(f"Additional cleanup: {additional_cleaned} LiteMCP related processes")

        # Clean up local service registry records while preserving remote services
        self._cleanup_local_registry_records()

        # Clean up all PID files
        self._cleanup_all_pid_files()

        if stopped_count > 0:
            self.log_info(f"Cleanup completed: {stopped_count} servers")
        else:
            self.log_info("No servers found needing cleanup")

    def stop_specific_server(self, server_name: str):
        """Stop specified server (enhanced version, supports cleanup of processes without PID files)"""
        self.log_info(f"Stopping specified server: {server_name}")

        pid_file = self.pid_dir / f"{server_name}.pid"
        stopped_via_pid = False

        # 1. Attempt to stop process via PID file
        if pid_file.exists():
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())

                if psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    stopped_count = self._stop_process_and_children(server_name, process, False)
                    if stopped_count > 0:
                        stopped_via_pid = True
                else:
                    self.log_info(f"{server_name} process in PID file doesn't exist", f"PID: {pid}")
                    pid_file.unlink()

            except (ValueError, FileNotFoundError, psutil.NoSuchProcess) as e:
                self.log_warning(f"Failed to stop {server_name} via PID: {e}")
                if pid_file.exists():
                    pid_file.unlink()
        else:
            self.log_info(f"No PID file found for {server_name}")

        # 2. If PID method failed or no PID file, scan for orphaned processes
        if not stopped_via_pid:
            cleaned_count = self._cleanup_orphaned_processes(server_name)
            if cleaned_count > 0:
                self.log_success(f"Cleaned {cleaned_count} orphaned {server_name} processes")
            else:
                self.log_info(f"No running {server_name} processes found")

        # 3. Clean up registry records
        self._cleanup_registry_for_server(server_name)

        # 4. Additional check: cleanup ports potentially used by this server
        self._cleanup_server_port(server_name)

    def _cleanup_orphaned_processes(self, server_name: str) -> int:
        """Clean up orphaned processes (processes not tracked by PID files)"""
        cleaned_count = 0

        try:
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])

                    # Check if this is the target server's process
                    is_target_server = False

                    # Exact server name matching
                    if 'src/cli.py' in cmdline and f'--server {server_name}' in cmdline:
                        is_target_server = True
                    # Handle proxy and API servers
                    elif server_name == 'proxy_server' and 'src/cli.py' in cmdline and 'proxy' in cmdline:
                        is_target_server = True
                    elif server_name == 'api_server' and 'src/cli.py' in cmdline and 'api' in cmdline:
                        is_target_server = True

                    if is_target_server:
                        self.log_info(f"Found orphaned process: {server_name} (PID: {proc.pid})")

                        # Use enhanced process stopping method
                        try:
                            process = psutil.Process(proc.pid)
                            stopped = self._stop_process_and_children(f"{server_name}_orphan", process, False)
                            if stopped > 0:
                                cleaned_count += stopped
                        except psutil.NoSuchProcess:
                            # Process already gone
                            continue

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            self.log_debug(f"Failed to clean up orphaned processes: {e}")

        return cleaned_count

    def _cleanup_server_port(self, server_name: str):
        """Clean up ports potentially occupied by specified server (dynamically retrieves port info)"""
        # Look up the server's port information from registry
        if not self.registry_file.exists():
            return

        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                registry = json.load(f)

            # Find the port record for this server
            for server_id, info in registry.items():
                if info.get('name') == server_name:
                    port = info.get('port')
                    if port and not self._is_port_available(port):
                        self.log_info(f"Checking if port {port} is occupied by {server_name}...")
                        if self._cleanup_port_if_litemcp(port):
                            self.log_success(f"Cleaned up process on port {port}")
                    break

        except Exception as e:
            self.log_debug(f"Failed to clean up server port: {e}")

    def _cleanup_registry_for_server(self, server_name: str):
        """Clean up registry records for specified server (only cleans local server records)"""
        if not self.registry_file.exists():
            return

        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                registry = json.load(f)

            # Find and remove matching local server records
            keys_to_remove = []
            for key, info in registry.items():
                if info.get('name') == server_name:
                    # Only clean up local server records
                    if self._is_local_server(info):
                        keys_to_remove.append(key)
                        self.log_debug(f"Preparing to clean local server record: {server_name}")
                    else:
                        self.log_debug(f"Skipping remote server record: {server_name} ({info.get('host', 'unknown')})")

            for key in keys_to_remove:
                del registry[key]
                self.log_debug(f"Cleaned local server registry record: {key}")

            # Write back to file
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.log_warning(f"Failed to clean registry: {e}")

    def start_mcp_server(self, server_config: ServerConfig) -> bool:
        """Start a single MCP server"""
        log_file = self.log_dir / f"{server_config.name}.log"
        pid_file = self.pid_dir / f"{server_config.name}.pid"
        
        # 1. Check if this service is already running
        processes = self.get_running_processes()
        if server_config.name in processes:
            existing_proc = processes[server_config.name]
            # Check if process is responsive
            try:
                if existing_proc.is_running() and existing_proc.status() != psutil.STATUS_ZOMBIE:
                    self.log_success(f"[OK] {server_config.name} is already running (PID: {existing_proc.pid})")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
            # Process exists but is unresponsive, stop it
            self.log_warning(f"Detected unresponsive {server_config.name} process, restarting...")
            self.stop_specific_server(server_config.name)
        
        # Clean up potentially existing old PID files
        if pid_file.exists():
            pid_file.unlink()
        
        # Clean up old records in registry
        self._cleanup_registry_for_server(server_config.name)
        
        self.log_info(f"Starting MCP server: {server_config.name} ({server_config.server_type})")
        
        # Resolve host address
        host = self.resolve_host_address(server_config.host, server_config.name, "ip")
        
        # Smart port allocation - prioritize port settings from config file
        if server_config.port is None or server_config.port == "null":
            try:
                # Use server name for smart port allocation
                port = self.get_smart_port_for_service(server_config.name, server_config.transport)
            except Exception as e:
                self.log_warning(f"Smart port allocation failed: {e}, trying default port allocation")
                try:
                    port = self.get_available_port(8000 + hash(server_config.name) % 1000)
                    if port:
                        self.log_info(f"Default port allocation successful: {port}")
                    else:
                        self.log_error("All port allocation methods failed")
                        return False
                except Exception as e2:
                    self.log_error(f"Default port allocation also failed: {e2}")
                    return False
        else:
            port = server_config.port
            
        # Check if port is available
        if not self._is_port_available(port):
            self.log_warning(f"Port {port} is already occupied, trying to automatically find available port")
            try:
                port = self.get_available_port(port + 1, 100)
                self.log_info(f"Found new available port: {port}")
            except Exception as e:
                self.log_error(f"Unable to find available port: {e}")
                return False
            
        # Build startup command
        cmd = [
            "src/cli.py",
            "serve",
            "--server", server_config.name,
            "--transport", server_config.transport,
            "--host", host,
            "--port", str(port)
        ]
        
        # Start server process
        try:
            result = self.run_python(
                *cmd,
                stdout=log_file.open("a"),
                stderr=log_file.open("a")
            )
            
            # Waiting for the server to start
            time.sleep(3)
            
            # Check if the process started successfully
            if result.poll() is None:
                # Save PID file
                with open(pid_file, 'w') as f:
                    f.write(str(result.pid))
                
                self.log_success(f"[OK] {server_config.name} startup successful")
                self.log_info(f"  PID: {result.pid}")
                self.log_info(f"  Port: {port}")
                # Build correct access URL based on transport mode
                if server_config.transport == "http":
                    access_url = f"http://{host}:{port}/mcp"
                elif server_config.transport == "sse":
                    access_url = f"http://{host}:{port}/sse"
                else:
                    access_url = f"http://{host}:{port}"
                self.log_info(f"  Access URL: {access_url}")
                self.log_info(f"  Log: {log_file}")
                return True
            else:
                # Check if another process successfully started the service
                time.sleep(2)  # Wait a moment to ensure process status update
                new_processes = self.get_running_processes()
                if server_config.name in new_processes:
                    # Try to get port information from command line
                    proc = new_processes[server_config.name]
                    cmdline = ' '.join(proc.cmdline())
                    actual_port = port
                    if "--port" in cmdline:
                        port_idx = cmdline.find("--port") + len("--port")
                        try:
                            actual_port = int(cmdline[port_idx:].split()[0])
                        except:
                            pass
                    
                    actual_host = host
                    if "--host" in cmdline:
                        host_idx = cmdline.find("--host") + len("--host")
                        try:
                            actual_host = cmdline[host_idx:].split()[0]
                        except:
                            pass
                            
                    self.log_success(f"[OK] {server_config.name} started (PID: {new_processes[server_config.name].pid})")
                    self.log_info(f"  Port: {actual_port}")
                    # Build correct access URL based on transport mode
                    if server_config.transport == "http":
                        access_url = f"http://{actual_host}:{actual_port}/mcp"
                    elif server_config.transport == "sse":
                        access_url = f"http://{actual_host}:{actual_port}/sse"
                    else:
                        access_url = f"http://{actual_host}:{actual_port}"
                    self.log_info(f"  Access URL: {access_url}")
                    return True
                
                self.log_error(f"[X] {server_config.name} startup failed")
                self.log_info(f"Please check log file: {log_file}")
                return False
            
        except Exception as e:
            self.log_error(f"[X] {server_config.name} startup error, please check logs")
            self.log_debug(f"Error details: {e}")
            
            # Check if service was started by other means
            new_processes = self.get_running_processes()
            if server_config.name in new_processes:
                self.log_success(f"[OK] {server_config.name} started (PID: {new_processes[server_config.name].pid})")
                return True
                
            return False
    
    def _start_proxy_server_enhanced(self) -> bool:
        """Start proxy server"""
        config = self.load_config()
        proxy_config = config.get('proxy_server', {})
        
        # Handle enabled configuration
        enabled_value = proxy_config.get('enabled', True)
        if isinstance(enabled_value, str):
            enabled = enabled_value.lower() in ('true', 'yes', '1', 'on')
        else:
            enabled = bool(enabled_value)
        
        if not enabled:
            self.log_info("Proxy server is disabled in configuration, skipping startup")
            return False
        
        self.log_step("Starting proxy server", "", "")
        
        # Get host and port configuration first
        host = self.resolve_host_address(
            proxy_config.get('host', 'localhost'), 
            'proxy_server', 
            'localhost'
        )
        
        # Process port configuration
        port_value = proxy_config.get('port', 1888)
        try:
            port = int(port_value)
        except (ValueError, TypeError):
            port = 1888

        # Check if proxy server is already running
        processes = self.get_running_processes()
        if "proxy_server" in processes:
            existing_proc = processes["proxy_server"]
            try:
                # Check if the process is responding
                if existing_proc.is_running() and existing_proc.status() != psutil.STATUS_ZOMBIE:
                    try:
                        # Test if port is listening
                        with socket.socket() as s:
                            s.settimeout(1)
                            if s.connect_ex((host, port)) == 0:
                                self.log_success(f"Proxy server is already running (PID: {existing_proc.pid})")
                                return True
                    except:
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            # Proxy server process exists but is unresponsive, stop it
            self.log_info("Detected unresponsive proxy server process, restarting...")
            self.stop_specific_server("proxy_server")
        else:
            # Stop potentially running proxy server
            self.stop_specific_server("proxy_server")
        
        # Check port availability and attempt to fix
        if not self._is_port_available(port):
            self.log_warning(f"Port {port} is occupied, attempting to clean up...")
            if not self._cleanup_port_if_litemcp(port):
                # Try to use other ports
                try:
                    new_port = self.get_available_port(port + 1, 100)
                    self.log_warning(f"Port {port} is not available, will use port {new_port}")
                    port = new_port
                except Exception:
                    self.log_error(f"Port {port} is occupied by other process, cannot start proxy server")
                    return False
        
        # Start proxy server
        log_file = self.log_dir / "proxy_server.log"
        pid_file = self.pid_dir / "proxy_server.pid"
        
        cmd_base = [
            sys.executable, "src/cli.py", "proxy",
            "--host", host,
            "--port", str(port)
        ]
        
        if self.use_poetry:
            cmd = ["poetry", "run"] + cmd_base
        else:
            cmd = cmd_base
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                if self.is_windows:
                    process = subprocess.Popen(
                        cmd,
                        cwd=self.project_dir,
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    process = subprocess.Popen(
                        cmd,
                        cwd=self.project_dir,
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        preexec_fn=os.setsid
                    )
            
            # Save PID
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))

            # Wait for startup
            for attempt in range(5):
                time.sleep(1)
                
                # Check if the process is still running
                if process.poll() is not None:
                    self.log_error("[X] Proxy server startup failed, process exited")
                    return False
                
                # Try to detect if service started via port    
                try:
                    with socket.socket() as s:
                        s.settimeout(1)
                        if s.connect_ex((host, port)) == 0:
                            # Get display host address
                            display_host = self.resolve_host_address(proxy_config.get('host', 'localhost'), 'proxy_server', 'display')
                            self.log_success(f"[OK] Proxy server startup successful (PID: {process.pid})")
                            self.log_info(f"   Access: http://{display_host}:{port}")
                            self.log_info(f"   Log: {log_file}")
                            self.log_info(f"   Status: http://{display_host}:{port}/proxy/status")
                            return True
                except:
                    pass
            
            # Try to confirm service startup by other means
            if process.poll() is None:
                # Process still running, service may be started but our detection method has issues
                display_host = self.resolve_host_address(proxy_config.get('host', 'localhost'), 'proxy_server', 'display')
                self.log_success(f"[OK] Proxy server started (PID: {process.pid})")
                self.log_info(f"   Access: http://{display_host}:{port}")
                self.log_info(f"   Log: {log_file}")
                return True
            else:
                self.log_error("[X] Proxy server startup failed")
                return False
                
        except Exception as e:
            self.log_error(f"Proxy server startup failed: {e}")
            return False

    def _start_api_server_enhanced(self) -> bool:
        """Start API server"""
        config = self.load_config()
        api_config = config.get('api_server', {})
        
        # Handle enabled configuration
        enabled_value = api_config.get('enabled', True)
        if isinstance(enabled_value, str):
            enabled = enabled_value.lower() in ('true', 'yes', '1', 'on')
        else:
            enabled = bool(enabled_value)
        
        if not enabled:
            self.log_info("API server is disabled in configuration, skipping startup")
            return False
        
        self.log_step("Starting API server", "", "")
        
        # Stop potentially running API server
        self.stop_specific_server("api_server")

        api_host = api_config.get('host', 'null')
        host = self.resolve_host_address(
            api_host if api_host else 'null',
            'api_server', 
            'ip'
        )
        
        # Process port configuration
        port_value = api_config.get('port', 9000)
        try:
            port = int(port_value)
        except (ValueError, TypeError):
            port = 9000
        
        # Check port availability
        if not self._is_port_available(port):
            self.log_warning(f"Port {port} is occupied, attempting to clean up...")
            if not self._cleanup_port_if_litemcp(port):
                self.log_error(f"Port {port} is occupied by other process, cannot start API server")
                return False
        
        # Start API server
        log_file = self.log_dir / "api_server.log"
        pid_file = self.pid_dir / "api_server.pid"
        
        cmd_base = [
            sys.executable, "src/cli.py", "api",
            "--host", host,
            "--port", str(port)
        ]
        
        if self.use_poetry:
            cmd = ["poetry", "run"] + cmd_base
        else:
            cmd = cmd_base
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                if self.is_windows:
                    process = subprocess.Popen(
                        cmd,
                        cwd=self.project_dir,
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    process = subprocess.Popen(
                        cmd,
                        cwd=self.project_dir,
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        preexec_fn=os.setsid
                    )
            
            # Save PID
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # Waiting to start and undergo health check
            time.sleep(5)
            max_attempts = 6
            attempt = 1

            while attempt <= max_attempts:
                try:
                    response = requests.get(f"http://{host}:{port}/health", timeout=3)
                    if response.status_code == 200:
                        self.log_success(f"[OK] API server startup successful (PID: {process.pid})")
                        self.log_info(f"   Access: http://{host}:{port}")
                        self.log_info(f"   Log: {log_file}")
                        return True
                except:
                    pass
                
                self.log_debug(f"Waiting for API server startup... (attempt {attempt}/{max_attempts})")
                time.sleep(3)
                attempt += 1
            
            self.log_error("[X] API server startup failed or health check failed")
            return False
                
        except Exception as e:
            self.log_error(f"Failed to start API server: {e}")
            return False

    def _auto_unregister_servers_from_proxy(self, custom_proxy_url: str = None, target_server: str = None):
        """Automatically unregister MCP servers from proxy"""
        config = self.load_config()
        proxy_config = config.get('proxy_server', {})
        
        # If using a custom proxy URL, skip the local proxy configuration check
        if not custom_proxy_url:
            # Check if the proxy server is enabled
            enabled_value = proxy_config.get('enabled', True)
            if isinstance(enabled_value, str):
                enabled = enabled_value.lower() in ('true', 'yes', '1', 'on')
            else:
                enabled = bool(enabled_value)
            
            if not enabled:
                self.log_info("Proxy server not enabled, skipping automatic unregistration")
                return

        host = "localhost"
        port = 1888
        # If a custom proxy URL is provided, use it directly
        if custom_proxy_url:
            proxy_url = custom_proxy_url.rstrip('/')
            self.log_info(f"Using custom proxy server address: {proxy_url}")
        else:
            # Use the settings in the configuration file
            host = self.resolve_host_address(
                proxy_config.get('host', 'localhost'), 
                'proxy_server', 
                'localhost'
            )
            
            # Process port configuration
            port_value = proxy_config.get('port', 1888)
            try:
                port = int(port_value)
            except (ValueError, TypeError):
                port = 1888
            
            # If the configured host is localhost or 127.0.0.1, use it directly
            # If it is another address (such as 0.0.0.0), try using the local IP address
            if host in ['localhost', '127.0.0.1']:
                connect_host = "localhost"
            elif host == "0.0.0.0":
                # Attempt to obtain the local IP address for connection
                machine_ip = self._get_local_ip_via_utils()
                connect_host = machine_ip if machine_ip else "localhost"
                self.log_info(f"Proxy server listening on 0.0.0.0, using local IP for connection: {connect_host}")
            else:
                connect_host = host
            
            proxy_url = f"http://{connect_host}:{port}"
        
        self.log_info(f"Starting to unregister MCP servers from proxy: {proxy_url}")
        
        # Waiting for proxy server to be available
        wait_count = 0
        max_wait = 10  # Reduce waiting time
        connection_error = None

        while wait_count < max_wait:
            try:
                response = requests.get(f"{proxy_url}/proxy/status", timeout=5)
                if response.status_code == 200:
                    self.log_success(f"Proxy server ready, status code: {response.status_code}")
                    connection_error = None
                    break
                else:
                    connection_error = f"Status code: {response.status_code}"
            except requests.exceptions.ConnectionError as e:
                connection_error = f"Connection error: {e}"
            except requests.exceptions.Timeout as e:
                connection_error = f"Request timeout: {e}"
            except Exception as e:
                connection_error = f"Request exception: {e}"
            
            time.sleep(1)
            wait_count += 1
        
        if wait_count == max_wait:
            self.log_error(f"Proxy server inaccessible, skipping automatic unregistration")
            if connection_error:
                self.log_warning(f"Connection error: {connection_error}")
            return
        
        # Unregister MCP servers
        unregistered_count = 0
        failed_count = 0
        
        # Determine servers to unregister
        if target_server:
            # Unregister only specified server
            servers_to_unregister = [target_server]
            self.log_info(f"Only unregistering specified server: {target_server}")
        else:
            # Get currently registered servers list
            try:
                response = requests.get(f"{proxy_url}/proxy/status", timeout=5)
                if response.status_code == 200:
                    status_data = response.json()
                    servers_to_unregister = list(status_data.get('servers', {}).keys())
                    if servers_to_unregister:
                        self.log_info(f"Found {len(servers_to_unregister)} registered servers")
                    else:
                        self.log_info("No registered servers in proxy")
                        return
                else:
                    self.log_error(f"Failed to get proxy status: HTTP {response.status_code}")
                    return
            except Exception as e:
                self.log_error(f"Failed to get proxy status: {e}")
                return
        
        for server_name in servers_to_unregister:
            try:
                self.log_info(f"Unregistering server: {server_name}")
                
                # Send unregistration request
                unregister_url = f"{proxy_url}/proxy/unregister/{server_name}"
                
                # Add retry mechanism
                max_retries = 3
                retry_count = 0
                success = False

                while retry_count < max_retries and not success:
                    try:
                        response = requests.delete(
                            unregister_url,
                            timeout=5
                        )
                        
                        if response.status_code == 200:
                            response_data = response.json()
                            status = response_data.get('status')
                            if status in ['success', 'unregistered']:
                                if status == 'success':
                                    self.log_success(f"{server_name} unregistered successfully")
                                elif status == 'unregistered':
                                    self.log_success(f"{server_name} unregistered (previously not registered or already unregistered)")
                                unregistered_count += 1
                                success = True
                            else:
                                retry_count += 1
                                self.log_warning(f"{server_name} unregistration failed (attempt {retry_count}/{max_retries}): {response_data}")
                                time.sleep(1)
                        elif response.status_code == 404:
                            self.log_warning(f"{server_name} unregistered successfully (server not registered in proxy)")
                            unregistered_count += 1
                            success = True  # 404 is also considered success since server is indeed not registered
                        else:
                            retry_count += 1
                            self.log_warning(f"{server_name} unregistration failed (attempt {retry_count}/{max_retries}): HTTP {response.status_code}")
                            time.sleep(1)
                    except Exception as e:
                        retry_count += 1
                        self.log_warning(f"{server_name} unregistration failed (attempt {retry_count}/{max_retries}): {e}")
                        time.sleep(1)
                
                if not success:
                    self.log_error(f"[X] {server_name} unregistration failed, attempted {max_retries} times")
                    failed_count += 1
                    
            except Exception as e:
                self.log_error(f"[X] {server_name} unregistration failed: {e}")
                failed_count += 1
        
        # Display unregistration results
        if target_server:
            # Result display for specified server mode
            if unregistered_count > 0:
                self.log_success(f"Specified server {target_server} unregistered successfully")
            else:
                self.log_error(f"Specified server {target_server} unregistration failed")
        else:
            # Result display for all servers mode
            if unregistered_count > 0:
                self.log_success(f"Automatic unregistration completed - Success: {unregistered_count}, Failed: {failed_count}")
            else:
                if servers_to_unregister:
                    self.log_error(f"Unregistration failed - Found {len(servers_to_unregister)} registered servers, but all unregistration failed")
                else:
                    self.log_warning("No unregisterable servers found")

    def _auto_register_servers_to_proxy(self, custom_proxy_url: str = None, target_server: str = None):
        """Automatically register MCP servers to proxy"""
        config = self.load_config()
        proxy_config = config.get('proxy_server', {})
        
        # If using a custom proxy URL, skip local proxy configuration check
        if not custom_proxy_url:
            # Check if proxy server is enabled
            enabled_value = proxy_config.get('enabled', True)
            if isinstance(enabled_value, str):
                enabled = enabled_value.lower() in ('true', 'yes', '1', 'on')
            else:
                enabled = bool(enabled_value)
            
            if not enabled:
                self.log_info("Proxy server not enabled, skipping automatic registration")
                return

        host = "localhost"
        port = 1888
        # If a custom proxy URL is provided, use it directly
        if custom_proxy_url:
            proxy_url = custom_proxy_url.rstrip('/')  # Remove trailing slash
            self.log_info(f"Using custom proxy server address: {proxy_url}")
        else:
            # Use settings from configuration file
            host = self.resolve_host_address(
                proxy_config.get('host', 'localhost'), 
                'proxy_server', 
                'localhost'
            )
            
            # Process port configuration
            port_value = proxy_config.get('port', 1888)
            try:
                port = int(port_value)
            except (ValueError, TypeError):
                port = 1888
            
            # If configured host is localhost or 127.0.0.1, use directly
            # If it's another address (like 0.0.0.0), try using local IP
            if host in ['localhost', '127.0.0.1']:
                connect_host = "localhost"
            elif host == "0.0.0.0":
                # Attempt to obtain local IP for connection
                machine_ip = self._get_local_ip_via_utils()
                connect_host = machine_ip if machine_ip else "localhost"
                self.log_info(f"Proxy server listening on 0.0.0.0, using local IP for connection: {connect_host}")
            else:
                connect_host = host
            
            proxy_url = f"http://{connect_host}:{port}"
        
        self.log_info(f"Starting automatic registration of MCP servers to proxy: {proxy_url}")
        
        # Wait for proxy server to fully start
        wait_count = 0
        max_wait = 30  # Increase maximum waiting time to 30 seconds
        connection_error = None
        
        self.log_info(f"Waiting for proxy server to be ready, timeout: {max_wait} seconds...")

        while wait_count < max_wait:
            try:
                response = requests.get(f"{proxy_url}/proxy/status", timeout=5)
                if response.status_code == 200:
                    self.log_success(f"Proxy server ready, status code: {response.status_code}")
                    connection_error = None
                    break
                else:
                    connection_error = f"Status code: {response.status_code}"
            except requests.exceptions.ConnectionError as e:
                connection_error = f"Connection error: {e}"
            except requests.exceptions.Timeout as e:
                connection_error = f"Request timeout: {e}"
            except Exception as e:
                connection_error = f"Request exception: {e}"
            
            # Display detailed waiting status
            if wait_count % 5 == 0:  # Show detailed log every 5 seconds
                detail = f"Attempting connection: {proxy_url}/proxy/status"
                if connection_error:
                    detail += f" - Error: {connection_error}"
                self.log_info(f"Waiting for proxy server startup... ({wait_count}/{max_wait} seconds)", detail)
            
            time.sleep(1)
            wait_count += 1
        
        if wait_count == max_wait:
            self.log_error(f"Proxy server startup timeout, skipping automatic registration")
            self.log_warning("Possible reasons:")
            self.log_warning("1. Proxy server failed to start successfully")
            self.log_warning(f"2. Proxy server address configuration error, current address: {proxy_url}")
            self.log_warning("3. Network issues preventing proxy access")
            if connection_error:
                self.log_warning(f"Last connection error: {connection_error}")
            
            # Try different connection methods for recovery
            self.log_info("Trying other ways to connect to proxy...")
            
            # Try connecting using localhost
            try:
                alt_proxy_url = f"http://localhost:{port}"
                self.log_info(f"Attempting connection using localhost: {alt_proxy_url}")

                response = requests.get(f"{alt_proxy_url}/proxy/status", timeout=5)
                if response.status_code == 200:
                    self.log_success(f"Connection via localhost successful!")
                    proxy_url = alt_proxy_url
                else:
                    self.log_warning(f"localhost connection failed: status code {response.status_code}")
            except Exception as e:
                self.log_warning(f"localhost connection failed: {e}")
        
        # Register MCP servers
        registered_count = 0
        failed_count = 0
        
        # Get running processes on local machine
        processes = self.get_running_processes()
        
        # Get remote service records
        remote_servers = {}
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
                
                for server_id, info in registry.items():
                    if not self._is_local_server(info):
                        # This is a remote service
                        server_name = info.get('name')
                        if server_name:
                            remote_servers[server_name] = info
                            self.log_debug(f"Discovered remote service: {server_name} ({info.get('host')}:{info.get('port')})")
                            
            except Exception as e:
                self.log_warning(f"Failed to read remote service records: {e}")
        
        # Get enabled servers from configuration file
        server_configs = self.get_server_configs()
        all_servers = {config.name: config for config in server_configs}
        
        # Determine which servers to register based on whether target_server is specified
        if target_server:
            # Register only the specified server
            if ((target_server in processes or target_server in remote_servers) and 
                target_server not in ["proxy_server", "api_server"]):
                mcp_servers = [target_server]
                server_type = "local" if target_server in processes else "remote"
                self.log_info(f"Only register specified {server_type} server: {target_server}")
            else:
                self.log_warning(f"Specified server {target_server} is not running or not enabled, skipping registration")
                return
        else:
            # Register all discovered MCP servers (locally running + remotely registered)
            local_mcp_servers = [name for name, _ in processes.items() 
                               if name not in ["proxy_server", "api_server"]]
            remote_mcp_servers = [name for name in remote_servers.keys()]
            
            mcp_servers = local_mcp_servers + remote_mcp_servers
            
            if not mcp_servers:
                self.log_warning("No registerable MCP servers found")
                return
            
            self.log_info(f"Discovered {len(local_mcp_servers)} local servers + {len(remote_mcp_servers)} remote servers, total {len(mcp_servers)} servers waiting for registration")

        # Process all servers needing registration (local + remote)
        for name in mcp_servers:
            # Skip non-MCP servers
            if name in ["proxy_server", "api_server"]:
                continue
            
            # If target_server is specified, only process the specified server
            if target_server and name != target_server:
                continue
            
            try:
                # Determine if it's a local service or remote service
                if name in processes:
                    # Local service: parse information from process command line
                    process = processes[name]
                    cmdline = ' '.join(process.cmdline())

                    # Parse port
                    actual_port = "unknown"
                    if "--port" in cmdline:
                        port_idx = cmdline.find("--port") + len("--port")
                        actual_port = cmdline[port_idx:].split()[0]

                    # Parse host
                    actual_host = "localhost"
                    if "--host" in cmdline:
                        host_idx = cmdline.find("--host") + len("--host")
                        actual_host = cmdline[host_idx:].split()[0]

                    if actual_port == "unknown":
                        self.log_warning(f"Skipping local server with unobtainable port: {name}")
                        continue

                    # Get correct transport protocol
                    expected_transport = all_servers[name].transport

                    register_data = {
                        "server_name": name,
                        "host": actual_host,
                        "port": int(actual_port),
                        "transport": expected_transport,
                        "pid": process.pid  # Add process PID
                    }

                    self.log_info(f"Registering local server: {name} -> {actual_host}:{actual_port}")

                elif name in remote_servers:
                    # Remote service: get information from registry.json
                    remote_info = remote_servers[name]
                    actual_host = remote_info.get('host', 'unknown')
                    actual_port = remote_info.get('port', 'unknown')

                    if actual_port == "unknown" or actual_host == "unknown":
                        self.log_warning(f"Skipping remote server with incomplete information: {name}")
                        continue

                    # Get correct transport protocol
                    expected_transport = remote_info.get('transport')

                    register_data = {
                        "server_name": name,
                        "host": actual_host,
                        "port": int(actual_port),
                        "transport": expected_transport,
                        # Remote services do not include local PID
                    }

                    self.log_info(f"Registering remote server: {name} -> {actual_host}:{actual_port}")

                else:
                    self.log_warning(f"Server {name} is neither running locally nor in remote records, skipping")
                    continue

                # Send registration request
                # First check if server is already registered (idempotency check)
                already_registered = False
                try:
                    check_response = requests.get(f"{proxy_url}/proxy/status", timeout=5)
                    if check_response.status_code == 200:
                        status_data = check_response.json()
                        registered_servers = status_data.get('servers', {})
                        if name in registered_servers:
                            server_info = registered_servers[name]
                            existing_host = server_info.get('host', '')
                            existing_port = server_info.get('port', 0)
                            # Check if it's the same server instance
                            if existing_host == actual_host and existing_port == int(actual_port):
                                self.log_info(f"[OK] {name} is already registered in proxy, skipping duplicate registration")
                                already_registered = True
                                registered_count += 1
                            else:
                                self.log_info(f"[INFO] {name} is already registered but with different configuration, will update registration information")
                except Exception as e:
                    self.log_debug(f"Failed to check server registration status: {e}")

                if already_registered:
                    continue  # Skip already registered servers

                # Execute registration request (no retry mechanism to avoid duplicate requests)
                register_url = f"{proxy_url}/proxy/register"
                self.log_debug(f"Sending registration request to: {register_url}")

                try:
                    response = requests.post(
                        register_url,
                        json=register_data,
                        headers={"Content-Type": "application/json"},
                        timeout=10  # Increase timeout period
                    )

                    if response.status_code == 200:
                        response_data = response.json()
                        # Check various success statuses
                        if response_data.get('status') in ['registered', 'success']:
                            self.log_success(f"[OK] {name} registered successfully")
                            if 'request_id' in response_data:
                                self.log_debug(f"Registration request ID: {response_data['request_id']}")
                            registered_count += 1
                        else:
                            self.log_error(f"{name} registration failed: {response_data}")
                            failed_count += 1
                    else:
                        try:
                            error_response = response.json()
                            error_detail = f" - Detailed information: {error_response}"
                        except:
                            try:
                                error_detail = f" - Response content: {response.text}"
                            except:
                                error_detail = " - Unable to get error details"

                        self.log_error(f"{name} registration failed: HTTP {response.status_code}{error_detail}")
                        failed_count += 1
                except requests.exceptions.Timeout:
                    self.log_error(f"{name} registration failed: Request timed out (10 seconds)")
                    failed_count += 1
                except requests.exceptions.ConnectionError as e:
                    self.log_error(f"{name} registration failed: Connection error - {e}")
                    failed_count += 1
                except Exception as e:
                    self.log_error(f"{name} registration failed: {e}")
                    failed_count += 1
            except Exception as e:
                self.log_error(f"[X] {name} registration failed: {e}")
                failed_count += 1
        
        # Display registration results
        if target_server:
            # Specified server mode: result display
            if registered_count > 0:
                self.log_success(f"Specified server {target_server} registered successfully")
            else:
                self.log_error(f"Specified server {target_server} registration failed")
        else:
            # All servers mode: result display
            if registered_count > 0:
                self.log_success(f"Automatic registration completed - Success: {registered_count}, Failed: {failed_count}")
            else:
                if mcp_servers:
                    self.log_error(f"Registration failed - Found {len(mcp_servers)} MCP servers, but all registration attempts failed")
                else:
                    self.log_warning("No registerable MCP servers found")
        
        # Verify registration results
        try:
            response = requests.get(f"{proxy_url}/proxy/status", timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                total_servers = status_data.get('total_servers', 0)
                registered_servers_dict = status_data.get('servers', {})
                
                if target_server:
                    # Specified server mode: check if target server is in registration list
                    if target_server in registered_servers_dict:
                        server_info = registered_servers_dict[target_server]
                        host = server_info.get('host', 'unknown')
                        port = server_info.get('port', 'unknown')
                        self.log_success(f"Verification successful: Successfully registered {target_server}({host}:{port}) to proxy server...")
                    else:
                        self.log_warning(f"Verification failed: {target_server} not found in proxy server registration list")
                        if self.verbose and registered_servers_dict:
                            self.log_debug(f"Currently registered servers: {', '.join(registered_servers_dict.keys())}")
                else:
                    # All servers mode: display overall status
                    self.log_info(f"Proxy server current registration status: {total_servers} servers")
                
                # Display all registered servers in verbose mode
                if self.verbose and registered_servers_dict:
                    self.log_debug("All registered servers:")
                    for server_name, server_info in registered_servers_dict.items():
                        host = server_info.get('host', 'unknown')
                        port = server_info.get('port', 'unknown')
                        self.log_debug(f"  {server_name}: {host}:{port}")
            else:
                self.log_warning(f"Failed to get proxy status: HTTP {response.status_code}")
        except Exception as e:
            self.log_debug(f"Failed to get proxy status: {e}")
    
    def _monitor_and_restart_servers(self):
        """Monitor and automatically restart servers (background thread)"""
        # Stop the old monitor thread
        self._stop_monitor_thread()
        
        # Create new stop event
        self._monitor_stop_event = threading.Event()
        
        def monitor_loop():
            while not self._monitor_stop_event.is_set():
                try:
                    # Get all server configurations
                    server_configs = self.get_server_configs()
                    enabled_servers = [s for s in server_configs if s.enabled and s.auto_restart]
                    
                    # Get currently running processes
                    processes = self.get_running_processes()
                    
                    for server in enabled_servers:
                        # Check if need to stop
                        if self._monitor_stop_event.is_set():
                            break
                            
                        # Check if server needs to restart
                        if server.name not in processes:
                            self.log_warning(f"Detected server {server.name} has stopped, attempting to restart...")
                            self.start_mcp_server(server)
                        else:
                            # Check if process is responsive
                            process = processes[server.name]
                            try:
                                if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
                                    self.log_warning(f"Detected unresponsive server {server.name}, attempting to restart...")
                                    self.stop_specific_server(server.name)
                                    time.sleep(2)
                                    self.start_mcp_server(server)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue
                    
                    # Use interruptible sleep
                    for _ in range(30):  # 30 seconds, check the stop signal once per second
                        if self._monitor_stop_event.is_set():
                            break
                        time.sleep(1)
                    
                except Exception as e:
                    self.log_debug(f"Monitor loop exception: {e}")
                    # Using interruptible sleep
                    for _ in range(60):  # 60 seconds, check the stop signal once per second
                        if self._monitor_stop_event.is_set():
                            break
                        time.sleep(1)
            
            self.log_debug("Server monitor thread has stopped")
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        self.log_debug("Server monitoring thread started")
    
    def _stop_monitor_thread(self):
        """Stop monitoring thread"""
        try:
            if self._monitor_stop_event is not None:
                self._monitor_stop_event.set()
            
            if self._monitor_thread is not None and self._monitor_thread.is_alive():
                self.log_debug("Waiting for monitor thread to stop...")
                self._monitor_thread.join(timeout=5)
                if self._monitor_thread.is_alive():
                    self.log_warning("Monitor thread stop timeout")
                else:
                    self.log_debug("Monitor thread has stopped")
            
            self._monitor_stop_event = None
            self._monitor_thread = None
        except Exception as e:
            self.log_debug(f"Exception occurred while stopping monitor thread: {e}")
            # reset state
            self._monitor_stop_event = None
            self._monitor_thread = None
    
    def _stop_process_and_children(self, name: str, process: psutil.Process, force: bool = False) -> int:
        """Stop the process and all its child processes"""
        try:
            self.log_info(f"Stopping {name} (PID: {process.pid})")
            
            # Get process tree (including all child processes)
            try:
                children = process.children(recursive=True)
                self.log_debug(f"{name} has {len(children)} child processes")
            except psutil.NoSuchProcess:
                children = []
            
            # Windows special handling: If it's a process group, try to terminate the entire process group
            if self.is_windows:
                success = self._terminate_windows_process_group(process, force)
                if success:
                    self.log_success(f"[OK] Stopping {name} (Windows process group)")
                    self._cleanup_pid_file(name)
                    return 1
            
            # Recursively stop all child processes
            for child in children:
                try:
                    self.log_debug(f"Stopping child process {child.pid}")
                    if force:
                        child.kill()
                    else:
                        child.terminate()
                        try:
                            child.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            child.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Stop the main process
            if force:
                process.kill()
            else:
                process.terminate()
                
            # Waiting for the process to end
            try:
                process.wait(timeout=5)
            except psutil.TimeoutExpired:
                self.log_warning(f"Process {name} stop timeout, forcing termination")
                process.kill()
                try:
                    process.wait(timeout=3)
                except psutil.TimeoutExpired:
                    self.log_error(f"Failed to force stop {name}")
            
            # Clean up PID files
            self._cleanup_pid_file(name)
            
            self.log_success(f"[OK] Stopped {name}")
            return 1
            
        except psutil.NoSuchProcess:
            self.log_info(f"{name} process does not exist")
            self._cleanup_pid_file(name)
            return 0
        except Exception as e:
            self.log_error(f"Failed to stop {name}: {e}")
            return 0
    
    def _terminate_windows_process_group(self, process: psutil.Process, force: bool = False) -> bool:
        """Terminate process group on Windows"""
        if not self.is_windows:
            return False
            
        try:
            # Terminate process tree using taskkill command on Windows
            if force:
                # Force terminate the entire process tree
                try:
                    cmd = ["taskkill", "/F", "/T", "/PID", str(process.pid)]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        self.log_debug(f"Windows process tree terminated successfully: PID {process.pid}")
                        return True
                    else:
                        self.log_debug(f"taskkill failed: {result.stderr}")
                        return False
                except subprocess.TimeoutExpired:
                    self.log_debug("taskkill timed out")
                    return False
                except Exception as e:
                    self.log_debug(f"taskkill exception: {e}")
                    return False
            else:
                # Gracefully terminate process tree
                try:
                    cmd = ["taskkill", "/T", "/PID", str(process.pid)]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        # Waiting for the process to end
                        try:
                            process.wait(timeout=5)
                            return True
                        except psutil.TimeoutExpired:
                            # Force termination after timeout
                            cmd_force = ["taskkill", "/F", "/T", "/PID", str(process.pid)]
                            subprocess.run(cmd_force, capture_output=True, timeout=5)
                            return True
                    else:
                        self.log_debug(f"taskkill graceful termination failed: {result.stderr}")
                        return False
                except subprocess.TimeoutExpired:
                    self.log_debug("taskkill graceful termination timed out")
                    return False
                except Exception as e:
                    self.log_debug(f"taskkill graceful termination exception: {e}")
                    return False
                    
        except Exception as e:
            self.log_debug(f"Windows process group termination failed: {e}")
            return False
    
    def _cleanup_all_litemcp_processes(self, force: bool = False) -> int:
        """Clean up all LiteMCP-related processes"""
        cleaned_count = 0
        
        try:
            # Find all possible LiteMCP-related processes
            litemcp_keywords = ['litemcp', 'cli.py', 'manage.py', 'src/cli.py']
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    
                    # Check if it's a LiteMCP-related process
                    is_litemcp = any(keyword in cmdline.lower() for keyword in litemcp_keywords)
                    
                    # Additional check: whether it contains our specific commands
                    if not is_litemcp:
                        is_litemcp = any(cmd in cmdline for cmd in ['serve', 'proxy', 'api']) and 'src/cli.py' in cmdline
                    
                    if is_litemcp:
                        # Exclude current management script process
                        current_pid = os.getpid()
                        if proc.info['pid'] == current_pid:
                            continue
                            
                        # Exclude all management script processes
                        if 'manage.py' in cmdline:
                            continue
                            
                        self.log_debug(f"Cleaning LiteMCP process: PID {proc.info['pid']}")
                        
                        if force:
                            proc.kill()
                        else:
                            proc.terminate()
                            try:
                                proc.wait(timeout=3)
                            except psutil.TimeoutExpired:
                                proc.kill()
                        
                        cleaned_count += 1
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                except Exception as e:
                    self.log_debug(f"Failed to clean up process: {e}")
                    
        except Exception as e:
            self.log_debug(f"Failed to scan processes: {e}")
        
        return cleaned_count
    
    def _cleanup_pid_file(self, name: str):
        """Clean up a single PID file"""
        pid_file = self.pid_dir / f"{name}.pid"
        if pid_file.exists():
            pid_file.unlink()
    
    def _cleanup_all_pid_files(self):
        """Clean up all PID files"""
        try:
            for pid_file in self.pid_dir.glob("*.pid"):
                pid_file.unlink()
                self.log_debug(f"Cleaning PID file: {pid_file.name}")
        except Exception as e:
            self.log_debug(f"Failed to clean up PID files: {e}")
    
    def start_servers(self, target_server: str = None, proxy_url: str = None):
        """Start servers"""
        if target_server:
            self.show_header("LiteMCP Framework", f"Starting specified server: {target_server}")
        else:
            self.show_header("LiteMCP Framework", "Starting server cluster")
        
        # Environment check
        self.show_section("Environment Check", self.icons['magnifying'])
        if not self.check_python_environment():
            return
        
        # Pre-cleanup check
        self.show_section("Pre-cleanup Check", self.icons['shield'])
        self.cleanup_dead_processes_and_ports()
        
        # Load remote services into memory
        self.show_section("Load Remote Services", self.icons['network'])
        self._load_remote_servers_to_memory()
        
        # Clean up registration records (scope depends on whether a server is specified)
        self.show_section("Clean Up Registration Records", self.icons['shield'])
        if target_server:
            # When starting a specific server, only clean up its registration records
            self.log_info(f"Cleaning registration records for specified server: {target_server}")
            self._cleanup_registry_for_server(target_server)
        else:
            # When starting all servers, clean up all local registration records (preserve remote service records)
            self.log_info("Cleaning registration records for all local servers, preserving remote service records")
            self._cleanup_local_registry_records()
        
        # Clean up existing servers
        self.show_section("Clean Up Existing Servers", self.icons['shield'])
        if target_server:
            self.stop_specific_server(target_server)
        else:
            self._cleanup_existing_servers_for_startup()
        
        # Get server configurations
        self.show_section("Read Configuration", self.icons['gear'])
        
        # Display configuration file information
        self.log_info(f"Configuration file: {self.config_file.name}")
        self.log_debug(f"Configuration file path: {self.config_file}")
        
        server_configs = self.get_server_configs()
        all_server_configs = server_configs.copy()  # Save all configurations for error messages
        
        if target_server:
            # Filter specified server
            server_configs = [s for s in server_configs if s.name == target_server]
            if not server_configs:
                self.log_error(f"Server configuration not found: {target_server}")
                available_servers = [s.name for s in all_server_configs]
                self.log_info(f"Available servers: {', '.join(available_servers)}")
                return
            
            # Display detailed configuration of the specified server
            for config in server_configs:
                self.log_info(f"Server {config.name} configuration:")
                if config.description:
                    self.log_info(f"  Description: {config.description}")
                self.log_debug(f"  server_type: {config.server_type}")
                self.log_debug(f"  transport: {config.transport}")
                self.log_debug(f"  host: {config.host}")
                self.log_debug(f"  port: {config.port}")
                self.log_debug(f"  enabled: {config.enabled}")
                self.log_debug(f"  auto_restart: {config.auto_restart}")
        else:
            # Display overview of all server configurations
            enabled_servers = [s for s in server_configs if s.enabled]
            disabled_servers = [s for s in server_configs if not s.enabled]
            
            self.log_info(f"There are {len(server_configs)} MCP servers in the configuration file")
            if enabled_servers:
                self.log_info(f"Enabled servers ({len(enabled_servers)}): {', '.join(s.name for s in enabled_servers)}")
            if disabled_servers:
                self.log_info(f"Disabled servers ({len(disabled_servers)}): {', '.join(s.name for s in disabled_servers)}")
            
            # Only start enabled servers
            server_configs = enabled_servers
        
        if not server_configs:
            self.log_warning("No servers available to start")
            return
        
        self.log_info(f"Preparing to start {len(server_configs)} servers", 
                     f"Servers: {', '.join(s.name for s in server_configs)}")
        
        # Start proxy server (only when starting all servers)
        proxy_started = False
        if not target_server:
            self.show_section("Start Proxy Server", self.icons['network'])
            proxy_started = self._start_proxy_server_enhanced()
        
        # Start MCP Servers
        self.show_section("Start MCP Servers", self.icons['server'])
        
        started_count = 0
        failed_count = 0
        
        for i, server_config in enumerate(server_configs, 1):
            self.log_step(f"Starting server: {server_config.name}", i, len(server_configs))
            
            if self.start_mcp_server(server_config):
                started_count += 1
            else:
                failed_count += 1
            
            time.sleep(1)  # Avoid port conflicts
        
        # Auto Register MCP Servers to Proxy
        should_register = False
        register_reason = ""
        
        if not target_server and proxy_started:
            # All servers started and local proxy started successfully
            should_register = True
            register_reason = "Local proxy server started successfully"
        elif target_server and proxy_url:
            # Specific server started with custom proxy URL provided
            should_register = True
            register_reason = f"Custom proxy address specified: {proxy_url}"
        elif not target_server and proxy_url:
            # All servers started with custom proxy URL provided (even if local proxy not started)
            should_register = True
            register_reason = f"Custom proxy address specified: {proxy_url}"
        elif target_server:
            # When starting specific server, check if proxy server is running
            running_processes = self.get_running_processes()
            if "proxy_server" in running_processes:
                should_register = True
                register_reason = "Detected local proxy server is running"
        
        if should_register:
            self.show_section("Register MCP Servers to Proxy", self.icons['gear'])
            self.log_info(f"Registration reason: {register_reason}")
            self._auto_register_servers_to_proxy(proxy_url, target_server)
        
        # Start API server (only when starting all servers)
        if not target_server:
            self.show_section("Start API Server", self.icons['network'])
            self._start_api_server_enhanced()
        
        # Start monitoring thread (only when starting all servers)
        if not target_server:
            self.show_section("Start Server Monitoring", self.icons['shield'])
            self._monitor_and_restart_servers()
        
        # Show results
        self.show_section("Startup Results", self.icons['chart'])
        if failed_count == 0:
            self.log_success(f"All servers started successfully! Success: {started_count}")
        else:
            self.log_warning(f"Some servers failed to start - Success: {started_count}, Failed: {failed_count}")
    
    def show_status(self):
        """Display server status"""
        self.show_header("LiteMCP Server Status")
        
        processes = self.get_running_processes()
        
        if RICH_AVAILABLE:
            table = Table(title="Server Status")
            table.add_column("Server", style="cyan", no_wrap=True)
            table.add_column("Status", style="green")
            table.add_column("Type", style="blue")
            table.add_column("Port", style="yellow")
            table.add_column("Access URL", style="magenta")
            table.add_column("PID", style="yellow")

            for name, process in processes.items():
                try:
                    # Get process information
                    cmdline = ' '.join(process.cmdline())

                    # Parse transport type
                    transport = "sse"
                    if "--transport" in cmdline:
                        transport_idx = cmdline.find("--transport") + len("--transport")
                        transport = cmdline[transport_idx:].split()[0]

                    # Parse port
                    port = "unknown"
                    if "--port" in cmdline:
                        port_idx = cmdline.find("--port") + len("--port")
                        port = cmdline[port_idx:].split()[0]

                    # Parse host
                    host = "localhost"
                    if "--host" in cmdline:
                        host_idx = cmdline.find("--host") + len("--host")
                        host = cmdline[host_idx:].split()[0]

                    # Build access URL
                    if port != "unknown":
                        # Build correct URL based on server type and transport mode
                        if name == "proxy_server":
                            # Proxy server doesn't need path
                            url = f"http://{host}:{port}"
                        elif name == "api_server":
                            # API server shows /docs path
                            url = f"http://{host}:{port}/docs"
                        elif transport == "http":
                            # HTTP mode MCP server shows /mcp path
                            url = f"http://{host}:{port}/mcp"
                        elif transport == "sse":
                            # SSE mode shows /sse path
                            url = f"http://{host}:{port}/sse"
                        else:
                            url = f"http://{host}:{port}"
                    else:
                        url = "N/A"

                    table.add_row(
                        name,
                        "[OK] Running",
                        transport,
                        port,
                        url,
                        str(process.pid)
                    )
                except psutil.NoSuchProcess:
                    table.add_row(name, "[X] Stopped", "N/A", "N/A", "N/A", "N/A")

            if not processes:
                table.add_row("No running servers", "", "", "", "", "")
            
            self.console.print(table)
        else:
            # Simple table display
            print(f"{'Server':<12} {'Status':<12} {'Type':<8} {'Port':<6} {'Access URL':<30} {'PID':<8}")
            print("-" * 80)

            for name, process in processes.items():
                try:
                    cmdline = ' '.join(process.cmdline())
                    transport = "sse"
                    port = "unknown"
                    host = "localhost"

                    if "--transport" in cmdline:
                        parts = cmdline.split("--transport")
                        if len(parts) > 1:
                            transport = parts[1].split()[0]

                    if "--port" in cmdline:
                        parts = cmdline.split("--port")
                        if len(parts) > 1:
                            port = parts[1].split()[0]

                    if "--host" in cmdline:
                        parts = cmdline.split("--host")
                        if len(parts) > 1:
                            host = parts[1].split()[0]

                    # Build access URL
                    if port != "unknown":
                        # Build correct URL based on server type and transport mode
                        if name == "proxy_server":
                            # Proxy server doesn't need path
                            url = f"http://{host}:{port}"
                        elif name == "api_server":
                            # API server shows /docs path
                            url = f"http://{host}:{port}/docs"
                        elif transport == "http":
                            # HTTP mode MCP server shows /mcp path
                            url = f"http://{host}:{port}/mcp"
                        elif transport == "sse":
                            # SSE mode shows /sse path
                            url = f"http://{host}:{port}/sse"
                        else:
                            url = f"http://{host}:{port}"
                    else:
                        url = "N/A"

                    print(f"{name:<12} {'[OK] Running':<12} {transport:<8} {port:<6} {url:<30} {process.pid:<8}")
                except psutil.NoSuchProcess:
                    print(f"{name:<12} {'[X] Stopped':<12} {'N/A':<8} {'N/A':<6} {'N/A':<30} {'N/A':<8}")

            if not processes:
                print("No running servers")
    
    def show_logs(self):
        """Display log information"""
        self.show_header("LiteMCP Server Logs")
        
        log_files = list(self.log_dir.glob("*.log"))
        
        if not log_files:
            self.log_info("No log files available")
            return
        
        if RICH_AVAILABLE:
            table = Table(title="Available Log Files")
            table.add_column("Log File", style="cyan")
            table.add_column("Size", style="green")
            table.add_column("Modified Time", style="yellow")
            
            for log_file in log_files:
                stat = log_file.stat()
                size = f"{stat.st_size / 1024:.1f} KB"
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                table.add_row(log_file.name, size, mtime)
            
            self.console.print(table)
        else:
            print(f"{'Log File':<20} {'Size':<10} {'Modified Time':<20}")
            print("-" * 55)
            
            for log_file in log_files:
                stat = log_file.stat()
                size = f"{stat.st_size / 1024:.1f} KB"
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                print(f"{log_file.name:<20} {size:<10} {mtime:<20}")

        print()
        self.log_info("View specific logs", f"tail -f {self.log_dir}/<server_name>.log")
        self.log_info("View all logs", f"tail -f {self.log_dir}/*.log")

    def health_check(self):
        """Perform health check

        Check the running status, port occupancy, process health of all servers, etc.
        """
        self.show_section("Health Check", self.icons['shield'])

        # Check configuration file
        if not self.config_file.exists():
            self.log_error(f"Configuration file does not exist: {self.config_file}")
            return False

        # Load configurations
        try:
            configs = self.get_server_configs()
        except Exception as e:
            self.log_error(f"Failed to load configuration file: {e}")
            return False

        # Check each server
        for config in configs:
            if not config.enabled:
                self.log_info(f"Skip disabled server: {config.name}")
                continue

            self.log_info(f"Check server: {config.name}")

            # Check PID file
            pid_file = self.pid_dir / f"{config.name}.pid"
            if not pid_file.exists():
                self.log_warning(f"PID file does not exist: {config.name}")
                continue

            try:
                pid = int(pid_file.read_text().strip())
            except (ValueError, IOError) as e:
                self.log_error(f"Failed to read PID file: {e}")
                continue

            # Check if process exists
            try:
                process = psutil.Process(pid)
                if not process.is_running():
                    self.log_error(f"Process stopped: {config.name} (PID: {pid})")
                    continue
            except psutil.NoSuchProcess:
                self.log_error(f"Process does not exist: {config.name} (PID: {pid})")
                continue

            # Check port occupancy
            if config.port:
                if not self._is_port_available(config.port):
                    # Check if occupied by other LiteMCP processes
                    if not self._cleanup_port_if_litemcp(config.port):
                        self.log_error(f"Port occupied: {config.port}")
                        continue

            # Check log file
            log_file = self.log_dir / f"{config.name}.log"
            if not log_file.exists():
                self.log_warning(f"Log file does not exist: {config.name}")
            else:
                try:
                    # Check log file size
                    log_size = log_file.stat().st_size
                    if log_size > 100 * 1024 * 1024:  # 100MB
                        self.log_warning(f"Log file too large: {config.name} ({log_size / 1024 / 1024:.1f}MB)")
                except IOError as e:
                    self.log_error(f"Failed to read log file: {e}")

            # Check server health status
            try:
                # Check process status
                process_status = process.status()
                memory_info = process.memory_info()
                cpu_percent = process.cpu_percent()

                # For network servers, check if endpoint is accessible
                endpoint_ok = True
                if config.port and config.transport in ["http", "sse"]:
                    endpoint_ok = self._check_server_endpoint(config.name, config.host, config.port, config.transport)

                if endpoint_ok:
                    self.log_success(f"Server running normally: {config.name}")
                    self.log_info(f"  PID: {pid}")
                    self.log_info(f"  Status: {process_status}")
                    self.log_info(f"  Memory: {memory_info.rss / 1024 / 1024:.1f}MB")
                    self.log_info(f"  CPU: {cpu_percent:.1f}%")
                    if config.port:
                        self.log_info(f"  Port: {config.port}")
                else:
                    self.log_error(f"Server endpoint inaccessible: {config.name}")
            except Exception as e:
                self.log_error(f"Health check failed: {config.name} - {e}")

        # Show check results
        if self.error_count == 0 and self.warning_count == 0:
            self.log_success("All servers are running normally")
        else:
            self.log_warning(f"Check completed - {self.error_count} errors, {self.warning_count} warnings")

        return self.error_count == 0

    @staticmethod
    def _check_server_endpoint(server_name: str, host: str, port: int, transport: str) -> bool:
        """Check if server endpoint is accessible"""
        try:
            # Build URL
            if transport == "http":
                url = f"http://{host}:{port}/"
            elif transport == "sse":
                url = f"http://{host}:{port}/sse"
            else:
                return True  # Skip check for other transport types

            # Create request
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'LiteMCP-HealthCheck/1.0')

            # Attempt connection (with short timeout)
            response = urllib.request.urlopen(request, timeout=5)
            return response.getcode() in [200, 404]  # 200 is OK, 404 also means server is running

        except ImportError:
            # Skip network check if imports fail
            return True
        except Exception:
            # Catch all exceptions including urllib.error.URLError
            return False

    def clean_files(self):
        """Clean up files"""
        self.show_header("Clean Up System Files")
        
        # Clean up log files
        log_files = list(self.log_dir.glob("*.log"))
        for log_file in log_files:
            log_file.unlink()
        
        # Clean up PID files
        pid_files = list(self.pid_dir.glob("*.pid"))
        for pid_file in pid_files:
            pid_file.unlink()
        
        self.log_success("Cleanup completed", f"Deleted {len(log_files)} log files and {len(pid_files)} PID files")
    
    def install_dependencies(self):
        """Install dependencies"""
        self.show_header("Install/Update Project Dependencies")
        
        # Required dependencies
        required_packages = [
            "psutil",
            "pyyaml", 
            "requests"
        ]
        
        # Optional dependencies
        optional_packages = [
            "rich"
        ]
        
        all_success = True
        
        if self.use_poetry:
            self.log_info("Installing dependencies with Poetry...")
            
            # Check and update Poetry lock file
            if not self._check_and_update_poetry_lock():
                self.log_warning("Poetry lock file update failed, but continuing installation attempt")
            
            try:
                result = subprocess.run(["poetry", "install", "--no-interaction"], 
                                      cwd=self.project_dir, check=True)
                self.log_success("Poetry dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                self.log_error(f"Failed to install Poetry dependencies: {e}")
                all_success = False
        else:
            # Install using pip
            requirements_file = self.project_dir / "requirements.txt"
            if requirements_file.exists():
                self.log_info("Installing project dependencies with pip...")
                try:
                    result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)], 
                                          cwd=self.project_dir, check=True)
                    self.log_success("Project dependencies installed successfully")
                except subprocess.CalledProcessError as e:
                    self.log_error(f"Failed to install project dependencies: {e}")
                    all_success = False
            
            # Check and install necessary dependencies for management tools
            self.log_info("Checking management tool dependencies...")
            
            for package in required_packages:
                if not self._check_package_installed(package):
                    if not self._install_package(package):
                        all_success = False
                else:
                    self.log_success(f"{package} is already installed")
            
            # Install optional dependencies
            for package in optional_packages:
                if not self._check_package_installed(package):
                    self._install_package(package, optional=True)
                else:
                    self.log_success(f"{package} is already installed")
        
        # Show usage examples
        if all_success:
            self._show_usage_examples()
            self.log_success("Dependency installation completed!")
        else:
            self.log_warning("Some dependencies failed to install, but core functionality is still available")

    def _check_and_update_poetry_lock(self) -> bool:
        """Check and update Poetry lock file"""
        try:
            # Check if pyproject.toml and poetry.lock files exist
            pyproject_file = self.project_dir / "pyproject.toml"
            poetry_lock_file = self.project_dir / "poetry.lock"
            
            if not pyproject_file.exists():
                self.log_warning("pyproject.toml file does not exist, skipping lock file check")
                return True
            
            # First, try the poetry check command to check the project status
            try:
                result = subprocess.run(["poetry", "check"], 
                                      cwd=self.project_dir, 
                                      capture_output=True, 
                                      text=True)
                
                if result.returncode == 0:
                    self.log_debug("Poetry project status check passed")
                    return True
                else:
                    self.log_debug(f"Poetry project status check failed: {result.stderr}")
                    
            except Exception as e:
                self.log_debug(f"Poetry project status check exception: {e}")
            
            # If poetry.lock does not exist or check fails, try to update lock file
            if not poetry_lock_file.exists():
                self.log_info("poetry.lock file does not exist, generating lock file...")
                lock_command = ["poetry", "lock"]
            else:
                self.log_info("Detected outdated lock file, updating lock file...")
                lock_command = ["poetry", "lock"]
            
            # Execute the poetry lock command
            try:
                result = subprocess.run(lock_command, 
                                      cwd=self.project_dir, 
                                      capture_output=True, 
                                      text=True,
                                      timeout=300)  # 5-minute timeout
                
                if result.returncode == 0:
                    self.log_success("Poetry lock file updated successfully")
                    return True
                else:
                    self.log_error(f"Failed to update Poetry lock file: {result.stderr}")
                    
                    # If the lock file update fails, try deleting the lock file and rebuilding it
                    if poetry_lock_file.exists():
                        try:
                            self.log_info("Deleting old lock file and regenerating...")
                            poetry_lock_file.unlink()
                            
                            retry_result = subprocess.run(["poetry", "lock"], 
                                                        cwd=self.project_dir, 
                                                        capture_output=True, 
                                                        text=True,
                                                        timeout=300)
                            
                            if retry_result.returncode == 0:
                                self.log_success("Poetry lock file regenerated successfully")
                                return True
                            else:
                                self.log_error(f"Failed to regenerate Poetry lock file: {retry_result.stderr}")
                        except Exception as e:
                            self.log_error(f"Failed to delete old lock file: {e}")
                    
                    return False
                    
            except subprocess.TimeoutExpired:
                self.log_error("Poetry lock file update timed out")
                return False
            except Exception as e:
                self.log_error(f"Poetry lock file update exception: {e}")
                return False
                
        except Exception as e:
            self.log_error(f"Failed to check Poetry lock file: {e}")
            return False

    @staticmethod
    def _check_package_installed(package_name: str) -> bool:
        """Check if package is installed"""
        try:
            __import__(package_name)
            return True
        except ImportError:
            return False
    
    def _install_package(self, package_name: str, optional: bool = False) -> bool:
        """Install Python package"""
        try:
            self.log_info(f"Installing {package_name}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_name],
                capture_output=True,
                text=True,
                check=True
            )
            self.log_success(f"{package_name} installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            if optional:
                self.log_warning(f"{package_name} installation failed (optional dependency)")
                return False
            else:
                self.log_error(f"{package_name} installation failed: {e}")
                return False
    
    def _show_usage_examples(self):
        """Show usage examples"""
        self.show_section("Usage Examples", self.icons['rocket'])
        
        if self.is_windows:
            self.log_info("Windows Users:")
            print("  scripts\\manage_py.bat up        # Start all servers")
            print("  scripts\\manage_py.bat ps        # Check status")
            print("  scripts\\manage_py.bat down      # Stop all servers")
            print("  scripts\\manage_py.bat --help    # Show help")
            print()
            print("Or use Python directly:")
            print("  python scripts\\manage.py up")
        else:
            self.log_info("Linux/macOS Users:")
            print("  python3 scripts/manage.py up     # Start all servers")
            print("  python3 scripts/manage.py ps     # Check status")
            print("  python3 scripts/manage.py down   # Stop all servers")
            print("  python3 scripts/manage.py --help # Show help")
            print()
            print("You can set an alias for easier use:")
            print("  alias litemcp='python3 scripts/manage.py'")
            print("  litemcp up")
        
        print()
        self.log_info("Specific server operations:")
        print("  python scripts/manage.py up -n example      # Start only example server")
        print("  python scripts/manage.py down --name school # Stop only school server")
        print()
        self.log_info("Verbose mode:")
        print("  python scripts/manage.py up --verbose       # Show detailed information")
        print("  python scripts/manage.py install --verbose  # Show detailed information when installing dependencies")

    def show_config(self):
        """Show configuration"""
        self.show_header("LiteMCP Current Configuration")
        
        if self.config_file.exists():
            self.log_info(f"Configuration file: {self.config_file}")
            print()
            
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if RICH_AVAILABLE:
                    syntax = Syntax(content, "yaml", theme="github-dark", line_numbers=True)
                    self.console.print(Panel(syntax, title="Configuration Content", border_style="cyan"))
                else:
                    print("Configuration Content:")
                    print("-" * 60)
                    print(content)
                    print("-" * 60)
            except Exception as e:
                self.log_error(f"Failed to read configuration file: {e}")
        else:
            self.log_error(f"Configuration file does not exist: {self.config_file}")
    
    def start_api_server_standalone(self):
        """Start API server standalone"""
        self.show_header("LiteMCP API Server", "Standalone Mode")
        
        # Environment check
        if not self.check_python_environment():
            return
        
        # Stop potentially running API server
        self.stop_specific_server("api_server")
        
        # Get configuration
        config = self.load_config()
        api_config = config.get('api_server', {})
        
        # Handle enabled configuration
        enabled_value = api_config.get('enabled', True)
        if isinstance(enabled_value, str):
            enabled = enabled_value.lower() in ('true', 'yes', '1', 'on')
        else:
            enabled = bool(enabled_value)
        
        if not enabled:
            self.log_warning("API server is disabled in configuration file")
            return
        
        host = self.resolve_host_address(
            api_config.get('host', 'null'), 
            'api_server', 
            'ip'
        )
        
        # Process port configuration
        port_value = api_config.get('port', 9000)
        try:
            port = int(port_value)
        except (ValueError, TypeError):
            port = 9000
            
        self.log_debug(f"API server configuration: host={host}, port={port}, enabled={enabled}")
        
        # Check port availability
        if not self._is_port_available(port):
            self.log_error(f"Port {port} is already occupied")
            return
        
        # Start API server
        log_file = self.log_dir / "api_server.log"
        pid_file = self.pid_dir / "api_server.pid"
        
        cmd_base = [
            sys.executable, "src/cli.py", "api",
            "--host", host,
            "--port", str(port)
        ]
        
        if self.use_poetry:
            cmd = ["poetry", "run"] + cmd_base
        else:
            cmd = cmd_base
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                if self.is_windows:
                    process = subprocess.Popen(
                        cmd,
                        cwd=self.project_dir,
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    process = subprocess.Popen(
                        cmd,
                        cwd=self.project_dir,
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        preexec_fn=os.setsid
                    )
            
            # Save PID
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # Wait for startup
            time.sleep(3)
            
            if process.poll() is None and not self._is_port_available(port):
                # Obtain the host address for display purposes
                display_host = self.resolve_host_address(api_config.get('host', 'null'), 'api_server', 'display')
                self.log_success("[OK] API server started successfully")
                self.log_info(f"   Access address: http://{display_host}:{port}")
                self.log_info(f"   Log file: {log_file}")
                self.log_info(f"   Process PID: {process.pid}")
            else:
                self.log_error("[X] API server failed to start")
                return False
                
        except Exception as e:
            self.log_error(f"Failed to start API server: {e}")
            return False
        
        return True
    
    def start_proxy_server_standalone(self):
        """Start proxy server standalone"""
        self.show_header("LiteMCP Proxy Server", "Standalone Mode")
        
        # Environment check
        if not self.check_python_environment():
            return
        
        # Stop potentially running proxy server
        self.stop_specific_server("proxy_server")
        
        # Get configuration
        config = self.load_config()
        proxy_config = config.get('proxy_server', {})
        
        # Handle enabled configuration
        enabled_value = proxy_config.get('enabled', True)
        if isinstance(enabled_value, str):
            enabled = enabled_value.lower() in ('true', 'yes', '1', 'on')
        else:
            enabled = bool(enabled_value)
        
        if not enabled:
            self.log_warning("Proxy server is disabled in configuration file")
            return
        
        host = self.resolve_host_address(
            proxy_config.get('host', 'localhost'), 
            'proxy_server', 
            'localhost'
        )
        
        # Process port configuration
        port_value = proxy_config.get('port', 1888)
        try:
            port = int(port_value)
        except (ValueError, TypeError):
            port = 1888
            
        self.log_debug(f"Proxy server configuration: host={host}, port={port}, enabled={enabled}")
        
        # Check port availability
        if not self._is_port_available(port):
            self.log_error(f"Port {port} is already occupied")
            return
        
        # Start proxy server
        log_file = self.log_dir / "proxy_server.log"
        pid_file = self.pid_dir / "proxy_server.pid"
        
        cmd_base = [
            sys.executable, "src/cli.py", "proxy",
            "--host", host,
            "--port", str(port)
        ]
        
        if self.use_poetry:
            cmd = ["poetry", "run"] + cmd_base
        else:
            cmd = cmd_base
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                if self.is_windows:
                    process = subprocess.Popen(
                        cmd,
                        cwd=self.project_dir,
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    process = subprocess.Popen(
                        cmd,
                        cwd=self.project_dir,
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        preexec_fn=os.setsid
                    )
            
            # Save PID
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # Wait for startup
            time.sleep(3)
            
            if process.poll() is None and not self._is_port_available(port):
                # Obtain the host address for display purposes
                display_host = self.resolve_host_address(proxy_config.get('host', 'localhost'), 'proxy_server', 'display')
                self.log_success("[OK] Proxy server started successfully")
                self.log_info(f"   Access address: http://{display_host}:{port}")
                self.log_info(f"   Log file: {log_file}")
                self.log_info(f"   Process PID: {process.pid}")
            else:
                self.log_error("[X] Proxy server failed to start")
                return False
                
        except Exception as e:
            self.log_error(f"Failed to start proxy server: {e}")
            return False
        
        return True
    
    def diagnose_system(self):
        """System diagnostic function"""
        self.show_header("LiteMCP System Diagnosis")
        
        # Python environment check
        self.show_section("Python Environment Check", self.icons['magnifying'])
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        self.log_info(f"Python version: Python {python_version}")
        self.log_info(f"Python path: {sys.executable}")
        self.log_info(f"Project directory: {self.project_dir}")
        self.log_info(f"Current working directory: {os.getcwd()}")
        
        # Module import check
        self.show_section("Module Import Check", self.icons['gear'])
        try:
            self.log_success("src.core.utils: [OK] Success")
        except Exception as e:
            self.log_error(f"Module import test failed: {e}")
        
        # Port allocation test
        self.show_section("Port Allocation Test", self.icons['lightning'])
        self.log_info("Testing smart port allocation...")
        
        try:
            # Test port allocation for several services
            for service in ['example', 'school', 'pm', 'sonic']:
                port = self.get_smart_port_for_service(service)
                self.log_success(f"{service}: {port}")
        except Exception as e:
            self.log_error(f"Port allocation test failed: {e}")
        
        # Network status check
        self.show_section("Network Status Check", self.icons['network'])
        self.log_info("Checking port occupancy for ports 8000-8010:")
        
        for port in range(8000, 8011):
            if self._is_port_available(port):
                self.log_info(f"Port {port} is available")
            else:
                self.log_warning(f"Port {port} is occupied")
        
        # Current process check
        self.show_section("Current LiteMCP Process Check", self.icons['server'])
        processes = self.get_running_processes()
        
        if processes:
            self.log_info("Found LiteMCP-related processes:")
            for name, process in processes.items():
                try:
                    cmdline = ' '.join(process.cmdline())
                    self.log_info(f"  {name} (PID: {process.pid})")
                    self.log_debug(f"    Command line: {cmdline}")
                except psutil.NoSuchProcess:
                    self.log_warning(f"  {name} process does not exist")
        else:
            self.log_info("No running LiteMCP processes found")
        
        # PID file check
        self.show_section("PID File Check", self.icons['chart'])
        pid_files = list(self.pid_dir.glob("*.pid"))
        
        if pid_files:
            self.log_info("Found PID files:")
            for pid_file in pid_files:
                try:
                    with open(pid_file, 'r') as f:
                        pid = int(f.read().strip())
                    
                    if psutil.pid_exists(pid):
                        self.log_success(f"  {pid_file.stem} (PID: {pid}) - Process running")
                    else:
                        self.log_warning(f"  {pid_file.stem} (PID: {pid}) - Process does not exist")
                except Exception as e:
                    self.log_error(f"  {pid_file.stem} - Failed to read: {e}")
        else:
            self.log_info("No PID files found")
        
        # Registry check
        self.show_section("Registry Check", self.icons['gear'])
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
                
                self.log_info(f"  Registry entries: {len(registry)}")
                for key, info in registry.items():
                    name = info.get('name', 'unknown')
                    host = info.get('host', 'unknown')
                    port = info.get('port', 'unknown')
                    transport = info.get('transport', 'unknown')
                    pid = info.get('pid', 'unknown')
                    self.log_info(f"  {name}: {host}:{port} ({transport}) PID:{pid}")
            except Exception as e:
                    self.log_error(f"Failed to read registry: {e}")
        else:
            self.log_info("Registry file does not exist")
    
    def cleanup_dead_processes(self):
        """Clean up dead processes and zombie ports"""
        self.show_header("Clean Up Dead Processes and Zombie Ports")
        
        cleaned_pids = 0
        cleaned_processes = 0
        cleaned_ports = 0
        
        # Clean up invalid PID files
        self.log_info("Cleaning up invalid PID files...")
        pid_files = list(self.pid_dir.glob("*.pid"))
        
        for pid_file in pid_files:
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                if not psutil.pid_exists(pid):
                    pid_file.unlink()
                    cleaned_pids += 1
                    self.log_success(f"Cleaned up invalid PID file: {pid_file.name}")
            except Exception as e:
                self.log_warning(f"Failed to process PID file {pid_file.name}: {e}")
        
        # Clean up orphan processes
        self.log_info("Searching for orphan processes...")
        try:
            for process in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(process.info['cmdline'] or [])
                    if ('cli.py serve' in cmdline or 
                        'cli.py api' in cmdline or 
                        'cli.py proxy' in cmdline):
                        
                        # Check if there is a corresponding PID file
                        has_pid_file = False
                        for pid_file in self.pid_dir.glob("*.pid"):
                            try:
                                with open(pid_file, 'r') as f:
                                    file_pid = int(f.read().strip())
                                if file_pid == process.info['pid']:
                                    has_pid_file = True
                                    break
                            except:
                                continue
                        
                        if not has_pid_file:
                            process.terminate()
                            cleaned_processes += 1
                            self.log_success(f"Clean up orphan process: PID {process.info['pid']}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.log_warning(f"Failed to clean up orphan processes: {e}")
        
        # Clean up local service registry records (keep remote service records)
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
                
                # Only keep remote server records
                cleaned_registry = {}
                for server_id, info in registry.items():
                    if not self._is_local_server(info):
                        # Keep remote server record
                        cleaned_registry[server_id] = info
                        server_name = info.get('name', 'unknown')
                        host = info.get('host', 'unknown')
                        self.log_info(f"Keep remote service record: {server_name} ({host})")
                
                # Write back cleaned registry
                with open(self.registry_file, 'w', encoding='utf-8') as f:
                    json.dump(cleaned_registry, f, indent=2, ensure_ascii=False)
                
                cleared_count = len(registry) - len(cleaned_registry)
                if cleared_count > 0:
                    self.log_success(f"Clean up local registry records: {cleared_count}")
                else:
                    self.log_info("No local registry records need to be cleaned up")
                    
            except Exception as e:
                self.log_warning(f"Failed to clean up registry: {e}")
        
        self.log_info(f"Cleanup completed: {cleaned_pids} PID files, {cleaned_processes} orphan processes, {cleaned_ports} zombie ports")
    
    def init_project(self):
        """Initialize project (first installation)"""
        self.show_header("LiteMCP Framework Project Initialization", "First Installation and Configuration")
        
        # 1. Python version check
        self.show_section("Python Environment Check", self.icons['magnifying'])
        if not self.check_python_environment():
            self.log_error("Python environment does not meet requirements, initialization failed")
            return False
        
        # 2. Install dependencies
        self.show_section("Install Dependencies", self.icons['gear'])
        self.install_dependencies()
        
        # 3. Create necessary directories
        self.show_section("Create Directory Structure", self.icons['shield'])
        self._create_project_directories()
        
        # 4. Verify installation
        self.show_section("Verify Installation", self.icons['star'])
        if self._test_installation():
            self.show_section("Initialization Completed", self.icons['rocket'])
            self.log_success("[DONE] LiteMCP Framework initialization successful!")
            self._show_quick_start_guide()
            return True
        else:
            self.log_error("Initialization verification failed")
            return False
    
    def _create_project_directories(self):
        """Create necessary project directories"""
        directories = [
            self.log_dir,
            self.pid_dir,
            self.project_dir / "runtime" / "cache"
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                self.log_success(f"Create directory: {directory.relative_to(self.project_dir)}")
            except Exception as e:
                self.log_error(f"Failed to create directory {directory}: {e}")
    
    def _test_installation(self):
        """Test if installation is successful"""
        self.log_info("Running health check...")
        
        try:
            # Test core functionality
            config = self.load_config()
            if not config:
                self.log_error("Failed to load configuration file")
                return False
            
            # Test server configuration analysis
            server_configs = self.get_server_configs()
            if not server_configs:
                self.log_warning("No server configuration found, but core functions are normal")
            else:
                self.log_success(f"Found {len(server_configs)} server configurations")
            
            # Test port allocation
            try:
                port = self.get_available_port()
                self.log_success(f"Port allocation test passed: {port}")
            except Exception as e:
                self.log_error(f"Port allocation test failed: {e}")
                return False
            
            self.log_success("Installation verification passed")
            return True
            
        except Exception as e:
            self.log_error(f"Installation verification failed: {e}")
            return False
    
    def _show_quick_start_guide(self):
        """Show quick start guide"""
        self.show_section("Quick Start Guide", self.icons['fire'])
        
        print("> You can now start using LiteMCP Framework!")
        print()
        
        self.log_info("1. Check current status:")
        print("   python3 scripts/manage.py ps")
        print()
        
        self.log_info("2. Start all servers:")
        print("   python3 scripts/manage.py up")
        print()
        
        self.log_info("3. Start specific server:")
        print("   python3 scripts/manage.py up --name example")
        print()
        
        self.log_info("4. Register to remote proxy:")
        print("   python3 scripts/manage.py up --proxy-url http://192.168.1.100:1888")
        print()
        
        self.log_info("5. View help information:")
        print("   python3 scripts/manage.py --help")
        print()
        
        self.log_info("6. System diagnosis:")
        print("   python3 scripts/manage.py diagnose")
        print()
        
        if self.is_windows:
            self.log_info("Windows users can also use batch files:")
            print("   scripts\\manage_py.bat up")
        else:
            self.log_info("It is recommended to set up an alias for easier use:")
            print("   echo 'alias litemcp=\"python3 scripts/manage.py\"' >> ~/.bashrc")
            print("   source ~/.bashrc")
            print("   litemcp up")
        
        print()
        self.log_success("Enjoy your usage! [DONE]")
    
    def show_help(self):
        """Show beautifully formatted help information"""
        self.show_header("LiteMCP Framework Management Tool")
        
        print()
        print("Usage: python scripts/manage.py <command> [options]")
        print()
        
        self.log_info("[TIP] Two command styles are supported:")
        print()
        
        print("[EDIT] Detailed commands (recommended for scripts):")
        print("  start         Start all configured servers")
        print("  stop          Stop all servers")
        print("  restart       Restart all servers")
        print("  status        View server status")
        print("  api           Start API server only")
        print("  proxy         Start proxy server only")
        print("  install       Install/update dependencies (automatically handle Poetry lock file)")
        print("  logs          View logs")
        print("  clean         Clean logs and PID files")
        print("  cleanup       Clean up dead processes and zombie ports")
        print("  health        Health check")
        print("  config        Show current configuration")
        print("  diagnose      System diagnosis")
        print("  init          Initialize project (first use)")
        print("  unregister    Unregister MCP server from proxy")
        print("  validate      Validate consistency between registry and configuration file")
        print("  fix           Clean up invalid records in registry")
        print()
        
        print("* Quick commands (recommended for daily use):")
        print("  up            > Start all servers (same as start)")
        print("  down          [STOP]  Stop all servers (same as stop --force)")
        print("  reboot        [SYNC] Restart all servers (same as restart)")
        print("  ps            [G] View server status (same as status)")
        print("  log           [EDIT] View log information (same as logs)")
        print("  check         [HEART] System health check (same as health)")
        print("  setup         [PKG] Install/update dependencies (same as install, automatically handle Poetry lock file)")
        print("  clear         [CLEAN] Clean temporary files (same as clean)")
        print("  conf          [#]  View configuration information (same as config)")
        print()

        print("[TARGET] General Options:")
        print("  --name, -n <server_name>    Specify server name to operate")
        print("  --proxy-url <address>       Specify proxy server address (e.g.: http://192.168.1.100:1888)")
        print("  --force                    Force execute operation")
        print("  --verbose                  Show verbose output")
        print("  --dry-run                  Only show what would be executed")
        print()

        print("[=] Usage Examples:")
        print("  python scripts/manage.py up                                  # Start all servers")
        print("  python scripts/manage.py up example                          # Start only example server")
        print("  python scripts/manage.py up --name example                   # Start only example server (equivalent)")
        print(
            "  python scripts/manage.py up --proxy-url http://192.168.1.100:1888  # Start and register to remote proxy")
        print("  python scripts/manage.py down school                         # Stop only school server")
        print("  python scripts/manage.py reboot pm                           # Restart only pm server")
        print("  python scripts/manage.py api                                 # Start only API server")
        print("  python scripts/manage.py proxy                               # Start only proxy server")
        print("  python scripts/manage.py init                                # First-time project initialization")
        print(
            "  python scripts/manage.py unregister --proxy-url http://192.168.1.100:1888  # Unregister all servers from proxy")
        print(
            "  python scripts/manage.py unregister --name example --proxy-url http://192.168.1.100:1888  # Unregister specific server from proxy")
        print(
            "  python scripts/manage.py validate                           # Validate registry and config consistency")
        print("  python scripts/manage.py fix                                # Clean invalid records in registry")
        print()

        print("[BUG] Debugging and Diagnosis:")
        print("  python scripts/manage.py diagnose              # Comprehensive system diagnosis")
        print("  python scripts/manage.py up --verbose          # Show detailed startup information")
        print("  python scripts/manage.py cleanup               # Clean dead processes and zombie ports")
        print("  python scripts/manage.py down --force          # Force stop all servers and child processes")
        print()

        print("[TIP] Server Specification Instructions:")
        print("  - Two syntaxes supported for server specification:")
        print("    * Positional argument: python scripts/manage.py up example")
        print("    * Option argument: python scripts/manage.py up --name example")
        print("  - Positional argument takes precedence over --name parameter")
        print("  - Supported commands: start/stop/restart/up/down/reboot")
        print("  - Starting specific server won't start proxy and API servers")
        print("  - But can register to remote proxy via --proxy-url parameter")
        print("  - Shows available server list if specified server doesn't exist")
        print()

        print("[ENHANCED] Enhanced Stop Functionality:")
        print("  - Automatically stops monitoring threads to prevent process residue")
        print("  - Recursively cleans all child processes and process trees")
        print("  - Windows system optimization: uses taskkill for process groups")
        print("  - Supports force mode (--force) to thoroughly clean all related processes")
        print("  - Automatically cleans orphan processes and zombie ports")
        print("  - Complete stop with single execution, no need for multiple runs")
        print("  - Intelligently distinguishes local and remote services, only cleans local service records")
        print()

        print("[NETWORK] Proxy Registration and Unregistration:")
        print("  - Registration: Automatically register to remote proxy via --proxy-url when starting server")
        print("  - Unregistration: Use unregister command to unregister server from proxy")
        print("  - Support specific server operations: --name parameter to specify server")
        print("  - Support batch operations: operate all servers when no server name is specified")
        print("  - Auto-retry mechanism: automatically retry on network request failure")
        print("  - Status verification: verify proxy status after operation")
        print()

        if self.is_windows:
            print("[WIN] Windows Users:")
            print("  - Direct usage: python scripts\\manage.py <command>")
            print("  - Or set alias: doskey litemcp=python scripts\\manage.py $*")
        else:
            print("[LINUX] Linux/macOS Users:")
            print("  - Direct usage: python3 scripts/manage.py <command>")
            print("  - Recommended alias: alias litemcp='python3 scripts/manage.py'")

    @staticmethod
    def _is_process_alive_and_healthy(pid: int) -> bool:
        """Check if process is alive and healthy (consistent with logic elsewhere)"""
        try:
            if not psutil.pid_exists(pid):
                return False
            
            process = psutil.Process(pid)
            # Check if process is running and not a zombie process
            return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False

    def _is_server_running_by_port_and_process(self, server_name: str, port: int) -> bool:
        """Check if server is running through port and process command line"""
        try:
            # Check if any LiteMCP process is using this server name or port
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])

                    # Check if it's a LiteMCP process
                    if 'src/cli.py' in cmdline and 'serve' in cmdline:
                        # Check if server name matches
                        server_name_match = f'--server {server_name}' in cmdline
                        # Check if port matches (via --port parameter)
                        port_match = f'--port {port}' in cmdline

                        if server_name_match or port_match:
                            # Check if process is healthy
                            if self._is_process_alive_and_healthy(proc.pid):
                                return True

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return False

        except Exception as e:
            self.log_debug(f"Failed to check server status through port: {e}")
            return False

    def cleanup_dead_processes_and_ports(self):
        """Clean up dead processes and zombie ports before startup"""
        # Clean up processes that don't exist in PID files
        for pid_file in self.pid_dir.glob('*.pid'):
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                if not self._is_process_alive_and_healthy(pid):
                    self.log_warning(f"Clean up invalid PID file: {pid_file.name}")
                    pid_file.unlink()
            except Exception as e:
                self.log_debug(f"Failed to clean up PID file: {e}")
            
        # Clean up zombie records in registry (only clean local services, keep remote services)
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
                
                cleaned_registry = {}
                for server_id, info in registry.items():
                    pid = info.get('pid')
                    server_name = info.get('name', 'unknown')
                    port = info.get('port')
                    
                    # First determine if it's a local server
                    if not self._is_local_server(info):
                        # Remote server: keep directly, no local check
                        cleaned_registry[server_id] = info
                        self.log_debug(f"Keep remote service record: {server_name} ({info.get('host', 'unknown')})")
                        continue
                    
                    # Local server: check if it's actually running
                    is_running = False
                    
                    if pid and self._is_process_alive_and_healthy(pid):
                        # PID exists and is healthy
                        is_running = True
                    elif not pid and port:
                        # PID is empty, but can check through port
                        is_running = self._is_server_running_by_port_and_process(server_name, port)
                    
                    if is_running:
                        cleaned_registry[server_id] = info
                        self.log_debug(f"Keep local service record: {server_name}")
                    else:
                        self.log_warning(f"Clean up local zombie registry record: {server_name}")
                
                with open(self.registry_file, 'w', encoding='utf-8') as f:
                    json.dump(cleaned_registry, f, indent=2, ensure_ascii=False)
                    
            except Exception as e:
                self.log_debug(f"Failed to clean up registry: {e}")
        
        # Clean up possible zombie ports
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.cmdline() or [])
                    if 'src/cli.py' in cmdline and any(cmd in cmdline for cmd in ['serve', 'proxy', 'api']):
                        # Check if process is actually running
                        if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                            self.log_warning(f"Clean up zombie process: PID {proc.pid}")
                            proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.log_debug(f"Failed to clean up zombie processes: {e}")

    def cleanup_registry_records(self):
        """Clean up registry records that don't match configuration file"""
        self.show_header("Clean up Registry Records")
        
        if not self.registry_file.exists():
            self.log_info("Registry file does not exist, no need to clean up")
            return
        
        try:
            # Load configuration file
            server_configs = self.get_server_configs()
            config_map = {config.name: config for config in server_configs}
            
            # Load registry
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            cleaned_records = []
            valid_records = {}
            
            for server_id, server_info in registry.items():
                server_name = server_info.get('name')
                transport = server_info.get('transport')
                
                # Check if server is in configuration file
                if server_name not in config_map:
                    cleaned_records.append(f"{server_name} (not in configuration file)")
                    continue
                
                # Check if transport protocol matches
                expected_transport = config_map[server_name].transport
                if transport != expected_transport:
                    cleaned_records.append(f"{server_name} (transport protocol mismatch: {transport} != {expected_transport})")
                    continue
                
                # Check if server is enabled
                if not config_map[server_name].enabled:
                    cleaned_records.append(f"{server_name} (disabled)")
                    continue
                
                # Record valid entries
                valid_records[server_id] = server_info
            
            # Write back cleaned registry
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(valid_records, f, indent=2, ensure_ascii=False)
            
            # Show cleanup results
            if cleaned_records:
                self.log_success(f"Cleaned up {len(cleaned_records)} invalid records:")
                for record in cleaned_records:
                    self.log_info(f"  - {record}")
            else:
                self.log_info("No invalid records found in registry")
            
            self.log_info(f"Retained {len(valid_records)} valid records")
            
        except Exception as e:
            self.log_error(f"Failed to clean up registry: {e}")

    def validate_registry_consistency(self):
        """Validate consistency between registry and configuration file"""
        self.show_header("Validate Registry Consistency")
        
        if not self.registry_file.exists():
            self.log_info("Registry file does not exist")
            return True
        
        try:
            # Load configuration file
            server_configs = self.get_server_configs()
            enabled_configs = {config.name: config for config in server_configs if config.enabled}
            
            # Load registry
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            issues = []
            
            # Check records in registry
            for server_id, server_info in registry.items():
                server_name = server_info.get('name')
                transport = server_info.get('transport')
                
                if server_name not in enabled_configs:
                    issues.append(f"Server {server_name} in registry is not enabled in configuration file")
                    continue
                
                expected_transport = enabled_configs[server_name].transport
                if transport != expected_transport:
                    issues.append(f"Server {server_name} transport protocol mismatch: registry={transport}, config={expected_transport}")
            
            # Check enabled servers in configuration file
            registry_servers = set(info.get('name') for info in registry.values())
            for server_name in enabled_configs:
                if server_name not in registry_servers:
                    self.log_info(f"Server {server_name} in configuration file not found in registry (may not be started yet)")
            
            if issues:
                self.log_warning(f"Found {len(issues)} consistency issues:")
                for issue in issues:
                    self.log_warning(f"  - {issue}")
                return False
            else:
                self.log_success("Registry and configuration file are consistent")
                return True
                
        except Exception as e:
            self.log_error(f"Failed to validate registry consistency: {e}")
            return False

    def _is_local_server(self, server_info: dict) -> bool:
        """Determine if server is local"""
        try:
            host = server_info.get('host', 'localhost')
            return is_local_ip(host)
        except Exception as e:
            self.log_debug(f"Failed to determine server locality: {e}")
            # If error occurs, conservatively assume it's a local server
            return True
    
    def _cleanup_local_registry_records(self):
        """Clean up local server records in registry, keep remote server records"""
        if not self.registry_file.exists():
            return
        
        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            remote_servers = {}
            local_servers_count = 0
            
            for server_id, server_info in registry.items():
                if self._is_local_server(server_info):
                    local_servers_count += 1
                    self.log_debug(f"Clean up local server record: {server_info.get('name', 'unknown')}")
                else:
                    remote_servers[server_id] = server_info
                    self.log_debug(f"Keep remote server record: {server_info.get('name', 'unknown')} ({server_info.get('host', 'unknown')})")
            
            # Write back registry containing only remote servers
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(remote_servers, f, indent=2, ensure_ascii=False)
            
            if local_servers_count > 0:
                self.log_info(f"Cleaned up {local_servers_count} local server records, kept {len(remote_servers)} remote server records")
            elif remote_servers:
                self.log_info(f"Kept {len(remote_servers)} remote server records")
            
        except Exception as e:
            self.log_error(f"Failed to clean up local registry records: {e}")
    
    def _load_remote_servers_to_memory(self):
        """Load remote servers from registry into memory"""
        if not self.registry_file.exists():
            return
        
        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            remote_servers_count = 0
            
            # Load remote services into registry memory via Python script
            for server_id, server_info in registry.items():
                if not self._is_local_server(server_info):
                    remote_servers_count += 1
                    self.log_debug(f"Load remote server into memory: {server_info.get('name', 'unknown')} ({server_info.get('host', 'unknown')})")
            
            if remote_servers_count > 0:
                # Reinitialize registry so remote services are loaded into memory
                try:
                    registry = ServerRegistry()
                    registry.load_from_file()
                    loaded_count = len(registry.get_all_servers())
                    self.log_info(f"Successfully loaded {remote_servers_count} remote servers into memory")
                    self.log_debug(f"Loaded {loaded_count} servers into memory")
                except Exception as e:
                    self.log_warning(f"Problem loading remote servers into memory: {e}")
            
        except Exception as e:
            self.log_error(f"Failed to load remote servers into memory: {e}")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="LiteMCP Framework Cross-Platform Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Usage Examples:
  python manage.py up                                 # Start all servers
  python manage.py up example                         # Start example server only
  python manage.py up --name example                  # Start example server only (equivalent)
  python manage.py up --proxy-url http://192.168.1.100:1888  # Start and register to remote proxy
  python manage.py down school                        # Stop school server only
  python manage.py ps                                 # View server status
  python manage.py log                                # View log information
  python manage.py health                             # Health check
  python manage.py unregister --proxy-url http://192.168.1.100:1888  # Unregister all servers from proxy
  python manage.py unregister --name example --proxy-url http://192.168.1.100:1888  # Unregister specific server from proxy
        """
    )
    
    # Main command
    parser.add_argument('command', 
                       choices=['start', 'stop', 'restart', 'status', 'logs', 'clean', 'health', 
                               'config', 'install', 'up', 'down', 'reboot', 'ps', 'log', 'check', 
                               'setup', 'clear', 'conf', 'api', 'proxy', 'diagnose', 'cleanup', 'init', 'help', 'unregister', 'validate', 'fix'],
                       help='Command to execute')
    
    # Optional server name positional parameter (supports bash syntax)
    parser.add_argument('server_name', nargs='?', 
                       help='Server name (optional, supports: python manage.py up example)')
    
    # General options
    parser.add_argument('--name', '-n', dest='target_server', 
                       help='Specify the server name to operate on')
    parser.add_argument('--proxy-url', '--proxy', dest='proxy_url',
                       help='Specify proxy server address (e.g.: http://192.168.1.100:1888)')
    parser.add_argument('--force', action='store_true', 
                       help='Force execution of operation')
    parser.add_argument('--verbose', action='store_true', 
                       help='Show detailed output')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show operations to be performed without actually executing')
    
    return parser


def main():
    """Main function"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Create manager instance
    manager = CrossPlatformManager()
    manager.verbose = args.verbose
    
    # Process server name parameter: positional parameter takes precedence over --name parameter
    target_server = args.server_name if args.server_name else args.target_server
    proxy_url = args.proxy_url
    
    # Execute command
    try:
        command = args.command
        force = args.force
        
        # Detailed commands
        if command == 'start':
            manager.start_servers(target_server, proxy_url)
        elif command == 'stop':
            if target_server:
                manager.stop_specific_server(target_server)
            else:
                manager.stop_all_servers(force)
        elif command == 'restart' or command == 'reboot':
            if target_server:
                manager.stop_specific_server(target_server)
                time.sleep(2)
                manager.start_servers(target_server, proxy_url)
            else:
                manager.stop_all_servers(force)
                time.sleep(2)
                manager.start_servers(None, proxy_url)
        elif command == 'status' or command == 'ps':
            manager.show_status()
        elif command == 'logs' or command == 'log':
            manager.show_logs()
        elif command == 'clean' or command == 'clear':
            manager.clean_files()
        elif command == 'health' or command == 'check':
            manager.health_check()
        elif command == 'config' or command == 'conf':
            manager.show_config()
        elif command == 'install' or command == 'setup':
            manager.install_dependencies()
        elif command == 'api':
            manager.start_api_server_standalone()
        elif command == 'proxy':
            manager.start_proxy_server_standalone()
        elif command == 'diagnose':
            manager.diagnose_system()
        elif command == 'cleanup':
            manager.cleanup_dead_processes()
        elif command == 'init':
            manager.init_project()
        elif command == 'help':
            manager.show_help()
        elif command == 'unregister':
            if not proxy_url:
                manager.log_error("unregister command requires --proxy-url parameter")
                manager.log_info("Usage example: python manage.py unregister --proxy-url http://192.168.1.100:1888")
                manager.log_info("Or specify server: python manage.py unregister --name example --proxy-url http://192.168.1.100:1888")
                return
            
            manager.show_header("LiteMCP Framework", f"Unregister {'Specific Server' if target_server else 'All Servers'} from Proxy")
            manager.show_section("Unregister MCP Server", manager.icons['network'])
            manager._auto_unregister_servers_from_proxy(proxy_url, target_server)
        elif command == 'validate':
            manager.validate_registry_consistency()
        elif command == 'fix':
            manager.cleanup_registry_records()
        
        # Quick commands (aliases)
        elif command == 'up':
            manager.start_servers(target_server, proxy_url)
        elif command == 'down':
            if target_server:
                manager.stop_specific_server(target_server)
            else:
                manager.stop_all_servers(True)  # The 'down' command defaults to forcing a stop
        
    except KeyboardInterrupt:
        manager.log_warning("Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        manager.log_error(f"Failed to execute command: {e}")
        if manager.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()