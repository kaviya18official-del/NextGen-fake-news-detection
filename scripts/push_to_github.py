"""Push NextGen NewsVerify repository to GitHub.

Usage:
    python scripts/push_to_github.py --token <YOUR_GITHUB_PERSONAL_ACCESS_TOKEN>
    OR
    set GITHUB_TOKEN=<YOUR_TOKEN>
    python scripts/push_to_github.py
"""

import argparse
import os
import sys
from dulwich import porcelain
from dulwich.repo import Repo

REPO_URL = "https://github.com/kaviya18official-del/NextGen-fake-news-detection.git"


def push_to_remote(token: str | None = None, branch: str = "main"):
    repo = Repo(".")

    token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        print("[!] Error: No GitHub Personal Access Token provided.")
        print("    GitHub requires a Personal Access Token (PAT) with 'repo' scope to push commits over HTTPS.")
        print("\n    How to get a token:")
        print("    1. Go to: https://github.com/settings/tokens?type=beta (Fine-grained) or https://github.com/settings/tokens (Classic)")
        print("    2. Grant 'Contents' read and write access (or 'repo' scope for classic tokens).")
        print("    3. Run: python scripts/push_to_github.py --token <YOUR_TOKEN>")
        sys.exit(1)

    # Construct authenticated HTTPS URL
    auth_remote = f"https://x-access-token:{token.strip()}@github.com/kaviya18official-del/NextGen-fake-news-detection.git"

    print(f"[*] Pushing local branch '{branch}' to: {REPO_URL} ...")
    try:
        porcelain.push(repo, auth_remote, refspecs=[f"refs/heads/{branch}".encode("utf-8")])
        print(f"[+] Successfully pushed to {REPO_URL} on branch '{branch}'!")
        print("\n[+] GitHub Pages will automatically deploy your live simulator via the GitHub Actions workflow:")
        print("    https://github.com/kaviya18official-del/NextGen-fake-news-detection/actions")
        print("\n[+] Once deployment completes, your live site will be accessible at:")
        print("    https://kaviya18official-del.github.io/NextGen-fake-news-detection/")
    except Exception as e:
        print(f"[!] Push failed: {type(e).__name__} - {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Push NextGen NewsVerify to GitHub repository.")
    parser.add_argument("--token", default=None, help="GitHub Personal Access Token (PAT)")
    parser.add_argument("--branch", default="main", help="Branch name (default: main)")
    args = parser.parse_args()

    push_to_remote(args.token, args.branch)
