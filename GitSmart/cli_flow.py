# GitSmart/cli_flow.py

import os
import re
import sys
import time
import threading
import questionary
from typing import List, Dict, Any, Tuple, Optional

from .config import logger
from .ui import console, printer, create_styled_table, configure_questionary_style
from .git_utils import (
    parse_diff,
    get_git_diff,
    get_file_diff,
    stage_files,
    unstage_files,
    run_git_command,
    get_repo_name,
    get_git_remotes,
    push_to_remote
)
from .ai_utils import generate_commit_message, generate_summary, extract_tag_value

"""
cli_flow.py

- Core user flows: staging, diff review, commit generation
- Always shows both 'Unstaged Changes' and 'Staged Changes' panels
- Each file row has +X, -Y
- If none, show 'No changes' row
"""

def main_menu_prompt(title: str, choices: list) -> str:
    """
    Enhanced UI prompt for the main menu with questionary + custom style.
    """
    return questionary.select(
        title,
        choices=choices,
        style=configure_questionary_style(),
        instruction="(Use ↑/↓ to move, Enter to select)"
    ).unsafe_ask()

def get_menu_options(
    staged_changes: List[Dict[str, Any]],
    unstaged_changes: List[Dict[str, Any]]
) -> Tuple[str, str, List[str]]:
    """
    Compute dynamic menu items based on presence of staged/unstaged changes.
    Returns a tuple of (title, status message with rich formatting, menu choices).
    Includes total additions/deletions in the status message.

    Enhanced so that when there are no changes at all (staged or unstaged),
    it omits "Stage Files", "Unstage Files", and "Review Changes" from the menu.
    """
    from .git_utils import get_repo_name

    # Base choices that are always relevant
    base_choices = [
        "View Commit History",
        "Summarize Commits",
        "Push Repo",
        "Ignore Files",
        "Select Model",
        "Exit"
    ]

    # We will build the final choices here
    dynamic_choices = []

    # Calculate change statistics
    total_additions = sum(ch["additions"] for ch in staged_changes + unstaged_changes)
    total_deletions = sum(ch["deletions"] for ch in staged_changes + unstaged_changes)

    # Basic repo name fallback
    repo_name = get_repo_name() or "UnknownRepo"

    # Conditionally add menu items based on presence of changes
    has_staged = bool(staged_changes)
    has_unstaged = bool(unstaged_changes)

    # 1. If we have staged changes
    if has_staged:
        dynamic_choices.append("Unstage Files")
        dynamic_choices.append(f"Generate Commit for Staged Changes ({len(staged_changes)})")

    # 2. If we have unstaged changes
    if has_unstaged:
        dynamic_choices.append("Stage Files")

    # 3. If we have either staged or unstaged changes, user might still want to "Review Changes"
    if has_staged or has_unstaged:
        dynamic_choices.append("Review Changes")

    # Determine overall repo status with color formatting
    if has_staged and has_unstaged:
        repo_status = "[#FFF781]⚠[/] [bold black on yellow] Staged and unstaged changes found[/]\n"
    elif has_staged:
        repo_status = "[blue]➤[/] [bold white on blue] Staged changes found[/]\n"
    elif has_unstaged:
        repo_status = "[yellow]✗[/] [italic #FFF781] Unstaged changes found[/]\n"
    else:
        repo_status = "[green]✔[/] [bold black on green] All changes are up to date[/]"

    # Display totals in the status message
    repo_status += f"\n[bold white]{repo_name}[/bold white] [green]+{total_additions}[/green], [red]-{total_deletions}[/red]"

    title = "Select an action:"
    # Combine any dynamic choices with the always-available base ones
    choices = dynamic_choices + base_choices

    return title, repo_status, choices

