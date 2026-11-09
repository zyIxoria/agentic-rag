"""
test_context_and_scope_classifier.py - Bộ kiểm thử nâng cấp phân loại ngữ cảnh & phạm vi câu hỏi (Module 0).

Bao hàm 7 nhóm kiểm thử chuẩn theo đặc tả:
1. Trường hợp A: Câu hỏi pháp luật lao động trực tiếp thuộc phạm vi (Direct In-Scope).
2. Trường hợp B: Câu hỏi tiếp nối cần sử dụng lịch sử hội thoại (Follow-up Queries with Context).
3. Trường hợp C: Chuyển chủ đề đột ngột (Topic Switch - không được ép thành in-scope).
4. Trường hợp D: Có từ khóa trùng nhau nhưng khác ngữ nghĩa (Semantic Disambiguation).
5. Trường hợp E: Câu hỏi ngoài phạm vi hoàn toàn (Explicit Out-of-Scope).
6. Trường hợp F: Câu hỏi pháp luật dùng từ đời thường, không chứa từ khóa pháp lý chuẩn.
7. Trường hợp G: Chuỗi hội thoại nhiều lượt liên tục (Multi-turn Conversation Threads).
"""

import unittest
from Adaptive_RAG.classifier.hybrid_classifier import HybridQueryClassifier
from Adaptive_RAG.classifier.schema import (
    ComplexityLevel,
    QueryIntent,
    RoutingDecision,
)


class TestContextAndScopeClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = HybridQueryClassifier()

    # =========================================================================
    # 1. TRƯỜNG HỢP A: CÂU HỎI PHÁP LUẬT LAO ĐỘNG TRỰC TIẾP
    # =========================================================================
    def test_case_a_direct_in_scope(self):
        """Kiểm tra các câu hỏi pháp luật lao động trực tiếp."""
        queries = [
            "Lương tối thiểu vùng hiện nay là bao nhiêu?",
            "Người lao động được nghỉ phép năm bao nhiêu ngày?",
            "Công ty có được đơn phương chấm dứt hợp đồng không?",
            "Thời gian thử việc đối với vị trí cử nhân đại học là bao lâu?",
            "Mức trợ cấp thôi việc được tính như thế nào?",
        ]
        for q in queries:
            res = self.classifier.classify(q)
            self.assertNotEqual(res.intent, QueryIntent.OUT_OF_SCOPE, f"Failed for query: {q}")
            self.assertNotEqual(res.suggested_route, RoutingDecision.DIRECT_REFUSAL, f"Failed for query: {q}")
            self.assertIn(res.suggested_route, [
                RoutingDecision.TRADITIONAL_RAG,
                RoutingDecision.CORRECTIVE_RAG,
                RoutingDecision.DECOMPOSE_AGENTIC,
            ])

    # =========================================================================
    # 2. TRƯỜNG HỢP B: CÂU HỎI TIẾP NỐI (FOLLOW-UP QUERIES WITH CONTEXT)
    # =========================================================================
    def test_case_b_followup_with_context(self):
        """Kiểm tra câu hỏi tiếp nối kế thừa ngữ cảnh hợp lệ từ câu trước."""
        history = [
            {"role": "user", "content": "Người lao động được nghỉ phép năm bao nhiêu ngày?"},
            {"role": "assistant", "content": "Theo quy định tại Điều 113 BLLĐ 2019, người lao động làm đủ 12 tháng được nghỉ 12 ngày phép năm."},
        ]

        follow_up_queries = [
            "Còn nếu làm được 3 năm?",
            "Vậy trường hợp đó thì sao?",
            "Có cần báo trước không?",
            "Thế công ty có phải bồi thường không?",
            "Nếu người lao động không đồng ý thì sao?",
            "Mức phạt là bao nhiêu?",
            "Quy định ở điều nào?",
            "Thời hạn bao lâu?",
        ]

        for q in follow_up_queries:
            res = self.classifier.classify(q, chat_history=history)
            self.assertNotEqual(res.intent, QueryIntent.OUT_OF_SCOPE, f"Followup should be in-scope: {q}")
            self.assertNotEqual(res.suggested_route, RoutingDecision.DIRECT_REFUSAL, f"Followup should not be refused: {q}")
            self.assertIn("tiếp nối", res.reasoning.lower(), f"Reasoning should mention followup: {res.reasoning}")

    # =========================================================================
    # 3. TRƯỜNG HỢP C: CHUYỂN CHỦ ĐỀ ĐỘT NGỘT (TOPIC SWITCH)
    # =========================================================================
    def test_case_c_topic_switch_not_forced_in_scope(self):
        """Dù câu trước là pháp luật lao động, câu sau chuyển sang ăn uống/thời tiết thì BẮT BUỘC là OUT_OF_SCOPE."""
        history = [
            {"role": "user", "content": "Người lao động được nghỉ phép năm bao nhiêu ngày?"},
            {"role": "assistant", "content": "Được 12 ngày làm việc trong điều kiện bình thường."},
        ]

        switched_queries = [
            "Hôm nay ăn gì?",
            "Thời tiết ngày mai có mưa không?",
            "Viết cho tôi một hàm Python tính giai thừa",
            "Nghỉ chơi ở đâu cuối tuần này?",
            "Tối nay có trận bóng đá nào hay không?",
        ]

        for q in switched_queries:
            res = self.classifier.classify(q, chat_history=history)
            self.assertEqual(res.intent, QueryIntent.OUT_OF_SCOPE, f"Topic switch query must be OUT_OF_SCOPE: {q}")
            self.assertEqual(res.suggested_route, RoutingDecision.DIRECT_REFUSAL, f"Must route to DIRECT_REFUSAL: {q}")

    # =========================================================================
    # 4. TRƯỜNG HỢP D: TỪ KHÓA TRÙNG NHAU NHƯNG KHÁC NGỮ NGHĨA (DISAMBIGUATION)
    # =========================================================================
    def test_case_d_semantic_disambiguation(self):
        """Khử nhập nhằng từ vựng: cùng từ nhưng khác ý nghĩa."""
        # Cặp 1: "Lương" (Tiền lương vs Lương thực)
        res_salary = self.classifier.classify("Lương tối thiểu vùng là bao nhiêu?")
        self.assertNotEqual(res_salary.intent, QueryIntent.OUT_OF_SCOPE)
        self.assertNotEqual(res_salary.suggested_route, RoutingDecision.DIRECT_REFUSAL)

        res_food = self.classifier.classify("Lương thực nấu món gì ngon?")
        self.assertEqual(res_food.intent, QueryIntent.OUT_OF_SCOPE)
        self.assertEqual(res_food.suggested_route, RoutingDecision.DIRECT_REFUSAL)

        # Cặp 2: "Nghỉ" (Nghỉ phép vs Nghỉ chơi)
        res_leave = self.classifier.classify("Nghỉ phép năm được bao nhiêu ngày?")
        self.assertNotEqual(res_leave.intent, QueryIntent.OUT_OF_SCOPE)
        self.assertNotEqual(res_leave.suggested_route, RoutingDecision.DIRECT_REFUSAL)

        res_play = self.classifier.classify("Nghỉ chơi ở đâu cuối tuần?")
        self.assertEqual(res_play.intent, QueryIntent.OUT_OF_SCOPE)
        self.assertEqual(res_play.suggested_route, RoutingDecision.DIRECT_REFUSAL)

        # Cặp 3: "Bảo hiểm" (BHXH vs Bảo hiểm xe máy)
        res_bhxh = self.classifier.classify("Mức đóng bảo hiểm xã hội bắt buộc của người lao động")
        self.assertNotEqual(res_bhxh.intent, QueryIntent.OUT_OF_SCOPE)

        res_bike = self.classifier.classify("Mua bảo hiểm xe máy giá bao nhiêu?")
        self.assertEqual(res_bike.intent, QueryIntent.OUT_OF_SCOPE)

        # Cặp 4: "Hợp đồng" (HĐLĐ vs Hợp đồng thuê nhà)
        res_hdld = self.classifier.classify("Thời hạn hợp đồng lao động tối đa bao nhiêu tháng?")
        self.assertNotEqual(res_hdld.intent, QueryIntent.OUT_OF_SCOPE)

        res_rent = self.classifier.classify("Mẫu hợp đồng thuê nhà nguyên căn 2 năm")
        self.assertEqual(res_rent.intent, QueryIntent.OUT_OF_SCOPE)

    # =========================================================================
    # 5. TRƯỜNG HỢP E: NGOÀI PHẠM VI HOÀN TOÀN
    # =========================================================================
    def test_case_e_explicit_out_of_scope(self):
        """Các chủ đề ngoài phạm vi hoàn toàn phải bị từ chối cửa ngõ."""
        queries = [
            "Công thức nấu món phở bò Nam Định",
            "Mức xử phạt tài xế ô tô vi phạm nồng độ cồn kịch khung",
            "Thủ tục ly hôn đơn phương giành quyền nuôi con",
            "Hướng dẫn lập trình web bằng React và Vite",
            "Giải phương trình bậc 2 có 2 nghiệm phân biệt",
            "Giá vé máy bay đi du lịch Đà Nẵng",
        ]
        for q in queries:
            res = self.classifier.classify(q)
            self.assertEqual(res.intent, QueryIntent.OUT_OF_SCOPE, f"Should be OUT_OF_SCOPE: {q}")
            self.assertEqual(res.suggested_route, RoutingDecision.DIRECT_REFUSAL, f"Should be DIRECT_REFUSAL: {q}")

    # =========================================================================
    # 6. TRƯỜNG HỢP F: CÂU HỎI PHÁP LUẬT DÙNG TỪ ĐỜI THƯỜNG
    # =========================================================================
    def test_case_f_informal_labor_queries(self):
        """Câu hỏi pháp luật không chứa số điều nhưng diễn đạt quan hệ lao động vẫn phải in_scope."""
        queries = [
            "Bị sếp đuổi việc vô cớ thì kiện ở đâu?",
            "Công ty bắt làm thêm ca đêm không trả tiền thì phải làm sao?",
            "Đi làm thử 2 tháng không trả một đồng lương nào có đúng không?",
            "Nghỉ đẻ xong đi làm lại có bị trừ lương không?",
            "Làm việc ở xưởng bị máy dập đứt ngón tay có được bồi thường không?",
        ]
        for q in queries:
            res = self.classifier.classify(q)
            self.assertNotEqual(res.intent, QueryIntent.OUT_OF_SCOPE, f"Informal labor query should be IN_SCOPE: {q}")
            self.assertNotEqual(res.suggested_route, RoutingDecision.DIRECT_REFUSAL, f"Should not refuse: {q}")

    # =========================================================================
    # 7. TRƯỜNG HỢP G: CHUỖI HỘI THOẠI NHIỀU LƯỢT (MULTI-TURN THREAD)
    # =========================================================================
    def test_case_g_multi_turn_conversation_thread(self):
        """Kiểm tra một chuỗi hội thoại thực tế diễn ra qua nhiều lượt hỏi."""
        history = []

        # Lượt 1: Hỏi về thử việc -> in_scope
        q1 = "Thời gian thử việc tối đa là bao lâu?"
        r1 = self.classifier.classify(q1, chat_history=history)
        self.assertEqual(r1.intent, QueryIntent.LEGAL_DIRECT_DEFINITION)
        self.assertEqual(r1.suggested_route, RoutingDecision.TRADITIONAL_RAG)
        history.append({"role": "user", "content": q1})
        history.append({"role": "assistant", "content": "Thời gian thử việc tối đa 180 ngày đối với quản lý, 60 ngày đối với đại học."})

        # Lượt 2: Câu hỏi tiếp nối -> in_scope nhờ history
        q2 = "Còn nếu không đạt thì công ty có phải báo trước không?"
        r2 = self.classifier.classify(q2, chat_history=history)
        self.assertNotEqual(r2.intent, QueryIntent.OUT_OF_SCOPE)
        self.assertIn(r2.suggested_route, [RoutingDecision.TRADITIONAL_RAG, RoutingDecision.CORRECTIVE_RAG])
        history.append({"role": "user", "content": q2})
        history.append({"role": "assistant", "content": "Trong thời gian thử việc, mỗi bên có quyền hủy bỏ thỏa thuận mà không cần báo trước."})

        # Lượt 3: Chuyển chủ đề đột ngột sang ăn trưa -> OUT_OF_SCOPE
        q3 = "Trưa nay ăn gì ngon gần công ty?"
        r3 = self.classifier.classify(q3, chat_history=history)
        self.assertEqual(r3.intent, QueryIntent.OUT_OF_SCOPE)
        self.assertEqual(r3.suggested_route, RoutingDecision.DIRECT_REFUSAL)
        history.append({"role": "user", "content": q3})
        history.append({"role": "assistant", "content": "Xin lỗi, tôi chỉ hỗ trợ pháp luật lao động."})

        # Lượt 4: Quay lại pháp luật lao động -> in_scope
        q4 = "Thế công ty có phải đóng bảo hiểm xã hội trong thời gian thử việc không?"
        r4 = self.classifier.classify(q4, chat_history=history)
        self.assertNotEqual(r4.intent, QueryIntent.OUT_OF_SCOPE)
        self.assertIn(r4.suggested_route, [RoutingDecision.TRADITIONAL_RAG, RoutingDecision.CORRECTIVE_RAG])

    def test_latency_under_10ms(self):
        """Kiểm tra độ trễ phân loại khi có ngữ cảnh lịch sử vẫn phải siêu nhanh (< 10ms)."""
        history = [
            {"role": "user", "content": "Người lao động được nghỉ phép năm bao nhiêu ngày?"},
            {"role": "assistant", "content": "Được 12 ngày phép năm."},
        ]
        res = self.classifier.classify("Còn nếu làm được 5 năm thì sao?", chat_history=history)
        self.assertLess(res.latency_ms, 10.0)


if __name__ == "__main__":
    unittest.main()
