import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]
        _client = create_client(url, key)
    return _client


def insert_link(data: dict) -> dict:
    client = get_client()
    result = client.table("links").insert(data).execute()
    return result.data[0]


def get_links(
    tag: str | None = None,
    status: str | None = None,
    folder: str | None = None,
    limit: int = 10,
) -> list[dict]:
    client = get_client()
    query = client.table("links").select("*").order("created_at", desc=True)

    if tag:
        query = query.contains("tags", [tag])
    if status:
        query = query.eq("status", status)
    if folder:
        query = query.eq("folder", folder)

    result = query.limit(limit).execute()
    return result.data


def search_links(query_text: str, limit: int = 10) -> list[dict]:
    client = get_client()
    result = (
        client.table("links")
        .select("*")
        .text_search("fts", query_text)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


def get_tags_with_counts() -> list[dict]:
    client = get_client()
    result = client.table("links").select("tags").execute()

    counts: dict[str, int] = {}
    for row in result.data:
        for tag in row.get("tags") or []:
            counts[tag] = counts.get(tag, 0) + 1

    return sorted(
        [{"tag": t, "count": c} for t, c in counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )


def get_folders() -> list[dict]:
    client = get_client()
    result = (
        client.table("links")
        .select("folder")
        .not_.is_("folder", "null")
        .execute()
    )

    counts: dict[str, int] = {}
    for row in result.data:
        f = row.get("folder")
        if f:
            counts[f] = counts.get(f, 0) + 1

    return sorted(
        [{"folder": f, "count": c} for f, c in counts.items()],
        key=lambda x: x["folder"],
    )


def update_link_status(link_id: str, status: str) -> dict:
    client = get_client()
    result = client.table("links").update({"status": status}).eq("id", link_id).execute()
    return result.data[0]


def update_link_tags(link_id: str, add_tags: list[str]) -> dict:
    client = get_client()
    existing = client.table("links").select("tags").eq("id", link_id).execute()
    current_tags: list[str] = existing.data[0].get("tags") or [] if existing.data else []
    merged = list(dict.fromkeys(current_tags + [t.lower() for t in add_tags]))
    result = client.table("links").update({"tags": merged}).eq("id", link_id).execute()
    return result.data[0]


def update_link_folder(link_id: str, folder: str) -> dict:
    client = get_client()
    result = (
        client.table("links")
        .update({"folder": folder.strip().lower()})
        .eq("id", link_id)
        .execute()
    )
    return result.data[0]


def delete_link(link_id: str) -> None:
    client = get_client()
    client.table("links").delete().eq("id", link_id).execute()


def get_link_by_id(link_id: str) -> dict | None:
    client = get_client()
    result = client.table("links").select("*").eq("id", link_id).execute()
    return result.data[0] if result.data else None
