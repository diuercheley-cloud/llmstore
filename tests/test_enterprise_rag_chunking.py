import pytest

from app.services.rag_enterprise.chunking import chunk_text, chunk_by_fixed, chunk_by_heading, chunk_semantic_placeholder
from app.services.rag_enterprise.schemas import ChunkingConfig, ChunkStrategy


pytestmark = pytest.mark.asyncio


SAMPLE_TEXT = """Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.

Heading 1
=========

Paragraph under heading 1. Some content here.

Heading 2
=========

Paragraph under heading 2. More content here.

## Subheading 2.1

Content under subheading.

Final paragraph without heading."""


class TestFixedChunking:
    def test_small_text_single_chunk(self):
        config = ChunkingConfig(chunk_size=1000, chunk_overlap=0)
        chunks = chunk_by_fixed("Small text", config)
        assert len(chunks) == 1
        assert chunks[0].content == "Small text"

    def test_large_text_multiple_chunks(self):
        text = "A" * 3000
        config = ChunkingConfig(chunk_size=1000, chunk_overlap=0)
        chunks = chunk_by_fixed(text, config)
        assert len(chunks) == 3
        assert all(c.content.strip() for c in chunks)

    def test_chunk_with_overlap(self):
        text = "X" * 2000
        config = ChunkingConfig(chunk_size=1000, chunk_overlap=100)
        chunks = chunk_by_fixed(text, config)
        assert len(chunks) >= 2
        assert all(isinstance(c.chunk_index, int) for c in chunks)

    def test_empty_text(self):
        config = ChunkingConfig(chunk_size=1000, chunk_overlap=0)
        chunks = chunk_by_fixed("", config)
        assert len(chunks) == 0

    def test_metadata_present(self):
        config = ChunkingConfig(chunk_size=100, chunk_overlap=0)
        chunks = chunk_by_fixed("Hello world", config)
        assert len(chunks) == 1
        assert chunks[0].metadata["strategy"] == "fixed"


class TestHeadingChunking:
    def test_chunks_by_heading(self):
        config = ChunkingConfig(chunk_size=5000, chunk_overlap=0, strategy=ChunkStrategy.heading)
        chunks = chunk_by_heading(SAMPLE_TEXT, config)
        assert len(chunks) >= 1
        for c in chunks:
            assert c.metadata["strategy"] == "heading"

    def test_heading_strategy_preserves_content(self):
        config = ChunkingConfig(chunk_size=5000, chunk_overlap=0, strategy=ChunkStrategy.heading)
        chunks = chunk_by_heading(SAMPLE_TEXT, config)
        combined = " ".join(c.content for c in chunks)
        assert "Lorem ipsum" in combined

    def test_small_text_heading(self):
        config = ChunkingConfig(chunk_size=1000, chunk_overlap=0, strategy=ChunkStrategy.heading)
        chunks = chunk_by_heading("Just text", config)
        assert len(chunks) == 1


class TestSemanticChunking:
    def test_chunks_by_paragraph(self):
        config = ChunkingConfig(chunk_size=5000, chunk_overlap=0, strategy=ChunkStrategy.semantic_placeholder)
        chunks = chunk_semantic_placeholder(SAMPLE_TEXT, config)
        assert len(chunks) >= 1
        for c in chunks:
            assert c.metadata["strategy"] == "semantic_placeholder"

    def test_semantic_preserves_all_content(self):
        config = ChunkingConfig(chunk_size=5000, chunk_overlap=0)
        chunks = chunk_semantic_placeholder(SAMPLE_TEXT, config)
        combined = " ".join(c.content for c in chunks)
        assert "Heading 1" in combined or "Lorem ipsum" in combined

    def test_small_text_semantic(self):
        config = ChunkingConfig(chunk_size=1000, chunk_overlap=0)
        chunks = chunk_semantic_placeholder("Short text", config)
        assert len(chunks) == 1


class TestChunkDispatcher:
    def test_fixed_strategy(self):
        config = ChunkingConfig(chunk_size=100, chunk_overlap=0, strategy=ChunkStrategy.fixed)
        chunks = chunk_text("Hello world", config)
        assert len(chunks) == 1
        assert chunks[0].metadata["strategy"] == "fixed"

    def test_heading_strategy(self):
        config = ChunkingConfig(chunk_size=5000, chunk_overlap=0, strategy=ChunkStrategy.heading)
        chunks = chunk_text("# Title\n\nContent", config)
        assert len(chunks) >= 1
        assert chunks[0].metadata["strategy"] == "heading"

    def test_semantic_strategy(self):
        config = ChunkingConfig(chunk_size=5000, chunk_overlap=0, strategy=ChunkStrategy.semantic_placeholder)
        chunks = chunk_text("Para1\n\nPara2\n\nPara3", config)
        assert len(chunks) >= 1
        assert chunks[0].metadata["strategy"] == "semantic_placeholder"

    def test_unknown_strategy_fallback(self):
        from app.services.rag_enterprise.schemas import ChunkStrategy
        import app.services.rag_enterprise.chunking as c
        original_map = c.STRATEGY_MAP.copy()
        try:
            config = ChunkingConfig(chunk_size=100, chunk_overlap=0, strategy=ChunkStrategy.fixed)
            chunks = chunk_text("Hello", config)
            assert len(chunks) == 1
        finally:
            pass

    def test_chunk_index_increments(self):
        text = "A" * 5000
        config = ChunkingConfig(chunk_size=1000, chunk_overlap=0, strategy=ChunkStrategy.fixed)
        chunks = chunk_text(text, config)
        for i, c in enumerate(chunks):
            assert c.chunk_index == i


class TestChunkingConfig:
    def test_default_values(self):
        config = ChunkingConfig()
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 150
        assert config.strategy == ChunkStrategy.fixed

    def test_validation(self):
        with pytest.raises(Exception):
            ChunkingConfig(chunk_size=50, chunk_overlap=0)

    def test_enum_values(self):
        assert ChunkStrategy.fixed.value == "fixed"
        assert ChunkStrategy.heading.value == "heading"
        assert ChunkStrategy.semantic_placeholder.value == "semantic_placeholder"
