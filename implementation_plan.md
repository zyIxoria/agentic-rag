# Implementation Plan - TASK RAG-01: Build Legal Dataset Embedding Pipeline

## 1. Overview
Triển khai phân hệ Embedding Pipeline (TASK RAG-01) cho Legal Dataset V2.1 (`Data_Processing/output_v2/legal_dataset_v2.json`) phục vụ Traditional RAG Baseline đã được freeze tại RAG-00.

Pipeline:
```text
Dataset V2.1 (1,390 chunks)
         ↓
Read chunks & Validate
         ↓
Extract text content
         ↓
Embedding Model (Batching + Normalization + CPU fallback)
         ↓
Vectors + 18 Preserved Metadata Fields
```

Ràng buộc nghiêm ngặt:
- **CHỈ làm Embedding**: Không triển khai Vector DB (đã hoàn tất ở RAG-02), không làm retrieval, không làm LLM generation.
- **Không sửa đổi Dataset V2.1**: Giữ nguyên vẹn `Data_Processing/output_v2/legal_dataset_v2.json`.

---

## 2. User Review Required

> [!IMPORTANT]
> **Embedding Model & Runtime Environment**:
> Hệ điều hành đang chạy Python 3.13.0 trên Windows 11. Thư viện `torch` và `sentence-transformers` chưa có bản phát hành ổn định cho Python 3.13 trên PyPI. Tuy nhiên, hệ thống đã cài đặt sẵn `onnxruntime` (1.29.0), `tokenizers` (0.23.2) và `chromadb` (1.5.9), hỗ trợ cực kỳ mượt mà mô hình cục bộ `all-MiniLM-L6-v2` (384 dimensions) qua ONNX runtime.
> 
> Thiết kế của chúng tôi cung cấp kiến trúc **Provider mở rộng (Extensible Provider Pattern)**:
> 1. `ONNXEmbeddingProvider` / `ChromaDefaultEmbeddingProvider`: Chạy offline tức thì bằng ONNX runtime (`all-MiniLM-L6-v2`, 384d).
> 2. `SentenceTransformerEmbeddingProvider`: Tự động kích hoạt khi có `sentence-transformers` (e.g. `BAAI/bge-m3`, 1024d).
> 3. `OpenAIEmbeddingProvider`: Sẵn sàng cho cloud API (`text-embedding-3-small`, 1536d) qua `requests`/`httpx`.
> 4. `DeterministicMockEmbeddingProvider`: Dành riêng cho testing tốc độ cao, deterministic và cô lập.
> 
> Tất cả các provider đều tuân thủ kiểm tra thiết bị: nếu cấu hình `EMBEDDING_DEVICE="cuda"` nhưng CUDA runtime không khả dụng, hệ thống tự động ghi log cảnh báo và **fallback an toàn về CPU**.

---

## 3. Proposed Changes

### Configuration
#### [NEW] [`RAG/config.py`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/config.py)
- Khai báo lớp cấu hình `EmbeddingConfig` (kế thừa `BaseSettings` / Pydantic V2):
  - `EMBEDDING_MODEL`: Tên định danh mô hình (mặc định `"sentence-transformers/all-MiniLM-L6-v2"` hoặc cấu hình tùy chọn như `"BAAI/bge-m3"`).
  - `EMBEDDING_DEVICE`: Thiết bị tính toán (`"cuda"`, `"cpu"`, `"auto"`).
  - `EMBEDDING_BATCH_SIZE`: Kích thước lô xử lý (mặc định `64`).
  - `NORMALIZE_EMBEDDINGS`: Chuẩn hóa véc-tơ L2 (`True`).
  - `DATASET_PATH`: Đường dẫn tới Dataset V2.1 (`"Data_Processing/output_v2/legal_dataset_v2.json"`).
- Hàm tiện ích `resolve_device(requested_device: str) -> str`: Kiểm tra khả năng hỗ trợ CUDA, tự động fallback sang CPU và ghi warning log nếu thiếu GPU/CUDA.

---

### Data Schema & Metadata Preservation
#### [NEW] [`RAG/embedding/schema.py`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/embedding/schema.py)
- `EmbeddedChunk`: Lớp dữ liệu chứa:
  - `chunk_id`: Định danh duy nhất toàn cục.
  - `embedding`: Vector véc-tơ (`List[float]`).
  - `content`: Văn bản đoạn luật gốc.
  - `metadata`: Dictionary chứa đầy đủ các thuộc tính.
- Đảm bảo 18 trường metadata bắt buộc không bao giờ bị mất:
  1. `chunk_id`
  2. `document_id`
  3. `document_number`
  4. `document_title`
  5. `document_type`
  6. `chapter_number`
  7. `chapter_title`
  8. `article_number`
  9. `article_title`
  10. `clause_number`
  11. `point_number`
  12. `content_type`
  13. `effective_from`
  14. `effective_to`
  15. `legal_status`
  16. `source_url`
  17. `parent_document`
  18. `parent_article`
