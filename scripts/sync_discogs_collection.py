#!/usr/bin/env python3
"""Generate a record list HTML page from a Discogs collection."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

API_BASE = "https://api.discogs.com"
DEFAULT_USER_AGENT = "herbadis-website-discogs-sync/1.0"
BUCKET_ORDER = ['5"', '7"', '8"', '9"', '10"', '11"', '12"', "CD", "Cassette", "Other"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync Discogs collection data into a static HTML record list."
    )
    parser.add_argument("--username", help="Discogs username")
    parser.add_argument(
        "--folder-id",
        type=int,
        default=0,
        help="Discogs collection folder id (0 is the All folder)",
    )
    parser.add_argument("--token", help="Discogs personal access token")
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent header for Discogs API requests",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=100,
        help="Items to fetch per page from Discogs API",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.1,
        help="Delay between paginated API calls",
    )
    parser.add_argument(
        "--input-json",
        help=(
            "Use local JSON instead of API. Accepts either a full Discogs page payload "
            "with 'releases' or a raw release list."
        ),
    )
    parser.add_argument(
        "--output",
        default="recordList.html",
        help="Output HTML path",
    )
    return parser.parse_args()


def request_json(url: str, user_agent: str, token: str | None) -> dict:
    headers = {"User-Agent": user_agent}
    if token:
        headers["Authorization"] = f"Discogs token={token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404 and "User does not exist" in body:
            raise RuntimeError(
                "Discogs user was not found. Pass the exact Discogs username."
            ) from exc
        raise RuntimeError(f"Discogs API error {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc


def fetch_collection_releases(
    username: str,
    folder_id: int,
    token: str | None,
    user_agent: str,
    per_page: int,
    sleep_seconds: float,
) -> list[dict]:
    releases: list[dict] = []
    page = 1
    total_pages = 1

    while page <= total_pages:
        query = urllib.parse.urlencode({"per_page": per_page, "page": page})
        path = (
            f"/users/{urllib.parse.quote(username)}/collection/folders/"
            f"{folder_id}/releases?{query}"
        )
        payload = request_json(f"{API_BASE}{path}", user_agent=user_agent, token=token)
        releases.extend(payload.get("releases", []))
        pagination = payload.get("pagination", {})
        total_pages = int(pagination.get("pages", 1))
        page += 1
        if page <= total_pages:
            time.sleep(sleep_seconds)

    return releases


def load_releases_from_json(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, dict) and "releases" in data and isinstance(data["releases"], list):
        return data["releases"]
    if isinstance(data, list):
        return data
    raise RuntimeError("Unsupported JSON structure. Expected releases list or payload with releases.")


def normalize_artist_name(name: str) -> str:
    # Discogs often appends disambiguation like "Artist (3)".
    return re.sub(r"\s+\(\d+\)$", "", name).strip()


def build_artist_string(artists: list[dict]) -> str:
    if not artists:
        return "Unknown Artist"
    names = [normalize_artist_name(a.get("name", "")) for a in artists]
    names = [n for n in names if n]
    return ", ".join(names) if names else "Unknown Artist"


def format_details(format_rows: list[dict]) -> tuple[list[str], list[str]]:
    tokens: list[str] = []
    formatted: list[str] = []

    for entry in format_rows:
        name = (entry.get("name") or "").strip()
        qty = (entry.get("qty") or "").strip()
        descriptions = [d.strip() for d in (entry.get("descriptions") or []) if d]

        if name:
            tokens.append(name.lower())
        tokens.extend(d.lower() for d in descriptions)

        parts: list[str] = []
        if qty and qty != "1":
            parts.append(f"{qty}x")
        if name:
            parts.append(name)
        if descriptions:
            parts.append(", ".join(descriptions))
        if parts:
            formatted.append(" ".join(parts))

    return tokens, formatted


def detect_bucket(tokens: list[str]) -> str:
    joined = " ".join(tokens)

    for inch in ['5"', '7"', '8"', '9"', '10"', '11"', '12"']:
        if inch.lower() in joined:
            return inch

    inch_match = re.search(r"(\d{1,2})\s*(?:\"|in)", joined)
    if inch_match:
        inferred = f'{inch_match.group(1)}"'
        if inferred in BUCKET_ORDER:
            return inferred

    if "lp" in joined:
        return '12"'
    if "cd" in joined:
        return "CD"
    if "cassette" in joined or "tape" in joined:
        return "Cassette"
    return "Other"


def build_discogs_url(release: dict, basic: dict) -> str | None:
    uri = basic.get("uri") or release.get("uri")
    if isinstance(uri, str) and uri.strip():
        clean_uri = uri.strip()
        if clean_uri.startswith("http://") or clean_uri.startswith("https://"):
            return clean_uri
        if clean_uri.startswith("/"):
            return f"https://www.discogs.com{clean_uri}"
        return f"https://www.discogs.com/{clean_uri}"

    resource_url = basic.get("resource_url") or release.get("resource_url")
    if isinstance(resource_url, str):
        match = re.search(r"/(releases|masters)/(\d+)", resource_url)
        if match:
            singular = "release" if match.group(1) == "releases" else "master"
            return f"https://www.discogs.com/{singular}/{match.group(2)}"

    basic_id = basic.get("id") or release.get("id")
    if isinstance(basic_id, int):
        return f"https://www.discogs.com/release/{basic_id}"
    if isinstance(basic_id, str) and basic_id.isdigit():
        return f"https://www.discogs.com/release/{basic_id}"
    return None


def normalize_release(release: dict) -> dict:
    basic = release.get("basic_information", {})
    artist = build_artist_string(basic.get("artists") or [])
    title = (basic.get("title") or "Untitled").strip()
    year = basic.get("year")
    labels = [x.get("name", "").strip() for x in (basic.get("labels") or []) if x.get("name")]
    tokens, formatted_formats = format_details(basic.get("formats") or [])
    bucket = detect_bucket(tokens)
    discogs_url = build_discogs_url(release, basic)

    return {
        "artist": artist,
        "title": title,
        "year": int(year) if isinstance(year, int) and year > 0 else None,
        "labels": labels,
        "formats": formatted_formats,
        "bucket": bucket,
        "discogs_url": discogs_url,
    }


def list_line(item: dict) -> str:
    parts = [item["artist"], item["title"]]
    if item["labels"]:
        parts.append(", ".join(item["labels"]))
    if item["formats"]:
        parts.append("; ".join(item["formats"]))
    if item["year"]:
        parts.append(str(item["year"]))
    return " / ".join(parts)


def render_html(username: str, folder_id: int, releases: list[dict]) -> str:
    normalized = [normalize_release(release) for release in releases]
    buckets: dict[str, list[dict]] = defaultdict(list)
    for item in normalized:
        buckets[item["bucket"]].append(item)

    for key in buckets:
        buckets[key].sort(key=lambda item: (item["artist"].casefold(), item["title"].casefold()))

    synced = dt.datetime.now().strftime("%B %d, %Y %H:%M")
    total = len(normalized)

    list_html: list[str] = []
    list_html.append('<li class="section-heading"><strong>Discogs Collection Sync</strong></li>')
    list_html.append(f'<li class="meta">User: {html.escape(username)}</li>')
    list_html.append(f'<li class="meta">Synced: {html.escape(synced)}</li>')
    list_html.append(f'<li class="meta">Total Records: {total}</li>')
    list_html.append('<li class="spacer" aria-hidden="true"></li>')
    list_html.append('<li class="divider" role="separator" aria-hidden="true"></li>')

    for bucket in BUCKET_ORDER:
        items = buckets.get(bucket)
        if not items:
            continue
        list_html.append('<li class="spacer" aria-hidden="true"></li>')
        list_html.append(f'<li class="section-heading"><strong>{html.escape(bucket)}</strong></li>')
        list_html.append(f'<li class="meta">{len(items)} release(s)</li>')
        list_html.append('<li class="spacer" aria-hidden="true"></li>')
        for item in items:
            line = html.escape(list_line(item))
            if item.get("discogs_url"):
                url = html.escape(item["discogs_url"], quote=True)
                list_html.append(
                    f'<li class="record-item"><a href="{url}" target="_blank" rel="noopener noreferrer">{line}</a></li>'
                )
            else:
                list_html.append(f'<li class="record-item">{line}</li>')

    list_body = "\n".join(f"            {row}" for row in list_html)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Record List</title>
<style>
:root {{
  --bg: #17171a;
  --panel: rgba(36, 36, 41, 0.92);
  --text: #ffffff;
  --muted: #c5c5cc;
  --accent: #00d9d9;
  --line: rgba(255, 255, 255, 0.24);
}}
* {{
  box-sizing: border-box;
}}
body {{
  background:
    radial-gradient(circle at top left, #2b2b31 0%, transparent 45%),
    radial-gradient(circle at bottom right, #141417 0%, transparent 40%),
    var(--bg);
  color: var(--text);
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  margin: 0;
  min-height: 100vh;
}}
.record-list-page {{
  align-items: stretch;
  display: flex;
  justify-content: center;
  min-height: 100vh;
  padding: clamp(16px, 3vw, 36px);
}}
.record-list-panel {{
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: 0 22px 48px rgba(0, 0, 0, 0.35);
  overflow: hidden;
  width: min(1080px, 100%);
}}
.record-list-header {{
  border-bottom: 1px solid var(--line);
  padding: clamp(16px, 2.8vw, 26px);
  text-align: center;
}}
.record-list-header h1 {{
  font-size: clamp(20px, 3vw, 30px);
  font-weight: 200;
  letter-spacing: 0.14em;
  margin: 0;
  text-transform: uppercase;
}}
.record-list {{
  list-style: none;
  margin: 0;
  max-height: calc(100vh - 180px);
  overflow: auto;
  padding: 18px clamp(16px, 2.5vw, 30px) 28px;
}}
.record-list li {{
  color: var(--text);
  font-size: clamp(12px, 1.15vw, 16px);
  line-height: 1.5;
  padding: 7px 0;
  transition: color 0.2s ease;
}}
.record-list .record-item {{
  color: var(--text);
}}
.record-list .record-item a {{
  color: inherit;
  display: block;
  text-decoration: none;
}}
.record-list .record-item:hover,
.record-list .record-item a:hover,
.record-list .record-item a:focus-visible {{
  color: var(--accent);
}}
.record-list .section-heading {{
  font-size: clamp(13px, 1.4vw, 18px);
  letter-spacing: 0.06em;
  padding: 4px 0;
  text-align: center;
  text-transform: uppercase;
}}
.record-list .section-heading strong {{
  font-weight: 400;
}}
.record-list .meta {{
  color: var(--muted);
  font-size: clamp(12px, 1.1vw, 15px);
  margin: 0;
  padding: 2px 0;
  text-align: center;
}}
.record-list .divider {{
  border-top: 1px solid var(--line);
  height: 0;
  margin: 10px auto 12px;
  padding: 0;
  width: min(460px, 100%);
}}
.record-list .spacer {{
  height: 12px;
  padding: 0;
}}
@media(max-width: 768px) {{
  .record-list {{
    max-height: none;
  }}
}}
@media (hover: none) {{
  .record-list .record-item:hover,
  .record-list .record-item a:hover {{
    color: var(--text);
  }}
}}
@media (prefers-reduced-motion: reduce) {{
  .record-list li {{
    transition: none;
  }}
}}
</style>
</head>
<body>
<main class="record-list-page">
  <section class="record-list-panel" aria-label="Record collection">
    <header class="record-list-header">
      <h1>Record List</h1>
    </header>
    <ul class="record-list">
{list_body}
    </ul>
  </section>
</main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    try:
        if args.input_json:
            releases = load_releases_from_json(args.input_json)
            username = args.username or "discogs-user"
        else:
            if not args.username:
                print("error: --username is required unless --input-json is used", file=sys.stderr)
                return 2
            releases = fetch_collection_releases(
                username=args.username,
                folder_id=args.folder_id,
                token=args.token,
                user_agent=args.user_agent,
                per_page=args.per_page,
                sleep_seconds=args.sleep_seconds,
            )
            username = args.username

        html_output = render_html(username=username, folder_id=args.folder_id, releases=releases)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(html_output)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: could not write output file '{args.output}': {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output} with {len(releases)} release(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
