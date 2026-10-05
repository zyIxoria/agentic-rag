# BÁO CÁO TRIỂN KHAI CITATION MAPPING & REFUSAL GUARD (TASK RAG-06)
## Ánh Xạ Trích Dẫn Pháp Lý Thực Tế & Chốt Chặn An Toàn Cho Traditional RAG

* **Mã tác vụ**: `RAG-06`
* **Dự án**: Nghiên cứu cơ chế điều phối thích ứng trong hệ thống Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam
* **Thành phần**: `Citation Mapping` & `Refusal Guard`
* **Gói mã nguồn**: [`RAG/citation/`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/citation/), [`RAG/guards/`](file:///d:/Filehoc/KLCN/agentic-rag/RAG/guards/)
* **Bộ kiểm thử**: [`tests/citation/`](file:///d:/Filehoc/KLCN/agentic-rag/tests/citation/), [`tests/guards/`](file:///d:/Filehoc/KLCN/agentic-rag/tests/guards/)
* **Ngày hoàn tất**: 2026-09-16
* **Trạng thái**: `PASS (100% Validated & Verified)`

---

## 1. Mục Tiêu & Kiến Trúc Phân Hệ (Objective & Architecture)

Mục tiêu cốt lõi của **TASK RAG-06** là giải quyết 2 bài toán sống còn về độ tin cậy và an toàn trong hệ thống RAG pháp lý:
1. **Citation Mapping**: Chuyển đổi các nhãn nguồn `[SOURCE N]` sinh ra từ LLM thành trích dẫn pháp lý thực tế dựa 100% trên siêu dữ liệu (metadata) của các chunks đã thu hồi. Tuyệt đối không cho phép LLM tự tạo số hiệu văn bản, số điều hay URL tra cứu.
2. **Refusal Guard**: Thiết lập chốt chặn an toàn 2 tầng:
   - **Pre-generation Guard**: Chặn sớm trước khi gọi LLM nếu `retrieved_chunks == []` hoặc điểm tương đồng cao nhất dưới ngưỡng tối thiểu (`score < threshold`). Tiết kiệm chi phí gọi API và triệt tiêu nguy cơ ảo giác.
   - **Post-generation Guard**: Xác thực trích dẫn sau khi sinh. Nếu LLM viện dẫn nguồn không tồn tại (ví dụ: `[SOURCE 99]`), thực thi nguyên tắc `REJECT INVALID CITATION`, loại bỏ trích dẫn giả mạo và cưỡng chế từ chối nếu không có căn cứ hợp lệ.

### Sơ đồ luồng xử lý:
```text
User Question + Retrieved Chunks (từ RAG-03)
               ↓
     [Pre-Generation Refusal Guard]
     - Empty chunks? -> REFUSE (Không gọi LLM)
     - Max score < SIMILARITY_THRESHOLD (0.45)? -> REFUSE (Không gọi LLM)
               ↓
    Context Builder (RAG-04) + LLM Generator (RAG-05)
               ↓
LLM Output (Answer + [SOURCE N] tags)
               ↓
     [Citation Resolver & Validator]
     - Parse [SOURCE N] from answer & citations list
     - Validate against citation_mapping / context sources
     - If [SOURCE 99] (invalid): REJECT INVALID CITATION
     - If valid: Render legal citation (e.g. [Bộ luật Lao động 2019, Điều 125, Khoản 1])
     - Map official source_url to Footnotes
               ↓
     [Post-Generation Refusal Guard]
     - Validate unsupported claims
     - Trigger refusal if 100% citations are invalid
               ↓
Final Enriched Answer (Answer with Legal Citations + References Footnotes + Validated Metadata)
```

---

## 2. Quy Cách Định Dạng Trích Dẫn Pháp Lý (Legal Citation Format)

Trích dẫn pháp lý được chuẩn hóa theo quy tắc chặt chẽ từ siêu dữ liệu gốc:
- Cấu trúc cơ sở: `[{document_title}, {article_number}]`
  - Ví dụ: `[Bộ luật Lao động 2019, Điều 125]`
- Nếu văn bản có Khoản: `[{document_title}, {article_number}, {clause_number}]`
  - Ví dụ: `[Bộ luật Lao động 2019, Điều 125, Khoản 1]`
- Nếu văn bản có Điểm: `[{document_title}, {article_number}, {clause_number}, {point_number}]`
  - Ví dụ: `[Bộ luật Lao động 2019, Điều 125, Khoản 1, Điểm a]`

### Ánh Xạ Đường Dẫn Tra Cứu (URL Mapping):
Mỗi trích dẫn hợp lệ được liên kết với `source_url` chính thức từ cơ sở dữ liệu văn bản quy phạm pháp luật (ví dụ: Cổng thông tin điện tử Chính phủ hoặc Cơ sở dữ liệu quốc gia về văn bản pháp luật vbpl.vn), được hiển thị trong danh mục tài liệu tham chiếu (`Footnotes`).

---

## 3. Cơ Chế Xử Lý Trích Dẫn Không Hợp Lệ (REJECT INVALID CITATION)

Khi mô hình ngôn ngữ sinh nhãn trích dẫn không có trong danh sách nguồn được cung cấp (ví dụ: ngữ cảnh chỉ có 5 nguồn nhưng LLM sinh `[SOURCE 99]` hoặc `[SOURCE 404]`):
1. **Phát hiện & Đánh dấu**: Phân hệ `CitationResolver` đối chiếu với `citation_mapping`, gắn cờ `is_valid = False` và đưa vào danh sách `invalid_citations`.
2. **Loại bỏ khỏi văn bản**: Thẻ giả mạo bị loại bỏ khỏi nội dung câu trả lời hoặc thay thế bằng chuỗi rỗng an toàn, tránh gây hiểu lầm cho người tra cứu.
3. **Tuyệt đối không bịa đặt siêu dữ liệu**: Không bao giờ render số điều hay tên văn bản giả cho nguồn invalid.
4. **Post-Guard can thiệp**: Nếu câu trả lời chỉ chứa các trích dẫn giả mạo và không có bất kỳ trích dẫn hợp lệ nào, `RefusalGuard` sẽ cưỡng chế chuyển trạng thái sang `refused = True`.

---

## 4. Cơ Chế Chốt Chặn An Toàn (Refusal Guard Mechanism)

### 4.1. Chốt chặn trước khi sinh (Pre-generation Guard)
- **Kiểm tra Retrieval rỗng**: Nếu `len(retrieved_chunks) == 0`, dừng pipeline ngay lập tức, trả về kết quả từ chối mà không tiêu tốn token gọi LLM.
- **Kiểm tra Ngưỡng tương đồng (Similarity Threshold)**: Căn cứ theo kiến trúc RAG-00 (`SIMILARITY_THRESHOLD = 0.45`), nếu độ tương đồng Cosine cao nhất của toàn bộ các chunk thu hồi nhỏ hơn `0.45`, hệ thống kết luận bằng chứng không đủ độ tin cậy và kích hoạt từ chối sớm.

### 4.2. Chốt chặn sau khi sinh (Post-generation Guard)
- **Đồng thuận trạng thái từ chối**: Nếu Generator đã tự kích hoạt `refused = True`, Guard bảo lưu và chuẩn hóa thông điệp.
- **Chặn trích dẫn rỗng/giả mạo**: Nếu câu trả lời khẳng định sự việc nhưng 100% nguồn dẫn chiếu là invalid (như `[SOURCE 99]`), Guard tự động ghi đè câu trả lời thành câu từ chối chuẩn mực.

### 4.3. Thông báo từ chối chuẩn mực (Standard Refusal Message)
Khi `refused = True`, câu trả lời bắt buộc phải là chuỗi quy chuẩn:
`"Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy."`

---

## 5. Kết Quả Kiểm Thử Đơn Vị (Unit Test Matrix)

Bộ kiểm thử được phân bổ vào 2 test suites:
- [`tests/citation/test_citation.py`](file:///d:/Filehoc/KLCN/agentic-rag/tests/citation/test_citation.py): 8 tests
- [`tests/guards/test_refusal_guard.py`](file:///d:/Filehoc/KLCN/agentic-rag/tests/guards/test_refusal_guard.py): 7 tests

| STT | Phân hệ | Tên ca kiểm thử | Mục đích kiểm tra | Kết quả |
| :--- | :--- | :--- | :--- | :---: |
| 1 | Citation | `test_01_valid_single_citation` | Ánh xạ 1 nguồn trích dẫn hợp lệ từ metadata | **PASS** |
| 2 | Citation | `test_02_multiple_citations` | Ánh xạ đồng thời nhiều nguồn trích dẫn (`[SOURCE 1]`, `[SOURCE 2]`) | **PASS** |
| 3 | Citation | `test_03_invalid_source_number` | Từ chối `[SOURCE 99]`, không render trích dẫn giả (REJECT INVALID CITATION) | **PASS** |
| 4 | Citation | `test_04_missing_source_in_mapping` | Xử lý khi thẻ nguồn bị thiếu trong mapping | **PASS** |
| 5 | Citation | `test_05_citation_metadata_correctness` | Kiểm tra chính xác định dạng theo cấp Điều, Khoản, Điểm | **PASS** |
| 6 | Citation | `test_06_url_mapping` | Ánh xạ đúng `source_url` vào danh mục Footnotes | **PASS** |
| 7 | Citation | `test_07_in_text_replacement_and_footnotes` | Kiểm tra thay thế in-text và danh mục tham chiếu | **PASS** |
| 8 | Citation | `test_08_no_invented_citation` | Đảm bảo không bịa đặt số hiệu hay điều luật cho nguồn invalid | **PASS** |
| 9 | Guard | `test_01_empty_retrieval_refusal` | Pre-guard kích hoạt từ chối khi retrieval rỗng | **PASS** |
| 10 | Guard | `test_02_low_similarity_threshold_refusal` | Pre-guard kích hoạt từ chối khi similarity score < 0.45 | **PASS** |
| 11 | Guard | `test_03_valid_retrieval_pass` | Pre-guard cho phép đi tiếp khi score >= 0.45 | **PASS** |
| 12 | Guard | `test_04_post_generation_all_invalid_citations` | Post-guard can thiệp từ chối khi 100% trích dẫn là invalid | **PASS** |
| 13 | Guard | `test_05_post_generation_valid_citations_pass` | Post-guard chấp thuận khi câu trả lời có trích dẫn hợp lệ | **PASS** |
| 14 | Guard | `test_06_standard_refusal_message` | Đảm bảo thông báo từ chối luôn khớp đúng câu chuẩn | **PASS** |
| 15 | Guard | `test_07_configurable_threshold` | Kiểm tra khả năng cấu hình ngưỡng tương đồng linh hoạt | **PASS** |

* **Tổng số kiểm thử toàn dự án**: **72/72 tests PASS** (Embedding: 14, Vector Store: 14, Retriever: 10, Context: 8, Generator: 11, Citation: 8, Guard: 7).

---

## 6. Thử Nghiệm Tích Hợp Toàn Chuỗi (End-to-End Pipeline Simulation)

```text
1. Q: "Người sử dụng lao động có quyền sa thải người lao động trong những trường hợp nào?"
   -> Pre-guard: Passed
   -> Refused: False
   -> Valid Citations (3):
      - [Bộ luật Lao động 2019 số 45/2019/QH14, Điều 37]
      - [Bộ luật Lao động 2019 số 45/2019/QH14, Điều 48, Khoản 2]
      - [Nghị định số 145/2020/NĐ-CP, Điều 5, Khoản 6]
   -> Invalid Citations: []
   -> Latency: 411.81 ms

2. Q: "Thời giờ làm việc bình thường của người lao động được quy định như thế nào?"
   -> Pre-guard: Passed
   -> Refused: False
   -> Valid Citations (3):
      - [Thông tư số 09/2020/TT-BLĐTBXH, Điều 3, Khoản 6]
      - [Bộ luật Lao động 2019 số 45/2019/QH14, Điều 158]
      - [Bộ luật Lao động 2019 số 45/2019/QH14, Điều 166]
   -> Latency: 257.32 ms

3. Q: "Mức đóng bảo hiểm thất nghiệp của người sử dụng lao động theo Luật Việc làm?"
   -> Pre-guard: Passed
   -> Refused: False
   -> Valid Citations (5):
      - [Bộ luật Lao động 2019 số 45/2019/QH14, Điều 158]
      - [Thông tư số 20/2023/TT-BCT, Điều 10]
      - [Nghị định số 145/2020/NĐ-CP, Điều 4, Khoản 1]
      - [Bộ luật Lao động 2019 số 45/2019/QH14, Điều 40]
      - [Nghị định số 145/2020/NĐ-CP, Điều 2]
   -> Latency: 244.78 ms

4. Q: "Thời gian nghỉ thai sản của lao động nữ khi sinh con?"
   -> Pre-guard: Passed
   -> Refused: False
   -> Valid Citations (1):
      - [Bộ luật Lao động 2019 số 45/2019/QH14, Điều 139, Khoản 1 đến Khoản 2]
   -> Latency: 262.94 ms

5. Q: "Thủ tục đăng ký bảo hộ nhãn hiệu quốc tế theo Thỏa ước Madrid?"
   -> Pre-guard: Passed
   -> Refused: True (Kích hoạt từ chối do ngoài phạm vi tài liệu lao động)
   -> Answer: "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy."
   -> Latency: 246.83 ms

6. Q: "Cách mua vé xem bóng đá Ngoại hạng Anh mùa giải 2026?"
   -> Refused: True (Kích hoạt từ chối an toàn)
   -> Answer: "Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy."
   -> Latency: 253.09 ms
```

---

## 7. Danh Mục Kiểm Tra Nghiệm Thu (Acceptance Checklist)

- [x] **Citation generated from metadata**: 100% trích dẫn pháp lý được ánh xạ từ metadata thật của retrieved chunks.
- [x] **No invented citation**: Tuyệt đối không cho phép LLM tự tạo số hiệu văn bản, số điều hay URL.
- [x] **Invalid citation rejected**: Thẻ nguồn không hợp lệ (như `[SOURCE 99]`) bị loại bỏ triệt để (REJECT INVALID CITATION).
- [x] **Refusal works**: Chốt chặn từ chối 2 tầng (Pre-guard & Post-guard) hoạt động hoàn hảo, bảo đảm thông điệp quy chuẩn.
- [x] **Tests PASS**: 15/15 tests trong `tests/citation/` và `tests/guards/` cùng 72/72 tests toàn dự án đều PASS.
