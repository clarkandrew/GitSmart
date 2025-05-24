import os
import configparser
import logging
from diskcache import Cache

# Initialize the config parser
config = configparser.ConfigParser()

# We assume 'config.ini' is one level up from this file
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.ini")
config.read(CONFIG_PATH)

# Directory for persistent storage
history_dir = ".gitsmart"
MODEL_CACHE = Cache(f"{history_dir}/model_cache")

# Load configurations
AUTH_TOKEN = config["API"]["auth_token"]
API_URL = config["API"]["api_url"]

# Check for cached model first, fallback to config if not found
MODEL = MODEL_CACHE.get("last_model", config["API"]["model"])
DEFAULT_MODEL = config["API"]["model"]
MAX_TOKENS = int(config["API"]["max_tokens"])
TEMPERATURE = float(config["API"]["temperature"])
USE_EMOJIS = config["PROMPTING"]["use_emojis"].lower() == "true"
DEBUG = config["APP"]["debug"].lower() == "true"
TOKEN_INCREMENT = 3000

# Initialize logger
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Brand palette ---
ACCENT_COLOR  = "#A259FF"      # purple highlight
SUCCESS_COLOR = "ansigreen"    # green for additions
ERROR_COLOR   = "ansired"      # red for deletions
WARNING_COLOR = "ansiyellow"   # yellow for warnings
SURFACE_COLOR = "#1C1C1C"      # If needed for specific panel backgrounds
TEXT_COLOR    = "white"
COMMENT_COLOR = "grey70"       # For dimmer text, like commit hashes or instructions

# --- High Contrast Brand palette ---
HC_ACCENT_COLOR  = "bright_magenta"
HC_SUCCESS_COLOR = "bright_green"
HC_ERROR_COLOR   = "bright_red"
HC_WARNING_COLOR = "bright_yellow" # Added for high contrast warnings
HC_SURFACE_COLOR = "black"
HC_TEXT_COLOR    = "white"
HC_COMMENT_COLOR = "bright_black" # ANSI name for dark grey / silver

# --- Prompt-toolkit token names ---
TOKEN_TEXT      = "class:text"
TOKEN_ADD       = "class:addition"
TOKEN_DEL       = "class:deletion"
TOKEN_HASH      = "class:hash"
TOKEN_PATH      = "class:path"
TOKEN_DIM       = "class:dim"

from rich.theme import Theme

def get_rich_theme(high_contrast: bool = False):
    accent = HC_ACCENT_COLOR if high_contrast else ACCENT_COLOR
    success = HC_SUCCESS_COLOR if high_contrast else SUCCESS_COLOR
    error = HC_ERROR_COLOR if high_contrast else ERROR_COLOR
    text = HC_TEXT_COLOR if high_contrast else TEXT_COLOR
    warning = HC_WARNING_COLOR if high_contrast else WARNING_COLOR
    # surface = HC_SURFACE_COLOR if high_contrast else SURFACE_COLOR # Not currently used in theme dict

    return Theme({
        "brand.header":   f"bold {accent}",
        "panel.border":   accent,
        "diff.add":       success,
        "diff.del":       error,
        "commit.hash":    "bright_cyan" if high_contrast else "cyan",
        "commit.msg":     text,
        "status.good":    success,
        "status.bad":     error,
        "status.warning": warning,
        # Add other styles as they become necessary from the issue description
    })

from questionary import Style

def configure_questionary_style(high_contrast: bool = False):
    accent = HC_ACCENT_COLOR if high_contrast else ACCENT_COLOR
    success = HC_SUCCESS_COLOR if high_contrast else SUCCESS_COLOR
    error = HC_ERROR_COLOR if high_contrast else ERROR_COLOR
    text = HC_TEXT_COLOR if high_contrast else TEXT_COLOR
    comment = HC_COMMENT_COLOR if high_contrast else COMMENT_COLOR
    
    # Define base styles that might change with high_contrast
    hash_style = "bright_cyan" if high_contrast else "cyan"
    path_style = "bright_magenta" if high_contrast else "magenta" # Using bright_magenta for HC path

    return Style([
        (TOKEN_TEXT,   f"fg:{text}"),
        (TOKEN_ADD,    f"fg:{success} bold"),
        (TOKEN_DEL,    f"fg:{error} bold"),
        (TOKEN_HASH,   f"fg:{hash_style}"),
        (TOKEN_PATH,   f"fg:{path_style}"),
        (TOKEN_DIM,    f"fg:{comment}"),
        # global questionary style from issue
        ("qmark",        f"fg:{accent} bold"),
        ("pointer",      f"fg:{accent} bold"),
        ("highlighted",  f"fg:{accent} bold"), # Consider if background changes are needed for HC (e.g. bg:white fg:black)
        ("selected",     f"fg:{accent}"),
        ("instruction",  f"fg:{comment}"),
        # Add other questionary style components as needed
    ])
