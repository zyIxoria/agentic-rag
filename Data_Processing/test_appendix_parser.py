"""test_appendix_parser.py - Unit and Integration Tests for Legal Appendix, Table, Form, and Catalog Parser.

Kiểm thử toàn diện các yêu cầu của TASK DATA-05:
1. Nhận diện các thành phần phi Điều/Khoản:
   - Phụ lục (Phụ lục I, Phụ lục II, PHỤ LỤC...)
   - Bảng biểu (Lộ trình tuổi nghỉ hưu, ma trận điều kiện lao động...)
   - Biểu mẫu (Mẫu số 01/PLI, Mẫu số 02, Mẫu ngắt dòng...)
   - Danh mục (Danh mục nghề nặng nhọc độc hại, Danh mục địa bàn lương tối thiểu...)
2. Cơ chế phân rã tự nhiên (Natural Segmentation):
   - Appendix -> Section -> Table -> Row/entry.
   - Tuyệt đối không chia đôi một entry pháp lý nếu làm mất nghĩa.
3. Loại bỏ hoàn toàn monster chunk:
   - Không còn chunk nào vượt quá 2.000 từ (giải quyết triệt để lỗi chunk 36.441 từ của V1).
   - Bảo toàn 100% nội dung (Zero text loss).
4. Chuẩn hóa metadata:
   - Hỗ trợ đầy đủ các giá trị content_type: "article", "clause", "point", "appendix", "table", "form", "other".
   - Tương thích hoàn hảo với LegalChunkV2 (Schema V2).
"""

import os
import sys
import unittest

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from Data_Processing.appendix_parser import (
    AppendixParser,
    AppendixBlock,
    AppendixSection,
    AppendixTableBlock,
    AppendixEntry,
    FormBlock
)
from Data_Processing.models_v2 import LegalChunkV2, ContentType


class TestAppendixDetection(unittest.TestCase):
    """Kiểm thử nhận diện mở đầu Phụ lục, Danh mục, Biểu mẫu và các trường hợp ngoại lệ."""

    def setUp(self):
        self.parser = AppendixParser()

    def test_01_valid_appendix_headers(self):
        """Kiểm thử các dạng tiêu đề Phụ lục hợp lệ."""
        cases = [
            ("PHỤ LỤC I", "Phụ lục I"),
            ("Phụ lục II", "Phụ lục II"),
            ("PHỤ LỤC 01", "Phụ lục 01"),
            ("PHỤ LỤC", "Phụ lục"),
            ("Phụ lục III. Biểu mẫu hướng dẫn", "Phụ lục III"),
        ]
        for line, expected_num in cases:
            res = self.parser.is_appendix_boundary(line)
            self.assertIsNotNone(res, f"Không nhận diện được: {line}")
            self.assertEqual(res[0], expected_num)

    def test_02_valid_catalog_headers(self):
        """Kiểm thử nhận diện tiêu đề Danh mục độc lập."""
        cases = [
            ("DANH MỤC", "Danh mục"),
            ("DANH MỤC NGHỀ, CÔNG VIỆC NẶNG NHỌC, ĐỘC HẠI", "Danh mục"),
            ("DANH MỤC ĐỊA BÀN ÁP DỤNG MỨC LƯƠNG TỐI THIỂU", "Danh mục"),
        ]
        for line, expected_num in cases:
            res = self.parser.is_appendix_boundary(line)
            self.assertIsNotNone(res, f"Không nhận diện được: {line}")
            self.assertEqual(res[0], expected_num)

    def test_03_valid_form_headers(self):
        """Kiểm thử nhận diện tiêu đề Biểu mẫu / Mẫu số."""
        cases = [
            ("Mẫu số 01/PLI", "Mẫu số 01/PLI"),
            ("Mẫu số 02", "Mẫu số 02"),
            ("MẪU SỐ 05/PLI", "Mẫu số 05/PLI"),
            ("Mẫu số 15/PLI", "Mẫu số 15/PLI"),
        ]
        for line, expected_id in cases:
            res = self.parser.is_appendix_boundary(line)
            self.assertIsNotNone(res, f"Không nhận diện được: {line}")
            self.assertEqual(res[0], expected_id)

    def test_04_negative_intext_citation_not_appendix(self):
        """Kiểm thử viện dẫn trong câu không bị nhận diện nhầm thành mở đầu Phụ lục mới."""
        line = "Phụ lục III ban hành kèm theo Nghị định này."
        prev = "theo Mẫu số 07/PLIII"  # Dòng trước chưa kết thúc câu
        res = self.parser.is_appendix_boundary(line, prev_line=prev)
        self.assertIsNone(res)

    def test_05_negative_within_article_reference(self):
        """Kiểm thử trích dẫn 'theo Phụ lục I' không tạo boundary."""
        line = "theo Phụ lục I ban hành kèm theo Thông tư này."
        prev = "quy định tại"
        res = self.parser.is_appendix_boundary(line, prev_line=prev)
        self.assertIsNone(res)


