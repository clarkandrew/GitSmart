#!/usr/bin/env python3
import re
import subprocess
import requests
import json
from rich.console import Console, Group
from rich.syntax import Syntax
from rich.align import Align
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.text import Text
import questionary
import logging
from typing import List, Dict, Any, Tuple, Optional
from prompts import SYSTEM_MESSAGE, USER_MSG_APPENDIX

# Initialize logger and console for logging and output
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
console = Console()

# Constants for API interaction
AUTH_TOKEN = "Bearer sk-123"
API_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL = "notes|nemotron:latest|61-219-64-161|o"
MAX_TOKENS = 2000
TEMPERATURE = 0.75

# Theme configuration
THEME = {
    "primary": "#e5c07b",  # Soft blue
    "secondary": "#ffcb6b",  # Light blue
    "accent": "#8ea6c0",  # Warm yellow
    "success": "#98c379",  # Soft green
    "error": "#e06c75",  # Soft red
    "warning": "#e5c07b",  # Warm yellow
    "background": "#282c34",  # Dark background
    "text": "#abb2bf",  # Light gray text
}

# Style configurations
PANEL_STYLE = f"bold {THEME['text']} on {THEME['background']}"
BORDER_STYLE = THEME["accent"]
HEADER_STYLE = f"bold {THEME['primary']}"

class StyledCLIPrinter:
    def __init__(self, console: Console):
        self.console = console

    def print_message(self, message: str, style: str, title: Optional[str] = None):
        content = Text(message, style=style)
        if title:
            panel = Panel(content, title=title, border_style=BORDER_STYLE, style=PANEL_STYLE, padding=(1, 2))
            self.console.print(panel)
        else:
            self.console.print(content)

    def print_error(self, message: str, title: str = "Error"):
        self.print_message(message, f"bold {THEME['error']}", title)

    def print_warning(self, message: str, title: str = "Warning"):
        self.print_message(message, f"bold {THEME['warning']}", title)

    def print_success(self, message: str, title: str = "Success"):
        self.print_message(message, f"bold {THEME['success']}", title)

    def print_divider(self, title: str = ""):
        self.console.print()
        self.console.rule(title, style=BORDER_STYLE)
        self.console.print()

def create_styled_table(title: Optional[str] = None) -> Table:
    table = Table(show_header=False, header_style=HEADER_STYLE, border_style=None, show_lines=False, box=None, padding=(2, 2), title=title)
    return table

def create_styled_table_clean(title: Optional[str] = None) -> Table:
    table = Table(show_header=False, header_style=None, border_style=None, show_lines=False, box=None, padding=(1, 1), title=title, style=None,expand=True)
    return table

def extract_tag_value(text: str, tag: str) -> str:
    """
    Extracts the value enclosed within specified XML-like or bracket-like tags, case-insensitive.
    """
    try:
        tag_lower = tag.lower()
        patterns = [rf"<({tag_lower})>(.*?)</\1>", rf"\[({tag_lower})\](.*?)\[/\1\]"]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(2).strip()
        return ""
    except Exception as e:
        console.log(f"Could not extract `{tag}` because {str(e)}\n")
        return ""

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

def generate_commit_message(diff: str) -> str:
    """
    Generate a commit message using an external service.
    """
    logger.debug("Entering generate_commit_message function.")
    headers = {"Authorization": AUTH_TOKEN, "Content-Type": "application/json"}
    messages = [{"role": "system", "content": SYSTEM_MESSAGE}, {"role": "user", "content": diff + USER_MSG_APPENDIX}]
    body = {"model": MODEL, "messages": messages, "max_tokens": MAX_TOKENS, "n": 1, "stop": None, "temperature": TEMPERATURE, "stream": True}

    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            task = progress.add_task("Waiting for response...", start=False)
            progress.start_task(task)

            response = requests.post(API_URL, headers=headers, json=body, stream=True)
            response.raise_for_status()

            commit_message = ""
            first_chunk_received = False

            for chunk in response.iter_lines():
                if chunk:
                    chunk_data = chunk.decode("utf-8").strip()
                    if chunk_data.startswith("data: "):
                        chunk_data = chunk_data[6:]
                        try:
                            data = json.loads(chunk_data)
                            delta_content = data["choices"][0]["delta"].get("content", "")
                            commit_message += delta_content

                            if not first_chunk_received:
                                progress.stop()
                                first_chunk_received = True

                            console.print(delta_content, end="")
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to decode JSON chunk: {e}")
                            continue

            commit_message_text = extract_tag_value(commit_message, "COMMIT_MESSAGE")
            if not commit_message_text:
                raise ValueError("Could not extract tag")

            console.log("Commit message generated successfully.")
            return commit_message_text
    except Exception as e:
        logger.error(f"Failed to generate commit message: {e}")
        console.print(f"[bold red]Failed to generate commit message: {e}[/bold red]")
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

