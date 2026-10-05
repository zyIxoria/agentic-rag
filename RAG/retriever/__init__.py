"""RAG.retriever - Gói thu hồi thông tin ngữ nghĩa (Dense Semantic Retrieval)."""

from __future__ import annotations

from RAG.retriever.schema import RetrievedChunk
from RAG.retriever.config import RetrieverConfig, default_retriever_config
from RAG.retriever.base import BaseRetriever
from RAG.retriever.dense_retriever import DenseTopKRetriever

__all__ = [
    "RetrievedChunk",
    "RetrieverConfig",
    "default_retriever_config",
    "BaseRetriever",
    "DenseTopKRetriever",
]
