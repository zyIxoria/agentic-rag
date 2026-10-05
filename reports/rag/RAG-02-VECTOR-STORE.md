# BÁO CÁO XÂY DỰNG PERSISTENT VECTOR STORE (TASK RAG-02)
## Triển Khai Cơ Sở Dữ Liệu Véc-tơ Bền Vững Cho Traditional RAG Baseline

* **Mã tác vụ**: `RAG-02`
* **Dự án**: Nghiên cứu cơ chế điều phối thích ứng trong hệ thống Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam
* **Thành phần**: `Persistent Vector Store (ChromaDB)`
* **Gói mã nguồn**: [`RAG/vector_store/`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/vector_store/)
* **Bộ kiểm thử**: [`tests/vector_store/`](file:///d:/Filehoc/KLCN/agentic-rag/tests/vector_store/)
* **Vị trí cơ sở dữ liệu**: [`data/chroma_db/`](file:///d:/Filehoc/KLCN/agentic-rag/data/chroma_db/)
* **Tên Collection chuẩn**: `legal_labor_baseline_minilm`
* **Ngày hoàn tất**: 2026-09-15
* **Trạng thái**: `PASS (100% Validated & Verified)`

---

## 1. Mục Tiêu & Phạm Vi Thực Thi (Objective & Strict Scope)

Mục tiêu cốt lõi của **TASK RAG-02** là xây dựng tầng lưu trữ véc-tơ bền vững (Persistent Vector Store) cho hệ thống Traditional RAG, kết nối trực tiếp với kết quả embedding từ **TASK RAG-01** để nạp và quản lý toàn bộ 1,390 chunks của **Legal Dataset V2.1**.

```text
Legal Dataset V2.1 (1,390 chunks)
              ↓
  RAG-01 LegalEmbeddingPipeline (all-MiniLM-L6-v2, 384d)
              ↓
  1,390 EmbeddedChunks (L2 Normalized)
              ↓
  PersistentChromaStore (data/chroma_db, HNSW Cosine)
              ↓
  Collection 'legal_labor_baseline_minilm' (1,390 vectors)
```

### Ràng buộc phạm vi nghiêm ngặt (Strict Scope & Non-Goals):
1. **Chỉ triển khai tầng lưu trữ (Storage & Ingestion Layer)**: Cung cấp đầy đủ các thao tác quản lý collection, nạp dữ liệu (upsert), đếm số lượng bản ghi (count), truy xuất theo ID (get_by_id) và lưu bền vững (persist).
2. **TUYỆT ĐỐI KHÔNG triển khai Logic Truy hồi (No Retrieval Logic)**: Không implement `search()`, `retrieve()`, `similarity_search()`, hay `query()`. Việc truy hồi ngữ nghĩa thuộc trách nhiệm của tác vụ `RAG-05 (Dense Retriever)`.
3. **TUYỆT ĐỐI KHÔNG tích hợp LLM (No LLM Logic)**: Tầng Vector Store độc lập hoàn toàn với các mô hình ngôn ngữ lớn.
4. **Bảo tồn nguyên vẹn Dataset V2.1**: Không chỉnh sửa bất kỳ tệp dữ liệu nào trong `Data_Processing/output_v2/`.
5. **Cơ chế an toàn FAIL FAST**: Kiểm soát chặt chẽ kích thước vector (dimension) và tính tương thích của mô hình embedding; báo lỗi ngay lập tức khi phát hiện sai lệch.

---

## 2. Công Nghệ Lựa Chọn & Thiết Lập Hệ Thống

* **Engine**: **ChromaDB** (`v1.5.9`) — Thư viện lưu trữ véc-tơ nhúng (embedded in-process vector database) hiệu năng cao cho Python.
* **Chế độ lưu trữ**: `chromadb.PersistentClient` với cơ chế lưu trữ bền vững trực tiếp xuống ổ đĩa cục bộ (`data/chroma_db/`).
* **Thuật toán chỉ mục**: HNSW (Hierarchical Navigable Small World).
* **Phép đo khoảng cách**: Khoảng cách Cosine (`hnsw:space = "cosine"`).
* **Mô hình định danh collection thực tế**:
  * Tên collection: `legal_labor_baseline_minilm`
  * Mô hình embedding liên kết: `sentence-transformers/all-MiniLM-L6-v2` (từ RAG-01).
  * Kích thước véc-tơ (Dimension): **384 chiều**.
  * Phiên bản tập dữ liệu liên kết: `dataset_version = "v2.1"`.

---

## 3. Kiến Trúc Data Model & Ánh Xạ Bản Ghi

Mỗi bản ghi vector trong ChromaDB tuân thủ cấu trúc 4 trường bắt buộc theo đặc tả của TASK RAG-02:

```text
id        = chunk_id        (Khóa chính duy nhất 100% từ Dataset V2.1)
embedding = vector          (Danh sách float List[float] có số chiều đúng chuẩn 384d)
document  = content         (Toàn văn nội dung đoạn pháp lý)
metadata  = legal metadata  (Toàn bộ các trường siêu dữ liệu phân cấp và hiệu lực)
```

### 3.1. Quy tắc Bảo toàn Siêu dữ liệu (Metadata Preservation)
ChromaDB chỉ chấp nhận các kiểu dữ liệu nguyên thủy: `str`, `int`, `float`, `bool` và nghiêm cấm dictionary rỗng `{}` hoặc giá trị `None`. Hệ thống đã thiết lập bộ chuyển đổi hai chiều tại [`RAG/vector_store/schema.py`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/vector_store/schema.py):
* **`sanitize_metadata(metadata)`**:
  * Chuyển đổi các giá trị `None` (VD: `point_number = None`, `effective_to = None`) thành chuỗi rỗng `""`.
  * Nếu dictionary rỗng, tự động bổ sung sentinel an toàn `{"_empty": True}` để tránh lỗi `0 metadata attributes in upsert`.
* **`desanitize_metadata(metadata, restore_none=True)`**:
  * Khi gọi `get_by_id()`, tự động khôi phục chuỗi rỗng `""` trở lại thành `None`.
  * Loại bỏ sentinel `_empty`, bảo đảm dữ liệu trả về cho ứng dụng khớp 100% với schema gốc.

---

## 4. Các Giao Diện & Phương Thức Đã Triển Khai

Gói mã nguồn [`RAG/vector_store/`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/vector_store/) cung cấp lớp trừu tượng [`BaseVectorStore`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/vector_store/base.py), lớp thực thi [`PersistentChromaStore`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/vector_store/chroma_store.py) và mô-đun nạp dữ liệu [`ingest.py`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/vector_store/ingest.py):

| Tên phương thức | Tham số đầu vào chính | Mô tả chức năng & Ràng buộc an toàn |
|:---|:---|:---|
| `create_collection()` | `name`, `embedding_dimension`, `embedding_model`, `dataset_version="v2.1"`, `distance_metric="cosine"`, `metadata=None`, `overwrite=False` | Khởi tạo collection với metadata an toàn. Nếu collection đã tồn tại và `overwrite=False`, thực hiện kiểm tra tương thích dimension, model, version (FAIL FAST nếu sai lệch). |
| `load_collection()` | `name`, `expected_dimension=None`, `expected_model=None`, `expected_version=None` | Nạp collection hiện có từ ổ đĩa. Tự động kiểm tra tính tương thích và kích hoạt `FAIL FAST` nếu dimension hoặc model không khớp cấu hình kỳ vọng. |
| `upsert()` | `ids`, `embeddings`, `documents`, `metadatas=None`, `batch_size=500`, `deduplicate_batch=True` | Nạp hoặc cập nhật dữ liệu. Kiểm tra đồng bộ kích thước mảng, kiểm tra từng vector với collection dimension (FAIL FAST nếu lệch chiều), tự động khử trùng lặp trong batch (giữ bản ghi sau cùng, đảm bảo 1 vector / chunk). |
| `upsert_records()` | `records: List[VectorRecord]`, `batch_size=500`, `deduplicate_batch=True` | Tiện ích nạp danh sách đối tượng `VectorRecord`. |
| `count()` | Không | Trả về tổng số lượng bản ghi véc-tơ thực tế đang được lưu trữ trong collection. |
| `get_by_id()` | `chunk_id: str`, `restore_none: bool = True` | Lấy chi tiết bản ghi theo `chunk_id`. Trả về dictionary gồm `id`, `embedding`, `document`, `metadata` (đã phục hồi `None`). Trả về `None` nếu không tìm thấy. |
| `persist()` | Không | Đồng bộ hóa dữ liệu xuống đĩa cứng (Persistence Guarantee). |
| `delete_collection()` | `name: str`, `confirm: bool = False` | Xóa collection. Bắt buộc phải truyền `confirm=True`; nếu không sẽ ném ngoại lệ `PermissionError` để chống xóa nhầm. |
| `list_collections()` | Không | Liệt kê toàn bộ tên collections hiện diện trên thư mục lưu trữ đĩa cứng. |
| `close()` | Không | Giải phóng tham chiếu collection và client an toàn. |
| `ingest_legal_dataset()` | `dataset_path`, `persist_directory`, `collection_name`, `overwrite=True` | Đường ống nạp tự động toàn bộ Dataset V2.1 với embedding sinh ra từ RAG-01 vào ChromaDB. |

---

## 5. Kết Quả Ingestion Thực Tế Vào `data/chroma_db/`

Đường ống [`ingest.py`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/vector_store/ingest.py) đã thực thi nạp toàn bộ **1,390 chunks** của Dataset V2.1 vào cơ sở dữ liệu `data/chroma_db/`:

| Chỉ số kiểm tra | Kết quả ghi nhận | Đánh giá |
|:---|:---:|:---:|
| **Thư mục cơ sở dữ liệu** | `data/chroma_db/` | Bền vững trên ổ đĩa (Persistent) |
| **Tên Collection** | `legal_labor_baseline_minilm` | Đồng bộ kiến trúc RAG Baseline |
| **Tổng số văn bản luật nạp** | **15 văn bản** | Đầy đủ 15/15 văn bản |
| **Tổng số vector nạp thành công** | **1,390 / 1,390** | 100% dữ liệu (0 thất thoát) |
| **Số bản ghi ghi nhận trong DB (`store.count()`)** | **1,390** | Khớp chính xác 1:1 |
| **Tỷ lệ Vector / Chunk** | **1 : 1** | Không nhân bản, không trùng lặp |
| **Kích thước số chiều (Dimension)** | **384** | Đồng nhất 100% |
| **Mô hình embedding liên kết** | `sentence-transformers/all-MiniLM-L6-v2` | Đồng bộ RAG-01 |
| **Tốc độ nạp (Throughput)** | **50.54 chunks / giây** | Hiệu năng cao (~27.5 giây toàn trình) |
| **Kiểm tra truy xuất mẫu (`get_by_id`)** | **Khớp 100%** nội dung và siêu dữ liệu | Toàn vẹn thông tin |
| **Kiểm tra Nạp lại (`load_collection`)** | **Thành công** từ tiến trình độc lập | Khả năng Reload hoàn hảo |

---

## 6. Cơ Chế An Toàn & Xử Lý Lỗi (Safety & FAIL FAST Verification)

Hệ thống định nghĩa cây phân cấp ngoại lệ chuyên biệt tại [`RAG/vector_store/exceptions.py`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/vector_store/exceptions.py):

```
VectorStoreError (Base)
├── DimensionMismatchError (Kích thước vector sai lệch -> FAIL FAST)
├── CompatibilityError (Model hoặc dataset version không khớp -> FAIL FAST)
├── CollectionNotFoundError (Không tìm thấy collection trên đĩa)
├── CollectionAlreadyExistsError (Collection đã tồn tại khi tạo mới)
└── DuplicateIDError (Phát hiện trùng lặp ID không hợp lệ)
```

### Minh chứng kiểm thử an toàn thực tế:
1. **Kiểm tra Dimension nghiêm ngặt trên `load_collection` (FAIL FAST)**:
   * Thử nạp collection `legal_labor_baseline_minilm` với `expected_dimension=1024`:
   * Kết quả: Ném ngoại lệ `DimensionMismatchError: FAIL FAST: Collection 'legal_labor_baseline_minilm' có dimension 384, không khớp với dimension kỳ vọng 1024.`
2. **Kiểm tra Dimension nghiêm ngặt trên `upsert` (FAIL FAST)**:
   * Thử nạp vector có chiều dài 512 vào collection:
   * Kết quả: Ném ngoại lệ `DimensionMismatchError: FAIL FAST: Vector tại chỉ mục 0 (ID='dummy_fail') có số chiều 512, không khớp với số chiều của collection (384).`
3. **Chống Ghi đè Vô thức (No Silent Overwrite)**:
   * `create_collection()` mặc định không xóa collection cũ trừ khi chỉ định rõ `overwrite=True`.
4. **Bảo vệ Thao tác Xóa (Explicit Delete Confirmation)**:
   * Gọi `delete_collection(name)` không có `confirm=True` lập tức bị chặn với `PermissionError`.

---

## 7. Kết Quả Bộ Kiểm Thử Đơn Vị (Unit Tests Execution)

Tất cả 14 ca kiểm thử trong [`tests/vector_store/test_vector_store.py`](file:///d:/Filehoc/KLCN/agentic-rag/tests/vector_store/test_vector_store.py) đều đạt kết quả `PASS`:

```text
test_01_collection_creation ... ok
test_02_insert_small_fixture ... ok
test_03_count ... ok
test_04_get_by_chunk_id ... ok
test_05_persistence_and_reload ... ok
test_06_metadata_preservation ... ok
test_07_duplicate_id_behavior ... ok
test_08_dimension_mismatch_fail_fast ... ok
test_09_empty_dataset ... ok
test_10_delete_collection_confirmation ... ok
test_11_compatibility_validation ... ok
test_12_vector_record_helper ... ok
test_13_real_dataset_v2_sample_ingestion ... ok
test_14_integration_with_rag01_embeddings ... ok

----------------------------------------------------------------------
Ran 14 tests in 1.910s

OK
```

---

## 8. Bảng Đối Chiếu Tiêu Chí Nghiệm Thu (Acceptance Checklist)

| Tiêu chí nghiệm thu (Acceptance Criteria) | Trạng thái | Minh chứng kỹ thuật |
|:---|:---:|:---|
| **Persistent vector DB** | **PASS** | ChromaDB PersistentClient lưu trữ bền vững tại `data/chroma_db/`. |
| **1 vector / chunk** | **PASS** | 1,390 chunks sinh đúng 1,390 vectors trong collection. |
| **chunk_id preserved** | **PASS** | ID trong collection khớp 100% với `chunk_id` của Dataset V2.1. |
| **metadata preserved** | **PASS** | 18 trường metadata bắt buộc được bảo toàn trọn vẹn kèm phục hồi giá trị `None`. |
| **reload works** | **PASS** | `load_collection()` tải lại thành công collection từ thư mục đĩa độc lập. |
| **dimension validated** | **PASS** | Kiểm soát chặt chẽ 384 dimensions; kích hoạt `FAIL FAST` nếu lệch chiều. |
| **tests PASS** | **PASS** | 14/14 tests đạt trạng thái OK trong 1.910 giây. |
| **no retrieval logic** | **PASS** | Tầng Vector Store không chứa hàm search, retrieve hay filter logic của truy hồi. |
| **no LLM** | **PASS** | Hoàn toàn độc lập với mô hình sinh ngôn ngữ lớn. |
