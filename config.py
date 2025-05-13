# config.py

import os
from dotenv import load_dotenv

# Load .env into environment
load_dotenv()

# These must be set in your .env (or real env)
API_ID      = int(os.getenv("API_ID"))
API_HASH    = os.getenv("API_HASH")
BOT_TOKEN   = os.getenv("BOT_TOKEN")

# Session name file for Telethon (defaults to "bot_session.session")
SESSION_NAME = os.getenv("SESSION_NAME", "bot_session")

# In-memory chat-state
STATE = {}
