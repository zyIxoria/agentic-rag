# GÓI BẰNG CHỨNG THỰC NGHIỆM CHƯƠNG 5 (CHAPTER 5 EVIDENCE BUNDLE)

> **Đề tài:** Nghiên cứu cơ chế điều phối thích ứng trong hệ thống Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam  
> **Thời điểm kiểm kê:** 2026-11-05T14:31:13.970522+07:00  
> **Git Commit:** `7edd2a8c004c42e094603f6e93a708425748ab2f` (Branch: `main`)  
> **Môi trường:** Python 3.13.0, Windows 11 Pro 64-bit, CPU Execution  

---

## 1. PHẠM VI VÀ MỤC ĐÍCH
Gói bằng chứng này được thiết kế và xuất tự động bằng chương trình (`export_chapter5_evidence.py`), cung cấp toàn bộ dữ liệu có thể kiểm tra độc lập để biên soạn **Chương 5 – Thực nghiệm và đánh giá** trong luận văn tốt nghiệp.

### Các nguyên tắc tuân thủ nghiêm ngặt:
- **100% Số liệu đếm trực tiếp:** Không dùng số liệu giả định; mọi số lượng văn bản, chunks, véc-tơ, câu hỏi đều đếm từ tệp nguồn.
- **Tính bất biến của dữ liệu gốc:** Không sửa câu hỏi, đáp án mẫu, gold sources, hoặc hạ ngưỡng để làm đẹp số liệu.
- **Không ghi đè:** Gói bằng chứng nằm hoàn toàn trong thư mục độc lập `chapter5_evidence/20261105_142500/`.

---

## 2. CẤU TRÚC GÓI BẰNG CHỨNG

```text
chapter5_evidence/20261105_142500/
├── README.md                      # Hướng dẫn và phạm vi gói bằng chứng
├── manifest.json                  # Metadata hệ thống, môi trường, git và mã băm
├── checksums.sha256               # Bảng mã băm SHA-256 toàn bộ các tệp trong gói
├── artifact_inventory.csv         # Danh mục toàn bộ artifact liên quan và tình trạng xác minh
├── corpus_summary.json            # Tổng quan chi tiết về corpus văn bản V2.1
├── corpus_documents.csv           # Bảng danh mục 19 văn bản pháp luật và số chunks
├── vector_store_audit.json        # Báo cáo kiểm định kho véc-tơ ChromaDB (1.390 véc-tơ)
├── benchmark_full.json            # Bản sao nguyên vẹn 80 câu hỏi kiểm định (legal_qa.json)
├── benchmark_groups.csv           # Phân bố 7 nhóm câu hỏi trong benchmark
├── benchmark_validation.csv       # Kết quả kiểm chứng chi tiết từng câu trong benchmark
├── run_comparability.csv          # Ma trận đối chiếu tính tương thích giữa các hệ thống
├── metric_specification.md        # Đặc tả công thức toán học và phương pháp tính metric
├── cases.json                     # Phân tích sâu 7 ca thực nghiệm điển hình
├── findings.md                    # Đúc kết các phát hiện khoa học cho Chương 5
├── unresolved_items.csv           # Danh mục vấn đề còn tồn đọng và ảnh hưởng
├── results/                       # Kết quả chi tiết từng câu của từng hệ thống
│   ├── traditional_rag_results.json
│   ├── crag_integrated_results.json
│   ├── adaptive_agentic_results.json
│   ├── corrective_internal_results.json
│   └── online_llm_results.json
├── tables/                        # Các bảng số liệu phục vụ đưa vào bài viết
│   ├── overall_metrics.csv        # Bảng so sánh tổng thể các metric cốt lõi
│   ├── category_metrics.csv       # Phân rã metric theo 7 nhóm câu hỏi
│   ├── routing_distribution.csv   # Phân bố quyết định định tuyến của Adaptive RAG
│   ├── routing_by_category.csv    # Ma trận định tuyến theo từng nhóm câu hỏi
│   ├── correction_metrics.csv     # Đánh giá hiệu quả cơ chế hiệu chỉnh (CRAG)
│   ├── latency_metrics.csv        # Thống kê độ trễ chi tiết (Mean, Median, P95)
│   ├── execution_errors.csv       # Báo cáo lỗi thực thi (0 lỗi / 100% thành công)
│   └── paired_comparison.csv      # Bảng so sánh ghép cặp từng câu giữa 3 hệ thống
└── analysis/                      # Mã nguồn script kiểm kê và xuất dữ liệu
    └── export_chapter5_evidence.py
```

---

## 3. CÁCH SỬ DỤNG GÓI BẰNG CHỨNG
1. **Đối chiếu số liệu bảng tổng hợp:** Đọc `tables/overall_metrics.csv` và `tables/category_metrics.csv`.
2. **Kiểm tra độ trễ:** Xem `tables/latency_metrics.csv` để lấy Mean, Median, P95 của các hệ thống.
3. **Phân tích cơ chế điều phối:** Đọc `tables/routing_distribution.csv` và `tables/routing_by_category.csv`.
4. **Trích dẫn ca điển hình:** Lấy nội dung chi tiết từ `cases.json` cho các mục Single Article, Multi-Document, Insufficient Evidence và Out-of-Scope.
5. **Kiểm tra tính toàn vẹn:** Sử dụng tệp `checksums.sha256` để kiểm tra mã băm của từng tệp tin trong gói.
