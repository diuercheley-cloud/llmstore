import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def test_cleanup_doc_exists():
    assert (ROOT / "docs" / "V1_7_1_WARNING_CLEANUP.md").exists()

def test_cleanup_doc_mentions_fixes():
    content = (ROOT / "docs" / "V1_7_1_WARNING_CLEANUP.md").read_text()
    assert "VERSION atualizada" in content
    assert "Branch correta" in content
    assert "Release manifest OK" in content
    assert "Chat/Responses/Embeddings 405" in content

def test_cleanup_doc_mentions_accepted():
    content = (ROOT / "docs" / "V1_7_1_WARNING_CLEANUP.md").read_text()
    assert "PSP/PIX real fora do escopo" in content
    assert "RAG 404" in content
    assert "TTS 404" in content
