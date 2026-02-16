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

## AWS Scheduled Sync

If you deploy as a static site on AWS, use the included serverless setup:

- Template: `aws/template.yaml`
- Lambda code: `aws/lambda/`
- Deployment guide: `aws/README.md`

This runs a scheduled backend sync (EventBridge -> Lambda -> S3) so your frontend stays static and your Discogs token remains private in Secrets Manager.
