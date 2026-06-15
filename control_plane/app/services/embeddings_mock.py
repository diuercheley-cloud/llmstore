import hashlib
import logging
import struct
from typing import Union

logger = logging.getLogger(__name__)


def get_mock_embedding(text: str, dimensions: int = 384) -> list[float]:
    """
    Gera um embedding determinístico para um dado texto.
    Útil para testes e desenvolvimento sem backend real.
    """
    # Use SHA-256 to get a deterministic hash of the text
    hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()

    embedding = []
    current_hash = hash_bytes

    while len(embedding) < dimensions:
        # Cada hash (32 bytes) fornece 8 floats (4 bytes cada)
        for i in range(0, len(current_hash), 4):
            if len(embedding) >= dimensions:
                break
            # Convert 4 bytes to an unsigned int
            val = struct.unpack("!I", current_hash[i : i + 4])[0]
            # Normalize to a float between -1 and 1
            # We use a simple normalization for mock purposes
            float_val = (val / 0xFFFFFFFF) * 2 - 1
            embedding.append(round(float(float_val), 6))

        if len(embedding) < dimensions:
            # Hash again to get more pseudo-random but deterministic bits
            current_hash = hashlib.sha256(current_hash).digest()

    return embedding


def process_mock_embeddings(
    inputs: Union[str, list[str]], model: str, dimensions: int = 384
) -> dict:
    """
    Processa uma requisição de embeddings usando o backend mock.
    Retorna um dicionário compatível com a resposta da OpenAI.
    """
    if isinstance(inputs, str):
        inputs = [inputs]

    data = []
    total_tokens = 0

    for i, text in enumerate(inputs):
        embedding = get_mock_embedding(text, dimensions)
        # Estimativa simples de tokens (4 chars = 1 token)
        tokens = max(1, len(text) // 4)
        total_tokens += tokens

        data.append({"object": "embedding", "index": i, "embedding": embedding})

    return {
        "object": "list",
        "data": data,
        "model": model,
        "usage": {"prompt_tokens": total_tokens, "total_tokens": total_tokens},
    }
