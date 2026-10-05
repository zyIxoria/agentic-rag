# BÁO CÁO CÀI ĐẶT QUERY DECOMPOSITION & SUB-QUERY PLANNER - ADAPTIVE RAG

## 1. TỔNG QUAN NHIỆM VỤ (TASK RAG-16)
- **Tên nhiệm vụ**: Xây dựng cơ chế Phân rã câu hỏi và Lập kế hoạch thực thi truy vấn con (Query Decomposition & Sub-query Planner).
- **Mục tiêu**: Khắc phục điểm yếu lớn nhất của cả Traditional RAG và Corrective RAG trên nhóm câu hỏi điều kiện phức tạp (Complex Conditions - chỉ đạt 33.33% ở RAG-14) và câu hỏi đa văn bản (Multi-Document).
- **Cơ sở khoa học**: Thay vì gửi toàn bộ một câu hỏi dài gồm nhiều mệnh đề xung đột hoặc liên văn bản vào một lượt Dense Retrieval duy nhất (dẫn đến việc véc-tơ trung bình hóa làm lu mờ các thực thể con), Query Decomposer bẻ tách câu hỏi thành $N$ truy vấn con nguyên tử (Atomic Sub-queries), kèm theo chiến lược thực thi (Song song hoặc Tuần tự) và chỉ dẫn tổng hợp (Synthesis Instruction).

---

## 2. THIẾT KẾ VÀ KIẾN TRÚC PHÂN RÃ

### 2.1. Nhận diện và Phân loại mẫu câu phức tạp
Lớp `LegalQueryDecomposer` áp dụng 4 chiến lược phân rã:
1. **Phân rã đa văn bản (Multi-Document Decomposition)**:
   - Nhận diện khi câu hỏi chứa từ 2 văn bản quy phạm trở lên (ví dụ: `Bộ luật Lao động 2019` và `Nghị định 145/2020/NĐ-CP`) hoặc các từ khóa so sánh đối chiếu.
   - Tạo ra các Sub-queries độc lập tập trung tra cứu vào từng văn bản mục tiêu.
   - Chiến lược: `ExecutionStrategy.PARALLEL`.
2. **Phân rã điều kiện tương phản (Contrastive Conditional Decomposition)**:
   - Nhận diện khi câu hỏi có các vế điều kiện xung đột pháp lý (ví dụ: vi phạm kỷ luật bị sa thải NHƯNG đang mang thai hoặc nuôi con dưới 12 tháng).
   - Tách thành 3 Sub-queries:
     - Sub 1: Căn cứ sa thải (Điều 125).
     - Sub 2: Trường hợp cấm/hoãn kỷ luật (Điều 122).
     - Sub 3: Hậu quả pháp lý nếu xử lý sai (Điều 41).
   - Chiến lược: `ExecutionStrategy.HYBRID` (Sub 1 & 2 song song, Sub 3 phụ thuộc).
3. **Phân rã câu hỏi kép liên từ "và" (Compound Questions)**:
   - Tách 2 vế câu hỏi riêng biệt: khía cạnh nội dung quyền lợi và khía cạnh chế tài xử phạt hành chính.
4. **Bảo tồn câu hỏi đơn nguyên (Atomic Queries)**:
   - Các câu hỏi đơn giản không bị phân rã thừa, giữ nguyên 1 truy vấn.

### 2.2. Cấu trúc Kế hoạch phân rã (DecompositionPlan)
- `SubQuery`: `sub_id`, `text` (đã bổ sung đầy đủ chủ ngữ/vị ngữ), `target_entity`, `dependency_ids`, `execution_order`.
- `ExecutionStrategy`: `PARALLEL`, `SEQUENTIAL`, `HYBRID`.
- `synthesis_instruction`: Hướng dẫn cho bộ tổng hợp (Synthesizer) cách liên kết các câu trả lời bộ phận.

---

## 3. KẾT QUẢ KIỂM THỬ (UNIT TESTS)
Toàn bộ 4 test cases trong `tests/adaptive/test_query_decomposition.py` đã vượt qua:
1. `test_decompose_multi_document`: Phân rã chính xác câu hỏi liên văn bản thành 2 sub-queries tương ứng theo từng văn bản quy phạm.
2. `test_decompose_contrastive_conditional`: Phân rã mâu thuẫn pháp lý sa thải vs bảo vệ thai sản thành các câu hỏi con có quan hệ phụ thuộc.
3. `test_decompose_compound_question`: Phân tách câu hỏi kép có liên từ "và".
4. `test_decompose_atomic_query`: Bảo tồn câu hỏi đơn nguyên không gây phân mảnh dư thừa.
