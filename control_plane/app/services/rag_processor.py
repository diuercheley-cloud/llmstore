import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.rag_document import RAGDocument
from app.models.rag_document_chunk import RAGDocumentChunk
from app.services.embeddings import get_embedding_service
from app.utils.token_estimator import estimate_tokens_from_text
from app.services.rag_usage import get_rag_usage_and_limits, record_rag_event
from app.models.client import Client
from app.models.billing_plan import BillingPlan

logger = logging.getLogger(__name__)
settings = get_settings()

async def process_rag_document(session: AsyncSession, document_id: uuid.UUID):
    doc = (await session.execute(select(RAGDocument).where(RAGDocument.id == document_id))).scalar_one_or_none()
    if not doc:
        logger.error(f"Document {document_id} not found for processing")
        return

    try:
        doc.status = "processing"
        await session.commit()

        client_stmt = (
            select(Client)
            .options(selectinload(Client.billing_plan).selectinload(BillingPlan.pricing_rules))
            .where(Client.id == doc.client_id)
        )
        client = (await session.execute(client_stmt)).scalar_one()
        usage_info = await get_rag_usage_and_limits(session, client)
        limits = usage_info["limits"]
        usage = usage_info["usage"]

        if not os.path.exists(doc.storage_path):
            raise FileNotFoundError(f"File not found at {doc.storage_path}")

        # 1. Extract text
        text_by_page = []
        file_ext = doc.original_filename.lower().split(".")[-1]
        
        if file_ext == "pdf":
            with fitz.open(doc.storage_path) as pdf:
                doc.page_count = len(pdf)
                
                if limits["max_pages_per_month"] is not None and (usage["pages_processed_month"] + doc.page_count) > limits["max_pages_per_month"]:
                    doc.status = "rejected_limit"
                    doc.error_message = f"Monthly page limit exceeded. Plan allows {limits['max_pages_per_month']} pages."
                    await session.commit()
                    return

                for page_num, page in enumerate(pdf, start=1):
                    text = page.get_text().strip()
                    if text:
                        text_by_page.append((page_num, text))
        elif file_ext in ["txt", "md"]:
            doc.page_count = 1
            if limits["max_pages_per_month"] is not None and (usage["pages_processed_month"] + 1) > limits["max_pages_per_month"]:
                doc.status = "rejected_limit"
                doc.error_message = f"Monthly page limit exceeded. Plan allows {limits['max_pages_per_month']} pages."
                await session.commit()
                return
                
            with open(doc.storage_path, "r", encoding="utf-8") as f:
                text = f.read().strip()
                if text:
                    text_by_page.append((1, text))
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

        if not text_by_page:
            raise ValueError("No text found in file")

        # 2. Chunk text
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            length_function=len,
        )

        chunks_to_process = []
        for page_num, text in text_by_page:
            page_chunks = text_splitter.split_text(text)
            for i, chunk_text in enumerate(page_chunks):
                chunks_to_process.append({
                    "page_number": page_num,
                    "content": chunk_text,
                })

        # 3. Generate embeddings
        embedding_service = get_embedding_service()
        texts = [c["content"] for c in chunks_to_process]
        embeddings = await embedding_service.embed_batch(texts)

        # 4. Save chunks
        # Delete existing chunks if reprocessing
        await session.execute(delete(RAGDocumentChunk).where(RAGDocumentChunk.document_id == document_id))
        
        for i, (chunk_data, embedding) in enumerate(zip(chunks_to_process, embeddings)):
            chunk = RAGDocumentChunk(
                document_id=doc.id,
                client_id=doc.client_id,
                chunk_index=i,
                page_number=chunk_data["page_number"],
                content=chunk_data["content"],
                token_count=estimate_tokens_from_text(chunk_data["content"]),
                embedding=embedding,
            )
            session.add(chunk)

        doc.chunk_count = len(chunks_to_process)
        doc.status = "indexed"
        doc.processed_at = utc_now()
        doc.error_message = None
        
        await record_rag_event(session, doc.client_id, "pages_processed", quantity=doc.page_count, document_id=doc.id)
        
        await session.commit()
        logger.info(f"Document {document_id} processed successfully with {doc.chunk_count} chunks")

    except Exception as e:
        logger.exception(f"Error processing document {document_id}")
        doc.status = "failed"
        doc.error_message = str(e)
        await session.commit()

async def delete_rag_document(session: AsyncSession, document: RAGDocument):
    # Delete chunks
    await session.execute(delete(RAGDocumentChunk).where(RAGDocumentChunk.document_id == document.id))
    # Delete file
    if os.path.exists(document.storage_path):
        try:
            os.remove(document.storage_path)
        except Exception as e:
            logger.error(f"Failed to delete file {document.storage_path}: {e}")
    # Delete document record
    await session.delete(document)
    await session.commit()
