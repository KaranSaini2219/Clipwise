from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.2:3b"
    openai_compatible_base_url: str = ""
    openai_compatible_api_key: str = ""
    openai_compatible_model: str = ""
    chroma_path: Path = Path(__file__).resolve().parents[2] / "data" / "chroma"
    frontend_dist_dir: Path = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    transcription_fallback_enabled: bool = True
    # base is the practical CPU default; use small only when extra accuracy is worth the wait.
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"


settings = Settings()
