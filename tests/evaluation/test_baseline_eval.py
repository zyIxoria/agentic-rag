"""
test_baseline_eval.py - Unit test suite cho module đánh giá Traditional RAG Baseline (RAG-10).
"""

from pathlib import Path
import sys
import unittest

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from evaluation.metrics.answer_metrics import evaluate_answer_correctness
from evaluation.metrics.faithfulness_metrics import evaluate_faithfulness
from evaluation.metrics.citation_metrics import evaluate_citations
from evaluation.metrics.refusal_metrics import evaluate_refusal
from evaluation.answer_evaluator.evaluator import LegalAnswerEvaluator
from evaluation.runner.baseline_runner import BaselineRunner
from RAG.schemas.pipeline_schema import RAGResponse
from RAG.retriever.schema import RetrievedChunk


class TestBaselineEvaluationSuite(unittest.TestCase):
    def setUp(self):
        self.sample_chunk = RetrievedChunk(
            chunk_id="BLLD_2019_Điều125_c1",
            content="Điều 125. Áp dụng hình thức xử lý kỷ luật sa thải. Hình thức xử lý kỷ luật sa thải được người sử dụng lao động áp dụng trong trường hợp người lao động có hành vi trộm cắp, tham ô, đánh bạc...",
            score=0.85,
            distance=0.15,
            metadata={"document_id": "BLLD_2019", "article_number": "Điều 125"},
            rank=1,
        )
        self.sample_gold = [
            {
                "document_id": "BLLD_2019",
                "article_number": "Điều 125",
                "chunk_ids": ["BLLD_2019_Điều125_c1"]
            }
        ]

    def test_answer_metrics_correct(self):
        """Kiểm tra đánh giá câu trả lời đúng."""
        res = evaluate_answer_correctness(
            generated_answer="Căn cứ Điều 125 Bộ luật Lao động 2019, hình thức xử lý kỷ luật sa thải được áp dụng khi người lao động có hành vi trộm cắp, tham ô...",
            reference_answer="Theo Điều 125 Bộ luật Lao động 2019, người sử dụng lao động được sa thải người lao động khi có hành vi trộm cắp, tham ô...",
            gold_sources=self.sample_gold,
            refused=False,
            requires_refusal=False,
            citations=["[Bộ luật Lao động 2019, Điều 125]"],
        )
        self.assertEqual(res["status"], "CORRECT")
        self.assertEqual(res["score"], 1.0)
        self.assertEqual(res["gold_article_recall"], 1.0)

    def test_answer_metrics_false_refusal(self):
        """Kiểm tra đánh giá khi từ chối nhầm câu hỏi hợp lệ."""
        res = evaluate_answer_correctness(
            generated_answer="Không tìm thấy đủ căn cứ pháp lý.",
            reference_answer="Theo Điều 125...",
            gold_sources=self.sample_gold,
            refused=True,
            requires_refusal=False,
            citations=[],
        )
        self.assertEqual(res["status"], "INCORRECT")
        self.assertEqual(res["score"], 0.0)

    def test_answer_metrics_correct_refusal(self):
        """Kiểm tra đánh giá khi từ chối đúng câu hỏi ngoài phạm vi."""
        res = evaluate_answer_correctness(
            generated_answer="Không tìm thấy đủ căn cứ pháp lý.",
            reference_answer="Từ chối trả lời.",
            gold_sources=[],
            refused=True,
            requires_refusal=True,
            citations=[],
        )
        self.assertEqual(res["status"], "CORRECT")
        self.assertEqual(res["score"], 1.0)

    def test_faithfulness_supported(self):
        """Kiểm tra tính trung thực khi câu trả lời dựa 100% vào context."""
        ans = "Hình thức xử lý kỷ luật sa thải được áp dụng theo Điều 125."
        res = evaluate_faithfulness(
            generated_answer=ans,
            retrieved_chunks=[self.sample_chunk],
            refused=False,
        )
        self.assertEqual(res["status"], "SUPPORTED")
        self.assertTrue(res["is_faithful"])

    def test_faithfulness_unsupported(self):
        """Kiểm tra tính trung thực khi câu trả lời bịa đặt Điều luật không có trong context."""
        ans = "Theo quy định tại Điều 999 Bộ luật Lao động, người lao động được nghỉ 100 ngày."
        res = evaluate_faithfulness(
            generated_answer=ans,
            retrieved_chunks=[self.sample_chunk],
            refused=False,
        )
        self.assertEqual(res["status"], "UNSUPPORTED")
        self.assertFalse(res["is_faithful"])
        self.assertIn("999", res["unsupported_articles"])

    def test_citation_metrics_valid(self):
        """Kiểm tra trích dẫn hợp lệ và khớp căn cứ vàng."""
        res = evaluate_citations(
            citations=["[BLLD_2019, Điều 125]"],
            retrieved_chunks=[self.sample_chunk],
            gold_sources=self.sample_gold,
            refused=False,
            requires_refusal=False,
        )
        self.assertTrue(res["has_citation"])
        self.assertEqual(res["citation_precision"], 1.0)
        self.assertEqual(res["citation_accuracy"], 1.0)
        self.assertEqual(res["invalid_citation_rate"], 0.0)

    def test_citation_metrics_invalid(self):
        """Kiểm tra trích dẫn không có trong retrieved chunks."""
        res = evaluate_citations(
            citations=["[Luật Hàng Không, Điều 500]"],
            retrieved_chunks=[self.sample_chunk],
            gold_sources=self.sample_gold,
            refused=False,
            requires_refusal=False,
        )
        self.assertEqual(res["invalid_citations"], 1)
        self.assertEqual(res["invalid_citation_rate"], 1.0)
        self.assertEqual(res["citation_accuracy"], 0.0)

    def test_refusal_metrics_matrix(self):
        """Kiểm tra toàn bộ 4 trạng thái của ma trận từ chối."""
        # 1. Correct Refusal
        r1 = evaluate_refusal(refused=True, requires_refusal=True)
        self.assertEqual(r1["status"], "CORRECT_REFUSAL")

        # 2. False Answer
        r2 = evaluate_refusal(refused=False, requires_refusal=True)
        self.assertEqual(r2["status"], "UNSUPPORTED_ANSWER")
        self.assertTrue(r2["is_false_answer"])

        # 3. False Refusal
        r3 = evaluate_refusal(refused=True, requires_refusal=False)
        self.assertEqual(r3["status"], "INCORRECT_REFUSAL")
        self.assertTrue(r3["is_false_refusal"])

        # 4. Correct Answer
        r4 = evaluate_refusal(refused=False, requires_refusal=False)
        self.assertEqual(r4["status"], "CORRECT_ANSWER")

    def test_evaluator_integration(self):
        """Kiểm tra tích hợp toàn diện của LegalAnswerEvaluator."""
        evaluator = LegalAnswerEvaluator()
        benchmark_item = {
            "question_id": "Q001",
            "question": "Trường hợp nào bị sa thải?",
            "category": "single_article",
            "requires_refusal": False,
            "reference_answer": "Theo Điều 125 sa thải khi...",
            "gold_sources": self.sample_gold,
        }
        from RAG.citation.schema import LegalCitation
        rag_response = RAGResponse(
            question="Trường hợp nào bị sa thải?",
            answer="Căn cứ Điều 125, sa thải khi trộm cắp.",
            citations=[
                LegalCitation(
                    source_id="[SOURCE 1]",
                    document_title="Bộ luật Lao động 2019",
                    article_number="Điều 125",
                    formatted_citation="[Bộ luật Lao động 2019, Điều 125]",
                )
            ],
            retrieved_chunks=[self.sample_chunk],
            latency=150.0,
            refused=False,
            retrieval_latency=140.0,
            context_latency=2.0,
            generation_latency=5.0,
            citation_latency=3.0,
        )
        record = evaluator.evaluate_response(benchmark_item, rag_response)
        self.assertEqual(record.question_id, "Q001")
        self.assertFalse(record.refused)
        self.assertIn(record.answer_correctness["status"], ("CORRECT", "PARTIALLY_CORRECT"))
        self.assertTrue(record.faithfulness["is_faithful"])


if __name__ == "__main__":
    unittest.main()
