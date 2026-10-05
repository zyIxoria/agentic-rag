"""test_vector_store.py - Bộ kiểm thử toàn diện cho Persistent Vector Store (ChromaDB).

Kiểm thử toàn bộ các yêu cầu của TASK RAG-02:
1. collection creation
2. insert small fixture
3. count
4. get by chunk_id
5. persistence/reload
6. metadata preservation
7. duplicate ID behavior
8. dimension mismatch (FAIL FAST)
9. empty dataset
10. delete_collection confirmation
11. compatibility validation
12. real dataset v2.1 sample ingestion
"""

from __future__ import annotations
import os
import json
import gc
import shutil
import tempfile
import unittest
from typing import List, Dict, Any

from RAG.vector_store.chroma_store import PersistentChromaStore
from RAG.vector_store.schema import (
    VectorRecord,
    CollectionConfig,
    sanitize_metadata,
    desanitize_metadata,
)
from RAG.vector_store.exceptions import (
    VectorStoreError,
    DimensionMismatchError,
    CompatibilityError,
    CollectionNotFoundError,
)


class TestPersistentVectorStore(unittest.TestCase):
    """Bộ kiểm thử unit và integration cho PersistentChromaStore."""

    def setUp(self):
        """Khởi tạo thư mục tạm và store mới cho mỗi ca kiểm thử."""
        self.temp_dir = tempfile.mkdtemp(prefix="chroma_test_")
        self.store = PersistentChromaStore(persist_directory=self.temp_dir)
        self.test_dim = 8
        self.test_model = "BAAI/bge-m3"
        self.test_version = "v2.1"
        self.collection_name = "test_labor_law"

    def tearDown(self):
        """Dọn dẹp kết nối ChromaDB và thư mục tạm."""
        if hasattr(self, "store") and self.store is not None:
            self.store.close()
            del self.store
            self.store = None
        gc.collect()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_collection_creation(self):
        """1. Kiểm thử tạo collection với đầy đủ metadata và kiểm tra các thuộc tính."""
        col = self.store.create_collection(
            name=self.collection_name,
            embedding_dimension=self.test_dim,
            embedding_model=self.test_model,
            dataset_version=self.test_version,
            distance_metric="cosine",
            metadata={"description": "Test Collection for Labor Law"},
        )
        self.assertIsNotNone(col)
        self.assertEqual(self.store.active_collection_name, self.collection_name)
        self.assertEqual(self.store.embedding_dimension, self.test_dim)
        self.assertEqual(self.store.embedding_model, self.test_model)
        self.assertEqual(self.store.dataset_version, self.test_version)

        # Kiểm tra metadata được ghi vào collection của ChromaDB
        col_meta = col.metadata or {}
        self.assertEqual(col_meta.get("embedding_dimension"), self.test_dim)
        self.assertEqual(col_meta.get("embedding_model"), self.test_model)
        self.assertEqual(col_meta.get("dataset_version"), self.test_version)
        self.assertEqual(col_meta.get("hnsw:space"), "cosine")

        # Kiểm tra danh sách collection
        collections = self.store.list_collections()
        self.assertIn(self.collection_name, collections)

    def test_02_insert_small_fixture(self):
        """2. Kiểm thử nạp fixture nhỏ (3 bản ghi chuẩn format pháp luật Việt Nam)."""
        self.store.create_collection(
            name=self.collection_name,
            embedding_dimension=self.test_dim,
            embedding_model=self.test_model,
            dataset_version=self.test_version,
        )

        ids = [
            "BLLD_2019_Điều1_0",
            "BLLD_2019_Điều2_1",
            "ND_145_2020_Điều5_0",
        ]
        embeddings = [
            [0.1 * i for i in range(self.test_dim)],
            [0.2 * i for i in range(self.test_dim)],
            [0.3 * i for i in range(self.test_dim)],
        ]
        documents = [
            "Điều 1. Phạm vi điều chỉnh Bộ luật Lao động quy định tiêu chuẩn lao động...",
            "Điều 2. Đối tượng áp dụng Người lao động, người học nghề, người tập nghề...",
            "Điều 5. Thỏa ước lao động tập thể theo Nghị định 145/2020/NĐ-CP...",
        ]
        metadatas = [
            {
                "document_id": "BLLD_2019",
                "document_title": "Bộ luật Lao động 2019",
                "article_number": "Điều 1",
                "legal_status": "Còn hiệu lực",
            },
            {
                "document_id": "BLLD_2019",
                "document_title": "Bộ luật Lao động 2019",
                "article_number": "Điều 2",
                "legal_status": "Còn hiệu lực",
            },
            {
                "document_id": "ND_145_2020",
                "document_title": "Nghị định 145/2020/NĐ-CP",
                "article_number": "Điều 5",
                "legal_status": "Còn hiệu lực",
            },
        ]

        upserted = self.store.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        self.assertEqual(upserted, 3)
        self.assertEqual(self.store.count(), 3)

    def test_03_count(self):
        """3. Kiểm thử hàm count() phản ánh chính xác số lượng bản ghi."""
        self.store.create_collection(
            name=self.collection_name,
            embedding_dimension=self.test_dim,
            embedding_model=self.test_model,
        )
        # Ban đầu collection rỗng
        self.assertEqual(self.store.count(), 0)

        # Thêm 2 bản ghi
        self.store.upsert(
            ids=["chunk_1", "chunk_2"],
            embeddings=[[0.1] * self.test_dim, [0.2] * self.test_dim],
            documents=["Nội dung 1", "Nội dung 2"],
        )
        self.assertEqual(self.store.count(), 2)

        # Thêm tiếp 3 bản ghi
        self.store.upsert(
            ids=["chunk_3", "chunk_4", "chunk_5"],
            embeddings=[[0.3] * self.test_dim, [0.4] * self.test_dim, [0.5] * self.test_dim],
            documents=["Nội dung 3", "Nội dung 4", "Nội dung 5"],
        )
        self.assertEqual(self.store.count(), 5)

    def test_04_get_by_chunk_id(self):
        """4. Kiểm thử truy xuất bản ghi chính xác theo chunk_id duy nhất."""
        self.store.create_collection(
            name=self.collection_name,
            embedding_dimension=self.test_dim,
            embedding_model=self.test_model,
        )
        test_id = "BLLD_2019_Điều36_Khoản1_P1_50"
        test_emb = [0.123] * self.test_dim
        test_doc = "Điều 36. Quyền đơn phương chấm dứt hợp đồng lao động..."
        test_meta = {
            "document_id": "BLLD_2019",
            "article_number": "Điều 36",
            "clause_number": "Khoản 1",
            "legal_status": "Còn hiệu lực",
        }

        self.store.upsert(
            ids=[test_id],
            embeddings=[test_emb],
            documents=[test_doc],
            metadatas=[test_meta],
        )

        # Truy xuất bản ghi tồn tại
        record = self.store.get_by_id(test_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["id"], test_id)
        self.assertEqual(record["document"], test_doc)
        self.assertEqual(record["metadata"]["article_number"], "Điều 36")
        self.assertEqual(record["metadata"]["clause_number"], "Khoản 1")

        # Kiểm tra vector
        self.assertIsNotNone(record["embedding"])
        self.assertEqual(len(record["embedding"]), self.test_dim)
        for val in record["embedding"]:
            self.assertAlmostEqual(val, 0.123, places=3)

        # Truy xuất ID không tồn tại -> Trả về None
        non_existent = self.store.get_by_id("NON_EXISTENT_ID")
        self.assertIsNone(non_existent)

    def test_05_persistence_and_reload(self):
        """5. Kiểm thử tính bền vững (Persistence) và nạp lại (Reload) từ đĩa cứng."""
        self.store.create_collection(
            name=self.collection_name,
            embedding_dimension=self.test_dim,
            embedding_model=self.test_model,
            dataset_version=self.test_version,
        )

        ids = ["chunk_persist_1", "chunk_persist_2"]
        embs = [[0.5] * self.test_dim, [0.6] * self.test_dim]
        docs = ["Văn bản lưu bền vững 1", "Văn bản lưu bền vững 2"]
        metas = [{"tag": "p1"}, {"tag": "p2"}]

        self.store.upsert(ids=ids, embeddings=embs, documents=docs, metadatas=metas)
        self.assertEqual(self.store.count(), 2)

        # Đóng client cũ hoàn toàn
        self.store.close()
        del self.store
        gc.collect()

        # Tạo đối tượng PersistentChromaStore MỚI trỏ vào cùng thư mục
        new_store = PersistentChromaStore(persist_directory=self.temp_dir)
        self.store = new_store  # Để tearDown tự dọn dẹp

        # Nạp lại collection và kiểm tra tính tương thích
        loaded_col = new_store.load_collection(
            name=self.collection_name,
            expected_dimension=self.test_dim,
            expected_model=self.test_model,
            expected_version=self.test_version,
        )
        self.assertIsNotNone(loaded_col)
        self.assertEqual(new_store.count(), 2)

        # Xác thực bản ghi nạp lại trùng khớp 100%
        rec1 = new_store.get_by_id("chunk_persist_1")
        self.assertIsNotNone(rec1)
        self.assertEqual(rec1["document"], "Văn bản lưu bền vững 1")
        self.assertEqual(rec1["metadata"]["tag"], "p1")

    def test_06_metadata_preservation(self):
        """6. Kiểm thử bảo toàn trọn vẹn toàn bộ 21 trường metadata bao gồm cả các trường null."""
        self.store.create_collection(
            name=self.collection_name,
            embedding_dimension=self.test_dim,
            embedding_model=self.test_model,
        )

        target_id = "FULL_METADATA_CHUNK_0"
        full_meta = {
            "document_id": "BLLD_2019",
            "document_number": "45/2019/QH14",
            "document_title": "Bộ luật Lao động 2019 số 45/2019/QH14",
            "document_type": "Bộ luật",
            "chapter_number": "Chương I",
            "chapter_title": "NHỮNG QUY ĐỊNH CHUNG",
            "section_number": None,  # Null trường
            "section_title": None,   # Null trường
            "article_number": "Điều 1",
            "article_title": "Phạm vi điều chỉnh",
            "clause_number": None,   # Null trường
            "point_number": None,    # Null trường
            "effective_from": "01/01/2021",
            "effective_to": None,    # Null trường
            "legal_status": "Còn hiệu lực",
            "source_url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-Luat-lao-dong-2019-333670.aspx",
            "parent_document": "BLLD_2019",
            "parent_article": "BLLD_2019_Điều1",
            "chunk_index": 0,
        }

        self.store.upsert(
            ids=[target_id],
            embeddings=[[0.1] * self.test_dim],
            documents=["Nội dung Điều 1..."],
            metadatas=[full_meta],
        )

        record = self.store.get_by_id(target_id, restore_none=True)
        self.assertIsNotNone(record)
        retrieved_meta = record["metadata"]

        # Kiểm tra các trường có giá trị
        self.assertEqual(retrieved_meta["document_number"], "45/2019/QH14")
        self.assertEqual(retrieved_meta["document_type"], "Bộ luật")
        self.assertEqual(retrieved_meta["article_number"], "Điều 1")
        self.assertEqual(retrieved_meta["article_title"], "Phạm vi điều chỉnh")
        self.assertEqual(retrieved_meta["legal_status"], "Còn hiệu lực")
        self.assertEqual(retrieved_meta["chunk_index"], 0)

        # Kiểm tra các trường null được khôi phục chính xác là None
        self.assertIsNone(retrieved_meta["section_number"])
        self.assertIsNone(retrieved_meta["section_title"])
        self.assertIsNone(retrieved_meta["clause_number"])
        self.assertIsNone(retrieved_meta["point_number"])
        self.assertIsNone(retrieved_meta["effective_to"])

    def test_07_duplicate_id_behavior(self):
        """7. Kiểm thử hành vi khi trùng lặp ID (bảo đảm nghiêm ngặt 1 vector / chunk)."""
        self.store.create_collection(
            name=self.collection_name,
            embedding_dimension=self.test_dim,
            embedding_model=self.test_model,
        )

        # Trường hợp A: Cùng 1 ID nạp qua 2 lệnh upsert riêng biệt -> Update nội dung, count giữ nguyên 1
        id_a = "DUP_TEST_CHUNK_A"
        self.store.upsert(
            ids=[id_a],
            embeddings=[[0.1] * self.test_dim],
            documents=["Phiên bản cũ"],
            metadatas=[{"version": 1}],
        )
        self.assertEqual(self.store.count(), 1)

        self.store.upsert(
            ids=[id_a],
            embeddings=[[0.9] * self.test_dim],
            documents=["Phiên bản mới"],
            metadatas=[{"version": 2}],
        )
        self.assertEqual(self.store.count(), 1)  # Không tăng count, vẫn là 1 vector/chunk
        rec_a = self.store.get_by_id(id_a)
        self.assertEqual(rec_a["document"], "Phiên bản mới")
        self.assertEqual(rec_a["metadata"]["version"], 2)

        # Trường hợp B: Trùng lặp ID trong CÙNG MỘT BATCH upsert
        # Với deduplicate_batch=True (mặc định), hệ thống tự giữ bản ghi sau cùng, không gây crash
        id_b = "DUP_TEST_CHUNK_B"
        batch_ids = [id_b, id_b]
        batch_embs = [[0.2] * self.test_dim, [0.8] * self.test_dim]
        batch_docs = ["Batch cũ", "Batch mới nhất"]
        batch_metas = [{"step": "old"}, {"step": "latest"}]

        upserted_count = self.store.upsert(
            ids=batch_ids,
            embeddings=batch_embs,
            documents=batch_docs,
            metadatas=batch_metas,
            deduplicate_batch=True,
        )
        self.assertEqual(upserted_count, 1)
        self.assertEqual(self.store.count(), 2)  # Tổng cộng gồm id_a và id_b
        rec_b = self.store.get_by_id(id_b)
        self.assertEqual(rec_b["document"], "Batch mới nhất")
        self.assertEqual(rec_b["metadata"]["step"], "latest")

    def test_08_dimension_mismatch_fail_fast(self):
        """8. Kiểm thử cơ chế FAIL FAST khi kích thước vector không khớp."""
        self.store.create_collection(
            name=self.collection_name,
            embedding_dimension=8,  # Yêu cầu 8 chiều
            embedding_model=self.test_model,
        )

        # Nạp vector có 7 chiều (thiếu chiều) -> Phải raise DimensionMismatchError ngay lập tức
        with self.assertRaises(DimensionMismatchError) as ctx1:
            self.store.upsert(
                ids=["err_chunk_1"],
                embeddings=[[0.1] * 7],
                documents=["Nội dung lỗi dimension"],
            )
        self.assertIn("FAIL FAST", str(ctx1.exception))
        self.assertIn("không khớp", str(ctx1.exception))

        # Nạp vector có 10 chiều (thừa chiều) -> Phải raise DimensionMismatchError ngay lập tức
        with self.assertRaises(DimensionMismatchError) as ctx2:
            self.store.upsert(
                ids=["err_chunk_2"],
                embeddings=[[0.1] * 10],
                documents=["Nội dung lỗi thừa dimension"],
            )
        self.assertIn("FAIL FAST", str(ctx2.exception))

        # Thử nạp collection với expected_dimension sai khác
        with self.assertRaises(DimensionMismatchError):
            self.store.load_collection(
                name=self.collection_name,
                expected_dimension=1024,  # Collection hiện tại là 8
            )

    def test_09_empty_dataset(self):
        """9. Kiểm thử xử lý an toàn khi truyền dataset/danh sách rỗng."""
        self.store.create_collection(
            name=self.collection_name,
            embedding_dimension=self.test_dim,
            embedding_model=self.test_model,
        )

        # Upsert rỗng
        result = self.store.upsert(
            ids=[],
            embeddings=[],
            documents=[],
            metadatas=[],
        )
        self.assertEqual(result, 0)
        self.assertEqual(self.store.count(), 0)

        # Upsert records rỗng
        res_records = self.store.upsert_records([])
        self.assertEqual(res_records, 0)
        self.assertEqual(self.store.count(), 0)

    def test_10_delete_collection_confirmation(self):
        """10. Kiểm thử xóa collection bắt buộc phải có cờ xác nhận tường minh confirm=True."""
        col_to_delete = "collection_to_be_deleted"
        self.store.create_collection(
            name=col_to_delete,
            embedding_dimension=self.test_dim,
            embedding_model=self.test_model,
        )
        self.assertIn(col_to_delete, self.store.list_collections())

        # Gọi delete_collection không có confirm hoặc confirm=False -> Phải raise PermissionError
        with self.assertRaises(PermissionError):
            self.store.delete_collection(name=col_to_delete, confirm=False)

        # Collection vẫn phải còn nguyên
        self.assertIn(col_to_delete, self.store.list_collections())

        # Gọi với confirm=True -> Xóa thành công
        self.store.delete_collection(name=col_to_delete, confirm=True)
        self.assertNotIn(col_to_delete, self.store.list_collections())

    def test_11_compatibility_validation(self):
        """11. Kiểm thử xác thực tính tương thích của model và dataset version (FAIL FAST)."""
        self.store.create_collection(
            name=self.collection_name,
            embedding_dimension=self.test_dim,
            embedding_model="BAAI/bge-m3",
            dataset_version="v2.1",
        )

        # Tải collection với model không khớp -> CompatibilityError
        with self.assertRaises(CompatibilityError) as ctx1:
            self.store.load_collection(
                name=self.collection_name,
                expected_model="text-embedding-3-small",
            )
        self.assertIn("FAIL FAST", str(ctx1.exception))

        # Tải collection với dataset version không khớp -> CompatibilityError
        with self.assertRaises(CompatibilityError) as ctx2:
            self.store.load_collection(
                name=self.collection_name,
                expected_version="v1.0",
            )
        self.assertIn("FAIL FAST", str(ctx2.exception))

    def test_12_vector_record_helper(self):
        """12. Kiểm thử lớp VectorRecord và phương thức upsert_records."""
        self.store.create_collection(
            name=self.collection_name,
            embedding_dimension=self.test_dim,
            embedding_model=self.test_model,
        )

        rec = VectorRecord(
            id="RECORD_TEST_1",
            embedding=[0.42] * self.test_dim,
            document="Văn bản test VectorRecord",
            metadata={"test_key": "test_val", "nullable": None},
        )
        count = self.store.upsert_records([rec])
        self.assertEqual(count, 1)

        fetched = self.store.get_by_id("RECORD_TEST_1", restore_none=True)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["id"], "RECORD_TEST_1")
        self.assertEqual(fetched["metadata"]["test_key"], "test_val")
        self.assertIsNone(fetched["metadata"]["nullable"])

    def test_13_real_dataset_v2_sample_ingestion(self):
        """13. Kiểm thử tích hợp nạp dữ liệu thực tế trích từ legal_dataset_v2.json."""
        dataset_path = "Data_Processing/output_v2/legal_dataset_v2.json"
        if not os.path.exists(dataset_path):
            self.skipTest(f"Không tìm thấy tệp dataset tại {dataset_path}")

        # Đọc 5 chunks đầu tiên từ dataset V2.1
        with open(dataset_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        sample_chunks = raw_data[:5]

        # Khởi tạo collection với số chiều chuẩn của BAAI/bge-m3 (1024 chiều)
        real_dim = 1024
        col = self.store.create_collection(
            name="real_sample_bge_m3",
            embedding_dimension=real_dim,
            embedding_model="BAAI/bge-m3",
            dataset_version="v2.1",
            overwrite=True,
        )

        records: List[VectorRecord] = []
        for idx, chunk in enumerate(sample_chunks):
            # Tạo vector giả lập 1024 chiều với giá trị xác định
            simulated_vector = [(idx + 1) * 0.001 * (j % 10) for j in range(real_dim)]
            rec = VectorRecord.from_dict(chunk, simulated_vector)
            records.append(rec)

        upserted = self.store.upsert_records(records)
        self.assertEqual(upserted, 5)
        self.assertEqual(self.store.count(), 5)

        # Kiểm tra chunk đầu tiên: BLLD_2019_Điều1_0
        first_id = sample_chunks[0]["chunk_id"]
        first_record = self.store.get_by_id(first_id, restore_none=True)
        self.assertIsNotNone(first_record)
        self.assertEqual(first_record["id"], first_id)
        self.assertIn("Điều 1. Phạm vi điều chỉnh", first_record["document"])
        self.assertEqual(first_record["metadata"]["document_id"], "BLLD_2019")
        self.assertEqual(first_record["metadata"]["article_number"], "Điều 1")
        self.assertEqual(len(first_record["embedding"]), real_dim)

    def test_14_integration_with_rag01_embeddings(self):
        """14. Kiểm thử tích hợp trực tiếp giữa RAG.embedding (RAG-01) và PersistentChromaStore."""
        from RAG.embedding import LegalEmbeddingPipeline, ONNXEmbeddingProvider

        dataset_path = "Data_Processing/output_v2/legal_dataset_v2.json"
        if not os.path.exists(dataset_path):
            self.skipTest(f"Không tìm thấy tệp dataset tại {dataset_path}")

        with open(dataset_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        sample_chunks = raw_data[:5]

        provider = ONNXEmbeddingProvider(device="cpu", batch_size=5)
        pipeline = LegalEmbeddingPipeline(provider=provider)
        embedded_chunks = pipeline.process_chunks(sample_chunks)

        self.store.create_collection(
            name="integration_test_rag01",
            embedding_dimension=provider.dimension,
            embedding_model=provider.model_name,
            dataset_version="v2.1",
            overwrite=True,
        )

        ids = [c.chunk_id for c in embedded_chunks]
        embs = [c.embedding for c in embedded_chunks]
        docs = [c.content for c in embedded_chunks]
        metas = [c.metadata for c in embedded_chunks]

        upserted = self.store.upsert(ids=ids, embeddings=embs, documents=docs, metadatas=metas)
        self.assertEqual(upserted, 5)
        self.assertEqual(self.store.count(), 5)

        for i, cid in enumerate(ids):
            rec = self.store.get_by_id(cid, restore_none=True)
            self.assertIsNotNone(rec)
            self.assertEqual(rec["id"], cid)
            self.assertEqual(rec["document"], docs[i])
            self.assertEqual(len(rec["embedding"]), provider.dimension)
            self.assertIn("document_id", rec["metadata"])
            self.assertIn("content_type", rec["metadata"])


if __name__ == "__main__":
    unittest.main()
