"""
Repository Management CLI Commands for GitSmart

This module provides command-line interface commands for managing repositories
in GitSmart's repository registry. It allows users to register, list, switch,
and manage multiple Git repositories.

Commands:
- repo list: List all registered repositories
- repo register <name> [path]: Register a repository
- repo switch <name>: Switch to a repository
- repo remove <name>: Remove a repository from registry
- repo status [name]: Get repository status
- repo alias <name> <alias>: Add alias to repository
- repo current: Show current repository
- repo discover [path]: Discover and register repositories
- repo export <file>: Export repository registry
- repo import <file>: Import repository registry
"""

import argparse
import os
import sys
import json
import time
from pathlib import Path
from typing import Optional, List

from .repo_registry import get_repository_registry, ensure_repository_context
from .repo_manager import get_repo_manager, register_current_repo, switch_to_repo, find_repo
from .ui import console, printer
from .config import logger, DEBUG


def print_success(message: str):
    """Print success message."""
    console.print(f"[bold green]✅ {message}[/bold green]")


def print_error(message: str):
    """Print error message."""
    console.print(f"[bold red]❌ {message}[/bold red]")


def print_warning(message: str):
    """Print warning message."""
    console.print(f"[bold yellow]⚠️  {message}[/bold yellow]")


def print_info(message: str):
    """Print info message."""
    console.print(f"[cyan]ℹ️  {message}[/cyan]")


