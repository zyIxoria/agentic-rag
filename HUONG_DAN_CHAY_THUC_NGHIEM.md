# SỔ TAY HƯỚNG DẪN CHẠY THỰC NGHIỆM HỆ THỐNG
*(Áp dụng thống nhất cho cả 3 mô hình: Traditional Baseline, Corrective RAG và Adaptive Agentic RAG)*

> **Đề tài**: Nghiên cứu cơ chế điều phối thích ứng trong hệ thống Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam.  
> **Chế độ chạy**: Offline 100% (sử dụng mô hình ONNX cục bộ `all-MiniLM-L6-v2` và local generator, không cần API key).

---

## 1. CÀI ĐẶT MÔI TRƯỜNG & THƯ VIỆN

Yêu cầu: **Python >= 3.10** (khuyến nghị Python 3.13).

```powershell
# 1. Khởi tạo và kích hoạt môi trường ảo (Windows PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt
```

---

## 2. CHẠY TƯƠNG TÁC QUA DÒNG LỆNH (CLI)

Hệ thống cung cấp sẵn 3 công cụ dòng lệnh độc lập tương ứng với 3 mô hình:

### A. Traditional RAG Baseline (Mô hình cơ sở tuyến tính)
*File thực thi: [`run_rag_baseline.py`](run_rag_baseline.py)*

```powershell
# Chế độ chat tương tác liên tục:
python run_rag_baseline.py

# Tra cứu nhanh 1 câu hỏi:
python run_rag_baseline.py --query "Thời giờ làm việc bình thường của người lao động là bao nhiêu?"

# Tùy chỉnh Top-K và ngưỡng lọc tương đồng:
python run_rag_baseline.py --query "Quy định về thử việc" --top-k 5 --threshold 0.45
```

### B. Corrective RAG — CRAG (Mô hình tự đánh giá & hiệu chỉnh)
*File thực thi: [`run_crag.py`](run_crag.py)*

```powershell
# Chế độ chat tương tác liên tục:
python run_crag.py

# Tra cứu 1 câu hỏi (tự động kích hoạt Grader, Strip & Filter và Query Rewriter):
python run_crag.py --query "Người lao động làm việc 5 năm thì được bao nhiêu ngày phép năm?"
```

### C. Adaptive Agentic RAG (Mô hình điều phối thích ứng)
*File thực thi: [`run_adaptive.py`](run_adaptive.py)*

```powershell
# Chế độ chat tương tác liên tục:
python run_adaptive.py

# Tra cứu câu hỏi phức tạp (tự động phân loại intent, bẻ sub-queries và tổng hợp):
python run_adaptive.py --query "So sánh quy định về thời giờ làm việc và làm thêm giờ giữa Bộ luật Lao động 2019 và Nghị định 145/2020?"
```

---

## 3. TRA CỨU & QUẢN LÝ LỊCH SỬ HỎI ĐÁP (SQLITE DATABASE)

Toàn bộ câu hỏi chạy qua 3 CLI trên đều được tự động lưu vào CSDL SQLite tại `data/history/query_history.db`.  
*File thực thi: [`show_history.py`](show_history.py)*

```powershell
# Xem tổng quan thống kê (tổng câu, tỷ lệ từ chối, độ trễ, tokens, chi phí):
python show_history.py --summary

# Xem 10 câu hỏi hỏi đáp gần nhất:
python show_history.py --list --limit 10

# Tìm kiếm lịch sử theo từ khóa:
python show_history.py --search "thử việc"

# Xem chi tiết một phiên hỏi đáp theo ID:
python show_history.py --view 1

# Xuất dữ liệu lịch sử ra file JSON hoặc CSV:
python show_history.py --export-json history.json
python show_history.py --export-csv history.csv
```

---

## 4. CHẠY BENCHMARK ĐỐI CHUẨN THỰC NGHIỆM (80 CÂU HỎI)

Tái hiện 100% số liệu thực nghiệm trên tập chuẩn [`evaluation/dataset/legal_qa.json`](evaluation/dataset/legal_qa.json):

```powershell
# 1. Đánh giá Dense Retrieval Baseline (Recall@5, Hit Rate, MRR)
python evaluation/evaluate_retrieval.py

# 2. Đánh giá End-to-End Traditional RAG Baseline (RAG-10)
python evaluation/runner/baseline_runner.py

# 3. Đánh giá End-to-End Corrective RAG (RAG-14)
python evaluation/runner/corrective_runner.py

# 4. Đánh giá Bộ phân loại độ phức tạp (Classifier)
python evaluation/runner/evaluate_classifier.py

# 5. Đánh giá Bộ phân rã câu hỏi (Decomposer)
python evaluation/runner/evaluate_decomposer.py

# 6. Đánh giá End-to-End Adaptive Agentic RAG (RAG-18)
python evaluation/runner/adaptive_runner.py

# 7. Đánh giá Thực nghiệm Cải tiến Retrieval V0 -> V4 (Hybrid BM25 + Reranker)
python evaluation/evaluate_improved_retrieval.py

# 8. Tính toán và quy đổi chi phí Token trên các LLM thương mại ($ & VNĐ)
python evaluation/cost_calculator.py --save
```

---

## 5. CHẠY BỘ KIỂM THỬ TỰ ĐỘNG (TEST SUITE)

```powershell
# 1. Chạy TOÀN BỘ bài test tự động của dự án (Zero Regression):
pytest tests/ -v

# 2. Chạy riêng bài test hồi quy cải tiến Retrieval V0-V4 (8 bài test):
pytest tests/test_retrieval_improvement.py -v

# 3. Chạy riêng bài test hệ thống lưu trữ lịch sử SQLite:
pytest tests/test_query_history.py -v
```

---

## 6. GỌI TRỰC TIẾP TRONG MÃ NGUỒN PYTHON (API)

```python
from Adaptive_RAG.orchestration.orchestrator import AdaptiveOrchestrator

# Khởi tạo bộ điều phối Adaptive Agentic RAG
orchestrator = AdaptiveOrchestrator()

# Thực thi truy vấn
response = orchestrator.route_and_execute("Thời gian thử việc tối đa là bao lâu?")

print(f"Nhánh điều phối: {response.route_taken.value}")
print(f"Câu trả lời: {response.answer}")
print(f"Căn cứ điều luật: {[c.article_number for c in response.citations]}")
print(f"Độ trễ: {response.latency_ms} ms")
```
