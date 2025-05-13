# fetcher.py

import requests
import asyncio
from urllib.parse import urljoin

HTML_BASE   = "https://hianimez.to"
# AniWatch-API v2 endpoints for episodes & sources
API_BASE    = "https://api-aniwatch.onrender.com/api/v2/hianime"

# Browser-style headers for JSON calls
_JSON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def _sync_search(query: str) -> list[dict]:
    """
    Quick HTML scrape of the site's search page for up to 5 results.
    """
    resp = requests.get(
        urljoin(HTML_BASE, "/search"),
        params={"keyword": query},
        headers=_JSON_HEADERS,
        timeout=10
    )
    resp.raise_for_status()
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "html.parser")

    out = []
    for a in soup.select("a[href^='/watch/']")[:5]:
        href  = a["href"].split("?", 1)[0]
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
    Calls GET /anime/{animeId}/episodes on AniWatch-API to get every episode.
    """
    slug = anime_path.split("/watch/")[-1].split("?", 1)[0]
    url  = f"{API_BASE}/anime/{slug}/episodes"
    resp = requests.get(url, headers=_JSON_HEADERS, timeout=10)
    resp.raise_for_status()
    js   = resp.json().get("data", {})
    eps  = js.get("episodes", [])

    out = []
    for ep in eps:
        out.append({
            "episodeId": ep["episodeId"],                     # e.g. "raven-…?ep=94361"
            "number":    str(ep["number"]),                    # e.g. "1", "2", …
            "title":     ep.get("title", "")                   # optional
        })
    return out


async def fetch_episodes(anime_path: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch_episodes, anime_path)


def fetch_tracks(episode_id: str) -> list[dict]:
    """
    Subtitle stub (no change).
    """
    return []


def fetch_sources_and_referer(episode_id: str) -> tuple[list[dict], str, str]:
    """
    Calls GET /episode/sources to get HLS URLs plus headers.
    Returns: (sources, referer, headers_str_for_ffmpeg)
    """
    url = f"{API_BASE}/episode/sources"
    resp = requests.get(
        url,
        params={"animeEpisodeId": episode_id},
        headers=_JSON_HEADERS,
        timeout=10
    )
    resp.raise_for_status()
    data = resp.json().get("data", {})

    # sources: [ {url: "...", isM3U8: true, quality: "720p"}, … ]
    sources = data.get("sources", [])

    # the API will return the exact headers the player needs
    hdrs = data.get("headers", {})
    # build one ffmpeg-style header block:
    header_lines = []
    for k in ("User-Agent", "Referer", "Accept", "Cookie"):
        if k in hdrs:
            header_lines.append(f"{k}: {hdrs[k]}")
    header_str = "\r\n".join(header_lines) + "\r\n" if header_lines else ""

    # some of your downloader.remux_hls callers expect (sources, referer, cookie_str)
    return sources, hdrs.get("Referer", HTML_BASE), header_str
