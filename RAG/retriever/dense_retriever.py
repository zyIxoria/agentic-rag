"""dense_retriever.py - Triển khai Dense Semantic Top-K Retriever cho Traditional RAG Baseline.

Tuân thủ nghiêm ngặt các nguyên tắc của TASK RAG-03:
- Kiến trúc thuần tuyến tính: Question -> Embedding -> Vector Search -> Top-K chunks.
- Không chứa BM25, hybrid search, reranker, query rewriting, expansion, hay corrective loop.
- Phân định rạch ròi giữa Distance (Cosine Distance từ ChromaDB) và Similarity (Cosine Similarity = 1 - Distance).
- Bảo toàn 100% metadata pháp lý từ Dataset V2.1 kèm khôi phục các giá trị None.
- Hỗ trợ đầy đủ bộ lọc ngưỡng SIMILARITY_THRESHOLD và tham số TOP_K linh hoạt.
"""

from __future__ import annotations
import logging
from datetime import date
from typing import List, Optional, Dict, Any, Union

from RAG.retriever.schema import RetrievedChunk
from RAG.retriever.base import BaseRetriever
from RAG.retriever.config import RetrieverConfig, default_retriever_config
from RAG.vector_store.chroma_store import PersistentChromaStore
from RAG.vector_store.schema import desanitize_metadata
from RAG.vector_store.base import BaseVectorStore
from RAG.embedding.embeddings import BaseEmbeddingProvider, get_embedding_provider

logger = logging.getLogger(__name__)


