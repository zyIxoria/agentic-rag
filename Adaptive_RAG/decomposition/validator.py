"""
Adaptive RAG Sub-Query Validator & Repairer.
Thực hiện kiểm định chất lượng (Validation) và sửa chữa tự động (Repair Loop)
cho các câu hỏi con sau phân rã theo 5 tiêu chuẩn khắt khe:
1. Coverage (Độ bao phủ ý định)
2. Context Preservation (Bảo toàn chủ thể, điều kiện, đối tượng)
3. Redundancy (Loại trừ trùng lặp nội dung giữa các câu hỏi cùng nguồn)
4. Atomicity (Tính nguyên tử, tập trung)
5. Retrieval Suitability (Tính tương thích với Dense/CRAG Retriever)
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple, Optional, Set
from Adaptive_RAG.decomposition.schema import SubQuery, ValidationResult


class SubQueryValidator:
    """Bộ kiểm định chất lượng các câu hỏi con sau phân rã."""

    # Danh sách các chủ thể đặc thù bắt buộc phải bảo toàn ngữ cảnh
    CRITICAL_SUBJECTS = [
        "mang thai", "thai sản", "nuôi con nhỏ", "chưa thành niên", "dưới 15 tuổi",
        "dưới 18 tuổi", "người nước ngoài", "thử việc", "cao tuổi", "người giúp việc",
        "tai nạn lao động", "bệnh nghề nghiệp", "công đoàn"
    ]

    # Danh sách các điều kiện/hoàn cảnh quan trọng
    CRITICAL_CONDITIONS = [
        "ban đêm", "ngày nghỉ lễ", "ngày tết", "ngày nghỉ hằng tuần",
        "tự ý bỏ việc", "5 ngày", "thiên tai", "hỏa hoạn",
        "đơn phương chấm dứt", "thay đổi cơ cấu", "sáp nhập", "giải thể"
    ]

    def _tokenize_legal_terms(self, text: str) -> Set[str]:
        """Tách từ vựng pháp lý cơ bản để so khớp độ bao phủ."""
        words = re.findall(r"\b[\w_]+\b", text.lower())
        stopwords = {"và", "hay", "hoặc", "của", "cho", "về", "thì", "là", "các", "những", "được", "có", "không", "như", "thế", "nào", "gì", "ai", "theo", "tại"}
        return {w for w in words if len(w) > 1 and w not in stopwords}

    def validate(
        self,
        original_query: str,
        sub_queries: List[SubQuery],
        detected_subjects: Optional[List[str]] = None,
    ) -> ValidationResult:
        """
        Thực hiện kiểm định 5 tiêu chí trên danh sách sub-queries.
        """
        issues: List[str] = []
        q_lower = original_query.lower()

        # Nếu không có sub-queries nào -> Fail ngay lập tức
        if not sub_queries:
            return ValidationResult(
                is_valid=False,
                coverage_score=0.0,
                context_preserved=False,
                has_redundancy=False,
                is_atomic=False,
                retrieval_suitable=False,
                issues=["Không có câu hỏi con nào được tạo ra sau phân rã."]
            )

        # ---------------------------------------------------------------------
        # 1. TIÊU CHÍ ATOMICITY (Tính nguyên tử)
        # ---------------------------------------------------------------------
        is_atomic = True
        for sq in sub_queries:
            text = sq.text.strip()
            # Một sub-query không được chứa từ 2 dấu hỏi chấm riêng biệt
            if text.count("?") >= 2:
                is_atomic = False
                issues.append(f"Truy vấn '{sq.sub_id}' chứa nhiều câu hỏi con chưa được tách nguyên tử hoàn chỉnh.")
            if len(text.split()) > 50 and ("và đồng thời" in text.lower() or "trong khi đó" in text.lower()):
                is_atomic = False
                issues.append(f"Truy vấn '{sq.sub_id}' quá dài và còn chứa nhiều mệnh đề phức tạp.")

        # ---------------------------------------------------------------------
        # 2. TIÊU CHÍ CONTEXT PRESERVATION (Bảo toàn ngữ cảnh)
        # ---------------------------------------------------------------------
        context_preserved = True
        all_sub_text = " ".join(sq.text for sq in sub_queries).lower()

        # Kiểm tra sự xuất hiện của các chủ thể đặc thù
        for subj in self.CRITICAL_SUBJECTS:
            if subj in q_lower and subj not in all_sub_text:
                context_preserved = False
                issues.append(f"Bị mất ngữ cảnh chủ thể đặc thù '{subj}' trong toàn bộ các câu hỏi con.")

        # Kiểm tra sự xuất hiện của các điều kiện mấu chốt
        for cond in self.CRITICAL_CONDITIONS:
            if cond in q_lower and cond not in all_sub_text:
                context_preserved = False
                issues.append(f"Bị mất điều kiện/hoàn cảnh quan trọng '{cond}' sau khi phân rã.")

        # Kiểm tra số Điều luật xuất hiện trong câu hỏi gốc
        orig_articles = re.findall(r"(?i)\bĐiều\s+\d+\b", original_query)
        for art in orig_articles:
            if art.lower() not in all_sub_text:
                context_preserved = False
                issues.append(f"Bị mất viện dẫn Điều luật '{art}' trong các câu hỏi con.")

        # ---------------------------------------------------------------------
        # 3. TIÊU CHÍ REDUNDANCY (Loại trừ trùng lặp giữa các câu hỏi cùng nguồn)
        # ---------------------------------------------------------------------
        has_redundancy = False
        n = len(sub_queries)
        for i in range(n):
            for j in range(i + 1, n):
                sq1 = sub_queries[i]
                sq2 = sub_queries[j]
                # Nếu hai sub-queries hướng tới hai thực thể/văn bản khác nhau -> Không coi là trùng lặp!
                if sq1.target_entity and sq2.target_entity and sq1.target_entity.strip().lower() != sq2.target_entity.strip().lower():
                    continue

                t1 = sq1.text.strip().lower()
                t2 = sq2.text.strip().lower()
                tokens_1 = self._tokenize_legal_terms(t1)
                tokens_2 = self._tokenize_legal_terms(t2)
                if tokens_1 and tokens_2:
                    jaccard = len(tokens_1 & tokens_2) / len(tokens_1 | tokens_2)
                    if jaccard >= 0.80:
                        has_redundancy = True
                        issues.append(f"Phát hiện trùng lặp cao (Jaccard={jaccard:.2f}) giữa '{sq1.sub_id}' và '{sq2.sub_id}'.")

        # ---------------------------------------------------------------------
        # 4. TIÊU CHÍ RETRIEVAL SUITABILITY (Tính phù hợp truy xuất)
        # ---------------------------------------------------------------------
        retrieval_suitable = True
        dangling_pronouns = ["làm điều đó", "như vậy", "nếu vậy", "trường hợp này", "họ", "anh ấy", "cô ấy"]
        for sq in sub_queries:
            t = sq.text.strip().lower()
            if len(t) < 15:
                retrieval_suitable = False
                issues.append(f"Truy vấn '{sq.sub_id}' quá ngắn (<15 ký tự), không đủ ngữ nghĩa để tìm kiếm.")
            for p in dangling_pronouns:
                if re.search(rf"\b{p}\b", t) and not any(k in t for k in ["lao động", "lương", "kỷ luật", "hợp đồng"]):
                    retrieval_suitable = False
                    issues.append(f"Truy vấn '{sq.sub_id}' chứa đại từ tham chiếu lửng lơ '{p}' chưa giải quyết ngữ cảnh.")

        # ---------------------------------------------------------------------
        # 5. TIÊU CHÍ COVERAGE (Độ bao phủ ý định)
        # ---------------------------------------------------------------------
        orig_tokens = self._tokenize_legal_terms(original_query)
        sub_tokens = self._tokenize_legal_terms(all_sub_text)
        coverage_score = 1.0
        if orig_tokens:
            covered = len(orig_tokens & sub_tokens)
            coverage_score = round(covered / len(orig_tokens), 4)
            if coverage_score < 0.60:
                issues.append(f"Độ bao phủ ý định thấp ({coverage_score*100:.1f}% < 60%).")

        is_valid = (
            context_preserved
            and not has_redundancy
            and is_atomic
            and retrieval_suitable
            and coverage_score >= 0.60
        )

        return ValidationResult(
            is_valid=is_valid,
            coverage_score=coverage_score,
            context_preserved=context_preserved,
            has_redundancy=has_redundancy,
            is_atomic=is_atomic,
            retrieval_suitable=retrieval_suitable,
            issues=issues,
        )


class SubQueryRepairer:
    """Bộ sửa chữa tự động các lỗi kiểm định của câu hỏi con (Repair Loop)."""

    def repair(
        self,
        original_query: str,
        sub_queries: List[SubQuery],
        validation: ValidationResult,
    ) -> List[SubQuery]:
        """
        Sửa chữa tự động các vấn đề phát hiện được từ ValidationResult:
        - Khử trùng lặp (Deduplicate)
        - Bổ sung ngữ cảnh bị thiếu (Context Injection)
        - Hoàn thiện định dạng câu hỏi tìm kiếm (Question Normalization)
        """
        if validation.is_valid:
            return sub_queries

        repaired_queries = list(sub_queries)

        # 1. Sửa lỗi Redundancy (Loại bỏ câu hỏi con bị trùng)
        validator = SubQueryValidator()
        if validation.has_redundancy and len(repaired_queries) >= 2:
            unique_queries: List[SubQuery] = []
            for sq in repaired_queries:
                is_dup = False
                for uq in unique_queries:
                    # Nếu khác target_entity thì không phải trùng lặp
                    if sq.target_entity and uq.target_entity and sq.target_entity.strip().lower() != uq.target_entity.strip().lower():
                        continue
                    w1 = validator._tokenize_legal_terms(sq.text)
                    w2 = validator._tokenize_legal_terms(uq.text)
                    if w1 and w2 and len(w1 & w2) / len(w1 | w2) >= 0.80:
                        is_dup = True
                        break
                if not is_dup:
                    unique_queries.append(sq)
            if len(unique_queries) >= 1:
                repaired_queries = unique_queries

        # 2. Sửa lỗi Context Preservation (Tiêm lại chủ thể/điều kiện quan trọng nếu bị mất)
        q_lower = original_query.lower()
        missing_terms: List[str] = []
        for term in SubQueryValidator.CRITICAL_SUBJECTS + SubQueryValidator.CRITICAL_CONDITIONS:
            if term in q_lower and not any(term in sq.text.lower() for sq in repaired_queries):
                missing_terms.append(term)

        if missing_terms and repaired_queries:
            inject_str = ", ".join(missing_terms)
            target_sq = repaired_queries[-1]
            if not target_sq.text.endswith("?"):
                target_sq.text = f"{target_sq.text.strip()} (áp dụng đối với {inject_str})?"
            else:
                base_t = target_sq.text.rstrip("?").strip()
                target_sq.text = f"{base_t} (áp dụng đối với {inject_str})?"
            if inject_str not in target_sq.constraints:
                target_sq.constraints.extend(missing_terms)

        # 3. Sửa lỗi Retrieval Suitability & Dấu câu
        for sq in repaired_queries:
            t = sq.text.strip()
            if not t.endswith("?"):
                sq.text = t + "?"
            for p in ["nếu vậy,", "trong trường hợp này,"]:
                if sq.text.lower().startswith(p):
                    sq.text = sq.text[len(p):].strip().capitalize()

        return repaired_queries
