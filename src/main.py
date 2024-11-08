import re
import subprocess
import requests
import os
import json
import configparser
import logging
import questionary
from typing import List, Dict, Any, Tuple, Optional
from prompts import SYSTEM_MESSAGE, USER_MSG_APPENDIX
from rich.console import Console, Group
from rich.syntax import Syntax
from rich.align import Align
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich.padding import Padding
from rich.markdown import Markdown

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
    "primary": "#e5c07b",
    "secondary": "#ffcb6b",
    "accent": "#8ea6c0",
    "success": "#98c379",
    "error": "#e06c75",
    "warning": "#e5c07b",
    "background": "#282c34",
    "text": "#abb2bf",
}

# Style configurations
PANEL_STYLE = f"bold {THEME['text']} on {THEME['background']}"
BORDER_STYLE = THEME["accent"]
HEADER_STYLE = f"bold {THEME['primary']}"

class StyledCLIPrinter:
    """
    A class to handle styled printing to the console using Rich.
    """
    def __init__(self, console: Console):
        self.console = console

    def print_message(self, message: str, style: str, title: Optional[str] = None):
        """
        Print a styled message to the console.
        """
        content = Text(message, style=style)
        panel = Panel(content, title=title, border_style=BORDER_STYLE, style=PANEL_STYLE, padding=(1, 2)) if title else content
        self.console.print(panel)

    def print_error(self, message: str, title: str = "Error"):
        """
        Print an error message to the console.
        """
        self.print_message(message, f"bold {THEME['error']}", title)

    def print_warning(self, message: str, title: str = "Warning"):
        """
        Print a warning message to the console.
        """
        self.print_message(message, f"bold {THEME['warning']}", title)

    def print_success(self, message: str, title: str = "Success"):
        """
        Print a success message to the console.
        """
        self.print_message(message, f"bold {THEME['success']}", title)

    def print_divider(self, title: str = ""):
        """
        Print a divider line to the console.
        """
        self.console.print()
        self.console.rule(title, style=BORDER_STYLE)
        self.console.print()
printer = StyledCLIPrinter(console)

def create_styled_table(title: Optional[str] = None, clean: bool = False) -> Table:
    """
    Create a styled table for displaying data.
    """
    padding = (0, 1) if clean else (2, 2)
    return Table(show_header=False, header_style=None if clean else HEADER_STYLE, border_style=None, show_lines=False, box=None, padding=padding, title=title, expand=clean)

