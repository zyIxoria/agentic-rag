"""
Unit tests for LegalToolRegistry and Function Calling Schemas.
"""

import unittest
from unittest.mock import MagicMock
from Adaptive_RAG.agent.tool_registry import LegalToolRegistry, LEGAL_TOOL_DEFINITIONS
from RAG.retriever.schema import RetrievedChunk


class TestLegalToolRegistry(unittest.TestCase):
    def setUp(self):
        self.mock_retriever = MagicMock()
        self.mock_web_searcher = MagicMock()
        self.registry = LegalToolRegistry(
            retriever=self.mock_retriever,
            web_searcher=self.mock_web_searcher,
        )

    def test_schema_formats(self):
        """Kiểm tra đặc tả schema chuẩn OpenAI và Gemini."""
        openai_tools = LegalToolRegistry.get_openai_tools()
        gemini_tools = LegalToolRegistry.get_gemini_tools()

        self.assertEqual(len(openai_tools), len(LEGAL_TOOL_DEFINITIONS))
        self.assertEqual(len(gemini_tools), len(LEGAL_TOOL_DEFINITIONS))

        # Kiểm tra cấu trúc OpenAI
        self.assertEqual(openai_tools[0]["type"], "function")
        self.assertIn("name", openai_tools[0]["function"])
        self.assertIn("parameters", openai_tools[0]["function"])

        # Kiểm tra danh sách tên các công cụ bắt buộc
        tool_names = [t["name"] for t in gemini_tools]
        self.assertIn("retrieve_legal_doc", tool_names)
        self.assertIn("calculate_overtime_pay", tool_names)
        self.assertIn("calculate_severance_or_redundancy", tool_names)
        self.assertIn("calculate_work_accident_benefit", tool_names)
        self.assertIn("calculate_unemployment_benefit", tool_names)
        self.assertIn("web_search_fallback", tool_names)
        self.assertIn("ask_clarification", tool_names)

    def test_execute_calculate_overtime_pay(self):
        """Kiểm tra thực thi công cụ calculate_overtime_pay."""
        res = self.registry.execute_tool(
            "calculate_overtime_pay",
            {"hourly_wage": 50000, "hours": 4, "day_type": "weekend", "is_night": True},
        )
        self.assertTrue(res.success)
        self.assertIsNotNone(res.data)
        # 50,000 * 4 * 270% = 540,000
        self.assertEqual(res.data.total_amount_vnd, 540000.0)
        self.assertIn("270", res.output_text)

    def test_execute_calculate_severance(self):
        """Kiểm tra thực thi công cụ calculate_severance_or_redundancy."""
        res = self.registry.execute_tool(
            "calculate_severance_or_redundancy",
            {
                "avg_monthly_salary_6m": 12000000,
                "total_months_worked": 40,
                "months_bhtn_participated": 16,
                "allowance_type": "thoi_viec",
            },
        )
        self.assertTrue(res.success)
        # 40 - 16 = 24 tháng = 2.0 năm -> 2.0 * 0.5 * 12tr = 12tr
        self.assertEqual(res.data.total_amount_vnd, 12000000.0)

    def test_execute_calculate_work_accident(self):
        """Kiểm tra thực thi công cụ calculate_work_accident_benefit."""
        res = self.registry.execute_tool(
            "calculate_work_accident_benefit",
            {
                "monthly_salary": 10000000,
                "impairment_percentage": 14,
                "is_worker_fault": False,
            },
        )
        self.assertTrue(res.success)
        # 1.5 + (14-10)*0.4 = 3.1 tháng -> 31,000,000
        self.assertEqual(res.data.total_amount_vnd, 31000000.0)

    def test_execute_retrieve_legal_doc(self):
        """Kiểm tra thực thi công cụ retrieve_legal_doc qua mock retriever."""
        mock_chunk = RetrievedChunk(
            chunk_id="BLLD_2019_D98",
            content="Người lao động làm thêm giờ được trả lương tính theo đơn giá...",
            score=0.89,
            rank=1,
            metadata={
                "document_name": "Bộ luật Lao động 2019",
                "article": "Điều 98",
                "title": "Tiền lương làm thêm giờ",
            },
        )
        self.mock_retriever.retrieve.return_value = [mock_chunk]

        res = self.registry.execute_tool(
            "retrieve_legal_doc",
            {"query": "tiền lương làm thêm giờ", "top_k": 3},
        )
        self.assertTrue(res.success)
        self.assertEqual(len(res.data), 1)
        self.assertIn("Điều 98", res.output_text)

    def test_execute_ask_clarification(self):
        """Kiểm tra công cụ ask_clarification."""
        res = self.registry.execute_tool(
            "ask_clarification",
            {
                "missing_info": ["mức lương theo HĐLĐ", "ca làm việc ban ngày hay ban đêm"],
                "clarification_question": "Bạn vui lòng cung cấp thêm mức lương và thời gian làm thêm?",
            },
        )
        self.assertTrue(res.success)
        self.assertIn("YÊU CẦU LÀM RÕ DỮ KIỆN", res.output_text)

    def test_unknown_tool_handling(self):
        """Kiểm tra xử lý an toàn khi gọi công cụ không tồn tại."""
        res = self.registry.execute_tool("non_existent_tool", {})
        self.assertFalse(res.success)
        self.assertIn("không tồn tại", res.output_text)


if __name__ == "__main__":
    unittest.main()
