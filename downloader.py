# downloader.py

import os
import requests
from streamlink import Streamlink

def download_episode(m3u8_url: str, referer: str, out_path: str):
    """
    Downloads an HLS stream (master.m3u8) to out_path using Streamlink,
    passing through browser-style headers and automatic reconnects.
    """
    # 1) Ensure output directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # 2) Prepare headers just like a real browser
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
    headers = {
        "User-Agent": UA,
        "Referer": referer,
        "Accept": "*/*",
    }

    # 3) Create a Streamlink session and configure headers
    session = Streamlink()
    session.set_option("http-headers", headers)

    # 4) Fetch available streams (will raise on 403/expired tokens)
    streams = session.streams(m3u8_url)
    if not streams:
        raise RuntimeError(f"No playable streams found for URL: {m3u8_url}")

    # 5) Pick the “best” quality and write it out chunk by chunk
    stream = streams.get("best") or next(iter(streams.values()))
    with open(out_path, "wb") as fd, stream.open() as stream_fd:
        for chunk in stream_fd:
            fd.write(chunk)


def download_subtitle(track: dict, out_dir: str, base_name: str) -> str:
    """
    Downloads a subtitle VTT file from the given track metadata.
    `track` should include at least {"file": URL, "lang" or "label": language}.
    Saves to out_dir/{base_name}_{lang}.vtt and returns that path.
    """
    os.makedirs(out_dir, exist_ok=True)

    # Derive a simple language tag
    lang = track.get("label", track.get("lang", "subtitle")).split()[0]
    filename = f"{base_name}_{lang}.vtt"
    path = os.path.join(out_dir, filename)

    # Fetch and write out the VTT
    resp = requests.get(track["file"])
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)

    return path
