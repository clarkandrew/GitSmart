# GitSmart/cli_flow.py

import os
import re
import sys
import time
import threading
import questionary
from questionary import Style
from typing import List, Dict, Any, Tuple, Optional
# Git-themed questionary style
fancy_questionary_style = Style([
    ('qmark', 'fg:#a259ff bold'),        # GitHub purple
    ('question', 'bold #a259ff'),        # GitHub purple
    ('answer', 'fg:#2ECC40 bold'),       # Green for confirmed answer
    ('pointer', 'fg:#a259ff bold'),      # GitHub purple pointer
    ('highlighted', 'fg:#2D2D2D bg:#F8E16C bold'),  # Highlighted choice: dark text on yellow
    ('selected', 'fg:#2D2D2D bg:#F8E16C bold'), # Selected item: dark text on yellow (like staged)
    ('separator', 'fg:#F8E16C'),         # Separator: yellow (like staged)
    ('instruction', 'italic #6A737D'),   # Instructions: gray
    ('text', 'bold #E0E0E0'),            # Chain name: light gray
    ('version', 'bold #F8E16C'),         # Version: yellow
    ('description', '#A9A9A9 italic'),   # Description: dark gray
    ('disabled', 'fg:#A9A9A9 italic'),   # Disabled: dark gray italic
    ('note', 'fg:#96DF71'),              # Note: green
    ('addition', 'fg:#2ECC40 bold'),     # Additions: green and bold
    ('deletion', 'fg:#FF4136 bold'),     # Deletions: red and bold
    ('file', 'bold #E0E0E0'),            # File name: light gray bold
    ("parenthesis", "#A9A9A9"),           # Parentheses: dark gray
    ("count", "bold")                     # For bold file counts in menus
])

from .config import logger, MODEL_CACHE, MODEL, DEFAULT_MODEL, DEBUG
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
    get_current_branch,
    get_all_branches,
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

import re

class MenuNavigationException(Exception):
    """Raised when user wants to navigate back from a submenu (e.g., Ctrl-C)."""
    pass

def main_menu_prompt(MODEL: str, title: str, choices: list) -> str:
    """
    Enhanced UI prompt for the main menu with questionary + custom style.
    Uses Git-themed colors and highlights 'Generate Commit' if staged changes exist.
    Always shows "Generate Commit" first when available, with colored additions and deletions.
    Additions are consistently shown in green (+) and deletions in red (-) for better visibility.
    """
    # Check for staged changes to highlight 'Generate Commit'
    _, _, staged_changes, unstaged_changes = get_status()
    styled_choices = []
    commit_option = None
    default_choice = None

    # First identify and separate out the Generate Commit option
    for i, c in enumerate(choices):
        if isinstance(c, str) and ("Generate Commit" in c or "Generate Commit for Staged Changes" in c):
            commit_option = c
            break

    # Add the generate commit option first if it exists
    if commit_option and staged_changes:
        styled_choices.append(
            questionary.Choice(
                title=f"🌟 {commit_option}", # Style will be handled by 'highlighted' in fancy_questionary_style
                value=commit_option
            )
        )
        default_choice = commit_option

    # Then process all other options
    for c in choices:
        # Skip the Generate Commit option since we already handled it
        if isinstance(c, str) and ("Generate Commit" in c or "Generate Commit for Staged Changes" in c):
            # Already handled above
            continue

        # Regex to parse "↓ Unstage Files (2) (+226, -59)"
        # Format: Arrow ActionText (Count) (+Additions, -Deletions)
        menu_item_match = re.match(r"^(↑|↓) (Unstage Files|Stage Files) \((\d+)\) \(\+(\d+), -(\d+)\)$", c)

        if menu_item_match:
            arrow, action_base, count_val, additions_val, deletions_val = menu_item_match.groups()

            styled_choices.append(
                questionary.Choice(
                    title=[
                        ("", f"{arrow} {action_base} "),       # e.g., "↓ Unstage Files "
                        ("class:parenthesis", "("),
                        ("class:count", count_val),            # e.g., "2" (bold)
                        ("class:parenthesis", ") "),           # ") "
                        ("class:parenthesis", "("),
                        ("class:addition", f"+{additions_val}"),
                        ("class:parenthesis", ", "),
                        ("class:deletion", f"-{deletions_val}"),
                        ("class:parenthesis", ")")
                    ],
                    value=c # The original string value is used for action dispatching
                )
            )
        else: # Corresponds to other menu items or if regex doesn't match
            styled_choices.append(c)

    return questionary.select(
        title,
        choices=styled_choices,
        style=fancy_questionary_style,
        instruction="(Use ↑/↓ to move, Enter to select)",
        default=default_choice
    ).unsafe_ask(patch_stdout=True)

