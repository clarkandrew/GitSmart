import re
import subprocess
import requests
import os
from count_tokens import count_tokens_in_string
import json
import configparser
from math import floor, ceil
import logging
import questionary
import time
import sys
from typing import List, Dict, Any, Tuple, Optional
from prompts import SYSTEM_MESSAGE, USER_MSG_APPENDIX, SYSTEM_MESSAGE_EMOJI,SUMMARIZE_COMMIT_PROMPT
from rich.console import Console, Group
from rich.syntax import Syntax
from rich.align import Align
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich.padding import Padding
from rich.markdown import Markdown
from prompt_toolkit.history import FileHistory

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
USE_EMOJIS = True if config["PROMPTING"]["use_emojis"] == "true" or config["PROMPTING"]["use_emojis"] == True else False
DEBUG = True if config["APP"]["debug"] == "true" or config["APP"]["debug"] == True else False


# Initialize logger and console for logging and output
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
console = Console()

# Theme configuration
THEME = {"primary": "#e5c07b", "secondary": "#ffcb6b", "accent": "#8ea6c0", "success": "#98c379", "error": "#e06c75", "warning": "#e5c07b", "background": "#282c34", "text": "#abb2bf"}

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


def truncate_diff(diff: str, system_message: str, user_msg_appendix: str, max_tokens: int) -> str:
    """
    Truncate the diff to ensure the total token count does not exceed max_tokens.

    The truncation is performed smartly by removing the least critical parts of the diff
    to retain as much context as possible.

    Parameters:
        diff (str): The original diff string to be truncated.
        system_message (str): The system message content.
        user_msg_appendix (str): The user message appendix content.
        max_tokens (int): The maximum allowed number of tokens.

    Returns:
        str: The truncated diff that fits within the token limit.
    """
    from math import floor

    # Helper function to count tokens in a given string
    def count_tokens(text: str) -> int:
        # Placeholder for actual token counting logic
        # Replace this with the appropriate tokenizer, e.g., OpenAI's tokenizer
        return len(text.split())

    total_allowed_tokens = max_tokens - count_tokens(system_message) - count_tokens(user_msg_appendix)
    current_tokens = count_tokens(diff)

    if current_tokens <= total_allowed_tokens:
        return diff

    logger.info(f"Truncating diff from {current_tokens} to {total_allowed_tokens} tokens.")

    # Split the diff into lines for granular truncation
    diff_lines = diff.splitlines()

    # Calculate average tokens per line
    avg_tokens_per_line = current_tokens / max(len(diff_lines), 1)

    # Estimate the number of lines to keep
    lines_to_keep = floor(total_allowed_tokens / avg_tokens_per_line)

    # Ensure at least one line is kept
    lines_to_keep = max(1, lines_to_keep)

    # Truncate the diff while keeping the start and end intact to preserve context
    if lines_to_keep < len(diff_lines):
        # Keep the first and last few lines
        head = diff_lines[: max(floor(lines_to_keep / 2), 1)]
        tail = diff_lines[-max(ceil(lines_to_keep / 2), 1) :]
        truncated_diff = "\n".join(head + ["..."] + tail)
        logger.debug("Diff truncated to preserve context at both ends.")
    else:
        # If lines_to_keep >= len(diff_lines), no truncation needed
        truncated_diff = diff

    # Verify the token count after truncation
    final_tokens = count_tokens(system_message + truncated_diff + user_msg_appendix)
    if final_tokens > max_tokens:
        logger.warning(f"Truncated diff still exceeds max tokens ({final_tokens}/{max_tokens}). Further truncation may be required.")

    return truncated_diff


