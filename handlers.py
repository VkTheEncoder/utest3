import os
import re
import logging
import asyncio

from telethon import events
from telethon.tl.custom import Button

import config
import downloader

# Pre‐compile URL regex
URL_RE = re.compile(r'(https?://\S+)')

async def register_handlers(client):
    @client.on(events.NewMessage(incoming=True, pattern=r'.+'))
    async def on_message(event):
        text = event.message.message or ""
        chat_id = event.chat_id

        # Extract first URL in the message
        m = URL_RE.search(text)
        if not m:
            return  # ignore non‐URL messages

        url = m.group(1).rstrip('.,)')
        safe_name = url.split('/')[-1].split('?')[0]  # fallback filename

        # Choose output filename
        out_dir = os.path.join(config.DOWNLOAD_DIR, chat_id.__str__())
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{safe_name}.mp4")

        status = await event.reply(f"⏳ Downloading… `{url}`", parse_mode="markdown")

        try:
            # Download in thread to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None,
                downloader.download_url,
                url,
                out_path
            )
            # Send the file back
            await client.send_file(
                chat_id,
                out_path,
                caption=f"▶️ Here’s your download:",
                allow_cache=False
            )
        except Exception as e:
            logging.exception("Download failed")
            await client.send_message(chat_id, f"❌ Download error: {e}")
        finally:
            await status.delete()
