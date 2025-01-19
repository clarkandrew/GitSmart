import os
import re
import sys
import time
import threading
import questionary
from typing import List, Dict, Any, Tuple, Optional

from .config import logger, MODEL
from .ui import (
    console, printer, create_styled_table, configure_questionary_style
)
from .git_utils import (
    parse_diff, get_git_diff, get_file_diff, stage_files, unstage_files,
    run_git_command, get_repo_name, get_git_remotes, push_to_remote
)
from .ai_utils import (
    generate_commit_message, generate_summary, extract_tag_value
)

"""
This module manages the core flow of questionary-based interactions,
including status retrieval, staging/unstaging files, commit generation,
and more. The main() function in main.py calls these flows.
"""

def handle_files(changes: List[Dict[str, Any]], action: str) -> str:
    """
    Handle the staging or unstaging of files based on user selection.
    """
    if not changes:
        return f"No {action}d changes found."

    choices = [f"{change['file']} (+{change['additions']}/-{change['deletions']})" for change in changes]
    selected_files = questionary.checkbox(
        f"Select files to {action}:",
        choices=choices,
        style=configure_questionary_style()
    ).unsafe_ask()

    if selected_files:
        files = [file.split()[0] for file in selected_files]
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
    filename: str, diff_lines: List[str], file_changes: List[Dict[str, Any]], panel_width: int = 100
):
    """
    Display a diff panel for a single file, utilizing Rich syntax highlighting.
    """
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.padding import Padding
    from rich.align import Align

    if not diff_lines:
        diff_text = "No changes."
    else:
        diff_text = "\n".join(diff_lines)

    is_staged = any(change["file"] == filename for change in file_changes)
    border_style = "green" if is_staged else "bright_red"
    title = f"[bold blue]{filename}[/bold blue] [{'Staged' if is_staged else 'Unstaged'}]"
    syntax = Syntax(diff_text, "diff", theme="github-dark", line_numbers=True)

    changes = next((change for change in file_changes if change["file"] == filename), {})
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
            width=panel_width,
        ),
        (1, 2)
    )
    return Align.center(panel)

def display_file_diffs(
    diff: str, staged_file_changes: List[Dict[str, Any]], subtitle: str, panel_width: int = 100
):
    """
    Display the diff for each file in separate Rich panels for clarity.
    """
    from rich.console import Group
    from rich.panel import Panel
    import re

    file_pattern = re.compile(r"diff --git a/(.+?) b/(.+)")
    current_file = None
    current_diff = []
    panels = []

    for line in diff.splitlines():
        file_match = file_pattern.match(line)
        if file_match:
            if current_file:
                panel = display_diff_panel(current_file, current_diff, staged_file_changes, panel_width=panel_width)
                if panel:
                    panels.append(panel)
            current_file = file_match.group(2)
            current_diff = [line]
        else:
            current_diff.append(line)

    if current_file:
        panel = display_diff_panel(current_file, current_diff, staged_file_changes, panel_width=panel_width)
        if panel:
            panels.append(panel)

    if panels:
        summary_panel = get_diff_summary_panel(staged_file_changes, title="Staged Changes", subtitle=subtitle)
        grouped_panels = Group(*panels)
        console.print(grouped_panels)
    else:
        console.print("[bold yellow]No diffs to display.[/bold yellow]")

def get_diff_summary_panel(file_changes: List[Dict[str, Any]], title: str, subtitle: str,
                           panel_width: int = 100, _panel_style: str = "bold white on rgb(39,40,34)"):
    """
    Display file changes in a neat table (summary).
    """
    from rich.table import Table
    from rich.panel import Panel

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

    for change in file_changes:
        table.add_row(change["file"], f"+{change['additions']}", f"-{change['deletions']}")

    return table

