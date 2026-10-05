"""
test_knowledge_refinement.py - Unit test suite cho module Strip & Filter trong CRAG (RAG-12).
"""

import unittest
from RAG.retriever.schema import RetrievedChunk
from CRAG.refinement.stripper import KnowledgeStripper
from CRAG.refinement.recomposer import KnowledgeRecomposer
from CRAG.refinement.schema import RefinedContext


class TestKnowledgeRefinement(unittest.TestCase):
    def setUp(self):
        self.stripper = KnowledgeStripper(strip_threshold=0.50)
        self.recomposer = KnowledgeRecomposer(stripper=self.stripper, max_context_chars=3000)

        # Mẫu văn bản Điều 125 Bộ luật Lao động với nhiều khoản khác nhau
        self.sample_chunk_125 = RetrievedChunk(
            chunk_id="BLLD_2019_Điều125_c1",
            content=(
                "Điều 125. Áp dụng hình thức xử lý kỷ luật sa thải\n"
                "1. Người lao động có hành vi trộm cắp, tham ô, đánh bạc, cố ý gây thương tích, sử dụng ma túy tại nơi làm việc.\n"
                "2. Người lao động có hành vi tiết lộ bí mật kinh doanh, bí mật công nghệ, xâm phạm quyền sở hữu trí tuệ của người sử dụng lao động.\n"
                "3. Người lao động bị xử lý kỷ luật kéo dài thời hạn nâng lương mà tái phạm trong thời gian chưa xóa kỷ luật.\n"
                "4. Người lao động tự ý bỏ việc 05 ngày cộng dồn trong thời hạn 30 ngày hoặc 20 ngày cộng dồn trong thời hạn 365 ngày mà không có lý do chính đáng."
            ),
            score=0.85,
            distance=0.15,
            rank=1,
            metadata={
                "document_id": "BLLD_2019",
                "document_title": "Bộ luật Lao động 2019",
                "document_number": "45/2019/QH14",
                "article_number": "Điều 125",
                "article_title": "Áp dụng hình thức xử lý kỷ luật sa thải",
            },
        )

        self.sample_chunk_noise = RetrievedChunk(
            chunk_id="ND145_2020_Điều58_c1",
            content=(
                "Điều 58. Chế độ bồi dưỡng bằng hiện vật đối với người lao động làm việc trong điều kiện có yếu tố nguy hiểm, độc hại.\n"
                "1. Việc tổ chức bồi dưỡng bằng hiện vật phải thực hiện trong ca làm việc, bảo đảm vệ sinh, an toàn thực phẩm.\n"
                "2. Không được trả bằng tiền, không được đưa vào đơn giá tiền lương."
            ),
            score=0.35,
            distance=0.65,
            rank=2,
            metadata={
                "document_id": "ND145_2020",
                "document_title": "Nghị định 145/2020/NĐ-CP",
                "document_number": "145/2020/NĐ-CP",
                "article_number": "Điều 58",
            },
        )

    def test_split_into_strips(self):
        """Kiểm tra khả năng phân rã điều luật thành các strips (heading + các khoản)."""
        strips = self.stripper._split_into_strips(self.sample_chunk_125.content)
        self.assertGreaterEqual(len(strips), 5)
        self.assertTrue(strips[0].startswith("Điều 125"))
        self.assertTrue(any("1. Người lao động" in s for s in strips))
        self.assertTrue(any("4. Người lao động" in s for s in strips))

    def test_strip_scoring_and_filtering(self):
        """
        Kiểm tra lọc bỏ khoản gây nhiễu:
        Truy vấn hỏi về 'tự ý bỏ việc 5 ngày' thì khoản 4 phải được giữ lại,
        khoản 2 (bí mật công nghệ) và khoản 3 không liên quan trực tiếp có điểm thấp hơn.
        """
        query = "Người lao động tự ý bỏ việc bao nhiêu ngày thì bị sa thải?"
        refined_doc = self.stripper.refine_chunk(
            chunk=self.sample_chunk_125, query=query, source_index=1
        )

        self.assertGreater(refined_doc.retained_strips_count, 0)
        # Heading Điều 125 phải luôn được giữ lại
        self.assertIn("Điều 125", refined_doc.refined_content)
        # Khoản 4 (tự ý bỏ việc) phải có mặt trong refined_content
        self.assertIn("tự ý bỏ việc", refined_doc.refined_content)
        # Phải loại bỏ ít nhất 1 strip gây nhiễu
        self.assertGreaterEqual(refined_doc.discarded_strips_count, 1)

    def test_preserve_heading_strip(self):
        """Đảm bảo tiêu đề điều luật luôn được bảo tồn để phục vụ trích dẫn."""
        query = "Hình thức sa thải kỷ luật"
        refined_doc = self.stripper.refine_chunk(
            chunk=self.sample_chunk_125, query=query, source_index=1
        )
        self.assertTrue(refined_doc.refined_content.startswith("Điều 125"))

    def test_recomposer_structure(self):
        """Kiểm tra cấu trúc context đầu ra của KnowledgeRecomposer chuẩn format [SOURCE N]."""
        query = "Quy định về sa thải khi tự ý bỏ việc"
        refined_ctx = self.recomposer.recompose(
            chunks=[self.sample_chunk_125], query=query
        )

        self.assertIn("[SOURCE 1]", refined_ctx.raw_context_text)
        self.assertIn("Document: Bộ luật Lao động 2019", refined_ctx.raw_context_text)
        self.assertIn("Article: Điều 125", refined_ctx.raw_context_text)
        self.assertIn("Content:", refined_ctx.raw_context_text)

    def test_compression_ratio_positive(self):
        """Kiểm tra hệ số nén ngữ cảnh (compression_ratio) phản ánh việc giảm thiểu ký tự thừa."""
        query = "tự ý bỏ việc không lý do chính đáng"
        refined_ctx = self.recomposer.recompose(
            chunks=[self.sample_chunk_125], query=query
        )

        self.assertLess(refined_ctx.refined_char_count, refined_ctx.original_char_count)
        self.assertGreater(refined_ctx.compression_ratio, 0.0)

    def test_recomposer_with_external_knowledge(self):
        """Kiểm tra tích hợp tri thức ngoại bộ (Web Search) vào context chung."""
        external_snippets = [
            {
                "title": "Hướng dẫn áp dụng Điều 125 BLLĐ",
                "url": "https://thuvienphapluat.vn/tintuc/sa-thai",
                "snippet": "Thời hạn 30 ngày được tính kể từ ngày đầu tiên người lao động tự ý bỏ việc.",
            }
        ]
        refined_ctx = self.recomposer.recompose(
            chunks=[self.sample_chunk_125],
            query="sa thải bỏ việc",
            external_snippets=external_snippets,
        )

        self.assertIn("[SOURCE 1]", refined_ctx.raw_context_text)
        self.assertIn("[SOURCE 2]", refined_ctx.raw_context_text)
        self.assertIn("Document: Tra cứu ngoài (Web Knowledge)", refined_ctx.raw_context_text)
        self.assertIn("Thời hạn 30 ngày được tính kể từ ngày đầu tiên", refined_ctx.raw_context_text)

    def test_empty_chunks_recompose(self):
        """Kiểm tra xử lý danh sách chunks rỗng an toàn."""
        refined_ctx = self.recomposer.recompose(chunks=[], query="test")
        self.assertEqual(refined_ctx.raw_context_text, "")
        self.assertEqual(refined_ctx.original_char_count, 0)
        self.assertEqual(refined_ctx.refined_char_count, 0)
        self.assertEqual(refined_ctx.compression_ratio, 0.0)


if __name__ == "__main__":
    unittest.main()
