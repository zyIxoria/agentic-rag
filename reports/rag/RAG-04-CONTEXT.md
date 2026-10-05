# BÁO CÁO XÂY DỰNG LEGAL CONTEXT BUILDER (TASK RAG-04)
## Đóng Gói Ngữ Cảnh Pháp Lý Chuẩn Hóa & Quản Lý Ngân Sách Token Cho LLM

* **Mã tác vụ**: `RAG-04`
* **Dự án**: Nghiên cứu cơ chế điều phối thích ứng trong hệ thống Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam
* **Thành phần**: `Legal Context Builder`
* **Gói mã nguồn**: [`RAG/context/`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/context/)
* **Bộ kiểm thử**: [`tests/context/`](file:///d:/Filehoc/KLCN/agentic-rag/tests/context/)
* **Ngày hoàn tất**: 2026-09-16
* **Trạng thái**: `PASS (100% Validated & Verified)`

---

## 1. Mục Tiêu & Phạm Vi Thực Thi (Objective & Strict Scope)

Mục tiêu trọng tâm của **TASK RAG-04** là tiếp nhận danh sách các đoạn luật thu hồi từ Dense Top-K Retriever (`RAG-03`), khử trùng lặp, định dạng thành các khối nguồn có cấu trúc rõ ràng và kiểm soát ngân sách token nghiêm ngặt để chuyển giao an toàn cho mô hình ngôn ngữ lớn (LLM).

```text
List[RetrievedChunk] (từ RAG-03)
            ↓
  1. Deduplication by chunk_id (Keep first occurrence)
            ↓
  2. Stable Source ID Assignment ([SOURCE 1], [SOURCE 2], ...)
            ↓
  3. Metadata Rendering (Document, Document Number, Article, Title, Clause, Point)
            ↓
  4. Verbatim Content Injection (No rewrite, No summarization)
            ↓
  5. Token Budgeting & Max Context Enforcement (MAX_CONTEXT_TOKENS = 3000)
            ↓
  BuildContextResult (Structured Context Text + Citation Mapping + Dropped Sources)
```

### Ràng buộc phạm vi nghiêm ngặt (Strict Scope & Non-Goals):
1. **Bảo tồn nguyên vẹn nội dung pháp lý (Verbatim Preservation)**: Tuyệt đối không tự ý viết lại (rewrite), diễn giải (paraphrase) hay tóm tắt (summarize) nội dung điều luật của chunk.
2. **Bảo toàn thứ tự thu hồi (Preserve Retrieval Order)**: Thứ tự xếp hạng từ RAG-03 (Rank 1, Rank 2, ...) được giữ nguyên vẹn tương ứng với `[SOURCE 1]`, `[SOURCE 2]`, ...
3. **Không để LLM tự suy đoán siêu dữ liệu trích dẫn**: Cung cấp đầy đủ văn bản, số hiệu, điều, tiêu đề, khoản, điểm trong header của từng nguồn.
4. **Không tự gọi lại retriever**: Khi bị tràn ngân sách token, Context Builder chỉ cắt giảm theo rank và ghi nhận vào `dropped_sources`.

---

## 2. Thiết Kế Định Dạng Khối Nguồn Chuẩn Hóa

Mỗi nguồn tài liệu pháp lý được hiển thị theo khuôn mẫu rõ ràng, giúp LLM dễ dàng tham chiếu và trích dẫn:

```text
[SOURCE 1]
Document: Bộ luật Lao động 2019
Document Number: 45/2019/QH14
Article: Điều 125
Article Title: Áp dụng hình thức xử lý kỷ luật sa thải
Clause: Khoản 1
Point: Điểm a
Content:
1. Người lao động có hành vi trộm cắp, tham ô, đánh bạc, cố ý gây thương tích...
```

* **Xử lý giá trị rỗng/None**: Nếu một trường siêu dữ liệu có giá trị `None` (ví dụ văn bản không chia Khoản hoặc Điểm), dòng thông tin đó sẽ được bỏ qua một cách tự nhiên, tuyệt đối không in chuỗi rác `"None"`.
* **Phân cách giữa các nguồn**: Sử dụng dải phân cách chuẩn hóa `\n\n---\n\n`.

---

## 3. Cơ Chế Khử Trùng Lặp (Deduplication by `chunk_id`)

Nếu cùng một `chunk_id` xuất hiện nhiều lần trong danh sách thu hồi (ví dụ do truy vấn lặp hoặc kết quả mở rộng):
* Hệ thống tuân thủ nguyên tắc **Keep first occurrence**: Bản ghi xuất hiện đầu tiên (có thứ hạng cao nhất và điểm tương đồng lớn nhất) được giữ lại.
* Các bản ghi xuất hiện sau có cùng `chunk_id` sẽ tự động bị loại bỏ mà không làm xáo trộn thứ tự đánh số nguồn `[SOURCE 1]`, `[SOURCE 2]`.

---

## 4. Kiểm Soát Ngân Sách Token (`MAX_CONTEXT_TOKENS`)

Hệ thống quản lý giới hạn token thông qua lớp `ContextConfig` với ngưỡng mặc định `MAX_CONTEXT_TOKENS = 3000` (đã đóng băng tại RAG-00):

* **Hệ số ước tính Token**: Sử dụng tỷ lệ BPE subword tiếng Việt `math.ceil(words * 1.3)`.
* **Nguyên tắc cắt giảm theo đơn vị toàn vẹn (Full Chunk Unit Truncation)**:
  * Khi việc bổ sung nguồn tiếp theo làm tổng số tokens vượt quá `MAX_CONTEXT_TOKENS`, hệ thống **ngắt ngay lập tức**.
  * Toàn bộ nguồn đó cùng các nguồn có rank thấp hơn được đưa vào danh sách `dropped_sources`.
  * **Tuyệt đối không cắt ngang giữa chừng** nội dung hoặc metadata của một chunk, bảo đảm văn bản luật đưa vào LLM luôn toàn vẹn và không bị đứt đoạn câu từ.

---

## 5. Bản Đồ Tra Cứu Trích Dẫn (`citation_mapping`)

Context Builder tạo ra đối tượng `citation_mapping` ánh xạ trực tiếp từ nhãn nguồn `[SOURCE X]` sang siêu dữ liệu pháp lý gốc:

```json
{
  "[SOURCE 1]": {
    "source_id": "[SOURCE 1]",
    "chunk_id": "BLLD_2019_Điều124_166",
    "document_id": "BLLD_2019",
    "document_number": "45/2019/QH14",
    "document_title": "Bộ luật Lao động 2019",
    "article_number": "Điều 124",
    "article_title": "Hình thức xử lý kỷ luật lao động",
    "clause_number": null,
    "point_number": null,
    "source_url": "https://thuvienphapluat.vn/...",
    "score": 0.721945,
    "rank": 1
  }
}
```
Bản đồ này cho phép mô-đun sinh câu trả lời (RAG-06) và bộ thẩm định trích dẫn (RAG-07) tự động kiểm tra xem LLM có trích dẫn đúng nguồn hay không mà không cần phân tích cú pháp lại context.

---

## 6. Kết Quả Thử Nghiệm Tích Hợp (Retriever -> Context Builder)

Thực thi tích hợp trên 5 câu hỏi pháp lý mẫu với `MAX_CONTEXT_TOKENS = 3000`:

| Mã | Câu hỏi pháp lý | Số chunks nhận | Số nguồn đưa vào | Số nguồn bị cắt | Tổng số Tokens | Tỷ lệ sử dụng ngân sách (3000 tokens) |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| **Q1** | *"Áp dụng hình thức xử lý kỷ luật sa thải"* | 5 | **5** (`[SOURCE 1]` → `[SOURCE 5]`) | 0 | **622 tokens** | 20.73% |
| **Q2** | *"Thời giờ làm việc bình thường của người lao động"* | 5 | **5** (`[SOURCE 1]` → `[SOURCE 5]`) | 0 | **761 tokens** | 25.37% |
| **Q3** | *"Thời gian thử việc đối với công việc"* | 5 | **5** (`[SOURCE 1]` → `[SOURCE 5]`) | 0 | **740 tokens** | 24.67% |
| **Q4** | *"Lao động nữ được nghỉ thai sản"* | 5 | **5** (`[SOURCE 1]` → `[SOURCE 5]`) | 0 | **869 tokens** | 28.97% |
| **Q5** | *"Tiền lương làm thêm giờ của người lao động"* | 5 | **5** (`[SOURCE 1]` → `[SOURCE 5]`) | 0 | **857 tokens** | 28.57% |

### Thử nghiệm tình huống tràn ngân sách token (Stress Test with `MAX_CONTEXT_TOKENS = 250`):
* **Đầu vào**: 5 chunks (tổng nhu cầu ~857 tokens).
* **Kết quả**:
  * **Số nguồn được đưa vào**: 1 nguồn (`[SOURCE 1]`, chiếm 189 tokens $\le$ 250).
  * **Số nguồn bị cắt bỏ (`dropped_sources`)**: 4 nguồn (Rank 2, Rank 3, Rank 4, Rank 5).
  * Khối nguồn `[SOURCE 1]` giữ nguyên vẹn 100% nội dung, không có hiện tượng cắt cụt giữa câu.

---

## 7. Kết Quả Bộ Kiểm Thử Đơn Vị (Unit Tests Execution)

Tất cả 8 ca kiểm thử trong [`tests/context/test_context_builder.py`](file:///d:/Filehoc/KLCN/agentic-rag/tests/context/test_context_builder.py) đều đạt kết quả `PASS`:

```text
test_01_source_numbering ... ok
test_02_metadata_rendering ... ok
test_03_duplicate_chunk_handling ... ok
test_04_max_context_limit ... ok
test_05_empty_retrieval ... ok
test_06_special_characters ... ok
test_07_citation_mapping ... ok
test_08_legal_content_unchanged ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.007s

OK
```

Toàn bộ hệ thống test suites của dự án hiện đạt **46/46 tests PASSED** (`tests/embedding/`, `tests/vector_store/`, `tests/retriever/`, `tests/context/`).

---

## 8. Bảng Đối Chiếu Tiêu Chí Nghiệm Thu (Acceptance Checklist)

| Tiêu chí nghiệm thu (Acceptance Criteria) | Trạng thái | Minh chứng kỹ thuật |
|:---|:---:|:---|
| **Context deterministic** | **PASS** | Cùng danh sách chunks đầu vào luôn sinh ra context_text giống nhau 100%. |
| **Source labels stable** | **PASS** | Nhãn nguồn `[SOURCE 1]`, `[SOURCE 2]`, ... đánh số liên tục theo thứ hạng thu hồi. |
| **Metadata preserved** | **PASS** | Hiển thị chính xác Document, Document Number, Article, Title, Clause, Point. |
| **Legal content unchanged** | **PASS** | Giữ nguyên từng ký tự của `chunk.content`, không rewrite, không summarize. |
| **Max context enforced** | **PASS** | Tôn trọng `MAX_CONTEXT_TOKENS`, cắt bỏ nguyên chunk theo rank và ghi nhận dropped sources. |
| **Tests PASS** | **PASS** | 8/8 unit tests đạt trạng thái OK trong 0.007 giây. |
