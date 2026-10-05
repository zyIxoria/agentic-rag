# BÁO CÁO THIẾT KẾ & KIỂM THỬ QUERY REWRITER (CRAG-02)

## 1. MỤC TIÊU & NGUYÊN TẮC THIẾT KẾ
Khi kết quả thu hồi lần đầu không đạt trạng thái `SUFFICIENT` (`PARTIAL` hoặc `INSUFFICIENT`), việc truy vấn lại (retry) với nguyên văn câu hỏi ban đầu là hoàn toàn vô nghĩa đối với mô hình Dense Retrieval tất định.
Module `QueryRewriter` (hiện thực tại `RAG/corrective/rewriter.py`) có nhiệm vụ tối ưu hóa câu hỏi người dùng thành một truy vấn tìm kiếm pháp lý chuẩn mực nhằm gia tăng cơ hội khớp véc-tơ ngữ nghĩa trong cơ sở dữ liệu.

### Quy tắc tối ưu hóa (Positive Transformations):
1. **Làm rõ chủ thể**: Mở rộng các viết tắt (`NLĐ` -> *người lao động*, `NSDLĐ` -> *người sử dụng lao động*, `HĐLĐ` -> *hợp đồng lao động*, `BHXH` -> *bảo hiểm xã hội*).
2. **Chuẩn hóa thuật ngữ đời thường thành thuật ngữ pháp lý**:
   - *"đuổi việc"* -> *xử lý kỷ luật sa thải*
   - *"nghỉ đẻ"* -> *nghỉ thai sản*
   - *"tăng ca"* -> *làm thêm giờ*
   - *"cưới / lấy vợ / lấy chồng"* -> *kết hôn*
   - *"nghỉ khi kết hôn"* -> *nghỉ việc riêng hưởng nguyên lương khi kết hôn*
3. **Làm rõ điều kiện & khung thời gian**: Bổ sung phạm vi áp dụng (ví dụ: làm thêm giờ tối đa *trong một ngày, một tháng và một năm*).
4. **Loại bỏ đệm hội thoại**: Cắt bỏ các cụm từ đệm xưng hô, chào hỏi (*"cho em hỏi ad ơi"*, *"ạ"*, *"nhỉ"*, *"nhé"*).

### RÀNG BUỘC PHÒNG CHỐNG BỊA ĐẶT (STRICT NEGATIVE CONSTRAINTS):
Nhằm bảo đảm tính khách quan và ngăn ngừa hiện tượng ảo giác (hallucination):
- **TUYỆT ĐỐI KHÔNG TỰ THÊM SỐ ĐIỀU LUẬT**: Không được tự động chèn *"Điều 115"*, *"Điều 107"* nếu câu gốc không nêu.
- **TUYỆT ĐỐI KHÔNG TỰ THÊM SỐ HIỆU NGHỊ ĐỊNH / THÔNG TƯ**: Không được tự chèn *"Nghị định 145/2020/NĐ-CP"*, v.v.
- **CƠ CHẾ ENFORCE_NEGATIVE_CONSTRAINTS**: Bộ lọc Regex tự động quét và thu hồi dứt khoát bất kỳ số điều hoặc số hiệu văn bản nào xuất hiện ngoài phạm vi câu gốc.

---

## 2. VÍ DỤ MINH HỌA
| Câu hỏi ban đầu (Original Query) | Truy vấn sau khi viết lại (Rewritten Query) | Ghi chú chuyển đổi |
|---|---|---|
| *"Cho em hỏi ad ơi, người lao động bị đuổi việc thì cần lý do gì ạ?"* | *"Quy định về người lao động bị xử lý kỷ luật sa thải thì cần lý do gì"* | Bỏ từ đệm, chuẩn hóa thuật ngữ sa thải |
| *"Thời gian nghỉ thai sản tối đa là mấy tháng?"* | *"Quy định đối với người lao động về thời gian nghỉ thai sản tối đa là mấy tháng"* | Bổ sung chủ thể pháp lý người lao động |
| *"Người lao động được nghỉ bao nhiêu ngày khi kết hôn?"* | *"Quy định về người lao động được nghỉ việc riêng hưởng nguyên lương khi kết hôn bao nhiêu ngày"* | Làm rõ điều kiện nghỉ hưởng lương |
| *"Số giờ làm thêm tối đa của người lao động?"* | *"Quy định về số làm thêm giờ tối đa của người lao động trong một ngày, một tháng và một năm"* | Làm rõ khung thời gian đối chiếu |

---

## 3. KẾT QUẢ KIỂM THỬ ĐƠN VỊ (UNIT TESTS)
Tập kiểm thử `tests/test_query_rewriter.py` đã thực thi thành công 7/7 ca kiểm thử:
- `test_01_clear_query_preserves_intent`: **PASSED** (Bảo toàn ý định câu hỏi rõ ràng).
- `test_02_ambiguous_conversational_query_clarified`: **PASSED** (Làm sạch câu hỏi hội thoại).
- `test_03_missing_subject_made_explicit`: **PASSED** (Bổ sung chủ thể người lao động).
- `test_04_missing_condition_clarified`: **PASSED** (Làm rõ chế độ nghỉ kết hôn hưởng lương).
- `test_05_timeframe_clarified`: **PASSED** (Làm rõ khung thời gian làm thêm).
- `test_06_already_sufficient_query_not_overwritten`: **PASSED** (Không viết lại quá mức khi câu đã chuẩn).
- `test_07_no_hallucination_of_article_or_decree_number`: **PASSED** (100% không bịa đặt số Điều, số Nghị định).
