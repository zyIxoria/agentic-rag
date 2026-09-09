"""test_schema_v2.py - Unit tests for Legal Dataset V2 Schema Validation.

Kiểm thử toàn diện các trường hợp:
1. Article-level chunk (có và không có Chương/Mục)
2. Clause-level chunk (Khoản không có Điểm)
3. Point-level chunk (Điểm thuộc Khoản và Điều)
4. Appendix chunk (Phụ lục độc lập)
5. Table / Form chunk (Bảng biểu, mẫu đơn)
6. Chunks thuộc cùng một Điều (chia sẻ parent_article, chunk_index tuần tự)
7. Missing metadata -> chuẩn hóa thành null (không tự bịa)
8. Từ chối bản ghi không hợp lệ (Validation rejection: empty content, empty ID, negative index, v.v.)
9. Kiểm tra tính duy nhất của chunk_id trong dataset
10. Kiểm tra xuất đúng 21 trường cốt lõi theo đặc tả
"""

import unittest
import json
from pydantic import ValidationError

from Data_Processing.models_v2 import (
    LegalChunkV2,
    DocumentType,
    LegalStatus,
    ContentType,
    sanitize_null
)
from Data_Processing.schema_v2 import (
    validate_chunk,
    validate_dataset,
    create_chunk_v2
)


