# AWS Scheduled Discogs Sync

This setup keeps your website static while auto-refreshing `recordList.html` from Discogs.

## Architecture

- EventBridge schedule triggers a Lambda every 6 hours (default).
- Lambda pulls your Discogs collection (folder `0` by default).
- Lambda renders the same HTML format used locally.
- Lambda writes `recordList.html` to your S3 site bucket.

## Prerequisites

- AWS CLI configured (`aws configure`)
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Existing S3 website bucket (or S3 + CloudFront static host)

## 1) Create a secret for the Discogs token

Store your token in AWS Secrets Manager as JSON:

```bash
aws secretsmanager create-secret \
  --name discogs/api-token \
  --secret-string '{"token":"YOUR_DISCOGS_TOKEN"}'
```

If the secret already exists, update it:

```bash
aws secretsmanager put-secret-value \
  --secret-id discogs/api-token \
  --secret-string '{"token":"YOUR_DISCOGS_TOKEN"}'
```

Capture its ARN for deployment:

```bash
SECRET_ARN=$(aws secretsmanager describe-secret \
  --secret-id discogs/api-token \
  --query 'ARN' \
  --output text)
```

## 2) Build and deploy

From repo root:

```bash
cd aws
sam build --template-file template.yaml

sam deploy \
  --template-file .aws-sam/build/template.yaml \
  --stack-name herbadis-discogs-sync \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    TargetBucketName=YOUR_BUCKET_NAME \
    TargetObjectKey=recordList.html \
    DiscogsUsername=oldgodnewgod \
    DiscogsFolderId=0 \
    DiscogsTokenSecretArn=$SECRET_ARN \
    ScheduleExpression='rate(6 hours)'
```

## 3) Manually test once

```bash
aws lambda invoke \
  --function-name herbadis-discogs-sync-DiscogsSyncFunction \
  --payload '{}' \
  /tmp/discogs-sync-result.json

cat /tmp/discogs-sync-result.json
```

## Notes

- The default schedule is every 6 hours (matches Discogs API freshness expectations).
- Keep the token in Secrets Manager only; do not hardcode it in the site.
- If you front with CloudFront, invalidate cache for `/recordList.html` after each sync or keep a short TTL.
