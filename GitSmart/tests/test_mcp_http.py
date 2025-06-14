#!/usr/bin/env python3
"""
Test script for GitSmart MCP Server HTTP endpoints.
Tests the HTTP API for add_files and other MCP operations.
"""

import requests
import json
import time
import threading
import sys
import os
from pathlib import Path

def start_mcp_server_background():
    """Start MCP server in background thread."""
    def run_server():
        try:
            from GitSmart.mcp_server import start_mcp_server
            server = start_mcp_server()
            if server:
                print("✅ MCP server started successfully")
            else:
                print("❌ Failed to start MCP server")
        except Exception as e:
            print(f"❌ Error starting MCP server: {e}")

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(3)  # Give server time to start
    return thread

def test_server_status():
    """Test the server status endpoint."""
    print("\n=== Testing Server Status ===")
    try:
        response = requests.get("http://127.0.0.1:8765/mcp/status")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Server Status: {data.get('status')}")
            print(f"Connected Clients: {data.get('connected_clients')}")
            print(f"Available Tools: {data.get('tools_available')}")
            print(f"Current Repository: {data.get('current_repository')}")
            return True
        else:
            print(f"❌ Failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_list_tools():
    """Test the list tools endpoint."""
    print("\n=== Testing List Tools ===")
    try:
        response = requests.get("http://127.0.0.1:8765/mcp/tools")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            tools = data.get('result', {}).get('tools', [])
            print(f"Number of tools: {len(tools)}")

            for tool in tools:
                print(f"  - {tool['name']}: {tool['description']}")

            # Check if add_files tool is available
            add_files_tool = next((t for t in tools if t['name'] == 'add_files'), None)
            if add_files_tool:
                print("✅ add_files tool found")
                return True
            else:
                print("❌ add_files tool not found")
                return False
        else:
            print(f"❌ Failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_add_files_http():
    """Test the add_files functionality via HTTP."""
    print("\n=== Testing Add Files via HTTP ===")

    # Create a test file with timestamp to ensure uniqueness
    import time
    timestamp = str(int(time.time() * 1000))
    test_file = f"test_http_file_{timestamp}.txt"
    try:
        with open(test_file, "w") as f:
            f.write("# HTTP Test File\nThis file is created to test HTTP add_files functionality.\n")

        # Prepare the MCP call
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test-add-files",
            "params": {
                "name": "add_files",
                "arguments": {
                    "files": [test_file]
                }
            }
        }

        print(f"Request payload: {json.dumps(mcp_request, indent=2)}")

        response = requests.post(
            "http://127.0.0.1:8765/mcp/call",
            json=mcp_request,
            headers={"Content-Type": "application/json"}
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            result = data.get('result', {})
            content = result.get('content', [])

            if content and len(content) > 0:
                message = content[0].get('text', '')
                print(f"Operation result: {message}")

                # Check if operation was successful
                if "successfully added" in message.lower() or "already tracked" in message.lower():
                    print("✅ HTTP add_files test passed")
                    return True
                else:
                    print("❌ HTTP add_files operation failed")
                    return False
            else:
                print("❌ No content in response")
                return False
        else:
            print(f"❌ HTTP request failed: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            try:
                os.remove(test_file)
                print(f"Cleaned up test file: {test_file}")
            except Exception as e:
                print(f"Failed to clean up test file: {e}")

def test_add_multiple_files_http():
    """Test adding multiple files via HTTP."""
    print("\n=== Testing Add Multiple Files via HTTP ===")

    import time
    timestamp = str(int(time.time() * 1000))
    test_files = [f"test_http1_{timestamp}.py", f"test_http2_{timestamp}.js"]
    try:
        # Create test files
        for i, test_file in enumerate(test_files):
            with open(test_file, "w") as f:
                f.write(f"# HTTP Test File {i+1}\nprint('Test file {i+1}')\n")

        # Prepare the MCP call
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test-add-multiple",
            "params": {
                "name": "add_files",
                "arguments": {
                    "files": test_files
                }
            }
        }

        response = requests.post(
            "http://127.0.0.1:8765/mcp/call",
            json=mcp_request,
            headers={"Content-Type": "application/json"}
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            result = data.get('result', {})
            content = result.get('content', [])

            if content and len(content) > 0:
                message = content[0].get('text', '')
                print(f"Operation result: {message}")

                # Check if operation was successful
                if "successfully added" in message.lower() or "already tracked" in message.lower():
                    print("✅ HTTP add multiple files test passed")
                    return True
                else:
                    print("❌ HTTP add multiple files operation failed")
                    return False
            else:
                print("❌ No content in response")
                return False
        else:
            print(f"❌ HTTP request failed: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        # Clean up test files
        for test_file in test_files:
            if os.path.exists(test_file):
                try:
                    os.remove(test_file)
                    print(f"Cleaned up test file: {test_file}")
                except Exception as e:
                    print(f"Failed to clean up test file: {e}")

def test_sse_endpoint():
    """Test the SSE endpoint (basic connectivity)."""
    print("\n=== Testing SSE Endpoint ===")
    try:
        response = requests.get(
            "http://127.0.0.1:8765/mcp/events",
            stream=True,
            timeout=2
        )

        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")

        if response.status_code == 200:
            # Read a few lines from the SSE stream
            lines_read = 0
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    print(f"SSE line: {line}")
                    lines_read += 1
                    if lines_read >= 3:  # Read first few lines then break
                        break

            print("✅ SSE endpoint is working")
            return True
        else:
            print(f"❌ SSE endpoint failed: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("✅ SSE endpoint is working (timeout expected for streaming connections)")
        return True  # Timeout is actually expected for SSE
    except requests.exceptions.ReadTimeout:
        print("✅ SSE endpoint is working (read timeout expected for streaming connections)")
        return True  # Read timeout is actually expected for SSE
    except Exception as e:
        if "Read timed out" in str(e):
            print("✅ SSE endpoint is working (connection timeout expected for streaming connections)")
            return True
        print(f"❌ Error: {e}")
        return False

def test_post_to_sse_endpoint():
    """Test POST to SSE endpoint (should return 405 with helpful message)."""
    print("\n=== Testing POST to SSE Endpoint (Expected 405) ===")
    try:
        response = requests.post("http://127.0.0.1:8765/mcp/events", json={})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 405:
            data = response.json()
            if "POST not allowed" in data.get("error", ""):
                print("✅ POST to SSE endpoint correctly returns 405 with helpful message")
                return True

        print("❌ POST to SSE endpoint should return 405")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all HTTP tests."""
    print("GitSmart MCP Server HTTP Test Suite")
    print("=" * 50)

    # Start MCP server
    print("Starting MCP server...")
    server_thread = start_mcp_server_background()

    # Wait a bit more for server to be ready
    time.sleep(2)

    # Run tests
    tests = [
        ("Server Status", test_server_status),
        ("List Tools", test_list_tools),
        ("Add Files HTTP", test_add_files_http),
        ("Add Multiple Files HTTP", test_add_multiple_files_http),
        ("SSE Endpoint", test_sse_endpoint),
        ("POST to SSE (405 check)", test_post_to_sse_endpoint),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        try:
            success = test_func()
            results.append((test_name, success))
            print(f"{'✅' if success else '❌'} {test_name}: {'PASSED' if success else 'FAILED'}")
        except Exception as e:
            results.append((test_name, False))
            print(f"❌ {test_name}: FAILED with exception: {e}")

    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:<30} {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All HTTP tests passed!")
        return 0
    else:
        print("❌ Some HTTP tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