def generate_commit_message(diff: str) -> str:
    """
    Generate a commit message using an external service.
    Retries until a properly formatted commit message is received or maximum retries reached.
    """
    logger.debug(USE_EMOJIS)
    INSTRUCT_PROMPT = SYSTEM_MESSAGE_EMOJI if USE_EMOJIS else SYSTEM_MESSAGE

    logger.debug("Entering generate_commit_message function.")
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"}
    messages = [{"role": "system", "content": INSTRUCT_PROMPT}, {"role": "user", "content": diff + USER_MSG_APPENDIX}]
    body = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "n": 1,
        "stop": None,
        "temperature": TEMPERATURE,
        "stream": True
    }
    request_tokens = count_tokens_in_string(INSTRUCT_PROMPT + diff + USER_MSG_APPENDIX)
    max_retries = 5
    retry_count = 0

    while retry_count < max_retries:
        if request_tokens > MAX_TOKENS:
            logger.warning(f"Request exceeds max tokens ({request_tokens}/{MAX_TOKENS})\n\ttruncating...")
            truncated_diff = truncate_diff(diff, INSTRUCT_PROMPT, USER_MSG_APPENDIX, MAX_TOKENS)
            messages = [{"role": "system", "content": INSTRUCT_PROMPT}, {"role": "user", "content": truncated_diff + USER_MSG_APPENDIX}]
            body["messages"] = messages
            request_tokens = count_tokens_in_string(INSTRUCT_PROMPT + truncated_diff + USER_MSG_APPENDIX)
            logger.info(f"After truncation, request tokens are {request_tokens}/{MAX_TOKENS}.")

        # Additional checks before proceeding
        if request_tokens > MAX_TOKENS:
            warning_message = f"The generated commit message exceeds the maximum token limit of {MAX_TOKENS} tokens. Do you want to proceed?"
            if not questionary.confirm(warning_message).ask():
                console.print("[bold red]Commit generation aborted by user.[/bold red]")
                return ""

        deletions = sum(change["deletions"] for change in parse_diff(diff))
        additions = sum(change["additions"] for change in parse_diff(diff))
        logger.debug(f"deletions: {deletions}, additions: {additions}")

        # Display warning if deletions are at least twice the additions
        if additions > 0:
            if deletions > 2 * additions:
                warning_message = f"The commit message indicates a high number of deletions ({deletions}) relative to additions ({additions}). Do you want to proceed?"
                if not questionary.confirm(warning_message).ask():
                    console.print("[bold red]Commit generation aborted by user.[/bold red]")
                    return ""
        elif deletions > 0:
            # Handle case where additions are zero but deletions exist
            warning_message = f"The commit message indicates {deletions} deletions with no additions. Do you want to proceed?"
            if not questionary.confirm(warning_message).ask():
                console.print("[bold red]Commit generation aborted by user.[/bold red]")
                return ""

        try:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}\npress ENTER again to auto-commit upon generation"), transient=True) as progress:
                prepend_msg = f"Sending {request_tokens} tokens to "
                task = progress.add_task(f"{prepend_msg} {MODEL} ({TEMPERATURE})" if len(MODEL) < 30 else f"{prepend_msg} {MODEL[0:31]} ({TEMPERATURE})...", start=False)
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
                if commit_message_text:
                    console.log("Commit message generated successfully.")
                    return commit_message_text
                else:
                    logger.error("Could not extract COMMIT_MESSAGE tags. Retrying...")
                    console.print("[bold red]Commit message format incorrect. Retrying...[/bold red]")
                    retry_count += 1
                    # Optionally, implement a short delay before retrying
                    time.sleep(2)

        except Exception as e:
            logger.error(f"Failed to generate commit message: {e}")
            console.print(f"[bold red]Failed to generate commit message: {e}[/bold red]")
            return ""

    # After max retries
    console.print("[bold red]Failed to generate a properly formatted commit message after multiple attempts.[/bold red]")
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

def summarize_selected_commits():
    """
    Summarize selected commit messages from the last 30 commits.
    """
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

    combined_messages = "\n\n---\n\n".join(f"{commit['hash']} {commit['message']}\n{commit['full_message']}" for commit in selected_commits)
    console.print(Panel(Markdown(combined_messages), title="Commit Messages", border_style="green", style="white on rgb(39,40,34)"))
    # Send the combined commit messages to the summarization API
    summary = generate_summary(combined_messages)
    if summary:
        console.print(Panel(summary, title="Summarized Commit Messages", border_style="green", style="white on rgb(39,40,34)"))
    else:
        console.print("[bold red]Failed to generate summary.[/bold red]")


