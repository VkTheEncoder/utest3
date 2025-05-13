# main.py

import asyncio
import logging

from telethon import TelegramClient
from telethon.errors import FloodWaitError

from config import TELETHON, BOT_TOKEN
from handlers import register_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Initialize the client from your config (API_ID, API_HASH, session name)
    client = TelegramClient(**TELETHON)

    # Register your handlers
    await register_handlers(client)

    # Try starting the bot, retrying on FloodWaitError
    while True:
        try:
            await client.start(bot_token=BOT_TOKEN)
            logger.info("Bot started successfully")
            break
        except FloodWaitError as e:
            wait = getattr(e, 'seconds', None) or getattr(e, 'retry_after', None)
            if not wait:
                # fallback if the exception doesn’t carry a wait time
                wait = 60
            logger.warning(f"Flood wait of {wait}s encountered. Retrying in {wait}s...")
            await asyncio.sleep(wait)

    # Run until disconnected (this keeps the bot alive)
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