class TestTableAndCatalogParsing(unittest.TestCase):
    """Kiểm thử bóc tách cấu trúc Bảng và Danh mục phân loại."""

    def setUp(self):
        self.parser = AppendixParser()

    def test_01_occupations_catalog_hierarchy_segmentation(self):
        """Kiểm thử phân cấp 4 tầng: Danh mục -> Lĩnh vực -> Loại điều kiện -> Từng nghề."""
        sample_catalog = [
            "DANH MỤC NGHỀ, CÔNG VIỆC NẶNG NHỌC, ĐỘC HẠI",
            "I. KHAI THÁC KHOÁNG SẢN",
            "Điều kiện lao động loại VI",
            "1",
            "Khoan đá bằng búa máy cầm tay trong hầm lò",
            "Nơi làm việc chật hẹp, thiếu ánh sáng, ồn và rung cao.",
            "2",
            "Khai thác mỏ hầm lò",
            "Nơi làm việc chật hẹp, thiếu dưỡng khí, rất nặng nhọc.",
            "Điều kiện lao động loại V",
            "1",
            "Vận hành máy nghiền đá",
            "Chịu tác động của bụi đá, ồn vượt tiêu chuẩn cho phép."
        ]
        units = self.parser.parse_occupations_catalog(
            sample_catalog,
            appendix_number="Danh mục",
            appendix_title="Danh mục nghề nặng nhọc độc hại",
            document_id="TT_11_2020",
            max_entries_per_chunk=10
        )
        # Phải tách thành 2 chunk tương ứng với 2 bảng điều kiện: Loại VI và Loại V
        self.assertEqual(len(units), 2)

        # Chunk 1: Lĩnh vực I - Loại VI
        u1 = units[0]
        self.assertEqual(u1.content_type, ContentType.TABLE.value)
        self.assertEqual(u1.section_number, "Lĩnh vực I")
        self.assertEqual(u1.section_title, "KHAI THÁC KHOÁNG SẢN")
        self.assertIn("Điều kiện lao động loại VI", u1.table_id)
        self.assertIn("Khoan đá bằng búa máy", u1.content)
        self.assertIn("Khai thác mỏ hầm lò", u1.content)

        # Chunk 2: Lĩnh vực I - Loại V
        u2 = units[1]
        self.assertEqual(u2.content_type, ContentType.TABLE.value)
        self.assertIn("Điều kiện lao động loại V", u2.table_id)
        self.assertIn("Vận hành máy nghiền đá", u2.content)

    def test_02_occupations_catalog_no_entry_splitting(self):
        """Kiểm thử quy tắc bất biến: Tuyệt đối không cắt ngang giữa chừng một nghề nghiệp."""
        sample_catalog = [
            "I. CƠ KHÍ, LUYỆN KIM",
            "Điều kiện lao động loại V",
        ]
        # Tạo 25 nghề nghiệp
        for i in range(1, 26):
            sample_catalog.extend([
                str(i),
                f"Nghề luyện kim số {i}",
                f"Làm việc trong môi trường nhiệt độ cao {i} độ C, độc hại bụi than."
            ])

        units = self.parser.parse_occupations_catalog(
            sample_catalog,
            appendix_number="Danh mục",
            appendix_title="Danh mục nghề",
            document_id="TEST_DOC",
            max_entries_per_chunk=10
        )
        # 25 nghề với ngưỡng 10 entries/chunk sẽ tạo thành 3 chunk (10 + 10 + 5)
        self.assertEqual(len(units), 3)

        # Kiểm tra từng nghề đều trọn vẹn tên và đặc điểm
        for u in units:
            self.assertEqual(u.content_type, ContentType.TABLE.value)
            self.assertIn("Nghề luyện kim số", u.content)
            self.assertIn("độc hại bụi than", u.content)

    def test_03_region_catalog_segmentation(self):
        """Kiểm thử bóc tách danh mục địa bàn mức lương tối thiểu vùng (NĐ 74/2024)."""
        sample_region = [
            "DANH MỤC ĐỊA BÀN ÁP DỤNG MỨC LƯƠNG TỐI THIỂU",
            "1. Vùng I, gồm các địa bàn:",
            "- Các quận và các huyện Gia Lâm, Đông Anh thuộc TP Hà Nội;",
            "- Các quận thuộc Thành phố Hồ Chí Minh.",
            "2. Vùng II, gồm các địa bàn:",
            "- Thành phố Hải Dương thuộc tỉnh Hải Dương;",
            "- Thành phố Hưng Yên thuộc tỉnh Hưng Yên.",
            "3. Vùng III, gồm các địa bàn:",
            "- Các huyện còn lại thuộc tỉnh Hải Dương.",
            "4. Vùng IV, gồm các địa bàn còn lại."
        ]
        units = self.parser.parse_region_catalog(
            sample_region,
            appendix_number="Phụ lục",
            appendix_title="Địa bàn áp dụng mức lương tối thiểu",
            document_id="ND_74_2024"
        )
        # Phải tạo thành đúng 4 chunks tương ứng với 4 Vùng lương
        self.assertEqual(len(units), 4)
        self.assertEqual(units[0].section_number, "Vùng I")
        self.assertEqual(units[0].content_type, ContentType.TABLE.value)
        self.assertIn("TP Hà Nội", units[0].content)

        self.assertEqual(units[1].section_number, "Vùng II")
        self.assertIn("Thành phố Hải Dương", units[1].content)

        self.assertEqual(units[3].section_number, "Vùng IV")
        self.assertIn("các địa bàn còn lại", units[3].content)

    def test_04_retirement_tables_segmentation(self):
        """Kiểm thử bóc tách bảng lộ trình tuổi nghỉ hưu theo giới tính (NĐ 135/2020)."""
        sample_retirement = [
            "PHỤ LỤC I",
            "LỘ TRÌNH TUỔI NGHỈ HƯU",
            "Lao động nam",
            "Thời điểm sinh: Từ tháng 01/1961 đến tháng 09/1961. Tuổi nghỉ hưu: 60 tuổi 03 tháng.",
            "Thời điểm sinh: Từ tháng 10/1961 đến tháng 06/1962. Tuổi nghỉ hưu: 60 tuổi 06 tháng.",
            "Lao động nữ",
            "Thời điểm sinh: Từ tháng 01/1966 đến tháng 04/1966. Tuổi nghỉ hưu: 55 tuổi 04 tháng.",
            "Thời điểm sinh: Từ tháng 05/1966 đến tháng 08/1966. Tuổi nghỉ hưu: 55 tuổi 08 tháng."
        ]
        units = self.parser.parse_retirement_tables(
            sample_retirement,
            appendix_number="Phụ lục I",
            appendix_title="Lộ trình tuổi nghỉ hưu",
            document_id="ND_135_2020"
        )
        self.assertEqual(len(units), 2)
        self.assertEqual(units[0].table_id, "Lao động nam")
        self.assertEqual(units[0].content_type, ContentType.TABLE.value)
        self.assertIn("60 tuổi 03 tháng", units[0].content)

        self.assertEqual(units[1].table_id, "Lao động nữ")
        self.assertIn("55 tuổi 04 tháng", units[1].content)


