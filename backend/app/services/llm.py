from openai import AsyncOpenAI
from app.core.config import settings
from app.services.rag import Chunk, timestamp


SYSTEM_PROMPT = """You are a precise YouTube transcript assistant. Answer ONLY using the transcript excerpts supplied by the user. Do not use outside knowledge or make assumptions. If the excerpts do not establish the answer, reply exactly that the transcript does not cover it. Do not invent timestamps or citations. Be concise while preserving names, figures, and important qualifications. Use short paragraphs and optional bullets."""


def client_and_model() -> tuple[AsyncOpenAI, str]:
    provider = settings.llm_provider.lower()
    if provider == "groq":
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is missing. Add it to the root .env file, or choose Ollama.")
        return AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=settings.groq_api_key), settings.groq_model
    if provider == "ollama":
        return AsyncOpenAI(base_url=settings.ollama_base_url, api_key="ollama"), settings.ollama_model
    if provider == "openai_compatible":
        if not all([settings.openai_compatible_base_url, settings.openai_compatible_api_key, settings.openai_compatible_model]):
            raise RuntimeError("OpenAI-compatible provider settings are incomplete in .env.")
        return AsyncOpenAI(base_url=settings.openai_compatible_base_url, api_key=settings.openai_compatible_api_key), settings.openai_compatible_model
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


def context(chunks: list[Chunk]) -> str:
    return "\n\n".join(f"[Transcript {timestamp(c.start)}–{timestamp(c.end)}]\n{c.text}" for c in chunks)


async def generate_summary(chunks: list[Chunk]) -> str:
    # A compact spread over the video keeps first-pass summarization fast.
    sample = chunks if len(chunks) <= 12 else [chunks[round(i * (len(chunks) - 1) / 11)] for i in range(12)]
    client, model = client_and_model()
    response = await client.chat.completions.create(
        model=model, temperature=0.1, max_tokens=700,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Create a structured summary of this video transcript. Include: a one-sentence overview, 3–6 key points, and notable examples or conclusions if present. Only state what appears in the excerpts.\n\n" + context(sample)},
        ],
    )
    return response.choices[0].message.content or "No summary was generated."


async def answer_question(question: str, chunks: list[Chunk]) -> str:
    client, model = client_and_model()
    response = await client.chat.completions.create(
        model=model, temperature=0, max_tokens=600,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {question}\n\nTranscript excerpts:\n{context(chunks)}"},
        ],
    )
    return response.choices[0].message.content or "The transcript does not cover this."

