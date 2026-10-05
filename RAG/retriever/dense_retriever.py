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
from typing import List, Optional, Dict, Any

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
            chroma.load_collection(
                name=self.config.COLLECTION_NAME,
                expected_dimension=self.embedding_provider.dimension,
                expected_model=self.embedding_provider.model_name,
            )
            self.vector_store = chroma

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
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

        # Giới hạn k tối đa bằng quy mô corpus (Tránh lỗi ChromaDB n_results > count)
        actual_k = min(k, total_chunks)

        # 4. Sinh vector cho câu hỏi (Dense Query Embedding)
        query_vector = self.embedding_provider.embed_text(query.strip())

        # 5. Truy vấn Vector Store (Dense Search qua ChromaDB)
        # PersistentChromaStore cung cấp thuộc tính .collection để truy cập trực tiếp client query
        if not hasattr(self.vector_store, "collection") or self.vector_store.collection is None:
            raise RuntimeError("Collection chưa được kích hoạt trong Vector Store.")

        chroma_res = self.vector_store.collection.query(
            query_embeddings=[query_vector],
            n_results=actual_k,
            include=["documents", "metadatas", "distances"],
        )

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

        # Giới hạn chính xác top_k sau khi lọc ngưỡng và gán thứ hạng 1..K
        final_results: List[RetrievedChunk] = []
        for rank_idx, chunk in enumerate(candidates[:k], start=1):
            chunk.rank = rank_idx
            final_results.append(chunk)

        logger.debug(
            f"Query '{query[:30]}...' -> Thu hồi {len(final_results)}/{k} chunks (Threshold: {threshold})."
        )
        return final_results
