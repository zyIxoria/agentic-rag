# BÁO CÁO CÀI ĐẶT KNOWLEDGE REFINEMENT (STRIP & FILTER) - CRAG

## 1. TỔNG QUAN NHIỆM VỤ (TASK RAG-12)
- **Tên nhiệm vụ**: Xây dựng cơ chế bóc tách dải tri thức và lọc nhiễu nội bộ (Knowledge Refinement: Decompose, Strip & Filter).
- **Mục tiêu**: Loại bỏ hiện tượng trôi dạt ngữ cảnh (Context Distraction/Drift) trong Traditional RAG khi các đoạn/khoản không liên quan nằm chung một chunk lớn (ví dụ: một điều luật có 4 khoản nhưng câu hỏi người dùng chỉ đề cập đến 1 tình huống cụ thể).
- **Cơ sở khoa học**: Tuân thủ nguyên lý Corrective RAG (Yan et al., 2024), phân nhỏ tài liệu thành dải tri thức câu/khoản (Knowledge Strips), đánh giá mức độ liên quan cục bộ, loại bỏ các strip rác dưới ngưỡng $\tau_{\text{strip}} = 0.50$, và tái cấu trúc context cô đọng, giàu thông tin.

---

## 2. KIẾN TRÚC VÀ CÁC THÀNH PHẦN

### 2.1. Phân rã văn bản (Text Decomposition)
Bộ `KnowledgeStripper` bóc tách văn bản pháp lý thành các đơn vị tri thức ngữ nghĩa:
- **Article Heading**: Nhận diện tiêu đề Điều luật (ví dụ: `Điều 125. Áp dụng hình thức xử lý kỷ luật sa thải`) và giữ lại làm anchor ngữ cảnh bắt buộc để bảo toàn thông tin số hiệu điều luật phục vụ trích dẫn pháp lý.
- **Numbered Clauses / Points**: Nhận diện các khoản đánh số (`1. `, `2. `) và điểm (`a) `, `b) `).
- **Sentence Level Fallback**: Phân tách câu theo dấu chấm câu đối với các đoạn văn xuôi dài $> 250$ ký tự.

### 2.2. Chấm điểm và Lọc nhiễu cục bộ (Local Strip Scoring & Filtering)
- Tinh lọc bộ từ dừng chuyên biệt cho lĩnh vực pháp luật lao động (loại bỏ các chủ thể phổ quát như `"người"`, `"lao"`, `"động"`, `"sử dụng"` vốn xuất hiện ở hầu hết mọi câu).
- Tính toán điểm liên quan kết hợp:
  $$S_{\text{strip}} = 0.25 \cdot S_{\text{chunk}} + 0.50 \cdot \text{OverlapRatio}_{\text{keywords}} + 0.25 \cdot \text{Bonus}_{\text{bigram}}$$
- Nếu strip không chứa từ khóa chuyên biệt nào từ câu hỏi: điểm bị phạt $\le 0.30 \to$ loại bỏ (Filter out).
- Ngưỡng lọc: $\tau_{\text{strip}} = 0.50$. Các strip có $S_{\text{strip}} \ge 0.50$ hoặc là tiêu đề điều luật sẽ được giữ lại.

### 2.3. Tái cấu trúc ngữ cảnh (Knowledge Recomposition)
Bộ `KnowledgeRecomposer` thực hiện:
- Tổ chức lại các strip được giữ lại theo thứ tự nguyên bản trong văn bản luật.
- Định dạng có cấu trúc theo chuẩn `[SOURCE N]` tương thích hoàn toàn với LLM Generator và Citation Guard.
- Ghép nối linh hoạt tri thức ngoại bộ khi kích hoạt cơ chế Fallback Web Search.
- Đo lường hệ số nén ngữ cảnh ($\text{Compression Ratio} = 1 - \frac{\text{Refined Chars}}{\text{Original Chars}}$).

---

## 3. KẾT QUẢ KIỂM THỬ (UNIT TESTS)
Toàn bộ 7 test cases trong `tests/crag/test_knowledge_refinement.py` đã hoàn thành xuất sắc:
1. `test_split_into_strips`: Phân rã chính xác điều luật thành các strip có cấu trúc (heading + các khoản).
2. `test_strip_scoring_and_filtering`: Lọc bỏ thành công các khoản không liên quan trực tiếp đến câu hỏi trong cùng một điều luật.
3. `test_preserve_heading_strip`: Bảo tồn 100% tiêu đề điều luật phục vụ truy vết citation.
4. `test_recomposer_structure`: Context đầu ra chuẩn format `[SOURCE N]` với đầy đủ metadata.
5. `test_compression_ratio_positive`: Hệ số nén đạt giá trị dương (giảm thiểu các ký tự nhiễu).
6. `test_recomposer_with_external_knowledge`: Tích hợp mượt mà tri thức ngoài (Web Search snippets).
7. `test_empty_chunks_recompose`: Xử lý an toàn khi danh sách chunks rỗng.
