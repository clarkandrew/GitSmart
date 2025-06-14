#!/usr/bin/env python3
"""
Test file for GitSmart add functionality.
This file should be untracked when created and can be used to test the add command.
"""

def hello_world():
    """Simple function to test git add functionality."""
    print("Hello from GitSmart test file!")
    print("This file was created to test the add files functionality.")

def main():
    """Main function."""
    hello_world()
    print("File operations:")
    print("- This file should initially be untracked")
    print("- Use 'gitsmart add test_new_file.py' to add it")
    print("- Check with 'git status' to verify it's staged")

if __name__ == "__main__":
    main()
