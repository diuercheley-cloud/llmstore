from app.services.rag_enterprise.reranking import apply_reranking, rerank_diversity


def test_reranking_position_and_diversity_are_bounded():
    chunks = [
        (0.9, {"chunk_index": 2, "embedding": [1.0, 0.0]}),
        (0.9, {"chunk_index": 1, "embedding": [1.0, 0.0]}),
        (0.8, {"chunk_index": 3, "embedding": [0.0, 1.0]}),
    ]

    assert apply_reranking(chunks, "position", 2)[0][1]["chunk_index"] == 1
    diverse = rerank_diversity(chunks, top_k=2)
    assert len(diverse) == 2
    assert diverse[1][1]["embedding"] == [0.0, 1.0]
