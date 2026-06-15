import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ChunkStrategy(str, Enum):
    fixed = "fixed"
    heading = "heading"
    semantic_placeholder = "semantic_placeholder"


class FileType(str, Enum):
    txt = ".txt"
    md = ".md"
    pdf = ".pdf"
    docx = ".docx"
    xlsx = ".xlsx"
    csv = ".csv"


SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".xlsx", ".csv"}

PARSER_AVAILABILITY = {
    ".txt": True,
    ".md": True,
    ".csv": True,
    ".pdf": None,
    ".docx": None,
    ".xlsx": None,
}


class ChunkingConfig(BaseModel):
    chunk_size: int = Field(default=1000, ge=100, le=8192)
    chunk_overlap: int = Field(default=150, ge=0, le=2048)
    strategy: ChunkStrategy = ChunkStrategy.fixed


class ParseResult(BaseModel):
    text: str
    pages: list[int]
    metadata: dict


class ChunkResult(BaseModel):
    content: str
    chunk_index: int
    page_number: int | None = None
    sheet_name: str | None = None
    metadata: dict = {}


class EnterpriseDocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    original_filename: str
    content_type: str
    file_size_bytes: int
    status: str
    page_count: int | None = None
    chunk_count: int | None = None
    error_message: str | None = None
    collection_id: uuid.UUID | None = None
    tags: list[str] | None = None
    retention_until: datetime | None = None
    created_at: datetime
    processed_at: datetime | None = None


class EnterpriseDocumentListResponse(BaseModel):
    data: list[EnterpriseDocumentResponse]
    total: int


class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    tags: list[str] | None = None


class CollectionResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    document_count: int = 0
    tags: list[str] | None = None
    created_at: datetime


class CollectionListResponse(BaseModel):
    data: list[CollectionResponse]


class EnterpriseQueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    collection_ids: list[uuid.UUID] | None = None
    document_ids: list[uuid.UUID] | None = None
    model: str = "default"
    top_k: int = Field(default=5, ge=1, le=50)
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    max_tokens: int = 700
    temperature: float = 0.2
    rerank: bool = False
    user_identity: str | None = None
    abac_attributes: dict | None = None


class EnterpriseSource(BaseModel):
    document_id: uuid.UUID
    filename: str
    page: int
    chunk_index: int
    text: str
    score: float


class EnterpriseQueryResponse(BaseModel):
    answer: str
    sources: list[EnterpriseSource]
    usage: dict


class EmbeddingRecord(BaseModel):
    provider: str
    model: str
    cost: float = 0.0
    dimensions: int = 384


class RAGCollection(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    client_id: uuid.UUID
    document_count: int = 0
    tags: list[str] | None = None
    created_at: datetime


class AdminOverview(BaseModel):
    total_documents: int
    total_collections: int
    total_chunks: int
    total_storage_bytes: int
    total_clients_with_rag: int
    documents_by_status: dict
    clients: list[dict]


class ParserStatus(BaseModel):
    extension: str
    supported: bool
    available: bool
    dependency: str | None = None
    remediation: str | None = None
