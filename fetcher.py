# fetcher.py

import os
import requests
import asyncio
from urllib.parse import urljoin

HTML_BASE = "https://hianimez.to"
API_EP_LIST   = urljoin(HTML_BASE, "/api/get-list-episode")
API_SOURCES   = urljoin(HTML_BASE, "/api/get-sources")
_USER_AGENT = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def _sync_search(query: str) -> list[dict]:
    """
    Simple HTML scrape for search; remains fast and reliable.
    """
    url  = urljoin(HTML_BASE, "/search")
    resp = requests.get(url, params={"keyword": query}, headers=_USER_AGENT, timeout=10)
    resp.raise_for_status()
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    for a in soup.find_all("a", href=lambda h: h and h.startswith("/watch/"), limit=5):
        href  = a["href"]
        title = (a.find("img", alt=True) or {}).get("alt") or a.get("title") or a.get_text(strip=True)
        if href and title:
            results.append({"id": href, "name": title.strip()})
    return results


async def search_anime(query: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_search, query)


def _sync_fetch_episodes(anime_path: str) -> list[dict]:
    """
    Calls the site’s JSON API to get every episode for this slug.
    """
    # slug is the part after /watch/ up to any ?
    slug = anime_path.split("/watch/")[1].split("?", 1)[0]
    resp = requests.get(API_EP_LIST, params={"slug": slug}, headers=_USER_AGENT, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    episodes = []
    for ep in data:
        episodes.append({
            "episodeId": str(ep["episodeId"]),        # numeric ID
            "number":    str(ep["episodeNumber"]),    # e.g. "1", "2"
            "title":     ep.get("title", "")
        })
    return episodes


async def fetch_episodes(anime_path: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch_episodes, anime_path)


def fetch_tracks(episode_id: str) -> list[dict]:
    # if there’s a JSON subtitles API, call it here; otherwise skip
    return []


def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    Calls the JSON API to get HLS sources and referer in one go.
    """
    resp = requests.get(
        API_SOURCES,
        params={"episodeId": episode_id},
        headers=_USER_AGENT,
        timeout=10
    )
    resp.raise_for_status()
    js = resp.json()
    sources = js.get("sources", [])
    # each source: {"file": URL, "type": "hls", "label": "720p"}
    # site might return file URLs without referer issues
    referer = js.get("referer", HTML_BASE)
    return sources, referer, ""