def display_diff_panel(filename: str, diff_lines: List[str], file_changes: List[Dict[str, Any]], panel_width: int = 100) -> Panel:
    """
    Display a diff panel for a single file.
    """
    diff_text = "\n".join(diff_lines)
    syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
    additions = next((change["additions"] for change in file_changes if change["file"] == filename), 0)
    deletions = next((change["deletions"] for change in file_changes if change["file"] == filename), 0)
    footer = f"Additions: +{additions}, Deletions: -{deletions}"
    diff_panel = Panel(syntax, title=f"[bold blue]{filename}[/bold blue]", border_style="dark_khaki", padding=(1, 2), subtitle=footer, width=panel_width)
    return diff_panel

def stage_files(files: List[str]):
    try:
        subprocess.run(["git", "add"] + files, check=True)
        console.print("[bold green]Files staged successfully.[/bold green]")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to stage files: {e}")
        console.print(f"[bold red]Failed to stage files: {e}[/bold red]")

def unstage_files(files: List[str]):
    try:
        subprocess.run(["git", "reset"] + files, check=True)
        console.print("[bold green]Files unstaged successfully.[/bold green]")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to unstage files: {e}")
        console.print(f"[bold red]Failed to unstage files: {e}[/bold red]")

def get_diff_summary_panel(file_changes: List[Dict[str, Any]], title: str, subtitle: str, panel_width: int = 100, _panel_style: str = "bold white on rgb(39,40,34)") -> Panel:
    """
    Display the staged changes in a neat panel.
    """
    table = Table(show_header=True, header_style="bold magenta", show_lines=False, box=None)
    table.add_column("File", justify="left", style="cyan", no_wrap=True)
    table.add_column("Additions", justify="right", style="green")
    table.add_column("Deletions", justify="right", style="red")

    for change in file_changes:
        table.add_row(change["file"], f"+{str(change['additions'])}", f"-{str(change['deletions'])}")

    aligned_table = Align.center(table)
    panel = Panel(aligned_table, title=f"[bold {THEME['text']}]{title}[/bold {THEME['text']}]", border_style=BORDER_STYLE, style=_panel_style, padding=(1, 2), expand=True, width=panel_width)

    return Align.center(panel, vertical="middle")

def display_file_diffs(diff: str, staged_file_changes: List[Dict[str, Any]], subtitle: str, panel_width: int = 100):
    """
    Display the diff for each file in a separate panel.
    """
    file_pattern = re.compile(r"diff --git a/(.+?) b/(.+)")
    current_file = None
    current_diff = []
    panels = []

    for line in diff.splitlines():
        file_match = file_pattern.match(line)
        if file_match:
            if current_file:
                panels.append(display_diff_panel(current_file, current_diff, staged_file_changes, panel_width=panel_width))
            current_file = file_match.group(2)
            current_diff = [line]
        else:
            current_diff.append(line)

    if current_file:
        panels.append(display_diff_panel(current_file, current_diff, staged_file_changes, panel_width=panel_width))
    summary_panel = get_diff_summary_panel(staged_file_changes, title="Staged Changes", subtitle=subtitle)

    panels += [Text("\n"), Rule(style="bold dark_khaki"), Text("\n")]
    panels.append(summary_panel)
    grouped_panels = Group(*panels)

    panel = Panel(grouped_panels, title="[bold white]File Diffs[/bold white]", border_style="dark_khaki", style="white on rgb(39,40,34)", padding=(2, 4), expand=True)

    console.print(Align.left(panel, vertical="middle"))

def display_commit_history(num_commits=5):
    try:
        result = subprocess.run(["git", "log", "--pretty=format:%h %s", "--stat", f"-n", str(num_commits)], stdout=subprocess.PIPE, check=True)
        log_output = result.stdout.decode("utf-8")
        commits = [commit for commit in log_output.split("\n\n") if commit.strip()]

        table = create_styled_table_clean("Recent Commits")
        table.add_column("Hash", style=f"bold {THEME['secondary']}")
        table.add_column("Message", style=THEME["text"])
        table.add_column("Additions", style=THEME["success"])
        table.add_column("Deletions", style=THEME["error"])

        for commit in commits:
            lines = commit.split("\n")
            if len(lines) < 2:
                continue

            commit_hash, commit_message = lines[0].split(" ", 1)
            commit_message = Text(commit_message, style="bold")

            additions = deletions = 0
            for line in lines[1:]:
                if "files changed" in line:
                    parts = line.split(", ")
                    for part in parts:
                        if "insertion" in part:
                            additions = int(part.split()[0])
                        elif "deletion" in part:
                            deletions = int(part.split()[0])

            table.add_row(commit_hash, commit_message, f"+{additions}", f"-{deletions}")

        console.print(Panel(table, style="", border_style=BORDER_STYLE, padding=(1, 2)))

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get commit history: {e}")
        console.print(f"[bold {THEME['error']}]Failed to get commit history: {e}[/bold {THEME['error']}]")

def configure_questionary_style():
    return questionary.Style(
        [
            ("qmark", f'fg:{THEME["accent"]} bold'),
            ("question", f'fg:{THEME["primary"]} bold'),
            ("answer", f'fg:{THEME["success"]} bold'),
            ("pointer", f'fg:{THEME["accent"]} bold'),
            ("highlighted", f'fg:{THEME["accent"]} bold'),
            ("selected", f'fg:{THEME["success"]} bold'),
            ("separator", f'fg:{THEME["secondary"]}'),
            ("instruction", f'fg:{THEME["text"]}'),
        ]
    )

