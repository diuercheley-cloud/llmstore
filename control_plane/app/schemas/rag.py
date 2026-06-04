import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RAGFileResponse(BaseModel):
    id: uuid.UUID
    filename: str
    original_filename: str
    content_type: str
    file_size_bytes: int
    status: str
    page_count: Optional[int] = None
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

class RAGFileListResponse(BaseModel):
    data: List[RAGFileResponse]

class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    file_ids: Optional[List[uuid.UUID]] = None
    collection_ids: Optional[List[uuid.UUID]] = None
    document_ids: Optional[List[uuid.UUID]] = None
    model: str = "default"
    top_k: int = 5
    max_tokens: int = 700
    temperature: float = 0.2
    score_threshold: Optional[float] = 0.0
    rerank: Optional[bool] = False
    user_identity: Optional[str] = None
    abac_attributes: Optional[dict] = None

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
    sources: List[RAGSource]
    usage: RAGUsage