def get_menu_options(
    MODEL: str,
    staged_changes: List[Dict[str, Any]],
    unstaged_changes: List[Dict[str, Any]]
) -> Tuple[str, str, List[str]]:
    """
    Compute dynamic menu items based on presence of staged/unstaged changes.
    Returns a tuple of (title, status message with rich formatting, menu choices).
    Includes total additions/deletions in the status message.

    Enhanced so that when there are no changes at all (staged or unstaged),
    it omits "Stage Files", "Unstage Files", and "Review Changes" from the menu.
    Always puts "Generate Commit" first when staged changes exist.
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

    # Always put Generate Commit first if we have staged changes
    if has_staged:
        staged_additions = sum(ch["additions"] for ch in staged_changes)
        staged_deletions = sum(ch["deletions"] for ch in staged_changes)
        dynamic_choices.append(f"Generate Commit for Staged Changes ({len(staged_changes)})")
        dynamic_choices.append(f"↓ Unstage Files ({len(staged_changes)}) (+{staged_additions}, -{staged_deletions})")

    # Next, show Stage Files with additions/deletions count if we have unstaged changes
    if has_unstaged:
        unstaged_additions = sum(ch["additions"] for ch in unstaged_changes)
        unstaged_deletions = sum(ch["deletions"] for ch in unstaged_changes)
        dynamic_choices.append(f"↑ Stage Files ({len(unstaged_changes)}) (+{unstaged_additions}, -{unstaged_deletions})")

    # Finally, add Review Changes if we have any changes
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

    # Display totals in the status message with consistent styling
    repo_status += f"\n[bold white]{repo_name} ({MODEL})[/bold white] [dim]([/dim][bold bright_green]+{total_additions}[/bold bright_green][dim], [/dim][bold bright_red]-{total_deletions}[/bold bright_red][dim])[/dim]"

    title = "Select an action:"
    # Combine any dynamic choices with the always-available base ones
    choices = dynamic_choices + base_choices

    return title, repo_status, choices

def handle_files(changes: List[Dict[str, Any]], action: str) -> str:
    """
    Let the user pick files to stage or unstage from a checkbox list.
    Shows file names with colored additions (green) and deletions (red).
    """
    if not changes:
        return f"No {action}d changes found."

    choices = []
    for c in changes:
        choice = questionary.Choice(
            title=[
                ("class:file", f"{c['file']} "),
                ("class:parenthesis", "("),
                ("class:addition", f"+{c['additions']}"),
                ("class:parenthesis", ", "),
                ("class:deletion", f"-{c['deletions']}"),
                ("class:parenthesis", ")")
            ],
            value=c['file']
        )
        choices.append(choice)

    try:
        selected_files = questionary.checkbox(
            f"Select files to {action}:",
            choices=choices,
            style=fancy_questionary_style # Use fancy_questionary_style for consistency
        ).unsafe_ask()
    except KeyboardInterrupt:
        # User pressed Ctrl-C in submenu, navigate back to main menu
        raise MenuNavigationException(f"Cancelled {action} operation")

    if selected_files:
        files = selected_files
        if action == "stage":
            result = stage_files(files)
        else:
            result = unstage_files(files)
        if "Error" in result:
            if DEBUG:
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
    footer = f"[dim]([/dim][bold bright_green]+{additions}[/][dim], [/dim][bold bright_red]-{deletions}[/][dim])[/dim]"

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
    table.add_column("Additions", justify="right", style="bold bright_green")
    table.add_column("Deletions", justify="right", style="bold bright_red")

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

    # Prompt for custom notes
    try:
        add_notes = questionary.text(
            "Add custom notes to guide the commit message? (y/n, Enter to skip):",
            style=configure_questionary_style()
        ).unsafe_ask(patch_stdout=True)

        custom_notes = None
        if add_notes and add_notes.strip().lower() == "y":
            notes = questionary.text(
                "Enter your custom notes (Markdown supported):",
                multiline=True,
                style=configure_questionary_style()
            ).unsafe_ask(patch_stdout=True)
            if notes:
                # Escape triple backticks
                notes = notes.replace("```", "\\`\\`\\`")
                custom_notes = notes
    except KeyboardInterrupt:
        console.print("[bold yellow]⚠️  Cancelled commit generation[/bold yellow]")
        raise MenuNavigationException("User cancelled commit generation")
    except Exception as e:
        # Handle RefreshMenuException and other interruptions during commit generation
        if "RefreshMenuException" in str(type(e)):
            console.print("[bold yellow]⚠️  Auto-refresh disabled during commit generation[/bold yellow]")
            # Continue with empty notes
            custom_notes = None
        else:
            console.print(f"[bold yellow]⚠️  Input error: {e}[/bold yellow]")
            custom_notes = None

    try:
        commit_message = generate_commit_message(MODEL, diff, custom_notes=custom_notes)
    except KeyboardInterrupt:
        console.print("[bold yellow]⚠️  Cancelled commit generation[/bold yellow]")
        raise MenuNavigationException("User cancelled commit generation")

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

        try:
            action = questionary.select(
                "What would you like to do?",
                choices=["Commit", "Edit commit message", "Retry", "Cancel"],
                style=configure_questionary_style()
            ).unsafe_ask(patch_stdout=True)
        except KeyboardInterrupt:
            console.print("[bold yellow]⚠️  Cancelled commit action[/bold yellow]")
            raise MenuNavigationException("User cancelled commit action")
        except Exception as e:
            # Handle RefreshMenuException and other interruptions during commit generation
            if "RefreshMenuException" in str(type(e)):
                console.print("[bold yellow]⚠️  Auto-refresh disabled during commit generation[/bold yellow]")
                action = "Cancel"  # Default to cancel if interrupted
            else:
                console.print(f"[bold yellow]⚠️  Selection error: {e}[/bold yellow]")
                action = "Cancel"

        printer.print_divider()

        if action == "Commit":
            commit_status = run_git_command(["git", "commit", "-m", commit_message])
            if "Success" in commit_status:
                return commit_status
            else:
                console.print(f"[bold red]{commit_status}[/bold red]")

        elif action == "Edit commit message":
            try:
                edited_commit = questionary.text(
                    "Edit your commit message below:",
                    multiline=True,
                    default=commit_message,
                    style=configure_questionary_style()
                ).unsafe_ask(patch_stdout=True)
            except KeyboardInterrupt:
                console.print("[bold yellow]⚠️  Cancelled commit edit[/bold yellow]")
                raise MenuNavigationException("User cancelled commit edit")
            except Exception as e:
                # Handle RefreshMenuException and other interruptions during commit generation
                if "RefreshMenuException" in str(type(e)):
                    console.print("[bold yellow]⚠️  Auto-refresh disabled during commit generation[/bold yellow]")
                    edited_commit = commit_message  # Use original commit message
                else:
                    console.print(f"[bold yellow]⚠️  Edit error: {e}[/bold yellow]")
                    edited_commit = commit_message

            # Show updated commit
            console.print(
                Padding(Panel(
                    Align.center(Padding(edited_commit, (3, 5))),
                    title="Edited Commit Message",
                    border_style="#ffffff",
                    style="#ffffff on #0D1116"
                ), (3, 8))
            )

            try:
                confirm_edit = questionary.select(
                    "Use this edited commit message?",
                    choices=["Commit", "Retry", "Cancel"],
                    style=configure_questionary_style()
                ).unsafe_ask(patch_stdout=True)
            except KeyboardInterrupt:
                console.print("[bold yellow]⚠️  Cancelled commit confirmation[/bold yellow]")
                raise MenuNavigationException("User cancelled commit confirmation")
            except Exception as e:
                # Handle RefreshMenuException and other interruptions during commit generation
                if "RefreshMenuException" in str(type(e)):
                    console.print("[bold yellow]⚠️  Auto-refresh disabled during commit generation[/bold yellow]")
                    confirm_edit = "Cancel"  # Default to cancel if interrupted
                else:
                    console.print(f"[bold yellow]⚠️  Confirmation error: {e}[/bold yellow]")
                    confirm_edit = "Cancel"

            if confirm_edit == "Commit":
                commit_status = run_git_command(["git", "commit", "-m", edited_commit])
                return commit_status
            elif confirm_edit == "Retry":
                if DEBUG:
                    logger.debug("Retrying commit message generation.")
                return handle_generate_commit(MODEL, diff, staged_changes)
            else:
                if DEBUG:
                    logger.debug("Commit aborted by user.")
                console.print("[bold yellow]Commit aborted by user.[/bold yellow]")

        elif action == "Retry":
            if DEBUG:
                logger.debug("Retrying commit message generation.")
            return handle_generate_commit(MODEL, diff, staged_changes)

        else:
            if DEBUG:
                logger.debug("Commit aborted by user.")
            console.print("[bold yellow]Commit aborted by user.[/bold yellow]")
    else:
        if DEBUG:
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
    Shows files with colored additions and deletions statistics.
    """
    import questionary

    staged_files = {ch["file"] for ch in staged_changes}
    unstaged_files = {ch["file"] for ch in unstaged_changes}
    all_files = staged_files.union(unstaged_files)

    if not all_files:
        console.print("[bold yellow]No changes to review.[/bold yellow]")
        return

    # Create a dict to lookup file stats
    file_stats = {}
    for ch in staged_changes + unstaged_changes:
        file_stats[ch["file"]] = (ch["additions"], ch["deletions"])

    choices = []
    for file in sorted(all_files):
        additions, deletions = file_stats.get(file, (0, 0))
        is_staged = file in staged_files

        title_parts = [
            ("class:file", f"{file}"),
            ("", " [Staged] " if is_staged else " "),
            ("class:parenthesis", "("),
            ("class:addition", f"+{additions}"),
            ("class:parenthesis", ", "),
            ("class:deletion", f"-{deletions}"),
            ("class:parenthesis", ")")
        ]

        choices.append(questionary.Choice(
            title=title_parts,
            value=file,
            checked=is_staged
        ))

    try:
        selected_files = questionary.checkbox(
            "Select files to review their diffs:",
            choices=choices,
            style=fancy_questionary_style, # Use fancy_questionary_style for consistency
            instruction="(Use space to select, Enter to confirm)"
        ).unsafe_ask()
    except KeyboardInterrupt:
        console.print("[bold yellow]⚠️  Cancelled file review[/bold yellow]")
        raise MenuNavigationException("User cancelled file review")

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
            Padding("[dim]([/dim][bright_green]+0[/][dim])[/dim]", (0, 2)),
            Padding("[dim]([/dim][bright_red]-0[/][dim])[/dim]", (0, 2))
        )
        return table

    for ch in file_changes:
        table.add_row(
            Padding(ch["file"], (0, 2)),
            Padding(f"[dim]([/dim][bright_green]+{ch['additions']}[/][dim])[/dim]", (0, 2)),
            Padding(f"[dim]([/dim][bright_red]-{ch['deletions']}[/][dim])[/dim]", (0, 2))
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
    Display unstaged changes first, then staged changes.
    """
    from rich.panel import Panel
    from rich.padding import Padding

    # Unstaged Panel - always show first
    if unstaged:
        if unstaged_changes:
            unstaged_additions = sum(ch["additions"] for ch in unstaged_changes)
            unstaged_deletions = sum(ch["deletions"] for ch in unstaged_changes)
            unstaged_table = get_diff_summary_table(unstaged_changes, "red")
            unstaged_panel = Panel(
                Padding(unstaged_table,(1,2)),
                title_align="left",
                title=f"[bold white on red]Unstaged Changes [dim]([/dim][bold white]+{unstaged_additions}[/bold white][dim], [/dim][bold white]-{unstaged_deletions}[/bold white][dim])[/dim][/]",
                border_style="red",
                width=50,
                expand=True
            )
            console.print(unstaged_panel)
        else:
            console.print("[dim]No unstaged changes[/dim]")

    # Staged Panel - show after unstaged
    if staged and staged_changes:
        staged_additions = sum(ch["additions"] for ch in staged_changes)
        staged_deletions = sum(ch["deletions"] for ch in staged_changes)
        staged_table = get_diff_summary_table(staged_changes, "green")
        staged_panel = Panel(
            Padding(staged_table,(1,2)),
            title_align="left",
            title=f"[bold black on green]Staged Changes [dim]([/dim][bold white]+{staged_additions}[/bold white][dim], [/dim][bold white]-{staged_deletions}[/bold white][dim])[/dim][/]",
            border_style="green",
            width=50,
            expand=True
        )
        console.print(staged_panel)
    elif staged:
        console.print("[dim]No staged changes[/dim]")

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
    """
    Prompts the user to select an AI model and saves the selection to cache.
    The selected model persists between application restarts.

    Returns:
        str: The selected model name
    """
    from prompt_toolkit.history import FileHistory
    import questionary

    # Set up history directory for command history
    history_dir = ".gitsmart"
    if os.path.exists(history_dir) and not os.path.isdir(history_dir):
        raise FileExistsError(f"A file named '{history_dir}' already exists.")
    os.makedirs(history_dir, exist_ok=True)
    history_file = os.path.join(history_dir, "model_selection")

    global MODEL



    # Prompt user for model selection with current model as default
    try:
        selected_model = questionary.text(
            "Select a model:\n",
            history=FileHistory(history_file),
            default=DEFAULT_MODEL
        ).ask()
    except KeyboardInterrupt:
        console.print("[bold yellow]⚠️  Cancelled model selection[/bold yellow]")
        raise MenuNavigationException("User cancelled model selection")

    if selected_model:
        MODEL = selected_model
        # Save the selected model to cache for persistence
        MODEL_CACHE["last_model"] = MODEL

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
    Shows files with their file extension highlighted.
    """
    import questionary
    import os

    ignored_files = load_gitignore()
    all_files = get_tracked_files()

    choices = []
    for file in all_files:
        # Highlight file extensions differently
        filename, ext = os.path.splitext(file)
        if ext:
            title_parts = [
                ("class:file", filename),
                ("class:note", ext)
            ]
        else:
            title_parts = [("class:file", file)]

        choices.append(questionary.Choice(title=title_parts, value=file, checked=(file in ignored_files)))

    try:
        action = questionary.select(
            "Would you like to select files to ignore or enter custom patterns?",
            choices=["Select files", "Enter custom patterns"],
            style=configure_questionary_style()
        ).unsafe_ask()
    except KeyboardInterrupt:
        console.print("[bold yellow]⚠️  Cancelled ignore files operation[/bold yellow]")
        raise MenuNavigationException("User cancelled ignore files operation")

    if action == "Select files":
        try:
            selected_files = questionary.checkbox(
                "Select files to ignore:",
                choices=choices,
                style=configure_questionary_style()
            ).unsafe_ask()
        except KeyboardInterrupt:
            console.print("[bold yellow]⚠️  Cancelled file selection[/bold yellow]")
            raise MenuNavigationException("User cancelled file selection")
    else:
        try:
            custom_patterns = questionary.text(
                "Enter custom patterns to ignore (comma-separated):",
                style=configure_questionary_style()
            ).unsafe_ask()
            selected_files = [pattern.strip() for pattern in custom_patterns.split(",")]
        except KeyboardInterrupt:
            console.print("[bold yellow]⚠️  Cancelled custom pattern entry[/bold yellow]")
            raise MenuNavigationException("User cancelled custom pattern entry")

    if selected_files:
        update_gitignore(selected_files)
        console.print(f"[bold green]Successfully updated .gitignore with {len(selected_files)} entries.[/bold green]")
    else:
        console.print("[bold yellow]No files were selected. .gitignore was not updated.[/bold yellow]")

def get_tracked_files() -> List[str]:
    import subprocess
    result = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    return result.stdout.splitlines()

def handle_push_repo() -> List[str]:
    import questionary

    # Get remotes
    remotes = get_git_remotes()
    if not remotes:
        console.print("[bold red]No remotes found. Please add a remote repository first.[/bold red]")
        return ["No remotes found."]

    # Get current branch and all branches
    current_branch = get_current_branch()
    all_branches = get_all_branches()

    if not current_branch:
        console.print("[bold red]No current branch detected. Make sure you're in a git repository.[/bold red]")
        return ["No current branch detected."]

    # Prepare branch choices
    branch_choices = []

    # Add current branch as default choice
    branch_choices.append(questionary.Choice(f"{current_branch} (current)", value=current_branch, checked=True))

    # Add other local branches
    for branch in all_branches["local"]:
        if branch != current_branch:
            branch_choices.append(questionary.Choice(f"{branch} (local)", value=branch))

    # Add remote branches
    for branch in all_branches["remote"]:
        # Extract just the branch name from remote/branch format
        branch_name = branch.split('/')[-1] if '/' in branch else branch
        if branch_name not in [current_branch] + all_branches["local"]:
            branch_choices.append(questionary.Choice(f"{branch_name} (remote: {branch})", value=branch_name))

    # Select branch to push
    if len(branch_choices) > 1:
        selected_branch = questionary.select(
            "Select branch to push:",
            choices=branch_choices,
            style=configure_questionary_style()
        ).unsafe_ask()
    else:
        selected_branch = current_branch
        console.print(f"[bold blue]Using current branch: {current_branch}[/bold blue]")

    if not selected_branch:
        console.print("[bold yellow]No branch selected. Push aborted.[/bold yellow]")
        return ["No branch selected."]

    # Select remotes
    selected_remotes = questionary.checkbox(
        "Select remote repositories to push to:",
        choices=[questionary.Choice(f"{name} ({url})", value=name) for name, url in remotes.items()]
    ).unsafe_ask()

    if not selected_remotes:
        console.print("[bold yellow]No remotes selected. Push aborted.[/bold yellow]")
        return ["No remotes selected."]

    # Confirmation
    confirmation_message = f"Are you sure you want to push branch '{selected_branch}' to the following remote(s):\n"
    for remote in selected_remotes:
        confirmation_message += f"- {remote} ({remotes[remote]})\n"

    confirm = questionary.confirm(
        confirmation_message,
        style=configure_questionary_style()
    ).ask()
    if not confirm:
        console.print("[bold yellow]Push action canceled by the user.[/bold yellow]")
        return "Push action canceled by the user."

    # Execute push
    status_messages = []
    for remote in selected_remotes:
        status_message = push_to_remote(remote, remotes[remote], selected_branch)
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
            if DEBUG:
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
        console.print("\n")
        return parsed_commits
    except subprocess.CalledProcessError as e:
        if DEBUG:
            logger.error(f"Failed to get commit history: {e}")
        console.print(f"[bold red]Failed to get commit history: {e}[/bold red]")
        return []

def select_commit(commits: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Let user pick a commit from a displayed summary.
    Shows commit with hash, message, and colored additions/deletions.
    """
    import questionary

    choices = []
    for c in commits:
        # Get additions and deletions if available, default to 0
        additions = c.get("additions", 0)
        deletions = c.get("deletions", 0)

        if additions > 0 or deletions > 0:
            title_parts = [
                ("", f"{c['hash']} "),
                ("", f"{c['message']} "),
                ("class:parenthesis", "("),
                ("class:addition", f"+{additions}"),
                ("class:parenthesis", ", "),
                ("class:deletion", f"-{deletions}"),
                ("class:parenthesis", ")")
            ]
        else:
            title_parts = [
                ("", f"{c['hash']} "),
                ("", f"{c['message']}")
            ]

        choices.append(questionary.Choice(title=title_parts, value=c))

    try:
        selected_commit = questionary.select(
            "Select a commit to view details:",
            choices=choices,
            style=fancy_questionary_style # Use fancy_questionary_style for consistency
        ).unsafe_ask()
        return selected_commit
    except KeyboardInterrupt:
        console.print("[bold yellow]⚠️  Cancelled commit selection[/bold yellow]")
        raise MenuNavigationException("User cancelled commit selection")

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

    commit_choices = []
    for c in commits:
        # Get additions and deletions if available, default to 0
        additions = c.get("additions", 0)
        deletions = c.get("deletions", 0)

        if additions > 0 or deletions > 0:
            title_parts = [
                ("", f"{c['hash']} "),
                ("", f"{c['message']} "),
                ("class:parenthesis", "("),
                ("class:addition", f"+{additions}"),
                ("class:parenthesis", ", "),
                ("class:deletion", f"-{deletions}"),
                ("class:parenthesis", ")")
            ]
        else:
            title_parts = [
                ("", f"{c['hash']} "),
                ("", f"{c['message']}")
            ]

        commit_choices.append(questionary.Choice(title=title_parts, value=c))
    try:
        selected_commits = questionary.checkbox(
            "Select commits to summarize:",
            choices=commit_choices,
            style=fancy_questionary_style, # Use fancy_questionary_style for consistency
            instruction="(Use space to select, Enter to confirm)"
        ).unsafe_ask()
    except KeyboardInterrupt:
        console.print("[bold yellow]⚠️  Cancelled commit summarization[/bold yellow]")
        raise MenuNavigationException("User cancelled commit summarization")

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
