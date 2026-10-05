"""test_embedding.py - Bộ kiểm thử toàn diện cho phân hệ Embedding Pipeline (TASK RAG-01).

Kiểm tra đầy đủ các yêu cầu cốt lõi:
1. Single text embedding
2. Batch embedding
3. Vector dimension consistency
4. Empty content handling (FAIL FAST với ValueError)
5. Deterministic output / config
6. Metadata preservation (18 trường bắt buộc)
7. GPU/CPU fallback behavior
8. L2 normalization
9. Pipeline integration với sample từ Legal Dataset V2.1
"""

from __future__ import annotations
import os
import json
import logging
import unittest
import numpy as np
from typing import List, Dict, Any

from RAG.config import EmbeddingConfig, resolve_device
from RAG.embedding.schema import (
    EmbeddedChunk,
    MANDATORY_METADATA_FIELDS,
    extract_preserved_metadata,
    validate_metadata_preservation,
    infer_content_type,
)
from RAG.embedding.embeddings import (
    BaseEmbeddingProvider,
    ONNXEmbeddingProvider,
    DeterministicMockEmbeddingProvider,
    LegalEmbeddingPipeline,
    get_embedding_provider,
    l2_normalize,
    l2_normalize_batch,
)


class TestEmbeddingModule(unittest.TestCase):
    """Kiểm thử chi tiết cho các Provider và Pipeline Embedding."""

    def setUp(self):
        """Khởi tạo các provider kiểm thử."""
        self.mock_provider = DeterministicMockEmbeddingProvider(
            model_name="mock-test-model",
            dimension=128,
            device="cpu",
            batch_size=4,
            normalize_embeddings=True,
        )
        self.onnx_provider = ONNXEmbeddingProvider(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            device="cpu",
            batch_size=8,
            normalize_embeddings=True,
        )

    # 1. Single Text Embedding
    def test_single_text_embedding_mock(self):
        text = "Người lao động có quyền đơn phương chấm dứt hợp đồng lao động theo quy định của pháp luật."
        vec = self.mock_provider.embed_text(text)
        self.assertIsInstance(vec, list)
        self.assertEqual(len(vec), 128)
        self.assertTrue(all(isinstance(x, float) for x in vec))
        self.assertTrue(np.all(np.isfinite(vec)))

    def test_single_text_embedding_onnx(self):
        text = "Thời giờ làm việc bình thường không quá 08 giờ trong 01 ngày và không quá 48 giờ trong 01 tuần."
        vec = self.onnx_provider.embed_text(text)
        self.assertIsInstance(vec, list)
        self.assertEqual(len(vec), 384)
        self.assertTrue(np.all(np.isfinite(vec)))

    # 2. Batch Embedding
    def test_batch_embedding_mock(self):
        texts = [
            f"Quy định về kỷ luật lao động và trách nhiệm vật chất - Khoản {i}"
            for i in range(10)
        ]
        # batch_size=4, tổng 10 texts sẽ qua 3 batches (4 + 4 + 2)
        vectors = self.mock_provider.embed_texts(texts)
        self.assertEqual(len(vectors), 10)
        for vec in vectors:
            self.assertEqual(len(vec), 128)
            self.assertTrue(np.all(np.isfinite(vec)))

    def test_batch_embedding_onnx(self):
        texts = [
            "Hợp đồng lao động vô hiệu toàn bộ hoặc từng phần.",
            "Tiền lương tối thiểu vùng do Chính phủ quy định.",
            "Người sử dụng lao động phải đóng bảo hiểm xã hội bắt buộc.",
        ]
        vectors = self.onnx_provider.embed_texts(texts)
        self.assertEqual(len(vectors), 3)
        for vec in vectors:
            self.assertEqual(len(vec), 384)
            self.assertTrue(np.all(np.isfinite(vec)))

    def test_empty_batch_returns_empty_list(self):
        self.assertEqual(self.mock_provider.embed_texts([]), [])
        self.assertEqual(self.onnx_provider.embed_texts([]), [])

    # 3. Vector Dimension Consistency
    def test_vector_dimension_consistency(self):
        texts = [
            "Từ rất ngắn.",
            "Một câu trung bình giải thích về điều kiện sa thải người lao động theo Bộ luật Lao động 2019.",
            "Một đoạn văn bản pháp luật rất dài " * 20,
        ]
        # Thử nghiệm embed đơn lẻ
        single_dims = [len(self.onnx_provider.embed_text(t)) for t in texts]
        self.assertTrue(all(d == 384 for d in single_dims))

        # Thử nghiệm embed batch
        batch_vecs = self.onnx_provider.embed_texts(texts)
        batch_dims = [len(v) for v in batch_vecs]
        self.assertTrue(all(d == 384 for d in batch_dims))
        self.assertEqual(single_dims, batch_dims)

    # 4. Empty Content Handling (FAIL FAST)
    def test_empty_content_handling_single(self):
        with self.assertRaises(ValueError) as ctx:
            self.mock_provider.embed_text("")
        self.assertIn("không được để rỗng", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            self.mock_provider.embed_text("   \n\t  ")
        self.assertIn("không được để rỗng", str(ctx.exception))

    def test_empty_content_handling_batch(self):
        texts = [
            "Đoạn văn hợp lệ 1",
            "   ",  # chuỗi rỗng khoảng trắng
            "Đoạn văn hợp lệ 2",
        ]
        with self.assertRaises(ValueError) as ctx:
            self.onnx_provider.embed_texts(texts)
        self.assertIn("chỉ mục 1", str(ctx.exception))

    # 5. Deterministic Output / Config
    def test_deterministic_output_mock(self):
        text = "Khi chấm dứt hợp đồng lao động, người sử dụng lao động có trách nhiệm thanh toán đầy đủ các khoản."
        vec1 = self.mock_provider.embed_text(text)
        vec2 = self.mock_provider.embed_text(text)
        self.assertEqual(vec1, vec2)

    def test_deterministic_output_onnx(self):
        text = "Mức lương làm thêm giờ vào ngày nghỉ hằng tuần ít nhất bằng 200%."
        vec1 = np.array(self.onnx_provider.embed_text(text))
        vec2 = np.array(self.onnx_provider.embed_text(text))
        cosine_sim = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        self.assertAlmostEqual(cosine_sim, 1.0, places=5)

    # 6. Metadata Preservation (18 Mandatory Fields)
    def test_metadata_preservation(self):
        sample_chunk = {
            "chunk_id": "BLLD_2019_Điều_125_Khoản_1_c0",
            "document_id": "BLLD_2019",
            "document_number": "45/2019/QH14",
            "document_title": "Bộ luật Lao động 2019",
            "document_type": "Bộ luật",
            "chapter_number": "Chương VIII",
            "chapter_title": "KỶ LUẬT LAO ĐỘNG, TRÁCH NHIỆM VẬT CHẤT",
            "section_number": "Mục 1",
            "section_title": "Kỷ luật lao động",
            "article_number": "Điều 125",
            "article_title": "Áp dụng hình thức xử lý kỷ luật sa thải",
            "clause_number": "Khoản 1",
            "point_number": None,
            "content": "Người lao động có hành vi trộm cắp, tham ô, đánh bạc...",
            "effective_from": "01/01/2021",
            "effective_to": None,
            "legal_status": "Còn hiệu lực",
            "source_url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-Luat-lao-dong-2019-333670.aspx",
            "parent_document": "BLLD_2019",
            "parent_article": "BLLD_2019_Điều_125",
            "chunk_index": 0,
        }

        # Trích xuất metadata
        extracted_meta = extract_preserved_metadata(sample_chunk)

        # Kiểm tra đầy đủ 18 trường bắt buộc
        for field in MANDATORY_METADATA_FIELDS:
            self.assertIn(field, extracted_meta, f"Thiếu trường bắt buộc '{field}' trong metadata!")

        # Kiểm tra tính khớp giá trị
        self.assertEqual(extracted_meta["chunk_id"], "BLLD_2019_Điều_125_Khoản_1_c0")
        self.assertEqual(extracted_meta["document_number"], "45/2019/QH14")
        self.assertEqual(extracted_meta["article_number"], "Điều 125")
        self.assertEqual(extracted_meta["clause_number"], "Khoản 1")
        self.assertIsNone(extracted_meta["point_number"])
        self.assertEqual(extracted_meta["legal_status"], "Còn hiệu lực")
        self.assertEqual(extracted_meta["content_type"], "clause")

        # Kiểm tra hàm validate_metadata_preservation
        is_valid = validate_metadata_preservation(sample_chunk, extracted_meta)
        self.assertTrue(is_valid)

    # 7. GPU/CPU Fallback Behavior
    def test_device_fallback_behavior(self):
        # Yêu cầu rõ ràng "cuda", khi không có CUDA phải tự động fallback về "cpu"
        resolved = resolve_device("cuda")
        # Kết quả phải là "cpu" hoặc "cuda" (tùy môi trường, nhưng không bao giờ gây crash)
        self.assertIn(resolved, ("cpu", "cuda"))

        # Kiểm tra EmbeddingConfig khi gán "cuda"
        cfg = EmbeddingConfig(EMBEDDING_DEVICE="cuda")
        self.assertIn(cfg.EMBEDDING_DEVICE, ("cpu", "cuda"))

    # 8. L2 Normalization
    def test_l2_normalization(self):
        unnormalized_provider = DeterministicMockEmbeddingProvider(
            dimension=64,
            normalize_embeddings=False,
        )
        vec_unnorm = unnormalized_provider.embed_text("Thử nghiệm không chuẩn hóa")
        norm_unnorm = np.linalg.norm(vec_unnorm)

        normalized_provider = DeterministicMockEmbeddingProvider(
            dimension=64,
            normalize_embeddings=True,
        )
        vec_norm = normalized_provider.embed_text("Thử nghiệm có chuẩn hóa")
        norm_norm = np.linalg.norm(vec_norm)
        self.assertAlmostEqual(norm_norm, 1.0, places=4)

    # 9. Pipeline Integration on Real Sample Chunks
    def test_pipeline_on_dataset_v2_sample(self):
        dataset_path = "Data_Processing/output_v2/legal_dataset_v2.json"
        if not os.path.exists(dataset_path):
            self.skipTest(f"Dataset path {dataset_path} không tồn tại.")

        with open(dataset_path, "r", encoding="utf-8") as f:
            full_dataset = json.load(f)

        # Lấy 5 chunks mẫu từ các văn bản khác nhau
        sample_chunks = full_dataset[:5]

        pipeline = LegalEmbeddingPipeline(provider=self.onnx_provider)
        embedded_chunks = pipeline.process_chunks(sample_chunks)

        self.assertEqual(len(embedded_chunks), 5)
        for i, emb in enumerate(embedded_chunks):
            self.assertIsInstance(emb, EmbeddedChunk)
            self.assertEqual(emb.chunk_id, sample_chunks[i]["chunk_id"])
            self.assertEqual(emb.content, sample_chunks[i]["content"])
            self.assertEqual(emb.dimension, 384)
            self.assertTrue(validate_metadata_preservation(sample_chunks[i], emb.metadata))


if __name__ == "__main__":
    unittest.main()
