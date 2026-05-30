# Owner: agent-platform
import re
from typing import List, Dict, Any

class KBChunker:
    """
    Handles segmentation of text into smaller chunks for RAG.
    """
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        """
        Splits text into overlapping chunks.
        Simplistic implementation for now.
        """
        chunks = []
        if not text:
            return chunks

        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += (self.chunk_size - self.chunk_overlap)
            
        return chunks

    def split_document(self, content: str, metadata: Dict = None) -> List[Dict[str, Any]]:
        """
        Splits a document and returns chunks with metadata.
        """
        text_chunks = self.split_text(content)
        result = []
        for i, chunk in enumerate(text_chunks):
            result.append({
                "content": chunk,
                "chunk_index": i,
                "metadata": metadata or {}
            })
        return result
