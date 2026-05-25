import os
from datetime import date
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv

load_dotenv()


def build_markdown(links: list[dict]) -> str:
    today = date.today().strftime("%Y-%m-%d")
    lines = [f"# LinkSaver Export — {today}\n"]

    grouped: dict[str, list] = {}
    untagged: list = []

    for lnk in links:
        tags = lnk.get("tags") or []
        if tags:
            for tag in tags:
                grouped.setdefault(tag, []).append(lnk)
        else:
            untagged.append(lnk)

    for tag in sorted(grouped.keys()):
        tag_links = grouped[tag]
        lines.append(f"\n## #{tag} ({len(tag_links)})\n")
        for lnk in tag_links:
            title = lnk.get("title") or lnk["url"]
            content_type = lnk.get("type", "other")
            created = (lnk.get("created_at") or "")[:10]
            lines.append(f"- [{title}]({lnk['url']}) — {content_type} — {created}")

    if untagged:
        lines.append(f"\n## без тегов ({len(untagged)})\n")
        for lnk in untagged:
            title = lnk.get("title") or lnk["url"]
            created = (lnk.get("created_at") or "")[:10]
            lines.append(f"- [{title}]({lnk['url']}) — {created}")

    return "\n".join(lines)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        from lib import storage

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        fmt = (params.get("format") or ["md"])[0]
        tag = (params.get("tag") or [None])[0]

        links = storage.get_links(tag=tag, limit=1000)

        if fmt == "md":
            content = build_markdown(links).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="links-export.md"',
            )
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Unsupported format. Use ?format=md")

    def log_message(self, format, *args):
        pass
