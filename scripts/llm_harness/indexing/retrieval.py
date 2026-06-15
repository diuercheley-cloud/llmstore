import os
from typing import Any

from ..tokenizer import TokenCounter
from .storage import IndexStorage


class VectorStoreInterface:
    def add_document(self, doc_id: str, text: str, metadata: dict) -> None:
        pass

    def similarity_search(self, query: str, k: int = 5) -> list[dict]:
        return []


def query_index(query_str: str, workspace_root: str = ".") -> list[dict[str, Any]]:
    storage = IndexStorage(workspace_root)
    index = storage.load_json("repo_index.json")
    if not index:
        return []

    results = []
    query_lower = query_str.lower().strip()
    language_filter = None
    for prefix in ("lang:", "language:"):
        if query_lower.startswith(prefix):
            remainder = query_lower[len(prefix) :].strip()
            parts = remainder.split(None, 1)
            language_filter = parts[0]
            query_lower = parts[1].strip() if len(parts) > 1 else ""
            break

    for rel_path, meta in index.items():
        score = 0
        path_lower = rel_path.lower()
        language = meta.get("language", "unknown").lower()

        if language_filter and language != language_filter:
            continue
        if language_filter:
            score += 5

        if query_lower and query_lower in path_lower:
            score += 15
            if os.path.basename(path_lower) == query_lower:
                score += 10

        symbols = meta.get("symbols", [])
        for sym in symbols:
            if query_lower and query_lower == sym.lower():
                score += 10
            elif query_lower and query_lower in sym.lower():
                score += 5

        full_path = os.path.join(workspace_root, rel_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            try:
                with open(full_path, errors="ignore") as f:
                    content = f.read()
                if query_lower:
                    count = content.lower().count(query_lower)
                    score += min(count, 20)
            except Exception:
                pass

        if score > 0:
            results.append(
                {
                    "path": rel_path,
                    "score": score,
                    "language": meta.get("language", "unknown"),
                    "size": meta.get("size", 0),
                    "modified_time": meta.get("modified_time", 0.0),
                    "imports": meta.get("imports", []),
                    "symbols": symbols,
                }
            )

    results.sort(key=lambda x: (-x["score"], x["path"]))
    return results


def get_retrieved_context(query_str: str, workspace_root: str = ".", max_tokens: int = 2000) -> str:
    results = query_index(query_str, workspace_root)
    if not results:
        return ""

    tokenizer = TokenCounter(method="auto")
    running_tokens = 0
    parts = ["=== Retrieved Context ==="]

    for res in results:
        if running_tokens >= max_tokens:
            break

        path = res["path"]
        full_path = os.path.join(workspace_root, path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            try:
                with open(full_path, errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            section = f"\n-- Match: {path} (Score: {res['score']}) --\n{content}\n"
            tokens = tokenizer.count_tokens(section)
            if running_tokens + tokens <= max_tokens:
                parts.append(section)
                running_tokens += tokens
            else:
                rem = max_tokens - running_tokens
                if rem > 100:
                    char_len = rem * 4
                    trunc = content[:char_len] + "\n... [TRUNCATED] ...\n"
                    parts.append(f"\n-- Match: {path} (Score: {res['score']}) --\n{trunc}")
                    running_tokens = max_tokens
                break

    return "\n".join(parts) if len(parts) > 1 else ""
