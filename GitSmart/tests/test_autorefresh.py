#!/usr/bin/env python3
"""
Test script to validate auto-refresh functionality.
This script creates, modifies, and deletes files to trigger git changes
and verify that GitSmart's auto-refresh detects them using the new polling-based approach.
"""

import os
import time
import subprocess
import sys
from pathlib import Path

def run_git_command(cmd):
    """Run a git command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def create_test_file(filename, content):
    """Create a test file with given content."""
    with open(filename, 'w') as f:
        f.write(content)
    print(f"✅ Created test file: {filename}")

def modify_test_file(filename, new_content):
    """Modify an existing test file."""
    with open(filename, 'a') as f:
        f.write(new_content)
    print(f"✏️  Modified test file: {filename}")

def delete_test_file(filename):
    """Delete a test file."""
    if os.path.exists(filename):
        os.remove(filename)
        print(f"🗑️  Deleted test file: {filename}")

def get_git_status():
    """Get current git status for validation."""
    success, stdout, stderr = run_git_command("git status --porcelain")
    if success:
        return stdout.strip().split('\n') if stdout.strip() else []
    return []

def test_auto_refresh():
    """Test auto-refresh functionality by creating git changes."""
    print("=== GitSmart Polling-Based Auto-Refresh Test ===")
    print("This script will create file changes to test the new auto-refresh detection.")
    print("Make sure GitSmart is running with auto_refresh=true in another terminal.")
    print("The new implementation uses polling instead of SIGINT interruption.")
    print()
    
    test_files = [
        "test_autorefresh_1.txt",
        "test_autorefresh_2.py", 
        "test_autorefresh_3.md"
    ]
    
    try:
        print("📋 Initial git status:")
        initial_status = get_git_status()
        print(f"   {len(initial_status)} files in git status")
        
        # Test 1: Create new files
        print("\n🔄 TEST 1: Creating new files...")
        for i, filename in enumerate(test_files):
            create_test_file(filename, f"# Auto-refresh test file {i+1}\nInitial content created at {time.time()}\n")
            time.sleep(1.5)  # Shorter wait for better testing
        
        print(f"\n⏳ Waiting {AUTO_REFRESH_INTERVAL + 2} seconds for auto-refresh to detect changes...")
        time.sleep(4)  # Wait longer than refresh interval
        
        current_status = get_git_status()
        print(f"📊 Current git status: {len(current_status)} files")
        
        # Test 2: Modify existing files  
        print("\n🔄 TEST 2: Modifying existing files...")
        for i, filename in enumerate(test_files):
            modify_test_file(filename, f"\n📝 Modified content {i+1} added at {time.time()}\n")
            time.sleep(1.5)
        
        print(f"\n⏳ Waiting {AUTO_REFRESH_INTERVAL + 2} seconds for auto-refresh to detect changes...")
        time.sleep(4)
        
        # Test 3: Stage some files
        print("\n🔄 TEST 3: Staging files...")
        success, stdout, stderr = run_git_command(f"git add {test_files[0]} {test_files[1]}")
        if success:
            print(f"📦 Staged {test_files[0]} and {test_files[1]}")
        else:
            print(f"❌ Failed to stage files: {stderr}")
        
        print(f"\n⏳ Waiting {AUTO_REFRESH_INTERVAL + 2} seconds for auto-refresh to detect staging...")
        time.sleep(4)
        
        # Test 4: Unstage files
        print("\n🔄 TEST 4: Unstaging files...")
        success, stdout, stderr = run_git_command(f"git reset {test_files[0]}")
        if success:
            print(f"↩️  Unstaged {test_files[0]}")
        else:
            print(f"❌ Failed to unstage {test_files[0]}: {stderr}")
        
        print(f"\n⏳ Waiting {AUTO_REFRESH_INTERVAL + 2} seconds for auto-refresh to detect unstaging...")
        time.sleep(4)
        
        # Test 5: Delete files
        print("\n🔄 TEST 5: Deleting files...")
        for filename in test_files:
            delete_test_file(filename)
            time.sleep(1.5)
        
        print(f"\n⏳ Waiting {AUTO_REFRESH_INTERVAL + 2} seconds for final auto-refresh detection...")
        time.sleep(4)
        
        final_status = get_git_status()
        print(f"📊 Final git status: {len(final_status)} files")
        
        print("\n=== Test Complete ===")
        print("✅ Expected behavior in GitSmart terminal:")
        print("   - '📡 Repository changes detected, refreshing menu...' messages")
        print("   - Menu should refresh automatically after each test phase")
        print("   - File counts in menu should update dynamically")
        print("   - No SIGINT-related errors (new polling approach)")
        
        if len(initial_status) == len(final_status):
            print("✅ Git status restored to initial state")
        else:
            print("⚠️  Git status differs from initial state - manual cleanup may be needed")
        
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test error: {e}")
    finally:
        # Cleanup
        print("\n🧹 Cleaning up test files...")
        for filename in test_files:
            delete_test_file(filename)
        
        # Reset any staged changes
        print("🔄 Resetting any staged changes...")
        run_git_command("git reset")
        
        print("✅ Cleanup complete")

# Get the refresh interval from config if possible
try:
    from GitSmart.config import AUTO_REFRESH_INTERVAL
except ImportError:
    AUTO_REFRESH_INTERVAL = 1  # Default fallback

if __name__ == "__main__":
    print(f"🔧 Using auto-refresh interval: {AUTO_REFRESH_INTERVAL}s")
    test_auto_refresh()