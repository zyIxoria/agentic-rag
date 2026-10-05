# BÁO CÁO ĐỐI CHIẾU THỰC NGHIỆM: TRADITIONAL RAG VS CORRECTIVE RAG (CRAG-07)

## 1. TỔNG QUAN ĐỐI CHIẾU HỆ THỐNG
Báo cáo này đối chiếu định lượng trực tiếp giữa **Traditional-RAG-v1** (Baseline tuyến tính đã đóng băng) và **Corrective-RAG-v1** (Hệ thống tích hợp Thẩm định tài liệu và Hiệu chỉnh truy xuất) trên cùng tập dữ liệu kiểm định chuẩn gồm **80 câu hỏi pháp luật lao động Việt Nam** (RAG-08).

Hai hệ thống chia sẻ 100% cùng điều kiện môi trường:
- Cùng cơ sở dữ liệu véc-tơ bền vững: ChromaDB, collection `legal_labor_baseline_minilm` (1,390 chunks).
- Cùng mô hình Embedding: `sentence-transformers/all-MiniLM-L6-v2` ONNX (384 dimensions, Cosine distance).
- Cùng tham số Top-K = 5.
- Cùng bộ công cụ đánh giá chuẩn tắc `LegalAnswerEvaluator`.

---

## 2. BẢNG TỔNG HỢP CHỈ SỐ ĐỐI CHIẾU ĐỊNH LƯỢNG

| Nhóm Metric | Chỉ số kiểm định | Traditional RAG | Corrective RAG | Chênh lệch ($\Delta$) | Xu hướng đánh giá |
|:---|:---|:---:|:---:|:---:|:---|
| **Truy xuất (Retrieval)** | Recall@5 (Chunk-level) | 14.31% | **14.17%** | -0.14% | Ổn định tương đương |
| | Hit Rate@5 | 29.69% | **29.69%** | 0.00% | Bằng nhau |
| | MRR (Chunk-level) | 0.1932 | **0.2005** | **+0.0073** | Cải thiện nhẹ thứ hạng |
| | Precision@5 | 6.25% | **6.25%** | 0.00% | Bằng nhau |
| **Chất lượng câu trả lời** | Overall Answer Correctness | 50.00% | **50.00%** | 0.00% | Ổn định |
| | Strict Answer Correctness | 26.56% | **21.88%** | -4.68% | Giảm nhẹ do thẩm định khắt khe |
| | Faithfulness Rate | 93.75% | **100.00%** | **+6.25%** | **Tuyệt đối trung thực (100%)** |
| | Unsupported Claim Rate | 6.25% | **0.00%** | **-6.25%** | **Triệt tiêu hoàn toàn ảo giác** |
| **Trích dẫn (Citation)** | Citation Accuracy | 34.38% | **35.94%** | **+1.56%** | Cải thiện độ chính xác nguồn |
| | Citation Coverage | 100.00% | **87.50%** | -12.50% | Giảm do từ chối các ca nghi vấn |
| | Citation Precision | 13.05% | **15.34%** | **+2.29%** | Tập trung hơn vào căn cứ cốt lõi |
| | Invalid Citation Rate | 4.27% | **5.57%** | +1.30% | Tương đương |
| **An toàn & Từ chối (Safety)** | **Refusal Accuracy** | **43.75%** | **93.75%** | **+50.00%** | **ĐỘT PHÁ VƯỢT BẬC (+50%)** |
| | **False Answer Rate** | **56.25%** | **6.25%** | **-50.00%** | **Giảm 9 lần rủi ro trả lời bừa** |
| | False Refusal Rate | 0.00% | **12.50%** | +12.50% | Đánh đổi bảo thủ để lấy an toàn |
| **Hiệu năng (Latency)** | Mean Latency (E2E) | 291.46 ms | **174.86 ms** | **-116.60 ms** | Nhanh hơn 40% (Fail-fast) |
| | Median Latency | 291.11 ms | **133.11 ms** | **-158.00 ms** | Tiết kiệm thời gian xử lý |
| | P95 Latency | 305.46 ms | **259.25 ms** | **-46.21 ms** | Kiểm soát trần độ trễ tốt hơn |
| **Chỉ số CRAG riêng biệt** | Corrective Trigger Rate | N/A | **43.75%** | N/A | 35/80 câu hỏi kích hoạt retry |
| | Correction Success Rate | N/A | **2.86%** | N/A | 1/35 ca cải thiện điểm số |
| | Recovery Rate | N/A | **2.86%** | N/A | 1/35 ca vớt được gold chunk |
| | Unnecessary Correction Rate | N/A | **0.00%** | N/A | 0% trường hợp viết lại thừa |
| | Average Retry Count | 0.0 | **0.4375** | +0.4375 | Tối đa 1 lần retry theo thiết kế |

