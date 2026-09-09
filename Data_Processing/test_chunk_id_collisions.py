"""test_chunk_id_collisions.py - Comprehensive Unit Tests for TASK DATA-09.

Kiểm thử toàn diện việc loại bỏ ID Collision và đảm bảo tính duy nhất toàn cục của chunk_id:
1. Test duplicate hierarchy: Cùng hierarchy trong cùng văn bản không bị trùng ID.
2. Test duplicate content: Cùng nội dung trong cùng văn bản không bị trùng ID.
3. Test same article multiple chunks: Một Điều luật chia thành nhiều chunk có ID độc lập và tuần tự.
4. Test same content different documents: Cùng nội dung ở các văn bản khác nhau có ID phân biệt (namespace document_id).
5. Test rerun reproducibility: Chạy lặp lại nhiều lần trên cùng input cho kết quả 100% giống nhau (deterministic).
6. Test acceptance criteria: total_chunks == unique_chunk_ids trên toàn bộ 15 văn bản thật trong corpus.
7. Test ID generation utilities: Kiểm tra các tiện ích generate_chunk_id và generate_content_hash_id.
"""

import unittest
import os
from typing import List

from Data_Processing.chunker_v2 import LegalAwareChunkerV2
from Data_Processing.config_v2 import DEFAULT_CHUNKER_CONFIG
from Data_Processing.models_v2 import LegalChunkV2
from Data_Processing.schema_v2 import (
    generate_chunk_id,
    generate_content_hash_id,
    validate_dataset
)


