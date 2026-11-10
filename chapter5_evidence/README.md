# THƯ MỤC BẰNG CHỨNG THỰC NGHIỆM PHỤC VỤ BIÊN SOẠN CHƯƠNG 5 (CHAPTER 5 EVIDENCE)

Thư mục này lưu trữ các gói bằng chứng thực nghiệm (evidence bundles) đã được niêm phong, kiểm kê và kiểm tra toàn vẹn bằng mã băm SHA-256 nhằm phục vụ việc biên soạn, đối chiếu số liệu và viết báo cáo cho **Chương 5: Thực nghiệm và Đánh giá kết quả** của luận văn.

---

## 📌 1. CÁC GÓI BẰNG CHỨNG THỰC NGHIỆM

### 🌟 [Gói 1] Gói Thực Nghiệm Chính Thức (Official Production Bundle)
- **Đường dẫn thư mục:** [`chapter5_evidence/20261110_benchmark300/`](./20261110_benchmark300/)
- **Bộ dữ liệu:** Benchmark 300 câu hỏi (`evaluation/dataset/benchmark_300.json`)
- **Mô hình nhúng thực tế:** `bkai-foundation-models/vietnamese-bi-encoder` (768 chiều, Cosine distance)
- **Kho véc-tơ:** `legal_labor_vietnamese_bi_encoder` (2.117 véc-tơ, 19 văn bản pháp luật, khớp 100% Corpus v2.1)
- **Tổng số lượt chạy:** 900 lượt thực thi (300 câu hỏi × 3 hệ thống: Traditional RAG, CRAG tích hợp, Adaptive Agentic RAG)
- **Các tài liệu cốt lõi:**
  - `tables/paired_comparison.csv`: Bảng đối chiếu ghép cặp 300 câu hỏi hàng-theo-hàng với đầy đủ điểm số, nhãn bám ngữ cảnh (faithfulness), thời gian thực thi (ms), tuyến định tuyến Adaptive và hành động CRAG.
  - `tables/table_5_6_score_distribution.csv`: Tái hiện và kiểm chứng 100% số liệu trong **Bảng 5.6** (Phân bố điểm $1.0$, $0.5$, $0.0$, $C^+(A)\%$, $\bar{S}(A)$, $\bar{S}(B)$).
  - `tables/table_5_11_faithfulness.csv`: Tái hiện và kiểm chứng 100% số liệu trong **Bảng 5.11** (Nhãn bám ngữ cảnh trên 250 câu có thể trả lời: Traditional 99,60%, CRAG 81,20%, Adaptive 80,00%).
  - `tables/branch_latency.csv`: Bảng phân rã độ trễ chi tiết theo từng nhánh định tuyến (`DIRECT_REFUSAL`: 0,47 ms, `CORRECTIVE_RAG`: 94,84 ms, `DECOMPOSE_AGENTIC`: 130,33 ms, `TRADITIONAL_RAG`: 165,84 ms).
  - `cases.json`: Toàn văn 300 trường hợp kiểm nghiệm kèm phân tích học thuật chuyên sâu cho các ca điển hình.
  - `findings.md`: Báo cáo khoa học phân tích nguyên nhân và hiện tượng thực nghiệm.
  - `chapter5_evidence_bundle.zip`: Gói nén toàn bộ bằng chứng (1,17 MB) để tải về và nhập liệu vào các công cụ phân tích bên ngoài.

---

### 📦 [Gói 2] Gói Thực Nghiệm Lịch Sử (Legacy Baseline Bundle)
- **Đường dẫn thư mục:** [`chapter5_evidence/20261105_142500/`](./20261105_142500/)
- **Bộ dữ liệu:** 80 câu hỏi (`evaluation/dataset/legal_qa.json`)
- **Mô hình nhúng:** `sentence-transformers/all-MiniLM-L6-v2` (384 chiều)
- **Kho véc-tơ:** `legal_labor_baseline_minilm` (1.390 véc-tơ / 15 văn bản gốc)
- **Mục đích:** Lưu trữ đối chứng lịch sử để phân tích bước nhảy hiệu năng khi chuyển đổi sang mô hình nhúng tiếng Việt chuyên biệt.

---

## 🔎 2. HƯỚNG DẪN TRÍCH XUẤT CHO PERPLEXITY / THẨM ĐỊNH VIÊN

Khi sử dụng công cụ AI (như Perplexity AI) để viết hoặc soát xét Chương 5, hãy trỏ công cụ vào thư mục [`chapter5_evidence/20261110_benchmark300/`](./20261110_benchmark300/):
1. **Để kiểm tra từng câu hỏi cụ thể:** Đọc tệp `tables/paired_comparison.csv` (300 dòng) hoặc `cases.json`.
2. **Để kiểm tra bảng chất lượng tổng thể (Bảng 5.6):** Đọc `tables/table_5_6_score_distribution.csv` hoặc Mục 1 trong `findings.md`.
3. **Để kiểm tra bảng nhãn bám ngữ cảnh (Bảng 5.11):** Đọc `tables/table_5_11_faithfulness.csv` hoặc Mục 2 trong `findings.md`.
4. **Để kiểm tra độ trễ theo từng nhánh định tuyến:** Đọc `tables/branch_latency.csv` hoặc Mục 3 trong `findings.md`.
5. **Để kiểm tra tính toàn vẹn:** Chạy `python chapter5_evidence/20261110_benchmark300/analysis/verify_bundle.py`.
