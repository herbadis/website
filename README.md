# website
Personal website.

## Discogs Collection Sync

Generate `recordList.html` from your Discogs collection:

```bash
python3 scripts/sync_discogs_collection.py \
  --username YOUR_DISCOGS_USERNAME \
  --token YOUR_DISCOGS_TOKEN \
  --folder-id 0 \
  --output recordList.html
```

Notes:
- `--folder-id 0` is Discogs' "All" collection folder.
- `--token` is your Discogs personal access token from Discogs account settings.
- The script sends `Authorization: Discogs token=...` and paginates through your collection.

Demo without API credentials:

```bash
python3 scripts/sync_discogs_collection.py \
  --input-json scripts/discogs_sample_collection.json \
  --username demo-user \
  --output recordList.discogs-demo.html
```

## Upload To S3 (Manual)

After generating `recordList.html`, upload these from the repo root to your S3 bucket:

- `index.html`
- `recordList.html`
- `css/`
- `assets/`
- `js/` (if you add JS files later)
