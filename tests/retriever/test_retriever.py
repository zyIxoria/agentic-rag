"""test_retriever.py - Bộ kiểm thử toàn diện cho phân hệ Dense Top-K Retriever (TASK RAG-03).

Kiểm thử 8 yêu cầu bắt buộc + 5 legal fixture queries:
1. exact legal query
2. semantic paraphrase
3. top-k correctness
4. score ordering
5. metadata preservation
6. empty query
7. top_k > corpus size
8. threshold filtering
9. score definition (Cosine Similarity = 1 - Cosine Distance)
10. legal fixture queries suite (5 benchmarks)
"""

from __future__ import annotations
import os
import unittest
import time
from typing import List, Dict, Any

from RAG.retriever.schema import RetrievedChunk
from RAG.retriever.config import RetrieverConfig
from RAG.retriever.dense_retriever import DenseTopKRetriever
from RAG.vector_store.chroma_store import PersistentChromaStore
from RAG.embedding.embeddings import ONNXEmbeddingProvider, DeterministicMockEmbeddingProvider
from RAG.embedding.schema import MANDATORY_METADATA_FIELDS


class TestDenseTopKRetriever(unittest.TestCase):
    """Bộ kiểm thử cho DenseTopKRetriever."""

    @classmethod
    def setUpClass(cls):
        """Khởi tạo Retriever kết nối với cơ sở dữ liệu ChromaDB hiện có."""
        cls.persist_dir = "data/chroma_db"
        cls.collection_name = "legal_labor_baseline_minilm"

        if not os.path.exists(cls.persist_dir):
            raise unittest.SkipTest(f"Cơ sở dữ liệu tại {cls.persist_dir} chưa được tạo (cần chạy RAG-02).")

        cls.provider = ONNXEmbeddingProvider(device="cpu")
        cls.store = PersistentChromaStore(persist_directory=cls.persist_dir)
        cls.store.load_collection(
            name=cls.collection_name,
            expected_dimension=cls.provider.dimension,
            expected_model=cls.provider.model_name,
        )

        cls.config = RetrieverConfig(
            TOP_K=5,
            SIMILARITY_THRESHOLD=None,
            PERSIST_DIRECTORY=cls.persist_dir,
            COLLECTION_NAME=cls.collection_name,
        )
        cls.retriever = DenseTopKRetriever(
            vector_store=cls.store,
            embedding_provider=cls.provider,
            config=cls.config,
        )

    # 1. Exact Legal Query
    def test_01_exact_legal_query(self):
        """1. Kiểm thử truy vấn chứa câu chữ pháp lý chính xác."""
        query = "Áp dụng hình thức xử lý kỷ luật sa thải"
        results = self.retriever.retrieve(query, top_k=5)

        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 5)

        # Kiểm tra nội dung trả về có liên quan tới sa thải hoặc kỷ luật
        top1 = results[0]
        self.assertIsInstance(top1, RetrievedChunk)
        self.assertGreater(top1.score, 0.6)
        all_text = " ".join([c.content for c in results])
        self.assertTrue("sa thải" in all_text.lower() or "kỷ luật" in all_text.lower())

    # 2. Semantic Paraphrase
    def test_02_semantic_paraphrase(self):
        """2. Kiểm thử truy vấn diễn đạt tự nhiên (paraphrase) không trùng khớp 100% từ khóa."""
        query = "Làm việc thử thách tay nghề trước khi ký hợp đồng chính thức thì kéo dài tối đa bao lâu?"
        results = self.retriever.retrieve(query, top_k=5)

        self.assertEqual(len(results), 5)
        top_chunk = results[0]
        # Kết quả ngữ nghĩa phải phản ánh nội dung thử việc hoặc hợp đồng lao động
        all_text = " ".join([c.content for c in results]).lower()
        self.assertTrue("thử việc" in all_text or "hợp đồng" in all_text)

    # 3. Top-K Correctness
    def test_03_top_k_correctness(self):
        """3. Kiểm thử tính chính xác của tham số top_k."""
        query = "Thời giờ làm việc bình thường của người lao động"
        for k in [1, 3, 5, 8]:
            res = self.retriever.retrieve(query, top_k=k)
            self.assertEqual(len(res), k, f"Kỳ vọng {k} kết quả, nhưng nhận được {len(res)}")
            for idx, item in enumerate(res, start=1):
                self.assertEqual(item.rank, idx)

    # 4. Score Ordering
    def test_04_score_ordering(self):
        """4. Kiểm thử tính sắp xếp giảm dần của điểm tương đồng score."""
        query = "Quy định về thời giờ nghỉ ngơi và nghỉ lễ tết"
        results = self.retriever.retrieve(query, top_k=5)

        self.assertGreaterEqual(len(results), 2)
        for i in range(len(results) - 1):
            self.assertGreaterEqual(
                results[i].score,
                results[i + 1].score,
                f"Lỗi sắp xếp thứ hạng: Rank {results[i].rank} ({results[i].score}) < Rank {results[i+1].rank} ({results[i+1].score})"
            )

    # 5. Metadata Preservation
    def test_05_metadata_preservation(self):
        """5. Kiểm thử bảo tồn trọn vẹn 18 trường metadata bắt buộc kèm giá trị None."""
        query = "Người sử dụng lao động có quyền sa thải trong trường hợp nào?"
        results = self.retriever.retrieve(query, top_k=3)

        for chunk in results:
            meta = chunk.metadata
            self.assertIsInstance(meta, dict)
            # Xác nhận có đầy đủ các trường bắt buộc
            for field in MANDATORY_METADATA_FIELDS:
                self.assertIn(field, meta, f"Thiếu trường '{field}' trong metadata của chunk {chunk.chunk_id}!")
            # Xác nhận chunk_id khớp
            self.assertEqual(chunk.chunk_id, meta["chunk_id"])
            # Xác nhận document_id hợp lệ
            self.assertTrue(len(str(meta["document_id"])) > 0)

    # 6. Empty Query Handling
    def test_06_empty_query_handling(self):
        """6. Kiểm thử xử lý câu truy vấn rỗng hoặc chỉ có khoảng trắng (FAIL FAST với ValueError)."""
        with self.assertRaises(ValueError) as ctx1:
            self.retriever.retrieve("")
        self.assertIn("không được để rỗng", str(ctx1.exception))

        with self.assertRaises(ValueError) as ctx2:
            self.retriever.retrieve("   \t\n  ")
        self.assertIn("không được để rỗng", str(ctx2.exception))

        with self.assertRaises(ValueError) as ctx3:
            self.retriever.retrieve("hợp lệ", top_k=0)
        self.assertIn("top_k phải là số nguyên dương", str(ctx3.exception))

    # 7. Top-K Greater Than Corpus Size
    def test_07_top_k_greater_than_corpus_size(self):
        """7. Kiểm thử khi yêu cầu top_k lớn hơn toàn bộ quy mô corpus."""
        total_chunks = self.store.count()
        query = "Bộ luật lao động"
        # Yêu cầu k = total_chunks + 500
        res = self.retriever.retrieve(query, top_k=total_chunks + 500)
        self.assertEqual(len(res), total_chunks)
        self.assertEqual(res[0].rank, 1)
        self.assertEqual(res[-1].rank, total_chunks)

    # 8. Threshold Filtering
    def test_08_threshold_filtering(self):
        """8. Kiểm thử lọc theo ngưỡng tương đồng score_threshold."""
        query = "Tiền lương làm thêm giờ vào ban đêm"

        # Khi không đặt threshold -> trả về đủ 5
        res_no_thresh = self.retriever.retrieve(query, top_k=5, score_threshold=None)
        self.assertEqual(len(res_no_thresh), 5)
        top1_score = res_no_thresh[0].score

        # Đặt threshold bằng đúng top1_score + 0.001 -> kỳ vọng 0 kết quả
        res_strict = self.retriever.retrieve(query, top_k=5, score_threshold=top1_score + 0.001)
        self.assertEqual(len(res_strict), 0)

        # Đặt threshold hợp lý (ví dụ 0.6) -> tất cả kết quả trả về phải có score >= 0.6
        res_filtered = self.retriever.retrieve(query, top_k=5, score_threshold=0.6)
        for c in res_filtered:
            self.assertGreaterEqual(c.score, 0.6)

    # 9. Score & Metric Definition
    def test_09_score_similarity_definition(self):
        """9. Kiểm thử phân định rạch ròi giữa Distance và Similarity (score = 1.0 - distance)."""
        query = "Nghỉ hằng năm của người lao động làm việc trong điều kiện bình thường"
        results = self.retriever.retrieve(query, top_k=5)

        for c in results:
            self.assertIsNotNone(c.distance)
            expected_sim = round(1.0 - c.distance, 6)
            self.assertAlmostEqual(c.score, expected_sim, places=5)
            # Cosine similarity phải thuộc khoảng [-1.0, 1.0]
            self.assertGreaterEqual(c.score, -1.0)
            self.assertLessEqual(c.score, 1.0)

    # 10. Legal Fixture Queries Suite (5 Benchmarks)
    def test_10_legal_fixture_suite(self):
        """10. Chạy benchmark 5 câu hỏi pháp lý mẫu và kiểm tra tính liên quan và độ trễ."""
        fixtures = [
            {
                "id": "Q1_DISMISSAL",
                "query": "Áp dụng hình thức xử lý kỷ luật sa thải",
                "expected_topic": ["sa thải", "kỷ luật", "lao động", "124", "125"],
            },
            {
                "id": "Q2_WORK_HOURS",
                "query": "Thời giờ làm việc bình thường của người lao động",
                "expected_topic": ["thời giờ làm việc", "người lao động", "làm việc", "105", "158"],
            },
            {
                "id": "Q3_PROBATION",
                "query": "Thời gian thử việc đối với công việc",
                "expected_topic": ["thử việc", "công việc", "thời hạn", "lao động"],
            },
            {
                "id": "Q4_MATERNITY",
                "query": "Lao động nữ được nghỉ thai sản",
                "expected_topic": ["thai sản", "lao động nữ", "nghỉ thai sản", "139"],
            },
            {
                "id": "Q5_OVERTIME_PAY",
                "query": "Tiền lương làm thêm giờ của người lao động",
                "expected_topic": ["làm thêm giờ", "tiền lương", "trả lương", "107", "95", "98"],
            },
        ]

        # Warmup trước khi đo kiểm độ trễ
        self.retriever.retrieve("Khởi động mô hình kiểm thử", top_k=1)

        latencies = []
        for fix in fixtures:
            t0 = time.perf_counter()
            results = self.retriever.retrieve(fix["query"], top_k=5)
            lat = (time.perf_counter() - t0) * 1000
            latencies.append(lat)

            self.assertEqual(len(results), 5)
            top1 = results[0]
            self.assertGreater(top1.score, 0.5)

            # Kiểm tra xem có xuất hiện từ khóa chủ đề trong top kết quả
            combined_text = " ".join([c.content + " " + (c.metadata.get("article_title") or "") for c in results]).lower()
            topic_matched = any(kw.lower() in combined_text for kw in fix["expected_topic"])
            self.assertTrue(topic_matched, f"Fixture {fix['id']} không tìm thấy từ khóa chủ đề mong đợi.")

        avg_latency = sum(latencies) / len(latencies)
        # Độ trễ trung bình kiểm soát trong ngưỡng chấp nhận được của môi trường CPU (< 500ms)
        self.assertLess(avg_latency, 500.0, f"Độ trễ trung bình quá cao: {avg_latency:.2f} ms")
        self.assertGreater(avg_latency, 0.0)


if __name__ == "__main__":
    unittest.main()
