# fetcher.py

import json
import requests
import asyncio
from urllib.parse import urljoin

from bs4 import BeautifulSoup

HTML_BASE   = "https://hianimez.to"
_USER_AGENT = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
}

def _sync_search(query: str) -> list[dict]:
    """
    Scrape /search for up to 5 results via HTML.
    """
    resp = requests.get(
        urljoin(HTML_BASE, "/search"),
        params={"keyword": query},
        headers=_USER_AGENT,
        timeout=10
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    out = []
    for a in soup.select("a[href^='/watch/']")[:5]:
        href  = a["href"].split("?", 1)[0]
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
    """
    Fetch the watch page HTML, parse the __NEXT_DATA__ JSON blob,
    and return props.pageProps.episodes.
    """
    page_url = urljoin(HTML_BASE, anime_path.split("?",1)[0])
    resp = requests.get(page_url, headers=_USER_AGENT, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return []  # no data found

    data = json.loads(script.string)
    props = data.get("props", {}).get("pageProps", {})
    eps_src = props.get("episodes") or props.get("anime", {}).get("episodes") or []

    out = []
    for ep in eps_src:
        eid   = str(ep.get("episodeId") or ep.get("id") or "")
        num   = str(ep.get("episodeNumber") or ep.get("episode") or eid)
        title = ep.get("title") or ep.get("name") or f"Episode {num}"
        if eid:
            out.append({"episodeId": eid, "number": num, "title": title})
    return out

async def fetch_episodes(anime_path: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch_episodes, anime_path)


def fetch_tracks(episode_id: str) -> list[dict]:
    """
    Subtitle stub—no change.
    """
    return []


def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    Unchanged ffmpeg/Playwright source grabber or your existing logic.
    """
    # (Paste your existing sources + referer + cookie logic here)
    raise NotImplementedError("Keep your existing sources logic")
