# fetcher.py

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "https://hianimez.to"
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
    url  = urljoin(BASE_URL, "/search")
    resp = requests.get(url, params={"keyword": query}, headers=_USER_AGENT, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    for a in soup.find_all("a", href=lambda h: h and h.startswith("/watch/"), limit=5):
        href = a["href"]
        # Title from <img alt>, then <a title>, then text
        title = None
        img = a.find("img", alt=True)
        if img:
            title = img["alt"].strip()
        elif a.has_attr("title"):
            title = a["title"].strip()
        else:
            title = a.get_text(strip=True)
        if href and title:
            results.append({"id": href, "name": title})
    return results


async def search_anime(query: str) -> list[dict]:
    """
    Async wrapper around the blocking _sync_search.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_search, query)


def _sync_fetch_episodes(anime_path: str) -> list[dict]:
    """
    Blocking helper: scrape the watch page for all episode links.
    """
    # The base path without any ?ep=… so we can match all the sibling links
    basepath = anime_path.split("?", 1)[0]
    page_url = urljoin(BASE_URL, basepath)
    resp     = requests.get(page_url, headers=_USER_AGENT, timeout=10)
    resp.raise_for_status()
    soup     = BeautifulSoup(resp.text, "html.parser")

    eps = []
    seen = set()
    # Look for <a href="/watch/<slug>?ep=123">…</a>
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith(basepath + "?ep="):
            continue
        ep_id = href.split("?ep=", 1)[1]
        if ep_id in seen:
            continue
        seen.add(ep_id)
        label = a.get_text(strip=True) or f"Episode {ep_id}"
        eps.append({"episodeId": ep_id, "number": label, "title": ""})

    # Optional: sort by numeric episodeId
    try:
        eps.sort(key=lambda x: int(x["episodeId"]))
    except ValueError:
        pass

    return eps


async def fetch_episodes(anime_path: str) -> list[dict]:
    """
    Async wrapper around the blocking _sync_fetch_episodes.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch_episodes, anime_path)


def fetch_tracks(episode_id: str) -> list[dict]:
    """
    Stub for subtitle tracks. Return [] or implement if you have a JSON endpoint.
    """
    return []


async def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    Async Playwright capture of the HLS URL + cookies.
    """
    watch_url = f"{BASE_URL}/watch/{episode_id}"
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
