# Knowledge Base Ingestion Pipeline

The KB Ingestion Pipeline automates the process of transforming raw documents into indexed data for RAG (Retrieval-Augmented Generation).

## Core Components

### 1. KB Registry
Manages the logical grouping of documents within a Knowledge Base. Each KB can have its own embedding model and provider configuration (e.g., Pinecone, Milvus, pgvector).

### 2. Document Ingestors
- **PDF Ingestor**: Extracts text and metadata from uploaded PDF files.
- **Web Ingestor**: Scrapes content from URLs. **Disabled by default** for security.
- **Text Ingestor**: Handles direct text uploads.

### 3. KB Chunker
Segments long documents into smaller, overlapping chunks to fit within LLM context windows and improve retrieval precision.
- **Default Chunk Size**: 1000 characters.
- **Default Overlap**: 200 characters.

### 4. Versioning & Maintenance
- **Document Versions**: Every ingestion creates a new version, allowing for tracking and rollback.
- **Reindexing**: Trigger a full reindex of a KB to update embeddings or change chunking strategies.

## Ingestion Workflow

1.  **Create KB**: Initialize a new Knowledge Base container.
2.  **Upload Doc**: Send a file (PDF/TXT) or URL to the ingestion endpoint.
3.  **Job Queued**: An ingestion job is created to track progress.
4.  **Processing**: The document is parsed, chunked, and embedded.
5.  **Indexing**: Chunks are stored in the vector store and linked to the document version.

## API Usage

### Create a KB
```bash
POST /api/v1/admin/kb/
{ "name": "Technical Docs", "description": "Internal technical manuals" }
```

### Upload a PDF
```bash
POST /api/v1/admin/kb/{id}/documents
# Form data with 'file' field
```

### Ingest a URL
```bash
POST /api/v1/admin/kb/{id}/ingest-url
{ "url": "https://docs.example.com" }
```

## Security and Privacy

- **Tenant Isolation**: Documents and embeddings are strictly isolated by tenant.
- **PII Redaction**: (Coming Soon) Automated redaction of sensitive data during extraction.
- **URL Whitelisting**: Configure allowed domains for web ingestion.
