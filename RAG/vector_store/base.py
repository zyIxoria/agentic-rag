"""base.py - Lớp cơ sở trừu tượng cho Vector Store trong Traditional RAG.

Định nghĩa interface chuẩn hóa cho các thao tác quản trị collection, nạp véc-tơ,
truy xuất theo ID và bền vững hóa dữ liệu.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from RAG.vector_store.schema import VectorRecord, CollectionConfig


class BaseVectorStore(ABC):
    """Giao diện trừu tượng cho Vector Store bền vững."""

    @abstractmethod
    def create_collection(
        self,
        name: str,
        embedding_dimension: int,
        embedding_model: str,
        dataset_version: str = "v2.1",
        distance_metric: str = "cosine",
        metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = False,
    ) -> Any:
        """Tạo collection mới với kiểm tra ràng buộc siêu dữ liệu an toàn."""
        pass

    @abstractmethod
    def load_collection(
        self,
        name: str,
        expected_dimension: Optional[int] = None,
        expected_model: Optional[str] = None,
        expected_version: Optional[str] = None,
    ) -> Any:
        """Tải collection hiện có kèm xác thực tính tương thích (FAIL FAST nếu không khớp)."""
        pass

    @abstractmethod
    def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        batch_size: int = 500,
        deduplicate_batch: bool = True,
    ) -> int:
        """Nạp hoặc cập nhật danh sách bản ghi véc-tơ vào collection hiện hành."""
        pass

    @abstractmethod
    def upsert_records(
        self,
        records: List[VectorRecord],
        batch_size: int = 500,
        deduplicate_batch: bool = True,
    ) -> int:
        """Nạp danh sách VectorRecord vào collection hiện hành."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Trả về tổng số bản ghi véc-tơ hiện có trong collection đang hoạt động."""
        pass

    @abstractmethod
    def get_by_id(
        self,
        chunk_id: str,
        restore_none: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Truy xuất bản ghi véc-tơ theo chunk_id chính xác."""
        pass

    @abstractmethod
    def persist(self) -> None:
        """Lưu trữ bền vững trạng thái vector store xuống đĩa cứng."""
        pass

    @abstractmethod
    def delete_collection(self, name: str, confirm: bool = False) -> None:
        """Xóa collection (bắt buộc xác nhận tường minh confirm=True)."""
        pass

    @abstractmethod
    def list_collections(self) -> List[str]:
        """Liệt kê danh sách tên toàn bộ collections hiện có."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Đóng kết nối và giải phóng tài nguyên."""
        pass


    @property
    @abstractmethod
    def active_collection_name(self) -> Optional[str]:
        """Tên của collection đang được kích hoạt."""
        pass

    @property
    @abstractmethod
    def embedding_dimension(self) -> Optional[int]:
        """Kích thước vector của collection hiện hành."""
        pass

    @property
    @abstractmethod
    def embedding_model(self) -> Optional[str]:
        """Tên mô hình embedding của collection hiện hành."""
        pass

    @property
    @abstractmethod
    def dataset_version(self) -> Optional[str]:
        """Phiên bản dataset của collection hiện hành."""
        pass
