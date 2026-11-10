# GÓI BẰNG CHỨNG THỰC NGHIỆM CHƯƠNG 5 (BENCHMARK 300)
## Thẩm định Thực nghiệm Hệ thống Adaptive Agentic RAG Pháp luật Lao động

Gói bằng chứng này chứa đầy đủ 100% dữ liệu gốc, kết quả chạy thực nghiệm từng câu và các bảng thống kê đối chiếu phục vụ trực tiếp cho việc biên soạn, trích dẫn và thẩm định Chương 5 Luận văn tốt nghiệp.

### 1. Cấu hình thực nghiệm chính thức:
- **Mô hình nhúng ngữ nghĩa (Embedding):** `bkai-foundation-models/vietnamese-bi-encoder` (768 chiều, Cosine distance).
- **Kho véc-tơ (ChromaDB):** `data/chroma_db` (Collection: `legal_labor_vietnamese_bi_encoder`, 2.117 véc-tơ, 19 văn bản pháp luật).
- **Bộ dữ liệu kiểm nghiệm (Benchmark):** `evaluation/dataset/benchmark_300.json` (300 câu hỏi, gồm 250 câu hỏi tra cứu nghiệp vụ và 50 câu hỏi kiểm định an toàn từ chối).
- **Ba hệ thống được đối sánh song song:**
  1. `Traditional RAG`: Pipeline tuyến tính cơ sở (Baseline).
  2. `CRAG tích hợp`: Corrective RAG với cơ chế Document Grading và Web Search Fallback.
  3. `Adaptive Agentic RAG`: Mô hình đề xuất với Module 0 Classifier, Dynamic Routing và Multi-Hop Decompose.

### 2. Cấu trúc thư mục bằng chứng:
```
chapter5_evidence/20261110_benchmark300/
├── README.md                          # Tài liệu hướng dẫn này
├── manifest.json                      # Bảng kê khai siêu dữ liệu, môi trường và mã băm
├── checksums.sha256                   # Mã băm toàn vẹn SHA-256 của từng tệp tin
├── findings.md                        # Báo cáo phân tích chuyên sâu các phát hiện khoa học
├── metric_specification.md            # Định nghĩa toán học các chỉ số đánh giá
├── corpus_summary.json                # Thống kê chi tiết 19 văn bản và 2.117 đoạn văn bản
├── corpus_documents.csv               # Bảng tra cứu 19 văn bản pháp luật trong corpus
├── vector_store_audit.json            # Báo cáo kiểm định 100% độ khớp của kho véc-tơ 768d
├── benchmark_full.json                # Toàn văn 300 câu hỏi, đáp án vàng và căn cứ pháp lý
├── benchmark_groups.csv               # Phân bố câu hỏi theo 8 nhóm kiểm thử
├── benchmark_validation.csv           # Bảng kiểm tra tính hợp lệ của từng câu hỏi
├── run_comparability.csv              # Ma trận so sánh tính tương thích của 3 hệ thống
├── cases.json                         # Danh mục chi tiết 300 câu hỏi và phân tích học thuật
├── chapter5_evidence_bundle.zip       # Gói nén toàn bộ bằng chứng
├── results/                           # Kết quả chạy chi tiết từng câu của 3 hệ thống
│   ├── traditional_rag_results.json   # 300 bản ghi chi tiết của Traditional RAG
│   ├── crag_integrated_results.json   # 300 bản ghi chi tiết của CRAG tích hợp
│   └── adaptive_agentic_results.json  # 300 bản ghi chi tiết của Adaptive Agentic RAG
├── tables/                            # Các bảng dữ liệu số xuất khẩu dưới dạng CSV
│   ├── paired_comparison.csv          # BẢNG ĐỐI CHIẾU GHÉP CẶP TỪNG CÂU CHO 300 CÂU
│   ├── table_5_6_score_distribution.csv # Bảng 5.6: Phân bố điểm và các phép tổng hợp chất lượng
│   ├── table_5_11_faithfulness.csv    # Bảng 5.11: Nhãn bám ngữ cảnh trên 250 câu
│   ├── overall_metrics.csv            # Các chỉ số vĩ mô toàn hệ thống
│   ├── category_metrics.csv           # Phân rã chỉ số theo 8 nhóm câu hỏi
│   ├── routing_distribution.csv       # Tỷ lệ định tuyến theo 5 nhánh của Adaptive
│   ├── routing_by_category.csv        # Ma trận phân bố định tuyến theo từng nhóm câu hỏi
│   ├── branch_latency.csv             # Độ trễ trung bình, trung vị và P95 theo từng nhánh
│   ├── correction_metrics.csv         # Thống kê các hành động hiệu chỉnh của CRAG
│   └── execution_errors.csv           # Nhật ký lỗi thực thi (0 lỗi / 900 lượt chạy)
└── analysis/                          # Mã nguồn Python xuất gói và kiểm định
    ├── export_chapter5_evidence_300.py # Script xuất khẩu toàn bộ gói bằng chứng
    └── verify_bundle.py               # Script kiểm tra tính toàn vẹn và quét mã độc/secret
```

### 3. Hướng dẫn đối chiếu và trích dẫn vào Chương 5:
- **Đối chiếu Bảng 5.6:** Mở tệp `tables/table_5_6_score_distribution.csv` hoặc mục 1 trong `findings.md`. Mọi số liệu (115, 94, 41 của Traditional; 85, 90, 75 của CRAG; 101, 86, 63 của Adaptive) đều được xác nhận trực tiếp từ 250 bản ghi trong `results/`.
- **Đối chiếu Bảng 5.11:** Mở tệp `tables/table_5_11_faithfulness.csv` hoặc mục 2 trong `findings.md`. Tỷ lệ bám ngữ cảnh (99,60% của Traditional; 81,20% của CRAG; 80,00% của Adaptive) được trích xuất từ nhãn `faithfulness` từng câu trong `tables/paired_comparison.csv`.
- **Đối chiếu câu hỏi bất kỳ (từ Q001 đến Q300):** Tra cứu theo `question_id` trong `tables/paired_comparison.csv` hoặc `cases.json` để xem đầy đủ câu hỏi, câu trả lời sinh ra, trích dẫn pháp lý, độ trễ từng pha và lý do định tuyến.
