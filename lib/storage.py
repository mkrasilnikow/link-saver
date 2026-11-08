"""Google Sheets storage backend.

Stores each link as a row in a single Google Sheet. The service account
(GOOGLE_SERVICE_ACCOUNT_JSON) must have edit access to the sheet
(GOOGLE_SHEET_ID). Tags are stored as a comma-separated string in one cell.

Public API is kept identical to the previous Supabase backend so that
api/webhook.py and api/export.py need no changes.
"""
import os
import json
import base64
import uuid
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
HEADERS = [
    "id", "url", "title", "description", "thumbnail",
    "type", "tags", "folder", "status", "source", "created_at",
]

_worksheet = None


def _load_credentials_info() -> dict:
    raw = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"].strip()
    # Support either raw JSON or base64-encoded JSON (easier for Vercel env vars).
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(base64.b64decode(raw).decode("utf-8"))


def _get_worksheet():
    global _worksheet
    if _worksheet is None:
        info = _load_credentials_info()
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(os.environ["GOOGLE_SHEET_ID"])
        ws = spreadsheet.sheet1
        _ensure_headers(ws)
        _worksheet = ws
    return _worksheet


def _ensure_headers(ws) -> None:
    first_row = ws.row_values(1)
    if first_row != HEADERS:
        if not first_row:
            ws.update([HEADERS], "A1")
        # If a partial/different header exists, leave it — don't clobber data.


def _row_to_link(row: dict) -> dict:
    tags_raw = str(row.get("tags", "") or "")
    return {
        "id": str(row.get("id", "")),
        "url": row.get("url", ""),
        "title": row.get("title") or None,
        "description": row.get("description") or None,
        "thumbnail": row.get("thumbnail") or None,
        "type": row.get("type") or "other",
        "tags": [t.strip() for t in tags_raw.split(",") if t.strip()],
        "folder": row.get("folder") or None,
        "status": row.get("status") or "unread",
        "source": row.get("source") or "web",
        "created_at": str(row.get("created_at", "")),
    }


def _all_links() -> list[dict]:
    ws = _get_worksheet()
    return [_row_to_link(r) for r in ws.get_all_records()]


def _find_row(ws, link_id: str) -> int | None:
    """Return the 1-based row number for a given link id (searches column A)."""
    cell = ws.find(link_id, in_column=HEADERS.index("id") + 1)
    return cell.row if cell else None


def insert_link(data: dict) -> dict:
    ws = _get_worksheet()
    link_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    record = {
        "id": link_id,
        "url": data.get("url", ""),
        "title": data.get("title") or "",
        "description": data.get("description") or "",
        "thumbnail": data.get("thumbnail") or "",
        "type": data.get("type") or "other",
        "tags": ",".join(data.get("tags") or []),
        "folder": data.get("folder") or "",
        "status": data.get("status") or "unread",
        "source": data.get("source") or "web",
        "created_at": created_at,
    }
    ws.append_row([record[h] for h in HEADERS], value_input_option="USER_ENTERED")

    return {**data, "id": link_id, "created_at": created_at}


def get_links(
    tag: str | None = None,
    status: str | None = None,
    folder: str | None = None,
    limit: int = 10,
) -> list[dict]:
    links = _all_links()

    if tag:
        links = [l for l in links if tag in l["tags"]]
    if status:
        links = [l for l in links if l["status"] == status]
    if folder:
        links = [l for l in links if l["folder"] == folder]

    links.sort(key=lambda l: l["created_at"], reverse=True)
    return links[:limit]


def search_links(query_text: str, limit: int = 10) -> list[dict]:
    q = query_text.lower().strip()
    links = _all_links()
    matched = [
        l for l in links
        if q in (l["title"] or "").lower() or q in (l["description"] or "").lower()
    ]
    matched.sort(key=lambda l: l["created_at"], reverse=True)
    return matched[:limit]


def get_tags_with_counts() -> list[dict]:
    counts: dict[str, int] = {}
    for link in _all_links():
        for tag in link["tags"]:
            counts[tag] = counts.get(tag, 0) + 1
    return sorted(
        [{"tag": t, "count": c} for t, c in counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )


def get_folders() -> list[dict]:
    counts: dict[str, int] = {}
    for link in _all_links():
        f = link["folder"]
        if f:
            counts[f] = counts.get(f, 0) + 1
    return sorted(
        [{"folder": f, "count": c} for f, c in counts.items()],
        key=lambda x: x["folder"],
    )


def _update_cell(link_id: str, column: str, value: str) -> dict:
    ws = _get_worksheet()
    row = _find_row(ws, link_id)
    if not row:
        return {}
    ws.update_cell(row, HEADERS.index(column) + 1, value)
    return get_link_by_id(link_id) or {}


def update_link_status(link_id: str, status: str) -> dict:
    return _update_cell(link_id, "status", status)


def update_link_folder(link_id: str, folder: str) -> dict:
    return _update_cell(link_id, "folder", folder.strip().lower())


def update_link_tags(link_id: str, add_tags: list[str]) -> dict:
    link = get_link_by_id(link_id)
    if not link:
        return {}
    merged = list(dict.fromkeys(link["tags"] + [t.lower() for t in add_tags]))
    return _update_cell(link_id, "tags", ",".join(merged))


def delete_link(link_id: str) -> None:
    ws = _get_worksheet()
    row = _find_row(ws, link_id)
    if row:
        ws.delete_rows(row)


def get_link_by_id(link_id: str) -> dict | None:
    for link in _all_links():
        if link["id"] == link_id:
            return link
    return None
