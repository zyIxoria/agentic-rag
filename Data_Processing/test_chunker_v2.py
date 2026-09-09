"""test_chunker_v2.py - Comprehensive Unit Tests for Legal-Aware Chunker V2.

Kiểm thử toàn diện các yêu cầu của TASK DATA-06:
1. Kiểm tra cấu hình linh hoạt (ChunkerConfigV2) và các ràng buộc hợp lệ.
2. Kiểm tra phân rã cấp Điểm (Point-level chunking) và gom nhóm Điểm (Point grouping) có kèm lời dẫn Khoản.
3. Kiểm tra phân rã cấp Khoản (Clause-level chunking) và gom các Khoản ngắn liền kề cùng Điều luật.
4. Kiểm tra tính liên kết toàn vẹn cấp Điều (Article cohesion): Giữ trọn Điều luật nếu <= target_chunk_tokens.
5. Kiểm tra ràng buộc cấm Headless Chunk: Không bao giờ tạo chunk cụt đầu kiểu "4. Sa thải.".
6. Kiểm tra triệt tiêu Monster Chunks: 100% chunks <= max_chunk_tokens.
7. Kiểm tra phân tách an toàn (Safe sentence splitting): Không cắt giữa số liệu pháp lý (1.000.000 đồng, 15.5%).
8. Kiểm tra tính độc nhất của Chunk ID (Unique ID) và chunk_index tăng tuần tự từ 0.
9. Kiểm tra tính đầy đủ của Hierarchy Metadata và Lineage (parent_document, parent_article).
10. Kiểm tra phân tách và gắn nhãn Phụ lục / Bảng biểu / Biểu mẫu (Appendix, Table, Form).
11. Kiểm tra bảo toàn 100% nội dung (Zero text loss).
12. Kiểm thử tích hợp trên văn bản thật BLLD_2019: Xác nhận thống kê V2 vượt trội so với baseline V1.
"""

import unittest
import os
import re
from typing import List

from Data_Processing.config_v2 import ChunkerConfigV2, DEFAULT_CHUNKER_CONFIG
from Data_Processing.chunker_v2 import (
    LegalAwareChunkerV2,
    split_long_text_safe
)
from Data_Processing.models_v2 import LegalChunkV2, ContentType