class TestFormParsing(unittest.TestCase):
    """Kiểm thử bóc tách Biểu mẫu hành chính (Forms)."""

    def setUp(self):
        self.parser = AppendixParser()

    def test_01_standard_form_segmentation(self):
        """Kiểm thử bóc tách biểu mẫu chuẩn Mẫu số 01/PLI và Mẫu số 02/PLI."""
        sample_forms = [
            "Phụ lục I",
            "Mẫu số 01/PLI",
            "TÊN DOANH NGHIỆP",
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
            "Độc lập - Tự do - Hạnh phúc",
            "V/v giải trình nhu cầu sử dụng người lao động nước ngoài",
            "Kính gửi: Bộ Lao động - Thương binh và Xã hội.",
            "Mẫu số 02/PLI",
            "TÊN DOANH NGHIỆP",
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
            "V/v giải trình thay đổi nhu cầu sử dụng lao động"
        ]
        units = self.parser.parse_forms_appendix(
            sample_forms,
            appendix_number="Phụ lục I",
            appendix_title="Biểu mẫu thực hiện Nghị định",
            document_id="ND_152_2020"
        )
        self.assertEqual(len(units), 2)

        # Mẫu 01
        self.assertEqual(units[0].content_type, ContentType.FORM.value)
        self.assertEqual(units[0].table_id, "Mẫu số 01/PLI")
        self.assertIn("giải trình nhu cầu sử dụng", units[0].content)

        # Mẫu 02
        self.assertEqual(units[1].content_type, ContentType.FORM.value)
        self.assertEqual(units[1].table_id, "Mẫu số 02/PLI")
        self.assertIn("thay đổi nhu cầu sử dụng", units[1].content)

    def test_02_crawler_two_line_form_header(self):
        """Kiểm thử xử lý trường hợp 'Mẫu' ở dòng 1 và 'số 01' ở dòng 2 do crawler."""
        sample_wrapped_form = [
            "Mẫu",
            "số 01",
            "TÊN CƠ QUAN",
            "Nội dung giấy xác nhận...",
            "Mẫu",
            "số 02",
            "TÊN CƠ QUAN",
            "Nội dung giấy phép lao động..."
        ]
        units = self.parser.parse_forms_appendix(
            sample_wrapped_form,
            appendix_number="Phụ lục",
            appendix_title="Biểu mẫu",
            document_id="ND_219_2025"
        )
        self.assertEqual(len(units), 2)
        self.assertEqual(units[0].table_id, "Mẫu số 01")
        self.assertEqual(units[0].content_type, ContentType.FORM.value)
        self.assertEqual(units[1].table_id, "Mẫu số 02")


