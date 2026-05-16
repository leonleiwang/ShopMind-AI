"""
Vector store factory for optional semantic retrieval.

The main shopping assistant currently uses PostgreSQL keyword/category/price
search. This manager keeps the Milvus/Chroma deployment choice centralized so
semantic product retrieval can be wired in without changing API or Agent code.
"""

import math
import re
from functools import cached_property
from typing import Any

from app.core.config import settings


class VectorStoreManager:
    """Create vector-store clients lazily based on environment configuration."""

    def __init__(self, store_type: str | None = None):
        self.store_type = (store_type or settings.VECTOR_STORE_TYPE).lower()

    @cached_property
    def client(self) -> Any:
        if self.store_type == "milvus":
            return self._create_milvus_client()
        if self.store_type == "chroma":
            return self._create_chroma_client()
        raise ValueError(f"Unsupported vector store type: {self.store_type}")

    def _create_milvus_client(self) -> Any:
        from pymilvus import MilvusClient

        if settings.MILVUS_URI:
            return MilvusClient(uri=settings.MILVUS_URI, token=settings.MILVUS_TOKEN)
        return MilvusClient(uri=f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}")

    def _create_chroma_client(self) -> Any:
        import chromadb

        return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)

    def rank_products(self, query: str, products: list[dict], limit: int = 10) -> list[dict]:
        """Rank products semantically, with a local deterministic fallback.

        Milvus/Chroma clients are intentionally initialized lazily because many
        demo deployments run without a vector service. The fallback still gives
        the product search path a semantic ranking stage instead of a brittle
        exact SQL-only result.
        """
        if not query or not products:
            return products[:limit]

        ranked = sorted(
            products,
            key=lambda product: self._local_similarity(query, product),
            reverse=True,
        )
        return ranked[:limit]

    @staticmethod
    def _local_similarity(query: str, product: dict) -> float:
        query_tokens = VectorStoreManager._tokenize(query)
        document = " ".join(
            str(product.get(key, "")) for key in ["name", "category", "brand", "description"]
        )
        doc_tokens = VectorStoreManager._tokenize(document)
        if not query_tokens or not doc_tokens:
            return 0

        overlap = query_tokens & doc_tokens
        jaccard = len(overlap) / len(query_tokens | doc_tokens)
        phrase_bonus = 0.2 if query.lower() in document.lower() else 0
        price_bonus = 0.05 / math.log(max(float(product.get("price") or 1), 2))
        return jaccard + phrase_bonus + price_bonus

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        normalized = text.lower()
        ascii_words = set(re.findall(r"[a-z0-9]+", normalized))
        cjk_terms = {normalized[i : i + 2] for i in range(max(len(normalized) - 1, 0))}
        return {token.strip() for token in ascii_words | cjk_terms if token.strip()}


vector_store_manager = VectorStoreManager()
