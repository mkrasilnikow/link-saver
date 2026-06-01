import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client: Groq | None = None

MAX_PROMPT_CHARS = 6000

SYSTEM_PROMPT = """
You are a content classifier. Given the title and body text of a web page or video,
return ONLY valid JSON with no explanation.

Response format:
{"tags": ["tag1", "tag2"], "type": "article|video|reel|other"}

Rules:
- Read the provided body text carefully and base the tags on what the content is actually about.
- tags: 1-5 specific, lowercase, topic-based tags in the same language as the content (Russian or English).
  Prefer concrete topics (java, spring, postgresql, нейросети, геймдизайн) over generic ones (программирование, технологии).
- type: "video" for YouTube/video content, "reel" for short-form, "article" for text articles, "other" otherwise.
"""


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _client


def get_tags_and_type(
    title: str,
    description: str,
    content: str = "",
    content_type_hint: str = "",
) -> dict:
    client = _get_client()

    # Prefer the full article body; fall back to the meta description.
    body = content.strip() or description.strip()

    user_content = f"Title: {title}\n\nBody:\n{body[:MAX_PROMPT_CHARS]}"
    if content_type_hint:
        user_content += f"\n\nContent type hint: {content_type_hint}"

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
