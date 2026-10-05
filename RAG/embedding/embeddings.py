"""embeddings.py - Các lớp sinh véc-tơ (Embedding Providers) và Pipeline xử lý dữ liệu.

Tuân thủ nghiêm ngặt các yêu cầu của TASK RAG-01:
- Interface rõ ràng: embed_text(text) -> vector, embed_texts(texts) -> vectors.
- Hỗ trợ batch embedding theo kích thước lô cấu hình (EMBEDDING_BATCH_SIZE).
- Chuẩn hóa véc-tơ (NORMALIZE_EMBEDDINGS).
- Không hardcode model; cấu hình hóa linh hoạt qua EmbeddingConfig.
- Fallback rõ ràng từ GPU/CUDA sang CPU khi không có môi trường phần cứng/driver tương thích.
- Xử lý nội dung rỗng (Empty Content Handling) nghiêm ngặt (FAIL FAST với ValueError).
- Không chứa bất kỳ logic truy hồi (Retrieval/Search), Vector DB hay LLM nào.
"""

from __future__ import annotations
import os
import math
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import numpy as np

from RAG.config import EmbeddingConfig, default_embedding_config, resolve_device
from RAG.embedding.schema import (
    EmbeddedChunk,
    extract_preserved_metadata,
    validate_metadata_preservation,
    MANDATORY_METADATA_FIELDS,
)

logger = logging.getLogger(__name__)


def l2_normalize(vector: Union[List[float], np.ndarray]) -> List[float]:
    """Chuẩn hóa L2 cho một vector."""
    arr = np.asarray(vector, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr.tolist()


def l2_normalize_batch(vectors: List[List[float]]) -> List[List[float]]:
    """Chuẩn hóa L2 cho một batch các vector."""
    arr = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    normalized = arr / norms
    return normalized.tolist()


class BaseEmbeddingProvider(ABC):
    """Giao diện trừu tượng chuẩn mực cho tất cả các mô hình Embedding trong hệ thống."""

    def __init__(
        self,
        model_name: str,
        device: str = "cpu",
        batch_size: int = 64,
        normalize_embeddings: bool = True,
    ):
        self._model_name = model_name
        self._device = resolve_device(device)
        self._batch_size = max(1, batch_size)
        self._normalize_embeddings = normalize_embeddings

    @property
    def model_name(self) -> str:
        """Tên hoặc đường dẫn của mô hình."""
        return self._model_name

    @property
    def device(self) -> str:
        """Thiết bị thực thi hiện tại ('cuda' hoặc 'cpu')."""
        return self._device

    @property
    def batch_size(self) -> int:
        """Kích thước lô mặc định khi sinh vector."""
        return self._batch_size

    @property
    def normalize_embeddings(self) -> bool:
        """Có chuẩn hóa L2 vector hay không."""
        return self._normalize_embeddings

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Kích thước số chiều (dimension) của không gian véc-tơ."""
        pass

    @abstractmethod
    def _embed_batch_impl(self, texts: List[str]) -> List[List[float]]:
        """Triển khai sinh vector cho một lô văn bản đã được kiểm tra tính hợp lệ."""
        pass

    def embed_text(self, text: str) -> List[float]:
        """Tạo vector embedding cho một chuỗi văn bản đơn lẻ.
        
        Args:
            text: Chuỗi văn bản cần nhúng véc-tơ.
            
        Returns:
            List[float]: Vector véc-tơ có chiều dài bằng self.dimension.
            
        Raises:
            ValueError: Nếu văn bản rỗng hoặc chỉ chứa khoảng trắng.
        """
        if text is None or not isinstance(text, str) or not text.strip():
            raise ValueError("Nội dung văn bản cần embedding không được để rỗng hoặc chỉ chứa khoảng trắng.")

        vectors = self.embed_texts([text])
        return vectors[0]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Tạo vector embedding cho danh sách các chuỗi văn bản theo batch.
        
        Args:
            texts: Danh sách chuỗi văn bản cần nhúng.
            
        Returns:
            List[List[float]]: Danh sách các vector véc-tơ.
            
        Raises:
            ValueError: Nếu danh sách chứa phần tử rỗng hoặc chỉ chứa khoảng trắng.
        """
        if not texts:
            return []

        # Kiểm tra tính hợp lệ của từng chuỗi (Empty Content Handling - FAIL FAST)
        for idx, t in enumerate(texts):
            if t is None or not isinstance(t, str) or not t.strip():
                raise ValueError(
                    f"Phát hiện văn bản rỗng hoặc chỉ chứa khoảng trắng tại vị trí chỉ mục {idx}."
                )

        all_vectors: List[List[float]] = []
        total_texts = len(texts)

        # Xử lý cắt theo batch_size
        for start_idx in range(0, total_texts, self._batch_size):
            batch = texts[start_idx : start_idx + self._batch_size]
            batch_vectors = self._embed_batch_impl(batch)

            if len(batch_vectors) != len(batch):
                raise RuntimeError(
                    f"Kích thước vector trả về ({len(batch_vectors)}) không khớp kích thước batch ({len(batch)})."
                )

            # Kiểm tra tính nhất quán về kích thước chiều (Dimension Consistency)
            expected_dim = self.dimension
            for v_idx, vec in enumerate(batch_vectors):
                if len(vec) != expected_dim:
                    raise ValueError(
                        f"Lệch chiều vector tại phần tử {start_idx + v_idx}: kỳ vọng {expected_dim}, nhận được {len(vec)}."
                    )

            if self._normalize_embeddings:
                batch_vectors = l2_normalize_batch(batch_vectors)

            all_vectors.extend(batch_vectors)

        return all_vectors


class ONNXEmbeddingProvider(BaseEmbeddingProvider):
    """Provider cục bộ sử dụng ONNX Runtime qua Chroma's DefaultEmbeddingFunction hoặc ONNX MiniLM.
    
    Đặc điểm:
    - Chạy offline siêu tốc, không phụ thuộc PyTorch.
    - Hỗ trợ all-MiniLM-L6-v2 (384 dimensions).
    - Tự động fallback CPU nếu CUDA runtime chưa sẵn sàng.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu",
        batch_size: int = 64,
        normalize_embeddings: bool = True,
    ):
        super().__init__(
            model_name=model_name,
            device=device,
            batch_size=batch_size,
            normalize_embeddings=normalize_embeddings,
        )
        self._dim = 384
        self._init_model()

    def _init_model(self) -> None:
        """Khởi tạo engine ONNX với kiểm tra thiết bị an toàn."""
        try:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
            self._ef = DefaultEmbeddingFunction()
            # Thử nghiệm 1 mẫu nhỏ để xác định dimension chính xác
            test_vec = self._ef(["test"])[0]
            self._dim = len(test_vec)
            logger.info(
                "Đã nạp thành công ONNX Embedding Engine (Model: %s, Dimension: %d, Device: %s)",
                self.model_name, self._dim, self.device
            )
        except Exception as e:
            raise RuntimeError(f"Không thể khởi tạo ONNXEmbeddingProvider: {e}") from e

    @property
    def dimension(self) -> int:
        return self._dim

    def _embed_batch_impl(self, texts: List[str]) -> List[List[float]]:
        # DefaultEmbeddingFunction nhận List[str] và trả về List[ndarray] hoặc List[List[float]]
        raw_output = self._ef(texts)
        return [list(vec) if not isinstance(vec, list) else vec for vec in raw_output]


class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    """Provider cho SentenceTransformers (ví dụ BAAI/bge-m3, 1024 dimensions)."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "cpu",
        batch_size: int = 64,
        normalize_embeddings: bool = True,
    ):
        super().__init__(
            model_name=model_name,
            device=device,
            batch_size=batch_size,
            normalize_embeddings=normalize_embeddings,
        )
        self._init_model()

    def _init_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
            # Fallback thiết bị nếu yêu cầu cuda nhưng torch không có cuda
            actual_device = self.device
            logger.info("Khởi tạo SentenceTransformer với device: %s", actual_device)
            self._model = SentenceTransformer(self.model_name, device=actual_device)
            self._dim = self._model.get_sentence_embedding_dimension()
        except ImportError as e:
            raise ImportError(
                "Gói 'sentence-transformers' chưa được cài đặt trong môi trường hiện tại. "
                "Vui lòng sử dụng ONNXEmbeddingProvider hoặc cài đặt sentence-transformers."
            ) from e

    @property
    def dimension(self) -> int:
        return self._dim

    def _embed_batch_impl(self, texts: List[str]) -> List[List[float]]:
        embeddings = self._model.encode(
            texts,
            batch_size=self._batch_size,
            show_progress_bar=False,
            normalize_embeddings=False,  # Chuẩn hóa tập trung tại lớp cha
            device=self.device,
        )
        return embeddings.tolist()


