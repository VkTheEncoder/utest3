# downloader.py

import subprocess
import os
from urllib.parse import urlparse
import requests

def remux_hls(m3u8_url: str, referer: str | None, out_path: str):
    """
    Downloads/remuxes an HLS stream into a single MP4, sending browser-like headers
    (User-Agent, Referer, Host, Accept) and enabling automatic reconnect on failures.
    """
    # 1) Make sure output directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # 2) Prepare headers
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
    parsed = urlparse(m3u8_url)
    host = parsed.netloc

    hdrs = [
        f"User-Agent: {UA}\r\n",
        f"Host: {host}\r\n",
    ]
    if referer:
        hdrs.insert(1, f"Referer: {referer}\r\n")
    hdrs.append("Accept: */*\r\n")

    # 3) Build ffmpeg command with reconnect logic
    cmd = [
        "ffmpeg",
        "-y",
        "-headers", "".join(hdrs),
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "2",
        "-i", m3u8_url,
        "-c", "copy",
        out_path
    ]

    # 4) Run and let it retry on transient network hiccups
    subprocess.run(cmd, check=True)


def download_subtitle(track: dict, out_dir: str, base_name: str) -> str:
    """
    Downloads a subtitle VTT file from the given track metadata.
    `track` must include at least {"file": URL, "lang" or "label": language}.
    Saves to out_dir/{base_name}_{lang}.vtt and returns that path.
    """
    os.makedirs(out_dir, exist_ok=True)

    lang = track.get("label", track.get("lang", "subtitle")).split()[0]
    filename = f"{base_name}_{lang}.vtt"
    path = os.path.join(out_dir, filename)

    resp = requests.get(track["file"])
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)

    return path
