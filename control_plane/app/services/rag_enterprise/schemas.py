import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

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
    pages: List[int]
    metadata: dict


class ChunkResult(BaseModel):
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    metadata: dict = {}


class EnterpriseDocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    original_filename: str
    content_type: str
    file_size_bytes: int
    status: str
    page_count: Optional[int] = None
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None
    collection_id: Optional[uuid.UUID] = None
    tags: Optional[List[str]] = None
    retention_until: Optional[datetime] = None
    created_at: datetime
    processed_at: Optional[datetime] = None


class EnterpriseDocumentListResponse(BaseModel):
    data: List[EnterpriseDocumentResponse]
    total: int


class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class CollectionResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    document_count: int = 0
    tags: Optional[List[str]] = None
    created_at: datetime


class CollectionListResponse(BaseModel):
    data: List[CollectionResponse]


class EnterpriseQueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    collection_ids: Optional[List[uuid.UUID]] = None
    document_ids: Optional[List[uuid.UUID]] = None
    model: str = "default"
    top_k: int = Field(default=5, ge=1, le=50)
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    max_tokens: int = 700
    temperature: float = 0.2
    rerank: bool = False
    user_identity: Optional[str] = None
    abac_attributes: Optional[dict] = None


class EnterpriseSource(BaseModel):
    document_id: uuid.UUID
    filename: str
    page: int
    chunk_index: int
    text: str
    score: float


class EnterpriseQueryResponse(BaseModel):
    answer: str
    sources: List[EnterpriseSource]
    usage: dict


class EmbeddingRecord(BaseModel):
    provider: str
    model: str
    cost: float = 0.0
    dimensions: int = 384


class RAGCollection(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    client_id: uuid.UUID
    document_count: int = 0
    tags: Optional[List[str]] = None
    created_at: datetime


class AdminOverview(BaseModel):
    total_documents: int
    total_collections: int
    total_chunks: int
    total_storage_bytes: int
    total_clients_with_rag: int
    documents_by_status: dict
    clients: List[dict]


class ParserStatus(BaseModel):
    extension: str
    supported: bool
    available: bool
    dependency: Optional[str] = None
    remediation: Optional[str] = None
