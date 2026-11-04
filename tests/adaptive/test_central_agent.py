"""
Unit tests for Central Autonomous ReAct Agent and Controller.
"""

import unittest
from unittest.mock import MagicMock
from Adaptive_RAG.agent.central_agent import CentralAgentController, AgentResponse
from Adaptive_RAG.agent.tool_registry import LegalToolRegistry
from Adaptive_RAG.agent.prompts import (
    build_react_agent_prompt,
    parse_react_action,
    CENTRAL_AGENT_SYSTEM_PROMPT,
)
from RAG.retriever.schema import RetrievedChunk


class TestCentralAgent(unittest.TestCase):
    def setUp(self):
        self.mock_retriever = MagicMock()
        mock_chunk = RetrievedChunk(
            chunk_id="BLLD_2019_D98",
            content="Điều 98. Tiền lương làm thêm giờ, làm việc vào ban đêm...",
            score=0.91,
            rank=1,
            metadata={
                "document_name": "Bộ luật Lao động 2019",
                "article": "Điều 98",
                "title": "Tiền lương làm thêm giờ",
            },
        )
        self.mock_retriever.retrieve.return_value = [mock_chunk]

        self.registry = LegalToolRegistry(retriever=self.mock_retriever)
        self.agent = CentralAgentController(tool_registry=self.registry)

    def test_react_prompt_builder_and_action_parser(self):
        """Kiểm tra xây dựng prompt ReAct và parse action/input."""
        prompt = build_react_agent_prompt(
            query="Tôi làm thêm 2 giờ ban đêm ngày nghỉ tuần được bao nhiêu tiền?",
            scratchpad="Thought: Cần tính tiền lương\n",
            tool_descriptions="- calculate_overtime_pay: tính lương",
        )
        self.assertIn("BỘ LUẬT LAO ĐỘNG", prompt.upper())
        self.assertIn("calculate_overtime_pay", prompt)

        # Test parser Action & Input
        sample_llm_step = (
            'Thought: Cần gọi công cụ tính tiền lương làm thêm giờ.\n'
            'Action: calculate_overtime_pay\n'
            'Action Input: {"hourly_wage": 60000, "hours": 3, "day_type": "weekend", "is_night": true}\n'
        )
        action_name, action_args, final_ans = parse_react_action(sample_llm_step)
        self.assertEqual(action_name, "calculate_overtime_pay")
        self.assertEqual(action_args["hourly_wage"], 60000)
        self.assertEqual(action_args["hours"], 3)
        self.assertTrue(action_args["is_night"])
        self.assertIsNone(final_ans)

        # Test parser Final Answer
        sample_llm_final = "Thought: Đã xong.\nFinal Answer: Người lao động được nhận 486.000 VNĐ."
        action_name, action_args, final_ans = parse_react_action(sample_llm_final)
        self.assertIsNone(action_name)
        self.assertEqual(final_ans, "Người lao động được nhận 486.000 VNĐ.")

    def test_overtime_calculation_agent_flow(self):
        """Kiểm tra chu trình ReAct tự chủ khi người dùng hỏi bài toán tính tiền làm thêm giờ."""
        query = "Lương tôi 50.000 đồng/giờ, tôi làm thêm 3 giờ ban đêm vào ngày nghỉ hàng tuần thì được bao nhiêu tiền?"
        resp: AgentResponse = self.agent.run(query)

        self.assertIsInstance(resp, AgentResponse)
        self.assertIn("calculate_overtime_pay", resp.tools_called)
        self.assertGreater(len(resp.steps), 0)
        # 50,000 * 3 * 270% = 405,000 VNĐ
        self.assertIn("405,000", resp.answer)
        self.assertIn("Điều 98", " ".join(resp.citations))

    def test_severance_calculation_agent_flow(self):
        """Kiểm tra chu trình ReAct khi hỏi tính trợ cấp thôi việc."""
        query = "Tôi làm việc được 4 năm, mức lương 10 triệu đồng/tháng, khi nghỉ việc được trợ cấp thôi việc bao nhiêu?"
        resp: AgentResponse = self.agent.run(query)

        self.assertIsInstance(resp, AgentResponse)
        self.assertIn("calculate_severance_or_redundancy", resp.tools_called)
        # 4 năm * 0.5 tháng * 10 triệu = 20 triệu
        self.assertIn("20,000,000", resp.answer)
        self.assertIn("Điều 46", " ".join(resp.citations))

    def test_general_legal_question_flow(self):
        """Kiểm tra xử lý câu hỏi pháp lý chung có gọi retrieve_legal_doc."""
        query = "Thời giờ làm việc bình thường theo luật là bao nhiêu giờ?"
        resp: AgentResponse = self.agent.run(query)

        self.assertIsInstance(resp, AgentResponse)
        self.assertIn("retrieve_legal_doc", resp.tools_called)
        self.assertGreater(len(resp.steps), 0)


if __name__ == "__main__":
    unittest.main()