class CLIPrinter:
    def __init__(self, console: Console):
        self.console = console

    def print_panel(self, message: str, title: str, style: str):
        panel = Panel(Text(message, style=f"bold {style}"), title=title, border_style=style)
        self.console.print(panel)

    def print_divider(self):
        self.console.print("\n")
        self.console.rule(style="dark_khaki")
        self.console.print("\n")

def display_status(unstaged_changes: List[Dict[str, Any]], staged_changes: List[Dict[str, Any]]):
    """
    Display the status of unstaged and staged changes.
    """
    subtitle = "Changes: Additions and Deletions"
    unstaged_panel = get_diff_summary_panel(unstaged_changes, "Unstaged Changes", subtitle, _panel_style="")
    staged_panel = get_diff_summary_panel(staged_changes, "Staged Changes", subtitle, _panel_style="")

    console.print(unstaged_panel)
    console.print(staged_panel)

def display_and_get_status() -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Display the status of unstaged and staged changes and return the diffs and changes.
    """
    diff = get_git_diff(staged=True)
    unstaged_diff = get_git_diff(staged=False)
    staged_changes = parse_diff(diff)
    unstaged_changes = parse_diff(unstaged_diff)

    display_status(unstaged_changes, staged_changes)

    return diff, unstaged_diff, staged_changes, unstaged_changes

from rich.markdown import Markdown
def main():
    """
    Main function to generate and commit a message based on staged changes.
    """

    console.print(Markdown("# c-01"))
    display_commit_history()
    printer = CLIPrinter(console)
    questionary_style = configure_questionary_style()

    logger.debug("Entering main function.")
    diff, unstaged_diff, staged_changes, unstaged_changes = display_and_get_status()

    while True:
        try:
            printer.print_divider()

            # Dynamically generate the list of choices based on the presence of staged changes
            choices = ["Generate commit for staged files"]
            if staged_changes:
                choices.extend(["Review Staged Changes", "Unstage Files"])
            choices.extend(["Stage Files", "History", "Exit"])

            action = questionary.select(
                "What would you like to do?",
                choices=choices,
                style=questionary_style
            ).unsafe_ask()

            if action == "Generate commit for staged files":
                if not diff:
                    console.print("[bold red]No staged changes detected.[/bold red]")
                    continue

                commit_message = generate_commit_message(diff)
                if commit_message:
                    printer.print_divider()
                    console.print(Panel(commit_message, title="Generated Commit Message", border_style="dark_khaki", style="white on rgb(39,40,34)"))
                    printer.print_divider()
                    action = questionary.select("What would you like to do?", choices=["Commit", "Retry commit message generation", "Cancel"]).ask()
                    printer.print_divider()
                    if action == "Commit":
                        try:
                            logger.debug("Committing changes.")
                            subprocess.run(["git", "commit", "-m", commit_message], check=True)
                            console.print("[bold green]Changes committed successfully.[/bold green]")
                        except subprocess.CalledProcessError as e:
                            logger.error(f"Failed to commit changes: {e}")
                            console.print(f"[bold red]Failed to commit changes: {e}[/bold red]")
                    elif action == "Retry commit message generation":
                        logger.info("Retrying commit message generation.")
                        continue
                    else:
                        logger.info("Commit aborted by user.")
                        console.print("[bold yellow]Commit aborted by user.[/bold yellow]")
                else:
                    logger.error("Failed to generate a commit message.")
                    console.print("[bold red]Failed to generate a commit message.[/bold red]")

            elif action == "Review Staged Changes":
                diff, unstaged_diff, staged_changes, unstaged_changes = display_and_get_status()

                if not diff:
                    console.print("[bold red]No staged changes detected.[/bold red]")
                    continue
                display_file_diffs(diff, staged_changes, subtitle="Changes: Additions and Deletions")
                display_status(unstaged_changes, staged_changes)

            elif action == "Stage Files":
                if not unstaged_changes:
                    console.print("[bold red]No unstaged changes detected.[/bold red]")
                    continue
                files_to_stage = questionary.checkbox("Select files to stage:", choices=[change["file"] for change in unstaged_changes]).unsafe_ask()
                if files_to_stage:
                    stage_files(files_to_stage)

            elif action == "Unstage Files":
                if not staged_changes:
                    console.print("[bold red]No staged changes detected.[/bold red]")
                    continue
                files_to_unstage = questionary.checkbox("Select files to unstage:", choices=[change["file"] for change in staged_changes]).unsafe_ask()
                if files_to_unstage:
                    unstage_files(files_to_unstage)

            elif action == "Exit":
                console.print("[bold green]Exiting...[/bold green]")
                break

        except KeyboardInterrupt:
            console.print("\n[bold red]Process interrupted by user. Exiting...[/bold red]")
            break

if __name__ == "__main__":
    main()
