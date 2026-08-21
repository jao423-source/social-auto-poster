#!/usr/bin/env python3
"""
Orchestrates one scheduled posting run:
  1. Pop the next unpublished entry from content/queue.json
  2. Render its quote-card image with generate_image.py
  3. Save the image into content/posted/ (so the workflow can commit + push
     it, giving Instagram's API a public raw.githubusercontent.com URL)
  4. Publish to Facebook + Instagram via post_to_meta.py
  5. Mark the entry as posted in content/state.json

Exits non-zero (without consuming the queue entry) if there's nothing left
to post, so the workflow can surface "queue empty" clearly.
"""
import json
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "content" / "queue.json"
STATE_PATH = ROOT / "content" / "state.json"
POSTED_DIR = ROOT / "content" / "posted"


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def _git(args):
    subprocess.run(["git", *args], cwd=ROOT.parent, check=True)


def main():
    queue = load_json(QUEUE_PATH, [])
    state = load_json(STATE_PATH, {"posted_ids": []})
    posted_ids = set(state.get("posted_ids", []))

    next_item = next((item for item in queue if item["id"] not in posted_ids), None)
    if next_item is None:
        print("Queue is empty — no unposted content left. Add more to content/queue.json.")
        sys.exit(2)

    POSTED_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    image_filename = f"{today}-{next_item['id']}.png"
    image_path = POSTED_DIR / image_filename
    image_repo_path = f"poster/content/posted/{image_filename}"

    subprocess.run(
        [
            sys.executable, str(ROOT / "scripts" / "generate_image.py"),
            "--text", next_item["text"],
            "--attribution", next_item.get("attribution", ""),
            "--out", str(image_path),
        ],
        check=True,
    )

    # Instagram's API needs a public URL for the image, and only sees what's
    # actually live on GitHub — so commit + push it *before* calling the
    # Graph API, not after. (Facebook doesn't need this: its /photos
    # endpoint takes the raw file directly.)
    _git(["add", image_repo_path])
    _git(["commit", "-m", f"Add post image: {image_filename}"])
    _git(["push"])
    time.sleep(5)  # brief buffer for raw.githubusercontent.com to serve the new file

    subprocess.run(
        [
            sys.executable, str(ROOT / "scripts" / "post_to_meta.py"),
            "--image", str(image_path),
            "--image-repo-path", image_repo_path,
            "--caption", next_item["caption"],
        ],
        check=True,
    )

    posted_ids.add(next_item["id"])
    state["posted_ids"] = sorted(posted_ids)
    state["last_posted_at"] = datetime.now(timezone.utc).isoformat()
    state["last_posted_id"] = next_item["id"]
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")

    print(f"Posted queue item '{next_item['id']}' and updated state.json")


if __name__ == "__main__":
    main()
