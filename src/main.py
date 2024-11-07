#!/usr/bin/env python3
import re
import subprocess
import requests
import os
import json
from rich.console import Console, Group
from rich.syntax import Syntax
from rich.align import Align
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
import configparser
from rich.table import Table
from rich.rule import Rule
from rich.text import Text
from rich.padding import Padding
import questionary
from rich.markdown import Markdown
import logging
from typing import List, Dict, Any, Tuple, Optional
from prompts import SYSTEM_MESSAGE, USER_MSG_APPENDIX

# Initialize logger and console for logging and output
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
console = Console()

# Initialize the config parser
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.ini")
config.read(config_path)

# Load configurations
AUTH_TOKEN = config["API"]["auth_token"]
API_URL = config["API"]["api_url"]
MODEL = config["API"]["model"]
MAX_TOKENS = int(config["API"]["max_tokens"])
TEMPERATURE = float(config["API"]["temperature"])

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
    table = Table(show_header=False, header_style=None, border_style=None, show_lines=False, box=None, padding=(0, 1), title=title, style=None, expand=True)
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
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}\npress ENTER again to auto-commit upon generation"), transient=True) as progress:

            task = progress.add_task(MODEL if len(MODEL) < 30 else f"{MODEL[0:31]}...", start=False)
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

def get_diff_summary_panel(file_changes: List[Dict[str, Any]], title: str, subtitle: str, panel_width: int = 100, _panel_style: str = "bold white on rgb(39,40,34)") -> Panel:
    """
    Display the staged changes in a neat panel.
    """
    if title == "Unstaged Changes":
        color = "red"
    else:
        color = "green"
    table = Table(show_header=False, header_style=f"bold {color}",style=f"italic {color}", show_lines=False, box=None)
    table.add_column("File", justify="left", style="bold white", no_wrap=True)
    table.add_column("Additions", justify="right", style="green")
    table.add_column("Deletions", justify="right", style="red")

    for change in file_changes:
        table.add_row(change["file"], f"+{str(change['additions'])}", f"-{str(change['deletions'])}")
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

    # panels += [Text("\n"), Rule(style="bold dark_khaki"), Text("\n")]
    # panels.append(summary_panel)
    grouped_panels = Group(*panels)

    panel = Panel(grouped_panels, title="[bold white]File Diffs[/bold white]", border_style="dark_khaki", style="white on rgb(39,40,34)", padding=(2, 4), expand=True)

    console.print(Align.center(panel, vertical="middle"))


def parse_commit_log(log_output: str):
    """Parse the git log output into a list of commit details."""
    commits = [commit for commit in log_output.split("\n\n") if commit.strip()]
    parsed_commits = []

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

        parsed_commits.append((commit_hash, commit_message, additions, deletions))

    return parsed_commits


def display_commit_history(num_commits: int = 5):
    """Display the commit history with the specified number of commits."""
    try:
        # Determine the number of commits to fetch
        num_commits_arg = ["-n", str(num_commits)] if num_commits > 0 else []

        result = subprocess.run(["git", "log", "--pretty=format:%h %s", "--stat"] + num_commits_arg, stdout=subprocess.PIPE, check=True)
        log_output = result.stdout.decode("utf-8")
        parsed_commits = parse_commit_log(log_output)

        table = create_styled_table_clean("Recent Commits")
        table.add_column("Hash", style=f"bold {THEME['secondary']}")
        table.add_column("Message", style=THEME["text"])
        table.add_column("Additions", style=THEME["success"])
        table.add_column("Deletions", style=THEME["error"])

        for commit_hash, commit_message, additions, deletions in parsed_commits:
            table.add_row(commit_hash, commit_message, f"+{additions}", f"-{deletions}")

        console.print(Panel(table, style="", border_style="black", padding=(1, 2)))

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

def get_diff_summary_table(file_changes: List[Dict[str, Any]], color: str) -> Table:
    """
    Create a table summarizing file changes.
    """
    table = Table(show_header=True, show_lines=True, box=None, padding=(0, 2))
    table.add_column("File", justify="left", style="bold white", no_wrap=True)
    table.add_column("Additions", justify="right", style="green")
    table.add_column("Deletions", justify="right", style="red")

    total_additions = 0
    total_deletions = 0
    for change in file_changes:
        file_with_counts = f"{change['file']} (+{change['additions']}/-{change['deletions']})"
        table.add_row(Padding(file_with_counts, (0, 3)), Padding(f"+{str(change['additions'])}", (0, 3)), Padding(f"-{str(change['deletions'])}", (0, 3)))
        total_additions += change["additions"]
        total_deletions += change["deletions"]

    # Add a summary row
    # table.add_row(Padding("Total", (0, 1)), Padding(f"+{str(total_additions)}", (0, 1)), Padding(f"-{str(total_deletions)}", (0, 1)), style="bold")

    return table

def display_status(unstaged_changes: List[Dict[str, Any]], staged_changes: List[Dict[str, Any]], staged: bool = True, unstaged: bool = False):
    """
    Display the status of unstaged and staged changes.
    """
    panel_width = 50  # Set a fixed width for the panels

    if unstaged:
        unstaged_table = get_diff_summary_table(unstaged_changes, "red")
        unstaged_panel = Panel(Padding(unstaged_table, (1, 1)), title_align="left", title="[bold red]Unstaged Changes", border_style="red", width=100, expand=False)
        console.print(unstaged_panel)

    if staged:
        staged_table = get_diff_summary_table(staged_changes, "green")
        staged_panel = Panel(Padding(staged_table, (1, 1)), title_align="left", title="[bold green]Staged Changes", border_style="green", width=100, expand=False)
        console.print(staged_panel)

