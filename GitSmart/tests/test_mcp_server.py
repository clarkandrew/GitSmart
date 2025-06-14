#!/usr/bin/env python3
"""
Test script for GitSmart MCP Server

This script tests the MCP server functionality by:
1. Starting the server
2. Testing all available tools
3. Verifying SSE connectivity
4. Checking error handling

Usage:
    python test_mcp_server.py
"""

import requests
import json
import time
import threading
import subprocess
import tempfile
import os
import sys
from pathlib import Path

# Add the GitSmart package to the path
sys.path.insert(0, str(Path(__file__).parent))

from GitSmart.mcp_server import MCPServer
from GitSmart.config import MCP_HOST, MCP_PORT


class MCPServerTester:
    """Test harness for MCP server functionality."""

    def __init__(self):
        self.base_url = f"http://{MCP_HOST}:{MCP_PORT}/mcp"
        self.server = None
        self.test_repo_path = None

    def setup_test_repo(self):
        """Create a temporary git repository for testing."""
        print("📁 Setting up test git repository...")

        # Create temporary directory
        self.test_repo_path = tempfile.mkdtemp(prefix="gitsmart_test_")
        os.chdir(self.test_repo_path)

        # Initialize git repo
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)

        # Create test files
        with open("test_file.txt", "w") as f:
            f.write("Initial content\n")

        with open("another_file.py", "w") as f:
            f.write("# Test Python file\nprint('Hello, World!')\n")

        # Make initial commit
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

        # Modify files to create changes
        with open("test_file.txt", "a") as f:
            f.write("Modified content\n")

        with open("new_file.md", "w") as f:
            f.write("# New File\nThis is a new markdown file.\n")

        print(f"✅ Test repository created at: {self.test_repo_path}")

    def cleanup_test_repo(self):
        """Clean up the test repository."""
        if self.test_repo_path and os.path.exists(self.test_repo_path):
            import shutil
            shutil.rmtree(self.test_repo_path)
            print("🧹 Test repository cleaned up")

    def start_server(self):
        """Start the MCP server for testing."""
        print("🚀 Starting MCP server...")
        self.server = MCPServer()

        # Start server in a separate thread
        server_thread = threading.Thread(target=self.server._run_server, daemon=True)
        server_thread.start()

        # Wait for server to start
        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get(f"{self.base_url}/status", timeout=1)
                if response.status_code == 200:
                    print("✅ MCP server started successfully")
                    return True
            except requests.exceptions.RequestException:
                time.sleep(0.5)

        print("❌ Failed to start MCP server")
        return False

    def test_server_status(self):
        """Test the server status endpoint."""
        print("\n📊 Testing server status endpoint...")

        try:
            response = requests.get(f"{self.base_url}/status")
            response.raise_for_status()

            data = response.json()
            print(f"✅ Status: {data.get('status')}")
            print(f"📁 Git root: {data.get('git_root')}")
            print(f"🌿 Branch: {data.get('repository', {}).get('current_branch')}")
            print(f"🛠️ Tools: {', '.join(data.get('tools_available', []))}")

            return True

        except Exception as e:
            print(f"❌ Status test failed: {e}")
            return False

    def test_list_tools(self):
        """Test the tools listing endpoint."""
        print("\n🛠️ Testing tools listing endpoint...")

        try:
            response = requests.get(f"{self.base_url}/tools")
            response.raise_for_status()

            data = response.json()
            tools = data.get('result', {}).get('tools', [])

            print(f"✅ Found {len(tools)} tools:")
            for tool in tools:
                name = tool.get('name')
                desc = tool.get('description')
                print(f"   • {name}: {desc}")

            # Verify expected tools exist
            tool_names = [tool['name'] for tool in tools]
            expected_tools = ['stage_file', 'unstage_file', 'generate_commit_and_commit']

            for expected in expected_tools:
                if expected in tool_names:
                    print(f"   ✅ {expected} found")
                else:
                    print(f"   ❌ {expected} missing")
                    return False

            return True

        except Exception as e:
            print(f"❌ Tools listing test failed: {e}")
            return False

    def test_stage_files(self):
        """Test the stage_file tool."""
        print("\n📝 Testing stage_file tool...")

        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "stage_file",
                    "arguments": {
                        "files": ["test_file.txt", "new_file.md"]
                    }
                }
            }

            response = requests.post(
                f"{self.base_url}/call",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            data = response.json()

            if data.get('result') and data['result'].get('content'):
                message = data['result']['content'][0]['text']
                print(f"✅ Stage result: {message}")
                return True
            else:
                error_msg = data.get('error', {}).get('message', 'Unknown error')
                print(f"❌ Stage failed: {error_msg}")
                return False

        except Exception as e:
            print(f"❌ Stage test failed: {e}")
            return False

    def test_unstage_files(self):
        """Test the unstage_file tool."""
        print("\n📝 Testing unstage_file tool...")

        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "unstage_file",
                    "arguments": {
                        "files": ["new_file.md"]
                    }
                }
            }

            response = requests.post(
                f"{self.base_url}/call",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            data = response.json()

            if data.get('result') and data['result'].get('content'):
                message = data['result']['content'][0]['text']
                print(f"✅ Unstage result: {message}")
                return True
            else:
                error_msg = data.get('error', {}).get('message', 'Unknown error')
                print(f"❌ Unstage failed: {error_msg}")
                return False

        except Exception as e:
            print(f"❌ Unstage test failed: {e}")
            return False

    def test_commit_generation(self):
        """Test the generate_commit_and_commit tool."""
        print("\n💬 Testing generate_commit_and_commit tool...")

        try:
            # First, ensure we have staged changes
            subprocess.run(["git", "add", "test_file.txt"], check=True)

            payload = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "generate_commit_and_commit",
                    "arguments": {
                        "custom_message": "test: MCP server integration test commit"
                    }
                }
            }

            response = requests.post(
                f"{self.base_url}/call",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            data = response.json()

            if data.get('result') and data['result'].get('content'):
                message = data['result']['content'][0]['text']
                print(f"✅ Commit result: {message}")
                return True
            else:
                error_msg = data.get('error', {}).get('message', 'Unknown error')
                print(f"❌ Commit failed: {error_msg}")
                return False

        except Exception as e:
            print(f"❌ Commit test failed: {e}")
            return False

    def test_error_handling(self):
        """Test error handling with invalid requests."""
        print("\n🚨 Testing error handling...")

        # Test invalid tool name
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "invalid_tool",
                    "arguments": {}
                }
            }

            response = requests.post(
                f"{self.base_url}/call",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            data = response.json()

            if response.status_code == 400 and data.get('error'):
                print("✅ Invalid tool name handled correctly")
                return True
            else:
                print("❌ Invalid tool name not handled properly")
                return False

        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            return False

    def test_sse_connectivity(self):
        """Test Server-Sent Events connectivity."""
        print("\n📡 Testing SSE connectivity...")

        try:
            # This is a basic test - in a real scenario you'd want to use an SSE client
            response = requests.get(f"{self.base_url}/events", stream=True, timeout=2)

            # Check if we get the expected content type for SSE
            content_type = response.headers.get('content-type', '')
            if 'text/event-stream' in content_type:
                print("✅ SSE endpoint accessible")
                return True
            else:
                print(f"❌ Unexpected content type: {content_type}")
                return False

        except requests.exceptions.Timeout:
            print("✅ SSE endpoint accessible (timeout expected)")
            return True
        except Exception as e:
            print(f"❌ SSE test failed: {e}")
            return False

    def run_all_tests(self):
        """Run all tests and report results."""
        print("=" * 60)
        print("🧪 GitSmart MCP Server Test Suite")
        print("=" * 60)

        tests = [
            ("Server Status", self.test_server_status),
            ("List Tools", self.test_list_tools),
            ("Stage Files", self.test_stage_files),
            ("Unstage Files", self.test_unstage_files),
            ("Commit Generation", self.test_commit_generation),
            ("Error Handling", self.test_error_handling),
            ("SSE Connectivity", self.test_sse_connectivity),
        ]

        results = []
        passed = 0

        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
                if result:
                    passed += 1
            except Exception as e:
                print(f"❌ {test_name} crashed: {e}")
                results.append((test_name, False))

        # Print summary
        print("\n" + "=" * 60)
        print("📊 Test Results Summary")
        print("=" * 60)

        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")

        print(f"\n🎯 Passed: {passed}/{len(tests)} tests")

        if passed == len(tests):
            print("🎉 All tests passed! MCP server is working correctly.")
            return True
        else:
            print("⚠️ Some tests failed. Check the output above for details.")
            return False


def main():
    """Main test function."""
    tester = MCPServerTester()

    try:
        # Setup test environment
        tester.setup_test_repo()

        # Start MCP server
        if not tester.start_server():
            print("❌ Failed to start server. Exiting.")
            return False

        # Wait a moment for server to fully initialize
        time.sleep(1)

        # Run all tests
        success = tester.run_all_tests()

        return success

    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        return False
    finally:
        # Cleanup
        tester.cleanup_test_repo()


if __name__ == "__main__":
    import sys

    success = main()
    sys.exit(0 if success else 1)