---

## 3. PHÂN RÃ CHI TIẾT THEO 7 CATEGORY (A - G)

### Bảng đối chiếu Category Breakdown:

| Category | Số câu | Strict Correctness (Trad $\to$ CRAG) | Faithfulness (Trad $\to$ CRAG) | Refusal Accuracy (Trad $\to$ CRAG) | False Answer Rate (Trad $\to$ CRAG) | Mean Latency (ms) (Trad $\to$ CRAG) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **A. Single Article** | 18 | 38.89% $\to$ **38.89%** | 94.44% $\to$ **100.00%** | N/A | N/A | 304.42 $\to$ **175.05** |
| **B. Multi-Chunk** | 12 | 33.33% $\to$ **25.00%** | 91.67% $\to$ **100.00%** | N/A | N/A | 296.54 $\to$ **157.10** |
| **C. Multi-Document** | 12 | 16.67% $\to$ **8.33%** | 100.00% $\to$ **100.00%** | N/A | N/A | 285.37 $\to$ **152.74** |
| **D. Cross-Reference** | 10 | 30.00% $\to$ **30.00%** | 100.00% $\to$ **100.00%** | N/A | N/A | 295.27 $\to$ **156.45** |
| **E. Complex Conditions** | 12 | 8.33% $\to$ **0.00%** | 83.33% $\to$ **100.00%** | N/A | N/A | 286.30 $\to$ **168.85** |
| **F. Insufficient Evidence** | 8 | N/A | N/A | **0.00% $\to$ 87.50%** | **100.00% $\to$ 12.50%** | 280.10 $\to$ **215.02** |
| **G. Out-of-Scope** | 8 | N/A | N/A | **87.50% $\to$ 100.00%** | **12.50% $\to$ 0.00%** | 278.11 $\to$ **226.14** |

---

## 4. PHÂN TÍCH LỖI VÀ BẢN CHẤT CỦA CÁC CA THỰC NGHIỆM (ERROR ANALYSIS)

### 1. Đột phá lớn nhất: Khắc phục triệt để lỗ hổng của Category F (Insufficient Evidence)
- **Traditional RAG**: Đạt **0.00%** Refusal Accuracy ở nhóm F (False Answer Rate = 100%). Khi người dùng hỏi các văn bản pháp luật ngoài cơ sở dữ liệu (Luật BHXH 2014, Luật Công đoàn 2012, Luật An toàn vệ sinh lao động 2015, Luật Việc làm), Dense Retriever vẫn thu hồi các chunk có cosine similarity > 0.45 do chứa từ khóa chung ("lao động", "bảo hiểm", "công đoàn"), dẫn tới việc LLM cố gắng trả lời và sinh ra thông tin sai lệch nghiêm trọng.
- **Corrective RAG**: Đạt **87.50%** Refusal Accuracy (7/8 câu hỏi từ chối thành công, False Answer Rate giảm từ 100% xuống còn 12.50%). Evaluator phát hiện ra văn bản gốc không tồn tại và các chunk thu hồi thiếu các số liệu/căn cứ nghiệp vụ định lượng, từ đó kích hoạt Explicit Refusal dứt khoát.

### 2. Triệt tiêu hoàn toàn hiện tượng Unsupported Claim (Ảo giác pháp lý)
- Nhờ cơ chế lọc bỏ các đoạn distractor (`irrelevant_chunk_ids`) trước khi ghép vào Context Builder, Faithfulness của CRAG đạt **100.00%** trên toàn bộ 64 câu hỏi answerable (so với 93.75% của Baseline).
- Unsupported Claim Rate giảm từ **6.25% về đúng 0.00%**.

