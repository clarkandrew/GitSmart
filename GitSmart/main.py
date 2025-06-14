# GitSmart/main.py

import argparse
import sys
import time
import threading
import signal
import os


from .config import logger, MODEL, DEBUG, MODEL_CACHE, AUTO_REFRESH, AUTO_REFRESH_INTERVAL, MCP_ENABLED, MCP_HOST, MCP_PORT
from .ui import console, printer, Console
from .cli_flow import (
    get_and_display_status,
    get_status,
    handle_generate_commit,
    handle_review_changes,
    display_commit_summary,
    select_commit,
    print_commit_details,
    handle_stage_files,
    handle_unstage_files,
    handle_ignore_files,
    handle_push_repo,
    summarize_selected_commits,
    select_model,
    reset_console,
    get_menu_options,
    main_menu_prompt
)
from .utils import chdir_to_git_root
from .repo_registry import get_repository_registry, ensure_repository_context
from .repo_manager import get_repo_manager, register_current_repo

if MCP_ENABLED:
    from .mcp_server import mcp, start_mcp_server, is_server_running

"""
main.py

- Orchestrates the main application loop
- Always uses get_and_display_status() to show both staged/unstaged
- Passes dynamic menu from get_menu_options() to main_menu_prompt
"""
def main(reload: bool = False):
    # Initialize repository context
    repo_registry = get_repository_registry()
    repo_manager = get_repo_manager()

    # Try to discover and register current repository
    current_repo = repo_registry.discover_repository()
    if current_repo:
        console.print(f"[bold cyan]# GitSmart - {current_repo.name}[/bold cyan]")
        console.print(f"[dim]Repository: {current_repo.path}[/dim]")
    else:
        # Try legacy git root discovery
        try:
            chdir_to_git_root()
            # Register the repository we just found
            register_current_repo()
            repo_info = repo_manager.get_current_repository()
            if repo_info:
                console.print(f"[bold cyan]# GitSmart - {repo_info['name']}[/bold cyan]")
                console.print(f"[dim]Repository: {repo_info['path']}[/dim]")
            else:
                console.print("[bold cyan]# GitSmart[/bold cyan]")
        except:
            console.print("[bold cyan]# GitSmart[/bold cyan]")
            console.print("[bold yellow]⚠️  No Git repository found. Some features may be limited.[/bold yellow]")

    display_commit_summary(3)

    exit_prompted = 0
    auto_refresh_active = False
    refresh_thread = None
    last_staged_state = None
    last_unstaged_state = None
    state_lock = threading.Lock()
    shutdown_requested = threading.Event()
    mcp_server_thread = None

    # Start MCP server if enabled
    if MCP_ENABLED:
        try:
            if is_server_running():
                console.print(f"[bold yellow]MCP Server already running on http://{MCP_HOST}:{MCP_PORT}[/bold yellow]")
                console.print("[dim]Available tools: stage_file, unstage_file, generate_commit_and_commit, add_files, etc.[/dim]")
            else:
                def run_mcp():
                    start_mcp_server()
                mcp_server_thread = threading.Thread(target=run_mcp, daemon=True)
                mcp_server_thread.start()
                console.print(f"[bold green]MCP Server started on http://{MCP_HOST}:{MCP_PORT}[/bold green]")
                console.print("[dim]Available tools: stage_file, unstage_file, generate_commit_and_commit, add_files, etc.[/dim]")
        except Exception as e:
            console.print(f"[bold red]Failed to start MCP server: {e}[/bold red]")
            logger.error(f"MCP server startup failed: {e}")

    # Flag to track when menu needs refresh
    menu_needs_refresh = threading.Event()

    # ─── Setup custom signal & exception for mid-prompt refresh ───────────────────
    class RefreshMenuException(Exception):
        """Raised to abort the questionary prompt so we can refresh the menu."""
        pass

    def _refresh_signal_handler(signum, frame):
        # When we get SIGUSR1, raise our custom exception in the main thread
        # But only if auto-refresh is actually active
        if auto_refresh_active:
            raise RefreshMenuException()
        else:
            # Auto-refresh is paused (e.g., during commit generation), ignore signal
            if DEBUG:
                logger.debug("SIGUSR1 received but auto-refresh is paused, ignoring signal")

    # Register the handler BEFORE any prompt is shown
    signal.signal(signal.SIGUSR1, _refresh_signal_handler)
    # ────────────────────────────────────────────────────────────────────────────────

    def check_for_changes():
        """Check if git status has changed since last check."""
        nonlocal last_staged_state, last_unstaged_state
        try:
            _, _, current_staged, current_unstaged = get_status()

            # Convert to comparable format (file paths with additions/deletions)
            current_staged_files = {f.get('file', ''): (f.get('additions', 0), f.get('deletions', 0)) for f in current_staged}
            current_unstaged_files = {f.get('file', ''): (f.get('additions', 0), f.get('deletions', 0)) for f in current_unstaged}

            with state_lock:
                if last_staged_state is None or last_unstaged_state is None:
                    if DEBUG:
                        logger.debug("Auto-refresh: Initial state setup")
                    last_staged_state = current_staged_files
                    last_unstaged_state = current_unstaged_files
                    return False

                # Check if anything changed
                changed = (current_staged_files != last_staged_state or
                          current_unstaged_files != last_unstaged_state)

                # Temporary debug logging to see what's happening
                if DEBUG:
                    logger.debug(f"Auto-refresh check - Changed: {changed}")
                if changed:
                    logger.debug(f"Auto-refresh check - Previous staged: {last_staged_state}")
                    logger.debug(f"Auto-refresh check - Previous unstaged: {last_unstaged_state}")
                    logger.debug(f"Auto-refresh check - Current staged: {current_staged_files}")
                    logger.debug(f"Auto-refresh check - Current unstaged: {current_unstaged_files}")
                    logger.debug(f"Auto-refresh: Repository changes detected!")

                if changed:
                    last_staged_state = current_staged_files
                    last_unstaged_state = current_unstaged_files

                return changed
        except Exception as e:
            logger.error(f"Error checking for changes: {e}")
            return False

    def auto_refresh_worker():
        """Background thread that monitors for git changes and sets refresh flag when detected."""
        nonlocal auto_refresh_active, menu_needs_refresh
        if DEBUG:
            logger.debug(f"Auto-refresh worker thread started (PID: {os.getpid()})")
            logger.debug(f"Initial auto_refresh_active state: {auto_refresh_active}")
            logger.debug(f"AUTO_REFRESH_INTERVAL: {AUTO_REFRESH_INTERVAL}")

        try:
            loop_count = 0
            while auto_refresh_active and not shutdown_requested.is_set():
                loop_count += 1
                if DEBUG:
                    logger.debug(f"Auto-refresh: Loop iteration #{loop_count}, sleeping for {AUTO_REFRESH_INTERVAL}s")

                # Use shutdown_requested.wait() instead of time.sleep() for interruptible sleep
                if shutdown_requested.wait(timeout=AUTO_REFRESH_INTERVAL):
                    # Shutdown was requested during sleep
                    if DEBUG:
                        logger.debug("Auto-refresh: Shutdown requested during sleep, exiting")
                    break

                if auto_refresh_active and not shutdown_requested.is_set():
                    try:
                        if DEBUG:
                            logger.debug("Auto-refresh: Checking for changes...")
                        # Double-check auto_refresh_active state before checking for changes
                        if auto_refresh_active and check_for_changes():
                            if DEBUG:
                                logger.debug("Auto-refresh: Repository changes detected, setting refresh flag")
                            # mark for refresh
                            menu_needs_refresh.set()
                            # actually break any in-flight Questionary prompt
                            try:
                                # Triple-check auto_refresh_active before sending signal
                                if auto_refresh_active and not shutdown_requested.is_set():
                                    os.kill(os.getpid(), signal.SIGUSR1)
                                elif DEBUG:
                                    logger.debug("Auto-refresh: Signal not sent - auto_refresh deactivated or shutdown requested")
                            except ProcessLookupError:
                                # Process might be shutting down
                                if DEBUG:
                                    logger.debug("Auto-refresh: Could not send SIGUSR1, process may be shutting down")
                        else:
                            if DEBUG and auto_refresh_active:
                                logger.debug("Auto-refresh: No changes detected")
                    except Exception as e:
                        if DEBUG:
                            logger.error(f"Auto-refresh: Error during change check: {e}")
                        # Continue running even if one check fails, unless shutdown is requested
                        if shutdown_requested.is_set():
                            break
                else:
                    if DEBUG:
                        logger.debug("Auto-refresh: auto_refresh_active is False or shutdown requested, breaking loop")
                    break
        except Exception as e:
            if DEBUG:
                logger.error(f"Auto-refresh worker thread crashed: {e}")
        finally:
            if DEBUG:
                logger.debug("Auto-refresh worker thread stopped")

    def start_auto_refresh():
        """Start the auto-refresh monitoring if enabled."""
        nonlocal auto_refresh_active, refresh_thread
        if AUTO_REFRESH and not auto_refresh_active:
            if DEBUG:
                logger.debug(f"Starting auto-refresh: enabled={AUTO_REFRESH}, interval={AUTO_REFRESH_INTERVAL}s")
            auto_refresh_active = True
            refresh_thread = threading.Thread(target=auto_refresh_worker, daemon=True)
            refresh_thread.start()
            if DEBUG:
                logger.debug(f"Auto-refresh thread started: {refresh_thread}")
        else:
            if DEBUG:
                logger.debug(f"Auto-refresh not started: enabled={AUTO_REFRESH}, already_active={auto_refresh_active}")

    def stop_auto_refresh():
        """Stop the auto-refresh monitoring."""
        nonlocal auto_refresh_active, refresh_thread
        if auto_refresh_active:
            if DEBUG:
                logger.debug("STOPPING AUTO-REFRESH - Called from stop_auto_refresh()")
                logger.debug("Stopping auto-refresh...")
            auto_refresh_active = False
            shutdown_requested.set()  # Signal shutdown to all threads
            if refresh_thread:
                try:
                    refresh_thread.join(timeout=2)
                    if refresh_thread.is_alive() and DEBUG:
                        logger.warning("Auto-refresh thread did not stop cleanly")
                except Exception as e:
                    if DEBUG:
                        logger.error(f"Error stopping auto-refresh thread: {e}")
                    # Don't re-raise; we're shutting down anyway
                refresh_thread = None
            if DEBUG:
                logger.debug("Auto-refresh stopped")

    class AutoRefreshSuspender:
        """Context manager to temporarily suspend auto-refresh during critical operations."""
        def __init__(self):
            self.was_active = False

        def __enter__(self):
            nonlocal auto_refresh_active
            self.was_active = auto_refresh_active
            if self.was_active:
                if DEBUG:
                    logger.debug("AUTO-REFRESH: Suspending for critical operation")
                auto_refresh_active = False
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            nonlocal auto_refresh_active
            if self.was_active:
                auto_refresh_active = True
                if DEBUG:
                    logger.debug("AUTO-REFRESH: Resumed after critical operation")

    def main_menu_prompt_with_refresh(MODEL: str, title: str, choices: list, refresh_event: threading.Event):
        """
        Enhanced main menu prompt that can be interrupted by auto-refresh.
        Uses a simple approach - just check for refresh before prompting.
        """
        # Check if refresh is needed before starting prompt
        if refresh_event.is_set():
            return None  # Indicate refresh needed

        try:
            # If we're already flagged for a refresh, bail early
            return main_menu_prompt(MODEL, title, choices)
        except RefreshMenuException:
            # Our signal handler raised this in-flight → immediately rebuild menu
            return None
        except (OSError, EOFError):
            # If terminal issues, fall back to a simple text-based approach
            console.print("[yellow]Terminal input issues detected. Using simplified menu...[/yellow]")
            for i, choice in enumerate(choices):
                console.print(f"{i+1}. {choice}")

            # For testing environments where input() blocks indefinitely,
            # provide a timeout mechanism
            import select
            import sys

            attempt_count = 0
            while True:
                if refresh_event.is_set():
                    return None  # Refresh needed

                attempt_count += 1
                if attempt_count > 100:  # Prevent infinite loops in non-interactive environments
                    console.print("[yellow]Non-interactive environment detected. Auto-selecting first option.[/yellow]")
                    return choices[0] if choices else "Exit"

                try:
                    # Check if we're in a non-interactive environment
                    if not sys.stdin.isatty():
                        time.sleep(0.1)  # Brief pause to allow refresh checks
                        continue

                    user_input = input("Enter choice number: ").strip()
                    choice_num = int(user_input) - 1
                    if 0 <= choice_num < len(choices):
                        return choices[choice_num]
                    else:
                        console.print("[red]Invalid choice. Please try again.[/red]")
                except (ValueError, EOFError, KeyboardInterrupt):
                    raise KeyboardInterrupt()
                except Exception:
                    console.print("[red]Input error. Please try again.[/red]")

    def loop():
        """Main application loop that handles user interactions."""
        nonlocal exit_prompted, last_staged_state, last_unstaged_state, auto_refresh_active, menu_needs_refresh
        global MODEL, MODEL_CACHE

        # Load saved model from cache at startup
        cached_model = MODEL_CACHE.get("last_model", None)
        if cached_model:
            MODEL = cached_model

        # Start auto-refresh if enabled
        start_auto_refresh()

        try:
            while True:
                try:
                    # Check if auto-refresh is requesting a menu refresh
                    if menu_needs_refresh.is_set():
                        reset_console()
                        console.print("[bold green]📡 Repository changes detected, refreshing menu...[/bold green]")
                        menu_needs_refresh.clear()
                        continue

                    # Always refresh status before showing the menu
                    diff, unstaged_diff, staged_changes, unstaged_changes = get_and_display_status()

                    # Update the state tracking for auto-refresh with thread safety
                    with state_lock:
                        last_staged_state = {f.get('file', ''): (f.get('additions', 0), f.get('deletions', 0)) for f in staged_changes}
                        last_unstaged_state = {f.get('file', ''): (f.get('additions', 0), f.get('deletions', 0)) for f in unstaged_changes}

                    console.print("\n")
                    title, repo_status, choices = get_menu_options(MODEL, staged_changes, unstaged_changes)
                    console.print(repo_status, justify="left")

                    # Present main menu with styling
                    try:
                        if AUTO_REFRESH and auto_refresh_active:
                            action = main_menu_prompt_with_refresh(MODEL, title, choices, menu_needs_refresh)
                            if action is None:
                                # Refresh was requested, continue to top of loop
                                reset_console()
                                console.print("[bold green]📡 Repository changes detected, refreshing menu...[/bold green]")
                                menu_needs_refresh.clear()
                                continue
                        else:
                            action = main_menu_prompt(MODEL, title, choices)
                    except (OSError, EOFError) as e:
                        if DEBUG:
                            logger.error(f"Terminal input error: {e}")
                        console.print("[bold red]Terminal input error. Please try running in a proper terminal.[/bold red]")
                        break

                except KeyboardInterrupt:
                    # Handle normal Ctrl+C from user
                    exit_prompted += 1
                    if exit_prompted == 1:
                        reset_console()
                        console.print(
                            "[bold yellow]⚠️  Press Ctrl+C again to exit GitSmart[/bold yellow]",
                            justify="center"
                        )
                        # Give user a moment to decide
                        time.sleep(0.5)
                        continue
                    elif exit_prompted >= 2:
                        reset_console()
                        console.print("[bold red]🛑 Shutting down GitSmart...[/bold red]", justify="center")
                        if DEBUG:
                            logger.debug("STOPPING AUTO-REFRESH - User exit via double Ctrl+C")
                        stop_auto_refresh()
                        break
                    else:
                        continue


                # Reset exit counter on successful action
                exit_prompted = 0

                if action.startswith("Generate Commit for Staged Changes"):
                    reset_console()
                    # Use context manager to safely suspend auto-refresh during commit generation
                    with AutoRefreshSuspender():
                        try:
                            status_msg = handle_generate_commit(MODEL, diff, staged_changes)
                            # No need to refresh here; will refresh at top of loop
                            if status_msg:
                                console.print(status_msg)
                        except KeyboardInterrupt:
                            reset_console()
                            console.print("[bold yellow]⚠️  Commit generation interrupted[/bold yellow]")
                            console.print("[dim]Returning to main menu...[/dim]")
                            time.sleep(1)
                    continue

                elif action == "Review Changes":
                    reset_console()
                    handle_review_changes(staged_changes, unstaged_changes, diff, unstaged_diff)

                elif action.startswith("↑ Stage Files"):
                    # Use context manager to safely suspend auto-refresh during nested prompts
                    with AutoRefreshSuspender():
                        status_msg = handle_stage_files(unstaged_changes)
                        reset_console()
                        console.print(status_msg)

                elif action.startswith("↓ Unstage Files"):
                    # Use context manager to safely suspend auto-refresh during nested prompts
                    with AutoRefreshSuspender():
                        status_msg = handle_unstage_files(staged_changes)
                        reset_console()
                        console.print(status_msg)

                elif action == "Ignore Files":
                    handle_ignore_files()
                    reset_console()

                elif action == "View Commit History":
                    reset_console()
                    commits = display_commit_summary(20)
                    selected_commit_data = select_commit(commits)
                    if selected_commit_data:
                        print_commit_details(selected_commit_data)

                elif action == "Select Model":
                    reset_console()
                    MODEL = select_model()
                    # select_model already updates the cache, so no need to do it again here
                    console.print(f"[bold green]Model selected:[/bold green] {MODEL}")

                elif action == "Push Repo":
                    reset_console()
                    status_msg = handle_push_repo()
                    console.print(status_msg)

                elif action == "Summarize Commits":
                    reset_console()
                    summarize_selected_commits()

                elif action == "Exit":
                    reset_console()
                    console.print("[bold red]Goodbye...[/bold red]")
                    if DEBUG:
                        logger.debug("STOPPING AUTO-REFRESH - User selected Exit")
                    stop_auto_refresh()
                    break
        except Exception as e:
            if DEBUG:
                logger.error(f"Unexpected error in main loop: {e}")
            console.print(f"[bold red]Unexpected error: {e}[/bold red]")
            if DEBUG:
                logger.debug("STOPPING AUTO-REFRESH - Exception in main loop")
            stop_auto_refresh()
            return

    if reload:
        refresh_interval = 5
        console.print(
            f"[bold yellow]Auto-reload is enabled. Repository status will refresh every {refresh_interval} seconds.[/bold yellow]"
        )

        def auto_refresh():
            while True:
                console.print("[bold yellow]...[/bold yellow]")
                time.sleep(refresh_interval)
                printer.print_divider("Auto Refresh")
                get_and_display_status()
                sys.stdout.flush()

        refresh_thread = threading.Thread(target=auto_refresh, daemon=True)
        refresh_thread.start()

    if AUTO_REFRESH and not reload:
        console.print(
            f"[bold cyan]🔄 Auto-refresh enabled - monitoring git changes every {AUTO_REFRESH_INTERVAL}s[/bold cyan]"
        )

    try:
        loop()
    except KeyboardInterrupt:
        if DEBUG:
            logger.debug("STOPPING AUTO-REFRESH - KeyboardInterrupt in main()")
        stop_auto_refresh()
        console.print("\n[bold red]🛑 GitSmart terminated[/bold red]")
        sys.exit(0)
    except Exception as e:
        if DEBUG:
            logger.error(f"STOPPING AUTO-REFRESH - Exception in main(): {e}")
        stop_auto_refresh()
        console.print(f"\n[bold red]❌ Unexpected error: {e}[/bold red]")
        sys.exit(1)
    else:
        if DEBUG:
            logger.debug("STOPPING AUTO-REFRESH - Normal exit from main()")
        stop_auto_refresh()
        console.print("[bold green]✅ GitSmart exited cleanly[/bold green]")
