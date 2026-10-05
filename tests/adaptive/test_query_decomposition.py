"""
test_query_decomposition.py - Unit test suite cho Query Decomposition & Sub-query Planner (RAG-16).
"""

import unittest
from Adaptive_RAG.decomposition.legal_decomposer import LegalQueryDecomposer
from Adaptive_RAG.decomposition.schema import ExecutionStrategy


class TestQueryDecomposition(unittest.TestCase):
    def setUp(self):
        self.decomposer = LegalQueryDecomposer()

    def test_decompose_multi_document(self):
        """Kiểm tra phân rã câu hỏi liên văn bản thành 2 sub-queries tương ứng."""
        q = "So sánh quy định về thời gian thử việc giữa Bộ luật Lao động 2019 và Nghị định 145/2020"
        plan = self.decomposer.decompose(q)

        self.assertEqual(len(plan.sub_queries), 2)
        self.assertEqual(plan.strategy, ExecutionStrategy.PARALLEL)
        self.assertTrue(any("Bộ luật Lao động" in sq.text for sq in plan.sub_queries))
        self.assertTrue(any("Nghị định 145/2020" in sq.text for sq in plan.sub_queries))
        self.assertIn("Tổng hợp và so sánh", plan.synthesis_instruction)

    def test_decompose_contrastive_conditional(self):
        """Kiểm tra phân rã câu hỏi mâu thuẫn/điều kiện đặc thù (sa thải vs thai sản)."""
        q = "Người lao động tự ý bỏ việc 5 ngày nhưng đang mang thai thì có bị sa thải không và công ty phải xử lý như thế nào?"
        plan = self.decomposer.decompose(q)

        self.assertGreaterEqual(len(plan.sub_queries), 2)
        self.assertEqual(plan.strategy, ExecutionStrategy.HYBRID)
        # Kiểm tra sự hiện diện của điều kiện sa thải và điều kiện bảo vệ thai sản
        all_texts = " ".join(sq.text for sq in plan.sub_queries)
        self.assertIn("sa thải", all_texts.lower())
        self.assertTrue("mang thai" in all_texts.lower() or "thai sản" in all_texts.lower())

    def test_decompose_compound_question(self):
        """Kiểm tra phân rã câu hỏi kép kết hợp liên từ 'và'."""
        q = "Hồ sơ xin cấp lại giấy phép lao động như thế nào và có bị phạt tiền không?"
        plan = self.decomposer.decompose(q)

        self.assertEqual(len(plan.sub_queries), 2)
        self.assertEqual(plan.strategy, ExecutionStrategy.PARALLEL)
        self.assertIn("phạt tiền", plan.sub_queries[1].text.lower())

    def test_decompose_atomic_query(self):
        """Kiểm tra câu hỏi đơn giản không bị phân rã thừa."""
        q = "Điều 125 Bộ luật Lao động quy định gì?"
        plan = self.decomposer.decompose(q)

        self.assertEqual(len(plan.sub_queries), 1)
        self.assertEqual(plan.sub_queries[0].text, q)
        self.assertEqual(plan.strategy, ExecutionStrategy.PARALLEL)


if __name__ == "__main__":
    unittest.main()
