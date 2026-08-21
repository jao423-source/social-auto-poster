#!/usr/bin/env python3
"""
Publishes one queued post to a Facebook Page and its linked Instagram
Business account via the Meta Graph API.

Designed to run inside GitHub Actions, where outbound internet access is
unrestricted (unlike the Cowork sandbox this was authored in). Reads
credentials from environment variables (populated from GitHub Actions
"Repository secrets" — see the accompanying workflow file):

    PAGE_ID                 Facebook Page ID
    PAGE_ACCESS_TOKEN       Long-lived Page access token
    IG_USER_ID              Instagram Business Account ID
    GITHUB_REPOSITORY       owner/repo (auto-provided by Actions)
    GITHUB_REF_NAME         branch name (auto-provided by Actions)

The image must already be committed and pushed to the repo before this
script runs (the workflow does that) — Instagram's API requires a public
image URL, and we use the repo's own raw.githubusercontent.com URL for
that instead of a third-party image host.
"""
import os
import sys
import json
import time
import argparse
import requests

GRAPH = "https://graph.facebook.com/v21.0"


def post_to_facebook(page_id, token, image_path, caption):
    url = f"{GRAPH}/{page_id}/photos"
    with open(image_path, "rb") as f:
        resp = requests.post(
            url,
            data={"caption": caption, "access_token": token},
            files={"source": f},
            timeout=60,
        )
    resp.raise_for_status()
    return resp.json()


def post_to_instagram(ig_user_id, token, image_public_url, caption):
    # Step 1: create a media container
    create_url = f"{GRAPH}/{ig_user_id}/media"
    resp = requests.post(
        create_url,
        data={
            "image_url": image_public_url,
            "caption": caption,
            "access_token": token,
        },
        timeout=60,
    )
    resp.raise_for_status()
    creation_id = resp.json()["id"]

    # Step 2: poll container status until it's ready to publish
    status_url = f"{GRAPH}/{creation_id}"
    for _ in range(10):
        status = requests.get(
            status_url,
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        ).json()
        if status.get("status_code") == "FINISHED":
            break
        time.sleep(3)

    # Step 3: publish it
    publish_url = f"{GRAPH}/{ig_user_id}/media_publish"
    resp = requests.post(
        publish_url,
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--image", required=True, help="Local path to the image file")
    p.add_argument("--image-repo-path", required=True,
                    help="Path of the image within the repo, e.g. content/posted/2026-08-24.png")
    p.add_argument("--caption", required=True)
    args = p.parse_args()

    page_id = os.environ["PAGE_ID"]
    page_token = os.environ["PAGE_ACCESS_TOKEN"]
    ig_user_id = os.environ["IG_USER_ID"]
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ.get("GITHUB_REF_NAME", "main")

    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{args.image_repo_path}"

    results = {}

    try:
        results["facebook"] = post_to_facebook(page_id, page_token, args.image, args.caption)
        print(f"[facebook] posted: {results['facebook']}")
    except Exception as e:
        print(f"[facebook] FAILED: {e}", file=sys.stderr)
        results["facebook_error"] = str(e)

    try:
        results["instagram"] = post_to_instagram(ig_user_id, page_token, raw_url, args.caption)
        print(f"[instagram] posted: {results['instagram']}")
    except Exception as e:
        print(f"[instagram] FAILED: {e}", file=sys.stderr)
        results["instagram_error"] = str(e)

    print(json.dumps(results, indent=2))

    if "facebook_error" in results or "instagram_error" in results:
        sys.exit(1)


if __name__ == "__main__":
    main()
