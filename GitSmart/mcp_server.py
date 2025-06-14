import os
import subprocess
import socket
import time
import atexit
from pathlib import Path
from typing import List, Optional
from fastmcp import FastMCP, Context
from .config import logger, MCP_PORT, MCP_HOST, MODEL
from .git_utils import stage_files, unstage_files, get_git_diff
from .ai_utils import generate_commit_message
from .repo_manager import get_repo_manager, get_current_repo_info, switch_to_repo, find_repo

mcp = FastMCP("GitSmart MCP Server")

# Global server state management
_server_lock_file = Path.home() / ".gitsmart" / "mcp_server.lock"
_server_pid_file = Path.home() / ".gitsmart" / "mcp_server.pid"
_server_running = False

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is already in use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False

def is_server_running() -> bool:
    """Check if MCP server is already running."""
    # Check if port is in use
    if not is_port_in_use(MCP_PORT, MCP_HOST):
        return False
    
    # Check if PID file exists and process is running
    if _server_pid_file.exists():
        try:
            with open(_server_pid_file, 'r') as f:
                pid = int(f.read().strip())
            # Check if process is still running
            os.kill(pid, 0)  # This will raise OSError if process doesn't exist
            return True
        except (OSError, ValueError):
            # Process doesn't exist or PID file is corrupted
            _server_pid_file.unlink(missing_ok=True)
            return False
    
    return False

def create_server_lock():
    """Create server lock and PID files."""
    global _server_running
    _server_lock_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create lock file
    with open(_server_lock_file, 'w') as f:
        f.write(str(os.getpid()))
    
    # Create PID file
    with open(_server_pid_file, 'w') as f:
        f.write(str(os.getpid()))
    
    _server_running = True
    
    # Register cleanup on exit
    atexit.register(cleanup_server_lock)

def cleanup_server_lock():
    """Clean up server lock and PID files."""
    global _server_running
    if _server_running:
        _server_lock_file.unlink(missing_ok=True)
        _server_pid_file.unlink(missing_ok=True)
        _server_running = False

def start_mcp_server():
    """Start MCP server only if not already running."""
    if is_server_running():
        logger.info(f"MCP server already running on {MCP_HOST}:{MCP_PORT}")
        return False
    
    try:
        create_server_lock()
        logger.info(f"Starting MCP server on {MCP_HOST}:{MCP_PORT}")
        mcp.run(transport="streamable-http", host=MCP_HOST, port=MCP_PORT, path="/mcp")
        return True
    except Exception as e:
        cleanup_server_lock()
        logger.error(f"Failed to start MCP server: {e}")
        return False

# Utility to ensure repo context

def ensure_repo_context(repo_name: Optional[str] = None):
    repo_manager = get_repo_manager()
    if repo_name:
        repo_info = find_repo(repo_name)
        if not repo_info:
            raise Exception(f"Repository '{repo_name}' not found")
        os.chdir(repo_info["path"])
        repo_manager.set_current_repository(repo_info["name"])
        return repo_info
    else:
        repo_info = get_current_repo_info()
        if repo_info:
            os.chdir(repo_info["path"])
            repo_manager.set_current_repository(repo_info["name"])
        return repo_info

@mcp.tool
def stage_file(files: List[str], repo_name: str, ctx: Context = None):
    """Stage a file or multiple files for commit in a specific repository.
    
    Args:
        files: List of file paths to stage for commit
        repo_name: Name of git repository based on parent directory name (required)
    """
    logger.info(f"Tool called: stage_file with args: files={files}, repo_name={repo_name}")
    try:
        ensure_repo_context(repo_name)
        result = stage_files(files)
        return {"success": True, "message": result}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool
def unstage_file(files: List[str], repo_name: str, ctx: Context = None):
    """Unstage a file or multiple files in a specific repository.
    
    Args:
        files: List of file paths to unstage (remove from staging area)
        repo_name: Name of git repository based on parent directory name (required)
    """
    logger.info(f"Tool called: unstage_file with args: files={files}, repo_name={repo_name}")
    try:
        ensure_repo_context(repo_name)
        result = unstage_files(files)
        return {"success": True, "message": result}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool
