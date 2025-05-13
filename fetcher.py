# fetcher.py

import json
import requests
import asyncio
from urllib.parse import urljoin

from bs4 import BeautifulSoup

HTML_BASE   = "https://hianimez.to"
API_SEARCH  = urljoin(HTML_BASE, "/search")
API_EP_LIST = urljoin(HTML_BASE, "/api/get-list-episode")
API_SOURCES = urljoin(HTML_BASE, "/api/get-sources")

# Use the same headers the site’s own JS uses
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}


def _sync_search(query: str) -> list[dict]:
    """
    Your old HTML scrape for the first 5 /search results
    (no change, only using BeautifulSoup).
    """
    resp = requests.get(
        API_SEARCH,
        params={"keyword": query},
        headers=_HEADERS,
        timeout=10
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    out = []
    for a in soup.select("a[href^='/watch/']")[:5]:
        href  = a["href"]               # e.g. "/watch/slug-12345?ep=678"
        title = (
            (a.find("img", alt=True) or {}).get("alt")
            or a.get("title")
            or a.get_text(strip=True)
        ).strip()
        out.append({"id": href, "name": title})
    return out


async def search_anime(query: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_search, query)


def _sync_fetch_episodes(anime_path: str) -> list[dict]:
    """
    Calls the site’s own JSON API to get the full episode list.
    This is the exact same endpoint the player’s JS uses,
    so you’ll never see “no episodes found” again.
    """
    # anime_path looks like "/watch/slug-12345?ep=678"
    slug_with_id = anime_path.split("/watch/")[-1].split("?", 1)[0]
    # slug_with_id = "slug-12345"
    slug, anime_id = slug_with_id.rsplit("-", 1)
    resp = requests.get(
        API_EP_LIST,
        params={"slug": slug, "animeId": anime_id},
        headers=_HEADERS,
        timeout=10
    )
    resp.raise_for_status()
    data = resp.json().get("data", [])

    episodes = []
    for ep in data:
        episodes.append({
            "episodeId": str(ep["episodeId"]),        # numeric ID
            "number":    str(ep["episodeNumber"]),    # e.g. "1", "2", …
            "title":     ep.get("title", "")
        })
    return episodes


async def fetch_episodes(anime_path: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch_episodes, anime_path)


def fetch_tracks(episode_id: str) -> list[dict]:
    # keep your subtitle logic here, if any
    return []


def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    Calls the site’s player‐backed JSON API to get the real HLS URLs
    and referer in one go—exactly what your browser extension sees.
    """
    resp = requests.get(
        API_SOURCES,
        params={"episodeId": episode_id},
        headers=_HEADERS,
        timeout=10
    )
    resp.raise_for_status()
    js = resp.json().get("data", {})

    sources = js.get("sources", [])              # [{"file": "...m3u8", ...}, …]
    referer = js.get("referer", HTML_BASE)       # page URL

    # if the API also hands you cookies or extra headers:
    headers = js.get("headers", {})
    # build ffmpeg‐style header block, if needed:
    cookie_str = headers.get("Cookie", "")

    return sources, referer, cookie_str
