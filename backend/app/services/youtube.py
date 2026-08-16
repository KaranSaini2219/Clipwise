import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse
import httpx
from youtube_transcript_api import YouTubeTranscriptApi


YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


@dataclass
class TranscriptSegment:
    text: str
    start: float
    end: float


class TranscriptUnavailable(Exception):
    pass


def video_id_from_url(url: str) -> str:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().removeprefix("www.")
    candidate = ""
    if host == "youtu.be":
        candidate = parsed.path.strip("/").split("/")[0]
    elif host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith(("/shorts/", "/embed/", "/live/")):
            candidate = parsed.path.strip("/").split("/")[1]
    if not YOUTUBE_ID.fullmatch(candidate):
        raise ValueError("Please enter a valid YouTube video URL.")
    return candidate


def get_transcript(video_id: str) -> tuple[list[TranscriptSegment], str]:
    try:
        fetched = YouTubeTranscriptApi().fetch(video_id)
        segments = [
            TranscriptSegment(
                text=" ".join(item.text.replace("\n", " ").split()),
                start=float(item.start),
                end=float(item.start + item.duration),
            )
            for item in fetched
            if item.text.strip()
        ]
        if not segments:
            raise TranscriptUnavailable("The video returned an empty transcript.")
        return segments, fetched.language_code
    except Exception as exc:
        raise TranscriptUnavailable(
            "A transcript could not be retrieved. The video may not have public captions or may be restricted."
        ) from exc


async def get_video_title(video_id: str) -> str:
    fallback = f"YouTube video ({video_id})"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                "https://www.youtube.com/oembed",
                params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            )
            response.raise_for_status()
            return response.json().get("title", fallback)
    except Exception:
        return fallback

