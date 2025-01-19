import argparse
import sys
import time

from .config import logger, MODEL, DEBUG
from .ui import console, printer
from .cli_flow import (
    get_and_display_status, handle_generate_commit, handle_review_changes,
    display_commit_summary, select_commit, print_commit_details,
    handle_stage_files, handle_unstage_files, handle_ignore_files,
    handle_push_repo, summarize_selected_commits, select_model,
    reset_console
)
from .git_utils import get_repo_name

"""
Main entry point for the C0MIT application. Ties together
the various modules and orchestrates the CLI loop.
"""

def main(reload: bool = False):
    """
    Main function to generate and commit a message based on staged changes.
    Incorporates repeated status checks, menu selection, and user actions.
    """
    console.print("# GitSmart")
    repo_name = get_repo_name()
    display_commit_summary(3)
    exit_prompted = 0

    def loop():
        nonlocal exit_prompted
        diff, unstaged_diff, staged_changes, unstaged_changes = get_and_display_status()

        while True:
            try:
                total_additions = sum(change["additions"] for change in staged_changes + unstaged_changes)
                total_deletions = sum(change["deletions"] for change in staged_changes + unstaged_changes)
                console.print(
                    f"\n\n[bold white on black]{repo_name} [green]+{total_additions}[/green], [red]-{total_deletions}[/]"
                )

                title, repo_status, choices = get_menu_options(staged_changes, unstaged_changes)
                console.print(repo_status)

                import questionary
                action = questionary.select(
                    title,
                    choices=choices,
                    style=None  # or configure_questionary_style()
                ).unsafe_ask()

                if action.startswith("Generate Commit for Staged Changes"):
                    reset_console()
                    status_msg = handle_generate_commit(diff, staged_changes)
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
                    console.print(f"Model selected: {MODEL}")

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

    # Additional function from original code that decides menu options
    from .cli_flow import get_menu_options

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
                diff, unstaged_diff, staged_changes, unstaged_changes = get_and_display_status()
                total_additions = sum(change["additions"] for change in staged_changes + unstaged_changes)
                total_deletions = sum(change["deletions"] for change in staged_changes + unstaged_changes)
                console.print(f"{repo_name} [green]+{total_additions}[/green], [red]-{total_deletions}[/]")
                sys.stdout.flush()

        import threading
        refresh_thread = threading.Thread(target=auto_refresh, daemon=True)
        refresh_thread.start()

    loop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automate git commit messages with enhanced features.")
    parser.add_argument("--reload", action="store_true", help="Enable auto-refresh of repository status.")
    args = parser.parse_args()
    main(reload=args.reload)
