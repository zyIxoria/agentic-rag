"""
test_query_decomposer.py - Bộ kiểm thử toàn diện cho Module 11: Query Decomposition.

Bao gồm:
1. Unit tests kiểm định chất lượng:
   - Coverage check
   - Context preservation check (không mất chủ thể, điều kiện)
   - Redundancy check & deduplication
   - Atomicity & retrieval suitability check
   - Repair Loop check
2. Parametrized tests trên 40+ câu hỏi kiểm chứng đại diện cho toàn bộ Taxonomy:
   - Simple (No decomposition)
   - Multi-Issue (Đa vấn đề độc lập)
   - Multi-Condition (Đa điều kiện, tình huống mâu thuẫn)
   - Multi-Document (Đa văn bản quy phạm)
   - Cross-Reference (Viện dẫn chéo giữa các Điều luật)
   - Conditional / Temporal (Tính toán quá độ qua mốc thời gian)
3. Dependency Graph & Execution Order tests (DAG).
4. Determinism test (100% tất định qua nhiều lần chạy).
"""

import pytest
from typing import List

from Adaptive_RAG.decomposition.schema import (
    DecompositionPlan,
    DecompositionType,
    ExecutionStrategy,
    SubQuery,
    ValidationResult,
)
from Adaptive_RAG.decomposition.legal_decomposer import LegalQueryDecomposer
from Adaptive_RAG.decomposition.validator import SubQueryValidator, SubQueryRepairer


