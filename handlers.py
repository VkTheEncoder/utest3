import os
import re
import logging
import asyncio

from telethon import events
import config, fetcher, downloader

URL_RE = re.compile(r"https?://hianimez\.to/watch/[^\s]+")

async def register_handlers(client):
    @client.on(events.NewMessage(incoming=True, pattern=URL_RE))
    async def on_message(event):
        url = URL_RE.search(event.text).group(0)
        chat_id = event.chat_id

        # Derive a safe filename
        slug = urlparse(url).path.split("/")[-1]
        ep_num = parse_qs(urlparse(url).query).get("ep", [""])[0]
        safe_name = f"{slug}_ep{ep_num}"

        out_dir = os.path.join(config.DOWNLOAD_DIR, slug)
        os.makedirs(out_dir, exist_ok=True)
        out_mp4 = os.path.join(out_dir, f"{safe_name}.mp4")

        status = await event.reply(f"⏳ Starting download for `{ep_num}`…", parse_mode="markdown")

        try:
            # 1) Get manifest + cookies via fetcher
            m3u8, referer, cookies = await fetcher.fetch_hls_manifest(url)

            # 2) Download via ffmpeg in a thread
            await asyncio.get_event_loop().run_in_executor(
                None,
                downloader.remux_hls,
                m3u8, referer, cookies, out_mp4
            )

            # 3) Send back the file
            await client.send_file(chat_id, out_mp4, caption="▶️ Here you go!")
        except Exception as e:
            logging.exception("Download failed")
            await event.reply(f"❌ Error: {e}")
        finally:
            await status.delete()
