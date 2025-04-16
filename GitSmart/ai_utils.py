import time
import json
import re
import requests
import questionary
from typing import Optional

from .ui import console, configure_questionary_style
from .config import (
    AUTH_TOKEN, API_URL, MODEL, MAX_TOKENS, TEMPERATURE,
    USE_EMOJIS, logger
)
from .git_utils import parse_diff
from .ui import printer
from .prompts import SYSTEM_MESSAGE, USER_MSG_APPENDIX, SYSTEM_MESSAGE_EMOJI, SUMMARIZE_COMMIT_PROMPT, USER_MSG_APPENDIX_EMOJI

# If an actual "count_tokens_in_string" is needed, import from a local module:
from count_tokens import count_tokens_in_string

# Import the new LLM helper function.
from .llm import get_chat_completion
def extract_from_codeblocks(text: str) -> str:
    """
    Extract text from code blocks enclosed within triple backticks or more.
    """
    pattern = r"```commit(?:`{3,})?(.*?)```(?:`{3,})?"
    matches = re.findall(pattern, text, re.DOTALL)
    return "\n".join(matches)
def extract_tag_value(text: str, tag: str) -> str:
    """
    Extract the value enclosed within specified XML-like or bracket-like tags, case-insensitive.
    """
    try:
        tag_lower = tag.lower()
        patterns = [
            rf"<({tag_lower})>(.*?)</\1>",
            rf"[({tag_lower})\](.*?)[/\1\]"
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(2).strip()
        return ""
    except Exception as e:
        console.log(f"Could not extract `{tag}` because {str(e)}\n")
        return ""

def truncate_diff(diff: str, system_message: str, user_msg_appendix: str, max_tokens: int) -> str:
    """
    Truncate the diff to ensure total token count doesn't exceed max_tokens.
    """
    from math import floor, ceil
    def count_tokens(text: str) -> int:
        return len(text.split())
    total_allowed_tokens = max_tokens - count_tokens(system_message) - count_tokens(user_msg_appendix)
    current_tokens = count_tokens(diff)
    if current_tokens <= total_allowed_tokens:
        return diff
    logger.info(f"Truncating diff from {current_tokens} to {total_allowed_tokens} tokens.")
    diff_lines = diff.splitlines()
    avg_tokens_per_line = current_tokens / max(len(diff_lines), 1)
    lines_to_keep = floor(total_allowed_tokens / avg_tokens_per_line)
    lines_to_keep = max(1, lines_to_keep)
    if lines_to_keep < len(diff_lines):
        head = diff_lines[: max(floor(lines_to_keep / 2), 1)]
        tail = diff_lines[-max(ceil(lines_to_keep / 2), 1) :]
        truncated_diff = "\n".join(head + ["..."] + tail)
        logger.debug("Diff truncated to preserve context at both ends.")
    else:
        truncated_diff = diff
    final_tokens = count_tokens(system_message + truncated_diff + user_msg_appendix)
    if final_tokens > max_tokens:
        logger.warning(
            f"Truncated diff still exceeds max tokens ({final_tokens}/{max_tokens}). "
            "Further truncation may be required."
        )
    return truncated_diff

def generate_commit_message(MODEL: str, diff: str) -> str:
    """
    Generate a commit message using an external service.
    Retries until a properly formatted commit message is received or max retries is reached.
    """
    logger.debug(USE_EMOJIS)
    INSTRUCT_PROMPT = SYSTEM_MESSAGE_EMOJI if USE_EMOJIS else SYSTEM_MESSAGE
    logger.debug("Entering generate_commit_message function.")

    messages = [
        {"role": "system", "content": INSTRUCT_PROMPT},
        {"role": "user", "content": "START BY CAREFULLY REVIEWING THE FOLLOWING DIFF:\n" + diff + (USER_MSG_APPENDIX if not USE_EMOJIS else USER_MSG_APPENDIX_EMOJI)},
    ]

    request_tokens = count_tokens_in_string(INSTRUCT_PROMPT + diff + USER_MSG_APPENDIX)
    max_retries = 5
    retry_count = 0

    while retry_count < max_retries:
        if request_tokens > MAX_TOKENS:
            logger.warning(f"Request exceeds max tokens ({request_tokens}/{MAX_TOKENS})\nTruncating...")
            truncated_diff = truncate_diff(diff, INSTRUCT_PROMPT, USER_MSG_APPENDIX, MAX_TOKENS)
            messages = [
                {"role": "system", "content": INSTRUCT_PROMPT},
                {"role": "user", "content": truncated_diff + USER_MSG_APPENDIX}
            ]
            request_tokens = count_tokens_in_string(INSTRUCT_PROMPT + truncated_diff + USER_MSG_APPENDIX)
            logger.info(f"After truncation, request tokens are {request_tokens}/{MAX_TOKENS}.")

        if request_tokens > MAX_TOKENS:
            warning_message = (
                f"The generated commit message exceeds the maximum token limit of {MAX_TOKENS} tokens. "
                "Do you want to proceed?"
            )
            if not questionary.confirm(warning_message, style=configure_questionary_style()).ask():
                console.print("[bold red]Commit generation aborted by user.[/bold red]")
                return ""

        deletions = sum(change["deletions"] for change in parse_diff(diff))
        additions = sum(change["additions"] for change in parse_diff(diff))
        logger.debug(f"deletions: {deletions}, additions: {additions}")
        if additions > 0:
            if deletions > 2 * additions:
                warning_message = (
                    f"The commit message indicates a high number of deletions ({deletions}) "
                    f"relative to additions ({additions}). Do you want to proceed?"
                )
                if not questionary.confirm(warning_message, style=configure_questionary_style()).ask():
                    console.print("[bold red]Commit generation aborted by user.[/bold red]")
                    return ""
        elif deletions > 0:
            warning_message = (
                f"The commit message indicates {deletions} deletions with no additions. "
                "Do you want to proceed?"
            )
            if not questionary.confirm(warning_message, style=configure_questionary_style()).ask():
                console.print("[bold red]Commit generation aborted by user.[/bold red]")
                return ""

        try:
            with console.status("[bold green]Analyzing changes to staged files...[/bold green]") as status:
                prepend_msg = f"> Analyzing changes to staged files with {clean_model_name(MODEL)} ({request_tokens} tokens)"
                status.update(prepend_msg)
                # Stream the commit message from the LLM provider using the new helper.
                commit_response = get_chat_completion(
                    model=MODEL,
                    messages=messages,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    stream=True,
                    timeout=60,
                    status_callback=lambda text: status.update(text)
                )
                if "</think>" in commit_response:
                    commit_response = commit_response.split("</think>")[1]

                commit_message_text = None
                if "<COMMIT_MESSAGE>" in commit_response:
                    commit_message_text = extract_tag_value(commit_response, "COMMIT_MESSAGE")
                elif "```commit" in commit_response:
                    commit_message_text = extract_from_codeblocks(commit_response)

                if commit_message_text:
                    return commit_message_text
                else:
                    logger.error("Could not extract COMMIT_MESSAGE tags. Retrying...")
                    console.print(f"[bold red]Commit message format incorrect.\n\n```\n\n{commit_response}\n\n```\n\nRetrying...[/bold red]")
                    retry_count += 1
                    time.sleep(2)
        except Exception as e:
            logger.error(f"Failed to generate commit message: {e}")
            console.print(f"[bold red]Failed to generate commit message: {e}[/bold red]")
            retry_count += 1
            if retry_count < max_retries:
                retry_prompt = questionary.confirm(
                    "Failed to generate commit message. Would you like to retry?",
                    style=configure_questionary_style()
                ).ask()
                if not retry_prompt:
                    console.print("[bold red]Commit generation aborted by user.[/bold red]")
                    return ""
    console.print("[bold red]Failed to generate a properly formatted commit message after multiple attempts.[/bold red]")
    return ""

def generate_summary(text: str) -> Optional[str]:
    """
    Generate a summary for the provided text using the external API.
    """
    try:
        messages = [
            {"role": "system", "content": SUMMARIZE_COMMIT_PROMPT},
            {"role": "user", "content": text}
        ]
        with console.status("[bold green]Analyzing changes to staged files...[/bold green]") as status:
            prepend_msg = f"Sending {count_tokens_in_string(text)} tokens to "
            status.update(f"{prepend_msg} {clean_model_name(MODEL)} ({TEMPERATURE})")
            summary = get_chat_completion(
                model=MODEL,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                stream=True,
                timeout=60,
                status_callback=lambda text: status.update(text)
            )
            if summary:
                logger.info("Summary generated successfully.")
                return summary
            else:
                logger.error("Could not extract summary text.")
                console.print("[bold red]Summary format incorrect.[/bold red]")
                return None
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        console.print(f"[bold red]Failed to generate summary: {e}[/bold red]")
        return None

def clean_model_name(model_name):
    """
    Clean or strip unwanted tokens from the model's display name.
    """
    model_name = model_name.replace("local|", "").replace("|{IP}|o", "").replace("local", "")
    return model_name
