import os
from yt_dlp import YoutubeDL

# Shared headers for all downloads
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
}

def download_url(url: str, out_path: str):
    """
    Download any video/audio URL (mp4, m3u8, etc.) into out_path
    using yt-dlp with retries, resume, and best‐quality.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    ydl_opts = {
        "outtmpl": out_path,
        "format": "best",
        "http_headers": _HEADERS,
        "retries": 10,
        "continuedl": True,
        "noplaylist": True,
        "quiet": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