def format_time_ago(timestamp: float) -> str:
    """Format timestamp as 'time ago' string."""
    now = time.time()
    diff = now - timestamp

    if diff < 60:
        return "just now"
    elif diff < 3600:
        minutes = int(diff / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(diff / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"


def cmd_list_repositories(args):
    """List all registered repositories."""
    console.print("[bold cyan]📚 Registered Repositories[/bold cyan]")
    console.print("=" * 50)

    registry = get_repository_registry()
    repositories = registry.list_repositories()

    if not repositories:
        print_warning("No repositories registered yet.")
        print_info("Use 'gitsmart repo register <name>' to register the current directory")
        print_info("Or 'gitsmart repo discover' to automatically find repositories")
        return

    current_repo = registry.get_current_repository()
    current_repo_id = current_repo.repo_id if current_repo else None

    # Display repositories in a table format
    console.print()
    for i, repo in enumerate(repositories, 1):
        is_current = repo.repo_id == current_repo_id
        status_icon = "👉" if is_current else "  "

        # Check if path still exists
        path_exists = os.path.exists(repo.path)
        path_icon = "📂" if path_exists else "❓"

        console.print(f"{status_icon} {i}. [bold]{repo.name}[/bold] {path_icon}")
        console.print(f"      Path: {repo.path}")

        if repo.remote_url:
            console.print(f"      Remote: {repo.remote_url}")

        console.print(f"      Last accessed: {format_time_ago(repo.last_accessed)}")
        console.print(f"      Stats: {repo.commit_count} commits, {repo.branch_count} branches, {repo.file_count} files")

        if repo.aliases:
            console.print(f"      Aliases: {', '.join(repo.aliases)}")

        if not path_exists:
            print_warning(f"      Path no longer exists!")

        console.print()

    console.print(f"[dim]Total: {len(repositories)} repositories[/dim]")

    if current_repo:
        console.print(f"[dim]Current: {current_repo.name}[/dim]")


def cmd_register_repository(args):
    """Register a repository."""
    repo_name = args.name
    repo_path = args.path if args.path else os.getcwd()

    # Validate path
    if not os.path.exists(repo_path):
        print_error(f"Path does not exist: {repo_path}")
        return

    # Check if it's a git repository
    git_dir = os.path.join(repo_path, '.git')
    if not os.path.exists(git_dir):
        print_error(f"Not a Git repository: {repo_path}")
        print_info("Initialize with 'git init' first")
        return

    registry = get_repository_registry()

    # Check if already registered
    existing_repo = registry.find_repository_by_path(repo_path)
    if existing_repo:
        print_warning(f"Repository already registered as '{existing_repo.name}'")

        # Ask if user wants to add alias
        if repo_name != existing_repo.name:
            registry.add_alias(existing_repo.name, repo_name)
            print_success(f"Added '{repo_name}' as alias for '{existing_repo.name}'")
        return

    # Register new repository
    repo_info = registry.register_repository_by_name(repo_name, repo_path)

    if repo_info:
        print_success(f"Registered repository '{repo_name}'")
        console.print(f"  Path: {repo_info.path}")
        if repo_info.remote_url:
            console.print(f"  Remote: {repo_info.remote_url}")
        console.print(f"  Stats: {repo_info.commit_count} commits, {repo_info.branch_count} branches")

        # Set as current if no current repository
        if not registry.get_current_repository():
            registry.set_current_repository(repo_info)
            print_info(f"Set '{repo_name}' as current repository")
    else:
        print_error(f"Failed to register repository '{repo_name}'")


def cmd_switch_repository(args):
    """Switch to a repository."""
    repo_name = args.name

    registry = get_repository_registry()
    repo_info = registry.switch_to_repository(repo_name)

    if repo_info:
        print_success(f"Switched to repository '{repo_info.name}'")
        console.print(f"  Path: {repo_info.path}")
        console.print(f"  Branch: ", end="")

        # Get current branch
        try:
            import subprocess
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, check=True
            )
            branch = result.stdout.strip()
            console.print(f"[bold green]{branch}[/bold green]")
        except:
            console.print("[dim]unknown[/dim]")

    else:
        print_error(f"Repository '{repo_name}' not found")
        print_info("Use 'gitsmart repo list' to see available repositories")


def cmd_remove_repository(args):
    """Remove a repository from registry."""
    repo_name = args.name

    registry = get_repository_registry()

    # Find repository first
    repo_info = registry.find_repository_by_name(repo_name)
    if not repo_info:
        print_error(f"Repository '{repo_name}' not found")
        return

    # Confirm removal
    console.print(f"[bold red]Remove repository '{repo_info.name}'?[/bold red]")
    console.print(f"  Path: {repo_info.path}")
    console.print(f"  This will only remove it from GitSmart registry, not delete the actual repository.")

    try:
        response = input("\nContinue? [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print_info("Cancelled")
            return
    except KeyboardInterrupt:
        print_info("\nCancelled")
        return

    # Remove repository
    if registry.remove_repository(repo_name):
        print_success(f"Removed repository '{repo_name}' from registry")
    else:
        print_error(f"Failed to remove repository '{repo_name}'")


def cmd_repository_status(args):
    """Get repository status."""
    repo_name = args.name if hasattr(args, 'name') and args.name else None

    registry = get_repository_registry()
    repo_manager = get_repo_manager()

    if repo_name:
        repo_info = registry.find_repository_by_name(repo_name)
        if not repo_info:
            print_error(f"Repository '{repo_name}' not found")
            return
    else:
        repo_info = registry.get_current_repository()
        if not repo_info:
            print_error("No current repository. Specify a repository name or switch to one.")
            return

    console.print(f"[bold cyan]📊 Repository Status: {repo_info.name}[/bold cyan]")
    console.print("=" * 50)

    # Basic info
    console.print(f"[bold]Name:[/bold] {repo_info.name}")
    console.print(f"[bold]Path:[/bold] {repo_info.path}")
    console.print(f"[bold]ID:[/bold] {repo_info.repo_id}")

    if repo_info.remote_url:
        console.print(f"[bold]Remote:[/bold] {repo_info.remote_url}")

    if repo_info.aliases:
        console.print(f"[bold]Aliases:[/bold] {', '.join(repo_info.aliases)}")

    console.print(f"[bold]Registered:[/bold] {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(repo_info.created_at))}")
    console.print(f"[bold]Last accessed:[/bold] {format_time_ago(repo_info.last_accessed)}")

    # Path validation
    path_exists = os.path.exists(repo_info.path)
    console.print(f"[bold]Path exists:[/bold] {'✅ Yes' if path_exists else '❌ No'}")

    if not path_exists:
        print_warning("Repository path no longer exists!")
        return

    # Git status (if accessible)
    original_cwd = os.getcwd()
    try:
        os.chdir(repo_info.path)

        # Update and display current stats
        registry.update_repository_stats(repo_info)
        console.print(f"[bold]Statistics:[/bold]")
        console.print(f"  Commits: {repo_info.commit_count}")
        console.print(f"  Branches: {repo_info.branch_count}")
        console.print(f"  Files: {repo_info.file_count}")

        # Current branch
        try:
            import subprocess
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, check=True
            )
            current_branch = result.stdout.strip()
            console.print(f"[bold]Current branch:[/bold] {current_branch}")
        except:
            console.print(f"[bold]Current branch:[/bold] [dim]unknown[/dim]")

        # Git status
        try:
            from .git_utils import get_git_diff, parse_diff

            staged_diff = get_git_diff(staged=True)
            unstaged_diff = get_git_diff(staged=False)

            staged_files = parse_diff(staged_diff)
            unstaged_files = parse_diff(unstaged_diff)

            console.print(f"[bold]Working directory:[/bold]")
            console.print(f"  Staged files: {len(staged_files)}")
            console.print(f"  Unstaged files: {len(unstaged_files)}")

            if staged_files:
                console.print("  [green]Staged:[/green]")
                for file_info in staged_files[:5]:  # Show first 5
                    console.print(f"    • {file_info['file']} (+{file_info['additions']}, -{file_info['deletions']})")
                if len(staged_files) > 5:
                    console.print(f"    ... and {len(staged_files) - 5} more")

            if unstaged_files:
                console.print("  [yellow]Unstaged:[/yellow]")
                for file_info in unstaged_files[:5]:  # Show first 5
                    console.print(f"    • {file_info['file']} (+{file_info['additions']}, -{file_info['deletions']})")
                if len(unstaged_files) > 5:
                    console.print(f"    ... and {len(unstaged_files) - 5} more")

        except Exception as e:
            console.print(f"[bold]Working directory:[/bold] [dim]Could not get status: {e}[/dim]")

    except Exception as e:
        print_error(f"Could not access repository: {e}")
    finally:
        os.chdir(original_cwd)


def cmd_add_alias(args):
    """Add alias to repository."""
    repo_name = args.name
    alias = args.alias

    registry = get_repository_registry()

    if registry.add_alias(repo_name, alias):
        print_success(f"Added alias '{alias}' to repository '{repo_name}'")
    else:
        print_error(f"Failed to add alias. Repository '{repo_name}' not found or alias already exists.")


def cmd_current_repository(args):
    """Show current repository."""
    registry = get_repository_registry()
    current_repo = registry.get_current_repository()

    if current_repo:
        console.print(f"[bold cyan]📍 Current Repository[/bold cyan]")
        console.print("=" * 30)
        console.print(f"[bold]Name:[/bold] {current_repo.name}")
        console.print(f"[bold]Path:[/bold] {current_repo.path}")

        if current_repo.remote_url:
            console.print(f"[bold]Remote:[/bold] {current_repo.remote_url}")

        # Show current directory
        console.print(f"[bold]Working directory:[/bold] {os.getcwd()}")

        # Check if we're in the repo directory
        if os.getcwd().startswith(current_repo.path):
            console.print("[green]✅ You are in the repository directory[/green]")
        else:
            console.print("[yellow]⚠️  You are not in the repository directory[/yellow]")
            print_info(f"Use 'cd {current_repo.path}' to navigate to the repository")
    else:
        print_warning("No current repository set")
        print_info("Use 'gitsmart repo switch <name>' to set a current repository")


def cmd_discover_repositories(args):
    """Discover and register repositories."""
    search_path = args.path if hasattr(args, 'path') and args.path else os.getcwd()

    console.print(f"[bold cyan]🔍 Discovering repositories in: {search_path}[/bold cyan]")

    registry = get_repository_registry()
    discovered = []

    # Search for git repositories
    for root, dirs, files in os.walk(search_path):
        if '.git' in dirs:
            # Found a git repository
            repo_path = root

            # Check if already registered
            existing_repo = registry.find_repository_by_path(repo_path)
            if existing_repo:
                console.print(f"[dim]Skipping {repo_path} (already registered as '{existing_repo.name}')[/dim]")
                continue

            # Discover and register
            repo_info = registry.discover_repository(repo_path)
            if repo_info:
                discovered.append(repo_info)
                console.print(f"[green]✅ Discovered: {repo_info.name} at {repo_info.path}[/green]")

            # Don't recurse into this git repository
            dirs[:] = [d for d in dirs if d != '.git']

    if discovered:
        print_success(f"Discovered and registered {len(discovered)} repositories")

        # Set the first one as current if no current repository
        if not registry.get_current_repository() and discovered:
            registry.set_current_repository(discovered[0])
            print_info(f"Set '{discovered[0].name}' as current repository")
    else:
        print_warning("No new repositories discovered")


def cmd_export_registry(args):
    """Export repository registry."""
    export_path = args.file

    registry = get_repository_registry()

    if registry.export_registry(export_path):
        print_success(f"Exported repository registry to {export_path}")
    else:
        print_error(f"Failed to export registry to {export_path}")


def cmd_import_registry(args):
    """Import repository registry."""
    import_path = args.file

    if not os.path.exists(import_path):
        print_error(f"Import file does not exist: {import_path}")
        return

    registry = get_repository_registry()

    if registry.import_registry(import_path):
        print_success(f"Imported repository registry from {import_path}")
    else:
        print_error(f"Failed to import registry from {import_path}")


def cmd_cleanup_registry(args):
    """Clean up invalid repositories."""
    registry = get_repository_registry()

    console.print("[bold cyan]🧹 Cleaning up repository registry...[/bold cyan]")

    removed_count = registry.cleanup_invalid_repositories()

    if removed_count > 0:
        print_success(f"Removed {removed_count} invalid repositories")
    else:
        print_info("No invalid repositories found")


def create_repo_parser(subparsers):
    """Create repository management parser."""
    repo_parser = subparsers.add_parser(
        'repo',
        help='Repository management commands',
        description='Manage GitSmart repository registry'
    )

    repo_subparsers = repo_parser.add_subparsers(
        dest='repo_command',
        help='Repository commands',
        required=True
    )

    # List repositories
    list_parser = repo_subparsers.add_parser(
        'list',
        help='List all registered repositories'
    )
    list_parser.set_defaults(func=cmd_list_repositories)

    # Register repository
    register_parser = repo_subparsers.add_parser(
        'register',
        help='Register a repository'
    )
    register_parser.add_argument(
        'name',
        help='Name for the repository'
    )
    register_parser.add_argument(
        'path',
        nargs='?',
        help='Path to repository (default: current directory)'
    )
    register_parser.set_defaults(func=cmd_register_repository)

    # Switch repository
    switch_parser = repo_subparsers.add_parser(
        'switch',
        help='Switch to a repository'
    )
    switch_parser.add_argument(
        'name',
        help='Repository name or alias to switch to'
    )
    switch_parser.set_defaults(func=cmd_switch_repository)

    # Remove repository
    remove_parser = repo_subparsers.add_parser(
        'remove',
        help='Remove repository from registry'
    )
    remove_parser.add_argument(
        'name',
        help='Repository name to remove'
    )
    remove_parser.set_defaults(func=cmd_remove_repository)

    # Repository status
    status_parser = repo_subparsers.add_parser(
        'status',
        help='Get repository status'
    )
    status_parser.add_argument(
        'name',
        nargs='?',
        help='Repository name (default: current repository)'
    )
    status_parser.set_defaults(func=cmd_repository_status)

    # Add alias
    alias_parser = repo_subparsers.add_parser(
        'alias',
        help='Add alias to repository'
    )
    alias_parser.add_argument(
        'name',
        help='Repository name'
    )
    alias_parser.add_argument(
        'alias',
        help='Alias to add'
    )
    alias_parser.set_defaults(func=cmd_add_alias)

    # Current repository
    current_parser = repo_subparsers.add_parser(
        'current',
        help='Show current repository'
    )
    current_parser.set_defaults(func=cmd_current_repository)

    # Discover repositories
    discover_parser = repo_subparsers.add_parser(
        'discover',
        help='Discover and register repositories'
    )
    discover_parser.add_argument(
        'path',
        nargs='?',
        help='Path to search (default: current directory)'
    )
    discover_parser.set_defaults(func=cmd_discover_repositories)

    # Export registry
    export_parser = repo_subparsers.add_parser(
        'export',
        help='Export repository registry'
    )
    export_parser.add_argument(
        'file',
        help='Export file path'
    )
    export_parser.set_defaults(func=cmd_export_registry)

    # Import registry
    import_parser = repo_subparsers.add_parser(
        'import',
        help='Import repository registry'
    )
    import_parser.add_argument(
        'file',
        help='Import file path'
    )
    import_parser.set_defaults(func=cmd_import_registry)

    # Cleanup registry
    cleanup_parser = repo_subparsers.add_parser(
        'cleanup',
        help='Clean up invalid repositories'
    )
    cleanup_parser.set_defaults(func=cmd_cleanup_registry)

    return repo_parser


def handle_repo_command(args):
    """Handle repository management commands."""
    if hasattr(args, 'func'):
        try:
            args.func(args)
        except KeyboardInterrupt:
            print_info("\nOperation cancelled")
        except Exception as e:
            print_error(f"Command failed: {e}")
            if DEBUG:
                logger.exception("Repository command error")
    else:
        print_error("No repository command specified")
        print_info("Use 'gitsmart repo --help' for available commands")