### 3. Giới hạn của cơ chế Query Rewriting đơn thuần trên Dense Retrieval cố định
- **Tỷ lệ cải thiện truy xuất (Recovery Rate = 2.86%, Correction Success Rate = 2.86%)**: Khi một câu hỏi thuộc dạng Multi-Document hoặc Complex Conditions (Category C và E) bị thiếu điều khoản ở lần thu hồi đầu, việc chỉ viết lại câu truy vấn (Query Rewriting) mà vẫn thực hiện đơn truy vấn dense retrieval một lượt không thể giải quyết được các câu hỏi đa mục tiêu.
- **Nguyên nhân**: Không gian nhúng của `all-MiniLM-L6-v2` gom toàn bộ câu hỏi vào một véc-tơ 384 chiều. Một véc-tơ đơn lẻ không thể đồng thời kéo các chunk ở 2 văn bản khác nhau (Bộ luật Lao động và Nghị định 145/2020) lên cùng Top-5 nếu hai văn bản này dùng các từ ngữ hoàn toàn khác nhau.
- **Hệ quả**: Strict Correctness ở Category C giảm từ 16.67% xuống 8.33%, Category E giảm từ 8.33% xuống 0.00%, do Evaluator nhận thấy tài liệu thu hồi lần 2 vẫn thiếu một vế và quyết định từ chối (False Refusal Rate = 12.50%) thay vì cố trả lời mạo hiểm như Baseline.

---

## 5. KẾT LUẬN THỰC NGHIỆM ĐỒ ÁN
1. **CRAG có cải thiện Retrieval không?**
   - Không cải thiện đáng kể về mặt độ phủ Recall@5 (+0% Hit Rate, Recall@5 14.17% so với 14.31%), nhưng cải thiện nhẹ thứ hạng liên quan (MRR tăng từ 0.1932 lên 0.2005). Lý do: Mô hình Dense Retriever cố định không thay đổi không gian biểu diễn; việc viết lại câu truy vấn chỉ hỗ trợ làm rõ thuật ngữ nhưng không thể phá vỡ giới hạn biểu diễn của single-query dense search.
2. **CRAG có cải thiện Answer Correctness không?**
   - Overall Correctness giữ nguyên ở mức **50.00%**. Strict Correctness giảm nhẹ từ 26.56% xuống 21.88% do hệ thống ưu tiên tính thận trọng pháp lý cao độ.
3. **CRAG có cải thiện An toàn và Từ chối (Safety & Refusal) không?**
   - **CẢI THIỆN ĐỘT PHÁ**. Refusal Accuracy tăng từ **43.75% lên 93.75%** (+50.00%), False Answer Rate giảm từ **56.25% xuống 6.25%**. Đây là đóng góp khoa học quan trọng nhất của giai đoạn CRAG: bảo vệ người dùng pháp luật trước thông tin sai lệch khi dữ liệu thiếu chứng cứ.
4. **Trích dẫn có tốt hơn không?**
   - Citation Accuracy tăng từ 34.38% lên **35.94%**, Citation Precision tăng từ 13.05% lên **15.34%**.
5. **Độ trễ (Latency) thay đổi thế nào?**
   - Trung bình toàn chu trình E2E nhanh hơn Baseline (**174.86 ms so với 291.46 ms**) do 56.25% số câu không kích hoạt corrective và các câu từ chối được ngắt sớm (Fail-Fast) trước khi phải gọi toàn bộ chu trình sinh và hậu kiểm phức tạp. Với các câu kích hoạt Corrective Retry, độ trễ trung bình là 239.37 ms, hoàn toàn nằm trong ngưỡng thời gian thực cho phép (<300 ms).

---

## 6. HƯỚNG ĐI TIẾP THEO: ADAPTIVE AGENTIC RAG
Kết quả thực nghiệm định lượng trên đây chứng minh rõ ràng: **Corrective RAG đã giải quyết triệt để bài toán An toàn Thẩm định (Safety/Refusal), nhưng thất bại trong việc giải quyết bài toán Đa văn bản (Multi-Document) và Đa điều kiện (Complex Conditions) do giới hạn của kiến trúc đơn truy vấn.**

Giai đoạn tiếp theo — **Adaptive Agentic RAG** — sẽ giải quyết đúng nút thắt còn lại này thông qua:
1. **Query Complexity Classifier**: Phân loại câu hỏi đơn giản vs câu hỏi phức tạp đa văn bản.
2. **Query Decomposition**: Phân rã câu hỏi đa văn bản thành các câu hỏi con độc lập (Sub-queries).
3. **Adaptive Routing**: Điều phối câu hỏi đơn qua Traditional/CRAG nhanh, điều phối câu hỏi phức tạp qua chuỗi phân rã và tổng hợp đa nguồn.
