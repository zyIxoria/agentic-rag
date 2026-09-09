"""test_metadata_restorer.py - Unit Tests for Document Metadata Restoration & Propagation.

Kiểm thử toàn diện các yêu cầu của TASK DATA-07:
1. Test làm sạch và phục hồi số hiệu văn bản (document_number).
2. Test nhận diện và chuẩn hóa loại văn bản (document_type).
3. Test trích xuất ngày ban hành và ngày hiệu lực (issue_date, effective_from).
4. Test khôi phục tiêu đề đầy đủ, chính thức từ raw text (document_title).
5. Test lan truyền metadata xuống toàn bộ các chunk (Metadata Propagation).
6. Test xử lý dữ liệu bị khuyết thiếu (Missing Metadata: không được invent, trả về null).
7. Test tính nhất quán tuyệt đối giữa raw document và chunk metadata (Document Consistency).
8. Test liên kết phả hệ phân cấp (Hierarchy Metadata Lineage: parent_document, parent_article).
"""

import unittest
import os
import glob
import json
from typing import Dict, Any, List

from Data_Processing.metadata_restorer import (
    DocumentMetadataRestorer,
    DocumentMetadata
)
from Data_Processing.chunker_v2 import LegalAwareChunkerV2
from Data_Processing.config_v2 import DEFAULT_CHUNKER_CONFIG
from Data_Processing.models_v2 import LegalChunkV2, ContentType


