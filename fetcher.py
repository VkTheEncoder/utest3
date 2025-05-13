# fetcher.py

import re
import json
import requests
import asyncio
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

HTML_BASE = "https://hianimez.to"
USER_AGENT = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
}


def _sync_search(query: str) -> list[dict]:
    """
    Scrape the search page for up to 5 results.
    """
    resp = requests.get(
        urljoin(HTML_BASE, "/search"),
        params={"keyword": query},
        headers=USER_AGENT,
        timeout=10
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    out = []
    for a in soup.find_all("a", href=lambda h: h and h.startswith("/watch/"), limit=5):
        href = a["href"]
        title = (a.find("img", alt=True) or {}).get("alt") or a.get("title") or a.get_text(strip=True)
        if href and title:
            out.append({"id": href, "name": title.strip()})
    return out


async def search_anime(query: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_search, query)


def _sync_fetch_episodes(anime_path: str) -> list[dict]:
    """
    1) Fetch the watch-page HTML.
    2) Extract Next.js buildId from the <script> tags.
    3) Fetch the JSON at /_next/data/{buildId}/{path}.json
    4) Pull episode list out of pageProps in that JSON.
    """
    # Normalize path and URLs
    page_path = anime_path.split("?", 1)[0]            # e.g. "/watch/raven-of-...-18168"
    html_url  = urljoin(HTML_BASE, page_path)
    resp      = requests.get(html_url, headers=USER_AGENT, timeout=10)
    resp.raise_for_status()
    html = resp.text

    # 1) Extract the Next.js buildId
    m = re.search(r'/_next/data/([^/]+)/', html)
    if not m:
        return []
    build_id = m.group(1)

    # 2) Construct JSON URL
    json_url = urljoin(
        HTML_BASE,
        f"/_next/data/{build_id}{page_path}.json"
    )

    jresp = requests.get(json_url, headers=USER_AGENT, timeout=10)
    jresp.raise_for_status()
    data = jresp.json()

    # 3) Drill into pageProps to find the episodes array
    #    This shape is typical for Next.js: data['pageProps']['episodes']
    pp = data.get("pageProps", {})
    eps_data = pp.get("episodes") or pp.get("anime", {}).get("episodes") or []

    out = []
    for ep in eps_data:
        # ep keys might be: episodeId (string/int), episodeNumber, name/title
        eid    = str(ep.get("episodeId"))
        number = str(ep.get("episodeNumber", ep.get("episodeId", "")))
        title  = ep.get("title") or ep.get("name") or ""
        out.append({"episodeId": eid, "number": number, "title": title})
    return out


async def fetch_episodes(anime_path: str) -> list[dict]:
    """
    Async wrapper for _sync_fetch_episodes.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch_episodes, anime_path)


def fetch_tracks(episode_id: str) -> list[dict]:
    """
    Stub for subtitle tracks.
    """
    return []


async def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    (Unchanged) use Playwright to grab the live .m3u8 URL and cookies.
    """
    watch_url = f"{HTML_BASE}/watch/{episode_id}"
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx     = await browser.new_context()
        page    = await ctx.new_page()

        m3u8 = None
        def cap(response):
            nonlocal m3u8
            if response.url.endswith(".m3u8") and not m3u8:
                m3u8 = response.url

        page.on("response", cap)
        await page.goto(watch_url, wait_until="networkidle")
        await page.reload(wait_until="networkidle")

        if not m3u8:
            await browser.close()
            raise RuntimeError("Could not locate HLS manifest URL")

        cookies = await ctx.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        await browser.close()

    return [{"url": m3u8}], watch_url, cookie_str
