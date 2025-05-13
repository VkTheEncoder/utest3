# downloader.py

import subprocess
import os
import requests

def remux_hls(m3u8_url: str, referer: str | None, out_path: str):
    """
    Downloads/remuxes an HLS stream into a single MP4, sending both
    a browser-like User-Agent and the Referer header if provided.
    """
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Start building the ffmpeg command
    cmd = ["ffmpeg", "-y"]

    # Always send a realistic browser User-Agent, and include Referer if given
    headers = [
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36\r\n"
    ]
    if referer:
        headers.append(f"Referer: {referer}\r\n")

    # Inject headers before the -i input URL
    cmd += ["-headers", "".join(headers)]
    cmd += ["-i", m3u8_url, "-c", "copy", out_path]

    # Run ffmpeg and raise on failure
    subprocess.run(cmd, check=True)

def download_subtitle(track: dict, out_dir: str, base_name: str) -> str:
    """
    Downloads a subtitle VTT file.
    track: { lang, file (URL) }
    Saves to out_dir/{base_name}_{lang}.vtt
    """
    lang = track.get("label", track.get("lang", "subtitle")).split()[0]
    fname = f"{base_name}_{lang}.vtt"
    path = os.path.join(out_dir, fname)

    os.makedirs(out_dir, exist_ok=True)
    resp = requests.get(track["file"])
    resp.raise_for_status()

    with open(path, "wb") as f:
        f.write(resp.content)

    return path
