# downloader.py

import os
import requests
from yt_dlp import YoutubeDL

def download_episode(m3u8_url: str, referer: str, out_path: str):
    """
    Downloads an HLS stream (master.m3u8) to out_path using yt-dlp,
    passing through browser-style headers and automatic retries.
    """
    # 1) Ensure the output directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # 2) Build the headers exactly as the site expects
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ),
        "Referer": referer,
        "Accept": "*/*",
    }

    # 3) yt-dlp options
    ydl_opts = {
        "outtmpl": out_path,
        "format": "best",         # picks the best HLS variant
        "http_headers": headers,  # browser-style headers
        "retries": 10,            # retry up to 10 times
        "continuedl": True,       # resume partial downloads
        "noplaylist": True,       # treat URL as single video
        "quiet": False,           # set to True to suppress console output
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([m3u8_url])


def download_subtitle(track: dict, out_dir: str, base_name: str) -> str:
    """
    Downloads a subtitle VTT file from the given track metadata.
    `track` should include at least {"file": URL, "lang" or "label": language}.
    Saves to out_dir/{base_name}_{lang}.vtt and returns that path.
    """
    # 1) Ensure output directory exists
    os.makedirs(out_dir, exist_ok=True)

    # 2) Derive a simple language tag
    lang = track.get("label", track.get("lang", "subtitle")).split()[0]
    filename = f"{base_name}_{lang}.vtt"
    path = os.path.join(out_dir, filename)

    # 3) Fetch and write out the VTT
    resp = requests.get(track["file"])
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)

    return path