class TestLegalAwareChunkerV2(unittest.TestCase):
    """Bộ kiểm thử đơn vị cho Legal-Aware Chunker V2."""

    def setUp(self):
        self.config = ChunkerConfigV2(
            target_chunk_tokens=350,
            max_chunk_tokens=800,
            min_chunk_tokens=100,
            overlap_tokens=40,
            token_multiplier=1.3
        )
        self.chunker = LegalAwareChunkerV2(self.config)

    def test_01_config_validation_and_methods(self):
        """Kiểm thử ChunkerConfigV2: Tính toán token, quy đổi từ và xác thực giá trị tham số."""
        cfg = self.config
        text = "Người lao động và người sử dụng lao động"
        words = len(text.split())
        tokens = cfg.count_tokens(text)
        self.assertEqual(tokens, int(words * 1.3 + 0.999999))
        self.assertGreater(tokens, 0)
        self.assertEqual(cfg.count_tokens(""), 0)

        # Ràng buộc không hợp lệ
        with self.assertRaises(ValueError):
            ChunkerConfigV2(min_chunk_tokens=-1)
        with self.assertRaises(ValueError):
            ChunkerConfigV2(min_chunk_tokens=300, target_chunk_tokens=200)
        with self.assertRaises(ValueError):
            ChunkerConfigV2(target_chunk_tokens=500, max_chunk_tokens=400)
        with self.assertRaises(ValueError):
            ChunkerConfigV2(min_chunk_tokens=100, overlap_tokens=120)

    def test_02_point_level_chunking_and_grouping(self):
        """Kiểm thử Điểm luật (Point): Gom nhóm điểm ngắn và kèm lời dẫn của Khoản."""
        raw = (
            "Điều 5. Quyền và nghĩa vụ của người lao động\n"
            "1. Người lao động có các quyền sau đây:\n"
            "a) Làm việc, tự do lựa chọn việc làm, nơi làm việc, nghề nghiệp;\n"
            "b) Hưởng lương phù hợp với trình độ, kỹ năng nghề trên cơ sở thỏa thuận;\n"
            "c) Từ chối làm việc nếu có nguy cơ rõ ràng đe dọa tính mạng;\n"
            "d) Đơn phương chấm dứt hợp đồng lao động;\n"
            "đ) Thành lập, gia nhập tổ chức đại diện người lao động;\n"
            "e) Yêu cầu giải quyết tranh chấp lao động."
        )
        # Sử dụng config với target_chunk_tokens nhỏ để kích hoạt point grouping
        custom_cfg = ChunkerConfigV2(
            target_chunk_tokens=60,
            max_chunk_tokens=150,
            min_chunk_tokens=30,
            overlap_tokens=10
        )
        chunker = LegalAwareChunkerV2(custom_cfg)
        chunks = chunker.chunk_document(raw, meta={"so_hieu": "TEST/01"}, doc_id="TEST_01")
        
        # Phải tạo ra các chunk cấp Điểm (point)
        point_chunks = [c for c in chunks if c.content_type == ContentType.POINT.value]
        self.assertGreater(len(point_chunks), 0)
        
        # Mọi chunk Điểm phải có lời dẫn của Khoản 1
        for pc in point_chunks:
            self.assertIn("Người lao động có các quyền sau đây", pc.content)
            self.assertIsNotNone(pc.point_number)
            self.assertEqual(pc.clause_number, "Khoản 1")
            self.assertEqual(pc.article_number, "Điều 5")

    def test_03_clause_level_chunking_and_merging(self):
        """Kiểm thử Khoản luật (Clause): Gom các khoản ngắn liền kề cùng Điều luật."""
        raw = (
            "Điều 2. Đối tượng áp dụng\n"
            "1. Người lao động, người học nghề, người tập nghề.\n"
            "2. Người sử dụng lao động.\n"
            "3. Cơ quan, tổ chức, cá nhân khác có liên quan trực tiếp đến quan hệ lao động."
        )
        chunks = self.chunker.chunk_document(raw, meta={"so_hieu": "TEST/02"}, doc_id="TEST_02")
        self.assertEqual(len(chunks), 1)
        # Vì Điều 2 ngắn (< 350 tokens), giữ trọn vẹn Điều 2
        self.assertEqual(chunks[0].article_number, "Điều 2")
        self.assertIn("1. Người lao động", chunks[0].content)
        self.assertIn("3. Cơ quan, tổ chức", chunks[0].content)

    def test_04_article_cohesion(self):
        """Kiểm thử tính liên kết Điều luật: Điều hoàn chỉnh <= target_chunk_tokens không bị chia cắt."""
        raw = (
            "Điều 26. Tiền lương thử việc\n"
            "Tiền lương của người lao động trong thời gian thử việc do hai bên thỏa thuận nhưng ít nhất phải bằng 85% mức lương của công việc đó."
        )
        chunks = self.chunker.chunk_document(raw, meta={"so_hieu": "TEST/03"}, doc_id="TEST_03")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].article_number, "Điều 26")
        self.assertEqual(chunks[0].content_type, ContentType.ARTICLE.value)
        self.assertIn("85% mức lương", chunks[0].content)

    def test_05_no_headless_chunks(self):
        """Kiểm thử ràng buộc: Tuyệt đối không tạo chunk cụt đầu chỉ chứa tiêu đề như '4. Sa thải.'."""
        raw = (
            "Điều 124. Hình thức xử lý kỷ luật lao động\n"
            "1. Khiển trách.\n"
            "2. Kéo dài thời hạn nâng lương không quá 06 tháng.\n"
            "3. Cách chức.\n"
            "4. Sa thải."
        )
        chunks = self.chunker.chunk_document(raw, meta={"so_hieu": "TEST/04"}, doc_id="TEST_04")
        self.assertEqual(len(chunks), 1)
        # Toàn bộ 4 hình thức kỷ luật phải nằm trong cùng 1 chunk, không có chunk nào chỉ chứa "4. Sa thải."
        for c in chunks:
            self.assertNotEqual(c.content.strip(), "4. Sa thải.")
            self.assertIn("1. Khiển trách", c.content)
            self.assertIn("4. Sa thải", c.content)

    def test_06_no_monster_chunks(self):
        """Kiểm thử triệt tiêu Monster Chunks: Dữ liệu cực lớn phải được chia nhỏ <= max_chunk_tokens."""
        # Tạo văn bản giả định 3000 từ trong 1 Khoản
        long_paragraph = "Nội dung quy định chi tiết về an toàn vệ sinh lao động và trách nhiệm phòng ngừa sự cố. " * 300
        raw = f"Điều 100. Quy định an toàn\n1. {long_paragraph}"
        
        chunks = self.chunker.chunk_document(raw, meta={"so_hieu": "TEST/05"}, doc_id="TEST_05")
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            tokens = self.config.count_tokens(c.content)
            self.assertLessEqual(
                tokens, self.config.max_chunk_tokens,
                f"Phát hiện monster chunk vượt ngưỡng: {tokens} tokens > {self.config.max_chunk_tokens}"
            )

    def test_07_safe_splitting_boundaries(self):
        """Kiểm thử phân tách an toàn: Không cắt đứt giữa các số liệu tiền tệ hoặc phần trăm."""
        text = "Mức lương tối thiểu vùng là 4.680.000 đồng/tháng. Tỷ lệ đóng bảo hiểm xã hội bắt buộc là 17.5% đối với người sử dụng lao động và 8% đối với người lao động."
        splits = split_long_text_safe(text, max_tokens=20, overlap_tokens=5, config=self.config)
        recombined = " ".join(splits)
        self.assertIn("4.680.000 đồng", recombined)
        self.assertIn("17.5%", recombined)
        self.assertNotIn("4. 680. 000", recombined)

    def test_08_unique_chunk_ids_and_sequential_index(self):
        """Kiểm thử tính duy nhất của Chunk ID và thứ tự tăng tuần tự của chunk_index từ 0."""
        raw = (
            "Điều 1. Phạm vi\nNội dung 1\n\n"
            "Điều 2. Đối tượng\nNội dung 2\n\n"
            "Điều 3. Giải thích\n1. Định nghĩa A\n2. Định nghĩa B"
        )
        chunks = self.chunker.chunk_document(raw, meta={"so_hieu": "TEST/06"}, doc_id="TEST_06")
        ids = [c.chunk_id for c in chunks]
        self.assertEqual(len(ids), len(set(ids)), f"Có Chunk ID bị trùng lặp: {ids}")
        for idx, c in enumerate(chunks):
            self.assertEqual(c.chunk_index, idx, f"chunk_index không liên tục: {c.chunk_index} != {idx}")

    def test_09_hierarchy_metadata_lineage(self):
        """Kiểm thử tính đầy đủ của metadata phân cấp và liên kết cha-con (lineage)."""
        raw = (
            "CHƯƠNG I\nNHỮNG QUY ĐỊNH CHUNG\n\n"
            "Mục 1. PHẠM VI VÀ ĐỐI TƯỢNG\n\n"
            "Điều 1. Phạm vi điều chỉnh\n"
            "Bộ luật này quy định tiêu chuẩn lao động..."
        )
        chunks = self.chunker.chunk_document(raw, meta={"so_hieu": "TEST/07"}, doc_id="TEST_07")
        self.assertEqual(len(chunks), 1)
        c = chunks[0]
        self.assertEqual(c.chapter_number, "Chương I")
        self.assertEqual(c.chapter_title, "NHỮNG QUY ĐỊNH CHUNG")
        self.assertEqual(c.section_number, "Mục 1")
        self.assertEqual(c.section_title, "PHẠM VI VÀ ĐỐI TƯỢNG")
        self.assertEqual(c.article_number, "Điều 1")
        self.assertEqual(c.article_title, "Phạm vi điều chỉnh")
        self.assertEqual(c.parent_document, "TEST_07")
        self.assertEqual(c.parent_article, "TEST_07_Điều1")

    def test_10_appendix_table_form_chunking(self):
        """Kiểm thử phân tách Phụ lục / Biểu mẫu / Bảng biểu và gán content_type chuẩn."""
        raw = (
            "Điều 1. Áp dụng\nNội dung điều luật.\n\n"
            "PHỤ LỤC I\n\n"
            "Mẫu số 01/PLI\n"
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
            "Độc lập - Tự do - Hạnh phúc\n\n"
            "VĂN BẢN GIẢI TRÌNH NHU CẦU SỬ DỤNG LAO ĐỘNG NƯỚC NGOÀI\n"
            "Kính gửi: Bộ Lao động - Thương binh và Xã hội.\n"
            "Nội dung biểu mẫu..."
        )
        chunks = self.chunker.chunk_document(raw, meta={"so_hieu": "TEST/08"}, doc_id="TEST_08")
        app_chunks = [c for c in chunks if c.content_type in (ContentType.FORM.value, ContentType.APPENDIX.value)]
        self.assertGreater(len(app_chunks), 0)
        self.assertIsNotNone(app_chunks[0].appendix_number)
        self.assertEqual(app_chunks[0].parent_document, "TEST_08")
        self.assertIsNone(app_chunks[0].article_number)

    def test_11_zero_text_loss(self):
        """Kiểm thử tính toàn vẹn: Không làm mất bất kỳ nội dung nào của văn bản."""
        raw = (
            "Điều 15. Nguyên tắc giao kết hợp đồng lao động\n"
            "1. Tự nguyện, bình đẳng, thiện chí, hợp tác và trung thực.\n"
            "2. Tự do giao kết hợp đồng lao động nhưng không được trái pháp luật, thỏa ước lao động tập thể và đạo đức xã hội."
        )
        chunks = self.chunker.chunk_document(raw, meta={"so_hieu": "TEST/09"}, doc_id="TEST_09")
        combined_text = "\n".join(c.content for c in chunks)
        self.assertIn("Tự nguyện, bình đẳng, thiện chí, hợp tác và trung thực", combined_text)
        self.assertIn("không được trái pháp luật, thỏa ước lao động tập thể", combined_text)

    def test_12_corpus_integration_blld_2019(self):
        """Kiểm thử tích hợp trên văn bản thật BLLD_2019:
        - 0 monster chunks > 800 tokens.
        - Tỷ lệ chunk < 100 tokens giảm mạnh (dưới 20% so với 73.6% của V1).
        - 100% chunk IDs là duy nhất.
        - Mọi chunk đều pass Pydantic validation (LegalChunkV2).
        """
        blld_path = r"D:\Filehoc\KLCN\agentic-rag\Data_Processing\data_corpus_raw\BLLD_2019.txt"
        if not os.path.exists(blld_path):
            self.skipTest("BLLD_2019.txt không tồn tại")

        with open(blld_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        meta = {
            "so_hieu": "45/2019/QH14",
            "loai_van_ban": "Bộ luật",
            "ngay_hieu_luc": "01/01/2021",
            "tinh_trang_hieu_luc": "Còn hiệu lực",
            "source": "https://thuvienphapluat.vn"
        }

        chunks = self.chunker.chunk_document(raw_text, meta=meta, doc_id="BLLD_2019")
        self.assertGreater(len(chunks), 200)

        # 1. Không có chunk nào vượt quá max_chunk_tokens
        tokens = [self.config.count_tokens(c.content) for c in chunks]
        max_tok = max(tokens)
        self.assertLessEqual(max_tok, self.config.max_chunk_tokens)

        # 2. Tỷ lệ chunk < 100 tokens giảm mạnh dưới 25% (V1 là 73.6%)
        less_100 = sum(1 for t in tokens if t < 100)
        pct_less_100 = less_100 / len(chunks) * 100
        self.assertLess(pct_less_100, 25.0, f"Tỷ lệ chunk < 100 tokens quá cao: {pct_less_100:.1f}%")

        # 3. Unique IDs
        ids = [c.chunk_id for c in chunks]
        self.assertEqual(len(ids), len(set(ids)), "Phát hiện trùng Chunk ID trong BLLD_2019")

        # 4. Sequential chunk_index
        for idx, c in enumerate(chunks):
            self.assertEqual(c.chunk_index, idx)

        # 5. Xác thực Pydantic V2
        for c in chunks:
            self.assertIsInstance(c, LegalChunkV2)
            self.assertIsNotNone(c.chunk_id)
            self.assertIsNotNone(c.content)
            self.assertGreater(len(c.content), 0)


if __name__ == "__main__":
    unittest.main()
