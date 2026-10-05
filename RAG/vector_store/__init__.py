"""RAG.vector_store - Gói lưu trữ véc-tơ bền vững cho Traditional RAG."""

from __future__ import annotations

from RAG.vector_store.base import BaseVectorStore
from RAG.vector_store.chroma_store import PersistentChromaStore
from RAG.vector_store.schema import (
    VectorRecord,
    CollectionConfig,
    sanitize_metadata,
    desanitize_metadata,
)
from RAG.vector_store.exceptions import (
    VectorStoreError,
    DimensionMismatchError,
    CompatibilityError,
    CollectionNotFoundError,
    CollectionAlreadyExistsError,
    DuplicateIDError,
)
from RAG.vector_store.ingest import ingest_legal_dataset

__all__ = [
    "BaseVectorStore",
    "PersistentChromaStore",
    "VectorRecord",
    "CollectionConfig",
    "sanitize_metadata",
    "desanitize_metadata",
    "VectorStoreError",
    "DimensionMismatchError",
    "CompatibilityError",
    "CollectionNotFoundError",
    "CollectionAlreadyExistsError",
    "DuplicateIDError",
    "ingest_legal_dataset",
]
