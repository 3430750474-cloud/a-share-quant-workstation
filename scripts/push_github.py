"""Upload this project to GitHub without requiring a local Git install.

Requires a GitHub personal access token with the `repo` scope. Set it in the
environment before running:

    $env:GITHUB_TOKEN="ghp_xxx"
    python scripts/push_github.py
"""

from __future__ import annotations

import base64
import getpass
import json
import os
import pathlib

import requests


ROOT = pathlib.Path(__file__).resolve().parents[1]
API = "https://api.github.com"
EXCLUDE_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    "node_modules",
    ".venv",
    "venv",
}
EXCLUDE_SUFFIXES = {".pyc", ".exe"}
EXCLUDE_FILES = {".env"}


def tree():
    files = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        parts = set(path.relative_to(ROOT).parts)
        if parts & EXCLUDE_DIRS or rel.endswith(tuple(EXCLUDE_SUFFIXES)):
            continue
        if path.name in EXCLUDE_FILES:
            continue
        files.append(rel)
    return files


def main():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        token = getpass.getpass("Paste GitHub token (masked): ").strip()
    if not token:
        raise SystemExit("Set GITHUB_TOKEN first.")
    owner = os.environ.get("GITHUB_OWNER", "").strip()
    repo = os.environ.get("GITHUB_REPO", "a-share-quant-workstation").strip()
    if not owner:
        user = requests.get(
            f"{API}/user", headers={"Authorization": f"token {token}"}, timeout=15
        ).json()
        owner = user.get("login", "")
    if not owner:
        raise SystemExit("Cannot resolve GitHub owner; set GITHUB_OWNER.")

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    repo_url = f"{API}/repos/{owner}/{repo}"
    response = requests.get(repo_url, headers=headers, timeout=15)
    if response.status_code == 404:
        created = requests.post(
            f"{API}/user/repos",
            headers=headers,
            json={
                "name": repo,
                "description": "A股短线量化工作站",
                "private": False,
                "has_issues": True,
                "has_wiki": False,
            },
            timeout=20,
        )
        if created.status_code not in (200, 201):
            raise SystemExit(f"Create repo failed: {created.text[:500]}")

    for rel in tree():
        local = ROOT / rel
        content = local.read_bytes()
        payload = {
            "message": f"Add {rel}",
            "content": base64.b64encode(content).decode("ascii"),
        }
        existing = requests.get(
            f"{repo_url}/contents/{rel}",
            headers=headers,
            timeout=20,
        )
        if existing.status_code == 200:
            payload["sha"] = existing.json().get("sha")
        result = requests.put(
            f"{repo_url}/contents/{rel}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if result.status_code not in (200, 201):
            print(f"failed {rel}: {result.text[:300]}")
        else:
            print(f"uploaded {rel}")

    print(f"repo: https://github.com/{owner}/{repo}")
    print("next: connect this repo to Render/Railway using render.yaml/railway.json")


if __name__ == "__main__":
    main()
