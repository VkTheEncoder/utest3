# fetcher.py

import requests
from playwright.sync_api import sync_playwright

# ——— YOUR API BASE URL ———
API_BASE = "http://api:4000/api/v2/hianime"


def search_anime(query: str) -> list[dict]:
    """
    Call your search endpoint and return a list of {id, name} dicts.
    """
    resp = requests.get(f"{API_BASE}/search", params={"q": query})
    resp.raise_for_status()
    return resp.json()


def fetch_episodes(anime_id: str) -> list[dict]:
    """
    Call your episodes endpoint and return a list of
    {"episodeId": ..., "number": ..., "title": ...} dicts.
    """
    resp = requests.get(f"{API_BASE}/anime/{anime_id}/episodes")
    resp.raise_for_status()
    return resp.json()


def fetch_tracks(episode_id: str) -> list[dict]:
    """
    Call your subtitle/track endpoint and return a list of
    {"file": ..., "lang"/"label": ...} dicts.
    """
    resp = requests.get(f"{API_BASE}/episode/{episode_id}/tracks")
    resp.raise_for_status()
    return resp.json()


def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    Launch a headless browser, navigate to the watch page, let the site's
    JS spin up the player, intercept the real .m3u8 URL and session cookies.
    Returns:
      - sources:  [{"url": "<fresh-master.m3u8>"}]
      - referer:  the watch page URL (used as Referer header)
      - cookies:  a "name=value; name2=value2" string for Cookie header
    """
    watch_url = f"https://YOUR-SITE/watch/{episode_id}"
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

        # 1) Navigate and wait for all network calls to finish
        page.goto(watch_url, wait_until="networkidle")
        # 2) Some players only fetch the manifest on reload
        page.reload(wait_until="networkidle")

        if not m3u8_url:
            browser.close()
            raise RuntimeError("Could not locate HLS manifest URL")

        # Gather cookies for the site
        cookie_list = context.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookie_list)

        browser.close()

    sources = [{"url": m3u8_url}]
    referer = watch_url
    return sources, referer, cookie_str
