import os
import re
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_REGEX = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})"
)
YOUTUBE_BOILERPLATE = "About Press Copyright Contact us Creators Advertise"

MAX_CONTENT_CHARS = 6000
NOISE_TAGS = ["script", "style", "noscript", "nav", "header", "footer",
              "aside", "form", "svg", "iframe", "button"]

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "sec-ch-ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def _fallback_title(url: str) -> str:
    try:
        host = urlparse(url).hostname or url
        return host.removeprefix("www.")
    except Exception:
        return url[:80]


def _extract_video_id(url: str) -> str | None:
    match = YOUTUBE_REGEX.search(url)
    return match.group(1) if match else None


def _extract_article_text(soup: BeautifulSoup) -> str:
    for tag in soup(NOISE_TAGS):
        tag.decompose()

    container = soup.find("article") or soup.find("main") or soup.body or soup

    paragraphs = [p.get_text(" ", strip=True) for p in container.find_all("p")]
    text = " ".join(p for p in paragraphs if len(p) > 30)

    if len(text) < 200:
        text = container.get_text(" ", strip=True)

    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_CONTENT_CHARS]


def _parse_youtube(url: str) -> dict:
    video_id = _extract_video_id(url)
    if not video_id or not YOUTUBE_API_KEY:
        return _parse_web(url)

    api_url = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet&id={video_id}&key={YOUTUBE_API_KEY}"
    )
    try:
        response = httpx.get(api_url, timeout=10)
        response.raise_for_status()
        items = response.json().get("items", [])
        if not items:
            return _parse_web(url)

        snippet = items[0]["snippet"]
        is_short = "shorts" in url
        return {
            "title": snippet.get("title", ""),
            "description": snippet.get("description", "")[:500],
            "content": "",
            "thumbnail": snippet.get("thumbnails", {}).get("maxres", {}).get("url")
                or snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "type": "reel" if is_short else "video",
            "source": "youtube",
        }
    except Exception:
        return _parse_web(url)


def _parse_web(url: str) -> dict:
    try:
        response = httpx.get(url, headers=_BROWSER_HEADERS, follow_redirects=True, timeout=10)

        if response.status_code in (401, 403, 429):
            return {
                "title": _fallback_title(url),
                "description": "",
                "content": "",
                "thumbnail": "",
                "type": "other",
                "source": "web",
                "error": f"HTTP {response.status_code}",
            }

        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        def og(prop: str) -> str:
            tag = soup.find("meta", property=f"og:{prop}") or soup.find("meta", attrs={"name": f"og:{prop}"})
            return tag.get("content", "") if tag else ""

        title = og("title") or (soup.title.string.strip() if soup.title else "")
        description = og("description")
        if not description:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            description = meta_desc.get("content", "") if meta_desc else ""

        thumbnail = og("image")
        content = _extract_article_text(soup)
        if content.startswith(YOUTUBE_BOILERPLATE):
            content = ""

        source = "web"
        if "instagram.com" in url:
            source = "instagram"

        return {
            "title": title[:500],
            "description": description[:1000],
            "content": content,
            "thumbnail": thumbnail,
            "type": "other",
            "source": source,
        }
    except Exception as e:
        return {
            "title": _fallback_title(url),
            "description": "",
            "content": "",
            "thumbnail": "",
            "type": "other",
            "source": "web",
            "error": str(e),
        }


def parse_url(url: str) -> dict:
    if "youtube.com" in url or "youtu.be" in url:
        if "/post/" in url:
            result = _parse_web(url)
            result["source"] = "youtube"
            return result
        return _parse_youtube(url)
    return _parse_web(url)
