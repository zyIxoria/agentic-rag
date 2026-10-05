# BÁO CÁO XÂY DỰNG LEGAL DATASET EMBEDDING PIPELINE (TASK RAG-01)
## Đường Ống Nhúng Véc-Tơ Pháp Lý Chuẩn Hóa Cho Traditional RAG Baseline

* **Mã tác vụ**: `RAG-01`
* **Dự án**: Nghiên cứu cơ chế điều phối thích ứng trong hệ thống Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam
* **Thành phần**: `Legal Dataset Embedding Pipeline`
* **Gói mã nguồn**: [`RAG/embedding/`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/embedding/), [`RAG/config.py`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/config.py)
* **Bộ kiểm thử**: [`tests/embedding/`](file:///d:/Filehoc/KLCN/agentic-rag/tests/embedding/)
* **Ngày hoàn tất**: 2026-09-15
* **Trạng thái**: `PASS (100% Validated & Verified)`

---

## 1. Mục Tiêu & Phạm Vi Thực Thi (Objective & Strict Scope)

Mục tiêu trọng tâm của **TASK RAG-01** là xây dựng đường ống chuyển đổi toàn bộ 1,390 đoạn văn bản pháp luật thuộc **Legal Dataset V2.1** thành các véc-tơ biểu diễn ngữ nghĩa (dense embeddings), chuẩn bị sẵn sàng cho quá trình lưu trữ và lập chỉ mục véc-tơ mà không làm thất thoát bất kỳ trường thuộc tính pháp lý nào.

```text
Legal Dataset V2.1 (1,390 chunks)
              ↓
    Read chunks & Validate
              ↓
     Extract text content
              ↓
  Embedding Model (Batching + L2 Norm + CPU Fallback)
              ↓
  EmbeddedChunk (Vector + 18 Preserved Metadata Fields)
```

### Ràng buộc phạm vi nghiêm ngặt (Strict Scope & Non-Goals):
1. **CHỈ LÀM EMBEDDING**: Thiết lập interface véc-tơ hóa, xử lý batching, chuẩn hóa L2, kiểm soát dimension và bảo tồn siêu dữ liệu.
2. **TUYỆT ĐỐI KHÔNG triển khai Vector DB**: Tầng lưu trữ ChromaDB đã được hoàn thiện độc lập tại `TASK RAG-02`.
3. **TUYỆT ĐỐI KHÔNG triển khai Logic Truy hồi (No Retrieval)**: Không implement `search()`, `similarity_search()`, hay `retrieve()`.
4. **TUYỆT ĐỐI KHÔNG tích hợp LLM (No Generation)**: Không sinh văn bản, không prompt template, không LLM completion.
5. **BẢO TỒN NGUYÊN VẸN DATASET V2.1**: Giữ nguyên tệp `Data_Processing/output_v2/legal_dataset_v2.json`.

---

## 2. Thiết Kế Kiến Trúc & Interface Chuẩn

Hệ thống tuân thủ thiết kế mở rộng (**Provider Pattern**), phân tách rõ ràng giữa cấu hình, hợp đồng giao diện, mô hình nhúng và đường ống xử lý:

### 2.1. Hợp đồng Giao diện (`BaseEmbeddingProvider`)
Định nghĩa tại [`RAG/embedding/embeddings.py`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/embedding/embeddings.py):
```python
class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Tạo vector embedding cho một chuỗi văn bản đơn lẻ."""
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Tạo vector embedding cho danh sách văn bản theo batch."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Kích thước số chiều (dimension) cố định của véc-tơ."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Tên định danh mô hình."""
        pass
```

### 2.2. Các Triển khai Mô hình (Concrete Providers)
1. **`ONNXEmbeddingProvider` (Mặc định Cục bộ)**:
   * Chạy thông qua runtime ONNX nhúng cực nhanh (`onnxruntime 1.29.0`, `tokenizers 0.23.2`).
   * Sử dụng trọng số `all-MiniLM-L6-v2` (384 chiều) đã lưu trữ trong cache cục bộ.
   * Hoàn toàn không phụ thuộc PyTorch wheel cồng kềnh, tương thích hoàn hảo với môi trường Python 3.13 trên Windows.
2. **`SentenceTransformerEmbeddingProvider` (Local Transformer)**:
   * Sẵn sàng tích hợp `BAAI/bge-m3` (1024 chiều) khi môi trường cài đặt gói `sentence-transformers`.
3. **`DeterministicMockEmbeddingProvider` (Mô phỏng Tiền định)**:
   * Tạo vector chuẩn hóa giả lập dựa trên SHA-256 hash của văn bản, bảo đảm tính tiền định (deterministic) 100% phục vụ chạy test độc lập trong môi trường CI/CD không có GPU/mạng.

---

## 3. Cấu Hình & Cơ Chế Fallback Thiết Bị (GPU/CUDA -> CPU Fallback)

Hệ thống quản lý cấu hình thông qua lớp `EmbeddingConfig` tại [`RAG/config.py`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/config.py):

| Tham số cấu hình | Giá trị mặc định | Mô tả & Quy tắc xử lý |
|:---|:---:|:---|
| `EMBEDDING_MODEL` | `"sentence-transformers/all-MiniLM-L6-v2"` | Tên mô hình (không hardcode, có thể ghi đè bằng `BAAI/bge-m3`). |
| `EMBEDDING_DEVICE` | `"cpu"` (hoặc `"cuda"`) | Thiết bị thực thi tính toán. |
| `EMBEDDING_BATCH_SIZE` | `64` | Kích thước lô xử lý khi embedding hàng loạt. |
| `NORMALIZE_EMBEDDINGS` | `True` | Bật chuẩn hóa L2 cho các vector đầu ra (`||v||_2 = 1.0`). |
| `DATASET_PATH` | `"Data_Processing/output_v2/legal_dataset_v2.json"` | Đường dẫn dữ liệu nguồn Dataset V2.1. |

### Cơ chế Fallback An toàn (Fail-Safe Device Fallback):
Hàm `resolve_device()` kiểm tra tính khả dụng thực tế của CUDA runtime qua `torch.cuda.is_available()` hoặc `onnxruntime.get_available_providers()`. Nếu người dùng cấu hình `EMBEDDING_DEVICE="cuda"` nhưng phần cứng hoặc driver runtime không hỗ trợ:
```text
WARNING: Device 'cuda' được yêu cầu nhưng CUDA/GPU runtime không khả dụng hoặc chưa cài đặt driver/wheel tương thích. Tự động fallback về 'cpu'.
```
Hệ thống chuyển trạng thái sang `"cpu"` minh bạch, tiếp tục xử lý mượt mà và không gây crash ứng dụng.

---

## 4. Cơ Chế Bảo Tồn Siêu Dữ Liệu (18 Mandatory Metadata Fields)

Theo yêu cầu của **TASK RAG-01**, pipeline tuyệt đối không được làm mất 18 trường thuộc tính cấu trúc và hiệu lực pháp lý của văn bản:

```python
MANDATORY_METADATA_FIELDS = (
    "chunk_id",
    "document_id",
    "document_number",
    "document_title",
    "document_type",
    "chapter_number",
    "chapter_title",
    "article_number",
    "article_title",
    "clause_number",
    "point_number",
    "content_type",
    "effective_from",
    "effective_to",
    "legal_status",
    "source_url",
    "parent_document",
    "parent_article",
)
```

Mô-đun [`RAG/embedding/schema.py`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/embedding/schema.py) triển khai hai hàm kiểm soát chất lượng:
* **`extract_preserved_metadata(raw_chunk)`**: Sao chép toàn vẹn 100% thuộc tính gốc, chuẩn hóa và suy luận tự động trường `content_type` (`article`, `clause`, `point`, `appendix`), đồng thời bảo toàn các trường mở rộng (`section_number`, `section_title`, `chunk_index`).
* **`validate_metadata_preservation(raw_chunk, metadata)`**: Kiểm tra đối chiếu từng trường giữa dữ liệu nguồn và bản ghi đích. Nếu phát hiện bất kỳ trường nào bị mất hoặc sai lệch giá trị, lập tức kích hoạt `RuntimeError`.

---

## 5. Kết Quả Thẩm Định Trên Toàn Bộ Dataset V2.1 (1,390 Chunks)

Toàn bộ 1,390 chunks thuộc 15 văn bản quy phạm pháp luật trong `legal_dataset_v2.json` đã được chạy thẩm định toàn diện qua `LegalEmbeddingPipeline`:

| Chỉ số thẩm định | Kết quả thực tế | Đánh giá |
|:---|:---:|:---:|
| **Trạng thái tổng thể** | **`PASS`** | Đạt 100% yêu cầu |
| **Mô hình thực thi** | `sentence-transformers/all-MiniLM-L6-v2` | ONNX Runtime nhúng cục bộ |
| **Kích thước số chiều (Dimension)** | **384** | 100% đồng nhất (384 / 384) |
| **Tổng số văn bản nguồn** | **15** văn bản | Đầy đủ 15/15 văn bản luật |
| **Tổng số chunks nạp & xử lý** | **1,390 / 1,390** chunks | 100% dung lượng corpus |
| **Số chunks thất bại (Failed chunks)** | **0** chunks | Không có lỗi phát sinh |
| **Kiểm tra NaN / Inf trong vector** | **0** (Không có) | Tất cả giá trị số thực hữu hạn |
| **Chuẩn hóa L2 (`NORMALIZE_EMBEDDINGS`)** | **Mean: 1.0, Min: 1.0, Max: 1.0** | Chuẩn hóa hoàn hảo |
| **Tỷ lệ bảo tồn 18 trường metadata** | **100.0% (1,390 / 1,390 chunks)** | 0 lỗi thất thoát metadata |
| **Thiết bị thực thi (Device)** | `cpu` | Fallback mượt mà |
| **Kích thước batch (`batch_size`)** | `64` | Xử lý mảng tối ưu |
| **Thời gian thực thi toàn trình** | **29.659 giây** | Tốc độ cao |
| **Thông lượng (Throughput)** | **46.87 chunks / giây** (~21.34 ms / chunk) | Đáp ứng thời gian thực |

### Thống kê độ phủ các trường siêu dữ liệu trên 1,390 chunks:
* `chunk_id`, `document_id`, `document_number`, `document_title`, `document_type`: **1,390 / 1,390 (100%)**
* `chapter_number`, `chapter_title`: **1,008 / 1,390 (72.5%)** (các văn bản hoặc phụ lục không chia chương có giá trị null)
* `article_number`, `parent_article`: **1,101 / 1,390 (79.2%)** (các phụ lục độc lập có giá trị null)
* `article_title`: **1,099 / 1,390**
* `clause_number`: **756 / 1,390**
* `point_number`: **147 / 1,390**
* `content_type`: **1,390 / 1,390 (100%)**
* `legal_status`, `source_url`, `parent_document`: **1,390 / 1,390 (100%)**

---

## 6. Kết Quả Bộ Kiểm Thử Đơn Vị (Unit Tests Execution)

Tất cả các ca kiểm thử trong [`tests/embedding/test_embedding.py`](file:///d:/Filehoc/KLCN/agentic-rag/tests/embedding/test_embedding.py) đều đạt kết quả `PASS`:

```text
test_batch_embedding_mock (test_embedding.TestEmbeddingModule) ... ok
test_batch_embedding_onnx (test_embedding.TestEmbeddingModule) ... ok
test_deterministic_output_mock (test_embedding.TestEmbeddingModule) ... ok
test_deterministic_output_onnx (test_embedding.TestEmbeddingModule) ... ok
test_device_fallback_behavior (test_embedding.TestEmbeddingModule) ... ok
test_empty_batch_returns_empty_list (test_embedding.TestEmbeddingModule) ... ok
test_empty_content_handling_batch (test_embedding.TestEmbeddingModule) ... ok
test_empty_content_handling_single (test_embedding.TestEmbeddingModule) ... ok
test_l2_normalization (test_embedding.TestEmbeddingModule) ... ok
test_metadata_preservation (test_embedding.TestEmbeddingModule) ... ok
test_pipeline_on_dataset_v2_sample (test_embedding.TestEmbeddingModule) ... ok
test_single_text_embedding_mock (test_embedding.TestEmbeddingModule) ... ok
test_single_text_embedding_onnx (test_embedding.TestEmbeddingModule) ... ok
test_vector_dimension_consistency (test_embedding.TestEmbeddingModule) ... ok

----------------------------------------------------------------------
Ran 14 tests in 4.216s

OK
```

---

## 7. Bảng Đối Chiếu Tiêu Chí Nghiệm Thu (Acceptance Checklist)

| Tiêu chí nghiệm thu (Acceptance Criteria) | Trạng thái | Minh chứng kỹ thuật |
|:---|:---:|:---|
| **Dataset đọc thành công** | **PASS** | Đọc trọn vẹn 1,390 chunks từ `Data_Processing/output_v2/legal_dataset_v2.json`. |
| **Tất cả legal chunks có thể embedding** | **PASS** | 1,390 / 1,390 chunks được véc-tơ hóa thành công (0 failed chunks). |
| **Không mất metadata** | **PASS** | 18 trường metadata bắt buộc được bảo tồn 100% trên toàn bộ các bản ghi. |
| **Dimension nhất quán** | **PASS** | 100% véc-tơ sinh ra có chiều dài chính xác bằng 384 dimensions. |
| **Batch embedding hoạt động** | **PASS** | Xử lý các lô `batch_size=64`, kiểm tra slice logic và ghép nối vector chính xác. |
| **GPU/CPU behavior rõ ràng** | **PASS** | `resolve_device()` kiểm tra CUDA, log cảnh báo rõ ràng và tự động fallback về CPU. |
| **Tests PASS** | **PASS** | 14/14 unit tests đạt trạng thái OK trong 4.2 giây. |
| **Không có vector DB** | **PASS** | Phân hệ chỉ làm nhiệm vụ embedding, không khởi tạo hay ghi vào cơ sở dữ liệu vector. |
| **Không có retrieval** | **PASS** | Không chứa bất kỳ phương thức tìm kiếm, cosine query hay retriever logic nào. |
| **Không có LLM generation** | **PASS** | Hoàn toàn độc lập với mô hình sinh ngôn ngữ lớn. |
