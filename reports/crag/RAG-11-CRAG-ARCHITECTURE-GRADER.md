# BÁO CÁO THIẾT KẾ KIẾN TRÚC VÀ CÀI ĐẶT RETRIEVAL EVALUATOR (CRAG)

## 1. TỔNG QUAN NHIỆM VỤ (TASK RAG-11)
- **Tên nhiệm vụ**: Thiết kế kiến trúc Corrective RAG (CRAG) và Xây dựng Retrieval Evaluator (Document Grader).
- **Mục tiêu**: Khắc phục triệt để khiếm khuyết của Traditional RAG (được định lượng tại RAG-09 và RAG-10) khi dense retriever nạp cả các chunk rác, trôi ngữ cảnh hoặc khi toàn bộ kết quả truy xuất đều không liên quan đến câu hỏi pháp lý.
- **Tiêu chuẩn học thuật**: Dựa trên kiến trúc Corrective Retrieval Augmented Generation (Yan et al., 2024), tích hợp cơ chế hiệu chuẩn đặc thù cho ngôn ngữ văn bản quy phạm pháp luật Việt Nam.

---

## 2. THIẾT KẾ KIẾN TRÚC CRAG (CORRECTIVE RAG ARCHITECTURE)

### 2.1. Luồng xử lý tổng thể (Workflow)
```text
                  [User Question]
                         │
                         ▼
             [Dense Top-K Retrieval]
                         │
                   Retrieved Chunks
                         │
                         ▼
        ┌───────────────────────────────────┐
        │        Document Grader            │
        │ (Evaluates Confidence & Content)  │
        └─────────────────┬─────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
     All INCORRECT    AMBIGUOUS      At least 1
          │          (Borderline)     CORRECT
          ▼               ▼               ▼
      [Action]        [Action]        [Action]
     WEB_SEARCH    COMBINE_SEARCH      REFINE
     (or REFUSE)          │               │
          │               ├───────────────┘
          │               ▼
          │       [Strip & Filter]
          │   (Filter internal noise)
          │               │
          ▼               ▼
   [Web Knowledge]  [Refined Legal Context]
          └───────────────┬───────────────┘
                          ▼
              [Conservative Generator]
                          │
                          ▼
            [Citation & Refusal Guard]
                          │
                          ▼
                    [Final Answer]
```

### 2.2. Quy tắc phân định hành động (Decision Boundary)
Dựa trên ngưỡng tin cậy hiệu chuẩn:
- **Upper Threshold** ($\tau_{\text{upper}} = 0.68$): Điểm số $\ge 0.68$ phân loại là `CORRECT`.
- **Lower Threshold** ($\tau_{\text{lower}} = 0.45$): Điểm số $< 0.45$ phân loại là `INCORRECT`.
- **Dải phân vân** $[0.45, 0.68)$: Phân loại là `AMBIGUOUS`.

Từ đánh giá từng tài liệu, Document Grader xác định hành động cấp hệ thống (`ActionTrigger`):
1. **REFINE**: Nếu có ít nhất 1 tài liệu đạt chuẩn `CORRECT`. Hệ thống chuyển sang bước Strip & Filter loại bỏ nhiễu nội bộ trong chunk trước khi tạo context.
2. **WEB_SEARCH**: Nếu toàn bộ tài liệu bị đánh giá là `INCORRECT` và câu hỏi thuộc phạm vi cần tra cứu bổ sung.
3. **REFUSE**: Nếu câu hỏi được phát hiện rõ ràng là ngoài phạm vi pháp luật lao động (Out-of-scope) hoặc không thể tra cứu.
4. **COMBINE_SEARCH**: Nếu không có tài liệu nào chắc chắn đúng nhưng có tài liệu tiềm năng (`AMBIGUOUS`). Hệ thống sẽ kết hợp tài liệu nội bộ đã tinh lọc cùng thông tin bổ sung.

---

## 3. CƠ CHẾ ĐÁNH GIÁ (SEMANTIC DOCUMENT GRADER)

### 3.1. Phương pháp chấm điểm kết hợp (Hybrid Confidence Scoring)
Do hiện tượng ngữ nghĩa dày đặc của embedding dense retriever khiến các chunk chứa từ vựng hành chính chung có cosine similarity tương đối cao dù nội dung sai lệch, `SemanticDocumentGrader` áp dụng công thức kết hợp:
$$S_{\text{calibrated}} = \alpha \cdot S_{\text{dense}} + \beta \cdot S_{\text{lexical\_topic}} - P_{\text{out\_of\_scope}}$$

Trong đó:
- $S_{\text{dense}}$: Cosine similarity của dense retriever (đã chuẩn hóa).
- $S_{\text{lexical\_topic}}$: Điểm trùng khớp thực thể pháp lý (Số điều luật, cụm danh từ nòng cốt: "sa thải", "thử việc", "nghỉ thai sản", v.v.).
- $P_{\text{out\_of\_scope}}$: Điểm phạt nghiêm khắc đối với câu hỏi vi phạm phạm vi (giao thông, đấu thầu, hộ chiếu, đất đai).

### 3.2. Cấu trúc Schema
- `GradeVerdict`: Enum gồm `CORRECT`, `AMBIGUOUS`, `INCORRECT`.
- `ActionTrigger`: Enum gồm `REFINE`, `WEB_SEARCH`, `COMBINE_SEARCH`, `REFUSE`.
- `DocumentGrade`: Chứa `chunk_id`, `score`, `verdict`, `rationale`, `extracted_key_phrases`.
- `RetrievalGradingResult`: Chứa `action`, `confidence`, `document_grades`, `correct_count`, `ambiguous_count`, `incorrect_count`.

---

## 4. KẾT QUẢ KIỂM THỬ (UNIT TESTS)
Toàn bộ 8 test case trong `tests/crag/test_document_grader.py` đều vượt qua:
1. `test_grade_document_correct`: Đánh giá chính xác tài liệu phù hợp (Điểm $\ge 0.68$, `GradeVerdict.CORRECT`).
2. `test_grade_document_incorrect`: Đánh giá chính xác tài liệu lạc đề dù dense score tương đối cao (`GradeVerdict.INCORRECT`).
3. `test_grade_document_out_of_scope`: Phạt triệt để câu hỏi ngoài phạm vi nghiệp vụ.
4. `test_grade_documents_action_refine`: Kích hoạt hành động `REFINE` khi có tài liệu tin cậy.
5. `test_grade_documents_action_combine_search`: Kích hoạt `COMBINE_SEARCH` khi tài liệu ở mức mơ hồ `AMBIGUOUS`.
6. `test_grade_documents_action_web_search`: Kích hoạt `WEB_SEARCH` khi toàn bộ tài liệu bị phân loại `INCORRECT`.
7. `test_grade_documents_action_refuse`: Kích hoạt `REFUSE` khi câu hỏi ngoài phạm vi pháp luật lao động.
8. `test_empty_chunks_handling`: Xử lý an toàn khi danh sách chunks rỗng.

Toàn bộ test suite hồi quy (98 tests) đạt tỷ lệ vượt qua **100%**.
