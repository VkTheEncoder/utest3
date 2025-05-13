# fetcher.py

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

HTML_BASE = "https://hianimez.to"


async def fetch_hls_manifest(episode_url: str):
    """
    1) Launch headless Chromium.
    2) Intercept the first response whose URL contains ".m3u8".
    3) Navigate to the episode_url, waiting for DOM load.
    4) wait_for_response will resolve as soon as the HLS manifest is fetched.
    5) Return (m3u8_url, referer, cookie_header_str).
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

        # Kick off navigation (no networkidle to avoid hangs)
        goto = page.goto(episode_url, wait_until="domcontentloaded", timeout=20_000)

        try:
            # Meanwhile, wait for the HLS manifest request to complete
            response = await page.wait_for_response(
                lambda res: ".m3u8" in res.url,
                timeout=20_000
            )
            m3u8_url = response.url
        except PlaywrightTimeout:
            await browser.close()
            raise RuntimeError("Could not intercept HLS manifest URL (.m3u8)")

        # Ensure navigation has finished (best‐effort)
        try:
            await goto
        except PlaywrightTimeout:
            pass

        # Gather cookies for ffmpeg headers
        cookies = await context.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

        await browser.close()

    # referer is simply the watch page URL
    return m3u8_url, episode_url, cookie_str
