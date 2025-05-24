# GitSmart/main.py

import time
import questionary # Added import
import argparse # Added for CLI arguments

from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

from .ui import console, initialize_console # Added initialize_console
from .cli_flow import (
    reset_console,
    get_layout_data_and_panels, # Changed from get_and_display_status
    get_menu_options,
    main_menu_prompt,
    handle_stage_files,
    handle_unstage_files,
    handle_generate_commit,
    handle_review_changes,
    display_commit_summary,
    select_commit,
    print_commit_details,
    summarize_selected_commits,
    handle_push_repo,
    handle_ignore_files,
    select_model
)
from .config import DEFAULT_MODEL, MODEL_CACHE # Removed logger, MODEL, DEBUG as they are not used directly

"""
main.py

- Orchestrates the main application loop using Rich Layout
- Fetches data and panels from cli_flow.get_layout_data_and_panels()
- Displays status and menu in the layout
- Handles user actions
"""

def main():
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="GitSmart CLI - AI Powered Git Helper")
    parser.add_argument("--no-color", action="store_true", help="Disable all color output")
    parser.add_argument("--high-contrast", action="store_true", help="Use high-contrast theme for better accessibility")
    args = parser.parse_args()

    # --- Initialize UI with Flags ---
    # This must be called BEFORE any Rich Console output or cli_flow functions that rely on themed styles.
    initialize_console(no_color=args.no_color, high_contrast=args.high_contrast)
    
    # --- Layout Definition ---
    layout = Layout(name="root")
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=5), # Increased footer size for status_message and prompt
    )
    layout["body"].split_row(
        Layout(name="left_panel", ratio=1), # Ensuring panels take available space
        Layout(name="right_panel", ratio=1)
    )

    # exit_prompted can be handled by questionary or loop break directly
    # global MODEL is not needed as current_model_val is fetched from cache each loop

    while True:
        try:
            current_model_val = MODEL_CACHE.get("last_model", DEFAULT_MODEL)
            reset_console() # Clears console before drawing layout

            diff, unstaged_diff, staged_changes, unstaged_changes, unstaged_panel, staged_panel = get_layout_data_and_panels()

            layout["header"].update(Panel(Text("🚀 GitSmart", style="brand.header", justify="center"), border_style="panel.border")) # Centered header text
            layout["left_panel"].update(unstaged_panel)
            layout["right_panel"].update(staged_panel)

            title, status_message, choices = get_menu_options(current_model_val, staged_changes, unstaged_changes)
            
            # Ensure status_message is a string and suitable for Panel content
            if not isinstance(status_message, str):
                status_message = str(status_message) # Basic conversion if it's not a string

            footer_prompt_text = "\nSelect an action. (Use ↑/↓, Enter to select, or type 'q' then Enter to quit in prompt)"
            # The main_menu_prompt itself will show its own instructions.
            # The footer here is more for overall status and app-level quit instructions.
            # However, main_menu_prompt doesn't directly support 'q' to quit.
            # The "Exit" option in the menu is the primary way.
            
            footer_content_text = f"{status_message}\n{title}" # Combining status and prompt title for context
            layout["footer"].update(Panel(Text(footer_content_text, justify="left"), title="[dim]Status & Controls[/dim]", border_style="panel.border", title_align="left"))

            console.print(layout)
            
            # main_menu_prompt will now be displayed after the layout is printed
            # This is a slight change from typical Rich applications where prompt might be part of the layout.
            # For questionary, it takes over the terminal temporarily.
            action = main_menu_prompt(current_model_val, "Select an action:", choices) # Title for main_menu_prompt is simplified

            if action is None or action == "Exit": # 'q' is not handled by main_menu_prompt, 'Exit' option is the way
                reset_console()
                console.print(Panel(Text("👋 Goodbye!", justify="center", style="bold #A259FF"), border_style="panel.border", padding=(1,5)))
                break
            
            # Action Handling
            # Adding console.clear() before actions that take over the screen
            # and questionary.press_any_key_to_continue for better UX
            if "Stage Files" in action:
                handle_stage_files(unstaged_changes) # This function might print its own status
                # Loop will redraw status
            elif "Unstage Files" in action:
                handle_unstage_files(staged_changes) # This function might print its own status
                # Loop will redraw status
            elif "Generate Commit" in action:
                console.clear()
                handle_generate_commit(current_model_val, diff, staged_changes)
                questionary.press_any_key_to_continue("Press any key to return...").ask()
            elif action == "Review Changes":
                console.clear()
                handle_review_changes(staged_changes, unstaged_changes, diff, unstaged_diff)
                questionary.press_any_key_to_continue("Press any key to return...").ask()
            elif action == "View Commit History":
                console.clear()
                commits = display_commit_summary() # display_commit_summary already prints
                if commits:
                    selected = select_commit(commits) # select_commit is a prompt
                    if selected:
                        console.clear() # Clear before showing details
                        print_commit_details(selected) # print_commit_details prints
                questionary.press_any_key_to_continue("Press any key to return...").ask()
            elif action == "Summarize Commits":
                console.clear()
                summarize_selected_commits() # This function prints
                questionary.press_any_key_to_continue("Press any key to return...").ask()
            elif action == "Push Repo":
                console.clear()
                handle_push_repo() # This function prints
                questionary.press_any_key_to_continue("Press any key to return...").ask()
            elif action == "Ignore Files":
                console.clear()
                handle_ignore_files() # This function prints
                questionary.press_any_key_to_continue("Press any key to return...").ask()
            elif action == "Select Model":
                console.clear()
                new_model = select_model() # This function prompts and prints
                # console.print(f"Model set to: {new_model}") # select_model might already print confirmation
                questionary.press_any_key_to_continue(f"Model set to: {new_model}. Press any key to return...").ask()
            else:
                # Fallback for actions not explicitly handled, or if main_menu_prompt returns unexpected string
                console.clear()
                console.print(Panel(Text(f"Action '{action}' not fully integrated or unknown.", justify="center"), border_style="status.warning"))
                time.sleep(2) # Increased sleep time

        except KeyboardInterrupt:
            # Simplified Ctrl+C handling, directly exits.
            reset_console()
            console.print(Panel(Text("👋 Goodbye! (Interrupted by user)", justify="center", style="bold #A259FF"), border_style="panel.border", padding=(1,5)))
            break
        except Exception as e:
            console.print_exception()
            console.print(Panel(Text(f"An unexpected error occurred: {e}\nPlease report this issue.", style="status.bad"), title="[bold red]Error[/bold red]"))
            questionary.press_any_key_to_continue("Press any key to continue...").ask()
            # Decide whether to break or continue
            # break


if __name__ == "__main__":
    main() # Directly call main, removed entry_point and argparse