def generate_summary(text: str) -> Optional[str]:
    """
    Generate a summary for the provided text using the external API.

    Args:
        text (str): The text to summarize.

    Returns:
        Optional[str]: The summarized text or None if summarization fails.
    """
    try:
        headers = {"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"}
        messages = [{"role": "system", "content": SUMMARIZE_COMMIT_PROMPT},
                    {"role": "user", "content": text}]
        body = {
            "model": MODEL,
            "messages": messages,
            "max_tokens": MAX_TOKENS,
            "n": 1,
            "stop": None,
            "temperature": TEMPERATURE,
            "stream": True
        }
        console.log(messages)

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}\npress ENTER again to auto-commit upon generation"), transient=True) as progress:
            prepend_msg = f"Sending {count_tokens_in_string(text)} tokens to "
            task = progress.add_task(f"{prepend_msg} {MODEL} ({TEMPERATURE})" if len(MODEL) < 30 else f"{prepend_msg} {MODEL[0:31]} ({TEMPERATURE})...", start=False)
            progress.start_task(task)

            response = requests.post(API_URL, headers=headers, json=body, stream=True, timeout=60)
            response.raise_for_status()

            summary = ""
            first_chunk_received = False

            for chunk in response.iter_lines():
                if chunk:
                    chunk_data = chunk.decode("utf-8").strip()
                    if chunk_data.startswith("data: "):
                        chunk_data = chunk_data[6:]
                        try:
                            data = json.loads(chunk_data)
                            delta_content = data["choices"][0]["delta"].get("content", "")
                            summary += delta_content

                            if not first_chunk_received:
                                progress.stop()
                                first_chunk_received = True

                            console.print(delta_content, end="")
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to decode JSON chunk: {e}")
                            continue

            summary_text = summary
            if summary_text:
                logger.info("Summary generated successfully.")
                return summary_text
            else:
                logger.error("Could not extract SUMMARY tags.")
                console.print("[bold red]Summary format incorrect.[/bold red]")
                return None

    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        console.print(f"[bold red]Failed to generate summary: {e}[/bold red]")
        return None


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
    choices = [questionary.Choice(title=f"{file} [Staged]" if file in staged_files else file, value=file, checked=file in staged_files) for file in sorted(all_files)]

    # Prompt the user to select files to review
    selected_files = questionary.checkbox("Select files to review their diffs:", choices=choices, style=configure_questionary_style(), instruction="(Use space to select, enter to confirm)").unsafe_ask()

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
        diff = result.stdout.strip().split("\n")
        return diff
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get diff for {file}: {e}")
        console.print(f"[bold red]Failed to get diff for {file}: {e}[/bold red]")
        return []


def run_git_command(command: List[str]) -> str:
    """
    Run a git command and return the result.

    Args:
        command (List[str]): The git command to run.

    Returns:
        str: Status message indicating the result of the command.
    """
    try:
        subprocess.run(command, check=True)
        return f"Success: {' '.join(command)}"
    except subprocess.CalledProcessError as e:
        error_message = f"Error: {' '.join(command)}. Error: {e}"
        logger.error(error_message)
        return error_message
    except FileNotFoundError as e:
        error_message = f"Error: Command not found. {' '.join(command)}. Error: {e}"
        logger.error(error_message)
        return error_message
    except Exception as e:
        error_message = f"Unexpected error: {' '.join(command)}. Error: {e}"
        logger.error(error_message)
        return error_message


def handle_files(changes: List[Dict[str, Any]], action: str) -> str:
    """
    Handle the staging or unstaging of files.

    Args:
        changes (List[Dict[str, Any]]): List of changes.
        action (str): Action to perform, either 'stage' or 'unstage'.

    Returns:
        str: Status message indicating the result of the action.
    """
    if not changes:
        return f"No {action}d changes detected."

    choices = [f"{change['file']} (+{change['additions']}/-{change['deletions']})" for change in changes]
    selected_files = questionary.checkbox(f"Select files to {action}:", choices=choices).unsafe_ask()

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


def stage_files(files: List[str]) -> str:
    """
    Stage the specified files.

    Args:
        files (List[str]): List of files to stage.

    Returns:
        str: Status message indicating the result of the staging.
    """
    return run_git_command(["git", "add"] + files)


def unstage_files(files: List[str]) -> str:
    """
    Unstage the specified files.

    Args:
        files (List[str]): List of files to unstage.

    Returns:
        str: Status message indicating the result of the unstaging.
    """
    return run_git_command(["git", "reset"] + files)


def handle_stage_files(unstaged_changes: List[Dict[str, Any]]) -> str:
    return handle_files(unstaged_changes, "stage")


