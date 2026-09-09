"""test_data_13_regression.py - Regression Test Suite for DATA-13 Fixes.

Kiểm thử toàn bộ các yêu cầu của DATA-13:
1. Case A: BLLD 2019 Điều 125 không bị merge vào Điều 124, được tách độc lập với metadata chuẩn xác.
2. Case B: NĐ 145/2020 Điều 85 được detect độc lập, không bị merge vào Điều 84.
3. Case C: NĐ 219/2025 Điều 6 được detect độc lập, không bị merge vào Điều 5.
4. Appendix Boundary Fix: TT 09/2020 Điều 13 là Article độc lập (content_type != appendix, article_number="Điều 13").
5. Ghost heading: TT 10/2020 không sinh chunk ma "Điều 142 .".
6. Micro table-header: NĐ 135/2020 không sinh micro-chunk "Lao động nam" đơn lẻ.
7. Citation-vs-Article: Phân biệt cấu trúc chính xác giữa Heading và Citation (theo Điều X, tại Điều X, quy định tại Điều X, áp dụng Điều X...).
"""

import os
import unittest
from Data_Processing.config_v2 import DEFAULT_CHUNKER_CONFIG
from Data_Processing.hierarchy_parser import HierarchyParser
from Data_Processing.chunker_v2 import LegalAwareChunkerV2
from Data_Processing.schema_v2 import ContentType

RAW_DIR = r"D:\Filehoc\KLCN\agentic-rag\Data_Processing\data_corpus_raw"