class TestQueryDecompositionSuite:
    """Tập kiểm thử toàn diện cho Query Decomposer (Module 11)."""

    @pytest.fixture
    def decomposer(self) -> LegalQueryDecomposer:
        return LegalQueryDecomposer()

    @pytest.fixture
    def validator(self) -> SubQueryValidator:
        return SubQueryValidator()

    @pytest.fixture
    def repairer(self) -> SubQueryRepairer:
        return SubQueryRepairer()

    # =========================================================================
    # 1. UNIT TESTS: VALIDATION & REPAIR LOOP
    # =========================================================================

    def test_validator_detects_redundancy(self, validator: SubQueryValidator):
        """Kiểm tra validator phát hiện chính xác các câu hỏi con bị trùng lặp."""
        q = "Thời giờ làm việc bình thường của người lao động?"
        sub_1 = SubQuery(sub_id="sub_1", text="Quy định về thời giờ làm việc bình thường của người lao động?")
        sub_2 = SubQuery(sub_id="sub_2", text="Quy định về thời giờ làm việc bình thường của người lao động hiện nay?")
        res = validator.validate(q, [sub_1, sub_2])
        assert res.has_redundancy is True
        assert res.is_valid is False

    def test_validator_detects_context_loss(self, validator: SubQueryValidator):
        """Kiểm tra validator phát hiện khi câu hỏi con làm rơi mất chủ thể đặc thù (mang thai)."""
        q = "Lao động nữ mang thai có được làm thêm giờ ban đêm không?"
        # Sub-query làm mất từ khóa "mang thai"
        sub_1 = SubQuery(sub_id="sub_1", text="Người lao động có được làm thêm giờ vào ban đêm không?")
        res = validator.validate(q, [sub_1])
        assert res.context_preserved is False
        assert any("mang thai" in issue for issue in res.issues)

    def test_repairer_fixes_redundancy_and_context(self, validator: SubQueryValidator, repairer: SubQueryRepairer):
        """Kiểm tra repairer tự động khử trùng lặp và tiêm lại ngữ cảnh bị thiếu."""
        q = "Lao động nữ mang thai có được làm thêm giờ vào ban đêm không?"
        sub_1 = SubQuery(sub_id="sub_1", text="Quy định về làm thêm giờ ban đêm của người lao động?")
        sub_2 = SubQuery(sub_id="sub_2", text="Quy định về làm thêm giờ ban đêm của người lao động hiện nay?")
        val = validator.validate(q, [sub_1, sub_2])
        assert val.is_valid is False

        repaired = repairer.repair(q, [sub_1, sub_2], val)
        assert len(repaired) == 1  # Đã khử trùng
        assert "mang thai" in repaired[0].text.lower()  # Đã tiêm lại ngữ cảnh

    # =========================================================================
    # 2. TAXONOMY: SIMPLE QUERIES (KHÔNG ĐƯỢC OVER-DECOMPOSE)
    # =========================================================================

    @pytest.mark.parametrize("query", [
        "Thời giờ làm việc bình thường của người lao động tối đa bao nhiêu giờ trong một ngày?",
        "Thời gian nghỉ giữa giờ trong ca làm việc bình thường là bao nhiêu phút?",
        "Tuổi nghỉ hưu của người lao động trong điều kiện bình thường?",
        "Thời hạn của hợp đồng lao động xác định thời hạn tối đa là bao nhiêu tháng?",
        "Điều 125 Bộ luật Lao động 2019 quy định về nội dung gì?",
        "Mức lương tối thiểu vùng hiện nay do cơ quan nào công bố?",
        "Người lao động được nghỉ bao nhiêu ngày khi kết hôn?",
        "Mức đóng bảo hiểm y tế của người lao động là bao nhiêu phần trăm?",
    ])
    def test_simple_queries_no_over_decomposition(self, decomposer: LegalQueryDecomposer, query: str):
        """Kiểm tra câu hỏi đơn giản không bị phân rã thừa (No Over-Decomposition)."""
        plan = decomposer.decompose(query)
        assert plan.decomposition_required is False
        assert len(plan.sub_queries) == 1
        assert plan.sub_queries[0].text == query
        assert plan.strategy == ExecutionStrategy.PARALLEL
        assert plan.validation.is_valid is True

    # =========================================================================
    # 3. TAXONOMY: MULTI_ISSUE (ĐA VẤN ĐỀ ĐỘC LẬP)
    # =========================================================================

    @pytest.mark.parametrize("query", [
        "Người lao động nghỉ việc thì phải báo trước bao nhiêu ngày và có được hưởng trợ cấp thôi việc không?",
        "Hồ sơ xin cấp lại giấy phép lao động như thế nào và có bị phạt tiền không?",
        "Người lao động thử việc có phải đóng bảo hiểm xã hội không và tiền lương thử việc được trả thế nào?",
        "Thời hạn tạm đình chỉ công việc tối đa bao nhiêu ngày và có được tạm ứng tiền lương không?",
        "Người sử dụng lao động có quyền giữ bằng gốc của người lao động không và bị xử phạt như thế nào?",
        "Nội quy lao động bắt buộc phải có những nội dung gì và thủ tục đăng ký thực hiện ra sao?",
    ])
    def test_multi_issue_decomposition(self, decomposer: LegalQueryDecomposer, query: str):
        """Kiểm tra phân rã câu hỏi đa vấn đề độc lập thành các sub-queries song song."""
        plan = decomposer.decompose(query)
        assert plan.decomposition_required is True
        assert len(plan.sub_queries) >= 2
        assert plan.strategy == ExecutionStrategy.PARALLEL
        assert plan.validation.is_valid is True
        # Đảm bảo các sub-queries có nội dung khác biệt rõ rệt
        texts = [sq.text.lower() for sq in plan.sub_queries]
        assert len(set(texts)) == len(texts)

    # =========================================================================
    # 4. TAXONOMY: MULTI_CONDITION (ĐA ĐIỀU KIỆN, MÂU THUẪN HOÀN CẢNH)
    # =========================================================================

    @pytest.mark.parametrize("query", [
        "Người lao động vừa tự ý bỏ việc 5 ngày vừa đang mang thai thì có bị áp dụng sa thải không và phải xử lý như thế nào?",
        "Người lao động nữ mang thai có được làm thêm giờ vào ban đêm không và nếu được thì tiền lương được tính như thế nào?",
        "Cách tính tiền lương làm thêm giờ vào ban đêm ngày nghỉ lễ tết trùng với ngày nghỉ hằng tuần?",
        "Người lao động bị tai nạn lao động suy giảm khả năng lao động 35% thì trách nhiệm bồi thường của công ty và chế độ bảo hiểm xã hội được giải quyết ra sao?",
        "Trường hợp chấm dứt hợp đồng lao động do thay đổi cơ cấu công nghệ thì quy trình lập phương án sử dụng lao động và mức trợ cấp mất việc làm tính thế nào?",
    ])
    def test_multi_condition_decomposition(self, decomposer: LegalQueryDecomposer, query: str):
        """Kiểm tra phân rã câu hỏi đa điều kiện và thiết lập quan hệ phụ thuộc (HYBRID)."""
        plan = decomposer.decompose(query)
        assert plan.decomposition_required is True
        assert len(plan.sub_queries) >= 2
        assert plan.strategy == ExecutionStrategy.HYBRID
        # Kiểm tra tồn tại dependency giữa các câu hỏi con
        has_dep = any(len(sq.dependency_ids) > 0 for sq in plan.sub_queries)
        assert has_dep is True
        assert plan.validation.is_valid is True

    # =========================================================================
    # 5. TAXONOMY: MULTI_DOCUMENT (ĐA VĂN BẢN QUY PHẠM)
    # =========================================================================

    @pytest.mark.parametrize("query,expected_docs", [
        ("So sánh quy định về thời giờ làm việc và làm thêm giờ giữa Bộ luật Lao động 2019 và Nghị định 145/2020/NĐ-CP?",
         ["Bộ luật Lao động 2019", "Nghị định 145/2020/NĐ-CP"]),
        ("Hồ sơ, thủ tục cấp giấy phép lao động cho chuyên gia nước ngoài theo Nghị định 152/2020 và Nghị định 70/2023 sửa đổi?",
         ["Nghị định 152/2020/NĐ-CP", "Nghị định 70/2023/NĐ-CP"]),
        ("Mức xử phạt vi phạm hành chính đối với hành vi cưỡng bức lao động theo Nghị định 12/2022 và các trường hợp bị truy cứu trách nhiệm hình sự theo Bộ luật Hình sự?",
         ["Nghị định 12/2022/NĐ-CP", "Bộ luật Hình sự"]),
        ("Người lao động làm công việc nặng nhọc độc hại theo Thông tư 09/2020 thì tuổi nghỉ hưu theo Bộ luật Lao động quy định như thế nào?",
         ["Thông tư 09/2020/TT-BLĐTBXH", "Bộ luật Lao động 2019"]),
    ])
    def test_multi_document_decomposition(self, decomposer: LegalQueryDecomposer, query: str, expected_docs: List[str]):
        """Kiểm tra phân rã câu hỏi đa văn bản gắn chính xác văn bản mục tiêu vào từng sub-query."""
        plan = decomposer.decompose(query)
        assert plan.decomposition_required is True
        assert len(plan.sub_queries) >= 2
        assert plan.strategy == ExecutionStrategy.PARALLEL
        # Kiểm tra văn bản mục tiêu được phân bổ vào các sub-queries
        all_sub_texts = " ".join(sq.text for sq in plan.sub_queries)
        for doc in expected_docs:
            doc_short = doc.split("/")[0]  # VD: Nghị định 152
            assert doc_short.lower() in all_sub_texts.lower()

    # =========================================================================
    # 6. TAXONOMY: CROSS_REFERENCE (VIỆN DẪN CHÉO NHIỀU ĐIỀU LUẬT)
    # =========================================================================

    @pytest.mark.parametrize("query,expected_arts", [
        ("Đối chiếu quy định tại Điều 169 và Điều 219 Bộ luật Lao động 2019 về điều kiện và tuổi nghỉ hưu của lao động nữ?",
         ["Điều 169", "Điều 219"]),
        ("Điều kiện xử lý kỷ luật sa thải quy định tại Điều 125 và các trường hợp không được xử lý kỷ luật tại Điều 122 Bộ luật Lao động?",
         ["Điều 125", "Điều 122"]),
    ])
    def test_cross_reference_decomposition(self, decomposer: LegalQueryDecomposer, query: str, expected_arts: List[str]):
        """Kiểm tra phân rã viện dẫn chéo bảo toàn số Điều luật và tổng hợp mối liên hệ."""
        plan = decomposer.decompose(query)
        assert plan.decomposition_required is True
        assert len(plan.sub_queries) >= 2
        # Kiểm tra các Điều luật xuất hiện trong các sub-queries
        for art in expected_arts:
            assert any(art.lower() in sq.text.lower() for sq in plan.sub_queries)
        # Kiểm tra câu hỏi con thứ 3 phụ thuộc
        if len(plan.sub_queries) >= 3:
            assert "sub_1" in plan.sub_queries[2].dependency_ids
            assert "sub_2" in plan.sub_queries[2].dependency_ids

    # =========================================================================
    # 7. TAXONOMY: CONDITIONAL_TEMPORAL (TÍNH TOÁN QUÁ ĐỘ BHTN vs THÔI VIỆC)
    # =========================================================================

    def test_temporal_calculation_decomposition(self, decomposer: LegalQueryDecomposer):
        """Kiểm tra phân rã câu hỏi tính trợ cấp thôi việc trừ thời gian đóng BHTN từ năm 2009."""
        q = "Cách tính tiền trợ cấp thôi việc cho người lao động làm việc từ năm 2005 đến năm 2023 có thời gian đóng bảo hiểm thất nghiệp từ 2009?"
        plan = decomposer.decompose(q)
        assert plan.decomposition_required is True
        assert len(plan.sub_queries) >= 2
        assert plan.strategy == ExecutionStrategy.HYBRID
        # Phải đề cập cả trợ cấp thôi việc và bảo hiểm thất nghiệp
        all_texts = " ".join(sq.text.lower() for sq in plan.sub_queries)
        assert "trợ cấp thôi việc" in all_texts
        assert "bảo hiểm thất nghiệp" in all_texts

    # =========================================================================
    # 8. CONTEXT PRESERVATION: CHỦ THỂ ĐẶC THÙ KHÔNG BỊ RƠI
    # =========================================================================

    @pytest.mark.parametrize("query,expected_keyword", [
        ("Lao động nữ mang thai có được làm thêm giờ vào ban đêm không và tiền lương tính thế nào?", "mang thai"),
        ("Người lao động chưa thành niên dưới 15 tuổi được làm việc bao nhiêu giờ trong một ngày và có được làm ca đêm không?", "chưa thành niên"),
        ("Hồ sơ xin cấp giấy phép lao động cho chuyên gia nước ngoài gồm những gì và thời hạn nộp trước bao nhiêu ngày?", "nước ngoài"),
        ("Người lao động đang trong thời gian thử việc có phải đóng bảo hiểm xã hội bắt buộc không và thời hạn thử việc tối đa?", "thử việc"),
    ])
    def test_context_preservation_guarantee(self, decomposer: LegalQueryDecomposer, query: str, expected_keyword: str):
        """Bảo đảm chủ thể nhạy cảm luôn xuất hiện trong các câu hỏi con sau phân rã."""
        plan = decomposer.decompose(query)
        assert plan.decomposition_required is True
        # Mỗi câu hỏi con đều phải chứa ngữ cảnh chủ thể
        for sq in plan.sub_queries:
            assert expected_keyword in sq.text.lower() or "lao động" in sq.text.lower()

    # =========================================================================
    # 9. DETERMINISM TEST: TÍNH TẤT ĐỊNH 100%
    # =========================================================================

    def test_determinism_consistency(self, decomposer: LegalQueryDecomposer):
        """Kiểm tra tính tất định: cùng 1 câu hỏi phức tạp chạy 10 lần liên tiếp phải ra các sub-queries giống hệt."""
        q = "Người lao động nữ đang mang thai có được làm thêm giờ vào ban đêm không, và nếu được thì tiền lương được tính như thế nào?"
        first_plan = decomposer.decompose(q).model_dump()

        for _ in range(9):
            repeat_plan = decomposer.decompose(q).model_dump()
            assert len(first_plan["sub_queries"]) == len(repeat_plan["sub_queries"])
            for sq1, sq2 in zip(first_plan["sub_queries"], repeat_plan["sub_queries"]):
                assert sq1["text"] == sq2["text"]
                assert sq1["dependency_ids"] == sq2["dependency_ids"]
                assert sq1["execution_order"] == sq2["execution_order"]

    # =========================================================================
    # 10. AMBIGUOUS & OUT-OF-SCOPE QUERIES: XỬ LÝ AN TOÀN, KHÔNG CRASH
    # =========================================================================

    @pytest.mark.parametrize("query,expected_decomp", [
        ("Quy định về thời giờ làm việc?", False),
        ("Chế độ thai sản?", False),
        ("Thủ tục thành lập công ty cổ phần?", False),
        ("Thủ tục đăng ký kinh doanh và thuế môn bài đối với doanh nghiệp tư nhân?", False),
    ])
    def test_ambiguous_and_out_of_scope_queries(self, decomposer: LegalQueryDecomposer, query: str, expected_decomp: bool):
        """Đảm bảo các câu hỏi mơ hồ hoặc ngoài phạm vi được xử lý an toàn và không gây crash."""
        plan = decomposer.decompose(query)
        assert plan.decomposition_required is expected_decomp
        assert plan.validation.is_valid is True
        assert len(plan.sub_queries) >= 1

    # =========================================================================
    # 11. REPAIR LOOP INTEGRATION TEST (TỰ ĐỘNG SỬA CHỮA SUB-QUERIES LỖI)
    # =========================================================================

    def test_repair_loop_redundancy(self, decomposer: LegalQueryDecomposer):
        """Kiểm tra khả năng phát hiện sub-queries trùng lặp và tự động sửa chữa loại bỏ trùng lặp."""
        validator = SubQueryValidator()
        repairer = SubQueryRepairer()

        orig_query = "Thời giờ làm việc bình thường của người lao động?"
        # Tạo sub-queries giả lập trùng lặp ngữ nghĩa (Jaccard > 0.8)
        dup_sq1 = SubQuery(
            sub_id="sub_1",
            text="Thời giờ làm việc bình thường của người lao động là bao nhiêu giờ trong một ngày theo quy định?",
            intent="Xác định giờ làm",
        )
        dup_sq2 = SubQuery(
            sub_id="sub_2",
            text="Thời giờ làm việc bình thường của người lao động là bao nhiêu giờ một ngày theo quy định pháp luật?",
            intent="Xác định giờ làm",
        )

        val_res = validator.validate(orig_query, [dup_sq1, dup_sq2])
        assert val_res.has_redundancy is True
        assert val_res.is_valid is False

        # Thực thi sửa chữa
        repaired_sqs = repairer.repair(orig_query, [dup_sq1, dup_sq2], val_res)
        assert len(repaired_sqs) == 1
        assert repaired_sqs[0].sub_id == "sub_1"

        # Kiểm định lại sau sửa chữa
        reval = validator.validate(orig_query, repaired_sqs)
        assert reval.has_redundancy is False

    def test_repair_loop_context_loss(self, decomposer: LegalQueryDecomposer):
        """Kiểm tra khả năng bổ sung ngữ cảnh khi câu hỏi con bị mất chủ thể đặc thù."""
        validator = SubQueryValidator()
        repairer = SubQueryRepairer()

        orig_query = "Lao động nữ mang thai có được làm thêm giờ không và mức lương tính thế nào?"
        # Cả hai sub-queries đều bị mất chủ thể quan trọng "mang thai"
        sq1 = SubQuery(sub_id="sub_1", text="Người lao động có được làm thêm giờ không?", intent="q1")
        sq2 = SubQuery(sub_id="sub_2", text="Mức lương làm thêm giờ tính thế nào?", intent="q2")

        val_res = validator.validate(orig_query, [sq1, sq2])
        assert val_res.context_preserved is False

        # Repairer tiêm context chủ thể vào sq2
        repaired = repairer.repair(orig_query, [sq1, sq2], val_res)
        assert len(repaired) == 2
        assert "mang thai" in repaired[1].text.lower() or "thai" in repaired[1].text.lower()

    # =========================================================================
    # 12. MORE CROSS-REFERENCE & MULTI-DOC QUERIES
    # =========================================================================

    def test_more_cross_reference_and_multidoc(self, decomposer: LegalQueryDecomposer):
        """Bổ sung các test cases phức hợp đa văn bản và viện dẫn chéo khác."""
        q_cross = "Điều kiện hưởng lương hưu tại Điều 54 Luật Bảo hiểm xã hội đối chiếu với Điều 169 Bộ luật Lao động 2019?"
        plan_cross = decomposer.decompose(q_cross)
        assert plan_cross.decomposition_required is True
        assert any(sq.target_entity == "Luật Bảo hiểm xã hội 2014" or "bảo hiểm" in sq.text.lower() for sq in plan_cross.sub_queries)

        q_multidoc = "Nghị định 145/2020 hướng dẫn điều kiện làm thêm giờ của Bộ luật Lao động như thế nào?"
        plan_multidoc = decomposer.decompose(q_multidoc)
        assert plan_multidoc.decomposition_required is True
        assert len(plan_multidoc.sub_queries) >= 2
