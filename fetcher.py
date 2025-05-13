# fetcher.py

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import asyncio

from playwright.async_api import async_playwright

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
    Blocking scrape of /search → [{"id": "/watch/...", "name": "..."}...]
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
        href  = a["href"]
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
    Async wrapper around _sync_search.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_search, query)


async def fetch_episodes(anime_path: str) -> list[dict]:
    """
    1) Headless-launch the watch page.
    2) Wait for DOMContentLoaded.
    3) Evaluate window.__NEXT_DATA__.props.pageProps.episodes.
    4) Return [{"episodeId": "...", "number": "...", "title": "..."}...].
    """
    page_path = anime_path.split("?", 1)[0]
    url       = urljoin(HTML_BASE, page_path)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page    = await browser.new_page()

        # load just enough for Next.js to inject __NEXT_DATA__
        await page.goto(url, wait_until="domcontentloaded")

        # grab the whole Next.js data object
        data = await page.evaluate("() => window.__NEXT_DATA__")
        await browser.close()

    # drill in
    props = data.get("props", {}).get("pageProps", {})
    # episodes may live under different keys
    eps_src = props.get("episodes") \
           or props.get("anime", {}).get("episodes") \
           or []

    out = []
    for ep in eps_src:
        eid   = str(ep.get("episodeId") or ep.get("id") or "")
        num   = str(ep.get("episodeNumber") or ep.get("index") or "")
        title = ep.get("title") or ep.get("name") or f"Episode {num}"
        if not eid:
            continue
        out.append({"episodeId": eid, "number": num, "title": title})

    return out


def fetch_tracks(episode_id: str) -> list[dict]:
    """
    Stub for subtitles. Return [] or implement if you have JSON.
    """
    return []


async def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    (Unchanged) headless browser grab of .m3u8 + cookies.
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
        await page.goto(watch_url, wait_until="domcontentloaded")
        await page.reload(wait_until="domcontentloaded")

        if not m3u8_url:
            await browser.close()
            raise RuntimeError("HLS manifest not found")

        cookies    = await ctx.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        await browser.close()

    return [{"url": m3u8_url}], watch_url, cookie_str
