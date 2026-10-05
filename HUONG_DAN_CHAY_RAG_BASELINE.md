# TÀI LIỆU HƯỚNG DẪN CHẠY MÔ HÌNH TRADITIONAL RAG BASELINE
*(Phiên bản chuẩn hóa đối sánh: `Traditional-RAG-v1`)*

---

## 1. TỔNG QUAN HỆ THỐNG

**Traditional RAG Baseline** là mô hình cơ sở đầu tiên trong đề tài nghiên cứu, được xây dựng theo kiến trúc tuyến tính, xác định (deterministic), không có logic tự thích ứng ẩn:

```text
User Question
      ↓
Query Preparation (Kiểm tra rỗng, chuẩn hóa)
      ↓
Embedding Pipeline (sentence-transformers/all-MiniLM-L6-v2, 384 chiều)
      ↓
Dense Vector Retrieval (ChromaDB - Cosine Similarity, Top-K = 5)
      ↓
Pre-Generation Refusal Guard (Ngưỡng tương đồng tối thiểu >= 0.45)
      ↓
Legal Context Builder (Đóng gói định dạng [SOURCE N], tối đa 3,000 tokens)
      ↓
Legal Generator (Sinh câu trả lời tiếng Việt, nhiệt độ = 0.0, bảo toàn trích dẫn)
      ↓
Citation Resolver (Ánh xạ [SOURCE N] thành tên văn bản, Điều luật và phụ lục)
      ↓
Post-Generation Refusal Guard (Kiểm tra tính hợp lệ của trích dẫn)
      ↓
Final RAGResponse (Câu trả lời + Trích dẫn + Đo lường độ trễ chi tiết)
```

* **Dữ liệu nguồn**: 1,390 chunks pháp lý thuộc **Dataset V2.1** (15 văn bản quy phạm pháp luật lao động Việt Nam).
* **Vector Store**: Lưu trữ tại thư mục `data/chroma_db/`, collection `legal_labor_baseline_minilm`.

---

## 2. CÁCH 1: CHẠY TRỰC TIẾP TƯƠNG TÁC QUA DÒNG LỆNH (CLI)

