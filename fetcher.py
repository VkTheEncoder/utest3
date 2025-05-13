# fetcher.py

import requests
import asyncio
from urllib.parse import urljoin

HTML_BASE    = "https://hianimez.to"
API_EP_LIST  = urljoin(HTML_BASE, "/api/get-list-episode")
API_SOURCES  = urljoin(HTML_BASE, "/api/get-sources")
_USER_AGENT  = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def _sync_search(query: str) -> list[dict]:
    url  = urljoin(HTML_BASE, "/search")
    resp = requests.get(url, params={"keyword": query}, headers=_USER_AGENT, timeout=10)
    resp.raise_for_status()
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "html.parser")

    out = []
    # find the first 5 anime links
    for a in soup.select("a[href^='/watch/']")[:5]:
        href  = a["href"].split("?")[0]
        title = (
            (a.find("img", alt=True) or {}).get("alt")
            or a.get("title")
            or a.get_text(strip=True)
        ).strip()
        if href and title:
            out.append({"id": href, "name": title})
    return out


async def search_anime(query: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_search, query)


def _sync_fetch_episodes(anime_path: str) -> list[dict]:
    # anime_path comes in as "/watch/your-slug-12345"
    slug = anime_path.split("/watch/")[-1]
    resp = requests.get(API_EP_LIST,
                        params={"slug": slug},
                        headers=_USER_AGENT,
                        timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", [])

    episodes = []
    for ep in data:
        episodes.append({
            "episodeId": str(ep["episodeId"]),
            "number":    str(ep["episodeNumber"]),
            "title":     ep.get("title", f"Episode {ep['episodeNumber']}")
        })
    return episodes


async def fetch_episodes(anime_path: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch_episodes, anime_path)


def fetch_tracks(episode_id: str) -> list[dict]:
    # (optional) pull subtitle info here if you have a JSON API for that
    return []


def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    resp = requests.get(API_SOURCES,
                        params={"episodeId": episode_id},
                        headers=_USER_AGENT,
                        timeout=10)
    resp.raise_for_status()
    js      = resp.json()
    sources = js.get("sources", [])
    referer = js.get("referer", HTML_BASE)
    return sources, referer, ""
