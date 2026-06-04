import logging
import re
from typing import List

from app.services.rag_enterprise.schemas import ChunkingConfig, ChunkResult, ChunkStrategy

logger = logging.getLogger(__name__)


def chunk_by_fixed(text: str, config: ChunkingConfig) -> List[ChunkResult]:
    chunks = []
    start = 0
    text_len = len(text)
    chunk_index = 0

    while start < text_len:
        end = min(start + config.chunk_size, text_len)
        if end < text_len and config.chunk_overlap > 0:
            end = min(end + config.chunk_overlap, text_len)

        content = text[start:end]
        if content.strip():
            chunks.append(ChunkResult(
                content=content,
                chunk_index=chunk_index,
                metadata={"strategy": "fixed", "start_char": start, "end_char": end},
            ))
            chunk_index += 1

        step = config.chunk_size
        if config.chunk_overlap > 0:
            step = config.chunk_size
        start += step

    return chunks


def chunk_by_heading(text: str, config: ChunkingConfig) -> List[ChunkResult]:
    heading_pattern = re.compile(r'^(#{1,6}\s+|(?:\w+\s?){1,10}\n[-=]+)', re.MULTILINE)
    sections = heading_pattern.split(text)

    chunks = []
    current_chunk = ""
    chunk_index = 0
    current_heading = ""

    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        if re.match(r'^#{1,6}\s', section) or re.match(r'^[\w\s]+\n[-=]+$', section):
            current_heading = section
            continue

        content = section
        if current_heading:
            content = f"{current_heading}\n{content}"

        if len(current_chunk) + len(content) > config.chunk_size and current_chunk:
            chunks.append(ChunkResult(
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                metadata={"strategy": "heading"},
            ))
            chunk_index += 1
            current_chunk = content
        else:
            if current_chunk:
                current_chunk += "\n\n" + content
            else:
                current_chunk = content

    if current_chunk.strip():
        chunks.append(ChunkResult(
            content=current_chunk.strip(),
            chunk_index=chunk_index,
            metadata={"strategy": "heading"},
        ))

    return chunks


def chunk_semantic_placeholder(text: str, config: ChunkingConfig) -> List[ChunkResult]:
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current_chunk = ""
    chunk_index = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) > config.chunk_size and current_chunk:
            chunks.append(ChunkResult(
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                metadata={"strategy": "semantic_placeholder"},
            ))
            chunk_index += 1
            current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

    if current_chunk.strip():
        chunks.append(ChunkResult(
            content=current_chunk.strip(),
            chunk_index=chunk_index,
            metadata={"strategy": "semantic_placeholder"},
        ))

    return chunks


STRATEGY_MAP = {
    ChunkStrategy.fixed: chunk_by_fixed,
    ChunkStrategy.heading: chunk_by_heading,
    ChunkStrategy.semantic_placeholder: chunk_semantic_placeholder,
}


def chunk_text(text: str, config: ChunkingConfig) -> List[ChunkResult]:
    strategy_fn = STRATEGY_MAP.get(config.strategy)
    if strategy_fn is None:
        logger.warning(f"Unknown strategy {config.strategy}, falling back to fixed")
        strategy_fn = chunk_by_fixed
    return strategy_fn(text, config)