def handle_files(changes: List[Dict[str, Any]], action: str) -> str:
    """
    Let the user pick files to stage or unstage from a checkbox list.
    """
    if not changes:
        return f"No {action}d changes found."

    choices = [f"{c['file']} (+{c['additions']}/-{c['deletions']})" for c in changes]
    selected_files = questionary.checkbox(
        f"Select files to {action}:",
        choices=choices,
        style=configure_questionary_style()
    ).unsafe_ask()

    if selected_files:
        files = [f.split()[0] for f in selected_files]
        if action == "stage":
            result = stage_files(files)
        else:
            result = unstage_files(files)
        if "Error" in result:
            logger.error(f"Failed to {action} files: {files}")
        return result

    return f"No files selected to {action}."

def handle_stage_files(unstaged_changes: List[Dict[str, Any]]) -> str:
    return handle_files(unstaged_changes, "stage")

def handle_unstage_files(staged_changes: List[Dict[str, Any]]) -> str:
    return handle_files(staged_changes, "unstage")

def display_diff_panel(
    filename: str,
    diff_lines: List[str],
    file_changes: List[Dict[str, Any]],
    panel_width: int = 100
):
    """
    Show a single file's diff in a Rich Panel.
    """
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.padding import Padding
    from rich.align import Align

    if not diff_lines:
        diff_text = "No changes."
    else:
        diff_text = "\n".join(diff_lines)

    is_staged = any(ch["file"] == filename for ch in file_changes)
    title = f"[bold blue]{filename}[/bold blue] [{'Staged' if is_staged else 'Unstaged'}]"
    syntax = Syntax(diff_text, "diff", theme="github-dark", line_numbers=True)

    changes = next((ch for ch in file_changes if ch["file"] == filename), {})
    additions = changes.get("additions", 0)
    deletions = changes.get("deletions", 0)
    footer = f"[bold green]+{additions}[/], [bold red]-{deletions}[/]"

    panel = Padding(
        Panel(
            Align.center(syntax),
            title=title,
            border_style="#0D1116",
            style="",
            padding=(1, 2),
            subtitle=footer,
            width=panel_width
        ),
        (1, 2)
    )
    return Align.center(panel)

def get_diff_summary_panel(
    file_changes: List[Dict[str, Any]],
    title: str,
    subtitle: str,
    panel_width: int = 100,
    _panel_style: str = "bold white on rgb(39,40,34)"
):
    """
    Create a table summarizing each file's +X, -Y changes.
    """
    from rich.table import Table

    color = "red" if title == "Unstaged Changes" else "green"
    table = Table(
        show_header=False,
        header_style=f"bold {color}",
        style=f"italic {color}",
        show_lines=False,
        box=None
    )
    table.add_column("File", justify="left", style="bold white", no_wrap=True)
    table.add_column("Additions", justify="right", style="green")
    table.add_column("Deletions", justify="right", style="red")

    for ch in file_changes:
        table.add_row(ch["file"], f"+{ch['additions']}", f"-{ch['deletions']}")
    return table

def display_file_diffs(
    diff: str,
    staged_file_changes: List[Dict[str, Any]],
    subtitle: str,
    panel_width: int = 100
):
    """
    For each file in the diff, display a separate Rich panel with syntax highlighting.
    """
    from rich.console import Group
    import re

    file_pattern = re.compile(r"diff --git a/(.+?) b/(.+)")
    current_file = None
    current_diff = []
    panels = []

    for line in diff.splitlines():
        match = file_pattern.match(line)
        if match:
            if current_file:
                panel = display_diff_panel(current_file, current_diff, staged_file_changes, panel_width=panel_width)
                if panel:
                    panels.append(panel)
            current_file = match.group(2)
            current_diff = [line]
        else:
            current_diff.append(line)

    # Last file
    if current_file:
        panel = display_diff_panel(current_file, current_diff, staged_file_changes, panel_width=panel_width)
        if panel:
            panels.append(panel)

    if panels:
        grouped_panels = Group(*panels)
        console.print(grouped_panels)
    else:
        console.print("[bold yellow]No diffs to display.[/bold yellow]")

