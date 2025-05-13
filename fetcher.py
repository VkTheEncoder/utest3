# fetcher.py

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

# ─── Base of all page URLs ────────────────────────────────────────────────────
BASE_URL = "https://hianimez.to"

# ─── 1) Search ────────────────────────────────────────────────────────────────
def search_anime(query: str) -> list[dict]:
    """
    Scrape hianimez.to’s search page for up to 5 matching anime.
    Returns: [{"id": "<relative_watch_path>", "name": "<title>"}…]
    """
    search_url = urljoin(BASE_URL, "/search")
    resp = requests.get(
        search_url,
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
    # Each result lives in <div class="item"> → <a class="name" href="…">
    for item in soup.select("div.item")[:5]:
        a = item.select_one("a.name")
        if not a or not a.has_attr("href"):
            continue
        rel_path = a["href"]                 # e.g. "/watch/raven-of-…-18168?ep=94361"
        title    = a.get_text(strip=True)    # e.g. "Raven of the Inner Palace"
        results.append({"id": rel_path, "name": title})
    return results


# ─── 2) Episode List ─────────────────────────────────────────────────────────
def fetch_episodes(anime_path: str) -> list[dict]:
    """
    Given the relative watch-page path (from search), hit the main watch page
    (strip any ?ep=…) and scrape the <select id="epslist"> dropdown for episodes.
    Returns: [{"episodeId": "<value>", "number": "<label>", "title": ""}, …]
    """
    # strip off any ?ep=… so we load the full page
    page_url = urljoin(BASE_URL, anime_path.split("?", 1)[0])
    resp = requests.get(
        page_url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        timeout=10
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    eps = []
    sel = soup.find("select", id="epslist")
    if not sel:
        return eps

    for opt in sel.find_all("option"):
        ep_id = opt["value"]                 # numeric episodeId
        label = opt.get_text(strip=True)     # e.g. "Episode 1"
        eps.append({"episodeId": ep_id, "number": label, "title": ""})
    return eps


# ─── 3) Subtitle Tracks ───────────────────────────────────────────────────────
def fetch_tracks(episode_id: str) -> list[dict]:
    """
    If you have a separate JSON endpoint for subtitles, plug it in here.
    Otherwise, return an empty list and skip subtitles.
    """
    return []


# ─── 4) HLS Sources + Referer + Cookies ───────────────────────────────────────
def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    Spins up headless Chromium to let the site’s JS fetch the real .m3u8 URL
    (including its expiring token), and grabs the session cookies.
    Returns:
      - sources:  [{"url": "<fresh-master.m3u8>"}]
      - referer:  the watch page URL
      - cookies:  a "name=value; name2=value" string for ffmpeg’s Cookie header
    """
    watch_url = f"{BASE_URL}/watch/{episode_id}"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context()
        page    = context.new_page()

        m3u8_url = None

        def _capture(response):
            nonlocal m3u8_url
            if response.url.endswith(".m3u8") and not m3u8_url:
                m3u8_url = response.url

        page.on("response", _capture)

        # 1) Navigate & wait for network idle
        page.goto(watch_url, wait_until="networkidle")
        # 2) Some players only fetch manifest on reload
        page.reload(wait_until="networkidle")

        if not m3u8_url:
            browser.close()
            raise RuntimeError("Could not locate HLS manifest URL")

        # Gather cookies for the domain
        cookie_list = context.cookies()
        cookie_str  = "; ".join(f"{c['name']}={c['value']}" for c in cookie_list)

        browser.close()

    return [{"url": m3u8_url}], watch_url, cookie_str
