# BÁO CÁO TÍCH HỢP TOÀN CHUỖI TRADITIONAL RAG BASELINE (TASK RAG-07)
## Đóng Gói Hoàn Chỉnh Quy Trình Hỏi Đáp Pháp Luật Tuyến Tính & Đo Lường Hiệu Năng

* **Mã tác vụ**: `RAG-07`
* **Dự án**: Nghiên cứu cơ chế điều phối thích ứng trong hệ thống Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam
* **Thành phần**: `End-to-End Traditional RAG Pipeline`
* **Gói mã nguồn**: [`RAG/pipeline/`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/pipeline/), [`RAG/schemas/`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/schemas/)
* **Bộ kiểm thử**: [`tests/rag/`](file:///d:/Filehoc/KLCN/agentic-rag/tests/rag/)
* **Ngày hoàn tất**: 2026-09-16
* **Trạng thái**: `PASS (100% Validated & Verified)`

---

## 1. Mục Tiêu & Kiến Trúc Tích Hợp Tuyến Tính (Linear E2E Pipeline)

Mục tiêu của **TASK RAG-07** là tích hợp toàn bộ các mắt xích độc lập từ RAG-01 đến RAG-06 thành một pipeline hỏi đáp hoàn chỉnh, đóng vai trò là **Traditional RAG Baseline chuẩn mực** phục vụ so sánh đối chuẩn khoa học với Corrective RAG và Agentic RAG sau này.

### Sơ đồ luồng xử lý E2E:
```text
User Question
      ↓ (Tiền kiểm tra tính hợp lệ: không rỗng, không rewrite)
DenseTopKRetriever (RAG-03)
      ↓ (Top-K Chunks + Cosine Similarity Scores + Retrieval Latency)
Pre-Generation Refusal Guard (RAG-06)
      ↓ (Kiểm tra mảng rỗng & max_score < 0.45 -> Kích hoạt từ chối sớm, 0 token LLM)
LegalContextBuilder (RAG-04)
      ↓ (Khử trùng lặp, Stable [SOURCE N] Formatting, kiểm soát trần 3000 tokens)
LLM Legal Generator (RAG-05)
      ↓ (temperature=0.0, Structured JSON Output, văn phong pháp lý Việt Nam)
CitationResolver (RAG-06)
      ↓ (Ánh xạ [SOURCE N] sang [Document, Article, Clause, Point] & REJECT INVALID CITATION)
Post-Generation Refusal Guard (RAG-06)
      ↓ (Xác thực trích dẫn hợp lệ, cưỡng chế từ chối nếu 100% citations là giả mạo)
RAGResponse (Final Answer + Citations + Retrieved Chunks + Latency Metrics)
```

---

## 2. Ràng Buộc "No Hidden Intelligence" Tuyệt Đối

Traditional RAG Baseline được đóng băng nghiêm ngặt để đảm bảo tính thuần túy của kiến trúc RAG truyền thống:
1. **Không Query Rewriting**: Không tự động viết lại, sửa đổi hoặc mở rộng câu hỏi của người dùng.
2. **Không Query Decomposition**: Không phân rã câu hỏi thành nhiều truy vấn con.
3. **Không Dynamic K**: Không tự động thay đổi số lượng K chunks thu hồi theo độ khó câu hỏi.
4. **Không Reranker**: Không áp dụng Cross-Encoder (bge-reranker hay Cohere) để sắp xếp lại kết quả.
5. **Không Retrieval Retry Loops**: Không có vòng lặp thử lại thu hồi khi điểm thấp.
6. **Không External Agents**: Không gọi subagent bổ sung hay điều phối thích ứng (Adaptive/Corrective).
7. **Tần suất thực thi chuẩn**: Mỗi câu hỏi của người dùng thực hiện chính xác:
   - **01 lần** tạo embedding câu hỏi.
   - **01 lần** thu hồi véc-tơ (Dense Retrieval).
   - **01 lần** đóng gói ngữ cảnh (Context Building).
   - **Tối đa 01 lần** gọi LLM Generator (bằng 0 nếu bị Pre-Guard chặn từ chối sớm).

---

## 3. Giao Diện Pipeline & Mô Hình Dữ Liệu `RAGResponse`

Giao diện thực thi chuẩn mực:
```python
from RAG.pipeline import TraditionalRAGPipeline

pipeline = TraditionalRAGPipeline()
response: RAGResponse = pipeline.answer("Thời giờ làm việc bình thường của người lao động?")
```

### Cấu trúc dữ liệu `RAGResponse`:
```python
class RAGResponse(BaseModel):
    question: str                   # Câu hỏi ban đầu của người dùng
    answer: str                     # Câu trả lời hoàn chỉnh kèm trích dẫn và phụ lục
    citations: List[LegalCitation]  # Danh sách trích dẫn pháp lý đầy đủ metadata
    retrieved_chunks: List[RetrievedChunk] # Chunks thu hồi gốc kèm score và rank
    latency: float                  # Tổng thời gian thực thi toàn chuỗi (ms)
    refused: bool                   # Trạng thái từ chối do thiếu căn cứ
    refusal_reason: Optional[str]   # Chi tiết lý do từ chối nếu có
    retrieval_latency: float        # Thời gian tìm kiếm véc-tơ (ms)
    context_latency: float          # Thời gian dựng ngữ cảnh (ms)
    generation_latency: float       # Thời gian sinh của LLM (ms)
    citation_latency: float         # Thời gian ánh xạ trích dẫn (ms)
    model_name: Optional[str]       # Tên mô hình LLM thực thi
    provider: Optional[str]         # Nhà cung cấp LLM
    metadata: Dict[str, Any]        # Thông tin chẩn đoán kỹ thuật
```

---

## 4. Ghi Log Có Cấu Trúc (Structured Logging)

Hệ thống ghi nhận đầy đủ telemetry phục vụ giám sát và kiểm toán khoa học mà không ghi lộ thông tin nhạy cảm hay API keys:
- `query`: Câu hỏi người dùng.
- `top_k`: Số lượng chunks yêu cầu thu hồi.
- `chunk_ids`: Danh sách ID các đoạn trích thu hồi được.
- `scores`: Danh sách điểm tương đồng ngữ nghĩa Cosine Similarity.
- `retrieval_latency`: Độ trễ vector search (ms).
- `context_size`: Kích thước ngữ cảnh (tokens).
- `generation_latency`: Độ trễ sinh câu trả lời (ms).
- `total_latency`: Tổng độ trễ toàn chuỗi (ms).
- `refused`: Trạng thái từ chối (`True`/`False`).
- `citations`: Danh sách các trích dẫn pháp lý tạo ra.

---

## 5. Kết Quả Kiểm Thử Đơn Vị & Tích Hợp (Unit Test Matrix)

Test suite tại [`tests/rag/test_pipeline.py`](file:///d:/Filehoc/KLCN/agentic-rag/tests/rag/test_pipeline.py) bao phủ 9 ca kiểm định toàn diện:

| STT | Tên ca kiểm thử | Mục đích kiểm tra | Kết quả |
| :--- | :--- | :--- | :---: |
| 1 | `test_01_simple_legal_question` | Câu hỏi pháp lý cơ bản vận hành trơn tru E2E | **PASS** |
| 2 | `test_02_article_specific_question` | Câu hỏi nhắm vào điều cụ thể (Điều 125 BLLD), trích dẫn chuẩn xác | **PASS** |
| 3 | `test_03_multi_source_question` | Câu hỏi đa nguồn, ánh xạ đầy đủ nhiều trích dẫn pháp lý | **PASS** |
| 4 | `test_04_irrelevant_question` | Câu hỏi ngoài phạm vi kích hoạt từ chối với thông báo chuẩn mực | **PASS** |
| 5 | `test_05_insufficient_evidence_refusal` | Ngữ cảnh có score thấp (< 0.45) bị Pre-Guard chặn từ chối sớm (0 LLM call) | **PASS** |
| 6 | `test_06_citation_validation` | Trích dẫn pháp lý trong văn bản và footnote URL chính xác 100% | **PASS** |
| 7 | `test_07_end_to_end_failure_handling` | Kiểm tra câu hỏi rỗng và bắt lỗi an toàn (Fail-fast với ValueError) | **PASS** |
| 8 | `test_08_no_hidden_intelligence_verification` | Kiểm tra đúng 1 lượt retrieval, 1 lượt context build, 1 generation | **PASS** |
| 9 | `test_09_latency_metrics_measurable` | Đảm bảo toàn bộ các chỉ số độ trễ đều dương và đo lường được | **PASS** |

* **Tổng số tests toàn dự án**: **81/81 tests PASS** (Embedding: 14, Vector Store: 14, Retriever: 10, Context: 8, Generator: 11, Citation: 8, Guards: 7, Pipeline E2E: 9).

---

## 6. Kết Quả Benchmark Hiệu Năng & Đo Lường Độ Trễ (Benchmark Results)

Thử nghiệm trên 7 câu hỏi đại diện thuộc các nhóm nghiệp vụ khác nhau:

| ID | Câu hỏi | Loại câu hỏi | Refused | Citations | Retrieval Latency | Generation Latency | Tổng Latency |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Q1** | Người sử dụng lao động có quyền sa thải người lao động trong trường hợp nào? | Cụ thể (Điều 125) | `False` | 3 nguồn | 517.29 ms | 1.44 ms | **520.73 ms** |
| **Q2** | Thời giờ làm việc bình thường của người lao động được quy định như thế nào? | Tổng quan (Điều 105) | `False` | 3 nguồn | 317.89 ms | 0.93 ms | **320.21 ms** |
| **Q3** | Mức đóng bảo hiểm thất nghiệp của người sử dụng lao động theo Luật Việc làm? | Luật chuyên ngành | `False` | 5 nguồn | 304.54 ms | 0.99 ms | **307.26 ms** |
| **Q4** | Thời gian nghỉ thai sản của lao động nữ khi sinh con? | Cụ thể (Điều 139) | `False` | 1 nguồn | 327.27 ms | 0.69 ms | **328.71 ms** |
| **Q5** | Thủ tục đăng ký bảo hộ nhãn hiệu quốc tế theo Thỏa ước Madrid? | Ngoài phạm vi | `True` | 0 nguồn | 294.76 ms | 0.40 ms | **295.53 ms** |
| **Q6** | Cách mua vé xem giải bóng đá Ngoại hạng Anh mùa giải 2026? | Hoàn toàn phi lý | `True` | 0 nguồn | 318.93 ms | 0.52 ms | **319.91 ms** |
| **Q7** | Người lao động có được tạm hoãn HĐLĐ khi đi nghĩa vụ quân sự không? | Cụ thể (Điều 31) | `False` | 4 nguồn | 310.65 ms | 0.94 ms | **312.85 ms** |

### Tổng hợp thống kê:
- **Số câu hỏi thử nghiệm**: 7
- **Số câu trả lời thành công**: 5 (71.43%)
- **Số câu từ chối an toàn**: 2 (28.57%)
- **Độ trễ trung bình (Average Latency)**: **343.60 ms**
- **Độ trễ trung vị (Median Latency)**: **319.91 ms**
- **Độ trễ thu hồi trung bình (Retrieval Latency)**: **341.62 ms**
- **Độ trễ sinh trung bình (Generation Latency)**: **0.84 ms** (với Mock Engine cục bộ)
- **Độ trễ dựng ngữ cảnh & trích dẫn**: **~1.09 ms**

---

## 7. Danh Mục Kiểm Tra Nghiệm Thu (Acceptance Checklist)

- [x] **E2E pipeline works**: Toàn bộ chuỗi hỏi đáp Traditional RAG vận hành trơn tru từ câu hỏi đến câu trả lời cuối cùng.
- [x] **Deterministic configuration**: Cấu hình tập trung, tất định (`temperature = 0.0`, `SIMILARITY_THRESHOLD = 0.45`, `MAX_CONTEXT_TOKENS = 3000`).
- [x] **Retrieval result traceable**: Các đoạn văn bản thu hồi được lưu vết đầy đủ trong `retrieved_chunks`.
- [x] **Citation traceable**: 100% trích dẫn pháp lý được truy vết ngược về siêu dữ liệu gốc và chunk ID.
- [x] **Refusal works**: Cơ chế từ chối 2 tầng hoạt động hoàn hảo với thông báo quy chuẩn: *"Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy."*
- [x] **Latency measurable**: Toàn bộ các mốc thời gian thành phần (Retrieval, Context, Generation, Citation, Total) đều được đo lường chính xác bằng mili-giây.
- [x] **Tests PASS**: 9/9 tests trong `tests/rag/` và 81/81 tests toàn bộ dự án đều PASS.
- [x] **No corrective/adaptive logic**: Tuyệt đối không có query rewriting, reranking, hay retry loops.
