# SỔ TAY HƯỚNG DẪN CHẠY THỰC NGHIỆM HỆ THỐNG
## TRADITIONAL RAG BASELINE • CORRECTIVE RAG (CRAG) • ADAPTIVE AGENTIC RAG

> **Đề tài**: Nghiên cứu cơ chế điều phối thích ứng trong hệ thống Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam.  
> **Tài liệu phục vụ**: Thử nghiệm thực tế, chạy benchmark tái lập số liệu khóa luận và kiểm thử tự động.

---

## MỤC LỤC
1. [Chuẩn bị môi trường & Cài đặt thư viện](#1-chuẩn-bị-môi-trường--cài-đặt-thư-viện)
2. [Cách 1: Chạy tương tác qua giao diện dòng lệnh (CLI)](#2-cách-1-chạy-tương-tác-qua-giao-diện-dòng-lệnh-cli)
   - [A. Traditional RAG Baseline (`run_rag_baseline.py`)](#a-chạy-traditional-rag-baseline)
   - [B. Corrective RAG (`run_crag.py`)](#b-chạy-corrective-rag-crag)
   - [C. Adaptive Agentic RAG (`run_adaptive.py`)](#c-chạy-adaptive-agentic-rag)
3. [Cách 2: Gọi trực tiếp trong mã nguồn Python (Python API)](#3-cách-2-gọi-trực-tiếp-trong-mã-nguồn-python-python-api)
4. [Cách 3: Chạy Benchmark đối chuẩn 80 câu hỏi (`evaluation/runner/`)](#4-cách-3-chạy-benchmark-đối-chuẩn-80-câu-hỏi)
5. [Cách 4: Chạy bộ kiểm thử tự động (Unit & Integration Tests)](#5-cách-4-chạy-bộ-kiểm-thử-tự-động-unit--integration-tests)
6. [Phân tích Case Study đối đầu thực tế giữa 3 mô hình](#6-phân-tích-case-study-đối-đầu-thực-tế-giữa-3-mô-hình)
7. [Bảng chỉ mục báo cáo và kết quả thực nghiệm](#7-bảng-chỉ-mục-báo-cáo-và-kết-quả-thực-nghiệm)

---

## 1. CHUẨN BỊ MÔI TRƯỜNG & CÀI ĐẶT THƯ VIỆN

Hệ thống hoạt động trên Python >= 3.10 (khuyến nghị **Python 3.13**).

### Cách A: Cài đặt trực tiếp từ `requirements.txt`
```powershell
pip install -r requirements.txt
```

### Cách B: Tạo môi trường ảo riêng biệt (`.venv`)
```powershell
# 1. Khởi tạo môi trường ảo
python -m venv .venv

# 2. Kích hoạt môi trường ảo (Windows PowerShell)
.venv\Scripts\Activate.ps1

# 3. Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

> **Lưu ý ngoại tuyến (Offline Mode)**: Mặc định toàn bộ 3 mô hình đều chạy **offline 100%** bằng mô hình nhúng ONNX cục bộ (`all-MiniLM-L6-v2`) và generator mô phỏng chuẩn xác (`mock`), không cần API key và không tốn phí.

---

## 2. CÁCH 1: CHẠY TƯƠNG TÁC QUA GIAO DIỆN DÒNG LỆNH (CLI)

Hệ thống cung cấp sẵn 3 công cụ dòng lệnh độc lập tương ứng với 3 mô hình:

### A. Chạy Traditional RAG Baseline:
File thực thi: [`run_rag_baseline.py`](file:///d:/Filehoc/KLCN/agentic-rag/run_rag_baseline.py)

* **Chế độ chat tương tác liên tục**:
  ```powershell
  python run_rag_baseline.py
  # Gõ câu hỏi tiếng Việt và nhấn Enter. Gõ 'exit', 'quit' hoặc 'q' để thoát.
  ```
* **Chế độ hỏi 1 câu trực tiếp (Single Query)**:
  ```powershell
  python run_rag_baseline.py --query "Thời giờ làm việc bình thường của người lao động là bao nhiêu?"
  ```
* **Tùy chỉnh tham số nâng cao**:
  ```powershell
  # Thay đổi Top-K và ngưỡng lọc tương đồng
  python run_rag_baseline.py --query "Quy định về thử việc" --top-k 10 --threshold 0.50
  ```

---

### B. Chạy Corrective RAG (CRAG):
File thực thi: [`run_crag.py`](file:///d:/Filehoc/KLCN/agentic-rag/run_crag.py)

Tự động kích hoạt bộ đánh giá chứng cứ (`RetrievalEvaluator`), cơ chế viết lại câu hỏi (`QueryRewriter`) và truy xuất vòng 2 khi cần:

* **Chế độ chat tương tác liên tục**:
  ```powershell
  python run_crag.py
  ```
* **Chế độ hỏi 1 câu trực tiếp (hiển thị chi tiết CRAG Trace)**:
  ```powershell
  python run_crag.py --query "Người lao động làm việc 5 năm thì được bao nhiêu ngày phép năm?"
  ```
* **Tùy chỉnh tham số**:
  ```powershell
  # Đổi ngưỡng tin cậy đánh giá chứng cứ (mặc định 0.6)
  python run_crag.py --query "Hành vi bị cấm khi xử lý kỷ luật?" --confidence-threshold 0.65 --top-k 5
  ```

---

### C. Chạy Adaptive Agentic RAG:
File thực thi: [`run_adaptive.py`](file:///d:/Filehoc/KLCN/agentic-rag/run_adaptive.py)

Tự động phân loại độ phức tạp câu hỏi (7 Intent), điều phối động 5 nhánh và bẻ nhỏ câu hỏi đa chặng (Sub-queries Decomposition):

* **Chế độ chat tương tác liên tục**:
  ```powershell
  python run_adaptive.py
  ```
* **Chế độ hỏi 1 câu trực tiếp**:
  ```powershell
  # 1. Câu hỏi đa văn bản phức tạp (Kích hoạt DECOMPOSE_AGENTIC)
  python run_adaptive.py --query "So sánh quy định về thời giờ làm việc và làm thêm giờ giữa Bộ luật Lao động 2019 và Nghị định 145/2020?"

  # 2. Câu hỏi ngoài phạm vi (Kích hoạt DIRECT_REFUSAL tức thì trong 0.3ms)
  python run_adaptive.py --query "Thủ tục xin cấp bằng lái xe máy thế nào?"

  # 3. Câu hỏi chào hỏi/xã giao (Kích hoạt DIRECT_ANSWER tức thì trong 0.1ms)
  python run_adaptive.py --query "Xin chào bạn, chúc bạn một ngày tốt lành!"
  ```

---

## 3. CÁCH 2: GỌI TRỰC TIẾP TRONG MÃ NGUỒN PYTHON (PYTHON API)

### A. Gọi Traditional RAG Pipeline:
```python
from RAG.pipeline import TraditionalRAGPipeline
from RAG.pipeline.config import PipelineConfig

config = PipelineConfig(TOP_K=5, SIMILARITY_THRESHOLD=0.45, LLM_PROVIDER="mock")
pipeline = TraditionalRAGPipeline(config=config)

res = pipeline.answer("Thời gian nghỉ giữa ca làm việc ban đêm là bao lâu?")
print("Câu trả lời:", res.answer)
print("Số chunks truy xuất:", len(res.retrieved_chunks))
print("Độ trễ:", res.latency, "ms")
```

### B. Gọi Corrective RAG (CRAG) Pipeline:
```python
from RAG.corrective import CorrectiveRAGPipeline
from RAG.corrective.config import CRAGConfig
from RAG.pipeline.config import PipelineConfig

crag_config = CRAGConfig(
    pipeline=PipelineConfig(TOP_K=5, LLM_PROVIDER="mock"),
    EVAL_CONFIDENCE_THRESHOLD=0.6,
    MAX_CORRECTIVE_RETRIES=1,
)
crag_pipeline = CorrectiveRAGPipeline(config=crag_config)

res = crag_pipeline.answer("Thời gian thử việc tối đa của trình độ đại học?")
print("Câu trả lời:", res.answer)
print("Có kích hoạt hiệu chỉnh không:", res.corrective_triggered)
if res.corrective_triggered:
    print("Câu hỏi đã viết lại:", res.rewritten_query)
```

### C. Gọi Adaptive Agentic RAG Pipeline:
```python
from RAG.pipeline.config import PipelineConfig
from Adaptive_RAG.config import AdaptiveRAGConfig
from Adaptive_RAG.pipeline.adaptive_pipeline import AdaptiveRAGPipeline

pipeline = AdaptiveRAGPipeline(
    config=AdaptiveRAGConfig(ENABLE_DIRECT_ROUTING=True),
    pipeline_config=PipelineConfig(LLM_PROVIDER="mock")
)

res = pipeline.answer("So sánh quy định về thời giờ làm việc giữa Bộ luật Lao động 2019 và Nghị định 145/2020?")
print("Nhánh định tuyến:", res.route_taken.value)
print("Ý định câu hỏi:", res.classification.intent.value)
print("Kế hoạch phân rã:", len(res.trace.sub_executions), "sub-queries")
print("Câu trả lời:", res.answer)
```

---

## 4. CÁCH 3: CHẠY BENCHMARK ĐỐI CHUẨN 80 CÂU HỎI

Tất cả các thực nghiệm định lượng chính thức trong đồ án đều chạy trên tập 80 câu hỏi pháp lý: [`evaluation/dataset/legal_qa.json`](file:///d:/Filehoc/KLCN/agentic-rag/evaluation/dataset/legal_qa.json).

```powershell
# 1. Đánh giá tầng Dense Retrieval Baseline (Recall@K, Hit Rate, MRR)
python evaluation/evaluate_retrieval.py
# -> Kết quả: evaluation/results/retrieval_baseline.json

# 2. Đánh giá End-to-End Traditional RAG Baseline (RAG-10)
python evaluation/runner/baseline_runner.py
# -> Kết quả: evaluation/results/traditional_baseline_full_eval.json

# 3. Đánh giá End-to-End Corrective RAG (RAG-14)
python evaluation/runner/corrective_runner.py
# -> Kết quả: evaluation/results/corrective_full_eval.json

# 4. Đánh giá Bộ Phân loại độ phức tạp (Classifier)
python evaluation/runner/evaluate_classifier.py
# -> Kết quả: evaluation/results/query_complexity_evaluation.json

# 5. Đánh giá Bộ Phân rã câu hỏi (Decomposer)
python evaluation/runner/evaluate_decomposer.py
# -> Kết quả: evaluation/results/query_decomposition_evaluation.json

# 6. Đánh giá End-to-End Toàn diện Adaptive Agentic RAG (RAG-18)
python evaluation/runner/adaptive_runner.py
# -> Kết quả: evaluation/results/adaptive_evaluation.json
```

---

## 5. CÁCH 4: CHẠY BỘ KIỂM THỬ TỰ ĐỘNG (UNIT & INTEGRATION TESTS)

Dự án duy trì hệ thống kiểm thử toàn diện gồm **391 bài test** tự động với cơ chế chống hồi quy (Zero Regression):

```powershell
# 1. Chạy TOÀN BỘ 391 bài test của toàn dự án:
pytest tests/ -v

# 2. Chạy 97 bài test của Traditional RAG Baseline:
pytest tests/rag tests/retriever tests/context tests/generator tests/citation tests/guards tests/embedding tests/vector_store tests/evaluation evaluation/tests -v

# 3. Chạy 66 bài test của Corrective RAG (CRAG):
pytest tests/crag tests/test_corrective_evaluator.py tests/test_corrective_loop.py tests/test_corrective_pipeline.py tests/test_query_rewriter.py -v

# 4. Chạy 91 bài test của Adaptive Agentic RAG:
pytest tests/adaptive tests/test_query_complexity_classifier.py tests/test_query_decomposer.py -v
```

---

## 6. PHÂN TÍCH CASE STUDY ĐỐI ĐẦU THỰC TẾ GIỮA 3 MÔ HÌNH

Ví dụ thực nghiệm đối đầu trên câu hỏi đa văn bản phức tạp:  
> *"So sánh quy định về thời giờ làm việc và làm thêm giờ giữa Bộ luật Lao động 2019 và Nghị định 145/2020?"*

| Tiêu chí | Traditional RAG Baseline | Corrective RAG (CRAG) | Adaptive Agentic RAG |
| :--- | :---: | :---: | :---: |
| **Command** | `python run_rag_baseline.py` | `python run_crag.py` | `python run_adaptive.py` |
| **Cơ chế xử lý** | Nhồi 1 câu dài vào ChromaDB | Đánh giá nhầm là đủ (`SUFFICIENT` 0.96) | **Phân loại `LEGAL_MULTI_DOC` ➔ Bẻ 2 sub-queries** |
| **Bao phủ văn bản** | ❌ **Mất Nghị định 145/2020** | ❌ **Mất Nghị định 145/2020** | ✅ **Bao phủ đủ cả BLLD 2019 & NĐ 145/2020** |
| **Số chunks truy xuất** | 5 chunks | 3 chunks | **6 chunks (3 BLLD + 3 NĐ 145)** |
| **Độ trễ toàn chuỗi** | **167.89 ms** (Nhanh nhất) | 185.20 ms | 286.27 ms (+118 ms để phân rã và tổng hợp) |
| **Đánh giá khoa học** | *Nhanh nhưng thiếu tài liệu* | *Trôi ngữ cảnh đa văn bản* | ⭐ **Đầy đủ, chính xác và trung thực nhất** |

---

## 7. BẢNG CHỈ MỤC BÁO CÁO VÀ KẾT QUẢ THỰC NGHIỆM

* **Báo cáo thực nghiệm tổng hợp mới nhất**: [`reports/experiment_latest/LATEST-EXPERIMENT-REPORT.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/experiment_latest/LATEST-EXPERIMENT-REPORT.md)
* **Văn bản đóng băng Traditional RAG Baseline**: [`reports/rag/TRADITIONAL-RAG-BASELINE-FROZEN.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/rag/TRADITIONAL-RAG-BASELINE-FROZEN.md)
* **Báo cáo nghiệm thu Corrective RAG (CRAG)**: [`reports/crag/RAG-14-CRAG-EVALUATION.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/crag/RAG-14-CRAG-EVALUATION.md)
* **Báo cáo nghiệm thu Adaptive Agentic RAG**: [`reports/adaptive/RAG-18-ADAPTIVE-EVALUATION.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/adaptive/RAG-18-ADAPTIVE-EVALUATION.md)
* **Báo cáo đối sánh khoa học Baseline vs CRAG**: [`reports/rag/CRAG-07-COMPARISON.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/rag/CRAG-07-COMPARISON.md)
