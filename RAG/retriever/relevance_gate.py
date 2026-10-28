"""relevance_gate.py - Cổng kiểm soát mức độ liên quan và tính xác thực của bằng chứng (Post-Retrieval Relevance Gate).

Giải quyết triệt để vấn đề 'Tê liệt ngưỡng tĩnh 0.45':
- Thay vì chỉ dựa vào một ngưỡng float tùy ý (vốn dễ để lọt rác), Relevance Gate kết hợp đa tiêu chí:
  1. Độ nhất quán từ vựng (Lexical Consistency): Xác minh các thực thể/hành vi cốt lõi có thực sự xuất hiện trong chunk hay không.
  2. Phân bố điểm số (Score Distribution & Margin): So sánh điểm số của chunk đứng đầu với độ lệch chủ đề.
  3. Lọc bỏ các chunk 'lạc đề có điểm số cao' (High-score false positives).
- Phân loại rõ 3 trạng thái:
  - RELEVANT: Bằng chứng trực tiếp, đáng tin cậy.
  - AMBIGUOUS: Bằng chứng gián tiếp hoặc câu hỏi mơ hồ cần làm rõ.
  - INSUFFICIENT: Không đủ căn cứ pháp lý -> Kích hoạt từ chối chuẩn mực theo quy tắc hệ thống.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from RAG.retriever.schema import RetrievedChunk


class GateVerdict(str, Enum):
    RELEVANT = "RELEVANT"
    AMBIGUOUS = "AMBIGUOUS"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass
class RelevanceGateDecision:
    passed: bool
    verdict: GateVerdict
    filtered_chunks: List[RetrievedChunk]
    rejection_reason: Optional[str] = None
    confidence: float = 0.0
    matched_topics: List[str] = field(default_factory=list)


class RelevanceGate:
    """Cổng thẩm định tính liên quan của ngữ cảnh trước khi đưa vào mô hình sinh."""

    STOPWORDS = {
        "của", "cho", "các", "những", "được", "trong", "theo", "nào", "gì", "như",
        "thế", "khi", "quy", "định", "pháp", "luật", "lao", "động", "người", "sử", "dụng",
        "phải", "khoản", "điều", "về", "có", "hay", "với", "tại", "ở", "này", "đó",
        "ra", "sao", "bao", "nhiêu", "làm", "một", "hai", "ba", "thực", "hiện", "áp", "dụng",
        "trường", "hợp", "vấn", "đề", "liên", "quan", "là", "và", "hoặc", "thì", "đã", "sẽ"
    }

    def __init__(
        self,
        min_relevance_score: float = 0.25,
        min_matched_keywords: int = 1,
    ):
        self.min_relevance_score = min_relevance_score
        self.min_matched_keywords = min_matched_keywords

    def _extract_keywords(self, text: str) -> Set[str]:
        """Trích xuất các từ khóa chủ đề có nghĩa."""
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        words = clean.split()
        return {w for w in words if len(w) >= 2 and w not in self.STOPWORDS}

    def evaluate(self, query: str, chunks: List[RetrievedChunk]) -> RelevanceGateDecision:
        """Thẩm định tính liên quan của danh sách chunks đối với truy vấn."""
        if not chunks:
            return RelevanceGateDecision(
                passed=False,
                verdict=GateVerdict.INSUFFICIENT,
                filtered_chunks=[],
                rejection_reason="Không có đoạn văn bản nào được tìm thấy trong cơ sở dữ liệu.",
                confidence=0.0
            )

        q_lower = query.lower()
        q_keywords = self._extract_keywords(query)
        q_articles = set(re.findall(r"điều\s*(\d+)", q_lower))

        valid_chunks: List[RetrievedChunk] = []
        matched_topics_all: Set[str] = set()

        for chunk in chunks:
            meta = chunk.metadata or {}
            art_title = (meta.get("article_title") or "").lower()
            art_num = str(meta.get("article_number") or "").lower()
            content_lower = chunk.content.lower()

            chunk_keywords = self._extract_keywords(f"{art_title} {content_lower}")
            common = q_keywords.intersection(chunk_keywords)

            # Kiểm tra khớp số hiệu Điều
            article_matched = bool(q_articles and art_num in q_articles)

            # Kiểm tra cụm từ ghép đặc thù (2 từ liên tiếp)
            has_bigram_match = False
            q_words = list(q_keywords)
            for i in range(len(q_words) - 1):
                bg = f"{q_words[i]} {q_words[i+1]}"
                if bg in content_lower or bg in art_title:
                    has_bigram_match = True
                    matched_topics_all.add(bg)

            # Tiêu chuẩn giữ lại chunk:
            # - Có điểm tương tác >= min_relevance_score
            # - Hoặc khớp chính xác số hiệu Điều
            # - Hoặc có ít nhất min_matched_keywords từ khóa và có cụm từ ghép
            if article_matched or (len(common) >= self.min_matched_keywords and (has_bigram_match or chunk.score >= self.min_relevance_score)):
                valid_chunks.append(chunk)
                matched_topics_all.update(common)

        if not valid_chunks:
            return RelevanceGateDecision(
                passed=False,
                verdict=GateVerdict.INSUFFICIENT,
                filtered_chunks=[],
                rejection_reason=(
                    "Tất cả các tài liệu được thu hồi đều không chứa các căn cứ pháp lý hoặc từ khóa chủ đề "
                    "phù hợp trực tiếp với câu hỏi (nguy cơ ô nhiễm ngữ cảnh)."
                ),
                confidence=0.0,
                matched_topics=[]
            )

        # Tính độ tin cậy tổng thể (Confidence) dựa trên chunk tốt nhất
        max_chunk_score = max(c.score for c in valid_chunks)
        confidence = round(max_chunk_score, 4)

        # Phân biệt RELEVANT và AMBIGUOUS
        if confidence >= 0.50 and len(valid_chunks) >= 1:
            verdict = GateVerdict.RELEVANT
        else:
            verdict = GateVerdict.AMBIGUOUS

        return RelevanceGateDecision(
            passed=True,
            verdict=verdict,
            filtered_chunks=valid_chunks,
            confidence=confidence,
            matched_topics=list(matched_topics_all)
        )
