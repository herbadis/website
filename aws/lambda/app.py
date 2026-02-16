"""AWS Lambda handler for scheduled Discogs -> S3 sync."""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from sync_renderer import DEFAULT_USER_AGENT, fetch_collection_releases, render_html


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _parse_secret_string(secret_text: str) -> str:
    stripped = secret_text.strip()
    if not stripped:
        raise RuntimeError("Discogs token secret is empty.")

    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Discogs token secret JSON is invalid.") from exc
        for key in ("token", "discogs_token", "api_token", "value"):
            token = payload.get(key)
            if isinstance(token, str) and token.strip():
                return token.strip()
        raise RuntimeError(
            "Discogs token secret JSON must include one of: token, discogs_token, api_token, value."
        )

    return stripped


def _load_discogs_token(secret_id: str) -> str:
    import boto3

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_id)

    if "SecretString" in response:
        return _parse_secret_string(response["SecretString"])

    secret_binary = response.get("SecretBinary")
    if secret_binary:
        decoded = base64.b64decode(secret_binary).decode("utf-8")
        return _parse_secret_string(decoded)

    raise RuntimeError("Discogs token secret contained no SecretString or SecretBinary.")


def _int_from_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _float_from_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return float(value)


def _load_releases_from_json(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict) and isinstance(payload.get("releases"), list):
        return payload["releases"]
    if isinstance(payload, list):
        return payload
    raise RuntimeError("input_json_path must point to a Discogs payload or raw releases list.")


def lambda_handler(event: dict[str, Any] | None, context: Any) -> dict[str, Any]:
    event = event or {}

    username = event.get("username") or _get_required_env("DISCOGS_USERNAME")
    folder_id = int(event.get("folder_id", _int_from_env("DISCOGS_FOLDER_ID", 0)))

    input_json_path = event.get("input_json_path")
    if input_json_path:
        releases = _load_releases_from_json(str(input_json_path))
    else:
        token = event.get("discogs_token")
        if not token:
            secret_id = _get_required_env("DISCOGS_TOKEN_SECRET_ID")
            token = _load_discogs_token(secret_id)

        releases = fetch_collection_releases(
            username=username,
            folder_id=folder_id,
            token=token,
            user_agent=os.getenv("DISCOGS_USER_AGENT", DEFAULT_USER_AGENT),
            per_page=_int_from_env("DISCOGS_PER_PAGE", 100),
            sleep_seconds=_float_from_env("DISCOGS_SLEEP_SECONDS", 1.1),
        )

    rendered = render_html(username=username, folder_id=folder_id, releases=releases)

    local_output_path = event.get("local_output_path")
    if local_output_path:
        with open(str(local_output_path), "w", encoding="utf-8") as handle:
            handle.write(rendered)
        return {
            "statusCode": 200,
            "message": "Discogs sync completed (local dry-run output).",
            "username": username,
            "folder_id": folder_id,
            "local_output_path": str(local_output_path),
            "release_count": len(releases),
        }

    target_bucket = event.get("target_bucket") or _get_required_env("TARGET_BUCKET_NAME")
    target_key = event.get("target_key") or os.getenv("TARGET_OBJECT_KEY", "recordList.html")

    import boto3

    s3_client = boto3.client("s3")
    s3_client.put_object(
        Bucket=target_bucket,
        Key=target_key,
        Body=rendered.encode("utf-8"),
        ContentType="text/html; charset=utf-8",
        CacheControl=os.getenv("TARGET_CACHE_CONTROL", "max-age=300"),
    )

    return {
        "statusCode": 200,
        "message": "Discogs sync completed.",
        "username": username,
        "folder_id": folder_id,
        "target_bucket": target_bucket,
        "target_key": target_key,
        "release_count": len(releases),
    }