class DeterministicMockEmbeddingProvider(BaseEmbeddingProvider):
    """Provider mô phỏng có tính tiền định (deterministic) cao phục vụ Unit Tests và CI/CD độc lập."""

    def __init__(
        self,
        model_name: str = "mock-deterministic-bge-m3",
        dimension: int = 384,
        device: str = "cpu",
        batch_size: int = 64,
        normalize_embeddings: bool = True,
    ):
        super().__init__(
            model_name=model_name,
            device=device,
            batch_size=batch_size,
            normalize_embeddings=normalize_embeddings,
        )
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _embed_batch_impl(self, texts: List[str]) -> List[List[float]]:
        results: List[List[float]] = []
        for text in texts:
            # Tạo seed ổn định tuyệt đối từ sha256 của chuỗi văn bản
            hasher = hashlib.sha256(text.encode("utf-8"))
            seed = int(hasher.hexdigest()[:8], 16)
            rng = np.random.RandomState(seed)
            # Sinh vector gaussian
            vec = rng.randn(self._dim).astype(np.float32).tolist()
            results.append(vec)
        return results


def get_embedding_provider(
    config: Optional[EmbeddingConfig] = None,
    **kwargs: Any
) -> BaseEmbeddingProvider:
    """Hàm Factory khởi tạo mô hình embedding phù hợp dựa trên cấu hình.
    
    Args:
        config: Đối tượng cấu hình EmbeddingConfig (nếu None sẽ dùng default_embedding_config).
        kwargs: Các thuộc tính ghi đè (override).
        
    Returns:
        BaseEmbeddingProvider instance.
    """
    cfg = config or default_embedding_config
    model_name = kwargs.get("model_name", cfg.EMBEDDING_MODEL)
    device = kwargs.get("device", cfg.EMBEDDING_DEVICE)
    batch_size = kwargs.get("batch_size", cfg.EMBEDDING_BATCH_SIZE)
    normalize = kwargs.get("normalize_embeddings", cfg.NORMALIZE_EMBEDDINGS)
    provider_type = kwargs.get("provider", cfg.EMBEDDING_PROVIDER).lower().strip()

    # Nếu chỉ định mock
    if provider_type == "mock" or "mock" in model_name.lower():
        dim = kwargs.get("dimension", 384)
        return DeterministicMockEmbeddingProvider(
            model_name=model_name,
            dimension=dim,
            device=device,
            batch_size=batch_size,
            normalize_embeddings=normalize,
        )

    # Nếu chỉ định sentence-transformers hoặc mô hình là bge-m3 mà sentence_transformers khả dụng
    if provider_type in ("sentence-transformers", "st"):
        return SentenceTransformerEmbeddingProvider(
            model_name=model_name,
            device=device,
            batch_size=batch_size,
            normalize_embeddings=normalize,
        )

    # Tự động phát hiện (auto)
    if provider_type == "auto":
        # Thử nạp SentenceTransformer nếu có
        try:
            import sentence_transformers  # noqa: F401
            # Nếu tên model là bge hoặc huggingface repo và gói st có sẵn
            if "bge" in model_name.lower() or "/" in model_name:
                return SentenceTransformerEmbeddingProvider(
                    model_name=model_name,
                    device=device,
                    batch_size=batch_size,
                    normalize_embeddings=normalize,
                )
        except ImportError:
            pass

    # Mặc định sử dụng ONNX runtime
    return ONNXEmbeddingProvider(
        model_name=model_name,
        device=device,
        batch_size=batch_size,
        normalize_embeddings=normalize,
    )


