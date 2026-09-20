import re
import time
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
    """Fetch any public caption track, preferring English where available.

    ``YouTubeTranscriptApi.fetch(video_id)`` defaults to English. That made a
    video with valid Spanish, Hindi, or other captions look as though it had no
    transcript at all. Listing the available tracks lets us use the best
    English track first, then a translatable track, then any public track.
    """
    try:
        fetched = _fetch_best_caption(video_id)
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


def _fetch_best_caption(video_id: str):
    """Return a public caption track without requiring it to be English."""
    last_error: Exception | None = None
    # Caption requests occasionally fail transiently from shared hosting IPs.
    # Retry the lookup, but do not fall back to audio here.
    for attempt in range(2):
        try:
            transcripts = list(YouTubeTranscriptApi().list(video_id))
            if not transcripts:
                raise TranscriptUnavailable("No public caption tracks were returned.")

            english = [
                transcript
                for transcript in transcripts
                if transcript.language_code.lower().startswith("en")
            ]
            # Prefer creator-provided captions over auto-generated captions.
            english.sort(key=lambda transcript: transcript.is_generated)
            if english:
                return english[0].fetch()

            translatable = [
                transcript for transcript in transcripts if transcript.is_translatable
            ]
            if translatable:
                translatable.sort(key=lambda transcript: transcript.is_generated)
                return translatable[0].translate("en").fetch()

            transcripts.sort(key=lambda transcript: transcript.is_generated)
            return transcripts[0].fetch()
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(0.5)

    assert last_error is not None
    raise last_error


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

