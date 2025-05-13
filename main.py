import asyncio
import logging

from telethon import TelegramClient
from telethon.errors import FloodWaitError

import config
from handlers import register_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # 1) Create the TelegramClient using config values
    client = TelegramClient(
        config.SESSION_NAME,
        config.API_ID,
        config.API_HASH
    )

    # 2) Register all your handlers (search, download, etc.)
    await register_handlers(client)

    # 3) Start & sign in the bot, retrying on FloodWaitError
    while True:
        try:
            await client.start(bot_token=config.BOT_TOKEN)
            logger.info("Bot started successfully")
            break
        except FloodWaitError as e:
            # Extract wait time, default to 60s if missing
            wait = getattr(e, "seconds", None) or getattr(e, "retry_after", 60)
            logger.warning(f"Flood-wait: sleeping for {wait}s before retry...")
            await asyncio.sleep(wait)

    # 4) Keep the bot running until you Ctrl+C
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
