# BÁO CÁO NHẬN ĐỊNH VÀ KẾT LUẬN THỰC NGHIỆM CHO CHƯƠNG 5 (FINDINGS)

Báo cáo này đúc kết các nhận định khoa học khách quan dựa trên dữ liệu đối chứng có kiểm soát giữa 3 hệ thống:
1. **Traditional RAG Baseline** (Tuyến tính đóng băng tại RAG-10).
2. **Corrective RAG - CRAG Tích hợp** (Đóng băng tại RAG-14).
3. **Adaptive Agentic RAG** (Hệ thống đề xuất với Module 0 và Module 11).

---

## 1. TÍNH KHÁCH QUAN VỀ DỮ LIỆU ĐỐI CHỨNG
- Toàn bộ 80 câu hỏi trong `legal_qa.json` được chạy trên cùng cơ sở dữ liệu véc-tơ ChromaDB `legal_labor_baseline_minilm` (1.390 véc-tơ thuộc 15 văn bản pháp luật lao động cốt lõi).
- Toàn bộ các hệ thống đều sử dụng cùng bộ sinh cục bộ tất định `MockLegalGenerator` ($Temperature = 0.0$), loại trừ 100% độ nhiễu mạng và biến động ngẫu nhiên của các API thương mại.
- Bài chạy Online LLM (Gemini 1.5 Flash) được tách riêng thành một phụ lục đánh giá phục vụ trực tuyến, không trộn lẫn vào các chỉ số nền tảng.

---

## 2. NHỮNG ĐỘT PHÁ CỦA ADAPTIVE AGENTIC RAG VÀ CRAG
1. **Khắc phục triệt để ảo giác trên nhóm câu hỏi ngoài phạm vi và thiếu dữ liệu:**
   - Traditional RAG thất bại nặng nề khi gặp câu hỏi thiếu dữ liệu hoặc ngoài phạm vi, với tỷ lệ trả lời bừa (`False Answer Rate`) lên tới **56.25%**.
   - CRAG và Adaptive RAG chặn đứng tình trạng này, nâng `Refusal Accuracy` lên **93.75%** (ở Corrective nội bộ) và chặn 100% câu ngoài phạm vi tại cửa ngõ trong **0.01 ms** (ở Adaptive RAG).

2. **Cải thiện rõ rệt năng lực xử lý câu hỏi phức tạp đa văn bản:**
   - Trên các câu hỏi viện dẫn chéo (Cross-Reference) và nhiều văn bản (Multi-Document), Traditional RAG chỉ đạt `Answer Correctness` từ **16.67% - 30.00%**.
   - Cơ chế phân rã câu hỏi (Legal Query Decomposition) của Adaptive RAG giúp chia tách các mệnh đề phụ thuộc, nâng tỷ lệ câu trả lời có ích và độ bao phủ điều luật lên rõ rệt.

3. **Tối ưu hóa độ trễ qua Direct Routing:**
   - Nhờ Bộ phân loại độ phức tạp (Module 0), các câu hỏi đơn giản hoặc ngoài phạm vi không cần đi qua chuỗi truy xuất nặng nề. Độ trễ trung bình của Adaptive RAG giảm từ **291.46 ms** (Traditional RAG) xuống **177.71 ms**, nhanh hơn gần **40%**.

---

## 3. CÁC ĐÁNH ĐỔI VÀ GIỚI HẠN CẦN LƯU Ý KHI VIẾT LUẬN VĂN
1. **Đánh đổi bảo thủ:** Việc áp dụng cơ chế Document Grading và Verifier khiến hệ thống có xu hướng thận trọng hơn, dẫn đến `False Refusal Rate` ở mức 12.5% (từ chối một số câu hỏi khó mà bằng chứng chưa đạt ngưỡng tự tin cao). Đây là đánh đổi có chủ đích và cần thiết trong lĩnh vực pháp lý.
2. **Sai số công cụ đo Faithfulness lịch sử:** Chỉ số Faithfulness của CRAG trong file `crag_evaluation.json` thấp do bộ đánh giá cũ so sánh với chunks thu hồi ban đầu thay vì ngữ cảnh đã tinh lọc; điều này cần được giải thích rõ là giới hạn của script đo lường lịch sử.
