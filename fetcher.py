# fetcher.py

import requests
import asyncio
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Base URLs
HTML_BASE = "https://hianimez.to"
API_BASE  = "https://hianime-api-production.up.railway.app/api/v1"

# A real browser UA
_USER_AGENT = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
}


def _sync_search(query: str) -> list[dict]:
    """
    Blocking search scrape: GET /search?keyword=…    
    """
    url = urljoin(HTML_BASE, "/search")
    resp = requests.get(url, params={"keyword": query}, headers=_USER_AGENT, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for a in soup.find_all("a", href=lambda h: h and h.startswith("/watch/"), limit=5):
        href = a["href"]
        # title from img@alt, then @title, then text
        title = (
            (a.find("img", alt=True) or {}).get("alt")
            or a.get("title")
            or a.get_text(strip=True)
        )
        if href and title:
            results.append({"id": href, "name": title.strip()})
    return results


async def search_anime(query: str) -> list[dict]:
    """
    Async wrapper for the blocking _sync_search.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_search, query)


def _sync_fetch_episodes(anime_path: str) -> list[dict]:
    """
    Blocking fetch of episodes via the JSON API:
      GET https://hianime-api-production.up.railway.app/api/v1/episodes/:id
    where :id is the slug after /watch/ and before ?ep=
    :contentReference[oaicite:0]{index=0}
    """
    # extract anime ID (e.g. "raven-of-the-inner-palace-18168")
    slug = anime_path.split("/watch/", 1)[1].split("?", 1)[0]
    url  = f"{API_BASE}/episodes/{slug}"
    resp = requests.get(url, headers=_USER_AGENT, timeout=10)
    resp.raise_for_status()

    data = resp.json()
    episodes = []
    for ep in data.get("episodes", []):
        episodes.append({
            "episodeId": ep["episodeId"],                     # "/watch/...-18168?ep=12345"
            "number":    str(ep["episodeNumber"]),             # "1", "2", …
            "title":     ep.get("title", "")                   # optional title
        })
    return episodes


async def fetch_episodes(anime_path: str) -> list[dict]:
    """
    Async wrapper for the blocking _sync_fetch_episodes.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch_episodes, anime_path)


def fetch_tracks(episode_id: str) -> list[dict]:
    """
    Stub for subtitle tracks. Return [] or implement your JSON endpoint.
    """
    return []


async def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    (Unchanged) use Playwright to grab the live .m3u8 + cookies.
    """
    watch_url = f"{HTML_BASE}/watch/{episode_id}"
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page    = await context.new_page()

        m3u8_url = None
        def capture(response):
            nonlocal m3u8_url
            if response.url.endswith(".m3u8") and m3u8_url is None:
                m3u8_url = response.url

        page.on("response", capture)
        await page.goto(watch_url, wait_until="networkidle")
        await page.reload(wait_until="networkidle")

        if not m3u8_url:
            await browser.close()
            raise RuntimeError("Could not locate HLS manifest URL")

        cookies = await context.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        await browser.close()

    return [{"url": m3u8_url}], watch_url, cookie_str
