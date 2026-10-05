# BÁO CÁO THIẾT KẾ & KIỂM THỬ RETRIEVAL EVALUATOR (CRAG-01)

## 1. MỤC TIÊU & NHIỆM VỤ
Trong hệ thống Traditional RAG, Retriever chỉ dựa hoàn toàn vào điểm khoảng cách véc-tơ (Cosine Distance/Similarity) để xếp hạng các đoạn văn bản. Tuy nhiên, thực nghiệm trên tập câu hỏi pháp luật lao động (đặc biệt là nhóm Category F - *Insufficient Evidence* và Category G - *Out-of-Scope*) đã chỉ ra khiếm khuyết chí mạng:
> **High Similarity != Sufficient Evidence** (Điểm tương đồng cao không đồng nghĩa với việc đoạn trích chứa đầy đủ căn cứ pháp lý để trả lời câu hỏi).

Module `RetrievalEvaluator` (hiện thực tại `RAG/corrective/evaluator.py`) được thiết kế nhằm độc lập thẩm định chất lượng các đoạn văn bản thu hồi trước khi đưa vào bộ sinh (Generator).

---

## 2. KIẾN TRÚC & SCHEMA DỮ LIỆU
Module tuân thủ nghiêm ngặt cấu trúc `RetrievalEvaluation` định nghĩa tại `RAG/corrective/schemas.py`:

```json
{
  "status": "SUFFICIENT | PARTIAL | INSUFFICIENT",
  "confidence": 0.95,
  "relevant_chunk_ids": ["BLLD_2019_Điều105_139"],
  "irrelevant_chunk_ids": ["BLLD_2019_Điều107_145"],
  "reason": "Giải thích chi tiết căn cứ đáp ứng hoặc thiếu hụt"
}
```

### Các ràng buộc toàn vẹn bắt buộc (Invariants):
1. **Enum Status**: Chỉ chấp nhận `SUFFICIENT`, `PARTIAL`, hoặc `INSUFFICIENT`.
2. **Confidence Range**: Bắt buộc nằm trong đoạn $[0.0, 1.0]$.
3. **Disjoint & Valid Subset**: `relevant_chunk_ids` và `irrelevant_chunk_ids` phải là hai tập hợp rời nhau và hoàn toàn là tập con của danh sách chunk thu hồi.
4. **Distractor Handling**: Tự động phát hiện các đoạn trích gây nhiễu (distractors) có cosine similarity cao nhưng thiếu điều kiện cốt lõi (ví dụ: truy vấn hỏi về *"tích lũy giờ làm thêm"* nhưng chunk chỉ quy định về *"làm thêm giờ"* thông thường).

---

## 3. CƠ CHẾ THẨM ĐỊNH NỘI TẠI
1. **Kiểm tra truy vấn rỗng hoặc tập thu hồi rỗng**: Trả về `INSUFFICIENT` với `confidence = 1.0`.
2. **Phát hiện Out-of-Scope**: Đối chiếu với danh mục các chủ đề hoàn toàn nằm ngoài pháp luật lao động (nhãn hiệu, visa, ly hôn, chứng khoán, thể thao, v.v.). Nếu phát hiện, gán toàn bộ chunk là `irrelevant_chunk_ids` và trả về `INSUFFICIENT` (`confidence = 0.95`).
3. **Phát hiện văn bản ngoài cơ sở dữ liệu (Missing External Laws)**: Nhận diện các câu hỏi đòi hỏi trực tiếp quy định của các luật không có trong 15 văn bản pháp luật của Dataset V2.1 (như Luật Bảo hiểm xã hội 2014, Luật Công đoàn 2012, Luật Việc làm, Luật An toàn vệ sinh lao động 2015). Đánh giá `INSUFFICIENT` dứt khoát.
4. **Phân tích điều kiện đặc thù & Phân loại tính đầy đủ**:
   - Phân tích sự hiện diện của các ràng buộc nghiệp vụ (tỷ lệ %, thời hạn, số giờ, tích lũy).
   - Nếu $\ge 2$ chunk khớp đầy đủ các vế câu hỏi: Đạt `SUFFICIENT`.
   - Nếu chỉ giải quyết được một vế trong câu hỏi phức hợp/đa điều kiện: Đạt `PARTIAL`.
   - Nếu không có chunk nào chứa bằng chứng trực tiếp: Đạt `INSUFFICIENT`.

---

## 4. KẾT QUẢ KIỂM THỬ ĐƠN VỊ (UNIT TESTS)
Tập kiểm thử `tests/test_corrective_evaluator.py` đã thực thi thành công 9/9 ca kiểm thử:
- `test_01_relevant_retrieval_sufficient`: **PASSED** (Thu hồi đúng Điều 105 -> `SUFFICIENT`).
- `test_02_partially_relevant_retrieval_partial`: **PASSED** (Câu hỏi kép chỉ tìm thấy 1 vế -> `PARTIAL`).
- `test_03_irrelevant_retrieval_insufficient`: **PASSED** (Câu hỏi tích lũy giờ làm thêm gặp chunk distractor Điều 107 -> `INSUFFICIENT`).
- `test_04_empty_retrieval_insufficient`: **PASSED** (Tập rỗng -> `INSUFFICIENT`, confidence = 1.0).
- `test_05_mixed_relevant_irrelevant`: **PASSED** (Phân tách chính xác chunk thử việc và chunk xử phạt).
- `test_06_invalid_evaluator_output_validation`: **PASSED** (Bắt lỗi chunk ID giả mạo không có trong tập thu hồi).
- `test_07_confidence_less_than_zero_rejected`: **PASSED** (Bắt lỗi confidence < 0).
- `test_08_confidence_greater_than_one_rejected`: **PASSED** (Bắt lỗi confidence > 1).
- `test_09_unknown_status_rejected`: **PASSED** (Bắt lỗi status không hợp lệ).