def handle_unstage_files(staged_changes: List[Dict[str, Any]]) -> str:
    return handle_files(staged_changes, "unstage")


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
        action = questionary.select("What would you like to do?", choices=["Commit", "Retry", "Cancel"]).ask()
        printer.print_divider()
        if action == "Commit":
            commit_status = run_git_command(["git", "commit", "-m", commit_message])
            if "Success" in commit_status:
                return commit_status
            else:
                console.print(f"[bold red]{commit_status}[/bold red]")
        elif action == "Retry":
            logger.info("Retrying commit message generation.")
            handle_generate_commit(diff, staged_changes)
        else:
            logger.info("Commit aborted by user.")
            console.print("[bold yellow]Commit aborted by user.[/bold yellow]")
    else:
        logger.error("Failed to generate a commit message.")
        console.print("[bold red]Failed to generate a commit message.[/bold red]")


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
        table.add_row(change["file"], f"+{change['additions']}", f"-{change['deletions']}")

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
    footer = f"[bold green]+{additions}[/], [bold red]-{deletions}[/]"

    # Create the panel
    panel = Padding(Panel(Align.center(syntax), title=title, border_style="", style="", padding=(1, 2), subtitle=footer, width=panel_width), (5, 5))

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
        console.print(grouped_panels)
    else:
        console.print("[bold yellow]No diffs to display.[/bold yellow]")


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
    table = Table(show_header=False, show_lines=True, box=None, padding=(0, 0))
    table.add_column("File", justify="left", style="bold white", no_wrap=True)
    table.add_column("Additions", justify="right", style="green")
    table.add_column("Deletions", justify="right", style="red")

    total_additions = 0
    total_deletions = 0
    for change in file_changes:
        max_file_name_len = 20
        display_file_name = change["file"]
        if len(display_file_name) > max_file_name_len:
            display_file_name = f"{display_file_name[0:max_file_name_len]}..."
        table.add_row(Padding(change["file"], (0, 2)), Padding(f"+{str(change['additions'])}", (0, 2)), Padding(f"-{str(change['deletions'])}", (0, 2)))
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
        unstaged_panel = Panel(Padding(unstaged_table, (1, 0)), title_align="left", title="[bold white on red]Unstaged Changes[/]", border_style="red", width=50, expand=True)
        console.print(unstaged_panel)

    if staged:
        staged_table = get_diff_summary_table(staged_changes, "green")
        staged_panel = Panel(Padding(staged_table, (1, 0)), title_align="left", title="[bold black on green]Staged Changes[/]", border_style="green", width=50, expand=True)
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


def get_tracked_files() -> List[str]:
    """
    Get a list of all tracked files in the repository.

    Returns:
        List[str]: List of tracked files.
    """
    result = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    return result.stdout.splitlines()


def get_and_display_status():
    diff, unstaged_diff, staged_changes, unstaged_changes = get_status()
    display_status(unstaged_changes, staged_changes, staged=bool(staged_changes), unstaged=bool(unstaged_changes))
    return diff, unstaged_diff, staged_changes, unstaged_changes


def select_model():
    history_dir = ".C0MMIT"

    # Check if .history exists and is a file
    if os.path.exists(history_dir) and not os.path.isdir(history_dir):
        raise FileExistsError(f"A file named '{history_dir}' already exists. Please remove or rename it.")

    # Ensure the .history directory exists
    os.makedirs(history_dir, exist_ok=True)

    # Use a valid file path for FileHistory
    history_file = os.path.join(history_dir, "model_selection")

    global MODEL
    MODEL = questionary.text("Select a model:\n", history=FileHistory(history_file)).ask()
    return MODEL


def reset_console():
    console.clear()
    print("\n" * 25)


def handle_ignore_files():
    """
    Handle the ignoring of files by appending selected files or custom patterns to .gitignore.
    Ensures that existing .gitignore entries outside the managed section are preserved.
    """
    ignored_files = load_gitignore()
    all_files = get_tracked_files()
    choices = [questionary.Choice(file, checked=(file in ignored_files)) for file in all_files]

    # Prompt user to select files to ignore or enter custom patterns
    action = questionary.select(
        "Would you like to select files to ignore or enter custom patterns?",
        choices=["Select files", "Enter custom patterns"]
    ).unsafe_ask()

    if action == "Select files":
        selected_files = questionary.checkbox(
            "Select files to ignore:",
            choices=choices
        ).unsafe_ask()
    else:
        custom_patterns = questionary.text(
            "Enter custom patterns to ignore (comma-separated):"
        ).unsafe_ask()
        selected_files = [pattern.strip() for pattern in custom_patterns.split(",")]

    if selected_files:
        update_gitignore(selected_files)
        console.print("[bold green]Updated .gitignore file with selected files/patterns.[/bold green]")
    else:
        console.print("[bold yellow]No files or patterns selected to ignore.[/bold yellow]")


