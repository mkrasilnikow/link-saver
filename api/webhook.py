import os
import re
import json
from http.server import BaseHTTPRequestHandler

import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
ALLOWED_USER_ID = int(os.environ.get("ALLOWED_USER_ID", "0"))

TG_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

URL_REGEX = re.compile(r"https?://[^\s]+")
UUID_REGEX = re.compile(r"id:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.I)
_TRAILING_JUNK = ").,;!?'\"<>»"


def extract_url(text: str) -> str | None:
    """Find the first URL anywhere in the message, stripping wrapping punctuation."""
    match = URL_REGEX.search(text)
    if not match:
        return None
    url = match.group(0)
    while url and url[-1] in _TRAILING_JUNK:
        if url[-1] == ")" and url.count("(") >= url.count(")"):
            break
        url = url[:-1]
    return url or None


def extract_link_id(text: str) -> str | None:
    """Extract the embedded link UUID from a bot confirmation message."""
    match = UUID_REGEX.search(text)
    return match.group(1) if match else None


def parse_reply_action(text: str) -> dict:
    """Parse a reply to a save confirmation.

    Supported formats (case-insensitive, combinable):
      +                     → mark as read
      openai, ai            → add tags
      : ai                  → set folder
      openai, ai : tech     → add tags + set folder
      + : tech              → mark as read + set folder
    """
    text = text.strip()
    action: dict = {}

    # Split off folder part (everything after the first ':')
    folder_part = ""
    if ":" in text:
        idx = text.index(":")
        folder_part = text[idx + 1:].strip().lower()
        text = text[:idx].strip()

    if folder_part:
        action["folder"] = folder_part

    # Process left side: check for '+' token and tags
    tokens = [t.strip().lstrip("#") for t in re.split(r"[,\s]+", text) if t.strip()]
    tags = []
    for token in tokens:
        if token == "+":
            action["read"] = True
        elif token:
            tags.append(token.lower())

    if tags:
        action["tags"] = tags

    return action


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
    folder = link.get("folder")
    folder_line = f"\n📁 {folder}" if folder else ""
    # Embed ID so replies can reference this link; shown as small code block.
    link_id = link.get("id", "")
    return (
        f"✅ <b>{title[:100]}</b>\n"
        f"🏷 {tag_str}\n"
        f"📌 Тип: {type_label}{folder_line}\n"
        f"<code>id:{link_id}</code>"
    )


def handle_url(chat_id: int, url: str) -> None:
    from lib.parser import parse_url
    from lib.tagger import get_tags_and_type
    from lib import storage

    existing_tags = [t["tag"] for t in storage.get_tags_with_counts()]

    parsed = parse_url(url)
    tagged = get_tags_and_type(
        parsed.get("title", ""),
        parsed.get("description", ""),
        parsed.get("content", ""),
        parsed.get("type", ""),
        existing_tags=existing_tags,
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


def handle_reply(chat_id: int, reply_text: str, original_text: str) -> None:
    """Handle a reply to a save confirmation message."""
    from lib import storage

    link_id = extract_link_id(original_text)
    if not link_id:
        return

    action = parse_reply_action(reply_text)
    if not action:
        send_message(chat_id, "Не понял действие. Примеры: тег1, тег2 / + / : папка")
        return

    parts = []

    if action.get("tags"):
        storage.update_link_tags(link_id, action["tags"])
        added = " ".join(f"#{t}" for t in action["tags"])
        parts.append(f"🏷 Теги добавлены: {added}")

    if action.get("folder"):
        storage.update_link_folder(link_id, action["folder"])
        parts.append(f"📁 Папка: {action['folder']}")

    if action.get("read"):
        storage.update_link_status(link_id, "read")
        parts.append("✅ Отмечено как прочитанное")

    if parts:
        send_message(chat_id, "\n".join(parts))
    else:
        send_message(chat_id, "Не понял действие. Примеры: тег1, тег2 / + / : папка")


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
            folder = f"📁 {lnk['folder']}" if lnk.get("folder") else ""
            lines.append(
                f'{status_icon} <a href="{lnk["url"]}">{(lnk.get("title") or lnk["url"])[:60]}</a>\n'
                f"   {tags} {folder}\n"
                f"   <code>{lnk['id']}</code>"
            )
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

    elif cmd == "/folders":
        folders = storage.get_folders()
        if not folders:
            send_message(chat_id, "Папок пока нет.")
            return
        lines = [f"📁 {f['folder']} — {f['count']}" for f in folders]
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
            "Отправь URL — я сохраню и расставлю теги.\n\n"
            "<b>Команды:</b>\n"
            "/list — последние 10 ссылок\n"
            "/list #java — фильтр по тегу\n"
            "/search &lt;запрос&gt; — поиск\n"
            "/tags — все теги\n"
            "/folders — все папки\n"
            "/read &lt;id&gt; — отметить прочитанным\n"
            "/delete &lt;id&gt; — удалить\n\n"
            "<b>Reply на подтверждение:</b>\n"
            "openai, ai — добавить теги\n"
            "+ — отметить прочитанным\n"
            ": папка — переместить в папку\n"
            "openai : ai — теги + папка"
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
        return

    # Reply to a save confirmation → edit the saved link
    reply_to = message.get("reply_to_message")
    if reply_to and reply_to.get("from", {}).get("id") == int(TELEGRAM_TOKEN.split(":")[0]) if TELEGRAM_TOKEN else False:
        original_text = (reply_to.get("text") or "").strip()
        if extract_link_id(original_text):
            handle_reply(chat_id, text, original_text)
            return

    url = extract_url(text)
    if url:
        send_message(chat_id, "⏳ Обрабатываю...")
        try:
            handle_url(chat_id, url)
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
