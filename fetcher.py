# fetcher.py

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

BASE_URL = "https://hianimez.to"


def search_anime(query: str) -> list[dict]:
    """
    Use a headless browser to load the search page,
    then scrape up to 5 results of {"id": "<watch-path>", "name": "<title>"}.
    """
    search_url = f"{BASE_URL}/search?keyword={query}"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(search_url, wait_until="networkidle")
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    results = []
    # Find the first 5 <a href="/watch/..."> anchors
    for a in soup.find_all("a", href=lambda h: h and h.startswith("/watch/"), limit=5):
        href = a["href"]
        # Try to get a human-readable title from <img alt>, then <a title>, then text
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


def fetch_episodes(anime_path: str) -> list[dict]:
    """
    Headless-browser fetch of the main watch page to scrape the episode dropdown.
    Returns [{"episodeId": "...", "number": "Ep 1", "title": ""}, …]
    """
    page_url = urljoin(BASE_URL, anime_path.split("?", 1)[0])
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(page_url, wait_until="networkidle")
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    episodes = []
    sel = soup.find("select", id="epslist")
    if not sel:
        return episodes

    for opt in sel.find_all("option"):
        eid   = opt["value"]
        label = opt.get_text(strip=True)
        episodes.append({"episodeId": eid, "number": label, "title": ""})
    return episodes


def fetch_tracks(episode_id: str) -> list[dict]:
    """
    Stub for subtitles—return [] if none or implement your JSON endpoint here.
    """
    return []


def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    Spins up headless Chromium to let the site’s JS fetch the real .m3u8 URL
    (with its expiring token) and collects the session cookies.
    Returns:
      - sources:  [{"url": "<fresh-master.m3u8>"}]
      - referer:  the watch-page URL
      - cookies:  "name=val; name2=val2" for ffmpeg’s Cookie header
    """
    watch_url = f"{BASE_URL}/watch/{episode_id}"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx     = browser.new_context()
        page    = ctx.new_page()

        m3u8_url = None
        def _capture(response):
            nonlocal m3u8_url
            if response.url.endswith(".m3u8") and not m3u8_url:
                m3u8_url = response.url

        page.on("response", _capture)
        page.goto(watch_url, wait_until="networkidle")
        page.reload(wait_until="networkidle")

        if not m3u8_url:
            browser.close()
            raise RuntimeError("Could not locate HLS manifest URL")

        # collect cookies
        cookie_list = ctx.cookies()
        cookie_str  = "; ".join(f"{c['name']}={c['value']}" for c in cookie_list)

        browser.close()

    return [{"url": m3u8_url}], watch_url, cookie_str
