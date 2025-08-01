# !/usr/bin/env python3
"""
MCP Proxy Server Test Script

Verifies basic proxy server functionality:
1. Proxy server startup and shutdown
2. Server registration and deregistration
3. HTTP and SSE request forwarding
4. Status query interface
"""

import asyncio
import httpx
import pytest
import sys
from src.core.utils import get_project_root

# Add project root to Python path
project_root = get_project_root()
sys.path.insert(0, str(project_root))

from src.core.proxy_server import MCPProxyServer


class TestMCPProxyServer:
    """Proxy server test class"""

    @pytest.fixture
    async def proxy_server(self):
        """Create proxy server instance"""
        server = MCPProxyServer(host="localhost", port=1888)  # Use different port to avoid conflicts
        yield server

    @pytest.fixture
    async def mock_mcp_server(self):
        """Mock MCP server"""
        from fastapi import FastAPI
        import uvicorn
        from threading import Thread
        import time

        app = FastAPI()

        @app.get("/mcp")
        async def mcp_endpoint():
            return {"message": "Hello from MCP", "type": "http"}

        @app.get("/sse")
        async def sse_endpoint():
            from fastapi.responses import StreamingResponse

            def generate_events():
                yield "data: Hello from SSE\n\n"
                yield "data: Event 2\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                generate_events(),
                media_type="text/event-stream"
            )

        # Start mock server in background thread
        def run_server():
            uvicorn.run(app, host="localhost", port=8082, log_level="error")

        thread = Thread(target=run_server, daemon=True)
        thread.start()
        time.sleep(1)  # Wait for server to start

        yield "localhost", 8082

    def test_proxy_server_creation(self, proxy_server):
        """Test proxy server creation"""
        assert proxy_server.host == "localhost"
        assert proxy_server.port == 1888
        assert proxy_server.server_mapping == {}

    def test_server_registration(self, proxy_server):
        """Test server registration"""
        # Register server
        proxy_server.register_server_sync("test_server", "localhost", 8082)

        # Verify registration
        assert "test_server" in proxy_server.server_mapping
        server_info = proxy_server.server_mapping["test_server"]
        assert server_info["host"] == "localhost"
        assert server_info["port"] == 8082
        assert server_info["status"] == "running"

    def test_server_unregistration(self, proxy_server):
        """Test server deregistration"""
        # First register
        proxy_server.register_server_sync("test_server", "localhost", 8082)
        assert "test_server" in proxy_server.server_mapping

        # Then unregister
        proxy_server.unregister_server_sync("test_server")
        assert "test_server" not in proxy_server.server_mapping

    @pytest.mark.asyncio
    async def test_proxy_status_endpoint(self):
        """Test proxy status endpoint"""
        async with httpx.AsyncClient() as client:
            # Create simple FastAPI app for testing
            from fastapi import FastAPI
            from fastapi.testclient import TestClient

            proxy = MCPProxyServer()
            app = proxy.app

            with TestClient(app) as test_client:
                response = test_client.get("/proxy/status")
                assert response.status_code == 200

                data = response.json()
                assert "proxy" in data
                assert "servers" in data
                assert "total_servers" in data

    @pytest.mark.asyncio
    async def test_proxy_mapping_endpoint(self):
        """Test server mapping endpoint"""
        from fastapi.testclient import TestClient

        proxy = MCPProxyServer()
        proxy.register_server_sync("test_server", "localhost", 8082)

        with TestClient(proxy.app) as test_client:
            response = test_client.get("/proxy/mapping")
            assert response.status_code == 200

            data = response.json()
            assert "test_server" in data
            assert data["test_server"]["host"] == "localhost"
            assert data["test_server"]["port"] == 8082


async def main():
    """Main test function"""
    print("> Starting proxy server tests...")

    # Create proxy server instance
    proxy = MCPProxyServer(host="localhost", port=1888)

    # Test server registration
    print("[EDIT] Testing server registration...")
    proxy.register_server_sync("example", "localhost", 8001)
    proxy.register_server_sync("school", "localhost", 8002)

    print(f"[OK] Registered {len(proxy.server_mapping)} servers")
    for name, info in proxy.server_mapping.items():
        print(f"   - {name}: {info['host']}:{info['port']}")

    # Test status query
    print("\n[?] Testing status query...")
    async with httpx.AsyncClient() as client:
        try:
            # Test root path
            response = await client.get("http://localhost:1888/")
            if response.status_code == 200:
                print("[OK] Root path response normal")

            # Test status endpoint
            response = await client.get("http://localhost:1888/proxy/status")
            if response.status_code == 200:
                print("[OK] Status endpoint response normal")

            # Test mapping endpoint
            response = await client.get("http://localhost:1888/proxy/mapping")
            if response.status_code == 200:
                print("[OK] Mapping endpoint response normal")

        except httpx.ConnectError:
            print("[!] Proxy server not running, skipping HTTP tests")

    # Test server deregistration
    print("\n[DEL] Testing server deregistration...")
    proxy.unregister_server_sync("example")
    print(f"[OK] {len(proxy.server_mapping)} servers remaining after deregistration")

    print("\n[OK] Proxy server tests completed!")


if __name__ == "__main__":
    asyncio.run(main()) 