def handle_generate_commit(diff: str, staged_changes: List[Dict[str, Any]]):
    """
    Handle the generation of a commit message and committing the changes via user prompts.
    """
    from rich.padding import Padding
    from rich.panel import Panel
    from rich.align import Align

    if not diff:
        console.print("[bold red]No staged changes found.[/bold red]")
        return

    display_file_diffs(diff, staged_changes, subtitle="Changes: Additions and Deletions")
    commit_message = generate_commit_message(diff)
    if commit_message:
        printer.print_divider()
        console.print(
            Padding(Panel(
                Align.center(Padding(commit_message, (3, 5))),
                title=f"Commit Generated by {MODEL if len(MODEL) < 30 else f'{MODEL}...'}",
                border_style="#ffffff",
                style="#ffffff on #0D1116"
            ), (3, 8))
        )
        printer.print_divider()

        action = questionary.select(
            "What would you like to do?",
            choices=["Commit Changes", "Edit Message", "Retry", "Cancel"],
            style=configure_questionary_style()
        ).ask()

        printer.print_divider()

        if action == "Commit Changes":
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

            # Show the updated commit in a styled panel just like the first time.
            # e.g.:
            console.print(
                Padding(Panel(
                    Align.center(Padding(edited_commit, (3,5))),
                    title="Edited Commit Message",
                    border_style="#ffffff",
                    style="#ffffff on #0D1116"
                ), (3,8))
            )

            # Now ask to confirm or commit the newly edited message:
            confirm_edit = questionary.select(
                "Use this edited commit message?",
                choices=["Commit", "Retry", "Cancel"],
                style=configure_questionary_style()
            ).ask()
        elif action == "Retry":
            logger.info("Retrying commit message generation.")
            handle_generate_commit(diff, staged_changes)
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
    Handle the review of changes by letting users select specific files to view diffs.
    """
    import questionary

    staged_files = set(change["file"] for change in staged_changes)
    unstaged_files = set(change["file"] for change in unstaged_changes)
    all_files = staged_files.union(unstaged_files)

    if not all_files:
        console.print("[bold yellow]No changes to review.[/bold yellow]")
        return

    choices = [
        questionary.Choice(
            title=f"{file} [Staged]" if file in staged_files else file,
            value=file,
            checked=file in staged_files
        )
        for file in sorted(all_files)
    ]
    selected_files = questionary.checkbox(
        "Select files to review their diffs:",
        choices=choices,
        style=configure_questionary_style(),
        instruction="(Use space to select, enter to confirm)"
    ).unsafe_ask()

    if not selected_files:
        console.print("[bold yellow]No files selected for review.[/bold yellow]")
        return

    for file in selected_files:
        is_staged = file in staged_files
        file_diff = get_file_diff(file, staged=is_staged)
        if file_diff:
            _panel = display_diff_panel(file, file_diff, staged_changes + unstaged_changes, panel_width=100)
            console.print(_panel)
        else:
            console.print(f"[bold red]No diff available for {file}.[/bold red]")

def get_diff_summary_table(file_changes: List[Dict[str, Any]], color: str):
    """
    Create a table summarizing file changes, used by display_status.
    """
    from rich.table import Table
    from rich.padding import Padding

    table = Table(show_header=False, show_lines=True, box=None, padding=(0, 0))
    table.add_column("File", justify="left", style="bold white", no_wrap=True)
    table.add_column("Additions", justify="right", style="green")
    table.add_column("Deletions", justify="right", style="red")

    for change in file_changes:
        max_file_name_len = 20
        display_file_name = change["file"]
        if len(display_file_name) > max_file_name_len:
            display_file_name = f"{display_file_name[0:max_file_name_len]}..."
        table.add_row(
            Padding(change["file"], (0, 2)),
            Padding(f"+{str(change['additions'])}", (0, 2)),
            Padding(f"-{str(change['deletions'])}", (0, 2))
        )
    return table

def display_status(
    unstaged_changes: List[Dict[str, Any]],
    staged_changes: List[Dict[str, Any]],
    staged: bool = True,
    unstaged: bool = False
):
    """
    Display the status of unstaged and staged changes in separate panels.
    """
    from rich.panel import Panel

    panel_width = 50
    if unstaged:
        unstaged_table = get_diff_summary_table(unstaged_changes, "red")
        unstaged_panel = Panel(
            unstaged_table,
            title_align="left",
            title="[bold white on red]Unstaged Changes[/]",
            border_style="red",
            width=50,
            expand=True
        )
        console.print(unstaged_panel)

    if staged:
        staged_table = get_diff_summary_table(staged_changes, "green")
        staged_panel = Panel(
            staged_table,
            title_align="left",
            title="[bold black on green]Staged Changes[/]",
            border_style="green",
            width=50,
            expand=True
        )
        console.print(staged_panel)

def get_status() -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Return diffs and parsed changes for both staged and unstaged changes.
    """
    diff = get_git_diff(staged=True)
    unstaged_diff = get_git_diff(staged=False)
    staged_changes = parse_diff(diff)
    unstaged_changes = parse_diff(unstaged_diff)
    return diff, unstaged_diff, staged_changes, unstaged_changes

def get_and_display_status():
    diff, unstaged_diff, staged_changes, unstaged_changes = get_status()
    display_status(
        unstaged_changes, staged_changes,
        staged=bool(staged_changes),
        unstaged=bool(unstaged_changes)
    )
    return diff, unstaged_diff, staged_changes, unstaged_changes

def select_model():
    """
    Allows user to specify a model name from the CLI, storing it in global MODEL.
    """
    from prompt_toolkit.history import FileHistory
    import questionary

    history_dir = ".C0MMIT"
    if os.path.exists(history_dir) and not os.path.isdir(history_dir):
        raise FileExistsError(f"A file named '{history_dir}' already exists. Please remove or rename it.")
    os.makedirs(history_dir, exist_ok=True)
    history_file = os.path.join(history_dir, "model_selection")

    global MODEL
    MODEL = questionary.text("Select a model:\n", history=FileHistory(history_file)).ask()
    return MODEL

