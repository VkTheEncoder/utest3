# fetcher.py

import asyncio
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
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
    Fast, blocking scrape of /search → first 5 results.
    """
    resp = requests.get(
        urljoin(BASE_URL, "/search"),
        params={"keyword": query},
        headers=_USER_AGENT,
        timeout=10
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    out = []
    for a in soup.find_all("a", href=lambda h: h and h.startswith("/watch/"), limit=5):
        href = a["href"]
        # pick a title from <img alt>, then title attr, then link text
        title = (
            (a.find("img", alt=True) or {}).get("alt")
            or a.get("title")
            or a.get_text(strip=True)
        )
        if href and title:
            out.append({"id": href, "name": title.strip()})
    return out


async def search_anime(query: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_search, query)


async def fetch_episodes(anime_path: str) -> list[dict]:
    """
    Renders the watch page in headless Chromium, waits for the JS-injected
    episode list to appear, then scrapes every <a> whose href has '?ep='.
    """
    watch_base = anime_path.split("?", 1)[0]
    url        = urljoin(BASE_URL, watch_base)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page    = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        # This selector matches the container that the site uses to hold its ep links
        # (you may need to tweak if HiAnimez tweaks its markup)
        await page.wait_for_selector("div.episo de-list, div.eplist, ul.eplist", timeout=10_000)

        # Now grab all the individual <a> tags inside it
        anchors = await page.query_selector_all("div.eplist a, ul.eplist a, div.episodes a")
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
            episodes.append({
                "episodeId": ep_id,
                "number":    label,
                "title":     ""
            })

        await browser.close()

    # Optional: sort by the numeric episodeId
    try:
        episodes.sort(key=lambda e: int(e["episodeId"]))
    except ValueError:
        pass

    return episodes


def fetch_tracks(episode_id: str) -> list[dict]:
    return []  # as before


async def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    (unchanged) headless browser grab of the .m3u8 + cookies.
    """
    watch_url = f"{BASE_URL}/watch/{episode_id}"
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx     = await browser.new_context()
        page    = await ctx.new_page()

        m3u8 = None
        def capture(r):
            nonlocal m3u8
            if r.url.endswith(".m3u8") and not m3u8:
                m3u8 = r.url

        page.on("response", capture)
        await page.goto(watch_url, wait_until="networkidle")
        await page.reload(wait_until="networkidle")

        if not m3u8:
            await browser.close()
            raise RuntimeError("Could not locate HLS manifest URL")

        cookies = await ctx.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        await browser.close()

    return [{"url": m3u8}], watch_url, cookie_str