def save_gitignore_section(ignored_files: List[str]):
    """
    Save the list of ignored files to a specific section in the .gitignore file.
    This prevents overwriting the entire file and keeps managed entries separate.

    Args:
        ignored_files (List[str]): List of files to ignore.
    """
    gitignore_path = ".gitignore"
    start_marker = "# >>> Managed by Git CLI Tool >>>\n"
    end_marker = "# <<< Managed by Git CLI Tool <<<\n"

    managed_section = start_marker
    for file in ignored_files:
        managed_section += f"{file}\n"
    managed_section += end_marker

    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            content = f.read()

        # Remove existing managed section
        content = re.sub(r"# >>> Managed by Git CLI Tool >>>\n.*?# <<< Managed by Git CLI Tool <<<\n", "", content, flags=re.DOTALL)

        # Append the new managed section
        content = content.strip() + "\n\n" + managed_section
    else:
        content = managed_section

    with open(gitignore_path, "w") as f:
        f.write(content)


def load_gitignore() -> List[str]:
    """
    Load the current .gitignore file and return the list of ignored files
    managed by this tool.

    Returns:
        List[str]: List of ignored files.
    """
    gitignore_path = ".gitignore"
    start_marker = "# >>> Managed by Git CLI Tool >>>"
    end_marker = "# <<< Managed by Git CLI Tool <<<"

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


def update_gitignore(selected_files: List[str]):
    """
    Update the .gitignore file by adding newly selected ignored files or patterns.
    Maintains a managed section to prevent duplication.

    Args:
        selected_files (List[str]): List of files or patterns to ignore.
    """
    existing_ignored = set(load_gitignore())
    new_ignored = set(selected_files) - existing_ignored

    if not new_ignored:
        console.print("[bold yellow]No new files or patterns to add to .gitignore.[/bold yellow]")
        return

    all_ignored = sorted(existing_ignored.union(new_ignored))
    save_gitignore_section(all_ignored)


def get_repo_name() -> str:
    """
    Function to get the repository name.

    Returns:
        str: The repository name.
    """
    try:
        repo_path = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], universal_newlines=True).strip()
        repo_name = os.path.basename(repo_path)
        return repo_name
    except subprocess.CalledProcessError:
        return "Unknown Repository"


def get_git_remotes() -> Dict[str, str]:
    """
    Retrieve a dictionary of all configured git remotes and their URLs.

    Returns:
        Dict[str, str]: Dictionary of remote names and their URLs.
    """
    try:
        result = subprocess.run(["git", "remote", "-v"], stdout=subprocess.PIPE, check=True, text=True)
        remotes = result.stdout.strip().split('\n')
        remote_dict = {}
        for remote in remotes:
            parts = remote.split()
            if len(parts) >= 2:
                name, url = parts[0], parts[1]
                if name not in remote_dict:
                    remote_dict[name] = url
        logger.debug(f"Available remotes: {remote_dict}")
        return remote_dict
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to retrieve git remotes: {e}")
        console.print(f"[bold red]Failed to retrieve git remotes: {e}[/bold red]")
        return {}


def push_to_remote(remote: str, url: str) -> str:
    """
    Push to a specific remote repository.

    Args:
        remote: The name of the remote.
        url: The URL of the remote.

    Returns:
        A status message indicating success or failure.
    """
    try:
        logger.debug(f"Pushing to remote: {remote}")
        subprocess.run(["git", "push", remote], check=True)
        return f"Successfully pushed to {remote} ({url})."
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to push to {remote}: {e}")
        return f"Failed to push to {remote}: {e}"


