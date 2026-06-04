from app.services.embeddings_mock import get_mock_embedding, process_mock_embeddings


def test_mock_embedding_determinism():
    """
    Testa se o embedding mock é determinístico.
    """
    text = "determinism test"
    emb1 = get_mock_embedding(text, dimensions=128)
    emb2 = get_mock_embedding(text, dimensions=128)
    assert emb1 == emb2
    
    text2 = "other test"
    emb3 = get_mock_embedding(text2, dimensions=128)
    assert emb1 != emb3

def test_mock_embedding_dimensions():
    """
    Testa se a dimensão solicitada é respeitada.
    """
    text = "dim test"
    emb = get_mock_embedding(text, dimensions=64)
    assert len(emb) == 64
    
    emb2 = get_mock_embedding(text, dimensions=384)
    assert len(emb2) == 384

def test_process_mock_embeddings_format():
    """
    Testa o formato da resposta do processador mock.
    """
    res = process_mock_embeddings("hello", model="test-model", dimensions=16)
    assert res["object"] == "list"
    assert res["model"] == "test-model"
    assert len(res["data"]) == 1
    assert len(res["data"][0]["embedding"]) == 16
    assert res["usage"]["total_tokens"] > 0
