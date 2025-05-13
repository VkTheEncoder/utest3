# downloader.py

import os
import requests
import subprocess

def download_episode(m3u8_url: str, referer: str, cookies: str, out_path: str):
    """
    Uses ffmpeg to download/remux an HLS stream to MP4, sending
    full browser headers (User-Agent, Referer, Cookie, Accept)
    and automatic reconnect on network hiccups.
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Browser-style User-Agent
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )

    # Build a single headers blob
    headers = [
        f"User-Agent: {UA}\r\n",
        f"Referer: {referer}\r\n",
        f"Cookie: {cookies}\r\n",
        "Accept: */*\r\n",
    ]

    cmd = [
        "ffmpeg",
        "-y",
        "-headers", "".join(headers),
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "2",
        "-i", m3u8_url,
        "-c", "copy",
        out_path,
    ]
    subprocess.run(cmd, check=True)


def download_subtitle(track: dict, out_dir: str, base_name: str) -> str:
    """
    Downloads a subtitle VTT file.
    track: {"file": URL, "lang"/"label": language}
    Saves to out_dir/{base_name}_{lang}.vtt
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