class TestLegalDatasetV2Schema(unittest.TestCase):
    """Bộ kiểm thử đơn vị cho Schema Legal Dataset V2."""

    def test_01_full_article_chunk(self):
        """Kiểm thử chunk cấp Điều hoàn chỉnh có đủ Chương, Mục."""
        raw_data = {
            "chunk_id": "BLLD_2019_C3_S1_D13_K0",
            "document_id": "BLLD_2019",
            "document_number": "45/2019/QH14",
            "document_title": "Bộ luật Lao động 2019",
            "document_type": "Bộ luật",
            "chapter_number": "Chương III",
            "chapter_title": "Hợp đồng lao động",
            "section_number": "Mục 1",
            "section_title": "Giao kết hợp đồng lao động",
            "article_number": "Điều 13",
            "article_title": "Hợp đồng lao động",
            "clause_number": None,
            "point_number": None,
            "content": "Hợp đồng lao động là sự thỏa thuận giữa người lao động và người sử dụng lao động...",
            "effective_from": "2021-01-01",
            "effective_to": None,
            "legal_status": "Còn hiệu lực",
            "source_url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-Luat-lao-dong-2019-333670.aspx",
            "parent_document": "BLLD_2019",
            "parent_article": "BLLD_2019_Điều13",
            "chunk_index": 45
        }
        chunk = validate_chunk(raw_data)
        self.assertEqual(chunk.chunk_id, "BLLD_2019_C3_S1_D13_K0")
        self.assertEqual(chunk.article_number, "Điều 13")
        self.assertEqual(chunk.chapter_number, "Chương III")
        self.assertEqual(chunk.section_number, "Mục 1")
        self.assertIsNone(chunk.clause_number)
        self.assertIsNone(chunk.point_number)

    def test_02_article_without_chapter(self):
        """Kiểm thử Điều luật trong văn bản KHÔNG có Chương (như Thông tư hoặc Quyết định)."""
        raw_data = {
            "chunk_id": "TT_10_2020_D3_K0",
            "document_id": "TT_10_2020",
            "document_number": "10/2020/TT-BLĐTBXH",
            "document_title": "Thông tư số 10/2020/TT-BLĐTBXH",
            "document_type": "Thông tư",
            "chapter_number": None,
            "chapter_title": None,
            "section_number": None,
            "section_title": None,
            "article_number": "Điều 3",
            "article_title": "Nội dung chủ yếu của hợp đồng lao động",
            "clause_number": None,
            "point_number": None,
            "content": "Nội dung chủ yếu của hợp đồng lao động theo quy định tại khoản 1 Điều 21...",
            "effective_from": "2021-01-01",
            "effective_to": None,
            "legal_status": "Còn hiệu lực",
            "source_url": "https://thuvienphapluat.vn/...",
            "parent_document": "TT_10_2020",
            "parent_article": "TT_10_2020_Điều3",
            "chunk_index": 5
        }
        chunk = validate_chunk(raw_data)
        self.assertIsNone(chunk.chapter_number)
        self.assertIsNone(chunk.chapter_title)
        self.assertEqual(chunk.article_number, "Điều 3")
        self.assertEqual(chunk.document_type, "Thông tư")

    def test_03_clause_without_point(self):
        """Kiểm thử Khoản luật không có Điểm (Clause without Point)."""
        raw_data = {
            "chunk_id": "BLLD_2019_C3_D24_K3",
            "document_id": "BLLD_2019",
            "document_number": "45/2019/QH14",
            "document_title": "Bộ luật Lao động 2019",
            "document_type": "Bộ luật",
            "chapter_number": "Chương III",
            "chapter_title": "Hợp đồng lao động",
            "section_number": None,
            "section_title": None,
            "article_number": "Điều 24",
            "article_title": "Thử việc",
            "clause_number": "Khoản 3",
            "point_number": None,
            "content": "3. Không áp dụng thử việc đối với người lao động giao kết hợp đồng lao động có thời hạn dưới 01 tháng.",
            "effective_from": "2021-01-01",
            "effective_to": None,
            "legal_status": "Còn hiệu lực",
            "source_url": None,
            "parent_document": "BLLD_2019",
            "parent_article": "BLLD_2019_Điều24",
            "chunk_index": 88
        }
        chunk = validate_chunk(raw_data)
        self.assertEqual(chunk.clause_number, "Khoản 3")
        self.assertIsNone(chunk.point_number)
        self.assertEqual(chunk.parent_article, "BLLD_2019_Điều24")

    def test_04_point_level_chunk(self):
        """Kiểm thử Điểm luật (Point-level) đầy đủ phân cấp."""
        raw_data = {
            "chunk_id": "BLLD_2019_C8_D118_K2_Pa",
            "document_id": "BLLD_2019",
            "document_number": "45/2019/QH14",
            "document_title": "Bộ luật Lao động 2019",
            "document_type": "Bộ luật",
            "chapter_number": "Chương VIII",
            "chapter_title": "Kỷ luật lao động, trách nhiệm vật chất",
            "section_number": None,
            "section_title": None,
            "article_number": "Điều 118",
            "article_title": "Nội quy lao động",
            "clause_number": "Khoản 2",
            "point_number": "Điểm a",
            "content": "a) Thời giờ làm việc, thời giờ nghỉ ngơi;",
            "effective_from": "2021-01-01",
            "effective_to": None,
            "legal_status": "Còn hiệu lực",
            "source_url": None,
            "parent_document": "BLLD_2019",
            "parent_article": "BLLD_2019_Điều118",
            "chunk_index": 312
        }
        chunk = validate_chunk(raw_data)
        self.assertEqual(chunk.point_number, "Điểm a")
        self.assertEqual(chunk.clause_number, "Khoản 2")
        self.assertEqual(chunk.article_number, "Điều 118")

    def test_05_appendix_chunk(self):
        """Kiểm thử chunk thuộc Phụ lục độc lập (Appendix support)."""
        raw_data = {
            "chunk_id": "TT_11_2020_PL1_Sec1",
            "document_id": "TT_11_2020",
            "document_number": "11/2020/TT-BLDTBXH",
            "document_title": "Thông tư số 11/2020/TT-BLĐTBXH",
            "document_type": "Thông tư",
            "chapter_number": None,
            "chapter_title": None,
            "section_number": None,
            "section_title": None,
            "article_number": None,
            "article_title": None,
            "clause_number": None,
            "point_number": None,
            "content": "DANH MỤC NGHỀ, CÔNG VIỆC NẶNG NHỌC, ĐỘC HẠI, NGUY HIỂM... Lĩnh vực Khai thác khoáng sản.",
            "effective_from": "2021-03-01",
            "effective_to": None,
            "legal_status": "Còn hiệu lực",
            "source_url": "https://thuvienphapluat.vn/...",
            "parent_document": "TT_11_2020",
            "parent_article": None,
            "chunk_index": 12,
            "content_type": "appendix",
            "appendix_number": "Phụ lục I",
            "appendix_title": "Danh mục nghề độc hại"
        }
        chunk = validate_chunk(raw_data)
        self.assertIsNone(chunk.article_number)
        self.assertIsNone(chunk.parent_article)
        self.assertEqual(chunk.content_type, "appendix")
        self.assertEqual(chunk.appendix_number, "Phụ lục I")

    def test_06_table_and_form_support(self):
        """Kiểm thử chunk định dạng Bảng biểu (Table) và Biểu mẫu (Form)."""
        table_content = (
            "| STT | Tên nghề, công việc | Đặc điểm điều kiện lao động |\n"
            "| --- | ------------------- | --------------------------- |\n"
            "| 1   | Khai thác than hầm lò| Nơi làm việc chật hẹp, thiếu dưỡng khí |"
        )
        chunk_table = create_chunk_v2(
            chunk_id="TT_11_2020_Table_01",
            document_id="TT_11_2020",
            document_title="Thông tư 11/2020/TT-BLĐTBXH",
            content=table_content,
            parent_document="TT_11_2020",
            chunk_index=3,
            content_type="table",
            appendix_number="Phụ lục I"
        )
        self.assertEqual(chunk_table.content_type, "table")
        self.assertIn("| Khai thác than hầm lò|", chunk_table.content)

        # Form support
        form_content = "Mẫu số 01/PLI: GIẤY ĐỀ NGHỊ CẤP GIẤY PHÉP LAO ĐỘNG..."
        chunk_form = create_chunk_v2(
            chunk_id="ND_152_2020_Form_01",
            document_id="ND_152_2020",
            document_title="Nghị định 152/2020/NĐ-CP",
            content=form_content,
            parent_document="ND_152_2020",
            chunk_index=50,
            content_type="form",
            appendix_number="Mẫu số 01/PLI"
        )
        self.assertEqual(chunk_form.content_type, "form")

    def test_07_chunks_belonging_to_same_article(self):
        """Kiểm thử các chunks thuộc cùng một Điều luật chia sẻ parent_article và có chunk_index tăng dần."""
        chunks_data = [
            {
                "chunk_id": "BLLD_2019_D124_K1",
                "document_id": "BLLD_2019",
                "document_title": "Bộ luật Lao động 2019",
                "article_number": "Điều 124",
                "article_title": "Hình thức xử lý kỷ luật lao động",
                "clause_number": "Khoản 1",
                "content": "1. Khiển trách.",
                "parent_document": "BLLD_2019",
                "parent_article": "BLLD_2019_Điều124",
                "chunk_index": 200
            },
            {
                "chunk_id": "BLLD_2019_D124_K2",
                "document_id": "BLLD_2019",
                "document_title": "Bộ luật Lao động 2019",
                "article_number": "Điều 124",
                "article_title": "Hình thức xử lý kỷ luật lao động",
                "clause_number": "Khoản 2",
                "content": "2. Kéo dài thời hạn nâng lương không quá 06 tháng.",
                "parent_document": "BLLD_2019",
                "parent_article": "BLLD_2019_Điều124",
                "chunk_index": 201
            },
            {
                "chunk_id": "BLLD_2019_D124_K3",
                "document_id": "BLLD_2019",
                "document_title": "Bộ luật Lao động 2019",
                "article_number": "Điều 124",
                "article_title": "Hình thức xử lý kỷ luật lao động",
                "clause_number": "Khoản 3",
                "content": "3. Cách chức.",
                "parent_document": "BLLD_2019",
                "parent_article": "BLLD_2019_Điều124",
                "chunk_index": 202
            },
            {
                "chunk_id": "BLLD_2019_D124_K4",
                "document_id": "BLLD_2019",
                "document_title": "Bộ luật Lao động 2019",
                "article_number": "Điều 124",
                "article_title": "Hình thức xử lý kỷ luật lao động",
                "clause_number": "Khoản 4",
                "content": "4. Sa thải.",
                "parent_document": "BLLD_2019",
                "parent_article": "BLLD_2019_Điều124",
                "chunk_index": 203
            }
        ]
        valid_chunks, errors = validate_dataset(chunks_data)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(valid_chunks), 4)
        for i, c in enumerate(valid_chunks):
            self.assertEqual(c.parent_article, "BLLD_2019_Điều124")
            self.assertEqual(c.chunk_index, 200 + i)

    def test_08_missing_metadata_normalized_to_null(self):
        """Kiểm thử: Mọi metadata không xác định hoặc placeholder rác ('Chưa xác định', 'Đã biết', 'N/A')
        phải được chuẩn hóa chính xác thành None (null), không được tự suy đoán."""
        raw_data = {
            "chunk_id": "ND_12_2022_D1_K0",
            "document_id": "ND_12_2022",
            "document_number": "12/2022/ND-CP",
            "document_title": "Nghị định 12/2022/NĐ-CP",
            "document_type": "Chưa xác định",  # Placeholder
            "chapter_number": "chưa có",        # Placeholder
            "chapter_title": "",                # Rỗng
            "section_number": "N/A",            # Placeholder
            "section_title": "none",            # Placeholder
            "article_number": "Điều 1",
            "article_title": "Phạm vi điều chỉnh",
            "clause_number": "0",               # Placeholder
            "point_number": None,
            "content": "Nghị định này quy định về hành vi vi phạm...",
            "effective_from": "",               # Rỗng
            "effective_to": None,
            "legal_status": "Đã biết",          # Rác crawler
            "source_url": "   ",                # Whitespace
            "parent_document": "ND_12_2022",
            "parent_article": None,
            "chunk_index": 0
        }
        chunk = validate_chunk(raw_data)
        self.assertIsNone(chunk.document_type)
        self.assertIsNone(chunk.chapter_number)
        self.assertIsNone(chunk.chapter_title)
        self.assertIsNone(chunk.section_number)
        self.assertIsNone(chunk.section_title)
        self.assertIsNone(chunk.clause_number)
        self.assertIsNone(chunk.effective_from)
        self.assertEqual(chunk.legal_status, "unknown")
        self.assertIsNone(chunk.source_url)

    def test_09_invalid_records_rejected(self):
        """Kiểm thử từ chối dứt khoát các bản ghi không hợp lệ (không âm thầm sửa)."""
        base = {
            "chunk_id": "BLLD_2019_C1_D1",
            "document_id": "BLLD_2019",
            "document_title": "BLLD 2019",
            "content": "Nội dung hợp lệ",
            "parent_document": "BLLD_2019",
            "chunk_index": 0
        }

        # 1. Thiếu hoặc rỗng chunk_id
        bad_id = dict(base, chunk_id="")
        with self.assertRaises(ValidationError):
            validate_chunk(bad_id)

        # 2. Thiếu hoặc rỗng content
        bad_content = dict(base, content="   ")
        with self.assertRaises(ValidationError):
            validate_chunk(bad_content)

        # 3. Thiếu hoặc rỗng document_id
        bad_doc_id = dict(base, document_id="")
        with self.assertRaises(ValidationError):
            validate_chunk(bad_doc_id)

        # 4. chunk_index âm
        bad_index = dict(base, chunk_index=-1)
        with self.assertRaises(ValidationError):
            validate_chunk(bad_index)

        # 5. chunk_index không phải kiểu số
        bad_type_index = dict(base, chunk_index="abc")
        with self.assertRaises(ValidationError):
            validate_chunk(bad_type_index)

        # 6. Sai cấu trúc phân cấp: Điểm xuất hiện mà không có Khoản hay Điều
        bad_hierarchy = dict(base, point_number="Điểm a", clause_number=None, article_number=None)
        with self.assertRaises(ValidationError):
            validate_chunk(bad_hierarchy)

    def test_10_dataset_duplicate_id_detection(self):
        """Kiểm thử phát hiện và từ chối các chunk_id trùng lặp trong dataset."""
        batch = [
            {
                "chunk_id": "ND_152_C4_D29_K1",
                "document_id": "ND_152",
                "document_title": "ND 152",
                "content": "Nội dung phần 1",
                "parent_document": "ND_152",
                "chunk_index": 0
            },
            {
                "chunk_id": "ND_152_C4_D29_K1",  # Trùng lặp ID!
                "document_id": "ND_152",
                "document_title": "ND 152",
                "content": "Nội dung phần 2 biểu mẫu",
                "parent_document": "ND_152",
                "chunk_index": 1
            }
        ]
        valid_chunks, errors = validate_dataset(batch, check_unique_ids=True)
        self.assertEqual(len(valid_chunks), 1)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "DUPLICATE_CHUNK_ID")

    def test_11_target_dictionary_keys(self):
        """Kiểm thử to_target_dict() đảm bảo chính xác 21 trường cốt lõi theo đặc tả."""
        chunk = create_chunk_v2(
            chunk_id="TEST_01",
            document_id="DOC_01",
            document_title="Văn bản Test",
            content="Nội dung test",
            parent_document="DOC_01",
            chunk_index=0
        )
        target_dict = chunk.to_target_dict()
        expected_keys = {
            "chunk_id", "document_id", "document_number", "document_title", "document_type",
            "chapter_number", "chapter_title",
            "section_number", "section_title",
            "article_number", "article_title",
            "clause_number", "point_number",
            "content",
            "effective_from", "effective_to", "legal_status",
            "source_url",
            "parent_document", "parent_article",
            "chunk_index"
        }
        self.assertEqual(set(target_dict.keys()), expected_keys)
        self.assertEqual(len(target_dict), 21)

    def test_12_json_serialization_produces_literal_null(self):
        """Kiểm thử tệp JSON xuất ra chứa literal 'null' cho các trường rỗng, không phải 'None' hay ''."""
        chunk = create_chunk_v2(
            chunk_id="TEST_02",
            document_id="DOC_02",
            document_title="Văn bản Test 2",
            content="Nội dung test 2",
            parent_document="DOC_02",
            chunk_index=1,
            chapter_number=None,
            effective_to=None
        )
        json_str = json.dumps(chunk.to_target_dict(), ensure_ascii=False)
        self.assertIn('"chapter_number": null', json_str)
        self.assertIn('"effective_to": null', json_str)
        self.assertNotIn('"None"', json_str)


if __name__ == "__main__":
    unittest.main()
