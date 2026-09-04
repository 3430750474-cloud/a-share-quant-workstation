"""Download cloudflared.exe for Windows with connection-resume retries."""

from __future__ import annotations

import pathlib
import time

import requests


TAG = "2026.8.3"
URL = (
    "https://github.com/cloudflare/cloudflared/releases/download/"
    f"{TAG}/cloudflared-windows-amd64.exe"
)
OUT = pathlib.Path("cloudflared.exe")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "*/*",
}


def main():
    offset = OUT.stat().st_size if OUT.exists() else 0
    while True:
        headers = dict(HEADERS)
        if offset:
            headers["Range"] = f"bytes={offset}-"
        try:
            response = requests.get(URL, headers=headers, stream=True, timeout=60)
            total = int(response.headers.get("Content-Length") or 0)
            if offset and response.status_code == 206:
                total += offset
            if not offset and response.status_code != 200:
                raise SystemExit(f"HTTP {response.status_code}")
            with open(OUT, "ab" if offset else "wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 512):
                    if chunk:
                        handle.write(chunk)
                        offset += len(chunk)
                        print(f"\r{offset / 1e6:.1f} MB", end="", flush=True)
            print()
            if total and offset >= total:
                return
        except (requests.ConnectionError, requests.Timeout):
            print("\nconnection reset; retrying...")
            time.sleep(1)


if __name__ == "__main__":
    main()
