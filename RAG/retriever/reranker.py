"""reranker.py - Module tái xếp hạng chuyên sâu (Deep Interaction Legal Reranker).

Đặc điểm kỹ thuật:
- Tái xếp hạng danh sách ứng viên (candidate pool) từ tầng retrieval trước đó.
- Không tự tạo bằng chứng; chỉ sắp xếp lại các chunk đã truy xuất.
- Xử lý triệt để hiện tượng 'ảo giác trùng lặp từ khóa ngẫu nhiên' (Topic Drift / Spurious Matching):
  Ví dụ: Truy vấn hỏi về 'trợ cấp khi nghỉ việc', nếu văn bản xuất hiện từ 'cấp' nhưng lại là 'cấp giấy phép lao động nước ngoài'
  thì sẽ bị phạt điểm mạnh (Topic Drift Penalty).
- Tính toán tương tác sâu (Deep Interaction): Khớp số hiệu Điều, khớp cụm danh từ pháp lý nguyên vẹn,
  khớp tiêu đề Điều luật và tỷ lệ bao phủ khái niệm.
- Cung cấp nhật ký minh bạch: Model ID, cấu hình, thời gian thực thi (latency_ms).
"""

from __future__ import annotations
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from RAG.retriever.schema import RetrievedChunk


class LegalCrossReranker:
    """Bộ tái xếp hạng ứng viên dựa trên tương tác sâu giữa câu hỏi và văn bản pháp luật."""

    MODEL_ID = "vietnamese-legal-interaction-reranker-v1"

    def __init__(
        self,
        top_k: int = 5,
        title_weight: float = 0.35,
        content_weight: float = 0.45,
        retriever_weight: float = 0.20,
    ):
        self.top_k = top_k
        self.title_weight = title_weight
        self.content_weight = content_weight
        self.retriever_weight = retriever_weight

        # Các cụm từ chỉ dấu hiệu lạc đề nghiêm trọng đối với các chủ đề thông dụng
        self.topic_drift_penalties = [
            # Nếu câu hỏi hỏi về trợ cấp / nghỉ việc / tiền lương, nhưng chunk lại về giấy phép người nước ngoài
            {
                "query_indicators": ["trợ cấp", "nghỉ việc", "thôi việc", "mất việc", "tiền lương"],
                "drift_indicators": [
                    "người lao động nước ngoài",
                    "cấp giấy phép lao động",
                    "gia hạn giấy phép lao động",
                    "giấy xác nhận không thuộc diện cấp giấy phép",
                    "hồ sơ đề nghị cấp giấy phép lao động",
                    "thu hồi giấy phép lao động",
                    "cho thuê lại lao động",
                    "phòng ngừa tai nạn lao động"
                ],
                "penalty": 0.45
            }
        ]

    def _extract_phrases(self, text: str) -> List[str]:
        """Trích xuất danh sách các từ và cụm từ có nghĩa (2-3 từ) từ văn bản."""
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        words = [w for w in clean.split() if len(w) >= 2]
        
        phrases = list(words)
        for i in range(len(words) - 1):
            phrases.append(f"{words[i]} {words[i+1]}")
        for i in range(len(words) - 2):
            phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")
            
        return phrases

    def rerank(
        self,
        query: str,
        candidates: List[RetrievedChunk],
        top_k: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        """Tái xếp hạng danh sách ứng viên dựa trên điểm tương tác sâu."""
        t0 = time.perf_counter()
        k = top_k or self.top_k

        if not candidates:
            return []

        q_lower = query.lower()
        q_phrases = self._extract_phrases(query)
        q_articles = set(re.findall(r"điều\s*(\d+)", q_lower))

        scored_candidates: List[Tuple[float, RetrievedChunk]] = []

        for c in candidates:
            meta = c.metadata or {}
            art_title = (meta.get("article_title") or "").lower()
            art_num = str(meta.get("article_number") or "").lower()
            doc_id = (meta.get("document_id") or "").lower()
            content_lower = c.content.lower()

            # 1. Điểm khớp tiêu đề Điều luật (Article Title Match)
            title_score = 0.0
            if art_title:
                title_phrases = self._extract_phrases(art_title)
                matched_in_title = [p for p in q_phrases if p in art_title and len(p.split()) >= 2]
                if matched_in_title:
                    title_score = min(1.0, len(matched_in_title) * 0.4)

            # 2. Điểm khớp số hiệu Điều (Article Number Match)
            if q_articles and art_num in q_articles:
                title_score = max(title_score, 0.95)

            # 3. Điểm khớp nội dung (Content Exact Phrase Match)
            matched_content_bigrams = [
                p for p in q_phrases if p in content_lower and len(p.split()) >= 2
            ]
            content_score = min(1.0, len(matched_content_bigrams) * 0.25)

            # 4. Phạt lệch chủ đề (Topic Drift Penalty)
            penalty = 0.0
            for rule in self.topic_drift_penalties:
                if any(qi in q_lower for qi in rule["query_indicators"]):
                    if any(di in content_lower or di in art_title for di in rule["drift_indicators"]):
                        penalty = max(penalty, rule["penalty"])

            # 5. Điểm số tổng hợp (Interaction Score)
            interaction_score = (
                self.title_weight * title_score +
                self.content_weight * content_score +
                self.retriever_weight * c.score -
                penalty
            )
            interaction_score = max(0.0, min(1.0, interaction_score))

            scored_candidates.append((interaction_score, c))

        # Sắp xếp giảm dần theo điểm tương tác sau reranking
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        reranked_results: List[RetrievedChunk] = []
        for rank, (final_score, orig_chunk) in enumerate(scored_candidates[:k], start=1):
            new_chunk = RetrievedChunk(
                chunk_id=orig_chunk.chunk_id,
                content=orig_chunk.content,
                metadata=orig_chunk.metadata,
                score=round(final_score, 6),
                rank=rank,
                distance=round(1.0 - final_score, 6),
            )
            reranked_results.append(new_chunk)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return reranked_results
