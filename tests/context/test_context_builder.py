"""test_context_builder.py - Bộ kiểm thử toàn diện cho Legal Context Builder (TASK RAG-04).

Kiểm tra đầy đủ 7 yêu cầu cốt lõi theo đặc tả:
1. source numbering: [SOURCE 1], [SOURCE 2] ổn định
2. metadata rendering: Document, Document Number, Article, Title, Clause, Point
3. duplicate chunk: keep first occurrence, deduplicate by chunk_id
4. max context: enforce MAX_CONTEXT_TOKENS, truncate by rank, record dropped_sources
5. empty retrieval: handle empty input cleanly
6. special characters: preserve quotes, markdown, brackets, newlines
7. citation mapping: accurate metadata mapping for citation generation
8. legal content unchanged: 100% verbatim, no rewrite, no summarization
"""

from __future__ import annotations
import os
import unittest
from typing import List, Dict, Any

from RAG.retriever.schema import RetrievedChunk
from RAG.context.schema import ContextSource, BuildContextResult
from RAG.context.config import ContextConfig
from RAG.context.builder import LegalContextBuilder, count_estimated_tokens


class TestLegalContextBuilder(unittest.TestCase):
    """Bộ kiểm thử cho LegalContextBuilder."""

    def setUp(self):
        """Khởi tạo builder mặc định và các chunk mẫu."""
        self.config = ContextConfig(MAX_CONTEXT_TOKENS=3000, TOKEN_MULTIPLIER=1.3)
        self.builder = LegalContextBuilder(config=self.config)

        self.sample_chunks = [
            RetrievedChunk(
                chunk_id="BLLD_2019_Điều125_Khoản1_167",
                content="1. Người lao động có hành vi trộm cắp, tham ô, đánh bạc, cố ý gây thương tích...",
                score=0.852,
                rank=1,
                distance=0.148,
                metadata={
                    "document_id": "BLLD_2019",
                    "document_number": "45/2019/QH14",
                    "document_title": "Bộ luật Lao động 2019",
                    "document_type": "Bộ luật",
                    "article_number": "Điều 125",
                    "article_title": "Áp dụng hình thức xử lý kỷ luật sa thải",
                    "clause_number": "Khoản 1",
                    "point_number": None,
                    "legal_status": "Còn hiệu lực",
                    "source_url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-Luat-lao-dong-2019-333670.aspx",
                },
            ),
            RetrievedChunk(
                chunk_id="ND_145_2020_Điều58_Khoản2_127",
                content="2. Khi xử lý kỷ luật sa thải, người sử dụng lao động phải chứng minh được lỗi của người lao động...",
                score=0.791,
                rank=2,
                distance=0.209,
                metadata={
                    "document_id": "ND_145_2020",
                    "document_number": "145/2020/NĐ-CP",
                    "document_title": "Nghị định 145/2020/NĐ-CP",
                    "document_type": "Nghị định",
                    "article_number": "Điều 58",
                    "article_title": "Trình tự, thủ tục xử lý kỷ luật lao động",
                    "clause_number": "Khoản 2",
                    "point_number": "Điểm a",
                    "legal_status": "Còn hiệu lực",
                    "source_url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-145-2020-ND-CP-huong-dan-Bo-luat-Lao-dong-ve-dieu-kien-lao-dong-460950.aspx",
                },
            ),
            RetrievedChunk(
                chunk_id="BLLD_2019_Điều126_169",
                content="Người lao động bị khiển trách sau 03 tháng hoặc bị kéo dài thời hạn nâng lương sau 06 tháng...",
                score=0.724,
                rank=3,
                distance=0.276,
                metadata={
                    "document_id": "BLLD_2019",
                    "document_number": "45/2019/QH14",
                    "document_title": "Bộ luật Lao động 2019",
                    "document_type": "Bộ luật",
                    "article_number": "Điều 126",
                    "article_title": "Xóa kỷ luật, giảm thời hạn chấp hành kỷ luật lao động",
                    "clause_number": None,
                    "point_number": None,
                    "legal_status": "Còn hiệu lực",
                    "source_url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-Luat-lao-dong-2019-333670.aspx",
                },
            ),
        ]

    # 1. Source Numbering
    def test_01_source_numbering(self):
        """1. Kiểm thử đánh số thứ tự [SOURCE 1], [SOURCE 2] ổn định và liên tục."""
        result = self.builder.build_context(self.sample_chunks)
        self.assertEqual(len(result.sources), 3)

        self.assertEqual(result.sources[0].source_id, "[SOURCE 1]")
        self.assertEqual(result.sources[0].source_number, 1)

        self.assertEqual(result.sources[1].source_id, "[SOURCE 2]")
        self.assertEqual(result.sources[1].source_number, 2)

        self.assertEqual(result.sources[2].source_id, "[SOURCE 3]")
        self.assertEqual(result.sources[2].source_number, 3)

        # Kiểm tra sự xuất hiện trong context_text
        self.assertIn("[SOURCE 1]", result.context_text)
        self.assertIn("[SOURCE 2]", result.context_text)
        self.assertIn("[SOURCE 3]", result.context_text)

    # 2. Metadata Rendering
    def test_02_metadata_rendering(self):
        """2. Kiểm thử hiển thị đầy đủ các trường Document, Document Number, Article, Title, Clause, Point."""
        result = self.builder.build_context(self.sample_chunks)

        # Kiểm tra source 1
        s1_text = self.builder.format_source_block(1, self.sample_chunks[0])
        self.assertIn("Document: Bộ luật Lao động 2019", s1_text)
        self.assertIn("Document Number: 45/2019/QH14", s1_text)
        self.assertIn("Article: Điều 125", s1_text)
        self.assertIn("Article Title: Áp dụng hình thức xử lý kỷ luật sa thải", s1_text)
        self.assertIn("Clause: Khoản 1", s1_text)
        # Point là None -> không được in "Point: None"
        self.assertNotIn("Point:", s1_text)
        self.assertNotIn("None", s1_text)

        # Kiểm tra source 2 (có Point: Điểm a)
        s2_text = self.builder.format_source_block(2, self.sample_chunks[1])
        self.assertIn("Point: Điểm a", s2_text)

        # Kiểm tra source 3 (Clause và Point đều None)
        s3_text = self.builder.format_source_block(3, self.sample_chunks[2])
        self.assertNotIn("Clause:", s3_text)
        self.assertNotIn("Point:", s3_text)

    # 3. Duplicate Chunk Handling
    def test_03_duplicate_chunk_handling(self):
        """3. Kiểm thử khử trùng lặp (Deduplication) theo chunk_id (Keep first occurrence)."""
        duplicate_chunk = RetrievedChunk(
            chunk_id="BLLD_2019_Điều125_Khoản1_167",  # Trùng với chunk 1
            content="Bản ghi trùng lặp nội dung với chunk 1 nhưng có score khác",
            score=0.650,
            rank=4,
            distance=0.350,
            metadata={"document_id": "BLLD_2019", "document_title": "Bộ luật Lao động 2019"},
        )
        chunks_with_dup = [self.sample_chunks[0], duplicate_chunk, self.sample_chunks[1]]

        result = self.builder.build_context(chunks_with_dup)
        # Kỳ vọng chỉ có 2 unique sources được đưa vào
        self.assertEqual(len(result.sources), 2)
        self.assertEqual(result.num_included, 2)
        # Chunk đầu tiên được giữ lại (score = 0.852)
        self.assertEqual(result.sources[0].score, 0.852)
        self.assertEqual(result.sources[0].chunk_id, "BLLD_2019_Điều125_Khoản1_167")
        self.assertEqual(result.sources[1].chunk_id, "ND_145_2020_Điều58_Khoản2_127")

    # 4. Max Context Limit & Dropped Sources
    def test_04_max_context_limit(self):
        """4. Kiểm thử giới hạn token tối đa (MAX_CONTEXT_TOKENS) và ghi nhận dropped_sources."""
        # Ước tính token của source 1
        s1_tokens = count_estimated_tokens(self.builder.format_source_block(1, self.sample_chunks[0]))

        # Cấu hình max_tokens chỉ vừa đủ chứa source 1, không đủ chứa source 2
        tight_limit = s1_tokens + 10
        result = self.builder.build_context(self.sample_chunks, max_tokens=tight_limit)

        # Kỳ vọng chỉ giữ lại source 1, cắt bỏ source 2 và 3
        self.assertEqual(len(result.sources), 1)
        self.assertEqual(result.sources[0].source_id, "[SOURCE 1]")
        self.assertEqual(result.num_included, 1)
        self.assertEqual(result.num_dropped, 2)
        self.assertEqual(len(result.dropped_sources), 2)
        self.assertEqual(result.dropped_sources[0].chunk_id, self.sample_chunks[1].chunk_id)
        self.assertEqual(result.dropped_sources[1].chunk_id, self.sample_chunks[2].chunk_id)

        # Tổng token phải nhỏ hơn hoặc bằng tight_limit
        self.assertLessEqual(result.total_tokens, tight_limit)

    # 5. Empty Retrieval Handling
    def test_05_empty_retrieval(self):
        """5. Kiểm thử khi danh sách thu hồi rỗng."""
        result = self.builder.build_context([])
        self.assertEqual(len(result.sources), 0)
        self.assertEqual(result.num_included, 0)
        self.assertEqual(result.num_dropped, 0)
        self.assertEqual(len(result.dropped_sources), 0)
        self.assertEqual(result.citation_mapping, {})
        self.assertIn("Không có ngữ cảnh", result.context_text)

    # 6. Special Characters Handling
    def test_06_special_characters(self):
        """6. Kiểm thử xử lý an toàn các ký tự đặc biệt (ngoặc kép, markdown, unicode, newline)."""
        special_chunk = RetrievedChunk(
            chunk_id="SPECIAL_01",
            content="Nội dung chứa \"dấu ngoặc kép\", [ngoặc vuông], $1,000 USD, 100% tỷ lệ, \n\n nhiều dòng xuống hàng.",
            score=0.9,
            rank=1,
            distance=0.1,
            metadata={
                "document_title": "Nghị định số \"145/2020/NĐ-CP\" [Đặc biệt]",
                "document_number": "145/2020/NĐ-CP",
                "article_number": "Điều 10 <Phụ lục>",
                "article_title": "Quy định về **tiền lương** & 'thưởng'",
            },
        )
        result = self.builder.build_context([special_chunk])
        self.assertEqual(len(result.sources), 1)
        # Toàn bộ ký tự đặc biệt phải được bảo toàn nguyên vẹn
        self.assertIn("\"dấu ngoặc kép\"", result.context_text)
        self.assertIn("[ngoặc vuông]", result.context_text)
        self.assertIn("$1,000 USD", result.context_text)
        self.assertIn("<Phụ lục>", result.context_text)
        self.assertIn("**tiền lương**", result.context_text)

    # 7. Citation Mapping
    def test_07_citation_mapping(self):
        """7. Kiểm thử tính chính xác của bản đồ tra cứu trích dẫn citation_mapping."""
        result = self.builder.build_context(self.sample_chunks)
        mapping = result.citation_mapping

        self.assertIn("[SOURCE 1]", mapping)
        self.assertIn("[SOURCE 2]", mapping)
        self.assertIn("[SOURCE 3]", mapping)

        s1_map = mapping["[SOURCE 1]"]
        self.assertEqual(s1_map["chunk_id"], "BLLD_2019_Điều125_Khoản1_167")
        self.assertEqual(s1_map["document_id"], "BLLD_2019")
        self.assertEqual(s1_map["document_number"], "45/2019/QH14")
        self.assertEqual(s1_map["article_number"], "Điều 125")
        self.assertEqual(s1_map["clause_number"], "Khoản 1")
        self.assertIsNone(s1_map["point_number"])
        self.assertEqual(s1_map["score"], 0.852)
        self.assertEqual(s1_map["rank"], 1)

    # 8. Legal Content Unchanged
    def test_08_legal_content_unchanged(self):
        """8. Kiểm thử câu chữ nội dung luật tuyệt đối không bị thay đổi, rewrite hay tóm tắt."""
        result = self.builder.build_context(self.sample_chunks)
        for idx, chunk in enumerate(self.sample_chunks):
            # Nội dung gốc phải xuất hiện chính xác từng ký tự trong context_text
            self.assertIn(chunk.content.strip(), result.context_text)
            self.assertEqual(result.sources[idx].content, chunk.content)


if __name__ == "__main__":
    unittest.main()
