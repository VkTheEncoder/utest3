import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse, parse_qs

HTML_BASE = "https://hianimez.to"

async def fetch_hls_manifest(episode_url: str):
    """
    1) Headless‐launch the watch page.
    2) Wait for the <video> element & click play.
    3) Intercept the first .m3u8 request.
    4) Return (m3u8_url, referer, cookie_header_str).
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ))
        page = await context.new_page()
        m3u8_url = None

        # Listen for manifest requests
        page.on("request", lambda req: _capture_m3u8(req, lambda u: globals().update(m3u8_candidate=u)))

        # Navigate
        await page.goto(episode_url, wait_until="domcontentloaded")

        # Wait for video element
        await page.wait_for_selector("video", timeout=10_000)

        # Try clicking “play” if needed
        try:
            await page.click("button.ytp-play-button", timeout=2_000)
        except:
            pass

        # Poll until we get a .m3u8 or timeout
        for _ in range(30):
            if m3u8_url:
                break
            await asyncio.sleep(0.5)
        await browser.close()

    if not m3u8_url:
        raise RuntimeError("Could not intercept .m3u8 URL")

    # Build cookie header
    cookies = await context.cookies()
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    return m3u8_url, episode_url, cookie_str


def _capture_m3u8(req, setter):
    url = req.url
    if url.endswith(".m3u8"):
        setter(url)