def handle_generate_commit(MODEL: str, diff: str, staged_changes: List[Dict[str, Any]]):
    """
    Generate commit message with AI, let the user commit or edit the result.
    """
    from rich.panel import Panel
    from rich.padding import Padding
    from rich.align import Align

    if not diff:
        console.print("[bold red]No staged changes found.[/bold red]")
        return

    display_file_diffs(diff, staged_changes, subtitle="Changes: Additions and Deletions")
    commit_message = generate_commit_message(MODEL, diff)

    if commit_message:
        printer.print_divider()
        console.print(
            Padding(Panel(
                Align.center(Padding(commit_message, (3, 5))),
                title=f"Commit Generated by {MODEL}",
                border_style="#ffffff",
                style="#ffffff on #0D1116"
            ), (3, 8))
        )
        printer.print_divider()

        action = questionary.select(
            "What would you like to do?",
            choices=["Commit", "Edit commit message", "Retry", "Cancel"],
            style=configure_questionary_style()
        ).unsafe_ask()

        printer.print_divider()

        if action == "Commit":
            commit_status = run_git_command(["git", "commit", "-m", commit_message])
            if "Success" in commit_status:
                return commit_status
            else:
                console.print(f"[bold red]{commit_status}[/bold red]")

        elif action == "Edit commit message":
            edited_commit = questionary.text(
                "Edit your commit message below:",
                multiline=True,
                default=commit_message,
                style=configure_questionary_style()
            ).unsafe_ask()

            # Show updated commit
            console.print(
                Padding(Panel(
                    Align.center(Padding(edited_commit, (3, 5))),
                    title="Edited Commit Message",
                    border_style="#ffffff",
                    style="#ffffff on #0D1116"
                ), (3, 8))
            )

            confirm_edit = questionary.select(
                "Use this edited commit message?",
                choices=["Commit", "Retry", "Cancel"],
                style=configure_questionary_style()
            ).unsafe_ask()

            if confirm_edit == "Commit":
                commit_status = run_git_command(["git", "commit", "-m", edited_commit])
                return commit_status
            elif confirm_edit == "Retry":
                logger.info("Retrying commit message generation.")
                return handle_generate_commit(MODEL, diff, staged_changes)
            else:
                logger.info("Commit aborted by user.")
                console.print("[bold yellow]Commit aborted by user.[/bold yellow]")

        elif action == "Retry":
            logger.info("Retrying commit message generation.")
            return handle_generate_commit(MODEL, diff, staged_changes)

        else:
            logger.info("Commit aborted by user.")
            console.print("[bold yellow]Commit aborted by user.[/bold yellow]")
    else:
        logger.error("Failed to generate a commit message.")
        console.print("[bold red]Failed to generate a commit message.[/bold red]")

def handle_review_changes(
    staged_changes: List[Dict[str, Any]],
    unstaged_changes: List[Dict[str, Any]],
    diff: str,
    unstaged_diff: str
):
    """
    Let the user select files from both staged & unstaged sets to see diffs individually.
    """
    import questionary

    staged_files = {ch["file"] for ch in staged_changes}
    unstaged_files = {ch["file"] for ch in unstaged_changes}
    all_files = staged_files.union(unstaged_files)

    if not all_files:
        console.print("[bold yellow]No changes to review.[/bold yellow]")
        return

    choices = []
    for file in sorted(all_files):
        label = f"{file} [Staged]" if file in staged_files else file
        choices.append(questionary.Choice(title=label, value=file, checked=(file in staged_files)))

    selected_files = questionary.checkbox(
        "Select files to review their diffs:",
        choices=choices,
        style=configure_questionary_style(),
        instruction="(Use space to select, Enter to confirm)"
    ).unsafe_ask()

    if not selected_files:
        console.print("[bold yellow]No files selected for review.[/bold yellow]")
        return

    for file in selected_files:
        is_staged = file in staged_files
        file_diff = get_file_diff(file, staged=is_staged)
        if file_diff:
            panel = display_diff_panel(file, file_diff, staged_changes + unstaged_changes, panel_width=100)
            console.print(panel)
        else:
            console.print(f"[bold red]No diff available for {file}.[/bold red]")

