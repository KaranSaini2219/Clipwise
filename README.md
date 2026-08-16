# YouTube Video RAG Assistant

A grounded question-answering app for a single YouTube video. Paste a URL, get a structured transcript-derived summary, then ask follow-up questions without re-indexing the video.

## Architecture

```
React + Vite UI → FastAPI → YouTube Transcript API → clean + timestamped chunks
                                          ↓
                         BAAI/bge-small-en-v1.5 → local Chroma collection
                                          ↓
                         retrieve top chunks → configurable LLM → cited answer
```

The backend keeps a persistent Chroma collection under `backend/data/chroma`. Each processed video gets a stable ID, so questions reuse the existing indexed chunks. The LLM is instructed to use only supplied transcript excerpts; source citations are added from retrieved chunks, never invented.

## Why this stack

- **Fast and free locally:** BGE-small is compact, accurate for English semantic retrieval, and runs on CPU.
- **No video downloads:** `youtube-transcript-api` requests YouTube captions directly.
- **Practical free generation:** Groq's developer free tier is the default provider and is very fast. Ollama is supported for fully local, offline generation.
- **Easy to swap:** all generation settings live in `.env`; services are separated from API routes.

## Setup

### 1. Backend

Python 3.11–3.13 is recommended. (Some ML wheels may not yet support Python 3.14.)

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item ..\.env.example ..\.env
```

Set `GROQ_API_KEY` in the root `.env` (create a free key at [console.groq.com](https://console.groq.com)). Then run:

```bash
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally `http://localhost:5173`). The frontend proxies `/api` to FastAPI in development.

## Providers

`LLM_PROVIDER=groq` uses the OpenAI-compatible Groq API and `GROQ_MODEL=llama-3.1-8b-instant` by default. For a fully local option, install [Ollama](https://ollama.com), run `ollama pull llama3.2:3b`, then set:

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:3b
```

Any OpenAI-compatible endpoint can be used via `openai_compatible` variables. Never commit `.env`.

## RAG behavior

1. Validates a YouTube URL and reads caption segments.
2. Cleans captions while retaining their start/end timestamps. If captions are unavailable, it downloads an audio-only temporary file and runs local Faster-Whisper transcription instead.
3. Creates ~850-character overlapping chunks, embeds them, and persists them in Chroma.
4. On each question, retrieves the strongest five chunks for that video.
5. Sends only those excerpts to the LLM with a strict grounding prompt.
6. Returns the answer plus timestamp references from the retrieved excerpts.

If an answer is not in the excerpts, the assistant says it is not covered by the transcript. The API rejects questions for unknown/unprocessed videos.

## Troubleshooting

- **No transcript available:** the app automatically tries local Whisper transcription after caption retrieval fails. The default `base` model is an accuracy/speed balance for CPU use. Set `WHISPER_MODEL=tiny` for maximum speed or `small` for higher accuracy; the first use of each model downloads it. It can still fail for private, age-restricted, or access-blocked videos.
- **Model download fails:** Sentence Transformers downloads BGE-small on first processing. Confirm internet access, or pre-cache the Hugging Face model.
- **Generation error:** check `.env`, restart FastAPI, and verify your provider's key/model. Transcript indexing still succeeds if generation fails.
- **CORS/dev proxy:** use `npm run dev`; it forwards `/api` to port 8000. For a separate deployment set `VITE_API_URL` when building.