def extract_tag_value(text: str, tag: str) -> str:
    """
    Extract the value enclosed within specified XML-like or bracket-like tags, case-insensitive.
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

            response = requests.post(API_URL, headers=headers, json=body, stream=True, timeout=60)
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

def handle_review_changes(staged_changes: List[Dict[str, Any]], unstaged_changes: List[Dict[str, Any]], diff: str, unstaged_diff: str):
    """
    Handle the review of changes by allowing users to select specific files to view diffs.

    Args:
        staged_changes (List[Dict[str, Any]]): List of staged changes.
        unstaged_changes (List[Dict[str, Any]]): List of unstaged changes.
        diff (str): The git diff of staged changes.
        unstaged_diff (str): The git diff of unstaged changes.
    """
    # Create sets for quick lookup
    staged_files = set(change["file"] for change in staged_changes)
    unstaged_files = set(change["file"] for change in unstaged_changes)
    all_files = staged_files.union(unstaged_files)

    if not all_files:
        console.print("[bold yellow]No changes to review.[/bold yellow]")
        return

    # Prepare choices with staged files pre-checked and labeled
    choices = [
        questionary.Choice(
            title=f"{file} [Staged]" if file in staged_files else file,
            value=file,
            checked=file in staged_files
        )
        for file in sorted(all_files)
    ]

    # Prompt the user to select files to review
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
        # Determine if the file is staged
        is_staged = file in staged_files

        # Get the appropriate diff for the file
        file_diff = get_file_diff(file, staged=is_staged)

        if file_diff:
            # Display the diff in a styled panel
            _panel = display_diff_panel(file, file_diff, staged_changes, panel_width=100)
            console.print(_panel)
        else:
            console.print(f"[bold red]No diff available for {file}.[/bold red]")

def get_file_diff(file: str, staged: bool = True) -> List[str]:
    """
    Retrieve the git diff for a specific file, either staged or unstaged.

    Args:
        file (str): The file path.
        staged (bool): Whether to retrieve the staged diff. Defaults to True.

    Returns:
        List[str]: The diff lines for the file.
    """
    try:
        cmd = ["git", "diff", "--staged", "--", file] if staged else ["git", "diff", "--", file]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, check=True, text=True)
        diff = result.stdout.strip().split('\n')
        return diff
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get diff for {file}: {e}")
        console.print(f"[bold red]Failed to get diff for {file}: {e}[/bold red]")
        return []

def stage_files(files: List[str]):
    """
    Stage the specified files.
    """
    try:
        subprocess.run(["git", "add"] + files, check=True)
        console.print("[bold green]Files staged successfully.[/bold green]")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to stage files: {e}")
        console.print(f"[bold red]Failed to stage files: {e}[/bold red]")

def unstage_files(files: List[str]):
    """
    Unstage the specified files.
    """
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
    color = "red" if title == "Unstaged Changes" else "green"
    table = Table(show_header=False, header_style=f"bold {color}", style=f"italic {color}", show_lines=False, box=None)
    table.add_column("File", justify="left", style="bold white", no_wrap=True)
    table.add_column("Additions", justify="right", style="green")
    table.add_column("Deletions", justify="right", style="red")

    for change in file_changes:
        table.add_row(change["file"], f"+{str(change['additions'])}", f"-{str(change['deletions'])}")

    return table

def display_diff_panel(filename: str, diff_lines: List[str], file_changes: List[Dict[str, Any]], panel_width: int = 100) -> Optional[Panel]:
    """
    Display a diff panel for a single file.

    Args:
        filename (str): The name of the file.
        diff_lines (List[str]): The lines of the diff.
        file_changes (List[Dict[str, Any]]): List of all file changes.
        panel_width (int): The width of the panel. Defaults to 100.

    Returns:
        Optional[Panel]: The created panel or None if no diff lines are provided.
    """
    if not diff_lines:
        diff_text = "No changes."
    else:
        diff_text = "\n".join(diff_lines)

    # Determine the styling based on staged or unstaged
    is_staged = any(change["file"] == filename for change in file_changes)
    border_style = "dark_khaki" if is_staged else "red"
    title = f"[bold blue]{filename}[/bold blue] [{'Staged' if is_staged else 'Unstaged'}]"

    # Create syntax-highlighted diff
    syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)

    # Extract additions and deletions
    changes = next((change for change in file_changes if change["file"] == filename), {})
    additions = changes.get("additions", 0)
    deletions = changes.get("deletions", 0)
    footer = f"Additions: +{additions}, Deletions: -{deletions}"

    # Create the panel
    panel = Panel(
        Align.center(syntax),
        title=title,
        border_style="",
        style="",
        padding=(1, 2),
        subtitle=footer,
        width=panel_width
    )

    return Align.center(panel)

def display_file_diffs(diff: str, staged_file_changes: List[Dict[str, Any]], subtitle: str, panel_width: int = 100):
    """
    Display the diff for each file in a separate panel.

    Args:
        diff (str): The git diff of staged changes.
        staged_file_changes (List[Dict[str, Any]]): List of staged changes.
        subtitle (str): Subtitle for the panels.
        panel_width (int): The width of the panels. Defaults to 100.
    """
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
        panel = Panel(grouped_panels, title="[bold white]File Diffs[/bold white]", border_style="dark_khaki", style="white on rgb(39,40,34)", padding=(2, 4), expand=True)
        console.print(panel)
    else:
        console.print("[bold yellow]No diffs to display.[/bold yellow]")
def parse_commit_log(log_output: str):
    """
    Parse the git log output into a list of commit details.

    Args:
        log_output (str): The git log output.

    Returns:
        List[Tuple[str, Text, int, int]]: List of parsed commit details.
    """
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
    """
    Display the commit history with the specified number of commits.

    Args:
        num_commits (int): Number of commits to display.
    """
    try:
        num_commits_arg = ["-n", str(num_commits)] if num_commits > 0 else []
        result = subprocess.run(["git", "log", "--pretty=format:%h %s", "--stat"] + num_commits_arg, stdout=subprocess.PIPE, check=True)
        log_output = result.stdout.decode("utf-8")
        parsed_commits = parse_commit_log(log_output)

        table = create_styled_table("Recent Commits", clean=True)
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
    """
    Configure the style for questionary prompts.

    Returns:
        questionary.Style: The configured style.
    """
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

    Args:
        file_changes (List[Dict[str, Any]]): List of file changes.
        color (str): Color for the table.

    Returns:
        Table: A styled table summarizing the file changes.
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

    return table

def display_status(unstaged_changes: List[Dict[str, Any]], staged_changes: List[Dict[str, Any]], staged: bool = True, unstaged: bool = False):
    """
    Display the status of unstaged and staged changes.

    Args:
        unstaged_changes (List[Dict[str, Any]]): List of unstaged changes.
        staged_changes (List[Dict[str, Any]]): List of staged changes.
        staged (bool): Whether to display staged changes.
        unstaged (bool): Whether to display unstaged changes.
    """
    panel_width = 50

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
    Get the status of unstaged and staged changes and return the diffs and changes.

    Returns:
        Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]: The diffs and changes.
    """
    diff = get_git_diff(staged=True)
    unstaged_diff = get_git_diff(staged=False)
    staged_changes = parse_diff(diff)
    unstaged_changes = parse_diff(unstaged_diff)

    return diff, unstaged_diff, staged_changes, unstaged_changes

