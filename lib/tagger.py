import os
import json
import sys
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

MODEL = "llama-3.3-70b-versatile"

_client: Groq | None = None

SYSTEM_PROMPT = """
You are a precise content classifier and tagger. Given the title and body text of a web page or video, return ONLY valid JSON.

Response format:
{"tags": ["tag1", "tag2"], "type": "article|video|reel|other"}

Rules:
- tags: 1-5 SPECIFIC, lowercase topic tags in the same language as the content (Russian or English).
  Use concrete terms, NOT generic ones:
    ❌ Bad:  программирование, технологии, разработка, software, development
    ✅ Good: python, django, postgresql, kubernetes, нейросети, llm, gamedev, react
- type: "video" for YouTube, "reel" for short-form vertical video, "article" for text, "other" otherwise.
- If a list of preferred tags is provided, reuse them when they genuinely fit — don't invent synonyms.

Examples:

Input: Title: "Building a REST API with Spring Boot and PostgreSQL"
       Body: "In this tutorial we'll create a production-ready REST API using Spring Boot 3, JPA, and a PostgreSQL database..."
Output: {"tags": ["spring-boot", "postgresql", "java", "rest-api"], "type": "article"}

Input: Title: "Как настроить Kubernetes на VPS — полный гайд"
       Body: "В этой статье разберём установку k8s кластера с нуля: kubeadm, flannel, ingress-nginx, cert-manager..."
Output: {"tags": ["kubernetes", "devops", "linux", "vps"], "type": "article"}

Input: Title: "I Tried Every AI Coding Assistant for 30 Days"
       Body: "Copilot, Cursor, Continue, Codeium — I used all of them on real projects. Here are my findings..."
Output: {"tags": ["ai", "copilot", "cursor", "productivity"], "type": "article"}

Input: Title: "Оформление тайской визы DTV — личный опыт"
       Body: "Рассказываю как мы с семьёй получили Destination Thailand Visa: документы, банковская выписка, страховка..."
Output: {"tags": ["таиланд", "виза", "эмиграция", "dtv"], "type": "article"}
"""

MAX_PROMPT_CHARS = 6000


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
    existing_tags: list[str] | None = None,
) -> dict:
    client = _get_client()

    body = content.strip() or description.strip()

    user_parts = [f"Title: {title}", f"\nBody:\n{body[:MAX_PROMPT_CHARS]}"]

    if existing_tags:
        vocab_tags = _filter_vocab(existing_tags)[:60]
        if vocab_tags:
            vocab = ", ".join(vocab_tags)
            user_parts.append(f"\nPreferred tag vocabulary (reuse when relevant): {vocab}")

    if content_type_hint and content_type_hint != "other":
        user_parts.append(f"\nContent type hint: {content_type_hint}")

    user_content = "".join(user_parts)

    _log("TAGGER INPUT", {
        "model": MODEL,
        "title": title[:120],
        "body_chars": len(body),
        "existing_tags_count": len(existing_tags) if existing_tags else 0,
        "content_type_hint": content_type_hint,
    })
    _log("TAGGER PROMPT (user)", user_content[:800])

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        _log("TAGGER RAW RESPONSE", raw)

        result = json.loads(raw)
        tags = [t.lower().strip() for t in result.get("tags", [])[:5]]
        content_type = result.get("type", "other")
        if content_type not in ("article", "video", "reel", "other"):
            content_type = "other"

        _log("TAGGER RESULT", {"tags": tags, "type": content_type})
        return {"tags": tags, "type": content_type}

    except Exception as e:
        _log("TAGGER ERROR", str(e))
        return {"tags": [], "type": content_type_hint or "other"}


_GENERIC_TAGS = frozenset({
    "other", "general information", "computing", "software", "technology",
    "технологии", "программирование", "разработка", "development",
    "api", "backend", "frontend", "web", "cloud", "ai", "data",
})


def _filter_vocab(tags: list[str]) -> list[str]:
    return [t for t in tags if t not in _GENERIC_TAGS and len(t) > 2]


def _log(label: str, value: object) -> None:
    print(f"[tagger] {label}: {value}", file=sys.stdout, flush=True)