class DenseTopKRetriever(BaseRetriever):
    """Bộ thu hồi văn bản ngữ nghĩa sử dụng Dense Vector Search (ChromaDB + Embedding Model)."""

    def __init__(
        self,
        vector_store: Optional[BaseVectorStore] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        config: Optional[RetrieverConfig] = None,
    ):
        """Khởi tạo DenseTopKRetriever.
        
        Args:
            vector_store: Instance của PersistentChromaStore (nếu None sẽ tự nạp theo config).
            embedding_provider: Instance của BaseEmbeddingProvider (nếu None sẽ dùng factory mặc định).
            config: Cấu hình RetrieverConfig.
        """
        self.config = config or default_retriever_config
        self.embedding_provider = embedding_provider or get_embedding_provider()

        if vector_store is not None:
            self.vector_store = vector_store
        else:
            chroma = PersistentChromaStore(persist_directory=self.config.PERSIST_DIRECTORY)
            target_col = self.config.COLLECTION_NAME
            # Tự động map sang collection tương ứng với dimension của model nếu đang để tên mặc định
            if target_col == "legal_labor_baseline_minilm":
                if self.embedding_provider.dimension == 768 or "vietnamese-bi-encoder" in self.embedding_provider.model_name.lower():
                    target_col = "legal_labor_vietnamese_bi_encoder"
                elif self.embedding_provider.dimension == 1024 or "bge-m3" in self.embedding_provider.model_name.lower():
                    target_col = "legal_labor_bge_m3"

            # Kiểm tra nếu collection mục tiêu chưa tồn tại thì fallback an toàn về baseline minilm nếu dim khớp
            existing_cols = [c.name for c in chroma.client.list_collections()]
            if target_col not in existing_cols and self.config.COLLECTION_NAME in existing_cols:
                logger.warning(
                    "Collection '%s' chưa được khởi tạo trên ChromaDB. Sử dụng collection '%s' (dim=%d).",
                    target_col, self.config.COLLECTION_NAME, self.embedding_provider.dimension
                )
                target_col = self.config.COLLECTION_NAME

            chroma.load_collection(
                name=target_col,
                expected_dimension=self.embedding_provider.dimension,
                expected_model=self.embedding_provider.model_name,
            )
            self.vector_store = chroma

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        as_of_date: Optional[Union[str, date]] = None,
        auto_temporal: bool = False,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """Thu hồi danh sách Top-K chunks pháp lý có độ tương đồng ngữ nghĩa cao nhất với câu hỏi.
        
        Args:
            query: Câu hỏi hoặc văn bản cần tra cứu.
            top_k: Số lượng chunks tối đa cần thu hồi (mặc định lấy từ config).
            score_threshold: Ngưỡng tương đồng tối thiểu (mặc định lấy từ config).
            
        Returns:
            List[RetrievedChunk]: Danh sách các đoạn luật được xếp hạng từ 1..K.
            
        Raises:
            ValueError: Nếu query rỗng, chỉ chứa khoảng trắng, hoặc top_k <= 0.
        """
        # 1. Kiểm tra tính hợp lệ của query (Empty Query Handling - FAIL FAST)
        if query is None or not isinstance(query, str) or not query.strip():
            raise ValueError("Câu truy vấn (query) không được để rỗng hoặc chỉ chứa khoảng trắng.")

        # 2. Xác định tham số k và threshold
        k = top_k if top_k is not None else self.config.TOP_K
        if k <= 0:
            raise ValueError(f"top_k phải là số nguyên dương > 0, nhận được: {k}")

        threshold = score_threshold if score_threshold is not None else self.config.SIMILARITY_THRESHOLD

        # 3. Kiểm tra số lượng bản ghi hiện có trong collection
        total_chunks = self.vector_store.count()
        if total_chunks == 0:
            logger.warning("Vector store hiện tại rỗng (0 bản ghi). Trả về danh sách rỗng.")
            return []

        # Xác định số lượng ứng viên cần kéo từ ChromaDB
        is_temporal = (as_of_date is not None) or auto_temporal
        fetch_k = min(total_chunks, max(k * 3, 20)) if is_temporal else min(k, total_chunks)
        actual_k = fetch_k

        # 4. Sinh vector cho câu hỏi (Dense Query Embedding)
        query_vector = self.embedding_provider.embed_text(query.strip())

        # 5. Truy vấn Vector Store (Dense Search qua ChromaDB)
        # PersistentChromaStore cung cấp thuộc tính .collection để truy cập trực tiếp client query
        if not hasattr(self.vector_store, "collection") or self.vector_store.collection is None:
            raise RuntimeError("Collection chưa được kích hoạt trong Vector Store.")

        query_kwargs: Dict[str, Any] = {
            "query_embeddings": [query_vector],
            "n_results": actual_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where

        try:
            chroma_res = self.vector_store.collection.query(**query_kwargs)
        except AttributeError as ae:
            if "bindings" in str(ae):
                logger.warning("Gặp lỗi RustBindingsAPI bindings trong quá trình query. Đang tự động phục hồi và thử lại...")
                if hasattr(self.vector_store, "_ensure_active_connection"):
                    self.vector_store._ensure_active_connection()
                chroma_res = self.vector_store.collection.query(**query_kwargs)
            else:
                raise ae

        raw_ids = chroma_res.get("ids", [[]])[0]
        raw_docs = chroma_res.get("documents", [[]])[0]
        raw_metas = chroma_res.get("metadatas", [[]])[0]
        raw_dists = chroma_res.get("distances", [[]])[0]

        candidates: List[RetrievedChunk] = []

        # 6. Chuyển đổi Distance sang Similarity & Đóng gói RetrievedChunk
        for i in range(len(raw_ids)):
            cid = raw_ids[i]
            content = raw_docs[i] if i < len(raw_docs) else ""
            dist = float(raw_dists[i]) if i < len(raw_dists) else 1.0

            # Chuyển đổi tường minh Cosine Distance sang Cosine Similarity:
            # ChromaDB cosine distance: d = 1 - cos(theta)
            # Cosine similarity: s = 1 - d
            sim_score = 1.0 - dist

            # Áp dụng bộ lọc ngưỡng SIMILARITY_THRESHOLD (nếu có)
            if threshold is not None and sim_score < threshold:
                continue

            raw_meta = raw_metas[i] if i < len(raw_metas) else {}
            # Khôi phục các giá trị None trong metadata
            meta = desanitize_metadata(raw_meta, restore_none=True)

            candidates.append(
                RetrievedChunk(
                    chunk_id=cid,
                    content=content,
                    score=round(sim_score, 6),
                    distance=round(dist, 6),
                    metadata=meta,
                    rank=1,  # Tạm thời, sẽ gán chính thức sau khi sort
                )
            )

        # 7. Đảm bảo sắp xếp giảm dần theo score (Rank Assignment)
        candidates.sort(key=lambda c: c.score, reverse=True)

        final_results = candidates

        # Áp dụng Temporal Legal Filtering nếu có yêu cầu
        target_date = as_of_date
        if target_date is None and auto_temporal:
            from RAG.retriever.temporal_filter import TemporalLegalFilter
            target_date, _ = TemporalLegalFilter.extract_temporal_intent(query)

        if target_date is not None:
            from RAG.retriever.temporal_filter import TemporalLegalFilter
            t_filter = TemporalLegalFilter()
            final_results = t_filter.filter_chunks(final_results, as_of_date=target_date)

        # Giới hạn chính xác top_k sau khi lọc và cập nhật thứ hạng 1..K
        final_results = final_results[:k]
        for rank_idx, chunk in enumerate(final_results, start=1):
            chunk.rank = rank_idx

        logger.debug(
            f"Query '{query[:30]}...' -> Thu hồi {len(final_results)}/{k} chunks (Threshold: {threshold})."
        )
        return final_results
