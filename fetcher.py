# fetcher.py

import json
import requests
import asyncio
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

HTML_BASE = "https://hianimez.to"
_USER_AGENT = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
}


def _sync_search(query: str) -> list[dict]:
    """
    Blocking HTML scrape of /search for up to 5 results.
    """
    resp = requests.get(
        urljoin(HTML_BASE, "/search"),
        params={"keyword": query},
        headers=_USER_AGENT,
        timeout=10
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    out = []
    for a in soup.find_all("a", href=lambda h: h and h.startswith("/watch/"), limit=5):
        href = a["href"]
        title = (
            (a.find("img", alt=True) or {}).get("alt")
            or a.get("title")
            or a.get_text(strip=True)
        )
        if href and title:
            out.append({"id": href, "name": title.strip()})
    return out


async def search_anime(query: str) -> list[dict]:
    """
    Async wrapper around the blocking _sync_search.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_search, query)


async def fetch_episodes(anime_path: str) -> list[dict]:
    """
    1) Load the watch page in headless Chromium (async).
    2) Extract the <script id="__NEXT_DATA__"> JSON blob.
    3) Parse pageProps to get the episodes array.
    """
    page_path = anime_path.split("?", 1)[0]        # "/watch/raven-...-18168"
    url       = urljoin(HTML_BASE, page_path)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page    = await browser.new_page()

        # Load the page just enough to get the JSON blob
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15_000)
        except PlaywrightTimeout:
            # fall back; maybe scripts are still running
            pass

        # Wait up to 10s for the __NEXT_DATA__ script to appear
        try:
            tag = await page.wait_for_selector("script#__NEXT_DATA__", timeout=10_000)
        except PlaywrightTimeout:
            await browser.close()
            return []

        # Grab its contents and parse JSON
        json_text = await tag.text_content()
        data = json.loads(json_text)

        await browser.close()

    # The Next.js data lives under props.pageProps
    props = data.get("props", {}).get("pageProps", {})

    # Episodes may live under different keys depending on build:
    eps_list = props.get("episodes") \
            or props.get("anime", {}).get("episodes") \
            or []

    out = []
    for ep in eps_list:
        # Next.js often gives episodeId as number or full link
        eid = str(ep.get("episodeId") or ep.get("ep_id") or "")
        num = str(ep.get("episodeNumber") or ep.get("episode") or eid)
        title = ep.get("title") or ep.get("name") or ""
        if not eid:
            continue
        out.append({"episodeId": eid, "number": num, "title": title})

    return out


def fetch_tracks(episode_id: str) -> list[dict]:
    # Subtitle stub (no change)
    return []


async def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    (Unchanged) Headless Chromium capture of the .m3u8 URL + cookies.
    """
    watch_url = f"{HTML_BASE}/watch/{episode_id}"
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx     = await browser.new_context()
        page    = await ctx.new_page()

        m3u8_url = None
        def capture(resp):
            nonlocal m3u8_url
            if resp.url.endswith(".m3u8") and not m3u8_url:
                m3u8_url = resp.url

        page.on("response", capture)
        await page.goto(watch_url, wait_until="networkidle")
        await page.reload(wait_until="networkidle")

        if not m3u8_url:
            await browser.close()
            raise RuntimeError("Could not locate HLS manifest URL")

        cookies = await ctx.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        await browser.close()

    return [{"url": m3u8_url}], watch_url, cookie_str
