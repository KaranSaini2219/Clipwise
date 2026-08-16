from pydantic import BaseModel, Field


class ProcessVideoRequest(BaseModel):
    url: str = Field(min_length=10, max_length=500)


class VideoInfo(BaseModel):
    video_id: str
    url: str
    title: str
    thumbnail_url: str
    duration_seconds: float
    transcript_language: str
    transcript_source: str


class ProcessVideoResponse(BaseModel):
    video: VideoInfo
    summary: str
    indexed_chunks: int
    already_indexed: bool = False


class AskRequest(BaseModel):
    video_id: str = Field(min_length=1)
    question: str = Field(min_length=2, max_length=1000)


class SourceReference(BaseModel):
    start_seconds: float
    end_seconds: float
    label: str
    excerpt: str


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
