"""evaluator.py - Bộ thẩm định chất lượng tài liệu thu hồi (Retrieval Evaluator) cho Corrective RAG.

Triển khai logic thẩm định:
- Đánh giá xem ngữ cảnh thu hồi có thực sự chứa bằng chứng để trả lời câu hỏi hay không.
- Phân biệt rạch ròi: High similarity != Sufficient evidence (loại bỏ distractor chunks).
- Xác định trạng thái: SUFFICIENT, PARTIAL, INSUFFICIENT.
- Phân loại rõ relevant_chunk_ids và irrelevant_chunk_ids.
- Kiểm tra tính hợp lệ nghiêm ngặt (confidence in [0, 1], status hợp lệ, chunk IDs tồn tại trong tập thu hồi).
"""

from __future__ import annotations
import re
import logging
from typing import List, Optional, Set, Dict, Any

from RAG.retriever.schema import RetrievedChunk
from RAG.corrective.schemas import EvaluationStatus, RetrievalEvaluation
from RAG.corrective.config import CRAGConfig, default_crag_config

logger = logging.getLogger("RAG.corrective.evaluator")

# Các từ dừng tiếng Việt trong lĩnh vực lao động không mang tính phân biệt chứng cứ
VIETNAMESE_LABOR_STOPWORDS = {
    "của", "cho", "các", "những", "được", "trong", "theo", "nào", "gì", "như",
    "thế", "khi", "quy", "định", "lao", "động", "người", "sử", "dụng", "nhiêu",
    "phải", "khoản", "điều", "về", "có", "hay", "với", "tại", "ở", "này", "đó",
    "ra", "sao", "bao", "một", "hai", "ba", "bốn", "năm", "thực", "hiện", "áp",
    "dụng", "văn", "bản", "pháp", "luật", "trường", "hợp", "vấn", "đề", "cho",
    "biết", "hỏi", "thưa", "xin", "ạ", "nhỉ", "nhé", "giúp", "tôi", "em", "mình"
}

# Các chủ đề nằm ngoài phạm vi pháp luật lao động (Out-of-scope)
OUT_OF_SCOPE_DOMAINS = [
    "nhãn hiệu", "thương hiệu", "madrid", "sáng chế", "bản quyền",
    "sở hữu trí tuệ", "visa", "hộ chiếu", "đại sứ quán", "ly hôn",
    "kết hôn giữa công dân việt nam và người nước ngoài", "thừa kế", "giao thông",
    "vượt đèn đỏ", "mô tô", "xe gắn máy", "đất đai", "nhà đất",
    "tiền ảo", "chứng khoán", "thuế giá trị gia tăng",
    "bóng đá", "thể thao", "ngoại hạng", "vé xem", "mua vé",
    "ca nhạc", "phim ảnh", "du lịch", "thời tiết", "nấu ăn", "phở bò", "nước dùng phở"
]

# Các văn bản luật không nằm trong tập dữ liệu 15 văn bản của Dataset V2.1
EXTERNAL_LEGAL_DOCUMENTS = [
    "luật công đoàn",
    "luật bảo hiểm xã hội",
    "luật an toàn, vệ sinh lao động 2015",
    "luật an toàn vệ sinh lao động",
    "luật việc làm",
    "luật năng lượng nguyên tử",
    "luật hôn nhân và gia đình",
    "thỏa ước madrid",
    "nghị định thư madrid"
]


