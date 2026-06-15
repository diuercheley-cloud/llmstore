import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RAGFileResponse(BaseModel):
    id: uuid.UUID
    filename: str
    original_filename: str
    content_type: str
    file_size_bytes: int
    status: str
    page_count: int | None = None
    chunk_count: int | None = None
    error_message: str | None = None
    created_at: datetime
    processed_at: datetime | None = None


class RAGFileListResponse(BaseModel):
    data: list[RAGFileResponse]


class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    file_ids: list[uuid.UUID] | None = None
    collection_ids: list[uuid.UUID] | None = None
    document_ids: list[uuid.UUID] | None = None
    model: str = "default"
    top_k: int = 5
    max_tokens: int = 700
    temperature: float = 0.2
    score_threshold: float | None = 0.0
    rerank: bool | None = False
    user_identity: str | None = None
    abac_attributes: dict | None = None


class RAGSource(BaseModel):
    file_id: uuid.UUID
    filename: str
    page: int
    chunk_index: int
    text: str
    score: float


class RAGUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[RAGSource]
    usage: RAGUsage