def get_status() -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Display the status of unstaged and staged changes and return the diffs and changes.
    """
    diff = get_git_diff(staged=True)
    unstaged_diff = get_git_diff(staged=False)
    staged_changes = parse_diff(diff)
    unstaged_changes = parse_diff(unstaged_diff)

    return diff, unstaged_diff, staged_changes, unstaged_changes

def load_gitignore():
    """
    Load the current .gitignore file and return the list of ignored files.
    """
    if not os.path.exists('.gitignore'):
        return []
    with open('.gitignore', 'r') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def save_gitignore(ignored_files):
    """
    Save the list of ignored files to the .gitignore file.
    """
    with open('.gitignore', 'w') as f:
        f.write('\n'.join(ignored_files) + '\n')

def get_tracked_files():
    """
    Get a list of all tracked files in the repository.
    """
    result = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    return result.stdout.splitlines()

def main():
    """
    Main function to generate and commit a message based on staged changes.
    """
    console.print(Markdown("# c-01"))
    printer = CLIPrinter(console)
    questionary_style = configure_questionary_style()

    display_commit_history(3)
    while True:
        try:
            printer.print_divider()
            diff, unstaged_diff, staged_changes, unstaged_changes = get_status()
            display_status(unstaged_changes, staged_changes, staged=True if staged_changes else False, unstaged=True if unstaged_changes else False)

            staged_changes = parse_diff(diff)
            unstaged_changes = parse_diff(unstaged_diff)

            # Count the number of staged files
            num_staged_files = len(staged_changes)

            # Dynamically generate the list of choices based on the presence of staged changes
            choices = []
            if staged_changes:
                choices.append(f"Generate commit for staged files ({num_staged_files})")
                choices.extend(["Review Changes", "Unstage Files"])
            choices.extend(["Stage Files", "Ignore Files", "History", "Exit"])

            action = questionary.select(f"What would you like to do?", choices=choices, style=questionary_style).unsafe_ask()
            if action == f"Generate commit for staged files ({num_staged_files})":
                if not diff:
                    console.print("[bold red]No staged changes detected.[/bold red]")
                    continue
                # Display the diff for staged changes
                display_file_diffs(diff, staged_changes, subtitle="Changes: Additions and Deletions")

                commit_message = generate_commit_message(diff)
                if commit_message:
                    printer.print_divider()
                    console.print(Panel(commit_message, title=f"Commit Generated by {MODEL if len(MODEL) < 30 else f'{MODEL[0:31]}...'}", border_style="dark_khaki", style="white on rgb(39,40,34)"))
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

            elif action == "Review Changes":
                review_choices = []
                if staged_changes:
                    review_choices.append("Staged")
                if unstaged_changes:
                    review_choices.append("Unstaged")
                review_action = questionary.select("Which changes would you like to review?", choices=review_choices, style=questionary_style).unsafe_ask()

                if review_action == "Staged":
                    # Display the diff for staged changes
                    display_file_diffs(diff, staged_changes, subtitle="Staged Changes")
                elif review_action == "Unstaged":
                    # Display the diff for unstaged changes
                    display_file_diffs(unstaged_diff, unstaged_changes, subtitle="Unstaged Changes")

            elif action == "Stage Files":
                if not unstaged_changes:
                    console.print("[bold red]No unstaged changes detected.[/bold red]")
                    continue
                files_to_stage = questionary.checkbox("Select files to stage:", choices=[change["file"] for change in unstaged_changes]).unsafe_ask()
                if files_to_stage:
                    stage_files(files_to_stage)
                    console.print(f"[bold green]Staged files: {', '.join(files_to_stage)}[/bold green]")

            elif action == "Unstage Files":
                if not staged_changes:
                    console.print("[bold red]No staged changes detected.[/bold red]")
                    continue
                files_to_unstage = questionary.checkbox("Select files to unstage:", choices=[change["file"] for change in staged_changes]).unsafe_ask()
                if files_to_unstage:
                    unstage_files(files_to_unstage)
                    console.print(f"[bold green]Unstaged files: {', '.join(files_to_unstage)}[/bold green]")

            elif action == "Ignore Files":
                ignored_files = load_gitignore()
                all_files = get_tracked_files()
                choices = [questionary.Choice(file, checked=(file in ignored_files)) for file in all_files]
                selected_files = questionary.checkbox("Select files to ignore:", choices=choices).unsafe_ask()
                save_gitignore(selected_files)
                console.print("[bold green]Updated .gitignore file.[/bold green]")

            elif action == "History":
                display_commit_history(0)
                console.print("[bold green]Displayed commit history.[/bold green]")

            elif action == "Exit":
                console.print("[bold green]Exiting...[/bold green]")
                break

        except KeyboardInterrupt:
            console.print("\n[bold red]Process interrupted by user. Exiting...[/bold red]")
            console.print("Goodbye.")
            break

if __name__ == "__main__":
    main()