Chúng tôi đã đóng gói sẵn công cụ chạy dòng lệnh cực kỳ tiện lợi: [`run_rag_baseline.py`](file:///d:/Filehoc/KLCN/agentic-rag/run_rag_baseline.py).

### A. Chế độ chat tương tác liên tục (Interactive Chatbot)
Mở Terminal / PowerShell tại thư mục gốc của dự án và chạy:
```bash
python run_rag_baseline.py
```
* Hệ thống sẽ khởi động giao diện hỏi đáp tương tác.
* Bạn chỉ cần gõ câu hỏi tiếng Việt và nhấn `Enter`.
* Để kết thúc phiên làm việc, gõ `exit`, `quit`, hoặc `q`.

### B. Chế độ tra cứu 1 câu hỏi nhanh (Single Query)
```bash
python run_rag_baseline.py --query "Người lao động có được đơn phương chấm dứt hợp đồng khi đang mang thai không?"
```

### C. Tùy chỉnh tham số nâng cao
* **Đổi số lượng chunks thu hồi (`--top-k`)**:
  ```bash
  python run_rag_baseline.py --query "Quy định về thời gian thử việc" --top-k 10
  ```
* **Đổi ngưỡng tương đồng tối thiểu (`--threshold`)**:
  ```bash
  python run_rag_baseline.py --query "Quy định về sa thải" --threshold 0.50
  ```
* **Chọn mô hình LLM Generator (`--provider`)**:
  ```bash
  # Mặc định: engine mock ngoại tuyến (tất định, không tốn phí, tuân thủ nghiêm ngặt 100% luật)
  python run_rag_baseline.py --provider mock

  # Sử dụng OpenAI (cần cấu hình OPENAI_API_KEY trong .env)
  python run_rag_baseline.py --provider openai --model gpt-4o-mini

  # Sử dụng Gemini (cần cấu hình GEMINI_API_KEY trong .env)
  python run_rag_baseline.py --provider gemini --model gemini-1.5-flash
  ```

---

## 3. CÁCH 2: GỌI TRONG CODE PYTHON (PYTHON API)

Bạn có thể dễ dàng nhúng mô hình vào bất kỳ kịch bản thử nghiệm hoặc ứng dụng nào:

```python
from RAG.pipeline import TraditionalRAGPipeline
from RAG.pipeline.config import PipelineConfig

# 1. Khởi tạo cấu hình mặc định hoặc tùy biến
config = PipelineConfig(
    TOP_K=5,                       # Lấy Top 5 kết quả gần nhất
    SIMILARITY_THRESHOLD=0.45,     # Ngưỡng lọc rác
    LLM_PROVIDER="mock",           # 'mock', 'openai', hoặc 'gemini'
    TEMPERATURE=0.0                # Bảo đảm tính tất định
)

# 2. Khởi tạo pipeline
pipeline = TraditionalRAGPipeline(config=config)

# 3. Đặt câu hỏi và nhận kết quả
question = "Trường hợp nào người sử dụng lao động được sa thải người lao động?"
response = pipeline.answer(question)

# 4. Trích xuất thông tin phản hồi
print("--- CÂU TRẢ LỜI ---")
print(response.answer)

print("\n--- TRẠNG THÁI TỪ CHỐI ---")
print(f"Bị từ chối: {response.refused} (Lý do: {response.refusal_reason})")

print("\n--- THÔNG SỐ ĐỘ TRỄ ---")
print(f"Độ trễ thu hồi: {response.retrieval_latency} ms")
print(f"Độ trễ sinh: {response.generation_latency} ms")
print(f"Tổng thời gian: {response.latency} ms")

print("\n--- DANH SÁCH CHUNKS THU HỒI ---")
for chunk in response.retrieved_chunks:
    print(f"• [{chunk.chunk_id}] (Score: {chunk.score:.4f}): {chunk.content[:100]}...")
```

---

## 4. CÁCH 3: CHẠY BỘ ĐÁNH GIÁ ĐỐI CHUẨN BENCHMARK (EVALUATION)

Để tái hiện lại toàn bộ kết quả đo lường khoa học phục vụ luận văn:

### A. Đánh giá riêng tầng Thu hồi (Retrieval Evaluation - RAG-09)
Chạy đánh giá các chỉ số `Recall@K`, `Hit Rate@K`, `Precision@K`, `MRR` trên 80 câu hỏi:
```bash
python evaluation/evaluate_retrieval.py
```
* Kết quả thô được lưu tại: `evaluation/results/retrieval_baseline.json`
* Báo cáo phân tích chi tiết tại: `reports/rag/RAG-09-RETRIEVAL-EVAL.md`

### B. Đánh giá toàn chuỗi End-to-End RAG (Full Baseline Evaluation - RAG-10)
Chạy đánh giá toàn bộ các chỉ số `Answer Correctness`, `Faithfulness`, `Citation Accuracy`, `Refusal Accuracy`, `Latency`, và `Token Cost`:
```bash
python evaluation/runner/baseline_runner.py
```
* Kết quả thô được lưu tại: `evaluation/results/traditional_baseline_full_eval.json`
* Báo cáo chính thức tại: `reports/rag/RAG-10-BASELINE-EVAL.md`
* Văn bản đóng băng tại: `reports/rag/TRADITIONAL-RAG-BASELINE-FROZEN.md`

---

## 5. CÁCH 4: CHẠY BỘ KIỂM THỬ TỰ ĐỘNG (UNIT & INTEGRATION TESTS)

Dự án có tổng cộng **97 bài kiểm thử** tự động phủ kín 100% các phân hệ.

### Chạy toàn bộ 90 tests của hệ thống RAG:
```bash
python -m unittest discover -s tests -t . -v
```

### Chạy riêng 7 tests kiểm tra dataset benchmark:
```bash
python -m unittest discover -s evaluation/tests -v
```

### Chạy kiểm tra từng phân hệ riêng lẻ:
```bash
# Kiểm tra embedding pipeline
python -m unittest discover -s tests/embedding -t . -v

# Kiểm tra vector store (ChromaDB)
python -m unittest discover -s tests/vector_store -t . -v

# Kiểm tra retriever
python -m unittest discover -s tests/retriever -t . -v

# Kiểm tra context builder
python -m unittest discover -s tests/context -t . -v

# Kiểm tra generator
python -m unittest discover -s tests/generator -t . -v

# Kiểm tra citation & guards
python -m unittest discover -s tests/citation -t . -v
python -m unittest discover -s tests/guards -t . -v

# Kiểm tra pipeline E2E
python -m unittest discover -s tests/rag -t . -v

# Kiểm tra evaluation metrics
python -m unittest tests/evaluation/test_baseline_eval.py -v
```

---

## 6. CẤU HÌNH BIẾN MÔI TRƯỜNG (`.env`)

Mô hình Traditional RAG có thể chạy **hoàn toàn ngoại tuyến (Offline)** mà không cần kết nối Internet hoặc API key. Tuy nhiên, nếu bạn muốn kết nối với OpenAI GPT hoặc Google Gemini, tạo file `.env` tại thư mục gốc với các thông số:

```env
# Nhà cung cấp LLM: 'mock', 'openai', hoặc 'gemini'
LLM_PROVIDER=mock

# Cấu hình OpenAI (nếu dùng OpenAI)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Cấu hình Gemini (nếu dùng Gemini)
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-1.5-flash

# Cấu hình Embedding Model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=64

# Cấu hình Vector Store & Pipeline
CHROMA_PERSIST_DIRECTORY=data/chroma_db
COLLECTION_NAME=legal_labor_baseline_minilm
TOP_K=5
SIMILARITY_THRESHOLD=0.45
MAX_CONTEXT_TOKENS=3000
```

---

## 7. ĐỊNH DẠNG KẾT QUẢ PHẢN HỒI (`RAGResponse`)

Đối tượng trả về từ phương thức `pipeline.answer(question)` chứa đầy đủ các thuộc tính có cấu trúc:

| Thuộc tính (Field) | Kiểu dữ liệu | Diễn giải |
|:---|:---|:---|
| `question` | `str` | Câu hỏi gốc của người dùng. |
| `answer` | `str` | Câu trả lời cuối cùng đã được thay thế trích dẫn nội văn và gắn phụ lục chân trang. |
| `citations` | `List[LegalCitation]` | Danh sách các đối tượng trích dẫn pháp lý chính xác (gồm `document_title`, `article_number`, `source_url`, v.v.). |
| `retrieved_chunks` | `List[RetrievedChunk]` | Danh sách Top-K đoạn văn bản được thu hồi từ ChromaDB kèm điểm tương đồng `score` và `rank`. |
| `refused` | `bool` | `True` nếu hệ thống kích hoạt cơ chế từ chối do câu hỏi thiếu dữ liệu hoặc ngoài phạm vi. |
| `refusal_reason` | `Optional[str]` | Lý do từ chối cụ thể (từ Pre-guard hoặc Generator). |
| `retrieval_latency` | `float` | Thời gian tính vector embedding và truy vấn ChromaDB (ms). |
| `context_latency` | `float` | Thời gian lọc và đóng gói ngữ cảnh (ms). |
| `generation_latency` | `float` | Thời gian sinh câu trả lời (ms). |
| `citation_latency` | `float` | Thời gian giải nghĩa trích dẫn và kiểm tra guard (ms). |
| `latency` | `float` | Tổng độ trễ toàn chuỗi (ms). |
| `model_name` | `str` | Tên mô hình LLM được sử dụng. |
| `provider` | `str` | Nhà cung cấp LLM (`mock`, `openai`, `gemini`). |

---

## 8. LIÊN HỆ CÁC BÁO CÁO NGHIỆM THU

* **Báo cáo kiến trúc hệ thống**: [`reports/rag/RAG-00-ARCHITECTURE.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/rag/RAG-00-ARCHITECTURE.md)
* **Báo cáo tích hợp E2E**: [`reports/rag/RAG-07-E2E.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/rag/RAG-07-E2E.md)
* **Báo cáo bộ đối chuẩn RAG-08**: [`reports/rag/RAG-08-EVALUATION-DATASET.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/rag/RAG-08-EVALUATION-DATASET.md)
* **Báo cáo thu hồi RAG-09**: [`reports/rag/RAG-09-RETRIEVAL-EVAL.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/rag/RAG-09-RETRIEVAL-EVAL.md)
* **Báo cáo đánh giá toàn diện RAG-10**: [`reports/rag/RAG-10-BASELINE-EVAL.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/rag/RAG-10-BASELINE-EVAL.md)
* **Văn bản đóng băng Baseline**: [`reports/rag/TRADITIONAL-RAG-BASELINE-FROZEN.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/rag/TRADITIONAL-RAG-BASELINE-FROZEN.md)
