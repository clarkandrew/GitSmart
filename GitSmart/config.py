import os
import configparser
import logging

# Initialize the config parser
config = configparser.ConfigParser()

# We assume 'config.ini' is one level up from this file
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.ini")
config.read(CONFIG_PATH)

# Load configurations
AUTH_TOKEN = config["API"]["auth_token"]
API_URL = config["API"]["api_url"]
MODEL = config["API"]["model"]
MAX_TOKENS = int(config["API"]["max_tokens"])
TEMPERATURE = float(config["API"]["temperature"])
USE_EMOJIS = True if config["PROMPTING"]["use_emojis"] in ["true", True] else False
DEBUG = True if config["APP"]["debug"] in ["true", True] else False

# Initialize logger
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