class TestData13Regression(unittest.TestCase):
    """Bộ kiểm thử hồi quy bảo đảm chất lượng DATA-13."""

    def setUp(self):
        self.chunker = LegalAwareChunkerV2(DEFAULT_CHUNKER_CONFIG)
        self.h_parser = HierarchyParser()

    def test_01_blld_2019_dieu_125_not_merged(self):
        """Case A: BLLD 2019 Điều 125 phải tách biệt hoàn toàn với Điều 124."""
        blld_path = os.path.join(RAW_DIR, "BLLD_2019.txt")
        if not os.path.exists(blld_path):
            self.skipTest("BLLD_2019.txt missing")

        with open(blld_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        chunks = self.chunker.chunk_document(raw_text, {"document_id": "BLLD_2019"}, doc_id="BLLD_2019")

        # Điều 125 phải tồn tại dưới dạng chunk riêng
        dieu_125_chunks = [c for c in chunks if c.article_number in ("Điều 125", "125")]
        self.assertGreaterEqual(len(dieu_125_chunks), 1, "Điều 125 phải có ít nhất 1 chunk độc lập")

        for c in dieu_125_chunks:
            self.assertIn("sa thải", c.article_title.lower(), "Tiêu đề Điều 125 phải có 'sa thải'")
            self.assertEqual(c.content_type, ContentType.CLAUSE.value)

        # Điều 124 KHÔNG ĐƯỢC chứa nội dung của Điều 125
        dieu_124_chunks = [c for c in chunks if c.article_number in ("Điều 124", "124")]
        self.assertGreaterEqual(len(dieu_124_chunks), 1, "Điều 124 phải tồn tại")
        for c in dieu_124_chunks:
            self.assertNotIn("Điều 125. Áp dụng hình thức xử lý kỷ luật sa thải", c.content,
                             "Điều 124 không được merge nội dung Điều 125")

    def test_02_nd_145_2020_dieu_85_independent(self):
        """Case B: NĐ 145/2020 Điều 85 phải được tách độc lập, không bị merge vào Điều 84."""
        nd145_path = os.path.join(RAW_DIR, "ND_145_2020.txt")
        if not os.path.exists(nd145_path):
            self.skipTest("ND_145_2020.txt missing")

        with open(nd145_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        chunks = self.chunker.chunk_document(raw_text, {"document_id": "ND_145_2020"}, doc_id="ND_145_2020")

        dieu_85_chunks = [c for c in chunks if c.article_number in ("Điều 85", "85")]
        self.assertGreaterEqual(len(dieu_85_chunks), 1, "Điều 85 NĐ 145/2020 phải có ít nhất 1 chunk độc lập")

        for c in dieu_85_chunks:
            self.assertIn("quấy rối tình dục", c.article_title.lower())

        # Điều 84 không được chứa Điều 85
        dieu_84_chunks = [c for c in chunks if c.article_number in ("Điều 84", "84")]
        for c in dieu_84_chunks:
            self.assertNotIn("Điều 85. Quy định của", c.content)

    def test_03_nd_219_2025_dieu_6_independent(self):
        """Case C: NĐ 219/2025 Điều 6 phải được tách độc lập, không bị merge vào Điều 5."""
        nd219_path = os.path.join(RAW_DIR, "ND_219_2025.txt")
        if not os.path.exists(nd219_path):
            self.skipTest("ND_219_2025.txt missing")

        with open(nd219_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        chunks = self.chunker.chunk_document(raw_text, {"document_id": "ND_219_2025"}, doc_id="ND_219_2025")

        dieu_6_chunks = [c for c in chunks if c.article_number in ("Điều 6", "6")]
        self.assertGreaterEqual(len(dieu_6_chunks), 1, "Điều 6 NĐ 219/2025 phải có ít nhất 1 chunk độc lập")

        for c in dieu_6_chunks:
            self.assertIn("giao dịch điện tử", c.article_title.lower())

        # Điều 5 không được chứa Điều 6
        dieu_5_chunks = [c for c in chunks if c.article_number in ("Điều 5", "5")]
        for c in dieu_5_chunks:
            self.assertNotIn("Điều 6. Quy định về giao dịch", c.content)

    def test_04_tt_09_2020_dieu_13_appendix_boundary(self):
        """Case TT_09_2020: Điều 13 không được gán content_type=appendix do reference Phụ lục ở Điều 12."""
        tt09_path = os.path.join(RAW_DIR, "TT_09_2020.txt")
        if not os.path.exists(tt09_path):
            self.skipTest("TT_09_2020.txt missing")

        with open(tt09_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        chunks = self.chunker.chunk_document(raw_text, {"document_id": "TT_09_2020"}, doc_id="TT_09_2020")

        dieu_13_chunks = [c for c in chunks if c.article_number in ("Điều 13", "13")]
        self.assertGreaterEqual(len(dieu_13_chunks), 1, "Điều 13 TT 09/2020 phải tồn tại")

        for c in dieu_13_chunks:
            self.assertNotEqual(c.content_type, ContentType.APPENDIX.value, "Điều 13 không được là appendix")
            self.assertIn(c.content_type, (ContentType.ARTICLE.value, ContentType.CLAUSE.value, ContentType.POINT.value))
            self.assertEqual(c.article_number, "Điều 13")
            self.assertEqual(c.article_title, "Hiệu lực thi hành")
            self.assertEqual(c.chapter_number, "Chương V")

    def test_05_tt_10_2020_no_ghost_heading_dieu_142(self):
        """TT 10/2020 không được tạo ghost chunk Điều 142 từ trích dẫn bị ngắt dòng."""
        tt10_path = os.path.join(RAW_DIR, "TT_10_2020.txt")
        if not os.path.exists(tt10_path):
            self.skipTest("TT_10_2020.txt missing")

        with open(tt10_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        chunks = self.chunker.chunk_document(raw_text, {"document_id": "TT_10_2020"}, doc_id="TT_10_2020")

        # Không có bất kỳ chunk nào có article_number là Điều 142
        dieu_142_chunks = [c for c in chunks if c.article_number in ("Điều 142", "142")]
        self.assertEqual(len(dieu_142_chunks), 0, "Không được tạo ghost chunk Điều 142")

        # Kiểm tra nội dung trích dẫn 'Điều 142' được bảo toàn trong Điều 1
        dieu_1_chunks = [c for c in chunks if c.article_number in ("Điều 1", "1")]
        combined_dieu_1 = " ".join(c.content for c in dieu_1_chunks)
        self.assertIn("Điều 142", combined_dieu_1, "Nội dung tham chiếu Điều 142 phải được bảo toàn trong Điều 1")

    def test_06_nd_135_2020_no_micro_table_headers(self):
        """NĐ 135/2020 không sinh micro chunks tiêu đề bảng < 20 tokens như 'Lao động nam'."""
        nd135_path = os.path.join(RAW_DIR, "ND_135_2020.txt")
        if not os.path.exists(nd135_path):
            self.skipTest("ND_135_2020.txt missing")

        with open(nd135_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        chunks = self.chunker.chunk_document(raw_text, {"document_id": "ND_135_2020"}, doc_id="ND_135_2020")

        # Không có chunk bảng/phụ lục nào chỉ có tiêu đề cụt < 20 tokens
        micro_chunks = [c for c in chunks if self.chunker.config.count_tokens(c.content) < 20]
        for c in micro_chunks:
            self.assertNotEqual(c.content.strip(), "Lao động nam", "Không được có chunk riêng biệt chỉ có 'Lao động nam'")
            self.assertNotEqual(c.content.strip(), "Lao động nữ", "Không được có chunk riêng biệt chỉ có 'Lao động nữ'")

    def test_07_citation_vs_article_structural_priority(self):
        """Kiểm thử ưu tiên nhận diện Article Heading cấu trúc trước citation detection."""
        sample_text = (
            "Chương I\n"
            "QUY ĐỊNH CHUNG\n\n"
            "Điều 1. Phạm vi điều chỉnh\n"
            "1. Người lao động thực hiện theo Điều 125 của Bộ luật này.\n"
            "2. Chế độ kỷ luật quy định tại Điều 125 được áp dụng nghiêm ngặt.\n"
            "3. Khi có căn cứ tại Điều 125, người sử dụng lao động ra quyết định.\n\n"
            "Điều 125. Áp dụng hình thức xử lý kỷ luật sa thải\n"
            "1. Hình thức sa thải được áp dụng trong các trường hợp sau:\n"
            "a) Trộm cắp tài sản;\n"
            "b) Tiết lộ bí mật kinh doanh."
        )

        doc = self.h_parser.parse(sample_text, "TEST_DOC")
        self.assertEqual(len(doc.articles), 2, "Phải nhận diện đúng 2 Điều (Điều 1 và Điều 125)")
        self.assertEqual(doc.articles[0].number, "Điều 1")
        self.assertEqual(doc.articles[0].title, "Phạm vi điều chỉnh")
        self.assertEqual(doc.articles[1].number, "Điều 125")
        self.assertEqual(doc.articles[1].title, "Áp dụng hình thức xử lý kỷ luật sa thải")

        # Thử nghiệm các tiền tố tham chiếu không biến thành Article mới
        ref_text = (
            "Điều 2. Các trường hợp tham chiếu\n"
            "1. Căn cứ theo Điều 10 của Luật này để xử phạt.\n"
            "2. Áp dụng Điều 15 cho đối tượng đặc biệt.\n"
            "3. Thực hiện theo Điều 20 trong thời hạn 30 ngày.\n"
            "4. Thẩm quyền nêu tại Điều 25 thuộc về Tòa án."
        )
        doc_ref = self.h_parser.parse(ref_text, "REF_DOC")
        self.assertEqual(len(doc_ref.articles), 1, "Chỉ có 1 Điều 2, các viện dẫn không được tạo Điều mới")
        self.assertEqual(doc_ref.articles[0].number, "Điều 2")


if __name__ == "__main__":
    unittest.main()
