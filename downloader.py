# downloader.py

import subprocess
import os
import requests

def remux_hls(m3u8_url: str, referer: str | None, out_path: str):
    """
    Downloads/remuxes an HLS stream into a single MP4, sending both
    a browser-like User-Agent and the Referer header if provided.
    """
    # 1) Ensure the output directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # 2) Prepare a realistic browser User-Agent
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )

    # 3) Build ffmpeg command
    cmd = [
        "ffmpeg",
        "-y",
        # Use the dedicated user_agent flag
        "-user_agent", UA,
    ]

    # 4) If we have a Referer, inject it via -headers
    if referer:
        # -headers expects all headers in a single string, separated by \r\n
        cmd += ["-headers", f"Referer: {referer}\r\n"]

    # 5) Point ffmpeg at the HLS URL, copy streams into the output file
    cmd += ["-i", m3u8_url, "-c", "copy", out_path]

    # 6) Execute and raise on any error
    subprocess.run(cmd, check=True)

def download_subtitle(track: dict, out_dir: str, base_name: str) -> str:
    """
    Downloads a subtitle VTT file from the given track metadata.
    `track` should have at least {"file": URL, "lang" or "label": language}.
    Saves to out_dir/{base_name}_{lang}.vtt and returns that path.
    """
    # Ensure the output directory exists
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
