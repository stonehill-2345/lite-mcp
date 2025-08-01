
"""
LiteMCP API Server Core Module

Provides core functionality for configuring API servers, including startup, shutdown and configuration management.
"""

import asyncio
import sys
from src.core.utils import get_project_root
from src.core.logger import init_logging, get_logger

# Add project root to Python path
project_root = get_project_root()
sys.path.insert(0, str(project_root))

class APIServer:
    """API Server Core Class"""
    
    def __init__(self, host: str = "localhost", port: int = 9000, log_level: str = "INFO"):
        """
        Initialize API server
        
        Args:
            host: Host address to listen on
            port: Port to listen on
            log_level: Logging level
        """
        self.host = host
        self.port = port
        self.log_level = log_level
        self.logger = None
        self._server = None
        
    def _init_logging(self):
        """Initialize logging system"""
        init_logging(self.log_level)
        self.logger = get_logger("litemcp.api_server", log_file="api_server.log")
        
    async def start(self):
        """Start API server"""
        if not self.logger:
            self._init_logging()
            
        try:
            import uvicorn
            from src.controller.config_api import app
            
            self.logger.info(f"Starting LiteMCP API server: http://{self.host}:{self.port}")
            self.logger.info(f"Log level: {self.log_level}")
            
            # Configure uvicorn
            config = uvicorn.Config(
                app,
                host=self.host,
                port=self.port,
                log_level=self.log_level.lower(),
                access_log=True
            )
            
            # Create and start server
            server = uvicorn.Server(config)
            self._server = server
            await server.serve()
            
        except KeyboardInterrupt:
            self.logger.info("Server stopped by user")
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            raise
        finally:
            self.logger.info("API server stopped")
            
    def run(self):
        """Run API server in synchronous mode"""
        asyncio.run(self.start())
        
    async def stop(self):
        """Stop API server"""
        if self._server:
            self.logger.info("Stopping API server...")
            self._server.should_exit = True
            await self._server.shutdown()
            self.logger.info("API server stopped")

def run_api_server(host: str = "localhost", port: int = 9000, log_level: str = "INFO"):
    """
    Convenience function to run API server
    
    Args:
        host: Host address to listen on
        port: Port to listen on
        log_level: Logging level
    """
    server = APIServer(host=host, port=port, log_level=log_level)
    server.run()

if __name__ == "__main__":
    # Support direct execution
    import argparse
    
    parser = argparse.ArgumentParser(description="LiteMCP API Server")
    parser.add_argument("--host", default="localhost", help="Host address to listen on")
    parser.add_argument("--port", type=int, default=9000, help="Port to listen on")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       help="Logging level")
    args = parser.parse_args()
    
    run_api_server(host=args.host, port=args.port, log_level=args.log_level)
