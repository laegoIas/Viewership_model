"""Push changes to the canonical GitHub repo (laegoIas/Viewership_model)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CANONICAL_REMOTE = "https://github.com/laegoIas/Viewership_model.git"
BRANCH = "main"


def run(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    current = run("git", "-C", str(root), "remote", "get-url", "origin")
    if current.rstrip("/") != CANONICAL_REMOTE.rstrip("/"):
        run("git", "-C", str(root), "remote", "set-url", "origin", CANONICAL_REMOTE)
        print(f"Reset origin to {CANONICAL_REMOTE}")

    status = run("git", "-C", str(root), "status", "--porcelain")
    if status:
        print("Uncommitted changes:")
        print(status)
        print("Commit first, then run push again.")
        sys.exit(1)

    subprocess.run(
        ["git", "-C", str(root), "push", "-u", "origin", BRANCH],
        check=True,
    )
    print(f"Pushed {BRANCH} to {CANONICAL_REMOTE}")


if __name__ == "__main__":
    main()
