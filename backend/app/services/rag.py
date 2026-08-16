from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.services.youtube import TranscriptSegment


@dataclass
class Chunk:
    text: str
    start: float
    end: float


def timestamp(seconds: float) -> str:
    total = max(0, round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def make_chunks(segments: list[TranscriptSegment], target_chars: int = 850, overlap_chars: int = 180) -> list[Chunk]:
    chunks: list[Chunk] = []
    buffer: list[TranscriptSegment] = []
    length = 0
    for segment in segments:
        if buffer and length + len(segment.text) + 1 > target_chars:
            chunks.append(Chunk(" ".join(x.text for x in buffer), buffer[0].start, buffer[-1].end))
            overlap: list[TranscriptSegment] = []
            overlap_length = 0
            for item in reversed(buffer):
                overlap.insert(0, item)
                overlap_length += len(item.text) + 1
                if overlap_length >= overlap_chars:
                    break
            buffer = overlap
            length = sum(len(x.text) + 1 for x in buffer)
        buffer.append(segment)
        length += len(segment.text) + 1
    if buffer:
        chunks.append(Chunk(" ".join(x.text for x in buffer), buffer[0].start, buffer[-1].end))
    return chunks


@lru_cache
def embedder() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model)


class VectorStore:
    def __init__(self) -> None:
        Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(settings.chroma_path))
        self.collection = self.client.get_or_create_collection(
            "video_chunks", metadata={"hnsw:space": "cosine"}
        )

    def has_video(self, video_id: str) -> bool:
        return self.collection.count() > 0 and bool(self.collection.get(where={"video_id": video_id})["ids"])

    def index(self, video_id: str, chunks: list[Chunk]) -> None:
        ids = [f"{video_id}:{i}" for i in range(len(chunks))]
        vectors = embedder().encode([item.text for item in chunks], normalize_embeddings=True).tolist()
        self.collection.upsert(
            ids=ids,
            documents=[item.text for item in chunks],
            embeddings=vectors,
            metadatas=[{"video_id": video_id, "start": item.start, "end": item.end} for item in chunks],
        )

    def search(self, video_id: str, question: str, limit: int = 5) -> list[Chunk]:
        vector = embedder().encode(question, normalize_embeddings=True).tolist()
        result = self.collection.query(
            query_embeddings=[vector], n_results=limit, where={"video_id": video_id}, include=["documents", "metadatas"]
        )
        return [
            Chunk(text=document, start=float(meta["start"]), end=float(meta["end"]))
            for document, meta in zip(result["documents"][0], result["metadatas"][0])
        ]


vector_store = VectorStore()

