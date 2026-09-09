"""test_build_dataset_v2.py - Unit & Integration Tests for TASK DATA-10 (Build Legal Dataset V2).

Kiểm thử toàn diện quy trình tạo Dataset V2 tự động:
1. Test pipeline execution: Khởi chạy pipeline thành công và sinh đủ artifacts.
2. Test output integrity: Kiểm tra định dạng chuẩn của legal_dataset_v2.json và legal_dataset_v2.jsonl.
3. Test no lost documents: Đủ 15/15 văn bản quy phạm trong dataset V2.
4. Test zero collisions: 100% Chunk IDs là duy nhất (total_chunks == unique_chunk_ids).
5. Test no monster chunks: Không có chunk nào vượt trần max_chunk_tokens (800 tokens).
6. Test metadata coverage: Độ phủ metadata đầy đủ và đúng quy tắc DATA-07/DATA-08.
7. Test appendix preservation: Phụ lục, biểu mẫu, bảng biểu được bảo tồn và chia nhỏ tự nhiên.
8. Test V1 baseline frozen: File V1 KhoaLuan_Data_HoanChinh.json được bảo tồn nguyên vẹn (SHA-256).
"""

import unittest
import os
import json
import hashlib

from Data_Processing.build_dataset_v2 import (
    build_legal_dataset_v2,
    calculate_sha256,
    V1_BASELINE_PATH,
    V1_EXPECTED_SHA256
)
from Data_Processing.schema_v2 import validate_dataset


