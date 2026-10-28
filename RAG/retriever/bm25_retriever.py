"""bm25_retriever.py - Bộ truy xuất từ khóa chuẩn Okapi BM25 cho dữ liệu pháp luật lao động.

Đặc điểm kỹ thuật:
- Tương thích 100% với BaseRetriever và Schema RetrievedChunk hiện có.
- Sử dụng trực tiếp tập dữ liệu 1.390 chunk từ ChromaDB collection 'legal_labor_baseline_minilm'.
- Tokenizer chuyên biệt cho tiếng Việt: hỗ trợ từ đơn và cụm từ ghép (unigrams + bigrams pháp lý).
- Thuật toán Okapi BM25 chuẩn mực với k1 = 1.5, b = 0.75.
- Hoạt động 100% offline, tốc độ truy xuất cực nhanh (< 10ms).
"""

from __future__ import annotations
import math
import re
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from RAG.retriever.base import BaseRetriever
from RAG.retriever.config import RetrieverConfig, default_retriever_config
from RAG.retriever.schema import RetrievedChunk
from RAG.vector_store.chroma_store import PersistentChromaStore


class BM25OkapiRetriever(BaseRetriever):
    """Bộ truy xuất Lexical BM25 chuẩn Okapi xây dựng trên dữ liệu ChromaDB hiện có."""

    # Các từ dừng tiếng Việt phổ biến không mang nghĩa chủ đề
    DEFAULT_STOPWORDS = {
        "của", "cho", "các", "những", "được", "trong", "theo", "nào", "gì", "như",
        "thế", "khi", "quy", "định", "pháp", "luật", "phải", "khoản", "điều", "về",
        "có", "hay", "với", "tại", "ở", "này", "đó", "ra", "sao", "bao", "nhiêu",
        "một", "hai", "ba", "thực", "hiện", "áp", "dụng", "trường", "hợp", "vấn",
        "đề", "liên", "quan", "là", "và", "hoặc", "thời", "gian", "số", "lại",
        "thì", "đã", "sẽ", "tôi", "em", "mình", "cho_biết", "hỏi", "xin_hỏi"
    }

    def __init__(
        self,
        config: Optional[RetrieverConfig] = None,
        vector_store: Optional[PersistentChromaStore] = None,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        self.config = config or default_retriever_config
        self.k1 = k1
        self.b = b
        self._vector_store = vector_store
        
        # Cấu trúc Inverted Index
        self.chunk_ids: List[str] = []
        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 0.0
        self.corpus_size: int = 0
        self.doc_freqs: Dict[str, int] = Counter()
        self.inverted_index: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
        
        self._is_indexed = False
        self._initialize_from_store()

    def _initialize_from_store(self) -> None:
        """Đọc toàn bộ chunks từ ChromaDB collection để đồng bộ 100% dữ liệu."""
        if self._vector_store is None:
            self._vector_store = PersistentChromaStore(
                persist_directory=self.config.PERSIST_DIRECTORY
            )
            self._vector_store.load_collection(
                name=self.config.COLLECTION_NAME
            )

        collection = self._vector_store.collection
        all_data = collection.get(include=["documents", "metadatas"])
        
        self.chunk_ids = all_data["ids"]
        self.documents = all_data["documents"]
        self.metadatas = all_data["metadatas"]
        self.corpus_size = len(self.chunk_ids)

        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        """Tách từ tiếng Việt hỗ trợ unigrams và bigrams từ ghép có nghĩa."""
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        words = clean.split()
        
        # Lọc từ đơn ngắn hoặc stopwords
        tokens = [w for w in words if len(w) >= 2 and w not in self.DEFAULT_STOPWORDS]
        
        # Sinh bigrams để bắt cụm từ ghép pháp lý: "thôi_việc", "trợ_cấp", "mất_việc", "lao_động"
        bigrams = []
        for i in range(len(words) - 1):
            w1, w2 = words[i], words[i + 1]
            if w1 not in self.DEFAULT_STOPWORDS or w2 not in self.DEFAULT_STOPWORDS:
                bigrams.append(f"{w1}_{w2}")
                
        return tokens + bigrams

    def _build_index(self) -> None:
        """Xây dựng chỉ mục ngược (Inverted Index) và tính tần suất Document Frequency."""
        t0 = time.perf_counter()
        self.doc_lengths = []
        self.doc_freqs.clear()
        self.inverted_index.clear()

        for doc_idx, doc_text in enumerate(self.documents):
            # Kết hợp cả tiêu đề Điều và nội dung để tăng trọng số thực thể
            meta = self.metadatas[doc_idx] if doc_idx < len(self.metadatas) else {}
            title = meta.get("article_title", "")
            art_num = meta.get("article_number", "")
            doc_id = meta.get("document_id", "")
            full_text = f"{doc_id} Điều {art_num} {title} {doc_text}"
            
            tokens = self._tokenize(full_text)
            self.doc_lengths.append(len(tokens))
            
            term_counts = Counter(tokens)
            for term, count in term_counts.items():
                self.doc_freqs[term] += 1
                self.inverted_index[term].append((doc_idx, count))

        self.avg_doc_len = sum(self.doc_lengths) / max(1, self.corpus_size)
        self._is_indexed = True
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """Thực hiện truy xuất Top-K văn bản theo điểm số Okapi BM25."""
        if not query or not query.strip():
            return []

        k = top_k or self.config.TOP_K
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # Tính điểm BM25 cho từng tài liệu có chứa ít nhất một query term
        doc_scores: Dict[int, float] = defaultdict(float)

        for q_term in query_tokens:
            if q_term not in self.doc_freqs:
                continue

            n_q = self.doc_freqs[q_term]
            # Công thức Robertson-Spärck Jones IDF
            idf = math.log((self.corpus_size - n_q + 0.5) / (n_q + 0.5) + 1.0)
            
            postings = self.inverted_index[q_term]
            for doc_idx, freq in postings:
                doc_len = self.doc_lengths[doc_idx]
                numerator = freq * (self.k1 + 1.0)
                denominator = freq + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                doc_scores[doc_idx] += idf * (numerator / denominator)

        if not doc_scores:
            return []

        # Sắp xếp giảm dần theo điểm BM25
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        max_score = sorted_docs[0][1] if sorted_docs else 1.0

        retrieved: List[RetrievedChunk] = []
        rank = 1

        for doc_idx, raw_score in sorted_docs:
            if where:
                # Áp dụng bộ lọc metadata nếu có
                meta = self.metadatas[doc_idx]
                match = True
                for wk, wv in where.items():
                    if meta.get(wk) != wv:
                        match = False
                        break
                if not match:
                    continue

            # Chuẩn hóa điểm số về khoảng [0.0, 1.0] tương đối để so sánh
            normalized_score = raw_score / max_score if max_score > 0 else 0.0

            if score_threshold is not None and normalized_score < score_threshold:
                continue

            chunk = RetrievedChunk(
                chunk_id=self.chunk_ids[doc_idx],
                content=self.documents[doc_idx],
                metadata=self.metadatas[doc_idx],
                score=round(normalized_score, 6),
                rank=rank,
                distance=round(1.0 - normalized_score, 6),
            )
            retrieved.append(chunk)
            rank += 1
            if len(retrieved) >= k:
                break

        return retrieved