class LegalEmbeddingPipeline:
    """Đường ống nạp, trích xuất nội dung và sinh vector cho Legal Dataset V2.1."""

    def __init__(
        self,
        provider: Optional[BaseEmbeddingProvider] = None,
        config: Optional[EmbeddingConfig] = None,
    ):
        self.config = config or default_embedding_config
        self.provider = provider or get_embedding_provider(self.config)

    def process_chunks(self, raw_chunks: List[Dict[str, Any]]) -> List[EmbeddedChunk]:
        """Xử lý danh sách các chunk pháp lý thô thành các đối tượng EmbeddedChunk.
        
        Args:
            raw_chunks: Danh sách dictionary các chunk từ Dataset V2.1.
            
        Returns:
            List[EmbeddedChunk]: Danh sách các chunk đã nhúng vector kèm metadata bảo tồn 100%.
        """
        if not raw_chunks:
            return []

        # 1. Trích xuất nội dung và kiểm tra metadata
        texts_to_embed: List[str] = []
        metadata_list: List[Dict[str, Any]] = []
        chunk_ids: List[str] = []

        for idx, chunk in enumerate(raw_chunks):
            chunk_id = chunk.get("chunk_id")
            if not chunk_id:
                raise ValueError(f"Bản ghi tại vị trí {idx} thiếu trường bắt buộc 'chunk_id'.")

            content = chunk.get("content")
            if content is None or not isinstance(content, str) or not content.strip():
                raise ValueError(
                    f"Chunk {chunk_id} (chỉ mục {idx}) có nội dung rỗng hoặc không hợp lệ."
                )

            # Bảo tồn đủ 18 trường metadata
            meta = extract_preserved_metadata(chunk)

            chunk_ids.append(chunk_id)
            texts_to_embed.append(content)
            metadata_list.append(meta)

        # 2. Sinh vector hàng loạt qua provider
        logger.info(
            "Bắt đầu sinh embedding cho %d chunks (Model: %s, Device: %s, Batch size: %d)...",
            len(texts_to_embed), self.provider.model_name, self.provider.device, self.provider.batch_size
        )
        vectors = self.provider.embed_texts(texts_to_embed)

        # 3. Đóng gói thành EmbeddedChunk và kiểm thực bảo tồn metadata
        embedded_chunks: List[EmbeddedChunk] = []
        for i in range(len(raw_chunks)):
            emb_chunk = EmbeddedChunk(
                chunk_id=chunk_ids[i],
                content=texts_to_embed[i],
                embedding=vectors[i],
                metadata=metadata_list[i],
            )
            # Kiểm tra xác thực tính nguyên vẹn của metadata
            if not validate_metadata_preservation(raw_chunks[i], emb_chunk.metadata):
                raise RuntimeError(
                    f"Phát hiện thất thoát metadata khi xử lý chunk {chunk_ids[i]}."
                )

            embedded_chunks.append(emb_chunk)

        logger.info("Hoàn tất nhúng thành công %d chunks.", len(embedded_chunks))
        return embedded_chunks
