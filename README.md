# social-auto-poster

Automatically generates a branded quote-card image and posts it to a
Facebook Page and its linked Instagram Business account, on a schedule,
via GitHub Actions.

## How it works

1. `.github/workflows/post.yml` fires on a cron schedule (or manually via
   the Actions tab's "Run workflow" button).
2. `poster/scripts/run.py` picks the next unposted entry from
   `poster/content/queue.json`.
3. `poster/scripts/generate_image.py` renders that entry's text into a
   1600×1600 quote-card PNG using the bundled fonts in `poster/fonts/`
   and the palette in `poster/content/theme.json` — no external services
   involved.
4. The image is committed to `poster/content/posted/` and pushed, so it's
   reachable at a public `raw.githubusercontent.com` URL (Instagram's API
   requires a public image URL; Facebook's doesn't, but we use the same
   one for consistency).
5. `poster/scripts/post_to_meta.py` publishes it to both platforms via the
   Meta Graph API, using credentials from GitHub's encrypted repo secrets.
6. `poster/content/state.json` is updated so the same entry isn't posted
   twice.

## One-time setup

In this repo's **Settings → Secrets and variables → Actions**, add three
repository secrets:

| Secret name | Value |
|---|---|
| `PAGE_ID` | Your Facebook Page ID |
| `PAGE_ACCESS_TOKEN` | Long-lived Page access token |
| `IG_USER_ID` | Instagram Business Account ID |

Then enable Actions for this repo (**Actions** tab → "I understand my
workflows, go ahead and enable them" if prompted).

## Adding more content

Add entries to `poster/content/queue.json`, each with a unique `id`:

```json
{
  "id": "unique-slug",
  "text": "The quote or line to render on the image",
  "attribution": "",
  "caption": "The full caption text, including hashtags, for the actual post"
}
```

The workflow always posts the oldest entry whose `id` isn't yet in
`poster/content/state.json`'s `posted_ids` list.

## Testing manually

Go to the **Actions** tab → "Auto-post to Facebook & Instagram" →
**Run workflow** to trigger a post immediately, without waiting for the
schedule.
