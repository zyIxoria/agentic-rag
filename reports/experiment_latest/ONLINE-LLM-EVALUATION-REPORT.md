# BÁO CÁO ĐÁNH GIÁ END-TO-END TRÊN MÔ HÌNH LLM TRỰC TUYẾN THỰC TẾ
*(ONLINE LLM SERVING BENCHMARK REPORT)*

**Hệ thống thực nghiệm**: Adaptive Agentic Legal RAG với Online LLM Serving (Google Gemini 1.5 Flash & OpenAI GPT-4o-mini).  
**Quy mô kiểm định**: 80 câu hỏi trắc nghiệm và tự luận pháp luật lao động đa cấp độ.  
**Thời điểm thực hiện**: 2026-11-04 11:35:04  

---

## 1. TỔNG QUAN HIỆU NĂNG VẬN HÀNH & ĐỘ TRỄ MẠNG THỰC TẾ (LATENCY PROFILE)

| Chỉ số độ trễ (Latency Metric) | Giá trị thực tế | Nhận xét vận hành |
| :--- | :---: | :--- |
| **Độ trễ trung bình (Mean Latency)** | **1460.07 ms** (~1.46s) | Đáp ứng tốt tiêu chuẩn tương tác thời gian thực cho hệ thống trợ lý ảo |
| **Độ trễ trung vị (P50 Latency)** | **1443.38 ms** | 50% số câu hỏi được phản hồi trong vòng chưa đầy 1.5 giây |
| **Độ trễ phân vị 95 (P95 Latency)** | **1791.78 ms** | Đảm bảo chặn đứng hiện tượng nghẽn mạng trên các câu hỏi đa chặng |
| **Độ trễ phân vị 99 (P99 Latency)** | **1844.30 ms** | Độ trễ đỉnh điểm khi kích hoạt toàn bộ chuỗi ReAct và tra cứu ngoài |

---

## 2. PHÂN TÍCH TIÊU THỤ TOKEN & CHI PHÍ TÀI CHÍNH THỰC TẾ (COST ANALYSIS)

### 2.1. Thống kê số lượng Token tiêu thụ
- **Tổng Input Tokens (80 câu)**: `10,439` tokens (Trung bình: `130.5` tokens/câu).
- **Tổng Output Tokens (80 câu)**: `9,914` tokens (Trung bình: `123.9` tokens/câu).
- **Tổng cộng Tokens**: `20,353` tokens.

### 2.2. So sánh chi phí giữa các nhà cung cấp mô hình (Tỷ giá: 1 USD = 25,500 VNĐ)

| Mô hình LLM | Chi phí 80 câu (USD) | Chi phí 80 câu (VNĐ) | Chi phí / 1 Câu hỏi (VNĐ) | Chi phí 100,000 câu (VNĐ) |
| :--- | :---: | :---: | :---: | :---: |
| **Gemini 1.5 Flash** (Google) | **$0.0038** | **96 VNĐ** | **1.2 VNĐ** | **120,000 VNĐ** (~$4.70) |
| **GPT-4o-mini** (OpenAI) | **$0.0075** | **192 VNĐ** | **2.4 VNĐ** | **240,000 VNĐ** (~$9.39) |

> **Khuyến nghị triển khai Production**:
> - **Gemini 1.5 Flash** là giải pháp tối ưu chi phí vượt trội nhất: Với mức phí chỉ **~1.2 VNĐ / truy vấn**, tổ chức có thể phục vụ 100,000 lượt tra cứu pháp luật cho người lao động chỉ với ngân sách **~120,000 VNĐ**.

---

## 3. ĐÁNH GIÁ CHẤT LƯỢNG VĂN PHONG PHÁP LÝ & TÍNH TRUNG THỰC

| Tiêu chí chất lượng | Điểm số đạt được | Tiêu chuẩn đánh giá |
| :--- | :---: | :--- |
| **Tính trung thực (Faithfulness)** | **88.0%** | Không bịa đặt điều luật, bảo đảm mọi mệnh đề đều có chứng cứ |
| **Độ bao phủ điều luật vàng (Recall)** | **100.0%** | Trích dẫn đúng và đủ các điều luật cốt lõi trong đáp án chuẩn |
| **Điểm văn phong pháp lý (Legal Style)** | **100.0 / 100** | Ngôn từ chuẩn mực, viện dẫn trang trọng, lập luận logic |

---

## 4. KẾT LUẬN & ĐÓNG GÓP HỌC THUẬT
1. Thí nghiệm xác nhận việc chuyển đổi từ Mock Generator sang Online Serving (Gemini 1.5 Flash / GPT-4o-mini) duy trì 100% tính ổn định của hệ thống với độ trễ phản hồi trung bình **~1.46 giây**.
2. Chi phí vận hành thực tế ở mức **siêu tiết kiệm (~1.2 VNĐ/câu)**, hoàn toàn khả thi để triển khai ứng dụng thực tế vào các cổng tư vấn pháp luật cộng đồng hoặc nội bộ doanh nghiệp.
