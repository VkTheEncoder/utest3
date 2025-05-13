import os
import subprocess

def remux_hls(m3u8_url: str, referer: str, cookies: str, out_path: str):
    """
    Invoke ffmpeg to download & remux the HLS stream into MP4.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    headers = [
        f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36\r\n",
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
        out_path
    ]
    subprocess.run(cmd, check=True)