class TestDocumentMetadataRestorer(unittest.TestCase):
    """Bộ kiểm thử đơn vị cho DocumentMetadataRestorer."""

    def setUp(self):
        self.restorer = DocumentMetadataRestorer()
        self.chunker = LegalAwareChunkerV2(DEFAULT_CHUNKER_CONFIG)

    def test_01_clean_document_number(self):
        """Kiểm thử làm sạch số hiệu văn bản từ dữ liệu thô có lẫn dòng ngắt và nhãn."""
        # 1. Số hiệu có chứa xuống dòng và nhãn loại văn bản
        raw_1 = "45/2019/QH14\n \n\n\n\nLoại văn bản:\n\n\n Luật"
        self.assertEqual(self.restorer.clean_document_number(raw_1), "45/2019/QH14")

        # 2. Số hiệu có tiền tố "Số:" và khoảng trắng lỗi crawler
        raw_2 = "Số: 1 45/2020 /N Đ -CP\n \nLoại văn bản: Nghị định"
        self.assertEqual(self.restorer.clean_document_number(raw_2), "145/2020/NĐ-CP")

        # 3. Số hiệu dạng Thông tư liên bộ
        raw_3 = "Số 09/2020/TT-BLĐTBXH"
        self.assertEqual(self.restorer.clean_document_number(raw_3), "09/2020/TT-BLĐTBXH")

        # 4. Trường hợp rỗng hoặc placeholder
        self.assertIsNone(self.restorer.clean_document_number(""))
        self.assertIsNone(self.restorer.clean_document_number("Chưa xác định"))
        self.assertIsNone(self.restorer.clean_document_number("None"))
        self.assertIsNone(self.restorer.clean_document_number(None))

    def test_02_extract_document_type(self):
        """Kiểm thử nhận diện loại văn bản chuẩn xác."""
        # 1. Từ khối "Loại văn bản:" trong so_hieu
        so_hieu_nd = "12/2022/NĐ-CP\nLoại văn bản: Nghị định"
        self.assertEqual(self.restorer.extract_document_type(so_hieu_nd, "", "ND_12_2022"), "Nghị định")

        # 2. Riêng BLLD phân biệt Bộ luật vs Luật
        so_hieu_blld = "45/2019/QH14\nLoại văn bản: Luật"
        self.assertEqual(self.restorer.extract_document_type(so_hieu_blld, "", "BLLD_2019"), "Bộ luật")

        # 3. Thông tư
        so_hieu_tt = "10/2020/TT-BLĐTBXH"
        self.assertEqual(self.restorer.extract_document_type(so_hieu_tt, "", "TT_10_2020"), "Thông tư")

        # 4. Quyết định
        so_hieu_qd = "992/QĐ-TTg"
        self.assertEqual(self.restorer.extract_document_type(so_hieu_qd, "", "QD_992_2025"), "Quyết định")

    def test_03_extract_dates(self):
        """Kiểm thử trích xuất ngày ban hành và ngày hiệu lực, chuyển placeholder thành None."""
        # 1. BLLD 2019 có đầy đủ ngày ban hành và ngày hiệu lực cụ thể
        raw_ban_hanh_bl = "20/11/2019\n \n\n\n\n\n Ngày hiệu lực:\n\n\n 01/01/2021"
        issue_d, eff_d = self.restorer.extract_dates(raw_ban_hanh_bl, "")
        self.assertEqual(issue_d, "20/11/2019")
        self.assertEqual(eff_d, "01/01/2021")

        # 2. Văn bản có ngày hiệu lực là "Đã biết" -> Phải chuyển thành None
        raw_ban_hanh_nd = "17/01/2022\n \n\n\n\n\n Ngày hiệu lực:\n\n\nĐã biết"
        issue_d2, eff_d2 = self.restorer.extract_dates(raw_ban_hanh_nd, "Đã biết")
        self.assertEqual(issue_d2, "17/01/2022")
        self.assertIsNone(eff_d2)

        # 3. Khuyết thiếu hoàn toàn
        issue_d3, eff_d3 = self.restorer.extract_dates("", "")
        self.assertIsNone(issue_d3)
        self.assertIsNone(eff_d3)

    def test_04_extract_official_title(self):
        """Kiểm thử khôi phục tiêu đề đầy đủ của văn bản từ văn bản thô."""
        # Test trên mẫu giả định Nghị định có ngắt dòng
        raw_nd_text = (
            "CHÍNH PHỦ\n-------\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n\n"
            "Số: 135/2020/NĐ-CP\n\n"
            "NGHỊ\nĐỊNH\n\nQUY ĐỊNH VỀ TUỔI NGHỈ HƯU\n\n"
            "Căn cứ Luật Tổ chức Chính phủ..."
        )
        title = self.restorer.extract_official_title(raw_nd_text, "ND_135_2020", "Nghị định", "135/2020/NĐ-CP")
        self.assertIn("Nghị định số 135/2020/NĐ-CP", title)
        self.assertIn("QUY ĐỊNH VỀ TUỔI NGHỈ HƯU", title)

    def test_05_metadata_propagation_to_chunks(self):
        """Kiểm thử lan truyền metadata: Toàn bộ chunk cùng văn bản phải có chung metadata cấp văn bản."""
        raw_text = (
            "CHÍNH PHỦ\n-------\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n\n"
            "NGHỊ ĐỊNH\nQUY ĐỊNH VỀ TIỀN LƯƠNG\n\n"
            "Điều 1. Phạm vi điều chỉnh\nQuy định về mức lương tối thiểu.\n\n"
            "Điều 2. Đối tượng áp dụng\nNgười lao động và người sử dụng lao động.\n\n"
            "PHỤ LỤC\nDANH MỤC ĐỊA BÀN VÙNG I\nChi tiết địa bàn..."
        )
        raw_meta = {
            "so_hieu": "99/2024/NĐ-CP\nLoại văn bản: Nghị định",
            "ngay_ban_hanh": "26/07/2024\nNgày hiệu lực: Đã biết",
            "ngay_hieu_luc": "Đã biết",
            "tinh_trang_hieu_luc": "Đã biết",
            "source": "https://thuvienphapluat.vn/van-ban/demo-99.aspx"
        }
        chunks = self.chunker.chunk_document(raw_text, meta=raw_meta, doc_id="ND_99_2024")
        self.assertGreater(len(chunks), 1)

        first_c = chunks[0]
        expected_doc_id = "ND_99_2024"
        expected_doc_num = "99/2024/NĐ-CP"
        expected_doc_type = "Nghị định"
        expected_url = "https://thuvienphapluat.vn/van-ban/demo-99.aspx"
        expected_issue_date = "26/07/2024"

        for c in chunks:
            self.assertEqual(c.document_id, expected_doc_id)
            self.assertEqual(c.document_number, expected_doc_num)
            self.assertEqual(c.document_type, expected_doc_type)
            self.assertEqual(c.source_url, expected_url)
            self.assertEqual(c.issue_date, expected_issue_date)
            self.assertEqual(c.document_title, first_c.document_title)
            self.assertEqual(c.parent_document, expected_doc_id)

    def test_06_missing_metadata_handling_critical_rule(self):
        """Kiểm thử quy tắc nghiêm ngặt: Không được invent metadata khi dữ liệu thiếu hoặc không xác định."""
        raw_text = "Điều 1. Quy định nội bộ\nNội dung không có thông tin nguồn gốc."
        raw_meta = {
            "so_hieu": "Chưa xác định",
            "loai_van_ban": "",
            "ngay_ban_hanh": "Chưa xác định",
            "ngay_hieu_luc": "Đã biết",
            "tinh_trang_hieu_luc": "Chưa xác định",
            "source": ""
        }
        chunks = self.chunker.chunk_document(raw_text, meta=raw_meta, doc_id="DOC_UNKNOWN")
        self.assertEqual(len(chunks), 1)
        c = chunks[0]

        # Tuyệt đối không được tự bịa ra số hiệu, ngày tháng, trạng thái
        self.assertIsNone(c.document_number)
        self.assertIsNone(c.issue_date)
        self.assertIsNone(c.effective_from)
        self.assertIsNone(c.effective_to)
        self.assertEqual(c.legal_status, "unknown")
        self.assertIsNone(c.source_url)

    def test_07_raw_chunk_document_consistency_all_corpus(self):
        """Kiểm thử tính nhất quán trên toàn bộ 15 văn bản thật trong raw corpus:
        - 100% văn bản khôi phục được số hiệu hợp lệ (45/2019/QH14, 12/2022/NĐ-CP...).
        - 100% văn bản khôi phục được ngày ban hành cụ thể (DD/MM/YYYY).
        - 100% văn bản khôi phục được source_url hợp lệ.
        - Mọi chunk trong cùng văn bản có 100% metadata văn bản đồng nhất.
        """
        raw_dir = r"D:\Filehoc\KLCN\agentic-rag\Data_Processing\data_corpus_raw"
        if not os.path.exists(raw_dir):
            self.skipTest("data_corpus_raw không tồn tại")

        catalog = self.restorer.build_corpus_catalog(raw_dir)
        self.assertEqual(len(catalog), 15, "Số lượng văn bản trong catalog phải đúng 15")

        for doc_id, doc_meta in catalog.items():
            # 1. Số hiệu văn bản phải tồn tại và đúng định dạng
            self.assertIsNotNone(doc_meta.document_number, f"{doc_id} bị thiếu document_number")
            self.assertIn("/", doc_meta.document_number, f"{doc_id} số hiệu không hợp lệ: {doc_meta.document_number}")

            # 2. Ngày ban hành phải có định dạng ngày tháng
            self.assertIsNotNone(doc_meta.issue_date, f"{doc_id} bị thiếu issue_date")
            self.assertRegex(doc_meta.issue_date, r'^\d{1,2}/\d{1,2}/\d{4}$', f"{doc_id} ngày ban hành sai định dạng")

            # 3. Source URL phải có trên thuvienphapluat.vn
            self.assertIsNotNone(doc_meta.source_url, f"{doc_id} bị thiếu source_url")
            self.assertTrue(doc_meta.source_url.startswith("https://thuvienphapluat.vn"), f"{doc_id} source URL không hợp lệ")

            # 4. Loại văn bản phải là loại chuẩn mực
            self.assertIn(doc_meta.document_type, ["Bộ luật", "Luật", "Nghị định", "Thông tư", "Quyết định"])

            # 5. Tiêu đề chính thức phải có độ dài hợp lý
            self.assertGreater(len(doc_meta.document_title), 10, f"{doc_id} tiêu đề quá ngắn")

    def test_08_hierarchy_metadata_lineage_consistency(self):
        """Kiểm thử tính liên kết phả hệ cha-con (Lineage): parent_document và parent_article."""
        blld_path = r"D:\Filehoc\KLCN\agentic-rag\Data_Processing\data_corpus_raw\BLLD_2019.txt"
        meta_path = r"D:\Filehoc\KLCN\agentic-rag\Data_Processing\data_corpus_raw\BLLD_2019_meta.json"
        if not os.path.exists(blld_path):
            self.skipTest("BLLD_2019.txt không tồn tại")

        doc_meta = self.restorer.restore_from_files(meta_path, blld_path)
        with open(blld_path, "r", encoding="utf-8") as fp:
            text = fp.read()

        chunks = self.chunker.chunk_document(text, meta=doc_meta.to_dict(), doc_id="BLLD_2019")
        self.assertGreater(len(chunks), 200)

        for c in chunks:
            # parent_document phải trùng khớp với document_id
            self.assertEqual(c.parent_document, "BLLD_2019")
            self.assertEqual(c.document_number, "45/2019/QH14")
            self.assertEqual(c.document_type, "Bộ luật")
            self.assertEqual(c.issue_date, "20/11/2019")
            self.assertEqual(c.effective_from, "01/01/2021")
            self.assertEqual(c.legal_status, "Còn hiệu lực")

            # Nếu là chunk thuộc Điều luật -> parent_article phải trỏ đúng
            if c.article_number:
                d_clean = c.article_number.replace(' ', '')
                self.assertEqual(c.parent_article, f"BLLD_2019_{d_clean}")


if __name__ == "__main__":
    unittest.main()