def load_gitignore() -> List[str]:
    """
    Load the current .gitignore file and return the list of ignored files.

    Returns:
        List[str]: List of ignored files.
    """
    if not os.path.exists('.gitignore'):
        return []
    with open('.gitignore', 'r') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def save_gitignore(ignored_files: List[str]):
    """
    Save the list of ignored files to the .gitignore file.

    Args:
        ignored_files (List[str]): List of files to ignore.
    """
    with open('.gitignore', 'w') as f:
        f.write('\n'.join(ignored_files) + '\n')

def get_tracked_files() -> List[str]:
    """
    Get a list of all tracked files in the repository.

    Returns:
        List[str]: List of tracked files.
    """
    result = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    return result.stdout.splitlines()

def get_repo_name() -> str:
    """
    Function to get the repository name.

    Returns:
        str: The repository name.
    """
    try:
        repo_name = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], universal_newlines=True).strip().split('/')[-1]
        return repo_name
    except subprocess.CalledProcessError:
        return "Unknown Repository"

def get_menu_options(staged_changes: List[Dict[str, Any]], unstaged_changes: List[Dict[str, Any]]) -> (str, List[str]):
    """
    Determine the appropriate menu title and options based on the current repository state.

    Args:
        staged_changes (List[Dict[str, Any]]): List of staged changes.
        unstaged_changes (List[Dict[str, Any]]): List of unstaged changes.

    Returns:
        Tuple[str, List[str]]: A tuple containing the menu title and the list of menu options.
    """
    num_staged_files = len(staged_changes)
    choices = []
    title = "Select an Action:"

    if staged_changes and unstaged_changes:
        title = "Repository Status: Staged and Unstaged Changes Detected"
        choices.extend([
            f"Commit Staged Files ({num_staged_files})",
            "Review Changes",
            "Stage Additional Files",
            "Unstage Files",
            "Ignore Files",
            "View Commit History",
            "Exit"
        ])
    elif staged_changes:
        title = "Repository Status: Staged Changes Detected"
        choices.extend([
            f"Commit Staged Files ({num_staged_files})",
            "Review Changes",
            "Unstage Files",
            "Ignore Files",
            "View Commit History",
            "Exit"
        ])
    elif unstaged_changes:
        title = "Repository Status: Unstaged Changes Detected"
        choices.extend([
            "Review Changes",
            "Stage Files",
            "Ignore Files",
            "View Commit History",
            "Exit"
        ])
    else:
        title = "Repository Status: Up to Date"
        choices.extend([
            "Ignore Files",
            "View Commit History",
            "Exit"
        ])

    return title, choices

