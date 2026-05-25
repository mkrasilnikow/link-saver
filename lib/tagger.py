import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client: Groq | None = None

SYSTEM_PROMPT = """
You are a content classifier. Given a title and description of a web page or video,
return ONLY valid JSON with no explanation.

Response format:
{"tags": ["tag1", "tag2"], "type": "article|video|reel|other"}

Rules:
- tags: 1-5 lowercase tags, in the same language as the content (Russian or English)
- type: "video" for YouTube/video content, "reel" for short-form, "article" for text, "other" otherwise
- tags should be topic-based: технологии, java, spring, игры, gamedev, дизайн, etc.
"""


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _client


def get_tags_and_type(title: str, description: str, content_type_hint: str = "") -> dict:
    client = _get_client()

    user_content = f"Title: {title}\nDescription: {description[:800]}"
    if content_type_hint:
        user_content += f"\nContent type hint: {content_type_hint}"

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=200,
        )
        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)
        tags = [t.lower().strip() for t in result.get("tags", [])[:5]]
        content_type = result.get("type", "other")
        if content_type not in ("article", "video", "reel", "other"):
            content_type = "other"
        return {"tags": tags, "type": content_type}
    except Exception:
        return {"tags": [], "type": content_type_hint or "other"}