def cmd_add_files(args):
    """Add untracked files to Git repository."""
    from .git_utils import add_files
    from .repo_manager import get_repo_manager, find_repo
    from .ui import console

    files = args.files
    repo_name = args.repo if hasattr(args, 'repo') and args.repo else None

    if not files:
        console.print("[bold red]❌ No files specified for adding[/bold red]")
        return

    # Handle repository switching
    original_cwd = None
    repo_info = None

    try:
        if repo_name:
            repo_info = find_repo(repo_name)
            if not repo_info:
                console.print(f"[bold red]❌ Repository '{repo_name}' not found[/bold red]")
                return

            original_cwd = os.getcwd()
            os.chdir(repo_info["path"])
        else:
            # Use current repository
            repo_manager = get_repo_manager()
            repo_info = repo_manager.get_current_repository()
            if repo_info:
                repo_name = repo_info["name"]

        # Check which files exist and are untracked
        valid_files = []
        invalid_files = []
        already_tracked = []

        for file_path in files:
            if not os.path.exists(file_path):
                invalid_files.append(file_path)
                continue

            # Check if file is already tracked
            try:
                import subprocess
                result = subprocess.run(
                    ["git", "ls-files", "--", file_path],
                    capture_output=True, text=True, check=True
                )
                if result.stdout.strip():
                    already_tracked.append(file_path)
                else:
                    valid_files.append(file_path)
            except subprocess.CalledProcessError:
                # If git ls-files fails, assume it's untracked
                valid_files.append(file_path)

        # Display status
        if invalid_files:
            console.print(f"[bold red]❌ Files not found: {', '.join(invalid_files)}[/bold red]")
        if already_tracked:
            console.print(f"[bold yellow]⚠️  Already tracked: {', '.join(already_tracked)}[/bold yellow]")

        # Add valid untracked files
        if valid_files:
            try:
                add_files(valid_files)
                console.print(f"[bold green]✅ Successfully added: {', '.join(valid_files)}[/bold green]")

                if repo_name:
                    console.print(f"[dim]Repository: {repo_name}[/dim]")

            except Exception as e:
                console.print(f"[bold red]❌ Git add failed: {str(e)}[/bold red]")
        else:
            if not invalid_files and not already_tracked:
                console.print("[bold yellow]⚠️  No valid untracked files to add[/bold yellow]")

    except Exception as e:
        logger.error(f"Error adding files: {e}")
        console.print(f"[bold red]❌ Error adding files: {str(e)}[/bold red]")
    finally:
        if original_cwd:
            os.chdir(original_cwd)


