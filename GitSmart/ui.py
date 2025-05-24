# GitSmart/ui.py

import os
import sys
import re
import time
import json
import logging
import questionary

from rich.console import Console
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.padding import Padding
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.align import Align

from GitSmart.config import get_rich_theme, configure_questionary_style

"""
ui.py

- Houses the Rich console + styling
- Provides a StyledCLIPrinter class for uniform message printing
- Defines a questionary style for cohesive CLI prompts
"""

# --- Global Accessibility Flags ---
NO_COLOR_MODE = False
HIGH_CONTRAST_MODE = False

# Initial console and printer, will be updated by initialize_console
# This ensures they exist at module load time for any early imports,
# but will be configured properly before significant UI work.
console = Console() 
printer = None # Will be set in initialize_console

def initialize_console(no_color: bool, high_contrast: bool):
    global console, printer, NO_COLOR_MODE, HIGH_CONTRAST_MODE
    
    NO_COLOR_MODE = no_color
    HIGH_CONTRAST_MODE = high_contrast
    
    # Re-initialize the console with the correct theme and no_color setting
    console = Console(theme=get_rich_theme(high_contrast=HIGH_CONTRAST_MODE), no_color=NO_COLOR_MODE)
    
    # Re-initialize the printer with the new console instance
    printer = StyledCLIPrinter(console)

class StyledCLIPrinter:
    """
    A helper class to print styled messages (info, error, warnings) using Rich.
    """
    def __init__(self, console: Console):
        self.console = console

    def print_message(self, message: str, style: str, title=None):
        content = Text(message, style=style) # Style here is now a theme style name
        panel = Panel(
            content,
            title=title,
            border_style="panel.border", # Use theme style for border
            padding=(1, 2)
            # PANEL_STYLE is removed, assuming background is handled by theme or transparent
        ) if title else content
        self.console.print(panel)

    def print_error(self, message: str, title: str = "Error"):
        self.print_message(message, "status.bad", title) # Use theme style

    def print_warning(self, message: str, title: str = "Warning"):
        self.print_message(message, "status.warning", title) # Use theme style

    def print_success(self, message: str, title: str = "Success"):
        self.print_message(message, "status.good", title) # Use theme style

    def print_divider(self, title: str = ""):
        """
        Print a divider line (Rich rule).
        """
        self.console.print()
        # Use a theme style for the rule, e.g., "panel.border" or a specific "rule.line"
        self.console.rule(title, style="panel.border")
        self.console.print()

# printer is initialized after StyledCLIPrinter class definition, and then re-initialized in initialize_console
# This initial printer is a placeholder if something tries to use it before initialize_console is called.
# However, initialize_console should be called early in main.py.
if printer is None: # Ensure printer is always initialized, even if initialize_console hasn't run
    printer = StyledCLIPrinter(console)


def create_styled_table(title=None, clean=False) -> Table:
    """
    Create a Rich table with optional styling.
    """
    padding = (0, 1) if clean else (2, 2)
    # Use theme style for header, e.g., "brand.header"
    header_style_to_use = None if clean else "brand.header"
    return Table(
        show_header=False,
        header_style=header_style_to_use,
        border_style=None, # Or a theme style like "table.border" if defined
        show_lines=False,
        box=None,
        padding=padding,
        title=title,
        expand=clean
    )

# The local configure_questionary_style function is removed.
# The one from GitSmart.config will be used directly in cli_flow.py or other places.
