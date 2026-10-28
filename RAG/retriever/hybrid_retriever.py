"""hybrid_retriever.py - Bộ truy xuất kết hợp (Hybrid Retriever: Dense + BM25) với Reciprocal Rank Fusion (RRF).

Đặc điểm kỹ thuật:
- Kết hợp sức mạnh ngữ nghĩa của Dense Bi-encoder và sức mạnh bắt từ khóa chính xác của BM25.
- Cả 2 retriever dùng chung 100% nguồn dữ liệu và tập chunk trong ChromaDB.
- Hợp nhất kết quả bằng thuật toán Reciprocal Rank Fusion (RRF, hằng số k=60).
- Ghi log minh bạch danh sách kết quả của từng retriever trước khi hợp nhất.
- Hỗ trợ chuyển đổi linh hoạt qua cờ mode: 'hybrid', 'dense', 'bm25'.
"""

from __future__ import annotations
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from RAG.retriever.base import BaseRetriever
from RAG.retriever.bm25_retriever import BM25OkapiRetriever
from RAG.retriever.config import RetrieverConfig, default_retriever_config
from RAG.retriever.dense_retriever import DenseTopKRetriever
from RAG.retriever.schema import RetrievedChunk

logger = logging.getLogger(__name__)


class HybridRetriever(BaseRetriever):
    """Bộ truy xuất lai kết hợp Dense và Lexical BM25 qua thuật toán RRF."""

    def __init__(
        self,
        config: Optional[RetrieverConfig] = None,
        dense_retriever: Optional[DenseTopKRetriever] = None,
        bm25_retriever: Optional[BM25OkapiRetriever] = None,
        mode: str = "hybrid",  # 'hybrid', 'dense', 'bm25'
        rrf_k: int = 60,
        dense_weight: float = 1.0,
        bm25_weight: float = 1.0,
    ):
        self.config = config or default_retriever_config
        self.mode = mode.lower()
        self.rrf_k = rrf_k
        self.dense_weight = dense_weight
        self.bm25_weight = bm25_weight

        # Khởi tạo Dense Retriever
        self.dense_retriever = dense_retriever or DenseTopKRetriever(config=self.config)
        
        # Khởi tạo BM25 Retriever dùng chung vector store
        self.bm25_retriever = bm25_retriever or BM25OkapiRetriever(
            config=self.config,
            vector_store=self.dense_retriever.vector_store
        )

        # Lưu vết kết quả truy xuất riêng biệt phục vụ audit
        self.last_dense_results: List[RetrievedChunk] = []
        self.last_bm25_results: List[RetrievedChunk] = []

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """Thực hiện truy xuất văn bản dựa trên chế độ cấu hình."""
        k = top_k or self.config.TOP_K

        # Chế độ chỉ dùng Dense
        if self.mode == "dense":
            results = self.dense_retriever.retrieve(
                query=query, top_k=k, score_threshold=score_threshold
            )
            self.last_dense_results = results
            self.last_bm25_results = []
            return results

        # Chế độ chỉ dùng BM25
        if self.mode == "bm25":
            results = self.bm25_retriever.retrieve(
                query=query, top_k=k, score_threshold=score_threshold, where=where
            )
            self.last_bm25_results = results
            self.last_dense_results = []
            return results

        # Chế độ HYBRID: Truy xuất ứng viên từ cả 2 nguồn (lấy 3*k ứng viên để rerank RRF)
        candidate_pool_size = max(k * 3, 20)

        dense_chunks = self.dense_retriever.retrieve(
            query=query, top_k=candidate_pool_size, score_threshold=None
        )
        bm25_chunks = self.bm25_retriever.retrieve(
            query=query, top_k=candidate_pool_size, score_threshold=None, where=where
        )

        self.last_dense_results = dense_chunks
        self.last_bm25_results = bm25_chunks

        # Áp dụng Reciprocal Rank Fusion (RRF)
        rrf_scores: Dict[str, float] = defaultdict(float)
        chunk_map: Dict[str, RetrievedChunk] = {}

        # 1. Chấm điểm từ Dense Ranking
        for rank, chunk in enumerate(dense_chunks, start=1):
            cid = chunk.chunk_id
            chunk_map[cid] = chunk
            rrf_scores[cid] += self.dense_weight / (self.rrf_k + rank)

        # 2. Chấm điểm từ BM25 Ranking
        for rank, chunk in enumerate(bm25_chunks, start=1):
            cid = chunk.chunk_id
            if cid not in chunk_map:
                chunk_map[cid] = chunk
            rrf_scores[cid] += self.bm25_weight / (self.rrf_k + rank)

        # Sắp xếp các chunk theo điểm RRF giảm dần
        sorted_cids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)
        max_rrf = rrf_scores[sorted_cids[0]] if sorted_cids else 1.0

        fused_results: List[RetrievedChunk] = []
        rank = 1

        for cid in sorted_cids:
            chunk = chunk_map[cid]
            raw_rrf = rrf_scores[cid]
            # Chuẩn hóa RRF về thang [0.0, 1.0]
            normalized_score = raw_rrf / max_rrf if max_rrf > 0 else 0.0

            if score_threshold is not None and normalized_score < score_threshold:
                continue

            fused_chunk = RetrievedChunk(
                chunk_id=chunk.chunk_id,
                content=chunk.content,
                metadata=chunk.metadata,
                score=round(normalized_score, 6),
                rank=rank,
                distance=round(1.0 - normalized_score, 6),
            )
            fused_results.append(fused_chunk)
            rank += 1
            if len(fused_results) >= k:
                break

        return fused_results
