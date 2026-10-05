"""
Adaptive RAG Hybrid Query Classifier.
Phân loại ý định và độ phức tạp của câu hỏi bằng kỹ thuật lai (Hybrid Rule & Semantic Pattern Matching).
"""

from __future__ import annotations
import re
import time
from typing import List, Optional, Tuple

from Adaptive_RAG.config import AdaptiveRAGConfig, adaptive_config
from Adaptive_RAG.classifier.base import BaseQueryClassifier
from Adaptive_RAG.classifier.schema import (
    ClassificationResult,
    ComplexityLevel,
    QueryIntent,
    RoutingDecision,
)


class HybridQueryClassifier(BaseQueryClassifier):
    """
    Bộ phân loại câu hỏi kết hợp nhận diện thực thể pháp lý, cấu trúc cú pháp đa điều kiện
    và mẫu câu chuyên biệt cho pháp luật lao động Việt Nam.
    """

    GREETING_PATTERNS = [
        r"^(xin\s+)?chào(\s+(bạn|ad|hệ\s+thống|mọi\s+người|ai\s+đó))?",
        r"^(hello|hi|hey)\b",
        r"\b(bạn\s+là\s+ai|giới\s+thiệu\s+về\s+bạn)\b",
        r"\b(cảm\s+ơn|thank\s+you|thanks)\b",
        r"^(tạm\s+biệt|bye)\b",
    ]

    OUT_OF_SCOPE_KEYWORDS = {
        "hàng không", "tàu bay", "phi công", "lái máy bay", "hộ chiếu", "visa",
        "schengen", "đại sứ quán", "giao thông", "nồng độ cồn", "bằng lái",
        "đấu thầu", "dự thầu", "gói thầu", "kết hôn", "ly hôn", "hôn nhân",
        "nuôi con nuôi", "thừa kế", "di chúc", "đất đai", "sổ đỏ", "nhà đất",
        "chứng khoán", "cổ phiếu", "tiền ảo", "thuế giá trị gia tăng", "thuế vat",
        "bóng đá", "thời tiết", "nấu ăn", "công thức", "phở bò", "du lịch",
        "căn cước", "cccd", "chứng minh nhân dân", "hộ tịch"
    }

    CONDITIONAL_CONNECTORS = [
        r"\bvừa\b.+\bvừa\b",
        r"\bnếu\b.+\bthì\b.+\bnhưng\b",
        r"\bđồng\s+thời\b",
        r"\btrong\s+trường\s+hợp\b.+\bvà\b",
        r"\bkhông\s+những\b.+\bmà\s+còn\b",
        r"\btrước\s+khi\b.+\bthì\s+có\s+được\b",
        r"\bbao\s+nhiêu\b.+\bvà\b.+\bnhư\s+thế\s+nào\b",
        r"\bcó\s+được\b.+\bvà\s+(phải|bị)\b",
    ]

    PROCEDURAL_PATTERNS = [
        r"\btrình\s+tự\b",
        r"\bthủ\s+tục\b",
        r"\bcác\s+bước\b",
        r"\bhồ\s+sơ\s+gồm\s+những\s+gì\b",
        r"\bthời\s+hạn\s+giải\s+quyết\b",
        r"\bquy\s+trình\b",
    ]

    def _extract_legal_entities(self, query: str) -> Tuple[List[str], List[str]]:
        """Bóc tách số Điều luật và các văn bản quy phạm được viện dẫn."""
        articles = re.findall(r"điều\s+\d+", query, re.IGNORECASE)
        articles = [a.title() for a in articles]

        documents = []
        doc_matches = re.findall(
            r"(nghị\s+định\s+\d+/\d+(?:/nđ-cp)?|thông\s+tư\s+\d+/\d+(?:/tt-blđtbxh)?|bộ\s+luật\s+lao\s+động(?:\s+\d+)?)",
            query,
            re.IGNORECASE,
        )
        for d in doc_matches:
            documents.append(d.strip())

        return articles, documents

    def classify(self, query: str) -> ClassificationResult:
        t_start = time.perf_counter()
        q_clean = query.strip()
        q_lower = q_clean.lower()

        # 1. Kiểm tra Greeting / Chit-chat
        for pattern in self.GREETING_PATTERNS:
            if re.search(pattern, q_lower):
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                return ClassificationResult(
                    query=q_clean,
                    intent=QueryIntent.GREETING_CHITCHAT,
                    complexity=ComplexityLevel.DIRECT,
                    suggested_route=RoutingDecision.DIRECT_ANSWER,
                    confidence=0.98,
                    reasoning="Câu hỏi mang tính xã giao/chào hỏi/cảm ơn thông thường, không yêu cầu tra cứu pháp luật.",
                    latency_ms=round(elapsed_ms, 2),
                )

        # 2. Kiểm tra Out-of-Scope (Ngoại phạm vi)
        for kw in self.OUT_OF_SCOPE_KEYWORDS:
            if kw in q_lower:
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                return ClassificationResult(
                    query=q_clean,
                    intent=QueryIntent.OUT_OF_SCOPE,
                    complexity=ComplexityLevel.DIRECT,
                    suggested_route=RoutingDecision.DIRECT_REFUSAL,
                    confidence=0.95,
                    reasoning=f"Phát hiện từ khóa ngoài phạm vi pháp luật lao động: '{kw}'. Từ chối an toàn ngay tại cửa ngõ.",
                    latency_ms=round(elapsed_ms, 2),
                )

        # 3. Bóc tách thực thể pháp lý
        articles, documents = self._extract_legal_entities(q_clean)

        # 4. Kiểm tra Multi-Document
        if len(documents) >= 2 or (len(documents) == 1 and len(articles) >= 2) or (
            "so sánh" in q_lower or "khác nhau" in q_lower or "sửa đổi" in q_lower
        ):
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return ClassificationResult(
                query=q_clean,
                intent=QueryIntent.LEGAL_MULTI_DOCUMENT,
                complexity=ComplexityLevel.COMPLEX_MULTI_HOP,
                suggested_route=RoutingDecision.DECOMPOSE_AGENTIC,
                confidence=0.90,
                reasoning="Câu hỏi liên quan đến nhiều văn bản quy phạm hoặc yêu cầu so sánh/dẫn chiếu chéo giữa Luật và Nghị định.",
                detected_articles=articles,
                detected_documents=documents,
                latency_ms=round(elapsed_ms, 2),
            )

        # 5. Kiểm tra Multi-Condition / Complex Conditions
        detected_conditions = []
        for cond_pat in self.CONDITIONAL_CONNECTORS:
            if re.search(cond_pat, q_lower):
                detected_conditions.append(cond_pat)

        # Đếm số lượng câu hỏi con (dấu ? hoặc liên từ nối đa mục tiêu)
        num_question_marks = q_clean.count("?")
        has_compound_questions = (
            ("và" in q_lower and ("bao nhiêu" in q_lower or "thế nào" in q_lower))
            or ("đồng thời" in q_lower)
            or ("trong khi" in q_lower)
        )

        if detected_conditions or num_question_marks >= 2 or has_compound_questions:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return ClassificationResult(
                query=q_clean,
                intent=QueryIntent.LEGAL_CONDITIONAL,
                complexity=ComplexityLevel.COMPLEX_MULTI_HOP,
                suggested_route=RoutingDecision.DECOMPOSE_AGENTIC,
                confidence=0.88,
                reasoning="Câu hỏi chứa nhiều vế điều kiện phức hợp hoặc hỏi nhiều mục tiêu cùng lúc, cần phân rã thành sub-queries.",
                detected_articles=articles,
                detected_documents=documents,
                detected_conditions=detected_conditions,
                latency_ms=round(elapsed_ms, 2),
            )

        # 6. Kiểm tra Procedural (Quy trình, thủ tục các bước)
        is_procedural = any(re.search(p, q_lower) for p in self.PROCEDURAL_PATTERNS)
        if is_procedural:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return ClassificationResult(
                query=q_clean,
                intent=QueryIntent.LEGAL_PROCEDURAL,
                complexity=ComplexityLevel.MODERATE_CORRECTIVE,
                suggested_route=RoutingDecision.CORRECTIVE_RAG,
                confidence=0.85,
                reasoning="Câu hỏi về trình tự, thủ tục các bước, cần cơ chế Corrective RAG để lọc bỏ các khoản không liên quan.",
                detected_articles=articles,
                detected_documents=documents,
                latency_ms=round(elapsed_ms, 2),
            )

        # 7. Câu hỏi đơn giản trực tiếp (Single-Hop)
        # Nếu câu hỏi ngắn gọn (< 15 từ) hoặc hỏi trực tiếp 1 Điều luật
        words = q_clean.split()
        if len(words) <= 18 and (len(articles) <= 1):
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return ClassificationResult(
                query=q_clean,
                intent=QueryIntent.LEGAL_DIRECT_DEFINITION,
                complexity=ComplexityLevel.SIMPLE_SINGLE_HOP,
                suggested_route=RoutingDecision.TRADITIONAL_RAG,
                confidence=0.90,
                reasoning="Câu hỏi tra cứu điều luật trực tiếp hoặc định nghĩa ngắn gọn, Traditional RAG xử lý nhanh và tối ưu nhất.",
                detected_articles=articles,
                detected_documents=documents,
                latency_ms=round(elapsed_ms, 2),
            )

        # 8. Mặc định: Phân về Corrective RAG để bảo đảm an toàn dữ liệu
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        return ClassificationResult(
            query=q_clean,
            intent=QueryIntent.LEGAL_DIRECT_DEFINITION,
            complexity=ComplexityLevel.MODERATE_CORRECTIVE,
            suggested_route=RoutingDecision.CORRECTIVE_RAG,
            confidence=0.75,
            reasoning="Câu hỏi pháp lý thông thường, sử dụng Corrective RAG để kiểm định mức độ phù hợp và lọc nhiễu.",
            detected_articles=articles,
            detected_documents=documents,
            latency_ms=round(elapsed_ms, 2),
        )