def get_diff_summary_table(file_changes: List[Dict[str, Any]], color: str):
    """
    Summarize file changes for display_status below. Each row is file +X -Y
    """
    from rich.table import Table
    from rich.padding import Padding

    table = Table(show_header=False, show_lines=True, box=None, padding=(0, 0))
    table.add_column("File", justify="left", style="bold white", no_wrap=True)
    table.add_column("Additions", justify="right", style="green")
    table.add_column("Deletions", justify="right", style="red")

    # If no changes, display one row with "No changes"
    if not file_changes:
        # Show "No changes" row
        table.add_row(
            Padding("No changes", (0, 2)),
            Padding("+0", (0, 2)),
            Padding("-0", (0, 2))
        )
        return table

    for ch in file_changes:
        table.add_row(
            Padding(ch["file"], (0, 2)),
            Padding(f"+{ch['additions']}", (0, 2)),
            Padding(f"-{ch['deletions']}", (0, 2))
        )
    return table

def display_status(
    unstaged_changes: List[Dict[str, Any]],
    staged_changes: List[Dict[str, Any]],
    staged: bool = True,
    unstaged: bool = True
):
    """
    Always display both 'Unstaged Changes' and 'Staged Changes' panels.
    If one set is empty, show 'No changes +0 -0' row to keep +/- columns consistent.
    """
    from rich.panel import Panel
    from rich.padding import Padding
    # Unstaged Panel
    if unstaged and unstaged_changes:
        unstaged_table = get_diff_summary_table(unstaged_changes, "red")
        unstaged_panel = Panel(
            Padding(unstaged_table,(1,2)),
            title_align="left",
            title="[bold white on red]Unstaged Changes[/]",
            border_style="red",
            width=50,
            expand=True
        )
        console.print(unstaged_panel)

    # Staged Panel
    if staged and staged_changes:
        staged_table = get_diff_summary_table(staged_changes, "green")
        staged_panel = Panel(
            Padding(staged_table,(1,2)),
            title_align="left",
            title="[bold black on green]Staged Changes[/]",
            border_style="green",
            width=50,
            expand=True
        )
        console.print(staged_panel)

