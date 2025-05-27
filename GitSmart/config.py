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
AUTO_REFRESH = config["APP"]["auto_refresh"].lower() == "true"
AUTO_REFRESH_INTERVAL = int(config["APP"]["auto_refresh_interval"])
TOKEN_INCREMENT = 3000

# Initialize logger
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
