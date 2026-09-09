"""test_date_status_v2.py - Comprehensive Unit Tests for TASK DATA-08.

Kiểm thử toàn diện việc chuẩn hóa ngày hiệu lực và tình trạng pháp lý:
1. Test valid date: Định dạng ngày tháng hợp lệ (DD/MM/YYYY, D/M/YYYY, YYYY-MM-DD).
2. Test missing date: Xử lý ngày khuyết thiếu, rỗng hoặc placeholder thành null.
3. Test invalid date: Bác bỏ ngày phi lý lịch (32/01/2021, 29/02/2021 không nhuận), chuỗi văn bản, và text status.
4. Test effective date != issue date: Tách bạch tuyệt đối ngày ban hành và ngày hiệu lực.
5. Test unknown legal status: Chuẩn hóa trạng thái thiếu/placeholder thành 'unknown' và hỗ trợ JSON target format.
6. Test corpus catalog consistency: Kiểm tra toàn bộ 15 văn bản trong raw corpus.
"""

import unittest
import os
import json
from pydantic import ValidationError

from Data_Processing.models_v2 import (
    LegalChunkV2,
    LegalStatus,
    sanitize_null
)
from Data_Processing.schema_v2 import (
    create_chunk_v2,
    validate_chunk
)
from Data_Processing.metadata_restorer import (
    DocumentMetadataRestorer,
    DocumentMetadata
)