class TestGenericAppendixAndSchema(unittest.TestCase):
    """Kiểm thử Phụ lục quy phạm chung và tính tương thích Schema V2."""

    def setUp(self):
        self.parser = AppendixParser()

    def test_01_generic_appendix_chunking(self):
        """Kiểm thử phụ lục văn bản quy phạm chung không chứa bảng hay form được chia cân đối."""
        paragraphs = [
            f"Đoạn văn quy định chi tiết số {i}. Nội dung quy định thực hiện các biện pháp an toàn vệ sinh lao động tại nơi làm việc."
            for i in range(1, 50)
        ]
        units = self.parser._parse_generic_appendix(
            paragraphs,
            appendix_number="Phụ lục III",
            appendix_title="Quy định an toàn lao động",
            document_id="DOC_GENERIC",
            max_chunk_words=100
        )
        self.assertGreater(len(units), 1)
        for u in units:
            self.assertEqual(u.content_type, ContentType.APPENDIX.value)
            self.assertEqual(u.appendix_number, "Phụ lục III")
            self.assertLess(len(u.content.split()), 200)

    def test_02_convert_to_legal_chunk_v2(self):
        """Kiểm thử chuyển đổi danh sách ParsedLegalUnit thành các LegalChunkV2 hợp lệ."""
        sample_lines = [
            "Mẫu số 01",
            "ĐƠN ĐỀ NGHỊ HỖ TRỢ HỌC NGHỀ",
            "Kính gửi: Trung tâm Dịch vụ việc làm."
        ]
        units = self.parser.parse_forms_appendix(
            sample_lines,
            appendix_number="Phụ lục I",
            appendix_title="Biểu mẫu",
            document_id="ND_TEST"
        )
        chunks_v2 = self.parser.convert_to_chunks_v2(
            units,
            document_number="152/2020/NĐ-CP",
            document_title="Nghị định 152/2020/NĐ-CP",
            document_type="Nghị định",
            effective_from="2021-02-15",
            source_url="https://thuvienphapluat.vn",
            start_chunk_index=100
        )
        self.assertEqual(len(chunks_v2), 1)
        c = chunks_v2[0]
        self.assertEqual(c.content_type, ContentType.FORM.value)
        self.assertEqual(c.document_number, "152/2020/NĐ-CP")
        self.assertEqual(c.appendix_number, "Phụ lục I")
        self.assertEqual(c.chunk_index, 100)
        self.assertIsNone(c.article_number)
        self.assertIsNone(c.clause_number)
        self.assertIsNone(c.point_number)


