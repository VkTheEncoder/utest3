import os

# ——— Telegram/API credentials ————————————————————————————————————
# Fill these via environment variables or hard-code (not recommended)
API_ID      = int(os.getenv("API_ID",    "YOUR_API_ID"))
API_HASH    = os.getenv("API_HASH",      "YOUR_API_HASH")
BOT_TOKEN   = os.getenv("BOT_TOKEN",     "YOUR_BOT_TOKEN")

# Session name for Telethon’s .session file
SESSION_NAME = os.getenv("SESSION_NAME", "bot_session")

# In-memory storage for per-chat state (search results, queues, etc.)
STATE = {}
