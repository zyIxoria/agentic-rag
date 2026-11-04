"""
Unit tests for Real-Time Hallucination Verifier and Faithfulness Gate.
"""

import unittest
from RAG.guards.hallucination_verifier import (
    RealTimeHallucinationVerifier,
    ClaimStatus,
    FaithfulnessVerificationReport,
)
from RAG.guards.refusal_guard import RefusalGuard, GuardCheckResult
from RAG.generator.schema import GenerationResult
from RAG.citation.schema import CitationResolutionResult, LegalCitation


class TestHallucinationVerifier(unittest.TestCase):
    def setUp(self):
        self.verifier = RealTimeHallucinationVerifier(faithfulness_threshold=0.65)
        self.guard = RefusalGuard(hallucination_verifier=self.verifier)

        self.context = (
            "[SOURCE 1] Bộ luật Lao động 2019 - Điều 25. Thời gian thử việc:\n"
            "Thời gian thử việc do hai bên thỏa thuận căn cứ vào tính chất và mức độ phức tạp của công việc "
            "nhưng chỉ được thử việc một lần đối với một công việc và bảo đảm điều kiện sau đây: "
            "1. Không quá 180 ngày đối với công việc của người quản lý doanh nghiệp; "
            "2. Không quá 60 ngày đối với công việc có chức danh nghề nghiệp cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên; "
            "3. Không quá 30 ngày đối với công việc có chức danh nghề nghiệp cần trình độ trung cấp."
        )

    def test_extract_claims(self):
        """Kiểm tra tách câu và bóc tách mệnh đề sự thật."""
        text = (
            "Xin chào bạn! Căn cứ theo Điều 25 Bộ luật Lao động 2019, thời gian thử việc tối đa là 180 ngày. "
            "Đối với người quản lý doanh nghiệp thì thời hạn không quá 180 ngày. Cảm ơn bạn!"
        )
        claims = self.verifier.extract_claims(text)
        self.assertGreaterEqual(len(claims), 1)
        self.assertFalse(any("xin chào" in c.lower() for c in claims))
        self.assertFalse(any("cảm ơn" in c.lower() for c in claims))

    def test_faithful_answer_verification(self):
        """Kiểm tra câu trả lời trung thực và có căn cứ trong tài liệu."""
        answer = (
            "Theo Điều 25 Bộ luật Lao động 2019, thời gian thử việc của người quản lý doanh nghiệp là không quá 180 ngày. "
            "Đối với công việc yêu cầu trình độ cao đẳng trở lên, thời gian thử việc tối đa là 60 ngày."
        )
        report: FaithfulnessVerificationReport = self.verifier.verify(answer, self.context)
        self.assertTrue(report.passed)
        self.assertGreaterEqual(report.faithfulness_score, 0.8)
        self.assertFalse(report.hallucination_detected)
        self.assertEqual(report.contradicted_count, 0)

    def test_hallucinated_article_rejection(self):
        """Kiểm tra phát hiện và chặn đứng bịa đặt số hiệu Điều luật."""
        answer = (
            "Căn cứ theo Điều 999 Bộ luật Lao động 2019, người lao động được nghỉ thử việc 500 ngày có hưởng lương."
        )
        report: FaithfulnessVerificationReport = self.verifier.verify(answer, self.context)
        self.assertFalse(report.passed)
        self.assertTrue(report.hallucination_detected)
        self.assertEqual(report.action_taken, "BLOCK_REFUSAL")
        self.assertGreaterEqual(report.contradicted_count, 1)

    def test_unsupported_claims_detection(self):
        """Kiểm tra phát hiện mệnh đề không có căn cứ trong ngữ cảnh."""
        answer = (
            "Người lao động muốn đi du lịch châu Âu phải nộp hồ sơ xin visa Schengen và chứng minh tài chính 200 triệu đồng."
        )
        report: FaithfulnessVerificationReport = self.verifier.verify(answer, self.context)
        self.assertFalse(report.passed)
        self.assertTrue(report.hallucination_detected)
        self.assertLess(report.faithfulness_score, 0.4)

    def test_guard_integration_block_hallucination(self):
        """Kiểm tra RefusalGuard tự động chặn câu trả lời ảo giác khi check_post_generation."""
        gen_res = GenerationResult(
            answer="Căn cứ theo Điều 888 Bộ luật Lao động, nhân viên được tăng lương gấp 10 lần.",
            citations=["[SOURCE 1]"],
            refused=False,
            model_name="mock-llm",
            provider="mock",
        )
        mock_cit = LegalCitation(
            source_id="[SOURCE 1]",
            document_title="Bộ luật Lao động 2019",
            article_number="Điều 25",
            formatted_citation="[Bộ luật Lao động 2019, Điều 25]",
        )
        cit_res = CitationResolutionResult(
            original_answer=gen_res.answer,
            enriched_answer=gen_res.answer,
            valid_citations=[mock_cit],
            citations_count=1,
            has_invalid_citations=False,
        )

        guard_res: GuardCheckResult = self.guard.check_post_generation(
            generation_result=gen_res,
            citation_result=cit_res,
            context_text=self.context,
        )

        self.assertFalse(guard_res.passed)
        self.assertTrue(guard_res.trigger_refusal)
        self.assertIn("ảo giác", guard_res.reason.lower())
        self.assertTrue(guard_res.metrics.get("hallucination_detected"))


if __name__ == "__main__":
    unittest.main()