def generate_commit_and_commit(repo_name: str, custom_message: Optional[str] = None, ctx: Context = None):
    """Generate an AI commit message and commit staged changes in a specific repository.
    
    Args:
        repo_name: Name of git repository based on parent directory name (required)
        custom_message: Custom commit message to use instead of AI-generated one (optional)
    
    Returns:
        Dict with success status and commit message or error details
    """
    logger.info(f"Tool called: generate_commit_and_commit with args: repo_name={repo_name}, custom_message={custom_message}")
    try:
        ensure_repo_context(repo_name)
        if custom_message:
            commit_message = custom_message
        else:
            # Get the staged diff and generate commit message
            diff = get_git_diff(staged=True)
            if not diff:
                return {"success": False, "message": "No staged changes found. Please stage some files first."}
            commit_message = generate_commit_message(MODEL, diff)
        
        result = subprocess.run([
            "git", "commit", "-m", commit_message
        ], capture_output=True, text=True)
        if result.returncode == 0:
            return {"success": True, "message": f"Committed: {commit_message}"}
        else:
            return {"success": False, "message": result.stderr}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool
def add_files(files: List[str], repo_name: str, ctx: Context = None):
    """Add untracked files to Git repository (git add for new files).
    
    Args:
        files: List of untracked file paths to add to the repository
        repo_name: Name of git repository based on parent directory name (required)
    
    Returns:
        Dict with success status, added files, and any files that couldn't be added
    """
    logger.info(f"Tool called: add_files with args: files={files}, repo_name={repo_name}")
    try:
        ensure_repo_context(repo_name)
        valid_files = []
        invalid_files = []
        already_tracked = []
        for file_path in files:
            if not os.path.exists(file_path):
                invalid_files.append(file_path)
                continue
            try:
                result = subprocess.run([
                    "git", "ls-files", "--", file_path
                ], capture_output=True, text=True, check=True)
                if result.stdout.strip():
                    already_tracked.append(file_path)
                else:
                    valid_files.append(file_path)
            except subprocess.CalledProcessError:
                valid_files.append(file_path)
        messages = []
        if invalid_files:
            messages.append(f"Files not found: {', '.join(invalid_files)}")
        if already_tracked:
            messages.append(f"Already tracked: {', '.join(already_tracked)}")
        if valid_files:
            try:
                result = subprocess.run(["git", "add"] + valid_files, capture_output=True, text=True, check=True)
                messages.append(f"Successfully added: {', '.join(valid_files)}")
                success = True
            except subprocess.CalledProcessError as e:
                messages.append(f"Git add failed: {e.stderr}")
                success = False
        else:
            if not invalid_files and not already_tracked:
                messages.append("No valid untracked files to add")
            success = len(invalid_files) == 0 and len(already_tracked) == 0
        return {
            "success": success,
            "message": "; ".join(messages),
            "added_files": valid_files,
            "invalid_files": invalid_files,
            "already_tracked": already_tracked,
            "operation": "add",
            "repository": repo_name or "current"
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool
def list_repositories(ctx: Context = None):
    """List all registered repositories.
    
    Returns:
        Dict containing a list of all registered repository names
    """
    logger.info("Tool called: list_repositories")
    try:
        repo_manager = get_repo_manager()
        repos = repo_manager.list_repositories()
        return {"repositories": list(repos.keys())}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool
def switch_repository(repo_name: str, ctx: Context = None):
    """Switch to a specific repository.
    
    Args:
        repo_name: Name of git repository based on parent directory name to switch to (required)
    
    Returns:
        Dict with success status and confirmation message
    """
    logger.info(f"Tool called: switch_repository with args: repo_name={repo_name}")
    try:
        repo_manager = get_repo_manager()
        success, prev_dir = switch_to_repo(repo_name)
        if success:
            return {"success": True, "message": f"Switched to {repo_name}"}
        else:
            return {"success": False, "message": f"Could not switch to {repo_name}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool
def get_repository_status(repo_name: str, ctx: Context = None):
    """Get detailed status of a specific repository.
    
    Args:
        repo_name: Name of git repository based on parent directory name to get status for (required)
    
    Returns:
        Dict with detailed repository information including name, path, branch, and change status
    """
    logger.info(f"Tool called: get_repository_status with args: repo_name={repo_name}")
    try:
        ensure_repo_context(repo_name)
        repo_manager = get_repo_manager()
        repo_info = repo_manager.get_current_repository()
        return repo_info
    except Exception as e:
        return {"success": False, "message": str(e)}

if __name__ == "__main__":
    start_mcp_server() 