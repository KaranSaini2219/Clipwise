"""Streamlit Community Cloud entrypoint for the YouTube Video RAG Assistant.

It deliberately reuses the production RAG services in backend/app rather than
maintaining a second retrieval or prompting implementation.
"""
import asyncio
import sys
from pathlib import Path

import streamlit as st

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.llm import answer_question, generate_summary
from app.services.rag import make_chunks, timestamp, vector_store
from app.services.transcription import AudioTranscriptionUnavailable, transcribe_youtube_audio
from app.services.youtube import TranscriptUnavailable, get_transcript, get_video_title, video_id_from_url


st.set_page_config(page_title="Clipwise — Video RAG", page_icon="✦", layout="wide")

st.markdown("""
<style>
    .stApp { background: #080d1a; color: #e2e8f0; }
    [data-testid="stHeader"] { background: transparent; }
    .hero { padding: 2.5rem 0 1.4rem; text-align: center; }
    .hero h1 { font-size: clamp(2.4rem, 6vw, 4.8rem); margin: 0; letter-spacing: -0.06em; color: #fff; }
    .hero p { color: #94a3b8; font-size: 1.08rem; margin: 1rem auto; max-width: 42rem; }
    .eyebrow { color: #c4b5fd; font-size: .72rem; font-weight: 700; letter-spacing: .13em; }
    div[data-testid="stMetric"] { border: 1px solid rgba(255,255,255,.12); border-radius: .8rem; padding: .5rem .8rem; }
    .source { color: #c4b5fd; font-size: .82rem; }
</style>
""", unsafe_allow_html=True)


def run(coroutine):
    return asyncio.run(coroutine)


def init_state() -> None:
    st.session_state.setdefault("video", None)
    st.session_state.setdefault("summary", "")
    st.session_state.setdefault("messages", [])


def process_video(url: str) -> tuple[dict, str]:
    video_id = video_id_from_url(url)
    source = "YouTube captions"
    try:
        segments, language = get_transcript(video_id)
    except TranscriptUnavailable:
        segments, language = transcribe_youtube_audio(video_id)
        source = "Local Whisper transcription"

    chunks = make_chunks(segments)
    already_indexed = vector_store.has_video(video_id)
    if not already_indexed:
        vector_store.index(video_id, chunks)
    title = run(get_video_title(video_id))
    summary = run(generate_summary(chunks))
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": title,
        "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "duration_seconds": segments[-1].end,
        "language": language,
        "source": source,
        "chunks": len(chunks),
        "already_indexed": already_indexed,
    }, summary


def duration_label(seconds: float) -> str:
    seconds = round(seconds)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


def reset_video() -> None:
    st.session_state.video = None
    st.session_state.summary = ""
    st.session_state.messages = []


init_state()

top_left, top_right = st.columns([6, 1])
with top_left:
    st.markdown("<div class='eyebrow'>✦ CLIPWISE / TRANSCRIPT-POWERED VIDEO INTELLIGENCE</div>", unsafe_allow_html=True)
with top_right:
    if st.session_state.video and st.button("New video", use_container_width=True):
        reset_video()
        st.rerun()

if not st.session_state.video:
    st.markdown("""
    <div class="hero">
      <h1>Your video,<br><span style="color:#c4b5fd">finally searchable.</span></h1>
      <p>Paste a YouTube link for a grounded summary and a conversation based only on what was said.</p>
    </div>
    """, unsafe_allow_html=True)
    with st.form("video_url_form"):
        url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=…", label_visibility="collapsed")
        submitted = st.form_submit_button("Analyze video", type="primary", use_container_width=True)
    if submitted:
        if not url.strip():
            st.warning("Paste a YouTube URL to continue.")
        else:
            try:
                with st.status("Preparing your video…", expanded=True) as status:
                    st.write("Checking for published YouTube captions…")
                    video, summary = process_video(url)
                    if video["source"] == "Local Whisper transcription":
                        st.write("No captions found — completed local audio transcription.")
                    st.write("Indexed timestamped transcript passages.")
                    status.update(label="Video ready", state="complete", expanded=False)
                st.session_state.video = video
                st.session_state.summary = summary
                st.session_state.messages = []
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except AudioTranscriptionUnavailable as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Unable to process this video: {exc}")
else:
    video = st.session_state.video
    left, right = st.columns([2, 1], gap="large")
    with left:
        st.image(video["thumbnail_url"], use_container_width=True)
        st.caption("READY TO EXPLORE")
        st.title(video["title"])
        st.markdown("### Video summary")
        st.markdown(st.session_state.summary)
    with right:
        st.subheader("Video context")
        st.metric("Duration", duration_label(video["duration_seconds"]))
        st.metric("Transcript", video["source"])
        st.metric("Indexed passages", video["chunks"])
        st.caption("Every response is constrained to retrieved transcript excerpts.")

    st.divider()
    st.subheader("Ask about this video")
    if not st.session_state.messages:
        st.caption("Try: “What are the main points?”, “What examples were given?”, or “At what point was X discussed?”")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            for source in message.get("sources", []):
                href = f"{video['url']}&t={int(source.start)}s"
                st.markdown(f"<span class='source'>⌚ <a href='{href}' target='_blank'>{timestamp(source.start)}</a> — {source.text[:160]}…</span>", unsafe_allow_html=True)

    if question := st.chat_input("Ask a question about the transcript…"):
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Searching the transcript…"):
                try:
                    chunks = vector_store.search(video["video_id"], question)
                    answer = run(answer_question(question, chunks))
                    st.markdown(answer)
                    for source in chunks[:3]:
                        href = f"{video['url']}&t={int(source.start)}s"
                        st.markdown(f"<span class='source'>⌚ <a href='{href}' target='_blank'>{timestamp(source.start)}</a> — {source.text[:160]}…</span>", unsafe_allow_html=True)
                    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": chunks[:3]})
                except Exception as exc:
                    message = f"I could not answer that: {exc}"
                    st.error(message)
                    st.session_state.messages.append({"role": "assistant", "content": message})

