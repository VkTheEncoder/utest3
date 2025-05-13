# fetcher.py

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "https://hianimez.to"


def _sync_search(query: str) -> list[dict]:
    """
    Blocking helper: GETs the search page and returns up to 5 results.
    """
    url = urljoin(BASE_URL, "/search")
    resp = requests.get(
        url,
        params={"keyword": query},
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            )
        },
        timeout=10
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    # look for the first 5 <a href="/watch/..."> anchors
    for a in soup.find_all("a", href=lambda h: h and h.startswith("/watch/"), limit=5):
        href = a["href"]
        # extract a title: prefer <img alt>, then <a title>, then link text
        title = None
        img = a.find("img", alt=True)
        if img:
            title = img["alt"].strip()
        if not title and a.has_attr("title"):
            title = a["title"].strip()
        if not title:
            title = a.get_text(strip=True)
        if href and title:
            results.append({"id": href, "name": title})
    return results


async def search_anime(query: str) -> list[dict]:
    """
    Async wrapper around our blocking _sync_search.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_search, query)


async def fetch_episodes(anime_path: str) -> list[dict]:
    """
    Given the relative watch-page path (from search), hit the main watch page
    and scrape the <select id="epslist"> dropdown for episodes.
    Returns: [{"episodeId": "...", "number": "Episode 1", "title": ""}, …]
    """
    page_url = urljoin(BASE_URL, anime_path.split("?", 1)[0])
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(page_url, wait_until="networkidle")
        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    episodes = []
    sel = soup.find("select", id="epslist")
    if not sel:
        return episodes

    for opt in sel.find_all("option"):
        eid = opt["value"]
        label = opt.get_text(strip=True)
        episodes.append({"episodeId": eid, "number": label, "title": ""})
    return episodes


def fetch_tracks(episode_id: str) -> list[dict]:
    """
    Stub for subtitle tracks. Return [] if not used,
    or implement your JSON endpoint here.
    """
    return []


async def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    Spins up headless Chromium to capture:
      1) the live .m3u8 URL (with its expiring token),
      2) the watch-page URL (for Referer),
      3) the session cookies (for ffmpeg’s Cookie header).
    Returns (sources, referer, cookie_str).
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
