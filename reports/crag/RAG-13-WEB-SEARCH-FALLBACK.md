# BÁO CÁO CÀI ĐẶT QUERY TRANSFORMATION & WEB SEARCH FALLBACK - CRAG

## 1. TỔNG QUAN NHIỆM VỤ (TASK RAG-13)
- **Tên nhiệm vụ**: Xây dựng cơ chế Biến đổi truy vấn (Query Transformation / Rewriting) và Tìm kiếm ngoại bộ dự phòng (Web Search Fallback).
- **Mục tiêu**: Kích hoạt cơ chế cứu vãn thông tin khi Retrieval Evaluator (Document Grader) đánh giá toàn bộ tài liệu nội bộ là `INCORRECT` hoặc rơi vào vùng `AMBIGUOUS`. Chuyển đổi câu hỏi tự nhiên dài dòng của người dùng thành từ khóa tìm kiếm cô đọng, truy cứu tri thức chuẩn xác từ nguồn tài liệu tham khảo pháp lý uy tín.
- **Cơ sở khoa học**: Theo thiết kế Corrective RAG (Yan et al., 2024), khi kho dữ liệu nội bộ không chứa câu trả lời hoặc dense retrieval thất bại (Zero Hit Rate), hệ thống không được tạo ảo giác mà phải viết lại câu hỏi và kích hoạt Search Fallback hoặc từ chối tường minh có căn cứ.

---

## 2. KIẾN TRÚC VÀ CÁC THÀNH PHẦN

### 2.1. Bộ viết lại truy vấn pháp lý (LegalQueryRewriter)
- **Loại bỏ giao tiếp hội thoại**: Cắt bỏ các tiền tố xưng hô (`"cho em hỏi"`, `"xin cho biết"`, `"sếp bắt tôi"`) và các câu hỏi đuôi (`"như vậy có đúng không"`, `"thì xử lý thế nào"`).
- **Bảo tồn thực thể pháp lý**: Nhận diện số hiệu điều luật (`Điều 125`, `Điều 25`) và số hiệu văn bản (`Nghị định 12/2022/NĐ-CP`, `Bộ luật Lao động 2019`).
- **Neo ngữ cảnh miền pháp lý (Domain Anchoring)**: Bổ sung từ khóa định danh ngành (`"quy định pháp luật lao động"`) khi câu hỏi là dạng ngôn ngữ tự nhiên không chứa tên văn bản, tránh việc search engine trả về các kết quả đời sống dân sự không liên quan.

### 2.2. Web Search Fallback Engine
- Cấu trúc giao diện mở rộng: `BaseWebSearcher` với phương thức `search(query, transformed_query, top_k) -> SearchResponse`.
- **MockLegalWebSearcher**: Được nạp các văn bản quy phạm pháp luật và chế tài hành chính quan trọng (như Nghị định 12/2022/NĐ-CP về xử phạt vi phạm hành chính trong lĩnh vực lao động, chế độ thai sản, thời hiệu kỷ luật) để đảm bảo 100% khả năng kiểm thử ngoại tuyến, độc lập với kết nối internet và không chịu rủi ro thay đổi API từ bên thứ ba.
- **LegalWebSearcher**: Dispatcher phân phối linh hoạt giữa Mock và Live Search thông qua cấu hình `SEARCH_PROVIDER`.

---

## 3. KẾT QUẢ KIỂM THỬ (UNIT TESTS)
Toàn bộ 6 test cases trong `tests/crag/test_web_search_fallback.py` đều vượt qua:
1. `test_query_rewriter_conversational_removal`: Lọc bỏ triệt để từ ngữ hội thoại, giữ lại từ khóa nghiệp vụ.
2. `test_query_rewriter_entity_preservation`: Nhận diện và bảo toàn chính xác Điều 125 và Nghị định 12/2022/NĐ-CP.
3. `test_query_rewriter_domain_anchoring`: Tự động bổ sung neo ngữ cảnh pháp luật lao động.
4. `test_mock_searcher_exact_keyword_hit`: Truy xuất chính xác trích đoạn xử phạt vi phạm thử việc theo Nghị định 12/2022/NĐ-CP.
5. `test_mock_searcher_latency_measurable`: Đo lường độ trễ tìm kiếm chính xác (số thực dương).
6. `test_legal_web_searcher_dispatch`: Dispatcher hoạt động trơn tru theo cấu hình.
