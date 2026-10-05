"""RAG Embedding Package.

Cung cấp interface và pipeline chuyển đổi văn bản pháp lý thành vector véc-tơ:
- BaseEmbeddingProvider: Interface trừu tượng cho embedding models.
- ONNXEmbeddingProvider: Bộ nhúng véc-tơ cục bộ qua ONNX runtime (all-MiniLM-L6-v2).
- DeterministicMockEmbeddingProvider: Bộ nhúng mô phỏng cho unit test độc lập.
- LegalEmbeddingPipeline: Đường ống xử lý Dataset V2.1 với bảo toàn 100% metadata.
- EmbeddedChunk: Cấu trúc bản ghi vector kèm siêu dữ liệu.
"""

from __future__ import annotations

from RAG.config import EmbeddingConfig, resolve_device, default_embedding_config
from RAG.embedding.schema import (
    EmbeddedChunk,
    MANDATORY_METADATA_FIELDS,
    extract_preserved_metadata,
    validate_metadata_preservation,
    infer_content_type,
)
from RAG.embedding.embeddings import (
    BaseEmbeddingProvider,
    ONNXEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
    DeterministicMockEmbeddingProvider,
    LegalEmbeddingPipeline,
    get_embedding_provider,
    l2_normalize,
    l2_normalize_batch,
)

__all__ = [
    "EmbeddingConfig",
    "resolve_device",
    "default_embedding_config",
    "EmbeddedChunk",
    "MANDATORY_METADATA_FIELDS",
    "extract_preserved_metadata",
    "validate_metadata_preservation",
    "infer_content_type",
    "BaseEmbeddingProvider",
    "ONNXEmbeddingProvider",
    "SentenceTransformerEmbeddingProvider",
    "DeterministicMockEmbeddingProvider",
    "LegalEmbeddingPipeline",
    "get_embedding_provider",
    "l2_normalize",
    "l2_normalize_batch",
]
