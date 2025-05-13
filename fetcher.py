# fetcher.py

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

HTML_BASE = "https://hianimez.to"


async def fetch_hls_manifest(episode_url: str):
    """
    1) Launch headless Chromium.
    2) Navigate to the watch URL (DOMContentLoaded).
    3) Use a Future + page.on('response') to catch the first '.m3u8' URL.
    4) Return (m3u8_url, referer, cookie_header_str).
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        m3u8_future = asyncio.get_event_loop().create_future()

        # Listener for any .m3u8 response
        def _capture(response):
            url = response.url
            if ".m3u8" in url and not m3u8_future.done():
                m3u8_future.set_result(url)

        page.on("response", _capture)

        # Start navigation (DOMContentLoaded)
        goto_task = asyncio.create_task(
            page.goto(episode_url, wait_until="domcontentloaded", timeout=20_000)
        )

        try:
            # Wait up to 20s for the manifest URL to be intercepted
            m3u8_url = await asyncio.wait_for(m3u8_future, timeout=20)
        except asyncio.TimeoutError:
            await browser.close()
            raise RuntimeError("Could not intercept HLS manifest URL (.m3u8)")

        # Ensure navigation finishes
        try:
            await goto_task
        except PlaywrightTimeout:
            pass

        # Collect cookies for ffmpeg
        cookies = await context.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

        await browser.close()

    return m3u8_url, episode_url, cookie_str
