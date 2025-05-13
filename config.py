import os
from dotenv import load_dotenv

load_dotenv()  # read .env

API_ID       = int(os.getenv("API_ID"))
API_HASH     = os.getenv("API_HASH")
BOT_TOKEN    = os.getenv("BOT_TOKEN")
SESSION_NAME = os.getenv("SESSION_NAME", "utest3_session")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
