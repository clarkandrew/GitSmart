#!/usr/bin/env python3
"""
Test script for GitSmart add files functionality.
Tests both CLI and MCP server add_files operations.
"""

import os
import sys
import tempfile
import subprocess
import shutil
from pathlib import Path

def create_test_repo():
    """Create a temporary git repository for testing."""
    test_dir = tempfile.mkdtemp(prefix="gitsmart_test_")
    os.chdir(test_dir)

    # Initialize git repo
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)

    # Create some test files
    with open("existing_file.txt", "w") as f:
        f.write("This file already exists in git\n")

    # Add and commit the existing file
    subprocess.run(["git", "add", "existing_file.txt"], check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

    # Create untracked files for testing
    with open("new_file1.py", "w") as f:
        f.write("# This is a new Python file\nprint('Hello, World!')\n")

    with open("new_file2.js", "w") as f:
        f.write("// This is a new JavaScript file\nconsole.log('Hello, World!');\n")

    os.makedirs("subdir", exist_ok=True)
    with open("subdir/nested_file.txt", "w") as f:
        f.write("This is a nested file\n")

    return test_dir

def test_git_status():
    """Test git status to see untracked files."""
    print("=== Git Status ===")
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    print("Git status output:")
    print(result.stdout)
    return result.returncode == 0

def test_cli_add_files():
    """Test the CLI add files functionality."""
    print("\n=== Testing CLI Add Files ===")

    # Test adding a single file
    try:
        result = subprocess.run([
            sys.executable, "-m", "GitSmart.main", "add", "new_file1.py"
        ], capture_output=True, text=True, cwd=os.getcwd())

        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")

        # Check if file was added
        git_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        print(f"Git status after add: {git_result.stdout}")

        return result.returncode == 0
    except Exception as e:
        print(f"CLI test failed: {e}")
        return False

def test_cli_add_multiple_files():
    """Test adding multiple files at once."""
    print("\n=== Testing CLI Add Multiple Files ===")

    try:
        result = subprocess.run([
            sys.executable, "-m", "GitSmart.main", "add", "new_file2.js", "subdir/nested_file.txt"
        ], capture_output=True, text=True, cwd=os.getcwd())

        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")

        # Check if files were added
        git_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        print(f"Git status after add: {git_result.stdout}")

        return result.returncode == 0
    except Exception as e:
        print(f"Multiple files CLI test failed: {e}")
        return False

def test_cli_add_already_tracked():
    """Test adding already tracked files."""
    print("\n=== Testing CLI Add Already Tracked File ===")

    try:
        result = subprocess.run([
            sys.executable, "-m", "GitSmart.main", "add", "existing_file.txt"
        ], capture_output=True, text=True, cwd=os.getcwd())

        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")

        # Should show warning about already tracked file
        return "already tracked" in result.stdout.lower() or "already tracked" in result.stderr.lower()
    except Exception as e:
        print(f"Already tracked test failed: {e}")
        return False

def test_cli_add_nonexistent():
    """Test adding non-existent files."""
    print("\n=== Testing CLI Add Non-existent File ===")

    try:
        result = subprocess.run([
            sys.executable, "-m", "GitSmart.main", "add", "nonexistent_file.txt"
        ], capture_output=True, text=True, cwd=os.getcwd())

        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")

        # Should show error about file not found
        return "not found" in result.stdout.lower() or "not found" in result.stderr.lower()
    except Exception as e:
        print(f"Non-existent file test failed: {e}")
        return False

def test_mcp_server_add_files():
    """Test the MCP server add files functionality."""
    print("\n=== Testing MCP Server Add Files ===")

    try:
        # Create another untracked file for MCP testing
        with open("mcp_test_file.md", "w") as f:
            f.write("# MCP Test File\nThis file is for testing MCP server functionality.\n")

        # Import the MCP server directly and test
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from GitSmart.mcp_server import MCPServer

        server = MCPServer()

        # Test the _add_files method directly
        result = server._add_files(["mcp_test_file.md"])

        print(f"MCP add_files result: {result}")

        # Check if file was added
        git_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        print(f"Git status after MCP add: {git_result.stdout}")

        return result.get("success", False)
    except Exception as e:
        print(f"MCP server test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("GitSmart Add Files Test Suite")
    print("=" * 40)

    original_dir = os.getcwd()
    test_dir = None

    try:
        # Create test repository
        test_dir = create_test_repo()
        print(f"Created test repository at: {test_dir}")

        # Run tests
        tests = [
            ("Git Status", test_git_status),
            ("CLI Add Single File", test_cli_add_files),
            ("CLI Add Multiple Files", test_cli_add_multiple_files),
            ("CLI Add Already Tracked", test_cli_add_already_tracked),
            ("CLI Add Non-existent", test_cli_add_nonexistent),
            ("MCP Server Add Files", test_mcp_server_add_files),
        ]

        results = []
        for test_name, test_func in tests:
            print(f"\n{'='*50}")
            print(f"Running: {test_name}")
            print('='*50)
            try:
                success = test_func()
                results.append((test_name, success))
                print(f"✅ {test_name}: {'PASSED' if success else 'FAILED'}")
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
            print("🎉 All tests passed!")
            return 0
        else:
            print("❌ Some tests failed")
            return 1

    except Exception as e:
        print(f"Test suite failed: {e}")
        return 1
    finally:
        # Cleanup
        os.chdir(original_dir)
        if test_dir and os.path.exists(test_dir):
            try:
                shutil.rmtree(test_dir)
                print(f"\nCleaned up test directory: {test_dir}")
            except Exception as e:
                print(f"Failed to cleanup test directory: {e}")

if __name__ == "__main__":
    sys.exit(main())
