# fetcher.py

import asyncio
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

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
    Blocking helper: scrape /search and return up to 5 matches.
    """
    url = urljoin(BASE_URL, "/search")
    resp = requests.get(url, params={"keyword": query}, headers=_USER_AGENT, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    for a in soup.find_all("a", href=lambda h: h and h.startswith("/watch/"), limit=5):
        href = a["href"]
        # Title from <img alt>, then title attr, then text
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


async def fetch_episodes(anime_path: str) -> list[dict]:
    """
    Uses headless Chromium to let the page's JS inject the episode links,
    but avoids networkidle timeouts by only waiting for DOMContentLoaded
    and then for the first "?ep=" links to appear.
    """
    # Drop any existing ?ep=... so we load the main watch page
    basepath = anime_path.split("?", 1)[0]
    url      = urljoin(BASE_URL, basepath)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page    = await browser.new_page()

        # 1) Navigate, but only wait for the document to be parsed
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
        except PlaywrightTimeout:
            # still proceed; page probably loaded enough to run its JS
            pass

        # 2) Wait for at least one episode link to appear
        selector = f'a[href^="{basepath}?ep="]'
        try:
            await page.wait_for_selector(selector, timeout=10_000)
        except PlaywrightTimeout:
            await browser.close()
            return []  # give up if the JS never injected them

        # 3) Grab them all
        anchors = await page.query_selector_all(selector)
        episodes = []
        seen = set()
        for a in anchors:
            href = await a.get_attribute("href")
            if not href or "?ep=" not in href:
                continue
            ep_id = href.split("?ep=", 1)[1]
            if ep_id in seen:
                continue
            seen.add(ep_id)
            label = (await a.inner_text()).strip() or f"Episode {ep_id}"
            episodes.append({"episodeId": ep_id, "number": label, "title": ""})

        await browser.close()

    # Sort by numeric id if possible
    try:
        episodes.sort(key=lambda e: int(e["episodeId"]))
    except ValueError:
        pass

    return episodes


def fetch_tracks(episode_id: str) -> list[dict]:
    """
    Subtitle stub: return [] unless you have a JSON endpoint.
    """
    return []


async def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    (Unchanged) headless Chromium capture of the .m3u8 URL + cookies.
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
        await page.goto(watch_url, wait_until="domcontentloaded")
        await page.reload(wait_until="domcontentloaded")

        if not m3u8_url:
            await browser.close()
            raise RuntimeError("Could not locate HLS manifest URL")

        cookies = await context.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        await browser.close()

    return [{"url": m3u8_url}], watch_url, cookie_str