def entry_point():
    """
    Minimal wrapper for console_scripts entry point.
    Parses command line arguments and launches the main application.
    """
    parser = argparse.ArgumentParser(
        description="Automate git commit messages with enhanced features.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Default command (interactive mode)
    default_parser = subparsers.add_parser('ui', help='Launch interactive UI (default)')
    default_parser.add_argument("--reload", action="store_true", help="Enable auto-refresh of repository status.")
    default_parser.set_defaults(func=lambda args: main(reload=args.reload))

    # Add files command
    add_parser = subparsers.add_parser('add', help='Add untracked files to Git repository')
    add_parser.add_argument('files', nargs='+', help='Files to add to Git tracking')
    add_parser.add_argument('--repo', '-r', help='Repository name (optional, uses current repo if not specified)')
    add_parser.set_defaults(func=cmd_add_files)

    # Repository management commands
    from .repo_cli import create_repo_parser, handle_repo_command
    repo_parser = create_repo_parser(subparsers)
    repo_parser.set_defaults(func=handle_repo_command)

    # Parse arguments
    args = parser.parse_args()

    # If no command specified, default to interactive UI
    if not args.command:
        main(reload=False)
        return

    # Handle top-level KeyboardInterrupt gracefully
    try:
        if hasattr(args, 'func'):
            args.func(args)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[bold red]🛑 GitSmart terminated by user[/bold red]")
        sys.exit(0)
    except Exception as e:
        console = Console()
        console.print(f"\n[bold red]❌ Fatal error: {e}[/bold red]")
        sys.exit(1)

if __name__ == "__main__":

    entry_point()
