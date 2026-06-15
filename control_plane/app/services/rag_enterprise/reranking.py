import logging

logger = logging.getLogger(__name__)


def rerank_by_recency(
    scored_chunks: list[tuple[float, dict]],
) -> list[tuple[float, dict]]:
    return sorted(scored_chunks, key=lambda x: (x[0], x[1].get("created_at", "")), reverse=True)


def rerank_by_position(
    scored_chunks: list[tuple[float, dict]],
) -> list[tuple[float, dict]]:
    return sorted(scored_chunks, key=lambda x: (x[0], -x[1].get("chunk_index", 0)), reverse=True)


def rerank_diversity(
    scored_chunks: list[tuple[float, dict]],
    top_k: int = 5,
    lambda_mmr: float = 0.5,
) -> list[tuple[float, dict]]:
    if not scored_chunks:
        return []

    selected = [scored_chunks[0]]
    candidate_pool = scored_chunks[1:]

    while len(selected) < min(top_k, len(scored_chunks)):
        if not candidate_pool:
            break

        best_score = -float("inf")
        best_idx = 0

        for i, (score, chunk) in enumerate(candidate_pool):
            relevance = score
            max_similarity = (
                max(
                    _cosine_sim(chunk.get("embedding", []), s[1].get("embedding", []))
                    for s in selected
                )
                if selected
                else 0
            )
            mmr_score = lambda_mmr * relevance - (1 - lambda_mmr) * max_similarity

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = i

        selected.append(candidate_pool.pop(best_idx))

    return selected


def _cosine_sim(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def apply_reranking(
    scored_chunks: list[tuple[float, dict]],
    strategy: str = "position",
    top_k: int = 5,
) -> list[tuple[float, dict]]:
    strategies = {
        "recency": rerank_by_recency,
        "position": rerank_by_position,
        "diversity": lambda x: rerank_diversity(x, top_k),
    }

    fn = strategies.get(strategy, rerank_by_position)
    reranked = fn(scored_chunks)
    return reranked[:top_k]
