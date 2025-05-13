import asyncio
import logging

from telethon import TelegramClient
from telethon.errors import FloodWaitError

import config
from handlers import register_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    client = TelegramClient(
        config.SESSION_NAME,
        config.API_ID,
        config.API_HASH
    )
    await register_handlers(client)

    # Handle FloodWait on startup
    while True:
        try:
            await client.start(bot_token=config.BOT_TOKEN)
            logger.info("Bot started successfully")
            break
        except FloodWaitError as e:
            wait = getattr(e, "seconds", None) or getattr(e, "retry_after", 60)
            logger.warning(f"Flood wait {wait}s; retrying...")
            await asyncio.sleep(wait)

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
