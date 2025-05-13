# fetcher.py

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "https://hianimez.to"
# Reusable User-Agent header
_USER_AGENT = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
}


def _sync_search(query: str) -> list[dict]:
    """
    Blocking helper: scrape /search for up to 5 results.
    """
    url = urljoin(BASE_URL, "/search")
    resp = requests.get(url, params={"keyword": query}, headers=_USER_AGENT, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    for a in soup.find_all("a", href=lambda h: h and h.startswith("/watch/"), limit=5):
        href = a["href"]
        # Title from <img alt>, then <a title>, then text
        title = (a.find("img", alt=True) or {}).get("alt") \
                or a.get("title") \
                or a.get_text(strip=True)
        if href and title:
            results.append({"id": href, "name": title.strip()})
    return results


async def search_anime(query: str) -> list[dict]:
    """
    Async wrapper for _sync_search.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_search, query)


def _sync_fetch_episodes(anime_path: str) -> list[dict]:
    """
    Blocking helper: scrape the watch page HTML for the <select id="epslist">.
    """
    page_url = urljoin(BASE_URL, anime_path.split("?", 1)[0])
    resp = requests.get(page_url, headers=_USER_AGENT, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    episodes = []
    sel = soup.find("select", id="epslist")
    if not sel:
        return episodes

    for opt in sel.find_all("option"):
        eid = opt["value"]
        label = opt.get_text(strip=True)
        episodes.append({
            "episodeId": eid,
            "number": label,
            "title": ""
        })
    return episodes


async def fetch_episodes(anime_path: str) -> list[dict]:
    """
    Async wrapper for _sync_fetch_episodes.
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
    Spins up headless Chromium (async) to grab:
      1) live .m3u8 URL (tokenized)
      2) the watch-page URL (for Referer)
      3) session cookies (for Cookie header)
    """
    watch_url = f"{BASE_URL}/watch/{episode_id}"
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

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