def reset_console():
    """
    Clears the console by calling Rich's clear method, plus extra newlines for cross-platform safety.
    """
    console.clear()
    print("\n" * 25)

def load_gitignore() -> List[str]:
    """
    Load .gitignore and return lines from the managed section if present.
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
def get_menu_options(staged_changes: List[Dict[str, Any]], unstaged_changes: List[Dict[str, Any]]) -> Tuple[str, str, List[str]]:
    """
    Determine the appropriate menu title and options based on the current repository state.
    """
    num_staged_files = len(staged_changes)
    base_choices = ["Ignore Files", "View Commit History", "Push Repo", "Summarize Commits", "Exit"]
    choices = []
    title = "Select an action:"
    repo_status = "[green]✔[/] [bold black on green] All changes are up to date[/]\n"
    if staged_changes and unstaged_changes:
        repo_status = "[#FFF781]⚠[/] [bold black on yellow] Staged and unstaged changes found[/]\n"
        choices = [f"Generate Commit for Staged Changes ({num_staged_files})", "Stage Files", "Unstage Files", "Review Changes", "Select Model"]
    elif staged_changes:
        repo_status = "[blue]➤[/] [bold white on blue] Staged changes found[/]\n"
        choices = [f"Generate Commit for Staged Changes ({num_staged_files})", "Unstage Files", "Review Changes", "Select Model"]
    elif unstaged_changes:
        repo_status = "[yellow]✗[/] [italic #FFF781] Unstaged changes found[/]\n"
        choices = ["Stage Files", "Review Changes", "Select Model"]
    choices.extend(base_choices)
    return title, repo_status, choices
def save_gitignore_section(ignored_files: List[str]):
    """
    Save the list of ignored files to a specific managed section in .gitignore.
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
        # Remove existing managed section
        content = re.sub(r"# >>> Managed by GitSmart >>>\n.*?# <<< Managed by GitSmart <<<\n", "", content, flags=re.DOTALL)
        content = content.strip() + "\n\n" + managed_section
    else:
        content = managed_section

    with open(gitignore_path, "w") as f:
        f.write(content)

def update_gitignore(selected_files: List[str]):
    """
    Update the .gitignore file by adding selected files or patterns.
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
    Allows the user to select files from the repo or enter custom patterns to ignore.
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
    """
    Get a list of all tracked files in the repo using 'git ls-files'.
    """
    import subprocess
    result = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    return result.stdout.splitlines()

def handle_push_repo() -> List[str]:
    """
    Handle pushing commits to remote repositories.
    """
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
    Parse the git log output into a list of commit details.
    """
    commits = [commit for commit in log_output.split("\n\n") if commit.strip()]
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
    Display the commit summary with the specified number of commits.
    """
    import subprocess
    from rich.panel import Panel

    try:
        num_commits_arg = ["-n", str(num_commits)] if num_commits > 0 else []
        result = subprocess.run(["git", "log", "--pretty=format:%h %s%n%b"] + num_commits_arg,
                                stdout=subprocess.PIPE, check=True)
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
    Allow the user to select a commit from a displayed summary.
    """
    import questionary
    choices = [questionary.Choice(f"{commit['hash']} {commit['message']}", value=commit) for commit in commits]
    selected_commit = questionary.select("Select a commit to view details:", choices=choices).unsafe_ask()
    return selected_commit

def print_commit_details(commit: Dict[str, Any]):
    """
    Print the full details of a selected commit.
    """
    from rich.markdown import Markdown
    from rich.panel import Panel

    commit_message_md = Markdown(commit['full_message'])
    console.print(Panel(commit_message_md,
                        title=f"Commit {commit['hash']}",
                        border_style="dark_khaki",
                        style="white on rgb(39,40,34)"))

def summarize_selected_commits():
    """
    Summarize selected commit messages from the last 30 commits using AI.
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

    commit_choices = [questionary.Choice(f"{commit['hash']} {commit['message']}", value=commit) for commit in commits]
    selected_commits = questionary.checkbox(
        "Select commits to summarize:",
        choices=commit_choices,
        style=configure_questionary_style(),
        instruction="(Use space to select, enter to confirm)"
    ).unsafe_ask()

    if not selected_commits:
        console.print("[bold yellow]No commits selected for summarization.[/bold yellow]")
        return

    combined_messages = "\n\n---\n\n".join(
        f"{commit['hash']} {commit['message']}\n{commit['full_message']}" for commit in selected_commits
    )
    console.print(
        Panel(Markdown(combined_messages),
              title="Commit Messages", border_style="#0D1116", style="white on #0D1116")
    )

    summary = generate_summary(combined_messages)
    if summary:
        console.print(
            Padding(Panel(
                Align.center(Padding(summary, (3, 7))),
                title=f"Summarized Commits",
                border_style="#ffffff",
                style="#ffffff on #0D1116"
            ), (3, 15))
        )
    else:
        console.print("[bold red]Failed to generate summary.[/bold red]")