def get_status() -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Return diffs for staged and unstaged changes, plus parse them into lists.
    """
    diff = get_git_diff(staged=True)
    unstaged_diff = get_git_diff(staged=False)
    staged_changes = parse_diff(diff)
    unstaged_changes = parse_diff(unstaged_diff)
    return diff, unstaged_diff, staged_changes, unstaged_changes

def get_and_display_status():
    """
    Always show both Unstaged Changes and Staged Changes panels,
    returning the raw diffs + parsed lists for further operations.
    """
    diff, unstaged_diff, staged_changes, unstaged_changes = get_status()
    # Force staged=True, unstaged=True so both panels appear every time
    display_status(unstaged_changes, staged_changes, staged=True, unstaged=True)
    return diff, unstaged_diff, staged_changes, unstaged_changes

def select_model():
    from prompt_toolkit.history import FileHistory
    import questionary

    history_dir = ".C0MMIT"
    if os.path.exists(history_dir) and not os.path.isdir(history_dir):
        raise FileExistsError(f"A file named '{history_dir}' already exists.")
    os.makedirs(history_dir, exist_ok=True)
    history_file = os.path.join(history_dir, "model_selection")

    global MODEL
    MODEL = questionary.text("Select a model:\n", history=FileHistory(history_file)).ask()
    return MODEL

def reset_console():
    """
    Clears the console thoroughly for cross-platform usage.
    """
    console.clear()
    print("\n" * 25)

def load_gitignore() -> List[str]:
    """
    Load .gitignore, returning lines from the custom-managed section if any.
    """
    gitignore_path = ".gitignore"
    start_marker = "# >>> Managed by GitSmart >>>"
    end_marker = "# <<< Managed by GitSmart <<<"

    if not os.path.exists(gitignore_path):
        return []

    with open(gitignore_path, "r") as f:
        lines = f.readlines()

    ignored_files = []
    in_managed_section = False
    for line in lines:
        if line.strip() == start_marker:
            in_managed_section = True
            continue
        if line.strip() == end_marker:
            in_managed_section = False
            continue
        if in_managed_section:
            stripped_line = line.strip()
            if stripped_line and not stripped_line.startswith("#"):
                ignored_files.append(stripped_line)

    return ignored_files

def save_gitignore_section(ignored_files: List[str]):
    """
    Save the updated list of ignored files to the special GitSmart-managed section.
    """
    gitignore_path = ".gitignore"
    start_marker = "# >>> Managed by GitSmart >>>\n"
    end_marker = "# <<< Managed by GitSmart <<<\n"

    managed_section = start_marker
    for file in ignored_files:
        managed_section += f"{file}\n"
    managed_section += end_marker

    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            content = f.read()
        # Remove any old managed section
        content = re.sub(r"# >>> Managed by GitSmart >>>\n.*?# <<< Managed by GitSmart <<<\n", "", content, flags=re.DOTALL)
        content = content.strip() + "\n\n" + managed_section
    else:
        content = managed_section

    with open(gitignore_path, "w") as f:
        f.write(content)

def update_gitignore(selected_files: List[str]):
    """
    Add newly selected files/patterns to the GitSmart-managed .gitignore section.
    """
    existing_ignored = set(load_gitignore())
    new_ignored = set(selected_files) - existing_ignored
    if not new_ignored:
        console.print("[bold yellow]No new files or patterns to add to .gitignore.[/bold yellow]")
        return

    all_ignored = sorted(existing_ignored.union(new_ignored))
    save_gitignore_section(all_ignored)

def handle_ignore_files():
    """
    Provide an option for selecting files or entering custom patterns to ignore.
    """
    import questionary
    ignored_files = load_gitignore()
    all_files = get_tracked_files()

    choices = [questionary.Choice(file, checked=(file in ignored_files)) for file in all_files]

    action = questionary.select(
        "Would you like to select files to ignore or enter custom patterns?",
        choices=["Select files", "Enter custom patterns"]
    ).unsafe_ask()

    if action == "Select files":
        selected_files = questionary.checkbox("Select files to ignore:", choices=choices).unsafe_ask()
    else:
        custom_patterns = questionary.text("Enter custom patterns to ignore (comma-separated):").unsafe_ask()
        selected_files = [pattern.strip() for pattern in custom_patterns.split(",")]

    if selected_files:
        update_gitignore(selected_files)
        console.print("[bold green]Updated .gitignore file with selected files/patterns.[/bold green]")
    else:
        console.print("[bold yellow]No files or patterns selected to ignore.[/bold yellow]")

def get_tracked_files() -> List[str]:
    import subprocess
    result = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    return result.stdout.splitlines()

def handle_push_repo() -> List[str]:
    import questionary

    remotes = get_git_remotes()
    if not remotes:
        console.print("[bold red]No remotes found. Please add a remote repository first.[/bold red]")
        return ["No remotes found."]

    selected_remotes = questionary.checkbox(
        "Select remote repositories to push to:",
        choices=[questionary.Choice(f"{name} ({url})", value=name) for name, url in remotes.items()]
    ).unsafe_ask()

    if not selected_remotes:
        console.print("[bold yellow]No remotes selected. Push aborted.[/bold yellow]")
        return ["No remotes selected."]

    confirmation_message = "Are you sure you want to push to the following remote(s):\n"
    for remote in selected_remotes:
        confirmation_message += f"- {remote} ({remotes[remote]})\n"

    confirm = questionary.confirm(confirmation_message).ask()
    if not confirm:
        console.print("[bold yellow]Push action canceled by the user.[/bold yellow]")
        return ["Push action canceled by the user."]

    status_messages = []
    for remote in selected_remotes:
        status_message = push_to_remote(remote, remotes[remote])
        if "Successfully" in status_message:
            console.print(f"[bold green]{status_message}[/bold green]")
        else:
            console.print(f"[bold red]{status_message}[/bold red]")
        status_messages.append(status_message)

    return status_messages

def parse_commit_log(log_output: str) -> List[Dict[str, Any]]:
    """
    Split 'git log' output into a structured list.
    """
    commits = [c for c in log_output.split("\n\n") if c.strip()]
    parsed_commits = []

    for commit in commits:
        lines = commit.split("\n")
        if len(lines) < 2:
            continue
        if " " in lines[0]:
            commit_hash, commit_message = lines[0].split(" ", 1)
            full_message = "\n".join(lines[1:]).strip()
            parsed_commits.append({
                "hash": commit_hash,
                "message": commit_message,
                "full_message": full_message
            })
        else:
            logger.warning(f"Skipping malformed commit line: {lines[0]}")

    return parsed_commits

def display_commit_summary(num_commits: int = 20) -> List[Dict[str, Any]]:
    """
    Show recent commits in a styled table.
    """
    import subprocess
    from rich.panel import Panel

    try:
        num_commits_arg = ["-n", str(num_commits)] if num_commits > 0 else []
        result = subprocess.run(["git", "log", "--pretty=format:%h %s%n%b"] + num_commits_arg,
                                stdout=subprocess.PIPE,
                                check=True)
        log_output = result.stdout.decode("utf-8")
        parsed_commits = parse_commit_log(log_output)

        table = create_styled_table("Recent Commits", clean=True)
        table.add_column("Hash", style="bold #6AD0FF")
        table.add_column("Message", style="#E6E6E6")

        for commit in parsed_commits:
            table.add_row(commit["hash"], commit["message"])

        console.print(Panel(table, style="", border_style="black", padding=(1, 2)))
        return parsed_commits
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get commit history: {e}")
        console.print(f"[bold red]Failed to get commit history: {e}[/bold red]")
        return []

def select_commit(commits: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Let user pick a commit from a displayed summary.
    """
    import questionary
    choices = [questionary.Choice(f"{c['hash']} {c['message']}", value=c) for c in commits]
    selected_commit = questionary.select(
        "Select a commit to view details:",
        choices=choices
    ).unsafe_ask()
    return selected_commit

