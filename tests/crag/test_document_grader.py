"""
test_document_grader.py - Bộ kiểm thử đơn vị cho phân hệ Document Grader (TASK RAG-11).
"""

import unittest
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from CRAG.config import CRAGConfig
from CRAG.evaluator.schema import GradeVerdict, ActionTrigger
from CRAG.evaluator.semantic_grader import SemanticDocumentGrader
from RAG.retriever.schema import RetrievedChunk


class TestDocumentGrader(unittest.TestCase):
    def setUp(self):
        self.config = CRAGConfig(
            UPPER_THRESHOLD=0.68,
            LOWER_THRESHOLD=0.45,
        )
        self.grader = SemanticDocumentGrader(config=self.config)

        # Chunk 1: Đúng trọng tâm về Thử việc (Điều 25)
        self.correct_chunk = RetrievedChunk(
            chunk_id="BLLD_2019_Điều25_c1",
            content="Điều 25. Thời gian thử việc. Thời gian thử việc do hai bên thỏa thuận căn cứ vào tính chất và mức độ phức tạp của công việc nhưng chỉ được thử việc một lần đối với một công việc và bảo đảm điều kiện sau đây: Không quá 180 ngày đối với công việc của người quản lý doanh nghiệp...",
            score=0.78,
            distance=0.22,
            metadata={
                "document_id": "BLLD_2019",
                "article_number": "Điều 25",
                "article_title": "Thời gian thử việc"
            },
            rank=1,
        )

        # Chunk 2: Lạc đề (Nghị định 152 về Giấy phép lao động nước ngoài)
        self.irrelevant_chunk = RetrievedChunk(
            chunk_id="ND_152_2020_Điều19_55",
            content="Điều 19. Thời hạn của giấy phép lao động được gia hạn. Thời hạn của giấy phép lao động được gia hạn theo thời hạn của một trong các trường hợp quy định tại Điều 10 Nghị định này nhưng chỉ được gia hạn một lần với thời hạn tối đa là 02 năm.",
            score=0.74,
            distance=0.26,
            metadata={
                "document_id": "ND_152_2020",
                "article_number": "Điều 19",
                "article_title": "Thời hạn của giấy phép lao động được gia hạn"
            },
            rank=2,
        )

        # Chunk 3: Mơ hồ / liên quan gián tiếp (Điều 140 về Chăm sóc y tế cho lao động nữ)
        self.ambiguous_chunk = RetrievedChunk(
            chunk_id="BLLD_2019_Điều140_c1",
            content="Điều 140. Chăm sóc y tế đối với lao động nữ. Người sử dụng lao động phải bảo đảm chăm sóc y tế và chế độ nghỉ thai sản khi sinh con theo quy định của pháp luật.",
            score=0.65,
            distance=0.35,
            metadata={
                "document_id": "BLLD_2019",
                "article_number": "Điều 140",
                "article_title": "Chăm sóc y tế đối với lao động nữ"
            },
            rank=3,
        )

    def test_grade_document_correct(self):
        """Kiểm tra chấm điểm tài liệu phù hợp trực tiếp (CORRECT)."""
        query = "Thời gian thử việc tối đa đối với người quản lý doanh nghiệp là bao nhiêu ngày?"
        grade = self.grader.grade_document(query, self.correct_chunk)

        self.assertEqual(grade.chunk_id, "BLLD_2019_Điều25_c1")
        self.assertEqual(grade.verdict, GradeVerdict.CORRECT)
        self.assertGreaterEqual(grade.relevance_score, self.config.UPPER_THRESHOLD)
        self.assertIn("thử việc", " ".join(grade.key_matches).lower())

    def test_grade_document_incorrect(self):
        """Kiểm tra chấm điểm tài liệu lạc đề dù dense score tương đối cao (INCORRECT)."""
        query = "Thời gian thử việc tối đa đối với người quản lý doanh nghiệp là bao nhiêu ngày?"
        grade = self.grader.grade_document(query, self.irrelevant_chunk)

        self.assertEqual(grade.chunk_id, "ND_152_2020_Điều19_55")
        self.assertEqual(grade.verdict, GradeVerdict.INCORRECT)
        self.assertLess(grade.relevance_score, self.config.LOWER_THRESHOLD)

    def test_grade_document_out_of_scope(self):
        """Kiểm tra phạt điểm câu hỏi ngoài phạm vi (Out-of-scope penalty)."""
        query = "Tiêu chuẩn cấp giấy phép nhân viên điều khiển tàu bay và bằng lái phi công dân dụng?"
        grade = self.grader.grade_document(query, self.correct_chunk)

        self.assertEqual(grade.verdict, GradeVerdict.INCORRECT)
        self.assertLess(grade.relevance_score, 0.40)
        self.assertIn("ngoài phạm vi", grade.reasoning.lower())

    def test_grade_documents_action_refine(self):
        """Kiểm tra quyết định hành động REFINE khi có ít nhất 1 tài liệu tin cậy (CORRECT)."""
        query = "Thời gian thử việc tối đa của người quản lý doanh nghiệp?"
        chunks = [self.correct_chunk, self.irrelevant_chunk]
        result = self.grader.grade_documents(query, chunks)

        self.assertEqual(result.overall_verdict, GradeVerdict.CORRECT)
        self.assertEqual(result.recommended_action, ActionTrigger.REFINE)
        self.assertEqual(result.correct_count, 1)
        self.assertEqual(result.incorrect_count, 1)
        self.assertGreaterEqual(result.overall_confidence, self.config.UPPER_THRESHOLD)

    def test_grade_documents_action_web_search(self):
        """Kiểm tra quyết định hành động WEB_SEARCH khi toàn bộ tài liệu đều lạc đề trên câu hỏi hợp lệ."""
        query = "Mức bồi thường thiệt hại khi người lao động làm mất dụng cụ thiết bị được tính như thế nào?"
        chunks = [self.irrelevant_chunk]
        result = self.grader.grade_documents(query, chunks)

        self.assertEqual(result.overall_verdict, GradeVerdict.INCORRECT)
        self.assertEqual(result.recommended_action, ActionTrigger.WEB_SEARCH)
        self.assertEqual(result.incorrect_count, 1)

    def test_grade_documents_action_refuse(self):
        """Kiểm tra quyết định hành động REFUSE khi câu hỏi hoàn toàn ngoài phạm vi pháp luật lao động."""
        query = "Thời hạn cấp đổi thẻ căn cước công dân gắn chíp tại cơ quan công an quận?"
        chunks = [self.irrelevant_chunk]
        result = self.grader.grade_documents(query, chunks)

        self.assertEqual(result.overall_verdict, GradeVerdict.INCORRECT)
        self.assertEqual(result.recommended_action, ActionTrigger.REFUSE)

    def test_grade_documents_action_combine_search(self):
        """Kiểm tra quyết định hành động COMBINE_SEARCH khi tài liệu ở mức mơ hồ (AMBIGUOUS)."""
        query = "Chế độ nghỉ thai sản và quyền lợi nuôi con nhỏ dưới 12 tháng tuổi của lao động nữ?"
        chunks = [self.ambiguous_chunk]
        result = self.grader.grade_documents(query, chunks)

        self.assertEqual(result.overall_verdict, GradeVerdict.AMBIGUOUS)
        self.assertEqual(result.recommended_action, ActionTrigger.COMBINE_SEARCH)
        self.assertEqual(result.ambiguous_count, 1)

    def test_empty_chunks_handling(self):
        """Kiểm tra xử lý danh sách chunks rỗng an toàn."""
        query = "Bất kỳ câu hỏi nào"
        result = self.grader.grade_documents(query, [])

        self.assertEqual(result.overall_verdict, GradeVerdict.INCORRECT)
        self.assertEqual(result.recommended_action, ActionTrigger.REFUSE)
        self.assertEqual(result.overall_confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