class TestBuildLegalDatasetV2(unittest.TestCase):
    """Bộ kiểm thử cho pipeline xây dựng Legal Dataset V2."""

    @classmethod
    def setUpClass(cls):
        """Khởi chạy pipeline tạo Dataset V2 trước khi chạy các kiểm thử."""
        cls.raw_dir = r"D:\Filehoc\KLCN\agentic-rag\Data_Processing\data_corpus_raw"
        cls.output_dir = r"D:\Filehoc\KLCN\agentic-rag\Data_Processing\output_v2"
        cls.json_path = os.path.join(cls.output_dir, "legal_dataset_v2.json")
        cls.jsonl_path = os.path.join(cls.output_dir, "legal_dataset_v2.jsonl")
        cls.meta_path = os.path.join(cls.output_dir, "build_metadata.json")
        cls.report_path = r"D:\Filehoc\KLCN\agentic-rag\reports\dataset_audit\DATA-10_dataset_v2_summary.md"

        # Thực thi pipeline nếu tệp chưa có hoặc chạy lại để đảm bảo tính mới
        cls.summary = build_legal_dataset_v2(
            raw_dir=cls.raw_dir,
            output_dir=cls.output_dir,
            verbose=False
        )

        with open(cls.json_path, "r", encoding="utf-8") as f:
            cls.v2_data = json.load(f)

    # -------------------------------------------------------------------------
    # 1. TEST PIPELINE EXECUTION & ARTIFACTS
    # -------------------------------------------------------------------------
    def test_01_pipeline_artifacts_exist_and_non_empty(self):
        """Kiểm thử: Tất cả các file đầu ra bắt buộc phải tồn tại và có dung lượng hợp lệ."""
        self.assertTrue(os.path.exists(self.json_path), "Thiếu file legal_dataset_v2.json")
        self.assertTrue(os.path.exists(self.jsonl_path), "Thiếu file legal_dataset_v2.jsonl")
        self.assertTrue(os.path.exists(self.meta_path), "Thiếu file build_metadata.json")
        self.assertTrue(os.path.exists(self.report_path), "Thiếu file DATA-10_dataset_v2_summary.md")

        self.assertGreater(os.path.getsize(self.json_path), 1_000_000)
        self.assertGreater(os.path.getsize(self.jsonl_path), 1_000_000)
        self.assertGreater(os.path.getsize(self.meta_path), 1_000)
        self.assertGreater(os.path.getsize(self.report_path), 2_000)

    # -------------------------------------------------------------------------
    # 2. TEST JSON & JSONL CONTENT INTEGRITY
    # -------------------------------------------------------------------------
    def test_02_json_and_jsonl_content_integrity(self):
        """Kiểm thử: JSON và JSONL chứa chính xác số lượng bản ghi và tuân thủ schema 21 trường."""
        total_chunks = len(self.v2_data)
        self.assertGreater(total_chunks, 1000)

        # 2.1. Đọc và đếm JSON Lines
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            jsonl_lines = [json.loads(line) for line in f if line.strip()]

        self.assertEqual(len(jsonl_lines), total_chunks, "Số bản ghi giữa JSON và JSONL không khớp")

        # 2.2. Kiểm tra chuẩn 21 trường cốt lõi theo đặc tả DATA-02
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
        for chunk in self.v2_data[:50]:
            self.assertEqual(set(chunk.keys()), expected_keys)
            self.assertEqual(len(chunk), 21)

    # -------------------------------------------------------------------------
    # 3. TEST NO LOST DOCUMENTS & CONTENT
    # -------------------------------------------------------------------------
    def test_03_no_lost_documents_and_no_empty_content(self):
        """Kiểm thử: Toàn bộ 15 văn bản raw đều có mặt đầy đủ trong Dataset V2 và không có chunk rỗng."""
        doc_ids_in_v2 = set(c["document_id"] for c in self.v2_data)
        self.assertEqual(len(doc_ids_in_v2), 15, f"Số văn bản trong V2 ({len(doc_ids_in_v2)}) khác 15")

        expected_docs = [
            "BLLD_2019", "ND_12_2022", "ND_135_2020", "ND_145_2020", "ND_152_2020",
            "ND_219_2025", "ND_70_2023", "ND_74_2024", "ND_83_2022", "ND_99_2024",
            "QD_992_2025", "TT_09_2020", "TT_10_2020", "TT_11_2020", "TT_20_2023"
        ]
        for doc in expected_docs:
            self.assertIn(doc, doc_ids_in_v2, f"Thiếu văn bản {doc} trong Dataset V2")

        for c in self.v2_data:
            self.assertTrue(len(c["content"].strip()) > 0, f"Chunk rỗng: {c['chunk_id']}")

    # -------------------------------------------------------------------------
    # 4. TEST ZERO ID COLLISIONS
    # -------------------------------------------------------------------------
    def test_04_zero_id_collisions_acceptance_criteria(self):
        """Tiêu chí chấp thuận: total_chunks == unique_chunk_ids (100% Unique)."""
        ids = [c["chunk_id"] for c in self.v2_data]
        unique_ids = set(ids)

        self.assertEqual(len(ids), len(unique_ids), f"Có {len(ids) - len(unique_ids)} ID collision!")

        # Tuyệt đối không chứa hậu tố _dup
        dup_suffixes = [cid for cid in ids if "_dup" in cid]
        self.assertEqual(len(dup_suffixes), 0, f"Còn sót lại {len(dup_suffixes)} ID chứa _dup")

        # Xác thực qua hàm schema validate_dataset
        valid_objs, errors = validate_dataset(self.v2_data, check_unique_ids=True)
        self.assertEqual(len(errors), 0, f"Phát hiện lỗi validate_dataset: {errors[:2]}")

    # -------------------------------------------------------------------------
    # 5. TEST NO MONSTER CHUNKS
    # -------------------------------------------------------------------------
    def test_05_no_monster_chunks(self):
        """Kiểm thử: Không tồn tại monster chunk (> 800 tokens) trong Dataset V2."""
        from Data_Processing.config_v2 import DEFAULT_CHUNKER_CONFIG

        tokens = [DEFAULT_CHUNKER_CONFIG.count_tokens(c["content"]) for c in self.v2_data]
        max_tok = max(tokens)
        self.assertLessEqual(max_tok, 800, f"Chunk vượt quá trần 800 tokens: {max_tok}")

        monster_chunks = [t for t in tokens if t > 800]
        self.assertEqual(len(monster_chunks), 0, f"Có {len(monster_chunks)} monster chunks")

    # -------------------------------------------------------------------------
    # 6. TEST METADATA COVERAGE & EFFECTIVE DATE/STATUS
    # -------------------------------------------------------------------------
    def test_06_metadata_coverage_and_status(self):
        """Kiểm thử: Phục hồi 100% số hiệu, loại văn bản, nguồn tra cứu; legal_status hợp lệ."""
        for c in self.v2_data:
            self.assertIsNotNone(c["document_number"], f"Thiếu số hiệu ở chunk {c['chunk_id']}")
            self.assertIsNotNone(c["document_title"], f"Thiếu tiêu đề ở chunk {c['chunk_id']}")
            self.assertIsNotNone(c["document_type"], f"Thiếu loại văn bản ở chunk {c['chunk_id']}")
            self.assertIsNotNone(c["source_url"], f"Thiếu URL nguồn ở chunk {c['chunk_id']}")
            self.assertIn(c["legal_status"], ["Còn hiệu lực", "unknown"])

            # Riêng BLLD 2019 có ngày hiệu lực 01/01/2021
            if c["document_id"] == "BLLD_2019":
                self.assertEqual(c["effective_from"], "01/01/2021")
                self.assertEqual(c["legal_status"], "Còn hiệu lực")
            else:
                self.assertIsNone(c["effective_from"], f"Không được tự bịa ngày hiệu lực cho {c['document_id']}")
                self.assertEqual(c["legal_status"], "unknown")

    # -------------------------------------------------------------------------
    # 7. TEST APPENDIX PRESERVED
    # -------------------------------------------------------------------------
    def test_07_appendix_and_tables_preserved(self):
        """Kiểm thử: Các phần Phụ lục, Bảng biểu, Biểu mẫu được nhận diện và bảo tồn."""
        app_chunks = [c for c in self.v2_data if any(kw in c["chunk_id"] for kw in ["PL", "Table", "Form", "Mẫu_số"])]
        self.assertGreater(len(app_chunks), 20, "Phần phụ lục/biểu mẫu bị mất hoặc không được nhận diện")

    # -------------------------------------------------------------------------
    # 8. TEST V1 BASELINE FROZEN
    # -------------------------------------------------------------------------
    def test_08_v1_baseline_dataset_frozen_and_unchanged(self):
        """Kiểm thử bắt buộc: File baseline V1 KhoaLuan_Data_HoanChinh.json tuyệt đối không bị thay đổi."""
        self.assertTrue(os.path.exists(V1_BASELINE_PATH))
        current_hash = calculate_sha256(V1_BASELINE_PATH)
        self.assertEqual(
            current_hash,
            V1_EXPECTED_SHA256,
            "CẢNH BÁO NGUY HIỂM: Dataset V1 đã bị thay đổi mã băm SHA-256!"
        )


if __name__ == "__main__":
    unittest.main()
