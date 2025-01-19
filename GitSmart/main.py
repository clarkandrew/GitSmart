# GitSmart/main.py

import argparse
import sys
import time

from .config import logger, MODEL, DEBUG
from .ui import console, printer
from .cli_flow import (
    get_and_display_status,
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

    def loop():
        nonlocal exit_prompted
        diff, unstaged_diff, staged_changes, unstaged_changes = get_and_display_status()
        global MODEL
        selected_model = MODEL
        while True:
            try:
                title, repo_status, choices = get_menu_options(staged_changes, unstaged_changes)
                console.print(repo_status, justify="left")

                # Present main menu with styling
                action = main_menu_prompt(title, choices)

                if action.startswith("Generate Commit for Staged Changes"):
                    reset_console()
                    status_msg = handle_generate_commit(MODEL, diff, staged_changes)
                    diff, unstaged_diff, staged_changes, unstaged_changes = get_and_display_status()
                    if status_msg:
                        console.print(status_msg)

                elif action == "Review Changes":
                    reset_console()
                    handle_review_changes(staged_changes, unstaged_changes, diff, unstaged_diff)
                    diff, unstaged_diff, staged_changes, unstaged_changes = get_and_display_status()

                elif action == "Stage Files":
                    status_msg = handle_stage_files(unstaged_changes)
                    reset_console()
                    diff, unstaged_diff, staged_changes, unstaged_changes = get_and_display_status()
                    console.print(status_msg)

                elif action == "Unstage Files":
                    status_msg = handle_unstage_files(staged_changes)
                    reset_console()
                    diff, unstaged_diff, staged_changes, unstaged_changes = get_and_display_status()
                    console.print(status_msg)

                elif action == "Ignore Files":
                    handle_ignore_files()
                    reset_console()
                    diff, unstaged_diff, staged_changes, unstaged_changes = get_and_display_status()

                elif action == "View Commit History":
                    reset_console()
                    commits = display_commit_summary(20)
                    selected_commit_data = select_commit(commits)
                    if selected_commit_data:
                        print_commit_details(selected_commit_data)

                elif action == "Select Model":
                    reset_console()
                    MODEL = select_model()
                    diff, unstaged_diff, staged_changes, unstaged_changes = get_and_display_status()
                    console.print(f"[bold green]Model selected:[/bold green] {MODEL}")

                elif action == "Push Repo":
                    reset_console()
                    status_msg = handle_push_repo()
                    diff, unstaged_diff, staged_changes, unstaged_changes = get_and_display_status()
                    console.print(status_msg)

                elif action == "Summarize Commits":
                    reset_console()
                    summarize_selected_commits()
                    diff, unstaged_diff, staged_changes, unstaged_changes = get_and_display_status()

                elif action == "Exit":
                    reset_console()
                    console.print("[bold red]Goodbye...[/bold red]")
                    break

            except KeyboardInterrupt:
                exit_prompted += 1
                if exit_prompted >= 3:
                    reset_console()
                    console.print("[bold]Goodbye...[/bold]")
                    break
                else:
                    reset_console()
                    console.print(
                        f"[bold black on red]Press Ctrl+C {3 - exit_prompted} more time(s) to exit.[/bold black on red]",
                        justify="center"
                    )

    if reload:
        refresh_interval = 5
        console.print(
            f"[bold yellow]Auto-reload is enabled. Repository status will refresh every {refresh_interval} seconds.[/bold yellow]"
        )

        import threading
        def auto_refresh():
            while True:
                console.print("[bold yellow]...[/bold yellow]")
                time.sleep(refresh_interval)
                printer.print_divider("Auto Refresh")
                diff, unstaged_diff, staged_changes, unstaged_changes = get_and_display_status()
                sys.stdout.flush()

        refresh_thread = threading.Thread(target=auto_refresh, daemon=True)
        refresh_thread.start()

    loop()

def entry_point():
    """
    Minimal wrapper for console_scripts entry point.
    """
    parser = argparse.ArgumentParser(description="Automate git commit messages with enhanced features.")
    parser.add_argument("--reload", action="store_true", help="Enable auto-refresh of repository status.")
    args = parser.parse_args()
    main(reload=args.reload)

if __name__ == "__main__":

    entry_point()
