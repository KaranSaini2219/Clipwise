"""Local audio-only fallback for videos without published YouTube captions."""
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory

from faster_whisper import WhisperModel
from yt_dlp import YoutubeDL

from app.core.config import settings
from app.services.youtube import TranscriptSegment


class AudioTranscriptionUnavailable(Exception):
    pass


@lru_cache
def whisper_model() -> WhisperModel:
    """Load once per API process; the model is downloaded on its first use."""
    return WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


def transcribe_youtube_audio(video_id: str) -> tuple[list[TranscriptSegment], str]:
    """Download a temporary audio stream, never a video file, and transcribe it locally."""
    if not settings.transcription_fallback_enabled:
        raise AudioTranscriptionUnavailable("Automatic transcription is disabled by configuration.")

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with TemporaryDirectory(prefix="video-rag-audio-") as temp_dir:
            output_template = str(Path(temp_dir) / "source.%(ext)s")
            options = {
                "format": "bestaudio/best",
                "outtmpl": output_template,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "retries": 1,
                "extractor_retries": 1,
                "socket_timeout": 30,
            }
            with YoutubeDL(options) as downloader:
                info = downloader.extract_info(video_url, download=True)
                audio_path = Path(downloader.prepare_filename(info))
            if not audio_path.exists():
                candidates = list(Path(temp_dir).glob("source.*"))
                if not candidates:
                    raise RuntimeError("Audio download did not produce a readable file.")
                audio_path = candidates[0]

            segments, info = whisper_model().transcribe(
                str(audio_path), beam_size=5, vad_filter=True, condition_on_previous_text=True
            )
            cleaned = [
                TranscriptSegment(text=" ".join(segment.text.split()), start=float(segment.start), end=float(segment.end))
                for segment in segments
                if segment.text.strip()
            ]
            if not cleaned:
                raise RuntimeError("No speech could be detected in this video's audio.")
            return cleaned, info.language or "unknown"
    except Exception as exc:
        raise AudioTranscriptionUnavailable(
            "The video has no accessible captions, and the local audio transcription fallback could not complete. "
            "The video may be restricted, unavailable, or blocked from audio access."
        ) from exc
