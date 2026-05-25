import os
import json
import asyncio
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler

import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
ALLOWED_USER_ID = int(os.environ.get("ALLOWED_USER_ID", "0"))

TG_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def send_message(chat_id: int, text: str, parse_mode: str = "HTML") -> None:
    httpx.post(
        f"{TG_API}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
        timeout=5,
    )


def format_link_confirmation(link: dict) -> str:
    tag_str = " ".join(f"#{t}" for t in link.get("tags", []))
    type_labels = {"article": "статья", "video": "видео", "reel": "reels", "other": "другое"}
    type_label = type_labels.get(link.get("type", "other"), "другое")
    title = link.get("title") or link.get("url", "")
    return f"✅ <b>{title[:100]}</b>\n🏷 {tag_str}\n📌 Тип: {type_label}"


def handle_url(chat_id: int, url: str) -> None:
    from lib.parser import parse_url
    from lib.tagger import get_tags_and_type
    from lib import storage

    parsed = parse_url(url)
    tagged = get_tags_and_type(
        parsed.get("title", ""),
        parsed.get("description", ""),
        parsed.get("type", ""),
    )

    content_type = tagged.get("type") or parsed.get("type", "other")

    link_data = {
        "url": url,
        "title": parsed.get("title") or None,
        "description": parsed.get("description") or None,
        "thumbnail": parsed.get("thumbnail") or None,
        "type": content_type,
        "tags": tagged.get("tags", []),
        "status": "unread",
        "source": parsed.get("source", "web"),
    }

    saved = storage.insert_link(link_data)
    send_message(chat_id, format_link_confirmation({**link_data, **saved}))


def handle_command(chat_id: int, text: str) -> None:
    from lib import storage

    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/list":
        tag = arg.lstrip("#") if arg else None
        links = storage.get_links(tag=tag, limit=10)
        if not links:
            send_message(chat_id, "Ничего не найдено.")
            return
        lines = []
        for lnk in links:
            status_icon = "📖" if lnk.get("status") == "read" else "🔖"
            tags = " ".join(f"#{t}" for t in (lnk.get("tags") or []))
            lines.append(f'{status_icon} <a href="{lnk["url"]}">{(lnk.get("title") or lnk["url"])[:60]}</a>\n   {tags}\n   <code>{lnk["id"]}</code>')
        send_message(chat_id, "\n\n".join(lines))

    elif cmd == "/search":
        if not arg:
            send_message(chat_id, "Использование: /search <запрос>")
            return
        links = storage.search_links(arg, limit=10)
        if not links:
            send_message(chat_id, "Ничего не найдено.")
            return
        lines = [f'🔍 <a href="{lnk["url"]}">{(lnk.get("title") or lnk["url"])[:60]}</a>' for lnk in links]
        send_message(chat_id, "\n".join(lines))

    elif cmd == "/tags":
        tags = storage.get_tags_with_counts()
        if not tags:
            send_message(chat_id, "Тегов пока нет.")
            return
        lines = [f"#{t['tag']} — {t['count']}" for t in tags]
        send_message(chat_id, "\n".join(lines))

    elif cmd == "/read":
        if not arg:
            send_message(chat_id, "Использование: /read <id>")
            return
        storage.update_link_status(arg, "read")
        send_message(chat_id, "✅ Отмечено как прочитанное.")

    elif cmd == "/delete":
        if not arg:
            send_message(chat_id, "Использование: /delete <id>")
            return
        storage.delete_link(arg)
        send_message(chat_id, "🗑 Удалено.")

    elif cmd == "/start" or cmd == "/help":
        help_text = (
            "📚 <b>LinkSaver Bot</b>\n\n"
            "Отправь URL — я сохраню и автоматически расставлю теги.\n\n"
            "<b>Команды:</b>\n"
            "/list — последние 10 ссылок\n"
            "/list #java — фильтр по тегу\n"
            "/search &lt;запрос&gt; — полнотекстовый поиск\n"
            "/tags — все теги с количеством\n"
            "/read &lt;id&gt; — отметить как прочитанное\n"
            "/delete &lt;id&gt; — удалить ссылку"
        )
        send_message(chat_id, help_text)

    else:
        send_message(chat_id, "Неизвестная команда. Отправь /help.")


def process_update(update: dict) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    user_id = message.get("from", {}).get("id")
    if user_id != ALLOWED_USER_ID:
        return

    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()

    if not text:
        return

    if text.startswith("/"):
        handle_command(chat_id, text)
    elif text.startswith("http://") or text.startswith("https://"):
        send_message(chat_id, "⏳ Обрабатываю...")
        try:
            handle_url(chat_id, text)
        except Exception as e:
            send_message(chat_id, f"❌ Ошибка при обработке ссылки: {e}")
    else:
        send_message(chat_id, "Отправь ссылку (http/https) или команду /help.")


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        secret_header = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if WEBHOOK_SECRET and secret_header != WEBHOOK_SECRET:
            self.send_response(403)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

        try:
            update = json.loads(body)
            process_update(update)
        except Exception:
            pass

    def log_message(self, format, *args):
        pass
