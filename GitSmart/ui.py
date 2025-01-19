import os
import re
import sys
import time
import json
import logging
from rich.console import Console, Group
from rich.syntax import Syntax
from rich.align import Align
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich.padding import Padding
from rich.markdown import Markdown

from questionary import Style, Choice
import questionary

# Import config to get THEME, DEBUG, logger, etc. if stored or override them here
from .config import logger

"""
This module provides a styled console using Rich, plus utility
functions for printing messages and creating standardized UI elements.
"""

# [UI Enhancement] Introduce colorblind-safe or more cohesive palette
THEME = {
    "primary": "#FFFFFF",
    "secondary": "#6AD0FF",
    "accent": "#6AD0FF",
    "success": "#96DF71",
    "error": "#D62828",
    "warning": "#F2BB05",
    "background": "#1E1F26",
    "text": "#E6E6E6"
}

# Panel/border styles
PANEL_STYLE = f"bold {THEME['text']} on {THEME['background']}"
BORDER_STYLE = THEME["accent"]
HEADER_STYLE = f"bold {THEME['primary']}"

# Initialize a Rich console instance for logging and output
console = Console()

class StyledCLIPrinter:
    """
    A class to handle styled printing to the console using Rich.
    Provides unified methods for standard info, warning, error, etc.
    """
    def __init__(self, console: Console):
        self.console = console

    def print_message(self, message: str, style: str, title=None):
        """
        Print a styled message to the console.
        """
        content = Text(message, style=style)
        panel = Panel(
            content,
            title=title,
            border_style=BORDER_STYLE,
            style=PANEL_STYLE,
            padding=(1, 2)
        ) if title else content
        self.console.print(panel)

    def print_error(self, message: str, title: str = "Error"):
        self.print_message(message, f"bold {THEME['error']}", title)

    def print_warning(self, message: str, title: str = "Warning"):
        self.print_message(message, f"bold {THEME['warning']}", title)

    def print_success(self, message: str, title: str = "Success"):
        self.print_message(message, f"bold {THEME['success']}", title)

    def print_divider(self, title: str = ""):
        """
        Print a divider line to the console using Rich rule.
        """
        self.console.print()
        self.console.rule(title, style=f"{THEME['primary']}")
        self.console.print()

printer = StyledCLIPrinter(console)

def create_styled_table(title=None, clean=False) -> Table:
    """
    Create a styled table for displaying data in the console.
    """
    padding = (0, 1) if clean else (2, 2)
    return Table(
        show_header=False,
        header_style=None if clean else HEADER_STYLE,
        border_style=None,
        show_lines=False,
        box=None,
        padding=padding,
        title=title,
        expand=clean
    )

def configure_questionary_style():
    """
    Configure the style for questionary prompts based on THEME.
    """
    return questionary.Style([
        ("qmark", f'fg:{THEME["accent"]} bold'),
        ("question", f'fg:{THEME["primary"]} bold'),
        ("answer", f'fg:{THEME["success"]} bold'),
        ("pointer", f'fg:{THEME["accent"]} bold'),
        ("highlighted", f'fg:{THEME["accent"]} bold'),
        ("selected", f'fg:{THEME["secondary"]} bold'),
        ("separator", f'fg:{THEME["secondary"]}'),
        ("instruction", f'fg:{THEME["text"]}'),
    ])