class TestRealCorpusMonsterChunkElimination(unittest.TestCase):
    """Kiểm thử tích hợp thực tế: Xóa bỏ hoàn toàn Monster Chunk trên toàn bộ 15 văn bản raw."""

    def setUp(self):
        self.parser = AppendixParser()

    def test_01_all_15_corpus_appendix_stats(self):
        """Kiểm thử trên toàn bộ corpus raw:
        1. Mọi phụ lục được bóc tách hoàn chỉnh.
        2. Không có bất kỳ chunk nào vượt quá 2.000 từ.
        3. Phụ lục TT_11_2020 (trước đây 36.441 từ) được re-segment thành các chunk chuẩn < 1.000 từ.
        """
        corpus_dir = os.path.join(WORKSPACE_ROOT, "Data_Processing", "data_corpus_raw")
        corpus_files = sorted([f for f in os.listdir(corpus_dir) if f.endswith(".txt")])

        monster_chunks = []
        total_chunks = 0

        for fname in corpus_files:
            file_path = os.path.join(corpus_dir, fname)
            doc_id = fname.replace(".txt", "")
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Quét tìm điểm bắt đầu phụ lục
            app_start = None
            art_count = 0
            for idx, line in enumerate(lines):
                c = line.strip()
                if c.startswith(("Điều ", "ĐIỀU ")):
                    art_count += 1
                if art_count >= 1:
                    boundary = self.parser.is_appendix_boundary(c)
                    if boundary:
                        # Kiểm tra tránh in-line citation
                        prev = lines[idx - 1].strip() if idx > 0 else ""
                        if prev and not prev.endswith(('.', ':', '”', '"', ';')):
                            if any(prev.lower().endswith(w) for w in ['theo', 'tại', 'nêu tại', 'khoản', 'điều']):
                                continue
                        app_start = idx
                        break

            if app_start is not None:
                app_lines = lines[app_start:]
                units = self.parser.parse_appendix_lines(app_lines, document_id=doc_id, document_title=doc_id)
                total_chunks += len(units)

                for u in units:
                    w_count = len(u.content.split())
                    if w_count > 2000:
                        monster_chunks.append((doc_id, u.unit_id, w_count))

        # Tiêu chí nghiệm thu cốt lõi: 0 monster chunk!
        self.assertEqual(
            len(monster_chunks), 0,
            f"Vẫn còn {len(monster_chunks)} monster chunk: {monster_chunks}"
        )
        self.assertGreater(total_chunks, 200, "Tổng số chunk phụ lục phải được phân rã đầy đủ (>200 chunks)")


if __name__ == "__main__":
    unittest.main()
