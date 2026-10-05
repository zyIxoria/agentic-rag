# BÁO CÁO KIẾN TRÚC TRADITIONAL RAG BASELINE (TASK RAG-00)
## Specification & Architecture Freeze cho Hệ Thống Hỏi Đáp Pháp Luật Lao Động Việt Nam

* **Mã tác vụ**: `RAG-00`
* **Dự án**: Nghiên cứu cơ chế điều phối thích ứng trong hệ thống Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam
* **Phiên bản kiến trúc**: `Baseline v1.0 (Traditional RAG Freeze)`
* **Ngày phê duyệt**: 2026-09-09
* **Trạng thái**: `PASS (Architecture & Specification Frozen)`
* **Môi trường thực thi dự kiến**: Python 3.13.0, Windows 11, NVIDIA GeForce RTX 5060 (8GB VRAM, CUDA 13.0)

---

## 1. Existing Project Analysis (Phân Tích Hiện Trạng Toàn Bộ Dự Án)

### 1.1. Hiện trạng Mã nguồn và Thư mục Dự án

Qua quá trình rà soát toàn diện cấu trúc cây thư mục và lịch sử Git (`branch: rag-baseline`, commits `0d0289a` và `f39eefc`), hệ thống hiện tại được tổ chức thành các phân hệ sau:

1. **Phân hệ Dữ liệu & Xử lý Pháp lý (`Data_Processing/`)**:
   * Chứa toàn bộ đường ống xử lý từ dữ liệu thô (`data_corpus_raw/`) đến phân đoạn văn bản và khôi phục siêu dữ liệu cấu trúc luật Việt Nam.
   * Chứa các mô-đun phân tích cú pháp nâng cao:
     * `hierarchy_parser.py`: Phân cấp Chương, Mục, Điều, Phụ lục và lọc trích dẫn tiến (Structural Forward Look-ahead).
     * `article_parser.py`: Tách Khoản, Điểm theo chuẩn thể thức văn bản quy phạm pháp luật Việt Nam.
     * `appendix_parser.py`: Phân tích và cấu trúc hóa bảng biểu phụ lục, danh mục nghề độc hại, bảng tuổi nghỉ hưu.
     * `metadata_restorer.py`: Khôi phục số hiệu, loại văn bản, ngày ban hành, ngày hiệu lực và liên kết cha-con.
     * `chunker_v2.py`: Bộ chia nhỏ có nhận thức cấu trúc pháp lý (Legal-Aware Chunker) tuân thủ giới hạn 100–800 tokens.
     * `models_v2.py` & `schema_v2.py`: Mô hình dữ liệu Pydantic V2 kiểm soát chặt chẽ 21 trường thuộc tính.
     * `config_v2.py`: Cấu hình tham số token chunking (`ChunkerConfigV2`).
     * Bộ kiểm thử toàn diện gồm 130 tests (`test_*.py`) bao phủ 100% các ca biên và hồi quy dữ liệu (tất cả đều đạt trạng thái `OK`).

2. **Phân hệ Thu thập Dữ liệu (`KhoaLuan_Crawler/`)**:
   * `tvpl_crawler.py`: Bộ cào dữ liệu tự động từ *Thư Viện Pháp Luật* sử dụng Playwright và BeautifulSoup4.
   * `data_corpus_raw/`: Lưu trữ 15 tệp văn bản thô `.txt` và 15 tệp siêu dữ liệu `.json` tương ứng.

3. **Phân hệ Thẩm định & Báo cáo (`reports/dataset_audit/`)**:
   * Lưu trữ toàn bộ lộ trình kiểm định từ `DATA-01` đến `DATA-13` cùng báo cáo tổng hợp `DATA-V2-AUDIT.md`.
   * Ghi nhận việc xử lý dứt điểm các lỗi nghiêm trọng về false-merge Điều luật và ranh giới phụ lục trong tác vụ `DATA-13`.

### 1.2. Hiện trạng Thành phần RAG (LLM, Embedding, Vector DB, Pipeline)

* **Runtime RAG Source**: Chưa có bất kỳ tệp thực thi RAG nào trong thư mục gốc (không có `config.py`, `llm.py`, `prompt.py`, `chain.py`, `retriever.py`, `utils.py` ở root).
* **Môi trường LLM & API Keys**:
  * Phát hiện biến môi trường hệ thống khả dụng: `OPENAI_API_KEY` và `GEMINI_API_KEY`.
  * Chưa có wrapper hay client kết nối LLM nào được cài đặt trong mã nguồn dự án.
* **Vector Database**:
  * Chưa có cơ sở dữ liệu véc-tơ nào được khởi tạo (`data/` hay `chroma_db/` chưa tồn tại).
  * Trong báo cáo `DATA-01` và `DATA-02`, ChromaDB đã được định hướng là đích đến tối ưu để nạp 1,390 chunks nhờ cấu trúc khóa chính duy nhất toàn cục `chunk_id`.
* **Môi trường Phần cứng & Thư viện Python**:
  * Python Runtime: `Python 3.13.0` (môi trường Windows 64-bit).
  * GPU: `NVIDIA GeForce RTX 5060 Laptop GPU` (VRAM: 8,151 MiB, Driver Version: 581.91, CUDA Version: 13.0). Khả năng xử lý song song và hỗ trợ mô hình embedding nội bộ (local GPU inference) rất mạnh mẽ.
  * Các gói chính hiện có: `pydantic` 2.13.5, `pydantic-settings` 2.15.0, `fastapi` 0.115.14, `python-dotenv` 1.2.3, `requests` 2.34.2, `PyYAML` 6.0.3.
  * Các gói RAG còn thiếu (cần bổ sung ở RAG-01): `chromadb`, `sentence-transformers`, `torch` (CUDA 13/cu12x), `openai`, `google-genai` (hoặc `google-generativeai`), `tiktoken`.

