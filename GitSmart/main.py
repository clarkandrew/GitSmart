# GitSmart/main.py

import argparse
import sys
import time
import threading
import signal
import os


from .config import logger, MODEL, DEBUG, MODEL_CACHE, AUTO_REFRESH, AUTO_REFRESH_INTERVAL
from .ui import console, printer
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

"""
main.py

- Orchestrates the main application loop
- Always uses get_and_display_status() to show both staged/unstaged
- Passes dynamic menu from get_menu_options() to main_menu_prompt
"""
def main(reload: bool = False):

    console.print("[bold cyan]# GitSmart[/bold cyan]")
    display_commit_summary(3)

    exit_prompted = 0
    auto_refresh_active = False
    refresh_thread = None
    last_staged_state = None
    last_unstaged_state = None
    state_lock = threading.Lock()

    # Flag to track when menu needs refresh
    menu_needs_refresh = threading.Event()

    # ─── Setup custom signal & exception for mid-prompt refresh ───────────────────
    class RefreshMenuException(Exception):
        """Raised to abort the questionary prompt so we can refresh the menu."""
        pass

    def _refresh_signal_handler(signum, frame):
        # When we get SIGUSR1, raise our custom exception in the main thread
        raise RefreshMenuException()

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
                    logger.info(f"Auto-refresh check - Changed: {changed}")
                if changed:
                    logger.info(f"Auto-refresh check - Previous staged: {last_staged_state}")
                    logger.info(f"Auto-refresh check - Previous unstaged: {last_unstaged_state}")
                    logger.info(f"Auto-refresh check - Current staged: {current_staged_files}")
                    logger.info(f"Auto-refresh check - Current unstaged: {current_unstaged_files}")
                    logger.info(f"Auto-refresh: Repository changes detected!")

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
            logger.info(f"Auto-refresh worker thread started (PID: {os.getpid()})")
            logger.info(f"Initial auto_refresh_active state: {auto_refresh_active}")
            logger.info(f"AUTO_REFRESH_INTERVAL: {AUTO_REFRESH_INTERVAL}")

        try:
            loop_count = 0
            while auto_refresh_active:
                loop_count += 1
                if DEBUG:
                    logger.info(f"Auto-refresh: Loop iteration #{loop_count}, sleeping for {AUTO_REFRESH_INTERVAL}s")
                time.sleep(AUTO_REFRESH_INTERVAL)

                if auto_refresh_active:
                    try:
                        if DEBUG:
                            logger.info("Auto-refresh: Checking for changes...")
                        if check_for_changes():
                            if DEBUG:
                                logger.info("Auto-refresh: Repository changes detected, setting refresh flag")
                            # mark for refresh
                            menu_needs_refresh.set()
                            # actually break any in-flight Questionary prompt
                            os.kill(os.getpid(), signal.SIGUSR1)
                        else:
                            if DEBUG:
                                logger.info("Auto-refresh: No changes detected")
                    except Exception as e:
                        if DEBUG:
                            logger.error(f"Auto-refresh: Error during change check: {e}")
                        # Continue running even if one check fails
                else:
                    if DEBUG:
                        logger.info("Auto-refresh: auto_refresh_active is False, breaking loop")
                    break
        except Exception as e:
            if DEBUG:
                logger.error(f"Auto-refresh worker thread crashed: {e}")
        finally:
            if DEBUG:
                logger.info("Auto-refresh worker thread stopped")

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
            logger.info("STOPPING AUTO-REFRESH - Called from stop_auto_refresh()")
            if DEBUG:
                logger.debug("Stopping auto-refresh...")
            auto_refresh_active = False
            if refresh_thread:
                try:
                    refresh_thread.join(timeout=2)
                    if refresh_thread.is_alive() and DEBUG:
                        logger.warning("Auto-refresh thread did not stop cleanly")
                except Exception as e:
                    logger.error(f"Error stopping auto-refresh thread: {e}")
            if DEBUG:
                logger.debug("Auto-refresh stopped")

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
                    if exit_prompted >= 3:
                        break
                    else:
                        reset_console()
                        console.print(
                            f"[bold black on red]Press Ctrl+C {3 - exit_prompted} more time(s) to exit.[/bold black on red]",
                            justify="center"
                        )
                        continue


                # Reset exit counter on successful action
                exit_prompted = 0

                if action.startswith("Generate Commit for Staged Changes"):
                    reset_console()
                    status_msg = handle_generate_commit(MODEL, diff, staged_changes)
                    # No need to refresh here; will refresh at top of loop
                    if status_msg:
                        console.print(status_msg)

                elif action == "Review Changes":
                    reset_console()
                    handle_review_changes(staged_changes, unstaged_changes, diff, unstaged_diff)

                elif action.startswith("↑ Stage Files"):
                    # Temporarily pause auto-refresh during nested prompts
                    was_active = auto_refresh_active
                    if was_active:
                        logger.info("STOPPING AUTO-REFRESH - Pausing for stage files prompt")
                        auto_refresh_active = False
                        if DEBUG:
                            logger.debug("Auto-refresh paused for nested prompt")

                    try:
                        status_msg = handle_stage_files(unstaged_changes)
                        reset_console()
                        console.print(status_msg)
                    finally:
                        # Resume auto-refresh
                        if was_active:
                            auto_refresh_active = True
                            if DEBUG:
                                logger.debug("Auto-refresh resumed after nested prompt")

                elif action.startswith("↓ Unstage Files"):
                    # Temporarily pause auto-refresh during nested prompts
                    was_active = auto_refresh_active
                    if was_active:
                        logger.info("STOPPING AUTO-REFRESH - Pausing for unstage files prompt")
                        auto_refresh_active = False
                        if DEBUG:
                            logger.debug("Auto-refresh paused for nested prompt")

                    try:
                        status_msg = handle_unstage_files(staged_changes)
                        reset_console()
                        console.print(status_msg)
                    finally:
                        # Resume auto-refresh
                        if was_active:
                            auto_refresh_active = True
                            if DEBUG:
                                logger.debug("Auto-refresh resumed after nested prompt")

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
                    logger.info("STOPPING AUTO-REFRESH - User selected Exit")
                    stop_auto_refresh()
                    break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            console.print(f"[bold red]Unexpected error: {e}[/bold red]")
            logger.info("STOPPING AUTO-REFRESH - Exception in main loop")
            stop_auto_refresh()
            return

    if reload:
        refresh_interval = 5
        console.print(
            f"[bold yellow]Auto-reload is enabled. Repository status will refresh every {refresh_interval} seconds.[/bold yellow]"
        )

        import threading as reload_threading
        def auto_refresh():
            while True:
                console.print("[bold yellow]...[/bold yellow]")
                time.sleep(refresh_interval)
                printer.print_divider("Auto Refresh")
                get_and_display_status()
                sys.stdout.flush()

        refresh_thread = reload_threading.Thread(target=auto_refresh, daemon=True)
        refresh_thread.start()

    if AUTO_REFRESH and not reload:
        console.print(
            f"[bold cyan]🔄 Auto-refresh enabled - monitoring git changes every {AUTO_REFRESH_INTERVAL}s[/bold cyan]"
        )

    try:
        loop()
    except KeyboardInterrupt:
        logger.info("STOPPING AUTO-REFRESH - KeyboardInterrupt in main()")
        stop_auto_refresh()
        raise
    except Exception as e:
        logger.error(f"STOPPING AUTO-REFRESH - Exception in main(): {e}")
        stop_auto_refresh()
        raise
    else:
        logger.info("STOPPING AUTO-REFRESH - Normal exit from main()")
        stop_auto_refresh()
def entry_point():
    """
    Minimal wrapper for console_scripts entry point.
    Parses command line arguments and launches the main application.
    """
    parser = argparse.ArgumentParser(description="Automate git commit messages with enhanced features.")
    parser.add_argument("--reload", action="store_true", help="Enable auto-refresh of repository status.")
    args = parser.parse_args()
    main(reload=args.reload)

if __name__ == "__main__":

    entry_point()