def print_commit_details(commit: Dict[str, Any]):
    """
    Display the full commit message in a Rich panel.
    """
    from rich.markdown import Markdown
    from rich.panel import Panel
    commit_message_md = Markdown(commit['full_message'])
    console.print(Panel(
        commit_message_md,
        title=f"Commit {commit['hash']}",
        border_style="dark_khaki",
        style="white on rgb(39,40,34)"
    ))

def summarize_selected_commits():
    """
    Summarize user-selected commits from the last 30.
    """
    from rich.padding import Padding
    from rich.panel import Panel
    from rich.align import Align
    from rich.markdown import Markdown
    import questionary

    commits = display_commit_summary(30)
    if not commits:
        console.print("[bold yellow]No commits available to summarize.[/bold yellow]")
        return

    commit_choices = [
        questionary.Choice(f"{c['hash']} {c['message']}", value=c) for c in commits
    ]
    selected_commits = questionary.checkbox(
        "Select commits to summarize:",
        choices=commit_choices,
        style=configure_questionary_style(),
        instruction="(Use space to select, Enter to confirm)"
    ).unsafe_ask()

    if not selected_commits:
        console.print("[bold yellow]No commits selected for summarization.[/bold yellow]")
        return

    combined_messages = "\n\n---\n\n".join(
        f"{c['hash']} {c['message']}\n{c['full_message']}"
        for c in selected_commits
    )
    console.print(Panel(
        Markdown(combined_messages),
        title="Commit Messages",
        border_style="#0D1116",
        style="white on #0D1116"
    ))

    summary = generate_summary(combined_messages)
    if summary:
        console.print(
            Padding(Panel(
                Align.center(Padding(summary, (3, 7))),
                title="Summarized Commits",
                border_style="#ffffff",
                style="#ffffff on #0D1116"
            ), (3, 15))
        )
    else:
        console.print("[bold red]Failed to generate summary.[/bold red]")