class TestChunkIdCollisions(unittest.TestCase):
    """Bộ kiểm thử đơn vị cho TASK DATA-09: Fix Chunk ID Collisions."""

    def setUp(self):
        self.chunker = LegalAwareChunkerV2(DEFAULT_CHUNKER_CONFIG)

    # -------------------------------------------------------------------------
    # 1. TEST DUPLICATE HIERARCHY
    # -------------------------------------------------------------------------
    def test_01_duplicate_hierarchy(self):
        """Kiểm thử: Các chunk có cùng cấp bậc phân cấp (cùng Điều, Khoản) phải có ID duy nhất."""
        long_content = "Quy định chi tiết về tiêu chuẩn kỹ thuật an toàn và vệ sinh lao động trong cơ sở sản xuất kinh doanh. " * 60
        raw_text = f"Điều 1. Tiêu chuẩn kỹ thuật\n1. {long_content}"
        meta = {"so_hieu": "01/2024/NĐ-CP", "document_title": "Nghị định 01"}
        chunks = self.chunker.chunk_document(raw_text, meta=meta, doc_id="ND_01_2024")

        self.assertGreaterEqual(len(chunks), 2)
        ids = [c.chunk_id for c in chunks]

        # Kiểm tra tính duy nhất tuyệt đối
        self.assertEqual(len(ids), len(set(ids)), f"Phát hiện trùng ID trong cùng hierarchy: {ids}")

        # Tất cả chunks đều có cùng hierarchy Điều 1, Khoản 1
        for c in chunks:
            self.assertEqual(c.article_number, "Điều 1")
            self.assertEqual(c.clause_number, "Khoản 1")

        # Không chứa hậu tố _dup ad-hoc
        for cid in ids:
            self.assertNotIn("_dup", cid)

    # -------------------------------------------------------------------------
    # 2. TEST DUPLICATE CONTENT
    # -------------------------------------------------------------------------
    def test_02_duplicate_content(self):
        """Kiểm thử: Hai chunk có nội dung văn bản hoàn toàn giống hệt nhau trong cùng văn bản không bị trùng ID."""
        text_clause = "Người sử dụng lao động có trách nhiệm bảo đảm quyền lợi hợp pháp của người lao động theo đúng quy định của pháp luật lao động. " * 5
        raw_text = (
            f"Điều 1. Trách nhiệm doanh nghiệp\n1. {text_clause}\n\n"
            f"Điều 2. Nghĩa vụ người sử dụng lao động\n1. {text_clause}"
        )
        meta = {"so_hieu": "02/2024/NĐ-CP", "document_title": "Nghị định 02"}
        chunks = self.chunker.chunk_document(raw_text, meta=meta, doc_id="ND_02_2024")

        self.assertEqual(len(chunks), 2)
        # Hai chunk_id hoàn toàn phân biệt
        self.assertNotEqual(chunks[0].chunk_id, chunks[1].chunk_id)
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertEqual(chunks[1].chunk_index, 1)

    # -------------------------------------------------------------------------
    # 3. TEST SAME ARTICLE MULTIPLE CHUNKS
    # -------------------------------------------------------------------------
    def test_03_same_article_multiple_chunks(self):
        """Kiểm thử: Một Điều luật dài được phân rã thành nhiều chunks thì mọi chunk đều có ID duy nhất và tuần tự."""
        clauses_3 = "\n\n".join([f"{i}. Nội dung quy định tại khoản {i} về tiền lương và trợ cấp thôi việc của người lao động. " * 5 for i in range(1, 6)])
        raw_text = f"Điều 10. Chế độ tiền lương\n\n{clauses_3}"
        meta = {"so_hieu": "03/2024/NĐ-CP", "document_title": "Nghị định 03"}
        chunks = self.chunker.chunk_document(raw_text, meta=meta, doc_id="ND_03_2024")

        self.assertEqual(len(chunks), 5)
        ids = [c.chunk_id for c in chunks]

        # Tất cả ID đều thuộc Điều 10
        for cid in ids:
            self.assertIn("Điều10", cid)

        # Tất cả ID đều duy nhất
        self.assertEqual(len(ids), len(set(ids)))

        # Thứ tự chunk_index tuần tự từ 0
        for idx, c in enumerate(chunks):
            self.assertEqual(c.chunk_index, idx)
            self.assertTrue(c.chunk_id.endswith(f"_{idx}"))

    # -------------------------------------------------------------------------
    # 4. TEST SAME CONTENT DIFFERENT DOCUMENTS
    # -------------------------------------------------------------------------
    def test_04_same_content_different_documents(self):
        """Kiểm thử: Cùng một Điều luật và nội dung nhưng ở hai văn bản khác nhau phải có chunk_id độc lập toàn cầu."""
        common_text = "Điều 1. Phạm vi điều chỉnh\nNghị định này quy định về chính sách tiền lương đối với người lao động."

        chunks_doc_a = self.chunker.chunk_document(common_text, meta={"so_hieu": "A/2024"}, doc_id="DOC_A")
        chunks_doc_b = self.chunker.chunk_document(common_text, meta={"so_hieu": "B/2024"}, doc_id="DOC_B")

        self.assertEqual(len(chunks_doc_a), 1)
        self.assertEqual(len(chunks_doc_b), 1)

        id_a = chunks_doc_a[0].chunk_id
        id_b = chunks_doc_b[0].chunk_id

        # Hai ID hoàn toàn khác nhau do namespace document_id
        self.assertNotEqual(id_a, id_b)
        self.assertTrue(id_a.startswith("DOC_A"))
        self.assertTrue(id_b.startswith("DOC_B"))

    # -------------------------------------------------------------------------
    # 5. TEST RERUN REPRODUCIBILITY
    # -------------------------------------------------------------------------
    def test_05_rerun_reproducibility(self):
        """Kiểm thử: Chạy quy trình chunking nhiều lần với cùng input phải sinh ra 100% chunk_id trùng khớp từng ký tự."""
        raw_text = (
            "CHƯƠNG I\nQUY ĐỊNH CHUNG\n\n"
            "Điều 1. Phạm vi\nNội dung 1\n\n"
            "Điều 2. Đối tượng\n1. Khoản 1\n2. Khoản 2\n\n"
            "PHỤ LỤC I\nBẢNG LƯƠNG TỐI THIỂU\nVùng I: 4.960.000 đồng"
        )
        meta = {"so_hieu": "REPRO/2024", "document_title": "Văn bản kiểm thử tái lập"}

        run_1 = self.chunker.chunk_document(raw_text, meta=meta, doc_id="DOC_REPRO")
        run_2 = self.chunker.chunk_document(raw_text, meta=meta, doc_id="DOC_REPRO")

        self.assertEqual(len(run_1), len(run_2))
        ids_1 = [c.chunk_id for c in run_1]
        ids_2 = [c.chunk_id for c in run_2]

        self.assertEqual(ids_1, ids_2, "Chunk ID không có tính xác định (deterministic) giữa các lần chạy!")

    # -------------------------------------------------------------------------
    # 6. TEST ACCEPTANCE CRITERIA ON ALL 15 CORPUS DOCUMENTS
    # -------------------------------------------------------------------------
    def test_06_corpus_total_chunks_equals_unique_chunk_ids(self):
        """Tiêu chí chấp thuận: total_chunks == unique_chunk_ids trên toàn bộ 15 văn bản thật."""
        raw_dir = r"D:\Filehoc\KLCN\agentic-rag\Data_Processing\data_corpus_raw"
        if not os.path.exists(raw_dir):
            self.skipTest("Thư mục data_corpus_raw không tồn tại")

        all_chunks = self.chunker.chunk_corpus(raw_dir)
        total_chunks = len(all_chunks)
        ids = [c.chunk_id for c in all_chunks]
        unique_ids = set(ids)

        # 1. Tiêu chí cốt lõi: total_chunks == unique_chunk_ids
        self.assertEqual(total_chunks, len(unique_ids), f"Có {total_chunks - len(unique_ids)} ID bị collision!")

        # 2. Không tồn tại bất kỳ hậu tố _dup nào
        dup_suffixes = [cid for cid in ids if "_dup" in cid]
        self.assertEqual(len(dup_suffixes), 0, f"Còn tồn tại {len(dup_suffixes)} ID chứa _dup: {dup_suffixes[:5]}")

        # 3. Xác thực bằng hàm validate_dataset
        chunk_dicts = [c.model_dump() for c in all_chunks]
        valid_objs, errors = validate_dataset(chunk_dicts, check_unique_ids=True)
        self.assertEqual(len(errors), 0, f"validate_dataset phát hiện lỗi: {errors[:3]}")
        self.assertEqual(len(valid_objs), total_chunks)

    # -------------------------------------------------------------------------
    # 7. TEST ID GENERATION UTILITIES
    # -------------------------------------------------------------------------
    def test_07_generate_chunk_id_and_hash_utilities(self):
        """Kiểm thử các hàm tiện ích generate_chunk_id và generate_content_hash_id."""
        # 7.1. generate_chunk_id đầy đủ Điều, Khoản, Điểm
        cid = generate_chunk_id(
            document_id="BLLD_2019",
            article_number="Điều 118",
            clause_number="Khoản 2",
            point_number="Điểm a",
            chunk_index=45
        )
        self.assertEqual(cid, "BLLD_2019_Điều118_Khoản2_Điểma_45")

        # 7.2. generate_chunk_id cấp Điều không có Khoản
        cid2 = generate_chunk_id(
            document_id="BLLD_2019",
            article_number="Điều 1",
            chunk_index=0
        )
        self.assertEqual(cid2, "BLLD_2019_Điều1_0")

        # 7.3. generate_chunk_id Phụ lục
        cid3 = generate_chunk_id(
            document_id="TT_11_2020",
            appendix_number="Phụ lục I",
            extra_suffix="Sec1",
            chunk_index=12
        )
        self.assertEqual(cid3, "TT_11_2020_PhụlụcI_Sec1_12")

        # 7.4. generate_content_hash_id tính xác định
        h1 = generate_content_hash_id("BLLD_2019", "Điều 1", "Nội dung A", 0)
        h2 = generate_content_hash_id("BLLD_2019", "Điều 1", "Nội dung A", 0)
        h3 = generate_content_hash_id("BLLD_2019", "Điều 1", "Nội dung B", 0)

        self.assertEqual(h1, h2, "Hash phải giống nhau với cùng input")
        self.assertNotEqual(h1, h3, "Hash phải khác nhau khi content đổi")
        self.assertEqual(len(h1), 24)


if __name__ == "__main__":
    unittest.main()
