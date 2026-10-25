"""Upload data/plans/escondido_plans.pdf to a running API (used by make demo).

Usage:
  uv run python backend/scripts/demo_upload.py
  uv run python backend/scripts/demo_upload.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PDF = REPO_ROOT / "data" / "plans" / "escondido_plans.pdf"


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload Escondido plans for the demo")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    args = parser.parse_args()

    if not args.pdf.exists():
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 1

    url = f"{args.base_url.rstrip('/')}/api/documents"
    with args.pdf.open("rb") as f:
        files = {"file": (args.pdf.name, f, "application/pdf")}
        resp = httpx.post(url, files=files, timeout=120.0)
    print(resp.status_code, resp.text)
    return 0 if resp.status_code in {200, 202} else 1


if __name__ == "__main__":
    raise SystemExit(main())