class TestDateAndLegalStatusMetadata(unittest.TestCase):
    """Bộ kiểm thử đơn vị cho TASK DATA-08."""

    def setUp(self):
        self.restorer = DocumentMetadataRestorer()
        self.base_chunk_kwargs = {
            "chunk_id": "TEST_DOC_C1_D1",
            "document_id": "TEST_DOC",
            "document_title": "Văn bản mẫu kiểm thử",
            "content": "Nội dung quy định pháp luật kiểm thử.",
            "parent_document": "TEST_DOC",
            "chunk_index": 0
        }

    # -------------------------------------------------------------------------
    # 1. TEST VALID DATE
    # -------------------------------------------------------------------------
    def test_01_valid_date_parsing_and_normalization(self):
        """Kiểm thử ngày tháng hợp lệ được phân tích và chuẩn hóa chính xác."""
        # 1.1. Chuẩn DD/MM/YYYY
        self.assertEqual(self.restorer.parse_and_validate_date("20/11/2019"), "20/11/2019")
        self.assertEqual(self.restorer.parse_and_validate_date("01/01/2021"), "01/01/2021")

        # 1.2. Dạng ngày/tháng 1 chữ số được chuẩn hóa thành 2 chữ số
        self.assertEqual(self.restorer.parse_and_validate_date("1/5/2022"), "01/05/2022")
        self.assertEqual(self.restorer.parse_and_validate_date("9/12/2020"), "09/12/2020")

        # 1.3. Chuẩn ISO YYYY-MM-DD
        self.assertEqual(self.restorer.parse_and_validate_date("2021-01-01"), "2021-01-01")

        # 1.4. Năm nhuận hợp lệ (2020 là năm nhuận -> 29/02/2020 hợp lệ)
        self.assertEqual(self.restorer.parse_and_validate_date("29/02/2020"), "29/02/2020")

        # 1.5. Model nhận diện và lưu trữ chính xác
        chunk = LegalChunkV2(
            **self.base_chunk_kwargs,
            issue_date="20/11/2019",
            effective_from="1/1/2021",
            effective_to="2025-12-31"
        )
        self.assertEqual(chunk.issue_date, "20/11/2019")
        self.assertEqual(chunk.effective_from, "01/01/2021")
        self.assertEqual(chunk.effective_to, "2025-12-31")

    # -------------------------------------------------------------------------
    # 2. TEST MISSING DATE
    # -------------------------------------------------------------------------
    def test_02_missing_date_normalized_to_null(self):
        """Kiểm thử ngày khuyết thiếu hoặc rỗng được chuyển thành None (null), không tự tạo."""
        # 2.1. None hoặc chuỗi rỗng
        self.assertIsNone(self.restorer.parse_and_validate_date(None))
        self.assertIsNone(self.restorer.parse_and_validate_date(""))
        self.assertIsNone(self.restorer.parse_and_validate_date("   "))

        # 2.2. Placeholders rác từ crawler
        self.assertIsNone(self.restorer.parse_and_validate_date("Đã biết"))
        self.assertIsNone(self.restorer.parse_and_validate_date("Chưa xác định"))
        self.assertIsNone(self.restorer.parse_and_validate_date("N/A"))
        self.assertIsNone(self.restorer.parse_and_validate_date("null"))

        # 2.3. Trong Model: Giá trị khuyết thiếu trả về None (null)
        chunk = LegalChunkV2(
            **self.base_chunk_kwargs,
            issue_date=None,
            effective_from="",
            effective_to="Đã biết"
        )
        self.assertIsNone(chunk.issue_date)
        self.assertIsNone(chunk.effective_from)
        self.assertIsNone(chunk.effective_to)

        target = chunk.to_target_dict()
        self.assertIsNone(target["effective_from"])
        self.assertIsNone(target["effective_to"])

    # -------------------------------------------------------------------------
    # 3. TEST INVALID DATE
    # -------------------------------------------------------------------------
    def test_03_invalid_date_rejection_and_safety(self):
        """Kiểm thử từ chối các ngày sai logic lịch và text status."""
        # 3.1. Ngày trong tháng vượt quá 31
        self.assertIsNone(self.restorer.parse_and_validate_date("32/01/2021"))
        self.assertIsNone(self.restorer.parse_and_validate_date("00/05/2022"))

        # 3.2. Tháng vượt quá 12
        self.assertIsNone(self.restorer.parse_and_validate_date("15/13/2021"))
        self.assertIsNone(self.restorer.parse_and_validate_date("10/00/2020"))

        # 3.3. Năm không nhuận (2021 không phải năm nhuận -> 29/02/2021 không hợp lệ)
        self.assertIsNone(self.restorer.parse_and_validate_date("29/02/2021"))
        self.assertIsNone(self.restorer.parse_and_validate_date("31/04/2021"))  # Tháng 4 chỉ có 30 ngày

        # 3.4. Chuỗi văn bản ngẫu nhiên
        self.assertIsNone(self.restorer.parse_and_validate_date("random_string_not_a_date"))
        self.assertIsNone(self.restorer.parse_and_validate_date("99/99/9999"))

        # 3.5. Model ném lỗi ValidationError khi nhận chuỗi ngày sai format cố tình
        with self.assertRaises(ValidationError):
            LegalChunkV2(**self.base_chunk_kwargs, issue_date="32/01/2021")

        with self.assertRaises(ValidationError):
            LegalChunkV2(**self.base_chunk_kwargs, effective_from="29/02/2021")

        with self.assertRaises(ValidationError):
            LegalChunkV2(**self.base_chunk_kwargs, effective_to="not-a-date")

    # -------------------------------------------------------------------------
    # 4. TEST EFFECTIVE DATE != ISSUE DATE (DECOUPLING)
    # -------------------------------------------------------------------------
    def test_04_effective_date_decoupled_from_issue_date(self):
        """Kiểm thử tách bạch tuyệt đối: Ngày ban hành != Ngày hiệu lực."""
        # 4.1. Cả hai ngày đều tồn tại và có giá trị khác nhau
        raw_ban_hanh = "20/11/2019\n Ngày hiệu lực:\n 01/01/2021"
        raw_hieu_luc = ""
        issue_d, eff_d = self.restorer.extract_dates(raw_ban_hanh, raw_hieu_luc)

        self.assertEqual(issue_d, "20/11/2019")
        self.assertEqual(eff_d, "01/01/2021")
        self.assertNotEqual(issue_d, eff_d, "Ngày ban hành và ngày hiệu lực phải độc lập")

        # 4.2. Có ngày ban hành nhưng ngày hiệu lực bị thiếu ('Đã biết')
        raw_ban_hanh_2 = "17/01/2022\n Ngày hiệu lực:\nĐã biết"
        issue_d2, eff_d2 = self.restorer.extract_dates(raw_ban_hanh_2, "")
        self.assertEqual(issue_d2, "17/01/2022")
        self.assertIsNone(eff_d2, "Tuyệt đối không gán issue_date thành effective_from khi thiếu")

        # 4.3. Trường hợp ngược lại: có ngày hiệu lực nhưng thiếu ngày ban hành
        issue_d3, eff_d3 = self.restorer.extract_dates("", "15/03/2021")
        self.assertIsNone(issue_d3)
        self.assertEqual(eff_d3, "15/03/2021")

    # -------------------------------------------------------------------------
    # 5. TEST UNKNOWN LEGAL STATUS
    # -------------------------------------------------------------------------
    def test_05_unknown_legal_status_handling(self):
        """Kiểm thử tình trạng pháp lý không xác định được chuẩn hóa thành 'unknown'."""
        # 5.1. Restorer chuẩn hóa các placeholder rác thành 'unknown'
        self.assertEqual(self.restorer.extract_legal_status("Đã biết"), "unknown")
        self.assertEqual(self.restorer.extract_legal_status("Chưa xác định"), "unknown")
        self.assertEqual(self.restorer.extract_legal_status(""), "unknown")
        self.assertEqual(self.restorer.extract_legal_status(None), "unknown")
        self.assertEqual(self.restorer.extract_legal_status("unknown"), "unknown")

        # 5.2. Trạng thái hợp lệ được bảo toàn
        self.assertEqual(self.restorer.extract_legal_status("Còn hiệu lực"), "Còn hiệu lực")
        self.assertEqual(self.restorer.extract_legal_status("Hết hiệu lực"), "Hết hiệu lực")
        self.assertEqual(self.restorer.extract_legal_status("Hết hiệu lực một phần"), "Hết hiệu lực một phần")

        # 5.3. LegalChunkV2 lưu trữ và xuất ra target dictionary đúng định dạng yêu cầu của DATA-08
        chunk = LegalChunkV2(
            **self.base_chunk_kwargs,
            effective_from=None,
            effective_to=None,
            legal_status="unknown"
        )
        target = chunk.to_target_dict()

        self.assertIsNone(target["effective_from"])
        self.assertIsNone(target["effective_to"])
        self.assertEqual(target["legal_status"], "unknown")

        # 5.4. Kiểm tra JSON serialization chính xác theo đặc tả DATA-08
        expected_subset = {
            "effective_from": None,
            "effective_to": None,
            "legal_status": "unknown"
        }
        for k, v in expected_subset.items():
            self.assertEqual(target[k], v, f"Trường {k} không đúng với đặc tả DATA-08")

    # -------------------------------------------------------------------------
    # 6. TEST CORPUS CONSISTENCY (15 DOCUMENTS)
    # -------------------------------------------------------------------------
    def test_06_corpus_catalog_date_status_coverage(self):
        """Kiểm tra độ phủ và tính đúng đắn trên toàn bộ 15 văn bản trong raw corpus."""
        raw_dir = r"D:\Filehoc\KLCN\agentic-rag\Data_Processing\data_corpus_raw"
        if not os.path.exists(raw_dir):
            self.skipTest("Thư mục data_corpus_raw không tồn tại")

        catalog = self.restorer.build_corpus_catalog(raw_dir)
        self.assertEqual(len(catalog), 15)

        # 6.1. 100% văn bản (15/15) có ngày ban hành hợp lệ
        for doc_id, meta in catalog.items():
            self.assertIsNotNone(meta.issue_date, f"{doc_id} bị thiếu issue_date")
            self.assertRegex(meta.issue_date, r'^\d{2}/\d{2}/\d{4}$', f"{doc_id} issue_date sai định dạng")

        # 6.2. Riêng BLLD_2019 có ngày hiệu lực và trạng thái 'Còn hiệu lực'
        blld = catalog["BLLD_2019"]
        self.assertEqual(blld.issue_date, "20/11/2019")
        self.assertEqual(blld.effective_from, "01/01/2021")
        self.assertEqual(blld.legal_status, "Còn hiệu lực")
        self.assertIsNone(blld.effective_to)

        # 6.3. Các văn bản khác có legal_status == 'unknown' và effective_from == None
        other_docs = [doc_id for doc_id in catalog if doc_id != "BLLD_2019"]
        self.assertEqual(len(other_docs), 14)

        for doc_id in other_docs:
            meta = catalog[doc_id]
            self.assertIsNone(meta.effective_from, f"{doc_id} không được tự tạo effective_from")
            self.assertIsNone(meta.effective_to, f"{doc_id} effective_to phải là None")
            self.assertEqual(meta.legal_status, "unknown", f"{doc_id} legal_status phải là 'unknown'")


if __name__ == "__main__":
    unittest.main()