def handle_push_repo() -> List[str]:
    """
    Handle pushing commits to selected remote repositories.

    Returns:
        A list of status messages for each push operation.
    """
    remotes = get_git_remotes()
    if not remotes:
        console.print("[bold red]No remotes found. Please add a remote repository first.[/bold red]")
        return ["No remotes found."]

    # Let user select one or multiple remotes
    selected_remotes = questionary.checkbox(
        "Select remote repositories to push to:",
        choices=[questionary.Choice(f"{name} ({url})", value=name) for name, url in remotes.items()]
    ).unsafe_ask()

    if not selected_remotes:
        console.print("[bold yellow]No remotes selected. Push aborted.[/bold yellow]")
        return ["No remotes selected."]

    # Prepare confirmation message with remote URLs
    confirmation_message = "Are you sure you want to push to the following remote(s):\n"
    for remote in selected_remotes:
        confirmation_message += f"- {remote} ({remotes[remote]})\n"

    # Confirmation
    confirm = questionary.confirm(confirmation_message).ask()

    if not confirm:
        console.print("[bold yellow]Push action canceled by the user.[/bold yellow]")
        return ["Push action canceled by the user."]

    # Execute git push for each selected remote and collect status messages
    status_messages = []
    for remote in selected_remotes:
        status_message = push_to_remote(remote, remotes[remote])
        console.print(f"[bold green]{status_message}[/bold green]" if "Successfully" in status_message else f"[bold red]{status_message}[/bold red]")
        status_messages.append(status_message)

    return status_messages


def get_menu_options(staged_changes: List[Dict[str, Any]], unstaged_changes: List[Dict[str, Any]]) -> Tuple[str, str, List[str]]:
    """
    Determine the appropriate menu title and options based on the current repository state.

    Args:
        staged_changes (List[Dict[str, Any]]): List of staged changes.
        unstaged_changes (List[Dict[str, Any]]): List of unstaged changes.

    Returns:
        Tuple[str, str, List[str]]: A tuple containing the menu title, repository status, and the list of menu options.
    """
    num_staged_files = len(staged_changes)
    base_choices = ["Ignore Files", "View Commit History", "Push Repo", "Summarize Commits", "Exit"]
    choices = []
    title = "Select an action:"

    # Default status: All changes up to date
    repo_status = "[green]✔[/] [bold black on green] All changes are up to date[/]"

    if staged_changes and unstaged_changes:
        # Both staged and unstaged changes detected
        repo_status = "[red]⚠[/] [bold white on red] Staged and unstaged changes detected[/]"
        choices = [f"Generate Commit for Staged Changes ({num_staged_files})", "Stage Files", "Unstage Files", "Review Changes", "Select Model"]
    elif staged_changes:
        # Only staged changes detected
        repo_status = "[blue]➤[/] [bold white on blue] Staged changes detected[/]"
        choices = [f"Generate Commit for Staged Changes ({num_staged_files})", "Unstage Files", "Review Changes", "Select Model"]
    elif unstaged_changes:
        # Only unstaged changes detected
        repo_status = "[yellow]✗[/] [bold black on yellow] Unstaged changes detected[/]"
        choices = ["Stage Files", "Review Changes", "Select Model"]

    # Append the base choices to the specific choices
    choices.extend(base_choices)

    return title, repo_status, choices


def parse_commit_log(log_output: str) -> List[Dict[str, Any]]:
    """
    Parse the git log output into a list of commit details.

    Args:
        log_output (str): The git log output.

    Returns:
        List[Dict[str, Any]]: List of parsed commit details.
    """
    commits = [commit for commit in log_output.split("\n\n") if commit.strip()]
    parsed_commits = []

    for commit in commits:
        lines = commit.split("\n")
        if len(lines) < 2:
            continue

        # Ensure the first line contains both a commit hash and a commit message
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

    Args:
        num_commits (int): Number of commits to display.

    Returns:
        List[Dict[str, Any]]: List of parsed commit details.
    """
    try:
        num_commits_arg = ["-n", str(num_commits)] if num_commits > 0 else []
        result = subprocess.run(["git", "log", "--pretty=format:%h %s%n%b"] + num_commits_arg, stdout=subprocess.PIPE, check=True)
        log_output = result.stdout.decode("utf-8")
        parsed_commits = parse_commit_log(log_output)

        # Display the commit summary
        table = create_styled_table("Recent Commits", clean=True)
        table.add_column("Hash", style=f"bold {THEME['secondary']}")
        table.add_column("Message", style=THEME["text"])

        for commit in parsed_commits:
            table.add_row(commit["hash"], commit["message"])

        console.print(Panel(table, style="", border_style="black", padding=(1, 2)))

        return parsed_commits

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get commit history: {e}")
        console.print(f"[bold {THEME['error']}]Failed to get commit history: {e}[/bold {THEME['error']}]")
        return []


def select_commit(commits: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Allow the user to select a commit from the summary.

    Args:
        commits (List[Dict[str, Any]]): List of parsed commit details.

    Returns:
        Optional[Dict[str, Any]]: The selected commit details or None if no selection is made.
    """
    choices = [questionary.Choice(f"{commit['hash']} {commit['message']}", value=commit) for commit in commits]

    selected_commit = questionary.select("Select a commit to view details:", choices=choices).unsafe_ask()

    return selected_commit


