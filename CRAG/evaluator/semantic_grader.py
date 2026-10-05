"""semantic_grader.py - Bộ đánh giá tài liệu dựa trên ngữ nghĩa và thực thể pháp lý (Calibrated Semantic Grader)."""

from __future__ import annotations
import re
import time
from typing import List, Optional, Set, Tuple

from CRAG.evaluator.base import BaseDocumentGrader
from CRAG.evaluator.schema import (
    ActionTrigger,
    DocumentGrade,
    GradeVerdict,
    RetrievalGradingResult,
)
from RAG.retriever.schema import RetrievedChunk
from CRAG.config import CRAGConfig, default_crag_config


class SemanticDocumentGrader(BaseDocumentGrader):
    """Bộ đánh giá tài liệu thu hồi kết hợp Dense Similarity Score và Topical Legal Entity Calibration.
    
    Giải quyết triệt để vấn đề 'ảo giác điểm số cao' (High-score irrelevant results) của Dense Retriever:
    - Nhận diện các thực thể/cụm từ pháp lý cốt lõi trong câu hỏi.
    - So sánh với tiêu đề Điều luật và nội dung quy định thực tế trong chunk.
    - Hiệu chỉnh điểm số tương đồng (Calibration) về khoảng đo chuẩn [0.0, 1.0].
    - Phân loại rõ ràng 3 trạng thái: CORRECT, INCORRECT, AMBIGUOUS.
    """

    def __init__(self, config: Optional[CRAGConfig] = None):
        super().__init__(config=config)

        # Danh mục từ khóa nhận diện câu hỏi ngoài phạm vi luật lao động (Out-of-scope)
        self.out_of_scope_keywords = {
            "hàng không", "tàu bay", "phi công", "lái máy bay", "hộ chiếu", "visa",
            "schengen", "đại sứ quán", "giao thông", "nồng độ cồn", "bằng lái",
            "đấu thầu", "dự thầu", "gói thầu", "kết hôn", "ly hôn", "hôn nhân",
            "nuôi con nuôi", "thừa kế", "di chúc", "đất đai", "sổ đỏ", "nhà đất",
            "chứng khoán", "cổ phiếu", "tiền ảo", "thuế giá trị gia tăng",
            "bóng đá", "thời tiết", "nấu ăn", "công thức", "phở bò", "du lịch",
            "căn cước", "công dân", "cccd", "chứng minh nhân dân"
        }

        # Stopwords tiếng Việt và từ chung không mang tính phân biệt chủ đề pháp lý
        self.legal_stopwords = {
            "của", "cho", "các", "những", "được", "trong", "theo", "nào", "gì", "như",
            "thế", "khi", "quy", "định", "pháp", "luật", "lao", "động", "người", "sử", "dụng",
            "phải", "khoản", "điều", "về", "có", "hay", "với", "tại", "ở", "này", "đó",
            "ra", "sao", "bao", "nhiêu", "làm", "một", "hai", "ba", "thực", "hiện", "áp", "dụng",
            "trường", "hợp", "vấn", "đề", "liên", "quan", "là", "đối", "và", "hoặc", "tối", "đa",
            "thời", "gian", "ngày", "tháng", "năm", "mức", "số", "lại", "thì", "đã", "sẽ"
        }

    def _extract_topical_phrases(self, text: str) -> Tuple[List[str], List[str]]:
        """Trích xuất từ khóa đơn ý nghĩa và cụm từ ghép 2 từ (Bigrams) mang tính phân biệt chủ đề."""
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        words = clean.split()

        # Từ đơn có nghĩa (loại bỏ stopwords và từ quá ngắn)
        singles = [w for w in words if len(w) >= 3 and w not in self.legal_stopwords]

        # Cụm từ ghép 2 từ có nghĩa (cả 2 từ đều không nằm trong stopwords)
        bigrams = []
        for i in range(len(words) - 1):
            w1, w2 = words[i], words[i + 1]
            if w1 not in self.legal_stopwords and w2 not in self.legal_stopwords:
                bigrams.append(f"{w1} {w2}")

        return list(set(singles)), list(set(bigrams))

    def _extract_specific_articles(self, text: str) -> Set[str]:
        """Trích xuất các số hiệu Điều luật cụ thể được nhắc tới (VD: 'điều 125' -> '125')."""
        matches = re.findall(r"điều\s*(\d+)", text.lower())
        return set(matches)

    def grade_document(self, query: str, chunk: RetrievedChunk) -> DocumentGrade:
        """Đánh giá mức độ phù hợp thực sự của một chunk đối với câu hỏi."""
        q_lower = query.lower()
        chunk_content_lower = chunk.content.lower()
        art_title_lower = (chunk.metadata.get("article_title") or "").lower()
        art_num = (chunk.metadata.get("article_number") or "").lower()
        doc_id = chunk.metadata.get("document_id") or ""

        # 1. Nhận diện câu hỏi ngoài phạm vi
        is_query_out_of_scope = any(kw in q_lower for kw in self.out_of_scope_keywords)

        # 2. Trích xuất từ khóa chủ đề và số hiệu Điều
        singles, bigrams = self._extract_topical_phrases(query)
        q_articles = self._extract_specific_articles(query)

        # 3. Tính toán độ khớp thực thể
        # Khớp số hiệu Điều luật
        article_match_score = 0.0
        if q_articles:
            chunk_art_numbers = self._extract_specific_articles(f"{art_num} {art_title_lower} {chunk_content_lower}")
            if q_articles & chunk_art_numbers:
                article_match_score = 1.0

        # Khớp cụm từ chủ đề (ưu tiên cao nhất)
        matched_bigrams_title = [bg for bg in bigrams if bg in art_title_lower]
        matched_bigrams_content = [bg for bg in bigrams if bg in chunk_content_lower]
        bigram_content_ratio = len(matched_bigrams_content) / len(bigrams) if bigrams else 0.0
        bigram_title_ratio = len(matched_bigrams_title) / len(bigrams) if bigrams else 0.0

        # Khớp từ đơn chủ đề
        matched_singles_content = [s for s in singles if s in chunk_content_lower]
        single_content_ratio = len(matched_singles_content) / len(singles) if singles else 0.0

        raw_dense_score = max(0.0, min(1.0, chunk.score))

        # 4. Hiệu chỉnh điểm số tương đồng (Calibration Formula)
        all_key_matches = list(set(matched_bigrams_title + matched_bigrams_content + matched_singles_content))

        if is_query_out_of_scope:
            calibrated_score = round(raw_dense_score * 0.35, 4)
            verdict = GradeVerdict.INCORRECT
            reasoning = "Câu hỏi thuộc lĩnh vực ngoài phạm vi pháp luật lao động; tài liệu không phù hợp."
            all_key_matches = []

        elif article_match_score == 1.0:
            calibrated_score = round(max(raw_dense_score, 0.85), 4)
            verdict = GradeVerdict.CORRECT
            reasoning = f"Tài liệu khớp chính xác số hiệu Điều luật được truy vấn: {art_num}."
            all_key_matches.append(art_num)

        elif bigram_title_ratio >= 0.50 or (bigram_content_ratio >= 0.50 and single_content_ratio >= 0.60):
            # Khớp chủ đề cốt lõi cao cả ở cụm từ tiêu đề và nội dung
            boosted = 0.35 * raw_dense_score + 0.40 * bigram_content_ratio + 0.25 * bigram_title_ratio
            calibrated_score = round(min(1.0, max(0.70, boosted)), 4)
            verdict = GradeVerdict.CORRECT
            reasoning = f"Nội dung và tiêu đề Điều '{art_num}' chứa trực tiếp các căn cứ pháp lý giải đáp câu hỏi."

        elif bigram_content_ratio >= 0.25 or (not bigrams and single_content_ratio >= 0.50):
            # Khớp một phần cụm từ chủ đề
            calibrated_score = round(0.50 * raw_dense_score + 0.50 * bigram_content_ratio, 4)
            if calibrated_score >= self.config.UPPER_THRESHOLD:
                verdict = GradeVerdict.CORRECT
                reasoning = "Tài liệu chứa căn cứ giải quyết câu hỏi."
            elif calibrated_score >= self.config.LOWER_THRESHOLD:
                verdict = GradeVerdict.AMBIGUOUS
                reasoning = "Tài liệu liên quan gián tiếp hoặc chỉ giải quyết một phần câu hỏi."
            else:
                verdict = GradeVerdict.INCORRECT
                reasoning = "Điểm số sau hiệu chỉnh không đạt ngưỡng tối thiểu."

        elif len(all_key_matches) == 0:
            # Hoàn toàn không khớp bất kỳ cụm từ hay từ khóa chủ đề nào
            calibrated_score = round(raw_dense_score * 0.40, 4)
            verdict = GradeVerdict.INCORRECT
            reasoning = "Tài liệu không chứa các từ khóa chủ đề cốt lõi của câu hỏi (lạc đề hoàn toàn)."

        else:
            # Chỉ khớp một vài từ đơn lẻ mờ nhạt
            calibrated_score = round(0.40 * raw_dense_score + 0.60 * (single_content_ratio * 0.5), 4)
            if calibrated_score >= self.config.LOWER_THRESHOLD:
                verdict = GradeVerdict.AMBIGUOUS
                reasoning = "Tài liệu chứa từ khóa chung nhưng ngữ cảnh giải quyết chưa rõ ràng."
            else:
                verdict = GradeVerdict.INCORRECT
                reasoning = "Tài liệu có mật độ từ khóa quá thấp, không giải đáp được câu hỏi."

        return DocumentGrade(
            chunk_id=chunk.chunk_id,
            document_id=doc_id,
            article_number=chunk.metadata.get("article_number"),
            relevance_score=calibrated_score,
            verdict=verdict,
            reasoning=reasoning,
            key_matches=all_key_matches,
        )

    def grade_documents(self, query: str, chunks: List[RetrievedChunk]) -> RetrievalGradingResult:
        """Đánh giá toàn bộ danh sách Top-K chunks và đưa ra quyết định hành động tổng thể."""
        t0 = time.perf_counter()

        if not chunks:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return RetrievalGradingResult(
                query=query,
                individual_grades=[],
                overall_confidence=0.0,
                overall_verdict=GradeVerdict.INCORRECT,
                recommended_action=ActionTrigger.REFUSE,
                correct_count=0,
                ambiguous_count=0,
                incorrect_count=0,
                latency_ms=round(elapsed_ms, 2),
                metadata={"reason": "Danh sách chunks đầu vào rỗng"},
            )

        # Chấm điểm từng chunk
        grades = [self.grade_document(query, c) for c in chunks]

        correct_grades = [g for g in grades if g.verdict == GradeVerdict.CORRECT]
        ambiguous_grades = [g for g in grades if g.verdict == GradeVerdict.AMBIGUOUS]
        incorrect_grades = [g for g in grades if g.verdict == GradeVerdict.INCORRECT]

        correct_count = len(correct_grades)
        ambiguous_count = len(ambiguous_grades)
        incorrect_count = len(incorrect_grades)

        # Tính toán độ tin cậy tổng thể (Overall Confidence)
        sorted_scores = sorted([g.relevance_score for g in grades], reverse=True)
        max_score = sorted_scores[0]
        overall_confidence = max_score

        # Kiểm tra dấu hiệu câu hỏi ngoài phạm vi
        q_lower = query.lower()
        is_query_out_of_scope = any(kw in q_lower for kw in self.out_of_scope_keywords)

        # Quyết định hành động tổng thể (Recommended Action Trigger)
        if is_query_out_of_scope:
            overall_verdict = GradeVerdict.INCORRECT
            recommended_action = ActionTrigger.REFUSE
        elif correct_count >= 1 or overall_confidence >= self.config.UPPER_THRESHOLD:
            overall_verdict = GradeVerdict.CORRECT
            recommended_action = ActionTrigger.REFINE
        elif ambiguous_count >= 1 or overall_confidence >= self.config.LOWER_THRESHOLD:
            overall_verdict = GradeVerdict.AMBIGUOUS
            recommended_action = ActionTrigger.COMBINE_SEARCH
        else:
            overall_verdict = GradeVerdict.INCORRECT
            recommended_action = ActionTrigger.WEB_SEARCH

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return RetrievalGradingResult(
            query=query,
            individual_grades=grades,
            overall_confidence=overall_confidence,
            overall_verdict=overall_verdict,
            recommended_action=recommended_action,
            correct_count=correct_count,
            ambiguous_count=ambiguous_count,
            incorrect_count=incorrect_count,
            latency_ms=round(elapsed_ms, 2),
            metadata={
                "upper_threshold": self.config.UPPER_THRESHOLD,
                "lower_threshold": self.config.LOWER_THRESHOLD,
                "is_out_of_scope_detected": is_query_out_of_scope,
            },
        )
