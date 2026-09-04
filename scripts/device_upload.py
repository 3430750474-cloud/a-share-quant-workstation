"""Upload the project with a GitHub device-flow token without printing it."""

from __future__ import annotations

import base64
import os
import pathlib
import time

import requests


ROOT = pathlib.Path(__file__).resolve().parents[1]
OWNER = "3430750474-cloud"
REPO = "a-share-quant-workstation"
CLIENT_ID = "178c6fc778ccc68e1d6a"
DEVICE_CODE = "eeefdeb174bb85b24e3b3d1ff28f0db9be97817b"
API = "https://api.github.com"
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".git", "node_modules", ".venv", "venv"}
EXCLUDE_SUFFIXES = {".pyc", ".exe"}


def get_token():
    env_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if env_token:
        return env_token
    for _ in range(40):
        response = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": CLIENT_ID,
                "device_code": DEVICE_CODE,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json"},
            timeout=20,
        )
        data = response.json()
        if data.get("access_token"):
            return data["access_token"]
        if data.get("error") == "authorization_pending":
            time.sleep(5)
            continue
        if data.get("error") == "slow_down":
            time.sleep(int(data.get("interval", 10)))
            continue
        raise SystemExit(f"token error: {data.get('error')}")
    raise SystemExit("authorization still pending")


def files_to_upload():
    paths = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if set(rel.split("/")) & EXCLUDE_DIRS:
            continue
        if rel.endswith(tuple(EXCLUDE_SUFFIXES)):
            continue
        paths.append((rel, path))
    return paths


def upload(token):
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    uploaded = 0
    for rel, local in files_to_upload():
        payload = {
            "message": f"Add {rel}",
            "content": base64.b64encode(local.read_bytes()).decode("ascii"),
        }
        result = requests.put(
            f"{API}/repos/{OWNER}/{REPO}/contents/{rel}",
            headers=headers,
            json=payload,
            timeout=60,
        )
        if result.status_code not in (200, 201):
            print(f"failed {rel}: {result.text[:300]}")
            continue
        uploaded += 1
        print(f"uploaded {rel}")
    return uploaded


def main():
    token = get_token()
    uploaded = upload(token)
    print(f"uploaded {uploaded} files")
    print(f"repo: https://github.com/{OWNER}/{REPO}")


if __name__ == "__main__":
    main()
