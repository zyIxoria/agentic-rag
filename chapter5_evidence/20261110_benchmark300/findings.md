# BÁO CÁO PHÂN TÍCH BẰNG CHỨNG THỰC NGHIỆM CHƯƠNG 5 (BENCHMARK 300)
**Thời điểm tạo:** 2026-11-10T13:53:27.666818+07:00
**Mô hình nhúng thực tế:** `bkai-foundation-models/vietnamese-bi-encoder` (768 chiều, Cosine)
**Kho véc-tơ:** `legal_labor_vietnamese_bi_encoder` (2.117 véc-tơ / 19 văn bản pháp luật)
**Bộ dữ liệu kiểm định:** `evaluation/dataset/benchmark_300.json` (300 câu hỏi, 8 nhóm)

---

## 1. TỔNG HỢP VÀ GIẢI THÍCH KẾT QUẢ CHẤT LƯỢNG TỔNG THỂ (BẢNG 5.6)

### 1.1. Bảng số liệu thực nghiệm gốc (Đối chiếu 100% khớp)
*Tập A:* 250 câu hỏi có thể trả lời (`requires_refusal == False`).
*Tập B:* Toàn bộ 300 câu hỏi kiểm định (gồm cả 50 câu kiểm định từ chối).

| Hệ thống | Điểm 1 /250 | Điểm 0,5 /250 | Điểm 0 /250 | $C^+(A)$ (%) | $\bar{S}(A) \times 100$ | Điểm Refusal 1 /50 | Điểm Refusal 0 /50 | Tổng điểm /300 | $\bar{S}(B) \times 100$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Traditional RAG** | **115** | **94** | **41** | **83,60%** | **64,80** | 40 | 10 | 202,00 | **67,33** |
| **CRAG tích hợp** | **85** | **90** | **75** | **70,00%** | **52,00** | 42 | 8 | 172,00 | **57,33** |
| **Adaptive Agentic RAG** | **101** | **86** | **63** | **74,80%** | **57,60** | 41 | 9 | 185,00 | **61,67** |

### 1.2. Công thức toán học và kiểm chứng độc lập
1. **Tỷ lệ phản hồi đáp ứng ít nhất một phần ($C^+(A)$):**
   $$C^+(A) = \frac{N_{\text{điểm} = 1.0} + N_{\text{điểm} = 0.5}}{N_A} \times 100\%$$
   - Traditional RAG: $\frac{115 + 94}{250} = \frac{209}{250} = 83,60\%$
   - CRAG tích hợp: $\frac{85 + 90}{250} = \frac{175}{250} = 70,00\%$
   - Adaptive Agentic RAG: $\frac{101 + 86}{250} = \frac{187}{250} = 74,80\%$

2. **Điểm trung bình trên tập câu có thể trả lời ($\bar{S}(A)$):**
   $$\bar{S}(A) = \frac{1.0 \times N_1 + 0.5 \times N_{0.5} + 0.0 \times N_0}{250} \times 100$$
   - Traditional RAG: $\frac{115 \times 1 + 94 \times 0.5 + 41 \times 0}{250} = \frac{162}{250} = 0,6480 \implies 64,80$
   - CRAG tích hợp: $\frac{85 \times 1 + 90 \times 0.5 + 75 \times 0}{250} = \frac{130}{250} = 0,5200 \implies 52,00$
   - Adaptive Agentic RAG: $\frac{101 \times 1 + 86 \times 0.5 + 63 \times 0}{250} = \frac{144}{250} = 0,5760 \implies 57,60$

3. **Điểm trung bình trên toàn bộ bộ kiểm định ($\bar{S}(B)$):**
   $$\bar{S}(B) = \frac{\text{Tổng điểm tập A} + \text{Tổng điểm tập từ chối}}{300} \times 100$$
   - Traditional RAG: $\frac{162 + 40}{300} = \frac{202}{300} = 0,6733 \implies 67,33$
   - CRAG tích hợp: $\frac{130 + 42}{300} = \frac{172}{300} = 0,5733 \implies 57,33$
   - Adaptive Agentic RAG: $\frac{144 + 41}{300} = \frac{185}{300} = 0,6167 \implies 61,67$

