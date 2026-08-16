from fastapi import APIRouter, HTTPException
from app.models.schemas import AskRequest, AskResponse, ProcessVideoRequest, ProcessVideoResponse, SourceReference, VideoInfo
from app.services.llm import answer_question, generate_summary
from app.services.rag import make_chunks, timestamp, vector_store
from app.services.youtube import TranscriptUnavailable, get_transcript, get_video_title, video_id_from_url
from app.services.transcription import AudioTranscriptionUnavailable, transcribe_youtube_audio

router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/videos/process", response_model=ProcessVideoResponse)
async def process_video(payload: ProcessVideoRequest) -> ProcessVideoResponse:
    try:
        video_id = video_id_from_url(payload.url)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    transcript_source = "YouTube captions"
    try:
        segments, language = get_transcript(video_id)
    except TranscriptUnavailable as exc:
        try:
            segments, language = transcribe_youtube_audio(video_id)
            transcript_source = "Local Whisper transcription"
        except AudioTranscriptionUnavailable as fallback_exc:
            raise HTTPException(422, str(fallback_exc)) from fallback_exc
    title = await get_video_title(video_id)
    chunks = make_chunks(segments)
    exists = vector_store.has_video(video_id)
    if not exists:
        vector_store.index(video_id, chunks)
    try:
        summary = await generate_summary(chunks)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "Transcript was indexed, but the summary provider could not respond.") from exc
    return ProcessVideoResponse(
        video=VideoInfo(video_id=video_id, url=f"https://www.youtube.com/watch?v={video_id}", title=title,
                        thumbnail_url=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg", duration_seconds=segments[-1].end,
                        transcript_language=language, transcript_source=transcript_source),
        summary=summary, indexed_chunks=len(chunks), already_indexed=exists,
    )


@router.post("/chat", response_model=AskResponse)
async def chat(payload: AskRequest) -> AskResponse:
    if not vector_store.has_video(payload.video_id):
        raise HTTPException(404, "This video has not been processed in this workspace.")
    chunks = vector_store.search(payload.video_id, payload.question)
    if not chunks:
        raise HTTPException(404, "No transcript chunks were found for this video.")
    try:
        answer = await answer_question(payload.question, chunks)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "The answer provider could not respond.") from exc
    return AskResponse(answer=answer, sources=[SourceReference(start_seconds=c.start, end_seconds=c.end, label=timestamp(c.start), excerpt=c.text[:210] + ("…" if len(c.text) > 210 else "")) for c in chunks[:3]])
