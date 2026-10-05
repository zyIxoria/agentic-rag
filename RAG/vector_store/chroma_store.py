"""chroma_store.py - Triển khai Persistent Vector Store sử dụng ChromaDB.

Đáp ứng đầy đủ các yêu cầu của TASK RAG-02:
- Lưu trữ bền vững trên đĩa (PersistentClient).
- 1 vector / chunk, bảo toàn 100% chunk_id và legal metadata.
- Kiểm tra tính tương thích và kích hoạt cơ chế FAIL FAST khi sai lệch kích thước vector.
- Không chứa bất kỳ logic truy hồi (Retrieval/Search) hay LLM nào.
"""

from __future__ import annotations
import os
import logging
from typing import List, Dict, Any, Optional, Union
import chromadb
from chromadb.config import Settings

from RAG.vector_store.base import BaseVectorStore
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
)

logger = logging.getLogger(__name__)


class PersistentChromaStore(BaseVectorStore):
    """Lớp quản lý ChromaDB Persistent Vector Store."""

    def __init__(
        self,
        persist_directory: str = "data/chroma_db",
        anonymized_telemetry: bool = False,
    ):
        """Khởi tạo ChromaDB Persistent Client.
        
        Args:
            persist_directory: Thư mục đĩa lưu trữ cơ sở dữ liệu véc-tơ.
            anonymized_telemetry: Tắt/bật thu thập thông tin của ChromaDB.
        """
        self._persist_directory = os.path.abspath(persist_directory)
        os.makedirs(self._persist_directory, exist_ok=True)

        settings = Settings(
            anonymized_telemetry=anonymized_telemetry,
            is_persistent=True,
            persist_directory=self._persist_directory,
        )
        self._client = chromadb.PersistentClient(
            path=self._persist_directory,
            settings=settings
        )
        self._collection: Optional[chromadb.Collection] = None
        self._config: Optional[CollectionConfig] = None

    @property
    def persist_directory(self) -> str:
        """Đường dẫn thư mục lưu trữ bền vững."""
        return self._persist_directory

    @property
    def client(self) -> chromadb.PersistentClient:
        """Truy cập đối tượng client ChromaDB cấp thấp."""
        return self._client

    @property
    def collection(self) -> Optional[chromadb.Collection]:
        """Truy cập đối tượng collection ChromaDB đang hoạt động."""
        return self._collection

    @property
    def active_collection_name(self) -> Optional[str]:
        """Tên collection đang được kích hoạt."""
        return self._collection.name if self._collection else None

    @property
    def embedding_dimension(self) -> Optional[int]:
        """Số chiều vector của collection hiện hành."""
        return self._config.embedding_dimension if self._config else None

    @property
    def embedding_model(self) -> Optional[str]:
        """Tên mô hình embedding của collection hiện hành."""
        return self._config.embedding_model if self._config else None

    @property
    def dataset_version(self) -> Optional[str]:
        """Phiên bản dataset của collection hiện hành."""
        return self._config.dataset_version if self._config else None

    def create_collection(
        self,
        name: str,
        embedding_dimension: int,
        embedding_model: str,
        dataset_version: str = "v2.1",
        distance_metric: str = "cosine",
        metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = False,
    ) -> chromadb.Collection:
        """Tạo mới hoặc kết nối an toàn tới collection trong ChromaDB.
        
        Args:
            name: Tên của collection.
            embedding_dimension: Số chiều của vector (bắt buộc > 0).
            embedding_model: Tên mô hình embedding (VD: 'BAAI/bge-m3').
            dataset_version: Phiên bản dataset (VD: 'v2.1').
            distance_metric: Phép đo khoảng cách ('cosine', 'l2', 'ip'). Mặc định 'cosine'.
            metadata: Các thuộc tính mở rộng.
            overwrite: Nếu True và collection đã tồn tại, xóa và tạo lại.
            
        Raises:
            ValueError: Nếu embedding_dimension <= 0 hoặc tham số không hợp lệ.
            DimensionMismatchError: Nếu collection đã tồn tại nhưng có dimension khác (FAIL FAST).
            CompatibilityError: Nếu collection đã tồn tại nhưng có model hoặc version khác.
        """
        if embedding_dimension <= 0:
            raise ValueError(f"embedding_dimension phải là số nguyên dương > 0, nhận được: {embedding_dimension}")
        if not name or not str(name).strip():
            raise ValueError("Tên collection không được để trống.")

        cfg = CollectionConfig(
            dataset_version=dataset_version,
            embedding_model=embedding_model,
            embedding_dimension=embedding_dimension,
            distance_metric=distance_metric,
            extra=metadata or {},
        )

        existing_names = [c.name for c in self._client.list_collections()]
        if name in existing_names:
            if overwrite:
                logger.warning(f"Ghi đè collection '{name}' theo yêu cầu overwrite=True.")
                self._client.delete_collection(name=name)
            else:
                # Collection đã tồn tại -> Kiểm tra tính tương thích (FAIL FAST nếu sai lệch)
                col = self._client.get_collection(name=name)
                col_meta = col.metadata or {}
                actual_dim = col_meta.get("embedding_dimension")
                actual_model = col_meta.get("embedding_model")
                actual_ver = col_meta.get("dataset_version")

                if actual_dim is not None and int(actual_dim) != embedding_dimension:
                    raise DimensionMismatchError(
                        f"FAIL FAST: Collection '{name}' đã tồn tại với dimension {actual_dim}, "
                        f"không tương thích với dimension yêu cầu {embedding_dimension}."
                    )
                if actual_model is not None and str(actual_model) != embedding_model:
                    raise CompatibilityError(
                        f"FAIL FAST: Collection '{name}' đã tồn tại với model '{actual_model}', "
                        f"không tương thích với model yêu cầu '{embedding_model}'."
                    )
                if actual_ver is not None and str(actual_ver) != dataset_version:
                    raise CompatibilityError(
                        f"FAIL FAST: Collection '{name}' đã tồn tại với dataset_version '{actual_ver}', "
                        f"không tương thích với version yêu cầu '{dataset_version}'."
                    )

                self._collection = col
                self._config = CollectionConfig.from_metadata(col_meta)
                logger.info(f"Đã nạp collection hiện có '{name}' (dimension={actual_dim}, model='{actual_model}').")
                return self._collection

        col_metadata = cfg.to_metadata()
        col = self._client.create_collection(
            name=name,
            metadata=col_metadata,
        )
        self._collection = col
        self._config = cfg
        logger.info(f"Đã tạo mới collection '{name}' (dimension={embedding_dimension}, model='{embedding_model}').")
        return self._collection

    def load_collection(
        self,
        name: str,
        expected_dimension: Optional[int] = None,
        expected_model: Optional[str] = None,
        expected_version: Optional[str] = None,
    ) -> chromadb.Collection:
        """Tải collection hiện có từ đĩa cứng kèm kiểm tra tính tương thích nghiêm ngặt.
        
        Args:
            name: Tên collection cần nạp.
            expected_dimension: Kích thước vector kỳ vọng (FAIL FAST nếu không khớp).
            expected_model: Tên mô hình kỳ vọng (FAIL FAST nếu không khớp).
            expected_version: Phiên bản dataset kỳ vọng (FAIL FAST nếu không khớp).
            
        Raises:
            CollectionNotFoundError: Nếu collection không tồn tại trên đĩa.
            DimensionMismatchError: Nếu kích thước vector không khớp cấu hình kỳ vọng.
            CompatibilityError: Nếu mô hình hoặc phiên bản dataset không khớp.
        """
        existing_names = [c.name for c in self._client.list_collections()]
        if name not in existing_names:
            raise CollectionNotFoundError(
                f"Không tìm thấy collection '{name}' trong cơ sở dữ liệu tại {self._persist_directory}. "
                f"Danh sách hiện có: {existing_names}"
            )

        col = self._client.get_collection(name=name)
        col_meta = col.metadata or {}

        # FAIL FAST nếu dimension không khớp
        actual_dim = col_meta.get("embedding_dimension")
        if expected_dimension is not None:
            if actual_dim is not None and int(actual_dim) != int(expected_dimension):
                raise DimensionMismatchError(
                    f"FAIL FAST: Collection '{name}' có dimension {actual_dim}, "
                    f"không khớp với dimension kỳ vọng {expected_dimension}."
                )

        # FAIL FAST nếu embedding_model không khớp
        actual_model = col_meta.get("embedding_model")
        if expected_model is not None:
            if actual_model is not None and str(actual_model) != str(expected_model):
                raise CompatibilityError(
                    f"FAIL FAST: Collection '{name}' sử dụng model '{actual_model}', "
                    f"không khớp với model kỳ vọng '{expected_model}'."
                )

        # FAIL FAST nếu dataset_version không khớp
        actual_ver = col_meta.get("dataset_version")
        if expected_version is not None:
            if actual_ver is not None and str(actual_ver) != str(expected_version):
                raise CompatibilityError(
                    f"FAIL FAST: Collection '{name}' có dataset_version '{actual_ver}', "
                    f"không khớp với version kỳ vọng '{expected_version}'."
                )

        self._collection = col
        self._config = CollectionConfig.from_metadata(col_meta)
        logger.info(f"Đã tải thành công collection '{name}'.")
        return self._collection

    def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        batch_size: int = 500,
        deduplicate_batch: bool = True,
    ) -> int:
        """Nạp hoặc cập nhật danh sách bản ghi véc-tơ vào collection hiện hành.
        
        Args:
            ids: Danh sách chunk_id duy nhất (từ Dataset V2.1).
            embeddings: Danh sách các véc-tơ float tương ứng.
            documents: Danh sách nội dung văn bản content.
            metadatas: Danh sách dictionary siêu dữ liệu pháp lý.
            batch_size: Kích thước phân lô khi gọi ChromaDB upsert.
            deduplicate_batch: Nếu True, tự động giữ bản ghi xuất hiện sau cùng cho mỗi ID trùng lặp.
            
        Returns:
            Số lượng bản ghi thực tế được nạp vào store.
            
        Raises:
            VectorStoreError: Nếu chưa có collection nào được kích hoạt.
            ValueError: Nếu kích thước các mảng đầu vào không đồng nhất hoặc ID rỗng.
            DimensionMismatchError: Nếu bất kỳ vector nào có dimension khác với collection (FAIL FAST).
        """
        if self._collection is None:
            raise VectorStoreError(
                "Chưa kích hoạt collection nào. Vui lòng gọi create_collection() hoặc load_collection() trước."
            )

        n_records = len(ids)
        if n_records == 0:
            logger.info("Mảng đầu vào rỗng. Bỏ qua thao tác upsert.")
            return 0

        if len(embeddings) != n_records:
            raise ValueError(f"Số lượng embeddings ({len(embeddings)}) không khớp với số lượng ids ({n_records}).")
        if len(documents) != n_records:
            raise ValueError(f"Số lượng documents ({len(documents)}) không khớp với số lượng ids ({n_records}).")
        if metadatas is not None and len(metadatas) != n_records:
            raise ValueError(f"Số lượng metadatas ({len(metadatas)}) không khớp với số lượng ids ({n_records}).")

        # Chuẩn bị metadatas mặc định nếu None
        if metadatas is None:
            metadatas = [{} for _ in range(n_records)]

        # Xác thực chunk_id và Dimension của từng vector (FAIL FAST)
        target_dim = self.embedding_dimension
        for idx in range(n_records):
            cid = ids[idx]
            if not cid or not str(cid).strip():
                raise ValueError(f"chunk_id tại chỉ mục {idx} bị rỗng hoặc không hợp lệ.")

            emb = embeddings[idx]
            if not isinstance(emb, list):
                raise TypeError(f"Vector tại chỉ mục {idx} phải là List[float], nhận được: {type(emb)}")
            if target_dim is not None and len(emb) != target_dim:
                raise DimensionMismatchError(
                    f"FAIL FAST: Vector tại chỉ mục {idx} (ID='{cid}') có số chiều {len(emb)}, "
                    f"không khớp với số chiều của collection ({target_dim})."
                )

        # Xử lý ID trùng lặp trong cùng batch nếu bật deduplicate_batch
        final_ids = ids
        final_embeddings = embeddings
        final_documents = documents
        final_metadatas = metadatas

        if deduplicate_batch and len(ids) > len(set(ids)):
            seen: Dict[str, int] = {}
            for i, cid in enumerate(ids):
                seen[cid] = i
            unique_indices = sorted(seen.values())
            logger.warning(
                f"Phát hiện {len(ids) - len(unique_indices)} ID trùng lặp trong batch. "
                f"Tự động giữ lại bản ghi sau cùng cho mỗi ID (1 vector / chunk)."
            )
            final_ids = [ids[i] for i in unique_indices]
            final_embeddings = [embeddings[i] for i in unique_indices]
            final_documents = [documents[i] for i in unique_indices]
            final_metadatas = [metadatas[i] for i in unique_indices]

        # Chuẩn hóa metadata sang định dạng an toàn cho ChromaDB
        # Nếu toàn bộ metadata rỗng, truyền None để ChromaDB không báo lỗi '0 metadata attributes'
        all_empty_meta = all((not m) for m in final_metadatas)
        sanitized_metas = None if all_empty_meta else [sanitize_metadata(m) for m in final_metadatas]

        # Nạp theo từng lô (Batching)
        total_upserted = 0
        total_items = len(final_ids)
        for start_idx in range(0, total_items, batch_size):
            end_idx = min(start_idx + batch_size, total_items)
            b_ids = final_ids[start_idx:end_idx]
            b_embs = final_embeddings[start_idx:end_idx]
            b_docs = final_documents[start_idx:end_idx]
            b_metas = None if sanitized_metas is None else sanitized_metas[start_idx:end_idx]

            self._collection.upsert(
                ids=b_ids,
                embeddings=b_embs,
                documents=b_docs,
                metadatas=b_metas,
            )
            total_upserted += len(b_ids)


        self.persist()
        return total_upserted

    def upsert_records(
        self,
        records: List[VectorRecord],
        batch_size: int = 500,
        deduplicate_batch: bool = True,
    ) -> int:
        """Nạp danh sách đối tượng VectorRecord vào collection."""
        if not records:
            return 0
        ids = [r.id for r in records]
        embeddings = [r.embedding for r in records]
        documents = [r.document for r in records]
        metadatas = [r.metadata for r in records]
        return self.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            batch_size=batch_size,
            deduplicate_batch=deduplicate_batch,
        )

    def count(self) -> int:
        """Trả về tổng số bản ghi véc-tơ hiện có trong collection đang hoạt động."""
        if self._collection is None:
            raise VectorStoreError("Chưa kích hoạt collection nào. Vui lòng nạp hoặc tạo collection trước.")
        return self._collection.count()

    def get_by_id(
        self,
        chunk_id: str,
        restore_none: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Truy xuất bản ghi véc-tơ theo chunk_id chính xác.
        
        Args:
            chunk_id: Mã định danh chunk cần tìm.
            restore_none: Nếu True, khôi phục các trường rỗng về None nguyên bản.
            
        Returns:
            Dictionary chứa 'id', 'embedding', 'document', 'metadata', hoặc None nếu không tìm thấy.
        """
        if self._collection is None:
            raise VectorStoreError("Chưa kích hoạt collection nào. Vui lòng nạp hoặc tạo collection trước.")

        res = self._collection.get(
            ids=[chunk_id],
            include=["embeddings", "documents", "metadatas"],
        )

        if not res["ids"] or len(res["ids"]) == 0:
            return None

        raw_meta = res["metadatas"][0] if res["metadatas"] else {}
        meta = desanitize_metadata(raw_meta, restore_none=restore_none) if raw_meta else {}

        emb = None
        if res["embeddings"] is not None and len(res["embeddings"]) > 0:
            emb = res["embeddings"][0]

        doc = ""
        if res["documents"] is not None and len(res["documents"]) > 0:
            doc = res["documents"][0]

        return {
            "id": res["ids"][0],
            "embedding": emb,
            "document": doc,
            "metadata": meta,
        }

    def persist(self) -> None:
        """Đảm bảo trạng thái dữ liệu được ghi bền vững xuống ổ đĩa.
        
        Đối với ChromaDB PersistentClient >= 0.4.0, các thay đổi được ghi tự động.
        Phương thức này kiểm tra và kích hoạt hook persist nếu client hỗ trợ.
        """
        if hasattr(self._client, "persist"):
            self._client.persist()

    def delete_collection(self, name: str, confirm: bool = False) -> None:
        """Xóa một collection khỏi vector database.
        
        Bắt buộc phải đặt confirm=True để ngăn chặn hành vi vô tình xóa dữ liệu.
        
        Args:
            name: Tên collection cần xóa.
            confirm: Cờ xác nhận tường minh.
            
        Raises:
            PermissionError: Nếu confirm=False.
        """
        if not confirm:
            raise PermissionError(
                f"Hành động xóa collection '{name}' bị chặn vì chưa được xác nhận tường minh. "
                f"Vui lòng đặt tham số confirm=True để thực thi."
            )
        self._client.delete_collection(name=name)
        if self._collection and self._collection.name == name:
            self._collection = None
            self._config = None
        logger.info(f"Đã xóa thành công collection '{name}'.")

    def list_collections(self) -> List[str]:
        """Liệt kê danh sách tên toàn bộ các collections hiện có trên đĩa."""
        return [c.name for c in self._client.list_collections()]

    def close(self) -> None:
        """Đóng kết nối cơ sở dữ liệu và giải phóng tài nguyên."""
        self._collection = None
        self._config = None