class RetrievalEvaluator:
    """Bộ đánh giá chất lượng tài liệu thu hồi trong Corrective RAG."""

    def __init__(self, config: Optional[CRAGConfig] = None):
        self.config = config or default_crag_config

    def evaluate(
        self,
        query: str,
        retrieved_documents: List[RetrievedChunk],
    ) -> RetrievalEvaluation:
        """Đánh giá mức độ đầy đủ căn cứ của các chunk thu hồi đối với câu hỏi.
        
        Args:
            query: Câu hỏi ban đầu hoặc câu hỏi đã được viết lại.
            retrieved_documents: Danh sách các đoạn văn bản thu hồi từ Vector Store.
            
        Returns:
            RetrievalEvaluation chứa status, confidence, relevant_chunk_ids, irrelevant_chunk_ids, reason.
        """
        # 1. Kiểm tra tập tài liệu thu hồi rỗng
        if not retrieved_documents:
            evaluation = RetrievalEvaluation(
                status=EvaluationStatus.INSUFFICIENT,
                confidence=1.0,
                relevant_chunk_ids=[],
                irrelevant_chunk_ids=[],
                reason="Tập tài liệu thu hồi rỗng, không tìm thấy đoạn văn bản nào trong cơ sở dữ liệu."
            )
            self.validate_evaluation(evaluation, retrieved_documents)
            return evaluation

        # 2. Tiền xử lý câu hỏi
        clean_query = (query or "").strip()
        if not clean_query:
            all_ids = [c.chunk_id for c in retrieved_documents]
            evaluation = RetrievalEvaluation(
                status=EvaluationStatus.INSUFFICIENT,
                confidence=1.0,
                relevant_chunk_ids=[],
                irrelevant_chunk_ids=all_ids,
                reason="Câu hỏi rỗng, không thể xác định căn cứ pháp lý."
            )
            self.validate_evaluation(evaluation, retrieved_documents)
            return evaluation

        q_lower = clean_query.lower()

        # 3. Kiểm tra câu hỏi ngoài phạm vi (Out-of-scope)
        # Bất kể retriever trả về chunk gì với điểm số nào, tài liệu lao động không thể trả lời câu hỏi ngoài ngành
        for oos_kw in OUT_OF_SCOPE_DOMAINS:
            if oos_kw in q_lower:
                all_ids = [c.chunk_id for c in retrieved_documents]
                evaluation = RetrievalEvaluation(
                    status=EvaluationStatus.INSUFFICIENT,
                    confidence=0.95,
                    relevant_chunk_ids=[],
                    irrelevant_chunk_ids=all_ids,
                    reason=f"Câu hỏi thuộc chủ đề ngoài phạm vi pháp luật lao động ('{oos_kw}'). Các đoạn văn bản thu hồi đều không liên quan."
                )
                self.validate_evaluation(evaluation, retrieved_documents)
                return evaluation

        # 4. Kiểm tra câu hỏi đòi hỏi văn bản luật không có trong cơ sở dữ liệu (Missing External Laws)
        for ext_doc in EXTERNAL_LEGAL_DOCUMENTS:
            if ext_doc in q_lower:
                # Kiểm tra xem có chunk nào thực sự thuộc văn bản này hoặc chứa điều khoản trực tiếp trả lời không
                # Lưu ý: Các điều khoản viện dẫn gián tiếp (như Điều 219 BLLD sửa đổi các luật khác) chỉ là điều khoản chuyển tiếp,
                # không phải văn bản luật gốc.
                has_direct_substantive_evidence = False
                for c in retrieved_documents:
                    c_text = (c.content or "").lower()
                    doc_id = str(c.metadata.get("document_id", "")).lower()
                    # Chỉ chấp nhận nếu văn bản gốc tồn tại hoặc chunk giải quyết trực tiếp câu hỏi
                    if ext_doc in doc_id:
                        has_direct_substantive_evidence = True
                        break
                    # Nếu chunk từ BLLD hay nghị định khác chỉ nhắc tên luật trong điều khoản sửa đổi chung
                    if "phần trăm" in q_lower or "%" in q_lower:
                        if ("%" in c_text or "phần trăm" in c_text) and ext_doc in c_text:
                            has_direct_substantive_evidence = True
                            break

                if not has_direct_substantive_evidence:
                    all_ids = [c.chunk_id for c in retrieved_documents]
                    evaluation = RetrievalEvaluation(
                        status=EvaluationStatus.INSUFFICIENT,
                        confidence=0.95,
                        relevant_chunk_ids=[],
                        irrelevant_chunk_ids=all_ids,
                        reason=f"Câu hỏi yêu cầu quy định từ '{ext_doc}', văn bản này không thuộc 15 tài liệu pháp lý của hệ thống và các chunk thu hồi không chứa căn cứ trả lời."
                    )
                    self.validate_evaluation(evaluation, retrieved_documents)
                    return evaluation

        # 5. Phân tích chi tiết mức độ đáp ứng bằng chứng của từng chunk (Distractor & Relevance Analysis)
        q_words = re.findall(r"\w+", q_lower)
        significant_keywords = [
            w for w in q_words
            if len(w) >= 2 and w not in VIETNAMESE_LABOR_STOPWORDS
        ]

        # Trích xuất các cụm từ điều kiện đặc thù (nghiêm ngặt)
        special_conditions: List[str] = []
        if "tích lũy" in q_lower:
            special_conditions.append("tích lũy")
        if "sa thải" in q_lower:
            special_conditions.append("sa thải")
        if "kết hôn" in q_lower or "nghỉ việc riêng" in q_lower:
            special_conditions.append("kết hôn")
        if "thử việc" in q_lower:
            special_conditions.append("thử việc")
        if "bình thường" in q_lower and ("giờ" in q_lower or "thời giờ" in q_lower):
            special_conditions.append("bình thường")
        if "làm thêm" in q_lower or "tăng ca" in q_lower:
            special_conditions.append("làm thêm")
        if "nghỉ hưu" in q_lower or "hưu trí" in q_lower:
            special_conditions.append("nghỉ hưu")
        if "lương tối thiểu" in q_lower:
            special_conditions.append("lương tối thiểu")
        if "nặng nhọc" in q_lower or "độc hại" in q_lower:
            special_conditions.append("nặng nhọc")
        if "người nước ngoài" in q_lower or "nước ngoài" in q_lower:
            special_conditions.append("nước ngoài")
        if "chưa thành niên" in q_lower:
            special_conditions.append("chưa thành niên")

        relevant_chunk_ids: List[str] = []
        irrelevant_chunk_ids: List[str] = []
        chunk_relevance_scores: Dict[str, float] = {}

        for chunk in retrieved_documents:
            c_text = (chunk.content or "").lower()
            c_meta_str = str(chunk.metadata or {}).lower()
            combined_text = f"{c_text} {c_meta_str}"

            # Kiểm tra distractor case quan trọng:
            # Nếu câu hỏi có điều kiện cụ thể (ví dụ "tích lũy"), mà chunk hoàn toàn không nhắc tới,
            # thì dù cosine similarity cao đến đâu chunk này cũng không chứa bằng chứng trả lời!
            violates_strict_condition = False
            for cond in special_conditions:
                if cond not in combined_text:
                    # Nếu điều kiện tiên quyết bị thiếu hoàn toàn trong chunk
                    if cond in ("tích lũy",):
                        violates_strict_condition = True
                        break

            if violates_strict_condition:
                irrelevant_chunk_ids.append(chunk.chunk_id)
                chunk_relevance_scores[chunk.chunk_id] = 0.0
                continue

            # Tính độ phủ từ khóa có ý nghĩa
            matched_keywords = [kw for kw in significant_keywords if kw in combined_text]
            keyword_ratio = len(matched_keywords) / max(len(significant_keywords), 1)

            # Kiểm tra xem chunk có điểm tương đồng và độ phủ từ khóa tối thiểu không
            is_relevant = False
            if chunk.score >= self.config.SIMILARITY_THRESHOLD:
                if len(matched_keywords) >= 2 or (len(significant_keywords) == 1 and len(matched_keywords) == 1):
                    # Khớp ít nhất một số từ khóa đặc thù
                    if special_conditions:
                        if any(cond in combined_text for cond in special_conditions):
                            is_relevant = True
                    else:
                        if keyword_ratio >= 0.3 or len(matched_keywords) >= 3:
                            is_relevant = True

            if is_relevant:
                relevant_chunk_ids.append(chunk.chunk_id)
                chunk_relevance_scores[chunk.chunk_id] = round(min(1.0, 0.5 + keyword_ratio * 0.5), 4)
            else:
                irrelevant_chunk_ids.append(chunk.chunk_id)
                chunk_relevance_scores[chunk.chunk_id] = round(keyword_ratio * 0.3, 4)

        # 6. Tổng hợp trạng thái và độ tin cậy
        if not relevant_chunk_ids:
            # Trường hợp không có chunk nào chứa bằng chứng hữu ích
            status = EvaluationStatus.INSUFFICIENT
            confidence = 0.85
            reason = "Các đoạn văn bản thu hồi không chứa điều khoản hay căn cứ trực tiếp trả lời câu hỏi."
        else:
            # Đánh giá xem bằng chứng là SUFFICIENT hay chỉ PARTIAL
            # Kiểm tra xem câu hỏi có nhiều vế (multi-part / multi-condition / multi-document) không
            is_multi_aspect = any(conj in q_lower for conj in [
                "và", "đồng thời", "vừa", "kết hợp", "bao nhiêu ngày và bao nhiêu tuần",
                "bao nhiêu giờ trong một ngày và một tuần", "bao nhiêu giờ trong một ngày và trong một tháng"
            ])
            
            top_scores = [chunk_relevance_scores[cid] for cid in relevant_chunk_ids]
            avg_rel_score = sum(top_scores) / len(top_scores)

            if len(relevant_chunk_ids) >= 2 and avg_rel_score >= self.config.EVALUATOR_SUFFICIENT_THRESHOLD:
                status = EvaluationStatus.SUFFICIENT
                confidence = round(min(1.0, 0.75 + avg_rel_score * 0.25), 4)
                reason = f"Đã thu hồi được {len(relevant_chunk_ids)} đoạn văn bản chứa đầy đủ căn cứ pháp lý để trả lời dứt khoát."
            elif len(relevant_chunk_ids) == 1 and not is_multi_aspect and avg_rel_score >= 0.65:
                status = EvaluationStatus.SUFFICIENT
                confidence = round(min(1.0, 0.70 + avg_rel_score * 0.25), 4)
                reason = "Tìm thấy đoạn văn bản trực tiếp quy định đầy đủ nội dung câu hỏi đơn."
            else:
                # Còn thiếu khía cạnh hoặc tài liệu chưa bao quát trọn vẹn
                status = EvaluationStatus.PARTIAL
                confidence = round(min(0.65, 0.35 + avg_rel_score * 0.30), 4)
                reason = f"Chỉ tìm thấy bằng chứng một phần ({len(relevant_chunk_ids)}/{len(retrieved_documents)} chunk phù hợp), cần bổ sung hoặc làm rõ thêm quy định liên quan."

        evaluation = RetrievalEvaluation(
            status=status,
            confidence=confidence,
            relevant_chunk_ids=relevant_chunk_ids,
            irrelevant_chunk_ids=irrelevant_chunk_ids,
            reason=reason
        )

        # 7. Kiểm tra tính hợp lệ bắt buộc (Fail-safe validation)
        self.validate_evaluation(evaluation, retrieved_documents)
        return evaluation

    @staticmethod
    def validate_evaluation(
        evaluation: RetrievalEvaluation,
        retrieved_documents: List[RetrievedChunk]
    ) -> None:
        """Kiểm tra tính toàn vẹn của kết quả đánh giá theo yêu cầu PHASE CRAG-01.
        
        Quy tắc:
        - status phải thuộc EvaluationStatus hợp lệ.
        - confidence phải nằm trong [0.0, 1.0].
        - relevant_chunk_ids phải là tập con của retrieved_documents.
        - irrelevant_chunk_ids phải là tập con của retrieved_documents.
        - relevant_chunk_ids và irrelevant_chunk_ids phải rời nhau (disjoint).
        """
        if not isinstance(evaluation.status, EvaluationStatus):
            raise ValueError(f"Unknown status: {evaluation.status}")

        if evaluation.confidence < 0.0 or evaluation.confidence > 1.0:
            raise ValueError(f"Confidence out of bounds [0, 1]: {evaluation.confidence}")

        retrieved_ids = {c.chunk_id for c in retrieved_documents}

        unknown_rel = set(evaluation.relevant_chunk_ids) - retrieved_ids
        if unknown_rel:
            raise ValueError(f"relevant_chunk_ids chứa chunk ID không tồn tại trong retrieval: {unknown_rel}")

        unknown_irrel = set(evaluation.irrelevant_chunk_ids) - retrieved_ids
        if unknown_irrel:
            raise ValueError(f"irrelevant_chunk_ids chứa chunk ID không tồn tại trong retrieval: {unknown_irrel}")

        overlap = set(evaluation.relevant_chunk_ids) & set(evaluation.irrelevant_chunk_ids)
        if overlap:
            raise ValueError(f"relevant_chunk_ids và irrelevant_chunk_ids bị trùng lặp chunk ID: {overlap}")
