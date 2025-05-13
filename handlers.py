# handlers.py

import os
import re
import logging
import asyncio

from urllib.parse import urlparse, parse_qs
from telethon import events

import config, fetcher, downloader

# Match any HiAnimez watch‐page URL
URL_RE = re.compile(r"(https?://hianimez\.to/watch/[^\s]+)")

async def register_handlers(client):
    @client.on(events.NewMessage(incoming=True, pattern=URL_RE))
    async def on_message(event):
        text = event.text or ""
        chat_id = event.chat_id

        # Extract the URL
        m = URL_RE.search(text)
        if not m:
            return
        url = m.group(1)

        # Derive filename from path + ep query
        parsed = urlparse(url)
        slug = parsed.path.split("/")[-1]                    # e.g. "raven-of-...-18168"
        ep_num = parse_qs(parsed.query).get("ep", [""])[0]   # e.g. "94361"
        filename = f"{slug}_ep{ep_num}.mp4"

        out_dir = os.path.join(config.DOWNLOAD_DIR, slug)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, filename)

        status = await event.reply(f"⏳ Starting download for `{ep_num}`…", parse_mode="markdown")

        try:
            # 1) Spin up Playwright + intercept the real .m3u8 manifest
            m3u8_url, referer, cookies = await fetcher.fetch_hls_manifest(url)

            # 2) Download/remux via ffmpeg in a background thread
            await asyncio.get_event_loop().run_in_executor(
                None,
                downloader.remux_hls,
                m3u8_url,
                referer,
                cookies,
                out_path
            )

            # 3) Send the MP4 back to the user
            await client.send_file(chat_id, out_path, caption="▶️ Here you go!")
        except Exception as e:
            logging.exception("Download failed")
            await event.reply(f"❌ Download error: {e}")
        finally:
            await status.delete()
