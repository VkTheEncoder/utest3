import os
from dotenv import load_dotenv

# Load .env into os.environ
load_dotenv()

# Required Telegram credentials
API_ID      = int(os.getenv("API_ID"))
API_HASH    = os.getenv("API_HASH")
BOT_TOKEN   = os.getenv("BOT_TOKEN")

# Session filename prefix
SESSION_NAME = os.getenv("SESSION_NAME", "bot_session")

# Where to save downloads
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
