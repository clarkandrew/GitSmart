import os
import re
import subprocess
from typing import List, Dict, Any, Optional
from math import floor, ceil

from .ui import console, printer
from .config import logger

"""
This module houses all Git-related operations such as fetching diffs,
staging, unstaging, commit history, etc.
"""

def run_git_command(command: List[str]) -> str:
    """
    Run a git command and return the result or an error message.
    """
    try:
        subprocess.run(command, check=True)
        return f"Success: {' '.join(command)}"
    except subprocess.CalledProcessError as e:
        error_message = f"Error: {' '.join(command)}. Error: {e}"
        logger.error(error_message)
        return error_message
    except FileNotFoundError as e:
        error_message = f"Error: Command not found. {' '.join(command)}. Error: {e}"
        logger.error(error_message)
        return error_message
    except Exception as e:
        error_message = f"Unexpected error: {' '.join(command)}. Error: {e}"
        logger.error(error_message)
        return error_message

def get_git_diff(staged: bool = True) -> str:
    """
    Get the git diff of staged or unstaged changes.
    """
    logger.debug(f"Entering get_git_diff function. Staged: {staged}")
    try:
        cmd = ["git", "diff", "--staged"] if staged else ["git", "diff"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)
        diff = result.stdout.decode("utf-8")
        logger.debug("Git diff retrieved successfully.")
        return diff
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get {'staged' if staged else 'unstaged'} diff: {e}")
        return ""


def parse_diff(diff: str) -> List[Dict[str, Any]]:
    """
    Parse the git diff to extract file names, additions, and deletions.
    """
    file_changes = []
    file_pattern = re.compile(r"diff --git a/(.+?) b/(.+)")
    addition_pattern = re.compile(r"^\+[^+].*")
    deletion_pattern = re.compile(r"^\-[^-].*")

    current_file = None
    additions = 0
    deletions = 0

    for line in diff.splitlines():
        file_match = file_pattern.match(line)
        if file_match:
            if current_file:
                file_changes.append({"file": current_file, "additions": additions, "deletions": deletions})
            current_file = file_match.group(2)
            additions = 0
            deletions = 0
        elif addition_pattern.match(line):
            additions += 1
        elif deletion_pattern.match(line):
            deletions += 1

    if current_file:
        file_changes.append({"file": current_file, "additions": additions, "deletions": deletions})

    return file_changes

def get_file_diff(file: str, staged: bool = True) -> List[str]:
    """
    Retrieve the git diff for a specific file, either staged or unstaged.
    """
    try:
        cmd = ["git", "diff", "--staged", "--", file] if staged else ["git", "diff", "--", file]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, check=True, text=True)
        diff = result.stdout.strip().split("\n")
        return diff
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get diff for {file}: {e}")
        console.print(f"[bold red]Failed to get diff for {file}: {e}[/bold red]")
        return []

def stage_files(files: List[str]) -> str:
    """
    Stage the specified files.
    """
    return run_git_command(["git", "add"] + files)

def unstage_files(files: List[str]) -> str:
    """
    Unstage the specified files.
    """
    return run_git_command(["git", "reset"] + files)

def get_repo_name() -> str:
    """
    Retrieve the current repository's name by reading top-level directory.
    """
    try:
        repo_path = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], universal_newlines=True).strip()
        repo_name = os.path.basename(repo_path)
        return repo_name
    except subprocess.CalledProcessError:
        return "Unknown Repository"

def get_git_remotes() -> Dict[str, str]:
    """
    Retrieve a dictionary of all configured git remotes and their URLs.
    """
    try:
        result = subprocess.run(["git", "remote", "-v"], stdout=subprocess.PIPE, check=True, text=True)
        remotes = result.stdout.strip().split('\n')
        remote_dict = {}
        for remote in remotes:
            parts = remote.split()
            if len(parts) >= 2:
                name, url = parts[0], parts[1]
                if name not in remote_dict:
                    remote_dict[name] = url
        logger.debug(f"Available remotes: {remote_dict}")
        return remote_dict
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to retrieve git remotes: {e}")
        console.print(f"[bold red]Failed to retrieve git remotes: {e}[/bold red]")
        return {}

def push_to_remote(remote: str, url: str) -> str:
    """
    Push to a specific remote repository.
    """
    try:
        logger.debug(f"Pushing to remote: {remote}")
        subprocess.run(["git", "push", remote], check=True)
        return f"Successfully pushed to {remote} ({url})."
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to push to {remote}: {e}")
        return f"Failed to push to {remote}: {e}"