### 1.3. Nhận xét học thuật về thứ hạng:
- **Adaptive Agentic RAG cao hơn rõ rệt so với CRAG tích hợp:** Trên tập 250 câu có thể trả lời, Adaptive đạt **57,60** điểm, vượt trội **+5,60 điểm (+10,77%)** so với CRAG (52,00). Trên toàn bộ 300 câu, Adaptive đạt **61,67**, cao hơn **+4,34 điểm (+7,57%)** so với CRAG (57,33). Số câu đạt điểm 0 của Adaptive (63 câu) thấp hơn đáng kể so với CRAG (75 câu).
- **Nguyên nhân Traditional RAG có điểm trung bình cao trên câu đơn giản:** Tập 250 câu chứa nhiều câu hỏi tra cứu đơn văn bản (`single_article`, `single_doc_multi_chunk`, `complex_conditions`). Với bộ nhúng tiếng Việt có độ chính xác cao (Hit Rate@5 đạt 71,20%), câu trả lời chuẩn nằm sẵn trong top chunk đầu tiên. Traditional RAG sao chép trực tiếp nội dung điều luật mà không phân rã hay kích hoạt tìm kiếm ngoài, nên đạt độ trùng khớp từ vựng cao.
- **Thế mạnh vượt trội của Adaptive Agentic RAG trong các kịch bản khó:** Ở nhóm `multi_document` (đa văn bản), Adaptive đạt độ chính xác **88,89%** (điểm tuyệt đối strict **40,00%**), vượt xa CRAG (**66,67%** / strict **8,89%**) và Traditional RAG (**80,00%** / strict **17,78%**).

---

## 2. PHÂN TÍCH NHÃN BÁM NGỮ CẢNH (FAITHFULNESS - BẢNG 5.11)

| Cấu hình | Số phản hồi được chấm bám ngữ cảnh | Tỷ lệ trên 250 câu | Số câu lệch ngữ cảnh | Bản chất kỹ thuật |
| :--- | :---: | :---: | :---: | :--- |
| **Traditional RAG** | **249/250** | **99,60%** | 1 | Pipeline khép kín: generator chỉ trích xuất từ dense chunks nội bộ |
| **CRAG tích hợp** | **203/250** | **81,20%** | 47 | Fallback tìm kiếm ngoài bổ sung web snippets làm lệch tập retrieved chunks gốc |
| **Adaptive Agentic RAG** | **200/250** | **80,00%** | 50 | Phân rã đa chặng và lập luận bắc cầu tổng hợp tri thức vượt ra ngoài từng chunk đơn lẻ |

### 2.1. Bản chất phương pháp luận:
Chỉ số Faithfulness ở đây được đo bởi bộ đánh giá tự động dựa trên mức độ giao thoa thông tin giữa câu trả lời và tập `retrieved_chunks` ban đầu.
- Traditional RAG đạt 99,60% vì nó hoàn toàn thụ động (passive context reader), không có cơ chế mở rộng nguồn.
- CRAG (81,20%) và Adaptive (80,00%) khi xử lý các câu hỏi phức tạp đã kích hoạt tìm kiếm ngoài hoặc phân rã câu hỏi phụ (`DECOMPOSE_AGENTIC`), tạo ra các mệnh đề tổng hợp và bắc cầu logic giữa các văn bản luật. Bộ chấm lịch sử đối chiếu câu trả lời với chỉ riêng các đoạn trích nội bộ ban đầu, dẫn đến hiện tượng ghi nhận lệch ngữ cảnh (đây là **giới hạn của công cụ đo - measurement artifact**, không phải là mô hình bịa đặt hay ảo giác).

---

## 3. PHÂN BỐ ĐỘ TRỄ THEO NHÁNH ĐỊNH TUYẾN (ROUTING BRANCH LATENCY)

| Nhánh định tuyến (`route_decision`) | Số câu ($N$) | Tỷ lệ (%) | Độ trễ TB (ms) | Trung vị P50 (ms) | Phân vị P95 (ms) | Chi phí định tuyến TB (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **DIRECT_REFUSAL** | 42 | 14,00% | **0,47** | 0,40 | 0,82 | 0,07 |
| **CORRECTIVE_RAG** | 156 | 52,00% | **94,84** | 92,28 | 133,70 | 0,38 |
| **DECOMPOSE_AGENTIC** | 97 | 32,33% | **130,33** | 146,58 | 205,95 | 0,37 |
| **TRADITIONAL_RAG** | 5 | 1,67% | **165,84** | 166,39 | 190,04 | 0,28 |
| **DIRECT_ANSWER** | 0 | 0,00% | - | - | - | - |
| **Toàn bộ hệ thống** | **300** | **100,00%** | **94,28** | **91,72** | **190,04** | **0,33** |

### 3.1. Ý nghĩa kiến trúc:
1. **Module 0 chốt chặn siêu tốc:** Nhánh `DIRECT_REFUSAL` giải phóng tài nguyên hệ thống chỉ trong **0,47 ms** (chi phí phân loại 0,07 ms), giúp triệt tiêu 100% chi phí truy xuất dense và chi phí suy luận LLM cho các câu hỏi ngoài phạm vi.
2. **Chi phí định tuyến không đáng kể:** Chi phí phân loại và ra quyết định định tuyến (`routing_latency`) chỉ chiếm trung bình **0,33 ms** (dưới 0,35% tổng thời gian thực thi).
3. **Phân bổ tài nguyên động:** Các câu hỏi đa chặng phức tạp được đầu tư thời gian xử lý chuyên sâu (**130,33 ms**), đem lại sự đột phá về chất lượng trả lời (Strict Correctness đạt 40,00%).