- Hàm kiểm thực `validate_metadata_preservation(source_record, embedded_chunk)`.

---

### Embedding Module & Pipeline
#### [NEW] [`RAG/embedding/embeddings.py`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/embedding/embeddings.py)
- Interface chuẩn:
  - `embed_text(text: str) -> List[float]`
  - `embed_texts(texts: List[str]) -> List[List[float]]`
  - Thuộc tính `dimension: int`, `model_name: str`, `device: str`.
- Các provider:
  - `BaseEmbeddingProvider` (Abstract Base Class).
  - `ONNXEmbeddingProvider` (Chroma/ONNX runtime, default).
  - `SentenceTransformerEmbeddingProvider` (hỗ trợ HuggingFace nếu có thư viện).
  - `OpenAIEmbeddingProvider` (hỗ trợ REST API).
  - `DeterministicMockEmbeddingProvider` (hỗ trợ unit test nhanh).
- Factory method:
  - `get_embedding_provider(config: EmbeddingConfig) -> BaseEmbeddingProvider`.
- Lớp điều phối pipeline:
  - `LegalEmbeddingPipeline`: Đọc Dataset V2.1, trích xuất `content`, nhúng theo batch kích thước `EMBEDDING_BATCH_SIZE`, giữ 100% metadata, trả về danh sách `EmbeddedChunk`.

#### [NEW] [`RAG/embedding/__init__.py`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/embedding/__init__.py)
- Export các public API: `BaseEmbeddingProvider`, `ONNXEmbeddingProvider`, `get_embedding_provider`, `LegalEmbeddingPipeline`, `EmbeddedChunk`, `EmbeddingConfig`.

---

### Unit Tests
#### [NEW] [`tests/embedding/__init__.py`](file:///d:/Filehoc/KLCN/agentic-rag/tests/embedding/__init__.py)
#### [NEW] [`tests/embedding/test_embedding.py`](file:///d:/Filehoc/KLCN/agentic-rag/tests/embedding/test_embedding.py)
Bộ kiểm thử toàn diện bao gồm:
1. `test_single_text_embedding`: Nhúng 1 chuỗi văn bản, kiểm tra kiểu trả về `List[float]` và dimension > 0.
2. `test_batch_embedding`: Nhúng danh sách texts (nhiều hơn batch size), kiểm tra số lượng và thứ tự vectors.
3. `test_vector_dimension_consistency`: Kiểm tra tất cả vector sinh ra (single & batch) có chiều dài bằng nhau tuyệt đối.
4. `test_empty_content_handling`: Kiểm tra xử lý chuỗi rỗng `""` hoặc chỉ chứa khoảng trắng `"   "` (ném ngoại lệ `ValueError` có thông điệp rõ ràng).
5. `test_deterministic_output`: Kiểm tra nhúng cùng 1 text sinh ra vector tương đương nhau với cấu hình cố định.
6. `test_metadata_preservation`: Kiểm tra 18 trường metadata gốc của Dataset V2.1 được giữ nguyên 100%.
7. `test_device_fallback_behavior`: Kiểm tra khi yêu cầu `cuda` mà không có CUDA, hệ thống fallback về `cpu` và log cảnh báo.
8. `test_pipeline_run_on_sample`: Chạy pipeline thực tế trên mẫu chunk từ Dataset V2.1.

---

### Dataset Embedding Run & Reports
#### [NEW] [`reports/rag/RAG-01-EMBEDDING.json`](file:///d:/Filehoc/KLCN/agentic-rag/reports/rag/RAG-01-EMBEDDING.json)
- Báo cáo số liệu máy đọc (JSON): Model, dimension, total documents, total chunks embedded, failed chunks, device, batch size, tests status, checksum.
#### [NEW] [`reports/rag/RAG-01-EMBEDDING.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/rag/RAG-01-EMBEDDING.md)
- Báo cáo tài liệu markdown chi tiết toàn diện tương tự phong cách chuẩn mực của `RAG-00` và `RAG-02`.

---

## 4. Verification Plan

### Automated Tests
- Chạy toàn bộ test suite trong `tests/embedding/`:
  ```bash
  python -m unittest discover -s tests/embedding -p "test_*.py" -v
  ```
- Chạy kiểm tra tích hợp toàn bộ Dataset V2.1 (1,390 chunks) thông qua script thẩm định:
  - Xác nhận 1,390/1,390 chunks được nhúng thành công (0 failed chunks).
  - Xác nhận không có NaN hoặc inf trong vector.
  - Xác nhận bảo tồn đủ 18 trường metadata cho 1,390 chunks.

### Manual / Sanity Checks
- Kiểm tra `git status` đảm bảo không có file nào ngoài phạm vi được phép bị sửa đổi, đặc biệt là `Data_Processing/output_v2/legal_dataset_v2.json` không bị thay đổi.
