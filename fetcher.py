# fetcher.py

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://hianimez.to"

def search_anime(query: str) -> list[dict]:
    """
    Scrape hianimez.to’s search page for up to 5 matching anime.
    Returns a list of {"id": "<relative_watch_path>", "name": "<title>"}.
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
    # Find thumbnail images whose parent link goes to /watch/…
    for img in soup.find_all("img", alt=True):
        parent = img.find_parent("a", href=True)
        href   = parent and parent["href"]
        if not href or not href.startswith("/watch/"):
            continue

        title = img["alt"].strip()
        results.append({"id": href, "name": title})
        if len(results) >= 5:
            break

    return results


def fetch_episodes(anime_path: str) -> list[dict]:
    """
    Given the relative watch-page path (from search), hit the main watch page
    and scrape the episodes dropdown (<select id="epslist">).
    """
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
        eps.append({
            "episodeId": opt["value"],
            "number":    opt.get_text(strip=True),
            "title":     ""
        })
    return eps


def fetch_tracks(episode_id: str) -> list[dict]:
    """
    If you have a JSON endpoint for subtitles, implement it here.
    Otherwise we’ll just skip subtitles.
    """
    return []


def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    Spins up headless Chromium (Playwright) to capture:
      1) the live .m3u8 URL (with token),
      2) the watch page URL (for Referer),
      3) the session cookies (for ffmpeg).
    """
    from playwright.sync_api import sync_playwright

    watch_url = f"{BASE_URL}/watch/{episode_id}"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx     = browser.new_context()
        page    = ctx.new_page()

        m3u8_url = None
        def _check(r):
            nonlocal m3u8_url
            if r.url.endswith(".m3u8") and not m3u8_url:
                m3u8_url = r.url

        page.on("response", _check)
        page.goto(watch_url, wait_until="networkidle")
        page.reload(wait_until="networkidle")

        if not m3u8_url:
            browser.close()
            raise RuntimeError("HLS manifest not found")

        cookies = ctx.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        browser.close()

    return [{"url": m3u8_url}], watch_url, cookie_str
