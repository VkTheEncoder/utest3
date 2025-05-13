import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

HTML_BASE = "https://hianimez.to"


async def fetch_hls_manifest(episode_url: str):
    """
    1) Launch headless Chromium.
    2) Navigate to the watch URL (networkidle).
    3) Intercept the first .m3u8 response.
    4) Return (m3u8_url, referer, cookie_header_str).
    """
    m3u8_url = None

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

        # Intercept .m3u8 responses
        def capture(response):
            nonlocal m3u8_url
            url = response.url
            if ".m3u8" in url and not m3u8_url:
                m3u8_url = url

        page.on("response", capture)

        # Navigate, wait for JS to load manifest
        try:
            await page.goto(episode_url, wait_until="networkidle", timeout=20_000)
        except PlaywrightTimeout:
            # networkidle can sometimes hang; page is likely usable
            pass

        # Poll for the manifest
        for _ in range(40):  # up to ~20s total
            if m3u8_url:
                break
            await asyncio.sleep(0.5)

        # Gather cookies for ffmpeg
        cookies = await context.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

        await browser.close()

    if not m3u8_url:
        raise RuntimeError("Could not intercept HLS manifest URL (.m3u8)")

    # referer is simply the watch page
    return m3u8_url, episode_url, cookie_str
