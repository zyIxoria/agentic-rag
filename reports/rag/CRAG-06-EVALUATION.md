# BÁO CÁO THỰC NGHIỆM ĐÁNH GIÁ ĐỘC LẬP CORRECTIVE RAG (CRAG-06)

## 1. PHẠM VI & ĐIỀU KIỆN THỰC NGHIỆM
- **Tập dữ liệu câu hỏi kiểm định**: Benchmark chuẩn RAG-08 (`evaluation/dataset/legal_qa.json`) gồm 80 câu hỏi phân bố trên 7 categories (A: 18, B: 12, C: 12, D: 10, E: 12, F: 8, G: 8).
- **Corpus pháp luật**: Dataset V2.1 gồm 15 văn bản quy phạm pháp luật, 1,390 chunks đã được lập chỉ mục véc-tơ bền vững tại `data/chroma_db` (collection `legal_labor_baseline_minilm`).
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` ONNX Runtime, 384 dimensions, L2 normalization.
- **Generator**: Local Deterministic Legal Generator (`LLM_PROVIDER="mock"`, `TEMPERATURE=0.0`).
- **Runner**: `evaluation/runner/corrective_runner.py`.
- **Dữ liệu xuất xưởng**: `evaluation/results/corrective_retrieval.json` và `evaluation/results/corrective_full_eval.json`.

---

## 2. KẾT QUẢ THỰC NGHIỆM TỔNG THỂ CỦA CORRECTIVE RAG

### A. Chỉ số Truy xuất (Retrieval Metrics - Trên 64 câu hỏi Answerable):
- **Recall@5 (Chunk-level)**: 14.17% (0.1417)
- **Hit Rate@5**: 29.69% (0.2969)
- **MRR (Chunk-level)**: 0.2005
- **Precision@5**: 6.25% (0.0625)

### B. Chỉ số Trả lời (Answer Metrics - Trên 64 câu hỏi Answerable):
- **Overall Answer Correctness**: 50.00% (0.5000)
- **Strict Answer Correctness**: 21.88% (0.2188)
- **Faithfulness Rate**: 100.00% (1.0000)
- **Unsupported Claim Rate**: 0.00% (0.0000)

### C. Chỉ số Trích dẫn (Citation Metrics):
- **Citation Accuracy**: 35.94% (0.3594)
- **Citation Coverage**: 87.50% (0.8750)
- **Citation Precision**: 15.34% (0.1534)
- **Invalid Citation Rate**: 5.57% (0.0557)

### D. Chỉ số An toàn & Từ chối (Safety / Refusal Metrics):
- **Refusal Accuracy**: **93.75%** (15/16 câu hỏi từ chối thành công)
- **False Answer Rate**: **6.25%** (Chỉ duy nhất 1 câu hỏi trả lời nhầm khi cần từ chối)
- **False Refusal Rate**: 12.50% (8/64 câu hỏi bị từ chối do thẩm định bảo thủ)

### E. Chỉ số Đặc thù của Corrective RAG (CRAG Specific Metrics):
- **Corrective Trigger Rate**: 43.75% (35/80 câu hỏi kích hoạt vòng lặp hiệu chỉnh truy xuất)
- **Total Retries**: 35 lần thử lại
- **Average Retry Count**: 0.4375 lần/câu hỏi
- **Correction Success Rate**: 2.86% (1/35 ca hiệu chỉnh cải thiện được điểm thu hồi)
- **Recovery Rate**: 2.86% (1/35 ca tìm thấy gold chunk bị bỏ sót ở lần 1)
- **Unnecessary Correction Rate**: 0.00% (0% trường hợp ban đầu đã đạt 100% gold chunk mà bị viết lại thừa)

### F. Chỉ số Thời gian Thực thi (Latency Metrics):
- **Mean Latency (E2E)**: 174.86 ms
- **Median Latency**: 133.11 ms
- **P95 Latency**: 259.25 ms
- **Latency khi không kích hoạt Corrective (45 câu)**: Mean = 124.69 ms, Median = 123.25 ms, P95 = 134.74 ms
- **Latency khi kích hoạt Corrective (35 câu)**: Mean = 239.37 ms, Median = 234.44 ms, P95 = 267.65 ms
- **Thời gian phân bổ thành phần**:
  - Retrieval Latency: Mean = 174.05 ms (bao gồm cả lần 1 và lần 2 nếu có)
  - Evaluator Latency: Mean = 0.21 ms
  - Rewriter Latency: Mean = 0.07 ms
  - Generation Latency: Mean = 0.21 ms