def handle_generate_commit(diff: str, staged_changes: List[Dict[str, Any]]):
    """
    Handle the generation of a commit message and committing the changes.

    Args:
        diff (str): The git diff of staged changes.
        staged_changes (List[Dict[str, Any]]): List of staged changes.
    """
    if not diff:
        console.print("[bold red]No staged changes detected.[/bold red]")
        return

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
            handle_generate_commit(diff, staged_changes)
        else:
            logger.info("Commit aborted by user.")
            console.print("[bold yellow]Commit aborted by user.[/bold yellow]")
    else:
        logger.error("Failed to generate a commit message.")
        console.print("[bold red]Failed to generate a commit message.[/bold red]")


def handle_stage_files(unstaged_changes: List[Dict[str, Any]]):
    """
    Handle the staging of files.

    Args:
        unstaged_changes (List[Dict[str, Any]]): List of unstaged changes.
    """
    if not unstaged_changes:
        console.print("[bold red]No unstaged changes detected.[/bold red]")
        return
    files_to_stage = questionary.checkbox("Select files to stage:", choices=[change["file"] for change in unstaged_changes]).unsafe_ask()
    if files_to_stage:
        stage_files(files_to_stage)
        console.print(f"[bold green]Staged files: {', '.join(files_to_stage)}[/bold green]")

def handle_unstage_files(staged_changes: List[Dict[str, Any]]):
    """
    Handle the unstaging of files.

    Args:
        staged_changes (List[Dict[str, Any]]): List of staged changes.
    """
    if not staged_changes:
        console.print("[bold red]No staged changes detected.[/bold red]")
        return
    files_to_unstage = questionary.checkbox("Select files to unstage:", choices=[change["file"] for change in staged_changes]).unsafe_ask()
    if files_to_unstage:
        unstage_files(files_to_unstage)
        console.print(f"[bold green]Unstaged files: {', '.join(files_to_unstage)}[/bold green]")

def handle_ignore_files():
    """
    Handle the ignoring of files.
    """
    ignored_files = load_gitignore()
    all_files = get_tracked_files()
    choices = [questionary.Choice(file, checked=(file in ignored_files)) for file in all_files]
    selected_files = questionary.checkbox("Select files to ignore:", choices=choices).unsafe_ask()
    save_gitignore(selected_files)
    console.print("[bold green]Updated .gitignore file.[/bold green]")

def main():
    """
    Main function to generate and commit a message based on staged changes.
    """
    console.print(Markdown("# c-01"))

    questionary_style = configure_questionary_style()
    repo_name = get_repo_name()  # Function to get the repository name

    display_commit_history(3)
    while True:
        try:
            printer.print_divider()
            diff, unstaged_diff, staged_changes, unstaged_changes = get_status()
            display_status(unstaged_changes, staged_changes, staged=bool(staged_changes), unstaged=bool(unstaged_changes))

            total_additions = sum(change["additions"] for change in staged_changes + unstaged_changes)
            total_deletions = sum(change["deletions"] for change in staged_changes + unstaged_changes)

            console.print(f"{repo_name} [green]+{total_additions}[/green], [red]-{total_deletions}[/]")

            title,choices = get_menu_options(staged_changes, unstaged_changes)
            action = questionary.select(title, choices=choices).unsafe_ask()

            if action == f"Generate commit for staged files ({len(staged_changes)})":
                handle_generate_commit(diff, staged_changes)
            elif action == "Review Changes":
                handle_review_changes(staged_changes, unstaged_changes, diff, unstaged_diff)
            elif action == "Stage Files":
                handle_stage_files(unstaged_changes)
            elif action == "Unstage Files":
                handle_unstage_files(staged_changes)
            elif action == "Ignore Files":
                handle_ignore_files()
            elif action == "History":
                display_commit_history(0)
                console.print("[bold green]Displayed commit history.[/bold green]")
            elif action == "Exit":
                console.print("[bold green]Exiting...[/bold green]")
                break

        except KeyboardInterrupt:
            continue

if __name__ == "__main__":
    main()