---

## 2. Existing Reusable Modules (Các Mô-đun Hiện Có Tái Sử Dụng Được)

Dự án tuyệt đối tuân thủ nguyên tắc **không tạo abstraction trùng lặp**. Các thành phần sau trong `Data_Processing/` được xác định là tài sản cốt lõi và sẽ được tái sử dụng trực tiếp trong hệ thống RAG:

| Mô-đun nguồn | Thành phần tái sử dụng | Mục đích trong Traditional RAG |
|:---|:---|:---|
| [`Data_Processing/models_v2.py`](file:///d:/Filehoc/KLCN/agentic-rag/Data_Processing/models_v2.py) | • `LegalChunkV2`<br>• `DocumentType`<br>• `LegalStatus`<br>• `ContentType`<br>• `sanitize_null()` | Mô hình hóa bản ghi văn bản khi nạp từ Dataset V2.1 vào Vector Store; trích xuất siêu dữ liệu và chuẩn hóa các trường rỗng/null; bảo toàn kiểu dữ liệu chuẩn xác. |
| [`Data_Processing/schema_v2.py`](file:///d:/Filehoc/KLCN/agentic-rag/Data_Processing/schema_v2.py) | • `validate_chunk()`<br>• `validate_dataset()` | Kiểm thực tính toàn vẹn và hợp thức của dataset trước khi lập chỉ mục (indexing); đảm bảo không có chunk lỗi cấu trúc được nạp vào Vector DB. |
| [`Data_Processing/config_v2.py`](file:///d:/Filehoc/KLCN/agentic-rag/Data_Processing/config_v2.py) | • `ChunkerConfigV2.count_tokens()`<br>• `ChunkerConfigV2.tokens_to_words()` | Đo lường và kiểm soát ngân sách token (Token Budgeting) cho Context Builder bằng hệ số BPE subword tiếng Việt (1.3 từ/token) mà không cần phụ thuộc thư viện bên ngoài nếu chạy offline. |
| [`Data_Processing/output_v2/`](file:///d:/Filehoc/KLCN/agentic-rag/Data_Processing/output_v2/) | • `legal_dataset_v2.json`<br>• `legal_dataset_v2.jsonl`<br>• `build_metadata.json` | Nguồn dữ liệu tri thức duy nhất (Single Source of Truth) cho quá trình Vector Ingestion. Tuyệt đối đóng băng, không chỉnh sửa dữ liệu này. |

---

## 3. Dataset V2.1 Detailed Specification

Tập dữ liệu chuẩn hóa phục vụ cho Traditional RAG là **Legal Dataset V2.1** (đã được nghiệm thu thành công sau khi hoàn tất sửa lỗi trong tác vụ `DATA-13`):

* **Đường dẫn tệp chính (JSON Array)**: `Data_Processing/output_v2/legal_dataset_v2.json`
* **Mã băm SHA-256 JSON**: `e48c6a3bece6819a0e25da8d985c8391ec162561c985e26d69dc3d13f2c87d92`
* **Đường dẫn tệp phụ trợ (JSON Lines)**: `Data_Processing/output_v2/legal_dataset_v2.jsonl`
* **Mã băm SHA-256 JSONL**: `bcd6d0f05b0239b6250a6aa30e93d27093599d6da08bf80344cfd3a8ce834265`
* **Tệp thông tin bản build**: `Data_Processing/output_v2/build_metadata.json`
* **Tổng số văn bản quy phạm pháp luật**: **15 văn bản**
* **Tổng số đoạn văn bản (Chunks)**: **1,390 chunks**
* **Số lượng Chunk ID duy nhất**: **1,390 / 1,390 (100% Unique - 0 Collision)**
* **Phân bố kích thước token**:
  * Nhỏ nhất (Min): 26 tokens (không còn micro table-header <10 từ).
  * Lớn nhất (Max): 800 tokens (100% không có monster chunk vượt trần).
  * Trung bình (Average): 264.75 tokens.
  * Trung vị (Median): 211.0 tokens.
  * Vùng tối ưu (100 – 350 tokens): 987 chunks (71.01%).

### 3.1. Danh mục 21 Trường Thuộc Tính Chuẩn (Schema Fields)

Mỗi chunk trong `legal_dataset_v2.json` chứa đúng 21 trường theo đặc tả TASK DATA-02:

| STT | Tên trường | Kiểu dữ liệu | Vai trò trong Traditional RAG |
|:---:|:---|:---:|:---|
| 1 | `chunk_id` | `str` (Bắt buộc) | Khóa chính duy nhất (Document ID trong Vector Store). |
| 2 | `document_id` | `str` (Bắt buộc) | Định danh văn bản nguồn (hỗ trợ lọc metadata). |
| 3 | `document_number` | `str` hoặc `null` | Số hiệu văn bản pháp lý (dùng để trích dẫn nguồn). |
| 4 | `document_title` | `str` (Bắt buộc) | Tiêu đề đầy đủ của văn bản luật. |
| 5 | `document_type` | `str` hoặc `null` | Loại văn bản (Bộ luật, Nghị định, Thông tư, Quyết định). |
| 6 | `chapter_number` | `str` hoặc `null` | Số thứ tự Chương (VD: Chương I, Chương III). |
| 7 | `chapter_title` | `str` hoặc `null` | Tiêu đề Chương (tạo ngữ cảnh phân cấp). |
| 8 | `section_number` | `str` hoặc `null` | Số thứ tự Mục (nếu có). |
| 9 | `section_title` | `str` hoặc `null` | Tiêu đề Mục (nếu có). |
| 10 | `article_number` | `str` hoặc `null` | Số hiệu Điều (VD: Điều 1, Điều 125). |
| 11 | `article_title` | `str` hoặc `null` | Tiêu đề Điều luật (dùng cho trích dẫn ngữ cảnh). |
| 12 | `clause_number` | `str` hoặc `null` | Số thứ tự Khoản (VD: Khoản 1, Khoản 2). |
| 13 | `point_number` | `str` hoặc `null` | Ký hiệu Điểm (VD: Điểm a, Điểm a đến b). |
| 14 | **`content`** | `str` (Bắt buộc) | **Nội dung ngữ nghĩa chính để tạo embedding và đưa vào LLM Context**. |
| 15 | `effective_from` | `str` hoặc `null` | Ngày bắt đầu có hiệu lực (DD/MM/YYYY). |
| 16 | `effective_to` | `str` hoặc `null` | Ngày hết hiệu lực (mặc định null). |
| 17 | `legal_status` | `str` (Bắt buộc) | Tình trạng hiệu lực (Còn hiệu lực / unknown). |
| 18 | `source_url` | `str` hoặc `null` | Đường dẫn URL tra cứu văn bản gốc tại TVPL (dùng cho Citation). |
| 19 | `parent_document` | `str` (Bắt buộc) | Liên kết định danh văn bản cấp cha. |
| 20 | `parent_article` | `str` hoặc `null` | Liên kết định danh Điều luật cấp cha. |
| 21 | `chunk_index` | `int` (Bắt buộc) | Thứ tự xuất hiện tự nhiên của chunk trong văn bản. |

---

## 4. Hardware, LLM & Embedding Selection Specification

### 4.1. Khảo sát Phần cứng & Môi trường Khả thi

Hệ thống ghi nhận cấu hình máy chủ cục bộ:
* **GPU**: NVIDIA GeForce RTX 5060 Laptop GPU (8GB GDDR6 VRAM, CUDA Compute 12/13).
* **RAM**: Khả dụng > 16GB.
* **Ổ đĩa**: NVMe SSD tốc độ cao tại `D:\Filehoc\KLCN\agentic-rag\`.

### 4.2. Lựa chọn Mô hình Embedding (Embedding Candidates & Recommendation)

| Tiêu chí so sánh | Ứng viên 1: `BAAI/bge-m3` (Khuyến nghị Cục bộ) | Ứng viên 2: `text-embedding-3-small` (Khuyến nghị API) | Ứng viên 3: `bkai-foundation-models/vietnamese-bi-encoder` |
|:---|:---:|:---:|:---:|
| **Loại hình** | Local HuggingFace Transformer | Cloud API (OpenAI) | Local HuggingFace Transformer |
| **Chiều véc-tơ (Dimension)**| **1024** | 1536 (có thể giảm 512/1024) | 768 |
| **Độ dài ngữ cảnh tối đa**| **8,192 tokens** (Bao trọn 800 tokens của dataset) | 8,191 tokens | 256 tokens (Quá ngắn, bị cắt cụt) |
| **Hỗ trợ Tiếng Việt** | Đa ngôn ngữ xuất sắc, đã benchmark tốt trên văn bản pháp lý | Rất tốt | Tốt cho câu ngắn |
| **Thiết bị hỗ trợ** | GPU CUDA (RTX 5060 tốn ~2.2GB VRAM) hoặc CPU | Không tốn VRAM cục bộ | GPU / CPU |
| **Độ phụ thuộc** | `sentence-transformers`, `torch` | `openai`, `requests` | `sentence-transformers`, `torch` |
| **Chi phí runtime** | 0 VNĐ (Chạy offline trên máy) | Phí API OpenAI rất nhỏ | 0 VNĐ |
| **Đánh giá phù hợp** | **LỰA CHỌN CHÍNH (PRIMARY RECOMMENDED)** | **LỰA CHỌN THAY THẾ (FALLBACK)** | LOẠI (Không đủ token context) |

> **Quyết định kiến trúc**:
> Cung cấp giao diện trừu tượng `EmbeddingProvider`. Mặc định cấu hình sử dụng `BAAI/bge-m3` chạy trên `cuda` (tận dụng GPU RTX 5060 8GB có sẵn), đồng thời hỗ trợ chuyển đổi sang `openai/text-embedding-3-small` thông qua biến môi trường `EMBEDDING_PROVIDER` mà không phải sửa code.

### 4.3. Lựa chọn LLM Provider & Model

| Tiêu chí | Ứng viên 1: OpenAI `gpt-4o-mini` | Ứng viên 2: Google `gemini-1.5-flash` | Ứng viên 3: Local 7B LLM (Qwen2.5) |
|:---|:---:|:---:|:---:|
| **Loại hình** | Cloud API (OpenAI) | Cloud API (Google DeepMind) | Local GPU (Ollama/vLLM) |
| **Trạng thái cấu hình** | Sẵn sàng (`OPENAI_API_KEY` đã có trong Env) | Sẵn sàng (`GEMINI_API_KEY` đã có trong Env) | Chưa cài đặt môi trường phục vụ |
| **Tuân thủ trích dẫn pháp lý** | Cực kỳ kỷ luật, ít ảo giác khi temperature=0 | Rất tốt, ngữ cảnh dài | Cần prompt tuning phức tạp |
| **Cơ chế từ chối (Refusal)** | Phản hồi từ chối chuẩn xác khi thiếu bằng chứng | Phản hồi tốt | Dễ sinh ảo giác ngoài ngữ cảnh |
| **Thời gian phản hồi (TTFT)** | ~0.4s – 0.8s | ~0.5s – 1.0s | Phụ thuộc VRAM chia sẻ với embedding |
| **Chi phí** | Rất thấp (~$0.15 / 1M tokens) | Miễn phí / rất thấp | Chi phí tính toán phần cứng |
| **Đánh giá phù hợp** | **LỰA CHỌN MẶC ĐỊNH (DEFAULT)** | **HỖ TRỢ SONG SONG (SUPPORTED)** | ĐỂ DÀNH CHO CÁC PHA SAU |

> **Quyết định kiến trúc**:
> Mặc định sử dụng OpenAI `gpt-4o-mini` (với `temperature=0.0` để đảm bảo tính khách quan và khả năng tái lập). Hỗ trợ song song Google `gemini-1.5-flash` qua abstraction `LLMProvider`.

### 4.4. Lựa chọn Vector Database & Chiến lược Lưu trữ

* **Công nghệ lựa chọn**: **ChromaDB** (`chromadb >= 0.5.0`).
* **Lý do lựa chọn**:
  1. Thư viện nhúng thuần Python, hoạt động cục bộ (embedded engine), không đòi hỏi dựng Docker container hay hạ tầng server phức tạp.
  2. Hỗ trợ đầy đủ thuật toán tìm kiếm tương đồng véc-tơ HNSW (Hierarchical Navigable Small World) với khoảng cách Cosine (`cosine similarity`).
  3. Quản lý metadata filtering mạnh mẽ (lọc theo `document_id`, `article_number`, `legal_status`).
  4. Hỗ trợ lưu trữ bền vững (Persistence) trực tiếp vào thư mục đĩa cục bộ.
* **Chiến lược bền vững hóa (Persistence Strategy)**:
  Sử dụng `chromadb.PersistentClient(path=VECTOR_DB_PATH)`.
* **Đường dẫn lưu trữ véc-tơ**: `data/chroma_db/`
* **Quy ước đặt tên Collection**:
  * Tên Collection mặc định: `legal_labor_baseline_bge_m3` (đối với bge-m3 1024d)
  * Tên Collection thay thế: `legal_labor_baseline_openai` (đối với text-embedding-3-small 1536d)

---

## 5. Strict Traditional RAG Architecture & Interfaces

### 5.1. Phạm vi RAG Đóng Băng (Strict Baseline Scope)

Traditional RAG là một đường ống tuần tự nghiêm ngặt, tuyến tính một chiều (Linear Pipeline):

```
                        [ User Question ]
                                ↓
                     [ 1. Query Preparation ]
                      (Trim, Clean, Validate)
                                ↓
                      [ 2. Vector Embedding ]
                    (EmbeddingProvider.embed_query)
                                ↓
                  [ 3. Dense Vector Retrieval ]
                    (ChromaDB HNSW Cosine Search)
                                ↓
                      [ 4. Top-K Chunks ]
                 (K=5 Chunks + Threshold Filtering)
                                ↓
                     [ 5. Context Builder ]
             (Legal Context Assembly + Token Budgeting)
                                ↓
                    [ 6. Prompt Engineering ]
           (Strict Labor Law Instructions + Role Definition)
                                ↓
                      [ 7. LLM Generation ]
                    (LLMProvider.generate_response)
                                ↓
                 [ 8. Citation & Refusal Check ]
                   (Format Citations / Emit Refusal)
                                ↓
                      [ Final Legal Answer ]
```

### 5.2. Các Thành phần Cốt lõi & Giao diện Trừu tượng (Abstract Interfaces)

Hệ thống kiến trúc gồm 7 thành phần độc lập, tương tác qua interface:

#### 1. `EmbeddingProvider` (Giao diện Vector hóa)
```python
from abc import ABC, abstractmethod
from typing import List

class EmbeddingProvider(ABC):
    """Giao diện trừu tượng cho mô hình chuyển đổi văn bản sang véc-tơ."""
    
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Tạo embedding véc-tơ cho một chuỗi văn bản đơn lẻ."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Tạo embedding hàng loạt cho danh sách văn bản (tối ưu hóa batch)."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Kích thước chiều của không gian véc-tơ (VD: 1024 đối với bge-m3)."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Tên định danh của mô hình."""
        pass
```

#### 2. `VectorStore` (Giao diện Lưu trữ & Tìm kiếm Véc-tơ)
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from rag.schema import RetrievedChunk

class VectorStore(ABC):
    """Giao diện quản lý lưu trữ và truy vấn tương đồng véc-tơ."""

    @abstractmethod
    def add_documents(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """Lưu trữ danh sách bản ghi kèm véc-tơ và metadata vào store."""
        pass

    @abstractmethod
    def query(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[RetrievedChunk]:
        """Tìm kiếm Top-K chunks gần nhất dựa trên độ tương đồng Cosine."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Trả về tổng số bản ghi hiện có trong collection."""
        pass
```

#### 3. `Retriever` (Giao diện Thu hồi Tài liệu Ngữ nghĩa)
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from rag.schema import RetrievedChunk

class BaseRetriever(ABC):
    """Giao diện truy hồi văn bản từ câu hỏi người dùng."""

    @abstractmethod
    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[RetrievedChunk]:
        """Thực hiện nhúng câu hỏi, truy vấn vector store và áp dụng ngưỡng lọc."""
        pass
```

#### 4. `ContextBuilder` (Giao diện Đóng gói Ngữ cảnh Pháp lý)
* **Nhiệm vụ**: Nhận danh sách các `RetrievedChunk`, kiểm tra giới hạn `MAX_CONTEXT_TOKENS` (ngân sách 3,000 tokens), đóng gói thành khối văn bản có cấu trúc rõ ràng gồm: Tiêu đề văn bản, Số hiệu, Điều luật, Khoản, Điểm và Nội dung chi tiết.
* **Nguyên tắc**: Giữ nguyên tính trung thực của văn bản, không tóm tắt làm sai lệch câu chữ lập pháp.

#### 5. `PromptTemplate` & `LegalPromptEngine` (Đặc tả Mẫu Lệnh Pháp lý)
* Thiết lập hệ thống prompt song ngữ/tiếng Việt chuẩn mực:
  * **System Role**: *"Bạn là Trợ lý Pháp lý ảo chuyên môn cao về Pháp luật Lao động Việt Nam. Nhiệm vụ duy nhất của bạn là giải đáp câu hỏi của người dùng DỰA HOÀN TOÀN VÀO NGỮ CẢNH ĐƯỢC CUNG CẤP."*
  * **Cơ chế Kỷ luật**:
    1. Chỉ sử dụng thông tin có trong Ngữ cảnh. Không suy diễn hoặc tự ý bổ sung kiến thức bên ngoài.
    2. Bắt buộc trích dẫn cụ thể căn cứ pháp lý: [Tên văn bản, Số hiệu, Điều X, Khoản Y].
    3. **Quy tắc Từ chối (Strict Refusal)**: Nếu ngữ cảnh không chứa đủ căn cứ để trả lời, phải trả lời rõ ràng: *"Căn cứ theo tài liệu pháp luật lao động được cung cấp, hiện chưa có đủ thông tin quy định cụ thể về vấn đề này."*

#### 6. `LLMProvider` (Giao diện Sinh Văn bản)
```python
from abc import ABC, abstractmethod
from typing import Optional

class LLMProvider(ABC):
    """Giao diện tương tác với mô hình ngôn ngữ lớn."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024
    ) -> str:
        """Sinh câu trả lời từ prompt văn bản với các tham số khống chế sinh ngẫu nhiên."""
        pass
```

#### 7. `CitationFormatter` & `RAGPipeline` (Định dạng Trích dẫn & Điều phối Pipeline)
* `CitationFormatter`: Trích xuất số hiệu văn bản, Điều, Khoản, Điểm từ metadata của chunks được truy hồi để tạo bảng tra cứu hoặc danh sách trích dẫn cuối câu trả lời kèm `source_url`.
* `TraditionalRAGPipeline`: Lớp trung tâm tiếp nhận `User Query`, gọi `Retriever` -> `ContextBuilder` -> `LLMProvider` -> `CitationFormatter` và trả về đối tượng `RAGResponse`.

---

## 6. Proposed File Structure (Cấu Trúc Thư Mục Chuẩn Cho Pha Baseline)

Dưới đây là cấu trúc tệp được thiết kế chi tiết trước khi tiến hành viết code (từ RAG-01 trở đi):

```text
agentic-rag/
│
├── Data_Processing/                          # [EXISTING - FROZEN] Phân hệ dữ liệu V2.1
│   ├── output_v2/
│   │   ├── legal_dataset_v2.json             # Dataset V2.1 chính thức (1,390 chunks)
│   │   ├── legal_dataset_v2.jsonl            # JSON Lines format
│   │   └── build_metadata.json               # Metadata xác nhận 0 collision, max 800 tokens
│   ├── models_v2.py                          # Reusable: LegalChunkV2 model
│   ├── schema_v2.py                          # Reusable: Validate helpers
│   └── config_v2.py                          # Reusable: Token estimation
│
├── rag/                                      # [NEW] Gói mã nguồn Traditional RAG Baseline
│   ├── __init__.py                           # Export public APIs
│   ├── config.py                             # Cấu hình Pydantic BaseSettings (nạp từ .env)
│   ├── schema.py                             # Schemas: QueryRequest, RetrievedChunk, RAGResponse, Citation
│   ├── prompt.py                             # Hệ thống Prompt pháp lý & Quy tắc từ chối
│   │
│   ├── embedding/                            # Phân hệ nhúng véc-tơ
│   │   ├── __init__.py
│   │   ├── base.py                           # Abstract EmbeddingProvider
│   │   ├── bge_provider.py                   # Local BAAI/bge-m3 qua SentenceTransformers
│   │   └── openai_provider.py                # Cloud OpenAI text-embedding-3-small
│   │
│   ├── vectorstore/                          # Phân hệ lưu trữ véc-tơ
│   │   ├── __init__.py
│   │   ├── base.py                           # Abstract VectorStore
│   │   └── chroma_store.py                   # Triển khai ChromaDB PersistentClient
│   │
│   ├── retriever/                            # Phân hệ truy hồi
│   │   ├── __init__.py
│   │   ├── base.py                           # Abstract BaseRetriever
│   │   └── dense_retriever.py                # Dense Top-K Retriever kèm Threshold Filter
│   │
│   ├── llm/                                  # Phân hệ sinh ngôn ngữ
│   │   ├── __init__.py
│   │   ├── base.py                           # Abstract LLMProvider
│   │   ├── openai_llm.py                     # OpenAI ChatCompletion wrapper
│   │   └── gemini_llm.py                     # Google Gemini SDK wrapper
│   │
│   ├── context_builder.py                    # Trình ghép ngữ cảnh & Quản lý ngân sách token
│   ├── citation.py                           # Trình thẩm định và định dạng căn cứ trích dẫn
│   ├── pipeline.py                           # TraditionalRAGPipeline điều phối toàn trình
│   └── indexer.py                            # Tác vụ nạp (Ingest) Dataset V2.1 vào ChromaDB
│
├── tests/
│   ├── rag/                                  # [NEW] Bộ kiểm thử cho RAG Baseline
│   │   ├── __init__.py
│   │   ├── test_config.py                    # Kiểm thử nạp và xác thực cấu hình
│   │   ├── test_schema.py                    # Kiểm thử validation input/output
│   │   ├── test_embedding.py                 # Kiểm thử tính toán kích thước vector
│   │   ├── test_vectorstore.py               # Kiểm thử CRUD và truy vấn ChromaDB
│   │   ├── test_dense_retriever.py           # Kiểm thử Top-K retrieval & lọc ngưỡng
│   │   ├── test_context_builder.py           # Kiểm thử giới hạn token & cấu trúc ngữ cảnh
│   │   ├── test_prompt.py                    # Kiểm thử tính nguyên vẹn của System Prompt
│   │   ├── test_citation.py                  # Kiểm thử trích dẫn và phát hiện từ chối
│   │   └── test_pipeline_e2e.py              # Kiểm thử tích hợp toàn trình (Mock & Real)
│   └── ... (các bài test cũ trong Data_Processing vẫn giữ nguyên)
│
├── data/
│   └── chroma_db/                            # [NEW] Thư mục lưu trữ cơ sở dữ liệu véc-tơ bền vững
│
├── reports/
│   ├── dataset_audit/                        # Lưu trữ audit DATA-01 -> DATA-13
│   └── rag/                                  # [NEW] Thư mục chứa báo cáo kiến trúc & đánh giá RAG
│       ├── RAG-00-ARCHITECTURE.md            # [TÀI LIỆU NÀY]
│       └── RAG-00-ARCHITECTURE.json          # Đặc tả máy đọc chuẩn JSON
│
├── .env.example                              # [NEW] Tệp mẫu cấu hình môi trường
└── requirements-rag.txt                      # [NEW] Danh sách thư viện phụ thuộc của RAG
```

---

## 7. Data Flow (Luồng Dữ Liệu Chi Tiết)

Hệ thống Traditional RAG gồm hai luồng dữ liệu độc lập:

### 7.1. Luồng Nạp và Đánh Chỉ Mục Dữ Liệu (Offline Ingestion Flow)

```
[ Data_Processing/output_v2/legal_dataset_v2.json ]
                         ↓
               [ rag/indexer.py ]
          (Đọc & Validate qua LegalChunkV2)
                         ↓
            [ Tách Batches: 64 chunks ]
                         ↓
         [ EmbeddingProvider.embed_batch ]
      (BAAI/bge-m3 sinh véc-tơ 1024 chiều)
                         ↓
        [ Chuẩn hóa Metadata sang kiểu nguyên bản ]
  (str, int, float, bool — loại bỏ hoàn toàn None)
                         ↓
       [ ChromaVectorStore.add_documents ]
       (Lưu trữ véc-tơ + content + metadata)
                         ↓
         [ data/chroma_db/ Persistence ]
        (Hoàn tất 1,390 chunks trong collection)
```

### 7.2. Luồng Hỏi Đáp Trực Tuyến (Online Inference Flow)

```
                       [ 1. User Query ]
                    "Thử việc tối đa bao lâu?"
                               ↓
                   [ 2. Query Sanitization ]
              (Loại bỏ khoảng trắng, kiểm tra min_length)
                               ↓
                  [ 3. Dense Query Embedding ]
              (EmbeddingProvider.embed_text(query))
                               ↓
                   [ 4. ChromaDB Similarity ]
         (Tính Cosine Similarity giữa Query và 1,390 Chunks)
                               ↓
              [ 5. Top-K Selection & Filtering ]
       (Chọn K=5 chunks có similarity >= SIMILARITY_THRESHOLD)
                               ↓
                    [ 6. Context Builder ]
  - Sắp xếp chunks theo độ tương đồng giảm dần
  - Kiểm tra tổng số tokens <= MAX_CONTEXT_TOKENS (3,000)
  - Ghép định dạng chuẩn:
    [Tài liệu 1]: Điều 25 - Bộ luật Lao động 2019 (45/2019/QH14)
    Nội dung: Thời gian thử việc do hai bên thỏa thuận...
                               ↓
                     [ 7. Prompt Assembly ]
      - System Prompt (Quy tắc pháp lý, nghiêm cấm bịa đặt)
      - Context Block (Khối ngữ cảnh đã ghép)
      - User Query
                               ↓
                     [ 8. LLM Generation ]
               (gpt-4o-mini, Temperature = 0.0)
                               ↓
               [ 9. Citation Post-Processing ]
      - Phân tích câu trả lời xem có phải là lời từ chối không
      - Định dạng danh sách nguồn tra cứu (source_url, Điều, Khoản)
                               ↓
                   [ 10. Output Response ]
      {
        "answer": "Thời gian thử việc của người lao động...",
        "citations": [ ... ],
        "retrieved_chunks": [ ... ],
        "is_refusal": false
      }
```

---

## 8. Configuration Design (Đặc Tả Tham Số Cấu Hình)

Toàn bộ tham số hệ thống được quản lý tập trung thông qua `Pydantic Settings` (`rag/config.py`), đọc từ biến môi trường hoặc tệp `.env`, tuyệt đối không hard-code trong mã thực thi:

| Biến cấu hình | Kiểu | Giá trị mặc định | Diễn giải & Ràng buộc kỹ thuật |
|:---|:---:|:---:|:---|
| `DATASET_PATH` | `str` | `"Data_Processing/output_v2/legal_dataset_v2.json"` | Đường dẫn tới dataset V2.1 chuẩn |
| `VECTOR_DB_TYPE` | `str` | `"chromadb"` | Hệ cơ sở dữ liệu véc-tơ (`chromadb`) |
| `VECTOR_DB_PATH` | `str` | `"data/chroma_db"` | Đường dẫn thư mục lưu trữ ChromaDB bền vững |
| `COLLECTION_NAME` | `str` | `"legal_labor_baseline_bge_m3"` | Tên collection đại diện cho baseline |
| `EMBEDDING_PROVIDER` | `str` | `"bge-m3"` | Nhà cung cấp embedding (`bge-m3` hoặc `openai`) |
| `EMBEDDING_MODEL` | `str` | `"BAAI/bge-m3"` | Định danh model HuggingFace hoặc OpenAI |
| `EMBEDDING_DIMENSION` | `int` | `1024` | Chiều véc-tơ (1024 cho bge-m3, 1536 cho openai) |
| `EMBEDDING_DEVICE` | `str` | `"cuda"` | Thiết bị chạy model (`cuda` hoặc `cpu`) |
| `EMBEDDING_BATCH_SIZE` | `int` | `64` | Kích thước lô khi đánh chỉ mục |
| `TOP_K` | `int` | `5` | Số lượng đoạn tài liệu truy hồi tối đa |
| `SIMILARITY_THRESHOLD`| `float` | `0.45` | Ngưỡng tương đồng cosine tối thiểu để đưa vào context |
| `LLM_PROVIDER` | `str` | `"openai"` | Nhà cung cấp LLM (`openai` hoặc `gemini`) |
| `LLM_MODEL` | `str` | `"gpt-4o-mini"` | Model LLM sinh phản hồi |
| `TEMPERATURE` | `float` | `0.0` | Khống chế tính ngẫu nhiên (0.0 cho sự kiện pháp lý) |
| `MAX_OUTPUT_TOKENS` | `int` | `1024` | Giới hạn số token câu trả lời của LLM |
| `MAX_CONTEXT_TOKENS` | `int` | `3000` | Giới hạn trần tổng token của khối ngữ cảnh |
| `OPENAI_API_KEY` | `str` | `""` | Khóa API OpenAI (lấy tự động từ môi trường) |
| `GEMINI_API_KEY` | `str` | `""` | Khóa API Google Gemini (lấy tự động từ môi trường) |

---

## 9. Dependency Graph (Sơ Đồ Phụ Thuộc Mã Nguồn)

```
[ .env / Environment Variables ]
              ↓
      [ rag/config.py ]
              ↓
  ┌───────────┴───────────┐
  ↓                       ↓
[ rag/schema.py ]   [ Data_Processing/models_v2.py ]
  ↓                       ↓
  ├───────────────┬───────┴───────────────┐
  ↓               ↓                       ↓
[ rag/embedding ] [ rag/vectorstore ] [ rag/context_builder.py ]
  └───────┬───────┘                       ↓
          ↓                               ↓
   [ rag/retriever ]             [ rag/prompt.py ]
          ↓                               ↓
          └───────────────┬───────────────┘
                          ↓
                   [ rag/llm ]
                          ↓
              [ rag/citation.py ]
                          ↓
            [ rag/pipeline.py ]
```

---

## 10. Baseline Limitations & Explicit Non-Goals

Để giữ vững tính chuẩn mực của một **Traditional RAG Baseline** dùng làm hệ quy chiếu (Benchmark Reference) cho các nghiên cứu chuyên sâu tiếp theo của Luận văn (Agentic RAG & Corrective RAG), kiến trúc được đóng băng nghiêm ngặt các giới hạn sau:

### 10.1. Baseline Limitations (Các Hạn Chế Cố Hữu của Baseline)
1. **Phụ thuộc hoàn toàn vào véc-tơ dày (Dense Retrieval Only)**: Không thể tìm kiếm chính xác tuyệt đối các mã định danh pháp lý rất cụ thể hoặc số hiệu nghị định hiếm gặp nếu embedding ngữ nghĩa không bắt trọn.
2. **Không có cơ chế đánh giá lại tài liệu (No Reranking)**: Thứ tự tài liệu đưa vào context phụ thuộc 100% vào khoảng cách cosine của bi-encoder, có thể bị nhiễu bởi các đoạn văn bản có từ khóa trùng nhưng sai ngữ cảnh áp dụng.
3. **Cố định số lượng tài liệu (Static Top-K)**: Luôn lấy tối đa $K=5$ đoạn kể cả câu hỏi đơn giản chỉ cần 1 đoạn hoặc câu hỏi phức hợp cần tổng hợp từ 8 đoạn.
4. **Không có khả năng tự sửa lỗi (No Self-Correction)**: Nếu Vector DB trả về tài liệu sai, LLM sẽ bị ảo giác hoặc phải từ chối trả lời; không có cơ chế tìm kiếm bù hay suy ngẫm.

### 10.2. Explicit Non-Goals (Các Thành Phần Nghiêm Cấm Triển Khai trong Baseline)

Các thành phần kỹ thuật sau đây **TUYỆT ĐỐI KHÔNG ĐƯỢC PHÉP XUẤT HIỆN** trong mã nguồn của Traditional RAG:

* ❌ **KHÔNG** triển khai BM25 / Sparse Retrieval
* ❌ **KHÔNG** triển khai Hybrid Search (RRF / Reciprocal Rank Fusion / Weighted Sum)
* ❌ **KHÔNG** tích hợp Cross-Encoder Reranker (bge-reranker, Cohere Rerank)
* ❌ **KHÔNG** triển khai Query Rewriting / Query Expansion / Synonyms Mapping
* ❌ **KHÔNG** triển khai Multi-Query / Sub-query generation
* ❌ **KHÔNG** triển khai HyDE (Hypothetical Document Embeddings)
* ❌ **KHÔNG** triển khai Query Decomposition / Step-back prompting
* ❌ **KHÔNG** triển khai Corrective RAG (CRAG) / Document Relevance Grader
* ❌ **KHÔNG** triển khai Retrieval Retry loops hoặc Fallback Web Search
* ❌ **KHÔNG** triển khai Self-Reflection / Self-Correction loops
* ❌ **KHÔNG** sử dụng Agent / ReAct Agent / Tool Use / Function Calling
* ❌ **KHÔNG** sử dụng Adaptive Router / Complexity Classifier / Intent Classifier
* ❌ **KHÔNG** sử dụng Confidence-based Routing

---

## 11. Implementation Sequence: RAG-01 → RAG-10

Lộ trình triển khai chi tiết từ RAG-01 đến RAG-10 được phân rã thành các tác vụ độc lập, tuần tự và có tiêu chí nghiệm thu rõ ràng:

```
RAG-00 ──► RAG-01 ──► RAG-02 ──► RAG-03 ──► RAG-04 ──► RAG-05
(Arch)     (Deps)     (Schema)   (Embed)    (Store)    (Retriever)
                                                           │
RAG-10 ◄── RAG-09 ◄── RAG-08 ◄── RAG-07 ◄── RAG-06 ◄──────┘
(Eval)     (E2E)      (Citation) (LLM)      (Context)
```

| Tác vụ | Tên tác vụ | Mục tiêu kỹ thuật | Sản phẩm bàn giao dự kiến |
|:---:|:---|:---|:---|
| **RAG-01** | **Dependencies & Environment Setup** | Thiết lập môi trường, tạo `requirements-rag.txt`, kiểm thử PyTorch CUDA trên RTX 5060, cài đặt ChromaDB và SDKs. | `requirements-rag.txt`, `tests/rag/test_env.py` |
| **RAG-02** | **Configuration & Schema Implementation** | Triển khai `rag/config.py` và `rag/schema.py`, tích hợp với `Data_Processing/models_v2.py`. | `rag/config.py`, `rag/schema.py`, unit tests |
| **RAG-03** | **Embedding Provider Implementation** | Xây dựng `EmbeddingProvider` hỗ trợ `BAAI/bge-m3` (CUDA) và `OpenAIEmbeddingProvider`. | `rag/embedding/*`, unit tests kiểm thử vector dimensions |
| **RAG-04** | **ChromaDB Vector Store & Indexing CLI** | Triển khai `ChromaVectorStore` và tập lệnh `rag/indexer.py` nạp trọn vẹn 1,390 chunks của Dataset V2.1. | `rag/vectorstore/*`, `rag/indexer.py`, thư mục `data/chroma_db/` |
| **RAG-05** | **Dense Retriever Implementation** | Triển khai `DenseRetriever`, xử lý câu truy vấn người dùng, Top-K cosine search, threshold filtering. | `rag/retriever/*`, unit tests truy hồi |
| **RAG-06** | **Context Builder & Token Budget Manager** | Xây dựng trình ghép ngữ cảnh có cấu trúc, kiểm soát trần 3,000 tokens và bảo toàn cấu trúc Điều/Khoản. | `rag/context_builder.py`, unit tests token capping |
| **RAG-07** | **Legal Prompt Engineering & LLM Wrapper** | Triển khai `rag/prompt.py` (system instructions & refusal rules) và `LLMProvider` (OpenAI / Gemini). | `rag/prompt.py`, `rag/llm/*`, unit tests |
| **RAG-08** | **Citation Formatter & Grounding Validator** | Triển khai trích xuất căn cứ pháp lý, sinh liên kết TVPL và thẩm định câu trả lời tuân thủ ngữ cảnh. | `rag/citation.py`, unit tests citation matching |
| **RAG-09** | **End-to-End Traditional RAG Pipeline** | Tích hợp toàn trình `TraditionalRAGPipeline`, hỗ trợ CLI query và kiểm thử tích hợp (E2E Integration Tests). | `rag/pipeline.py`, `main_baseline.py`, `test_pipeline_e2e.py` |
| **RAG-10** | **Baseline Evaluation & Freezing** | Đánh giá chất lượng trên bộ câu hỏi thử nghiệm pháp lý (Retrieval Hit@K, MRR, Faithfulness), đóng băng kết quả đo lường làm chuẩn so sánh cho Luận văn. | `reports/rag/RAG-10-BASELINE-EVALUATION.md` |

---

## 12. Verification & Freezing Statement

Báo cáo này chính thức **ĐÓNG BĂNG KIẾN TRÚC TRADITIONAL RAG BASELINE**. Tuyệt đối không bổ sung các kỹ thuật nâng cao (BM25, Hybrid, Reranker, Agentic, Corrective) trong giai đoạn xây dựng baseline này.
Tác vụ kế tiếp: **`RAG-01 — SETUP DEPENDENCIES & ENVIRONMENT`**.
