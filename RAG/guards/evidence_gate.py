"""evidence_gate.py - Tier 3: Pre-Generation Evidence Gate.

Đặc tả và triển khai chốt chặn kiểm định bằng chứng trước khi sinh (Tier 3):
- Khung đánh giá 5 chiều: 4 chiều điểm nội dung + 1 Cổng điều kiện tiên quyết về hiệu lực pháp lý (G_temporal).
- Công thức tính điểm trên từng chunk (S_chunk) và Điểm tổng hợp tập bằng chứng (S_composite).
- Biên thưởng bao phủ (CoverageBonus) có chặn trên [0.0, 1.0] và chống thưởng trùng.
- Quy tắc phủ quyết an toàn 3 cấp (Safe Veto Rule) chống ontology misclassification.
- Trả về đối tượng báo cáo kiểm toán chi tiết EvidenceGradingReport.
"""

from __future__ import annotations
import json
import logging
import math
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set
from pydantic import BaseModel, Field

from RAG.retriever.schema import RetrievedChunk

logger = logging.getLogger("RAG.guards.evidence_gate")


class ChunkGrade(BaseModel):
    """Điểm đánh giá chi tiết cho từng đoạn trích ứng viên."""

    chunk_id: str
    document_id: str
    article_number: Optional[str] = None
    scores: Dict[str, float] = Field(default_factory=dict)
    chunk_score: float = Field(..., description="Điểm tổng hợp của chunk: G_temporal * S_content")
    verdict: str = Field(..., description="SUPPORTED, PARTIAL, hoặc UNSUPPORTED")
    reason: Optional[str] = None


class EvidenceGradingReport(BaseModel):
    """Báo cáo kiểm toán bằng chứng đầy đủ của Tier 3 Pre-Generation Evidence Gate."""

    query: str
    total_chunks_evaluated: int
    chunk_grades: List[ChunkGrade] = Field(default_factory=list)
    best_chunk_score: float = 0.0
    coverage_bonus: float = 0.0
    composite_evidence_score: float = 0.0
    threshold_applied: float = 0.52
    overall_verdict: str = "UNSUPPORTED"
    trigger_refusal: bool = False
    refusal_reason: Optional[str] = None
    refusal_message: Optional[str] = None
    conflict_resolution_trace: Optional[str] = None
    latency_ms: float = 0.0