def print_commit_details(commit: Dict[str, Any]):
    """
    Print the full details of the selected commit.

    Args:
        commit (Dict[str, Any]): The selected commit details.
    """
    commit_message_md = Markdown(commit['full_message'])
    console.print(Panel(commit_message_md, title=f"Commit {commit['hash']}", border_style="dark_khaki", style="white on rgb(39,40,34)"))




def run_git_command(command: List[str]) -> str:
    """
    Run a git command and return the result.

    Args:
        command (List[str]): The git command to run.

    Returns:
        str: Status message indicating the result of the command.
    """
    try:
        subprocess.run(command, check=True)
        return f"Success: {' '.join(command)}"
    except subprocess.CalledProcessError as e:
        error_message = f"Error: {' '.join(command)}. Error: {e}"
        logger.error(error_message)
        return error_message
    except FileNotFoundError as e:
        error_message = f"Error: Command not found. {' '.join(command)}. Error: {e}"
        logger.error(error_message)
        return error_message
    except Exception as e:
        error_message = f"Unexpected error: {' '.join(command)}. Error: {e}"
        logger.error(error_message)
        return error_message


def main(reload: bool = False):
    """
    Main function to generate and commit a message based on staged changes.

    Args:
        reload (bool): Whether to enable auto-reloading of repository status.
    """
    diff, unstaged_diff, staged_changes, unstaged_changes = None, None, None, None
    console.print(Markdown("# Git CLI Tool"))

    questionary_style = configure_questionary_style()
    repo_name = get_repo_name()  # Function to get the repository name

    display_commit_summary(3)
    exit_prompted = 0

    def loop():
        nonlocal exit_prompted
        printer.print_divider()
        diff, unstaged_diff, staged_changes, unstaged_changes = get_and_display_status()
        while True:
            try:

                total_additions = sum(change["additions"] for change in staged_changes + unstaged_changes)
                total_deletions = sum(change["deletions"] for change in staged_changes + unstaged_changes)

                console.print(f"\n\n[bold white on black]{repo_name} [green]+{total_additions}[/green], [red]-{total_deletions}[/]")
                title, repo_status, choices = get_menu_options(staged_changes, unstaged_changes)
                console.print(repo_status)
                action = questionary.select(
                    title,
                    choices=choices,
                    style=configure_questionary_style()
                ).unsafe_ask()

                if action.startswith("Generate Commit for Staged Changes"):
                    reset_console()
                    status_msg = handle_generate_commit(diff, staged_changes)
                    diff, unstaged_diff, staged_changes, unstaged_changes = get_and_display_status()
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
                    selected_commit = select_commit(commits)
                    if selected_commit:
                        print_commit_details(selected_commit)

                elif action == "Select Model":
                    reset_console()
                    select_model()
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
                    console.print(f"[bold black on red]Press Ctrl+C {3 - exit_prompted} more time(s) to exit.[/bold black on red]", justify="center")

    if reload:
        refresh_interval = 5  # seconds
        console.print(f"[bold yellow]Auto-reload is enabled. Repository status will refresh every {refresh_interval} seconds.[/bold yellow]")

        def auto_refresh():
            while True:
                console.print(f"[bold yellow]...[/bold yellow]")
                time.sleep(refresh_interval)
                printer.print_divider("Auto Refresh")
                diff, unstaged_diff, staged_changes, unstaged_changes = get_status()

                display_status(unstaged_changes, staged_changes, staged=bool(staged_changes), unstaged=bool(unstaged_changes))
                total_additions = sum(change["additions"] for change in staged_changes + unstaged_changes)
                total_deletions = sum(change["deletions"] for change in staged_changes + unstaged_changes)
                console.print(f"{repo_name} [green]+{total_additions}[/green], [red]-{total_deletions}[/]")
                sys.stdout.flush()

        import threading
        refresh_thread = threading.Thread(target=auto_refresh, daemon=True)
        refresh_thread.start()

    loop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Automate git commit messages with enhanced features.")
    parser.add_argument("--reload", action="store_true", help="Enable auto-refresh of repository status.")
    args = parser.parse_args()

    main(reload=args.reload)
