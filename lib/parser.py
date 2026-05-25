import os
import re
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_REGEX = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})"
)


def _extract_video_id(url: str) -> str | None:
    match = YOUTUBE_REGEX.search(url)
    return match.group(1) if match else None


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
            "thumbnail": snippet.get("thumbnails", {}).get("maxres", {}).get("url")
                or snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "type": "reel" if is_short else "video",
            "source": "youtube",
        }
    except Exception:
        return _parse_web(url)


def _parse_web(url: str) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; LinkSaverBot/1.0)"
        )
    }
    try:
        response = httpx.get(url, headers=headers, follow_redirects=True, timeout=10)
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

        source = "web"
        if "instagram.com" in url:
            source = "instagram"

        return {
            "title": title[:500],
            "description": description[:1000],
            "thumbnail": thumbnail,
            "type": "other",
            "source": source,
        }
    except Exception as e:
        return {
            "title": "",
            "description": "",
            "thumbnail": "",
            "type": "other",
            "source": "web",
            "error": str(e),
        }


def parse_url(url: str) -> dict:
    if "youtube.com" in url or "youtu.be" in url:
        return _parse_youtube(url)
    return _parse_web(url)
