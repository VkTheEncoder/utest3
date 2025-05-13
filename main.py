import asyncio, logging
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

    while True:
        try:
            await client.start(bot_token=config.BOT_TOKEN)
            logger.info("Bot started!")
            break
        except FloodWaitError as e:
            wait = getattr(e, "seconds", 60)
            logger.warning(f"Flood wait {wait}s; sleeping…")
            await asyncio.sleep(wait)

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
