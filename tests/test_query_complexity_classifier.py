"""
test_query_complexity_classifier.py - Bộ kiểm thử toàn diện cho Module 0: Query Complexity Classifier.

Bao gồm:
1. Unit tests từng đặc trưng (Feature extraction: single/multi-issue, multi-condition, multi-doc, cross-ref, temporal, calculation, ambiguity).
2. Edge cases tests (Empty, whitespace, greeting, out-of-scope).
3. Classification tests trên 40+ câu hỏi kiểm định đại diện 3 nhóm (SIMPLE, MODERATE, COMPLEX).
4. Determinism test (Kiểm tra tính tất định 100% qua nhiều lần lặp).
5. Complex-to-Simple error rate test (Bảo đảm không bao giờ trượt từ COMPLEX sang SIMPLE).
"""

import pytest
from typing import List, Tuple

from Adaptive_RAG.classifier.schema import (
    ComplexityClass,
    RoutingStrategy,
    QueryComplexityFeatures,
    QueryComplexityResult,
)
from Adaptive_RAG.classifier.query_complexity_classifier import QueryComplexityClassifier


class TestQueryComplexityClassifier:
    """Tập kiểm thử toàn diện cho Query Complexity Classifier (Module 0)."""

    @pytest.fixture
    def classifier(self) -> QueryComplexityClassifier:
        return QueryComplexityClassifier()

    # =========================================================================
    # 1. UNIT TESTS: TỪNG ĐẶC TRƯNG RIÊNG LẺ (FEATURE EXTRACTION)
    # =========================================================================

    def test_feature_single_issue(self, classifier: QueryComplexityClassifier):
        """Kiểm tra nhận diện câu hỏi 1 vấn đề pháp lý đơn nhất."""
        q = "Thời giờ làm việc bình thường của người lao động tối đa bao nhiêu giờ trong một ngày?"
        feats = classifier.extract_features(q)
        assert feats.number_of_legal_issues == 1
        assert feats.multi_document is False
        assert feats.cross_reference is False

    def test_feature_multiple_issues(self, classifier: QueryComplexityClassifier):
        """Kiểm tra nhận diện câu hỏi kết hợp nhiều vấn đề pháp lý (làm việc + tiền lương + thai sản)."""
        q = "Lao động nữ mang thai có được làm việc vào ban đêm không và tiền lương làm thêm giờ được tính như thế nào?"
        feats = classifier.extract_features(q)
        assert feats.number_of_legal_issues >= 2
        assert feats.calculation_required is True

    def test_feature_multi_condition(self, classifier: QueryComplexityClassifier):
        """Kiểm tra nhận diện cấu trúc điều kiện phức hợp (nếu... thì... và...)."""
        q = "Nếu người lao động tự ý bỏ việc 5 ngày liên tục nhưng có lý do thiên tai thì có bị kỷ luật sa thải không?"
        feats = classifier.extract_features(q)
        assert feats.multi_condition is True

    def test_feature_cross_reference(self, classifier: QueryComplexityClassifier):
        """Kiểm tra nhận diện viện dẫn chéo giữa các Điều luật."""
        q = "Điều kiện hưởng lương hưu quy định tại khoản 2 Điều 169 và Điều 219 Bộ luật Lao động?"
        feats = classifier.extract_features(q)
        assert feats.cross_reference is True
        assert len(feats.detected_articles) >= 2

    def test_feature_temporal_condition(self, classifier: QueryComplexityClassifier):
        """Kiểm tra nhận diện điều kiện ràng buộc mốc thời gian."""
        q = "Người lao động trong thời gian thử việc 30 ngày có được hưởng nguyên lương vào ngày nghỉ lễ không?"
        feats = classifier.extract_features(q)
        assert feats.temporal_condition is True

    def test_feature_calculation_required(self, classifier: QueryComplexityClassifier):
        """Kiểm tra nhận diện yêu cầu tính toán số học / tỷ lệ phần trăm."""
        q = "Cách tính tiền lương làm thêm giờ vào ban đêm ngày nghỉ lễ bằng bao nhiêu phần trăm?"
        feats = classifier.extract_features(q)
        assert feats.calculation_required is True

    def test_feature_multi_document(self, classifier: QueryComplexityClassifier):
        """Kiểm tra nhận diện câu hỏi đòi hỏi đối chiếu giữa 2 văn bản quy phạm."""
        q = "So sánh quy định về thời giờ làm việc giữa Bộ luật Lao động 2019 và Nghị định 145/2020"
        feats = classifier.extract_features(q)
        assert feats.multi_document is True
        assert len(feats.detected_documents) >= 1

    def test_feature_ambiguity(self, classifier: QueryComplexityClassifier):
        """Kiểm tra nhận diện câu hỏi mơ hồ, đàm thoại, từ vựng đời thường."""
        q = "Cho em hỏi ad ơi, bị đuổi việc thì làm sao nhỉ?"
        feats = classifier.extract_features(q)
        assert feats.ambiguity is True

    # =========================================================================
    # 2. EDGE CASES TESTS
    # =========================================================================

    def test_edge_empty_query(self, classifier: QueryComplexityClassifier):
        """Kiểm tra xử lý câu hỏi rỗng."""
        res = classifier.classify("")
        assert res.complexity == ComplexityClass.SIMPLE
        assert res.recommended_strategy == RoutingStrategy.DIRECT_RAG
        assert "rỗng" in res.reasons[0].lower()

    def test_edge_whitespace_query(self, classifier: QueryComplexityClassifier):
        """Kiểm tra xử lý câu hỏi chỉ có khoảng trắng."""
        res = classifier.classify("   \n\t  ")
        assert res.complexity == ComplexityClass.SIMPLE
        assert res.recommended_strategy == RoutingStrategy.DIRECT_RAG

    def test_edge_greeting_query(self, classifier: QueryComplexityClassifier):
        """Kiểm tra xử lý câu hỏi chào hỏi / xã giao."""
        greetings = ["Xin chào bạn", "Hello ad", "Cảm ơn bạn nhiều nhé"]
        for g in greetings:
            res = classifier.classify(g)
            assert res.complexity == ComplexityClass.SIMPLE
            assert res.recommended_strategy == RoutingStrategy.DIRECT_RAG
            assert res.features["is_greeting"] is True

    def test_edge_out_of_scope_query(self, classifier: QueryComplexityClassifier):
        """Kiểm tra nhận diện câu hỏi ngoài phạm vi pháp luật lao động."""
        oos_queries = [
            "Hồ sơ xin cấp visa du lịch Schengen gồm những gì?",
            "Mức phạt người đi xe máy vượt đèn đỏ theo luật giao thông?",
            "Công thức nấu nước dùng phở bò Hà Nội chuẩn vị?",
            "Biểu thuế chuyển nhượng chứng khoán hiện hành?"
        ]
        for q in oos_queries:
            res = classifier.classify(q)
            assert res.complexity == ComplexityClass.SIMPLE
            assert res.recommended_strategy == RoutingStrategy.DIRECT_RAG
            assert res.features["is_out_of_scope"] is True

    # =========================================================================
    # 3. CLASSIFICATION TESTS TRÊN TẬP 40+ CÂU HỎI ĐẠI DIỆN 3 LỚP
    # =========================================================================

    @pytest.mark.parametrize("query", [
        # Nhóm SIMPLE: 1 vấn đề pháp lý, 1 điều/khoản trực tiếp, direct retrieval
        "Thời giờ làm việc bình thường của người lao động được quy định tối đa bao nhiêu giờ trong một ngày?",
        "Thời gian nghỉ giữa giờ trong ca làm việc bình thường là bao nhiêu phút?",
        "Tuổi nghỉ hưu của người lao động trong điều kiện lao động bình thường?",
        "Thời hạn của hợp đồng lao động xác định thời hạn tối đa là bao nhiêu tháng?",
        "Mức lương tối thiểu vùng hiện nay do cơ quan nào công bố?",
        "Người lao động được nghỉ bao nhiêu ngày khi kết hôn?",
        "Tiền lương làm việc vào ban đêm được trả thêm ít nhất bao nhiêu phần trăm?",
        "Định nghĩa về quấy rối tình dục tại nơi làm việc trong Bộ luật Lao động?",
        "Hình thức xử lý kỷ luật kéo dài thời hạn nâng lương không quá bao nhiêu tháng?",
        "Điều 125 Bộ luật Lao động 2019 quy định về nội dung gì?",
        "Mức đóng bảo hiểm y tế của người lao động là bao nhiêu phần trăm?",
        "Thời hiệu xử lý kỷ luật lao động tối đa là bao nhiêu tháng?",
    ])
    def test_classification_simple_queries(self, classifier: QueryComplexityClassifier, query: str):
        res = classifier.classify(query)
        assert res.complexity == ComplexityClass.SIMPLE
        assert res.recommended_strategy == RoutingStrategy.DIRECT_RAG
        assert res.confidence >= 0.85
        assert len(res.reasons) > 0

    @pytest.mark.parametrize("query", [
        # Nhóm MODERATE: Nhiều điều kiện tình huống, thủ tục, cần CRAG thẩm định bằng chứng
        "Người lao động thử việc có được hưởng lương trong thời gian thử việc không?",
        "Trình tự, thủ tục các bước tiến hành xử lý kỷ luật sa thải người lao động theo quy định?",
        "Người lao động có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước trong trường hợp nào?",
        "Thủ tục đăng ký nội quy lao động tại cơ quan chuyên môn về lao động cấp tỉnh gồm những gì?",
        "Người lao động có được tạm hoãn thực hiện hợp đồng lao động khi phải thực hiện nghĩa vụ quân sự không?",
        "Trong trường hợp người sử dụng lao động không trả lương đúng hạn thì người lao động có quyền gì?",
        "Cho em hỏi ad ơi, người lao động bị đuổi việc thì công ty phải báo trước mấy ngày ạ?",
        "Điều kiện để người sử dụng lao động được chuyển người lao động làm công việc khác so với hợp đồng lao động?",
        "Thời hạn giải quyết quyền lợi của người lao động kể từ ngày chấm dứt hợp đồng lao động?",
        "Quy trình xử lý tai nạn lao động tại cơ sở sản xuất kinh doanh gồm các bước nào?",
        "Người lao động làm công việc nặng nhọc, độc hại được nghỉ hằng năm tăng thêm bao nhiêu ngày?",
        "Thủ tục cấp lại giấy phép lao động cho người lao động nước ngoài hết hạn?",
    ])
    def test_classification_moderate_queries(self, classifier: QueryComplexityClassifier, query: str):
        res = classifier.classify(query)
        assert res.complexity == ComplexityClass.MODERATE
        assert res.recommended_strategy == RoutingStrategy.CRAG
        assert res.confidence >= 0.80

    @pytest.mark.parametrize("query", [
        # Nhóm COMPLEX: Đa văn bản, viện dẫn chéo, câu hỏi kép đa vấn đề, tính toán phức hợp
        "Người lao động nữ đang mang thai có được làm thêm giờ vào ban đêm không, và nếu được thì tiền lương được tính như thế nào?",
        "So sánh quy định về thời giờ làm việc và làm thêm giờ giữa Bộ luật Lao động 2019 và Nghị định 145/2020/NĐ-CP?",
        "Người lao động vừa tự ý bỏ việc 5 ngày cộng dồn vừa đang nuôi con nhỏ dưới 12 tháng thì người sử dụng lao động có được áp dụng sa thải không và phải xử lý như thế nào?",
        "Cách tính tiền lương làm thêm giờ vào ban đêm ngày nghỉ lễ tết trùng với ngày nghỉ hằng tuần?",
        "Đối chiếu quy định tại Điều 169 và Điều 219 Bộ luật Lao động 2019 về điều kiện và tuổi nghỉ hưu của lao động nữ?",
        "Mức xử phạt vi phạm hành chính đối với hành vi cưỡng bức lao động theo Nghị định 12/2022 và các trường hợp bị truy cứu trách nhiệm hình sự?",
        "Hồ sơ, thủ tục cấp giấy phép lao động cho chuyên gia nước ngoài theo Nghị định 152/2020 và Nghị định 70/2023 sửa đổi?",
        "Nếu người lao động bị tai nạn lao động suy giảm khả năng lao động 35% thì trách nhiệm bồi thường của người sử dụng lao động và chế độ bảo hiểm xã hội được tính như thế nào?",
        "Trường hợp chấm dứt hợp đồng lao động do thay đổi cơ cấu công nghệ thì quy trình xây dựng phương án sử dụng lao động và mức trợ cấp mất việc làm được tính ra sao?",
        "Người lao động làm công việc đặc biệt nặng nhọc độc hại theo Thông tư 09/2020 thì tuổi nghỉ hưu thấp hơn tối đa bao nhiêu tuổi và mức lương hưu tính theo quy định nào?",
        "Quy định về thời giờ làm việc ban đêm, số giờ làm thêm tối đa và cách tính lương tăng ca cho lao động chưa thành niên?",
        "Điều kiện thành lập tổ chức của người lao động tại doanh nghiệp và quan hệ với tổ chức Công đoàn theo Bộ luật Lao động và các văn bản hướng dẫn?",
    ])
    def test_classification_complex_queries(self, classifier: QueryComplexityClassifier, query: str):
        res = classifier.classify(query)
        assert res.complexity == ComplexityClass.COMPLEX
        assert res.recommended_strategy == RoutingStrategy.DECOMPOSITION_CRAG
        assert res.confidence >= 0.85

    # =========================================================================
    # 4. DETERMINISM TEST: TÍNH TẤT ĐỊNH 100%
    # =========================================================================

    def test_determinism_consistency(self, classifier: QueryComplexityClassifier):
        """Kiểm tra tính tất định: cùng query chạy 10 lần liên tiếp phải cho 10 kết quả giống hệt nhau."""
        test_queries = [
            "Thời giờ làm việc bình thường trong 01 ngày?",
            "Thủ tục sa thải người lao động gồm những bước nào?",
            "Lao động nữ mang thai làm thêm ban đêm và tiền lương tính thế nào giữa BLLD và Nghị định 145?",
        ]

        for q in test_queries:
            first_res = classifier.classify(q)
            for _ in range(9):
                rep_res = classifier.classify(q)
                assert rep_res.complexity == first_res.complexity
                assert rep_res.confidence == first_res.confidence
                assert rep_res.recommended_strategy == first_res.recommended_strategy
                assert rep_res.reasons == first_res.reasons
                assert rep_res.features == first_res.features

    # =========================================================================
    # 5. COMPLEX-TO-SIMPLE SAFETY ERROR RATE TEST
    # =========================================================================

    def test_complex_to_simple_error_rate_is_strictly_zero(self, classifier: QueryComplexityClassifier):
        """Bảo đảm Complex-to-Simple Error Rate = 0%: Không một câu phức tạp nào bị phân loại thành SIMPLE."""
        complex_samples = [
            "So sánh BLLD 2019 và Nghị định 145/2020 về thời giờ làm việc?",
            "Điều 169 và Điều 219 quy định về tuổi nghỉ hưu ra sao?",
            "Lao động nữ vừa nuôi con nhỏ vừa bỏ việc thì sa thải thế nào và tiền lương tính ra sao?",
            "Cách tính tiền lương làm thêm giờ ban đêm ngày lễ tết?",
            "Thủ tục cấp phép lao động nước ngoài theo Nghị định 152 và Nghị định 70?",
            "Người lao động bị tai nạn lao động 35% thì trợ cấp thôi việc và bồi thường thế nào?",
        ]

        for q in complex_samples:
            res = classifier.classify(q)
            assert res.complexity != ComplexityClass.SIMPLE, f"NGUY HIỂM: Câu phức tạp '{q}' bị phân loại nhầm thành SIMPLE!"
            assert res.complexity == ComplexityClass.COMPLEX