class PreGenerationEvidenceGate:
    """Chốt chặn kiểm định bằng chứng 5 chiều trước khi gọi LLM sinh văn bản (Tier 3)."""

    # Bản đồ các chủ đề / chế định pháp luật lao động cốt lõi
    LEGAL_REGIMES: Dict[str, List[str]] = {
        "wage_remuneration": [
            r"\b(tiền\s+lương|lương|trả\s+lương|bảng\s+lương|khấu\s+trừ\s+lương|nợ\s+lương|chậm\s+lương|tạm\s+ứng\s+lương)\b",
            r"\b(lương\s+tối\s+thiểu|lương\s+cơ\s+bản|phụ\s+cấp|thưởng|thưởng\s+tết|lương\s+tháng\s+13)\b",
            r"\b(ngừng\s+việc|lương\s+ngừng\s+việc|làm\s+đêm|lương\s+làm\s+đêm|làm\s+thêm\s+giờ|tăng\s+ca|lương\s+thêm\s+giờ)\b",
        ],
        "discipline_termination": [
            r"\b(kỷ\s+luật|kỷ\s+luật\s+lao\s+động|sa\s+thải|khiển\s+trách|cách\s+chức|kéo\s+dài\s+thời\s+hạn\s+nâng\s+lương)\b",
            r"\b(đơn\s+phương\s+chấm\s+dứt|chấm\s+dứt\s+hợp\s+đồng|đuổi\s+việc|đuổi\s+ngang|bồi\s+thường\s+do\s+chấm\s+dứt)\b",
            r"\b(trách\s+nhiệm\s+vật\s+chất|bồi\s+thường\s+thiệt\s+hại|làm\s+hư\s+hỏng|tạm\s+đình\s+chỉ\s+công\s+việc)\b",
            r"\b(xử\s+phạt\s+vi\s+phạm|vi\s+phạm\s+hành\s+chính|nghị\s+định\s+12/2022)\b",
        ],
        "working_rest_time": [
            r"\b(thời\s+giờ\s+làm\s+việc|giờ\s+làm\s+việc|thời\s+giờ\s+nghỉ\s+ngơi|nghỉ\s+giữa\s+giờ|nghỉ\s+chuyển\s+ca)\b",
            r"\b(nghỉ\s+phép|nghỉ\s+hằng\s+năm|phép\s+năm|nghỉ\s+hàng\s+năm|nghỉ\s+lễ|nghỉ\s+tết|nghỉ\s+việc\s+riêng)\b",
            r"\b(nghỉ\s+không\s+hưởng\s+lương|nghỉ\s+không\s+lương|làm\s+việc\s+ban\s+đêm|ca\s+đêm)\b",
        ],
        "contract_probation": [
            r"\b(hợp\s+đồng\s+lao\s+động|hđlđ|giao\s+kết\s+hợp\s+đồng|loại\s+hợp\s+đồng|hợp\s+đồng\s+xác\s+định\s+thời\s+hạn)\b",
            r"\b(hợp\s+đồng\s+không\s+xác\s+định\s+thời\s+hạn|thử\s+việc|hợp\s+đồng\s+thử\s+việc|thời\s+gian\s+thử\s+việc)\b",
            r"\b(kết\s+thúc\s+thử\s+việc|tạm\s+hoãn\s+hợp\s+đồng|phụ\s+lục\s+hợp\s+đồng|chuyển\s+làm\s+công\s+việc\s+khác)\b",
        ],
        "social_insurance_benefits": [
            r"\b(bảo\s+hiểm\s+xã\s+hội|bhxh|bảo\s+hiểm\s+thất\s+nghiệp|bhtn|bảo\s+hiểm\s+y\s+tế|bhyt)\b",
            r"\b(thai\s+sản|chế\s+độ\s+thai\s+sản|ốm\s+đau|chế\s+độ\s+ốm\s+đau|dưỡng\s+sức|phục\s+hồi\s+sức\s+khỏe)\b",
            r"\b(hưu\s+trí|nghỉ\s+hưu|lương\s+hưu|tuổi\s+nghỉ\s+hưu|trợ\s+cấp\s+thôi\s+việc|trợ\s+cấp\s+mất\s+việc)\b",
            r"\b(sổ\s+bảo\s+hiểm|chốt\s+sổ|đóng\s+bảo\s+hiểm|trốn\s+đóng\s+bảo\s+hiểm)\b",
        ],
        "occupational_safety": [
            r"\b(an\s+toàn\s+lao\s+động|vệ\s+sinh\s+lao\s+động|atvsld|tai\s+nạn\s+lao\s+động|tnlđ|bệnh\s+nghề\s+nghiệp)\b",
            r"\b(khám\s+sức\s+khỏe|trang\s+bị\s+bảo\s+hộ|phương\s+tiện\s+bảo\s+vệ\s+cá\s+nhân|bồi\s+thường\s+tai\s+nạn)\b",
            r"\b(nghề\s+nặng\s+nhọc|công\s+việc\s+độc\s+hại|nguy\s+hiểm)\b",
        ],
        "foreign_labor": [
            r"\b(lao\s+động\s+nước\s+ngoài|người\s+nước\s+ngoài|giấy\s+phép\s+lao\s+động|work\s+permit|miễn\s+giấy\s+phép)\b",
        ],
        "trade_union_collective_bargaining": [
            r"\b(công\s+đoàn|kinh\s+phí\s+công\s+đoàn|đoàn\s+phí|ban\s+chấp\s+hành\s+công\s+đoàn|tổ\s+chức\s+đại\s+diện)\b",
            r"\b(thỏa\s+ước\s+lao\s+động\s+tập\s+thể|thương\s+lượng\s+tập\s+thể|thỏa\s+ước\s+tập\s+thể)\b",
        ],
        "dispute_strike": [
            r"\b(tranh\s+chấp\s+lao\s+động|hòa\s+giải\s+viên|hội\s+đồng\s+trọng\s+tài|đình\s+công|khiếu\s+nại|tố\s+cáo|khởi\s+kiện)\b",
        ],
        "recruitment_training": [
            r"\b(tuyển\s+dụng|đào\s+tạo\s+nghề|chi\s+phí\s+đào\s+tạo|học\s+nghề|tập\s+nghề|hợp\s+đồng\s+đào\s+tạo)\b",
        ],
    }

    # Các chủ thể trong quan hệ lao động
    LEGAL_SUBJECTS = {
        "female_worker": [r"\b(lao\s+động\s+nữ|phụ\s+nữ|mang\s+thai|sinh\s+con|nuôi\s+con\s+nhỏ|con\s+dưới\s+12\s+tháng)\b"],
        "minor_worker": [r"\b(chưa\s+thành\s+niên|dưới\s+15\s+tuổi|dưới\s+18\s+tuổi|học\s+nghề|tập\s+nghề)\b"],
        "disabled_worker": [r"\b(người\s+khuyết\s+tật|suy\s+giảm\s+khả\s+năng\s+lao\s+động)\b"],
        "elderly_worker": [r"\b(người\s+lao\s+động\s+cao\s+tuổi|hưu\s+trí)\b"],
        "foreign_worker": [r"\b(người\s+nước\s+ngoài|lao\s+động\s+nước\s+ngoài|chuyên\s+gia\s+nước\s+ngoài)\b"],
        "general_labor": [r"\b(người\s+lao\s+động|người\s+sử\s+dụng\s+lao\s+động|nsdlđ|nld|công\s+nhân|nhân\s+viên|sếp|công\s+ty|doanh\s+nghiệp)\b"],
    }

    def __init__(
        self,
        weights: Optional[Tuple[float, float, float, float]] = None,
        threshold_unsupported: float = 0.50,
        coverage_alpha: float = 0.15,
        high_sem_override: float = 0.78,
        registry_path: Optional[str] = None,
    ):
        """Khởi tạo Tier 3 Evidence Gate với siêu tham số cấu hình."""
        # Trọng số 4 chiều nội dung (w1: sem, w2: subj, w3: issue, w4: cond)
        self.weights = weights or (0.25, 0.25, 0.30, 0.20)
        self.threshold_unsupported = threshold_unsupported
        self.coverage_alpha = coverage_alpha
        self.high_sem_override = high_sem_override

        # Nạp legal validity registry để lấy G_temporal
        if registry_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            registry_path = str(base_dir / "data" / "legal_validity_registry.json")
        self.registry_path = registry_path
        self._doc_status_cache: Dict[str, str] = {}
        self._load_registry_status()

    def _load_registry_status(self) -> None:
        """Tải trạng thái hiệu lực văn bản từ registry."""
        p = Path(self.registry_path)
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                supp = data.get("supported_documents", {})
                for doc_id, doc_info in supp.items():
                    self._doc_status_cache[doc_id] = doc_info.get("legal_status", "ACTIVE")
            except Exception as e:
                logger.warning("Could not read registry status: %s", e)

    def _get_temporal_gate(self, document_id: str) -> float:
        """Tính cổng nhân tử G_temporal(c) cho từng document_id."""
        status = self._doc_status_cache.get(document_id, "ACTIVE")
        if status in ("ACTIVE", "ACTIVE_AMENDED"):
            return 1.0
        elif status == "TRANSITIONAL":
            return 1.0  # Vẫn có hiệu lực trong giai đoạn chuyển tiếp
        elif status == "FUTURE_ACTIVE":
            return 0.8  # Đã ban hành, sắp có hiệu lực (ví dụ Luật BHXH 2024)
        elif status in ("REPEALED", "EXPIRED"):
            return 0.0  # Hết hiệu lực hoàn toàn
        return 1.0  # Mặc định

    def _identify_query_issues(self, query: str) -> Set[str]:
        """Xác định tập hợp các chế định pháp luật mà câu hỏi đề cập."""
        q_lower = query.lower()
        matched_issues: Set[str] = set()
        for regime, patterns in self.LEGAL_REGIMES.items():
            for pat in patterns:
                if re.search(pat, q_lower):
                    matched_issues.add(regime)
                    break
        return matched_issues

    def _identify_query_subjects(self, query: str) -> Set[str]:
        """Xác định các chủ thể được hỏi trong câu hỏi."""
        q_lower = query.lower()
        matched_subjects: Set[str] = set()
        for subj, patterns in self.LEGAL_SUBJECTS.items():
            for pat in patterns:
                if re.search(pat, q_lower):
                    matched_subjects.add(subj)
                    break
        if not matched_subjects:
            matched_subjects.add("general_labor")
        return matched_subjects

    def _score_chunk(
        self,
        chunk: RetrievedChunk,
        query: str,
        q_issues: Set[str],
        q_subjects: Set[str],
    ) -> ChunkGrade:
        """Chấm điểm độc lập cho một đoạn trích ứng viên."""
        content = (chunk.content or "").lower()
        doc_id = (chunk.metadata.get("document_id") if chunk.metadata else "") or ""
        article_num = (chunk.metadata.get("article_number") if chunk.metadata else "") or ""

        # 1. Chiều 1: Semantic relevance (chuẩn hóa về [0.0, 1.0])
        raw_score = chunk.score if chunk.score is not None else 0.5
        # Nếu score là cosine similarity ~ 0.5-0.9, chuẩn hóa min-max an toàn
        s_sem = max(0.0, min(1.0, float(raw_score)))

        # 2. Chiều 2: Legal subject match {0.0, 1.0}
        s_subj = 0.0
        if "general_labor" in q_subjects:
            s_subj = 1.0
        else:
            for subj in q_subjects:
                patterns = self.LEGAL_SUBJECTS.get(subj, [])
                for pat in patterns:
                    if re.search(pat, content):
                        s_subj = 1.0
                        break
                if s_subj == 1.0:
                    break

        # 3. Chiều 3: Legal issue match {0.0, 1.0}
        s_issue = 0.0
        if not q_issues:
            s_issue = 1.0  # Không nhận diện được issue hẹp -> Không phạt
        else:
            for issue in q_issues:
                patterns = self.LEGAL_REGIMES.get(issue, [])
                for pat in patterns:
                    if re.search(pat, content):
                        s_issue = 1.0
                        break
                if s_issue == 1.0:
                    break

        # 4. Chiều 4: Condition scope match [0.0, 1.0]
        # Tìm các con số, thời hạn, tỷ lệ % hoặc từ khóa điều kiện
        has_number = bool(re.search(r"\b\d+(\s*([%]|ngày|tháng|năm|giờ|triệu|đồng))?\b", content))
        has_condition = bool(re.search(r"\b(trường\s+hợp|điều\s+kiện|quy\s+định|nếu|trừ\s+khi|ngoại\s+lệ)\b", content))
        s_cond = 0.0
        if has_number and has_condition:
            s_cond = 1.0
        elif has_number or has_condition:
            s_cond = 0.6
        else:
            s_cond = 0.2

        # 5. Cổng nhân tử hiệu lực G_temporal
        g_temp = self._get_temporal_gate(doc_id)

        # Tính S_content = sum(w_i * s_i)
        w1, w2, w3, w4 = self.weights
        s_content = w1 * s_sem + w2 * s_subj + w3 * s_issue + w4 * s_cond

        # Điểm chunk cuối cùng
        s_chunk = g_temp * s_content

        verdict = "SUPPORTED" if s_chunk >= 0.55 else ("PARTIAL" if s_chunk >= 0.40 else "UNSUPPORTED")
        reason = None
        if g_temp == 0.0:
            reason = f"Văn bản {doc_id} đã hết hiệu lực hoàn toàn (G_temporal = 0.0)."
        elif s_issue == 0.0 and s_sem > 0.70:
            reason = "Ảo giác tương đồng ngữ nghĩa: Điểm cosine cao nhưng lạc sang chế định pháp lý khác."

        return ChunkGrade(
            chunk_id=chunk.chunk_id,
            document_id=doc_id,
            article_number=article_num,
            scores={
                "semantic_relevance": round(s_sem, 4),
                "legal_subject_match": round(s_subj, 4),
                "legal_issue_match": round(s_issue, 4),
                "condition_scope_match": round(s_cond, 4),
                "temporal_validity_gate": round(g_temp, 4),
            },
            chunk_score=round(s_chunk, 4),
            verdict=verdict,
            reason=reason,
        )

    def evaluate(self, query: str, retrieved_chunks: List[RetrievedChunk]) -> EvidenceGradingReport:
        """Đánh giá toàn diện tập bằng chứng thu hồi và đưa ra phán quyết trước sinh."""
        if not retrieved_chunks:
            return EvidenceGradingReport(
                query=query,
                total_chunks_evaluated=0,
                overall_verdict="UNSUPPORTED",
                trigger_refusal=True,
                refusal_reason="Danh sách đoạn trích thu hồi rỗng.",
                refusal_message="Hệ thống không tìm thấy bất kỳ tài liệu pháp lý nào liên quan trong kho dữ liệu.",
            )

        q_issues = self._identify_query_issues(query)
        q_subjects = self._identify_query_subjects(query)

        chunk_grades: List[ChunkGrade] = []
        for c in retrieved_chunks:
            grade = self._score_chunk(c, query, q_issues, q_subjects)
            chunk_grades.append(grade)

        # Tìm chunk điểm cao nhất
        best_grade = max(chunk_grades, key=lambda g: g.chunk_score)
        best_score = best_grade.chunk_score

        # --- ÁP DỤNG SAFE VETO RULE (Quy tắc Phủ quyết An toàn 3 cấp) ---
        # Điều kiện Veto: Khi có nhận diện issue (q_issues không rỗng),
        # nhưng 100% chunk đều có legal_issue_match == 0 VÀ không có chunk nào vượt ngưỡng ngữ nghĩa cao (>= 0.82)
        veto_triggered = False
        veto_trace = None

        if q_issues:
            # Kiểm tra câu hỏi tình huống đời thường (Colloquial Situation Query):
            # Tránh phủ quyết sai khi ontology gán nhầm hoặc câu hỏi dùng từ ngữ đời thường (bảo vệ FRR)
            is_colloquial_query = bool(re.search(
                r"\b(em|tôi|sếp|chủ|chỗ\s+làm|quán\s+ăn|phụ\s+bếp|thợ|đi\s+làm|nghỉ\s+ngang|bị\s+đuổi|trừ\s+lương|thử\s+việc)\b",
                query.lower()
            ))

            all_issue_mismatch = all(g.scores.get("legal_issue_match", 0.0) == 0.0 for g in chunk_grades)
            any_high_semantic = any(g.scores.get("semantic_relevance", 0.0) >= self.high_sem_override for g in chunk_grades)

            if all_issue_mismatch and not any_high_semantic and not is_colloquial_query:
                veto_triggered = True
                veto_trace = "SAFE_VETO_RULE: 100% chunks không khớp vấn đề pháp lý của câu hỏi và không có chunk nào vượt ngưỡng ngữ nghĩa cao (tau_high_sem = 0.78)."
                logger.info("Tier 3 Evidence Gate: %s", veto_trace)
            elif all_issue_mismatch:
                veto_trace = "UNCERTAIN_ISSUE_OVERRIDE: 100% chunks lệch issue theo ontology nhưng câu hỏi đời thường hoặc có chunk đạt ngữ nghĩa cao -> Cho phép chuyển tiếp sang Tier 4."
                logger.info("Tier 3 Evidence Gate: %s", veto_trace)

        # Tính Coverage Bonus
        # Nếu có ít nhất 2 chunk có issue match hoặc subject match bổ sung cho nhau
        coverage_bonus = 0.0
        if not veto_triggered and len(chunk_grades) >= 2:
            other_grades = [g for g in chunk_grades if g.chunk_id != best_grade.chunk_id and g.chunk_score >= 0.40]
            if other_grades:
                # Đóng góp biên: chunk phụ cung cấp thêm điều kiện con số hoặc đối tượng
                has_extra_cond = any(g.scores.get("condition_scope_match", 0.0) >= 0.8 for g in other_grades)
                if has_extra_cond and best_grade.scores.get("condition_scope_match", 0.0) < 0.8:
                    coverage_bonus = self.coverage_alpha

        # Tính Composite Score với hàm chặn trên min(1.0, ...)
        if veto_triggered:
            composite_score = 0.0
        else:
            composite_score = min(1.0, best_score + coverage_bonus)

        # Phán quyết cuối cùng
        trigger_refusal = composite_score < self.threshold_unsupported
        overall_verdict = "SUPPORTED" if not trigger_refusal else "UNSUPPORTED"
        refusal_reason = None
        refusal_msg = None

        if trigger_refusal:
            if veto_triggered:
                refusal_reason = "Phủ quyết do toàn bộ tài liệu thu hồi sai lệch vấn đề pháp lý cốt lõi."
            else:
                refusal_reason = (
                    f"Điểm bằng chứng tổng hợp ({composite_score:.4f}) thấp hơn ngưỡng an toàn tối thiểu ({self.threshold_unsupported:.4f}). "
                    f"Kho dữ liệu không có đủ chứng cứ pháp lý xác thực để khẳng định câu trả lời."
                )
            refusal_msg = (
                "Căn cứ cơ sở dữ liệu văn bản pháp luật hiện hành, hệ thống không tìm thấy đủ chứng cứ pháp lý xác thực "
                "để khẳng định câu trả lời cho trường hợp này. Vui lòng đối chiếu thêm các văn bản hướng dẫn hoặc cung cấp thêm tình tiết."
            )

        return EvidenceGradingReport(
            query=query,
            total_chunks_evaluated=len(chunk_grades),
            chunk_grades=chunk_grades,
            best_chunk_score=round(best_score, 4),
            coverage_bonus=round(coverage_bonus, 4),
            composite_evidence_score=round(composite_score, 4),
            threshold_applied=self.threshold_unsupported,
            overall_verdict=overall_verdict,
            trigger_refusal=trigger_refusal,
            refusal_reason=refusal_reason,
            refusal_message=refusal_msg,
            conflict_resolution_trace=veto_trace,
        )
