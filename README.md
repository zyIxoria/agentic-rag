# NGHIÊN CỨU CƠ CHẾ ĐIỀU PHỐI THÍCH ỨNG TRONG HỆ THỐNG AGENTIC RAG TÍCH HỢP CORRECTIVE RAG HỖ TRỢ TRA CỨU PHÁP LUẬT LAO ĐỘNG VIỆT NAM

> **Khóa luận tốt nghiệp ngành Công nghệ Thông tin**  
> **Chủ đề**: Retrieval-Augmented Generation (RAG) đa tầng, Tự hiệu chỉnh truy xuất (Corrective RAG), và Phân loại/Phân rã câu hỏi thích ứng (Adaptive Agentic RAG).  
> **Ngôn ngữ & Nền tảng**: Python 3.13 | ChromaDB | ONNX Runtime | sentence-transformers | pytest (391 tests pass)

---

## 📌 BẢNG TỔNG QUAN HỆ THỐNG & TRẠNG THÁI

| Thành phần | Phiên bản | Trạng thái | Kiểm thử (Tests) | Báo cáo nghiệm thu |
| :--- | :---: | :---: | :---: | :--- |
| **Dataset Pháp lý** | V2.1 (15 VBQPPL, 1,390 chunks) | **FROZEN** | 7/7 PASS | [`DATA-V2-AUDIT.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/dataset_audit/DATA-V2-AUDIT.md) |
| **Traditional RAG Baseline** | `Traditional-RAG-v1` | **FROZEN** | 97/97 PASS | [`TRADITIONAL-RAG-BASELINE-FROZEN.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/rag/TRADITIONAL-RAG-BASELINE-FROZEN.md) |
| **Corrective RAG (CRAG)** | `Corrective-RAG-v1` | **FROZEN** | 163/163 PASS | [`RAG-14-CRAG-EVALUATION.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/crag/RAG-14-CRAG-EVALUATION.md) |
| **Adaptive Agentic RAG** | `Adaptive-RAG-v1` | **HOÀN THÀNH** | 254/254 PASS | [`RAG-18-ADAPTIVE-EVALUATION.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/adaptive/RAG-18-ADAPTIVE-EVALUATION.md) |
| **Toàn bộ dự án** | Bản tổng hợp nghiệm thu | **READY** | **391/391 PASS** | [`LATEST-EXPERIMENT-REPORT.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/experiment_latest/LATEST-EXPERIMENT-REPORT.md) |

---

## 📊 KẾT QUẢ ĐỐI CHUẨN THỰC NGHIỆM (80 CÂU HỎI BENCHMARK)

Toàn bộ kết quả được đo lường khách quan trên tập đối chuẩn 80 câu hỏi pháp lý (`evaluation/dataset/legal_qa.json`) thuộc 7 nhóm danh mục (A–G):

| Nhóm Chỉ số | Metric | Traditional RAG Baseline | Corrective RAG (CRAG) | Adaptive Agentic RAG | So sánh Cải thiện |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Truy xuất (Retrieval)** | **Recall@5 (Chunk)** | 0.8267 | 0.8667 | **0.8733** | **+4.66%** |
| | **Hit Rate@5** | 87.50% | 92.50% | **93.75%** | **+6.25%** |
| | **MRR** | 0.8125 | 0.8438 | **0.8521** | **+0.0396** |
| **Chất lượng trả lời** | **Answer Correctness** | 81.25% | 88.75% | **91.25%** | **+10.00%** |
| | **Strict Correctness** | 75.00% | 82.50% | **85.00%** | **+10.00%** |
| | **Faithfulness Rate** | 98.75% | 98.75% | **98.75%** | Giữ vững độ trung thực |
| | **Unsupported Claim** | 1.25% | 1.25% | **1.25%** | Không sinh ảo |
| **Trích dẫn (Citation)** | **Citation Coverage** | 88.75% | 92.50% | **93.75%** | **+5.00%** |
| | **Citation Accuracy** | 97.50% | 98.75% | **98.75%** | **+1.25%** |
| **An toàn & Từ chối** | **Refusal Accuracy** | 93.75% | 95.00% | **96.25%** | **+2.50%** |
| | **False Answer Rate** | 6.25% | 5.00% | **3.75%** | **-2.50% (An toàn hơn)** |
| **Độ trễ (Latency)** | **Mean Latency** | **418.52 ms** | 682.41 ms | 542.18 ms | Tối ưu hóa điều phối |

---

## 🔬 CASE STUDY: ĐỐI CHIẾU THỰC NGHIỆM TRỰC QUAN 3 MÔ HÌNH

Ví dụ đối chiếu thực tế khi chạy cả 3 mô hình trên câu hỏi pháp lý đa văn bản:  
> *"So sánh quy định về thời giờ làm việc và làm thêm giờ giữa Bộ luật Lao động 2019 và Nghị định 145/2020?"*

| Tiêu chí đối sánh | Traditional RAG Baseline (`run_rag_baseline.py`) | Corrective RAG (`run_crag.py`) | Adaptive Agentic RAG (`run_adaptive.py`) |
| :--- | :---: | :---: | :---: |
| **Cơ chế xử lý** | Nhồi toàn bộ câu hỏi dài vào ChromaDB | Đánh giá nhầm là đủ (`SUFFICIENT` 0.96) ➔ Direct Pass | **Phân loại `LEGAL_MULTI_DOC` ➔ Bẻ 2 sub-queries song song** |
| **Bao phủ văn bản luật** | ❌ **Bỏ sót Nghị định 145/2020** (Bị trôi sang NĐ 12/2022) | ❌ **Bỏ sót Nghị định 145/2020** (Chỉ lấy BLLD 2019 & NĐ 12) | ✅ **Bao phủ trọn vẹn cả BLLD 2019 & NĐ 145/2020** |
| **Số chunks truy xuất** | 5 chunks | 3 chunks | **6 chunks (3 BLLD 2019 + 3 NĐ 145/2020)** |
| **Độ trễ toàn chuỗi** | **167.89 ms** (Nhanh nhất) | 185.20 ms | 286.27 ms (+118 ms để phân rã và tổng hợp) |
| **Kết luận chất lượng** | *Nhanh nhưng thiếu một nửa văn bản cần so sánh* | *Nhanh nhưng trôi ngữ cảnh đa văn bản* | ⭐ **Chính xác, đầy đủ và chuẩn xác nhất theo yêu cầu câu hỏi** |

> **Ý nghĩa khoa học**: Trong tư vấn pháp luật, độ trễ thấp không có giá trị nếu câu trả lời bỏ sót văn bản luật đối chiếu. Adaptive Agentic RAG chấp nhận đánh đổi ~118ms để phân rã câu hỏi, từ đó đạt độ bao phủ văn bản đối chiếu tuyệt đối (100% Multi-Doc Coverage).

---

## 🚀 CÀI ĐẶT & KHỞI CHẠY HỆ THỐNG

### 1. Cài đặt môi trường & Thư viện

Yêu cầu Python >= 3.10 (khuyến nghị Python 3.13).

```bash
# Cách A: Cài đặt trực tiếp từ file requirements.txt
pip install -r requirements.txt

# Cách B: Tạo môi trường ảo riêng biệt (.venv)
python -m venv .venv
# Kích hoạt trên Windows PowerShell:
.venv\Scripts\Activate.ps1
# Kích hoạt trên Linux/macOS:
source .venv/bin/activate
# Cài đặt thư viện:
pip install -r requirements.txt
```

---

## 💻 HƯỚNG DẪN SỬ DỤNG GIAO DIỆN DÒNG LỆNH (CLI)

Hệ thống cung cấp sẵn các công cụ CLI độc lập, hỗ trợ cả chế độ chat tương tác và tra cứu đơn lẻ:

### 1. Chạy Traditional RAG Baseline
* **Hỏi đáp tương tác liên tục**:
  ```bash
  python run_rag_baseline.py
  ```
* **Tra cứu nhanh 1 câu hỏi**:
  ```bash
  python run_rag_baseline.py --query "Thời giờ làm việc bình thường của người lao động là bao nhiêu?"
  ```
* **Tùy chỉnh số chunk truy xuất (`--top-k`) và ngưỡng tương đồng (`--threshold`)**:
  ```bash
  python run_rag_baseline.py --query "Quy định về thử việc" --top-k 10 --threshold 0.50
  ```

### 2. Chạy Corrective RAG (CRAG)
Hệ thống tự động kích hoạt bộ đánh giá chứng cứ (`RetrievalEvaluator`) và cơ chế viết lại câu hỏi (`QueryRewriter`) khi truy xuất thiếu:
* **Hỏi đáp tương tác liên tục**:
  ```bash
  python run_crag.py
  ```
* **Tra cứu 1 câu hỏi (hiển thị chi tiết CRAG Trace, vòng 1 & vòng 2)**:
  ```bash
  python run_crag.py --query "Người lao động làm việc 5 năm thì được bao nhiêu ngày phép năm?"
  ```

### 3. Chạy Adaptive Agentic RAG
Tự động phân loại độ phức tạp câu hỏi (7 Intent), bẻ nhỏ câu hỏi đa chặng (Sub-queries Decomposition), tra cứu song song và tổng hợp câu trả lời:
* **Hỏi đáp tương tác liên tục**:
  ```bash
  python run_adaptive.py
  ```
* **Tra cứu 1 câu hỏi (hiển thị chi tiết Adaptive Routing Trace & Sub-queries Plan)**:
  ```bash
  python run_adaptive.py --query "So sánh quy định về thời giờ làm việc và làm thêm giờ giữa Bộ luật Lao động 2019 và Nghị định 145/2020?"
  ```

---

## 🧪 HƯỚNG DẪN CHẠY BENCHMARK THỰC NGHIỆM (EVALUATION RUNNERS)

Để tái hiện lại 100% số liệu thực nghiệm phục vụ viết báo cáo khóa luận:

### 1. Đánh giá tầng Dense Retrieval Baseline (RAG-09)
```bash
python evaluation/evaluate_retrieval.py
```
* Kết quả xuất ra: [`evaluation/results/retrieval_baseline.json`](file:///d:/Filehoc/KLCN/agentic-rag/evaluation/results/retrieval_baseline.json)

### 2. Đánh giá End-to-End Traditional RAG Baseline (RAG-10)
```bash
python evaluation/runner/baseline_runner.py
```
* Kết quả xuất ra: [`evaluation/results/traditional_baseline_full_eval.json`](file:///d:/Filehoc/KLCN/agentic-rag/evaluation/results/traditional_baseline_full_eval.json)

### 3. Đánh giá End-to-End Corrective RAG (CRAG) (RAG-14)
```bash
python evaluation/runner/corrective_runner.py
```
* Kết quả xuất ra: [`evaluation/results/corrective_full_eval.json`](file:///d:/Filehoc/KLCN/agentic-rag/evaluation/results/corrective_full_eval.json)

### 4. Đánh giá Bộ Phân loại độ phức tạp (Query Complexity Classifier)
```bash
python evaluation/runner/evaluate_classifier.py
```
* Kết quả xuất ra: [`evaluation/results/query_complexity_evaluation.json`](file:///d:/Filehoc/KLCN/agentic-rag/evaluation/results/query_complexity_evaluation.json)

### 5. Đánh giá Bộ Phân rã câu hỏi (Query Decomposition)
```bash
python evaluation/runner/evaluate_decomposer.py
```
* Kết quả xuất ra: [`evaluation/results/query_decomposition_evaluation.json`](file:///d:/Filehoc/KLCN/agentic-rag/evaluation/results/query_decomposition_evaluation.json)

### 6. Đánh giá End-to-End Toàn diện Adaptive Agentic RAG (RAG-18)
```bash
python evaluation/runner/adaptive_runner.py
```
* Kết quả xuất ra: [`evaluation/results/adaptive_evaluation.json`](file:///d:/Filehoc/KLCN/agentic-rag/evaluation/results/adaptive_evaluation.json)


### 7. Tính toán & Quy đổi Chi phí Token trên LLM Thương Mại
```bash
python evaluation/cost_calculator.py --save
```
* Báo cáo Markdown chi tiết: [`reports/experiment_latest/BANG_TINH_CHI_PHI_TOKEN_LLM.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/experiment_latest/BANG_TINH_CHI_PHI_TOKEN_LLM.md)
* Kết quả JSON cấu trúc: [`reports/experiment_latest/commercial_llm_cost_analysis.json`](file:///d:/Filehoc/KLCN/agentic-rag/reports/experiment_latest/commercial_llm_cost_analysis.json)

---

## 💰 BẢNG QUY ĐỔI CHI PHÍ TOKEN TRÊN CÁC LLM THƯƠNG MẠI ($ & VNĐ)

> **Tỷ giá áp dụng:** 1 USD = 25,500 VNĐ  
> **Dữ liệu thực nghiệm:** Đo đạc trên 80 câu hỏi kiểm định (Benchmark RAG-08) thuộc 7 nhóm độ phức tạp pháp luật lao động.

### 1. Thống kê tiêu thụ Token trung bình / câu hỏi
| Mô hình | Mean Input Tokens | Mean Output Tokens | Mean Total Tokens | Tiết kiệm Token vs Baseline |
| :--- | :---: | :---: | :---: | :---: |
| **Traditional RAG (Baseline)** | 611.0 | 1,087.0 | **1,698.1** | Baseline (Gốc) |
| **Corrective RAG (CRAG)** | 610.4 | 703.5 | **1,313.9** | **-22.62%** |
| **Adaptive Agentic RAG** | 512.4 | 794.6 | **1,307.0** | **-23.03%** |

### 2. Chi phí quy đổi cho 1 câu hỏi tra cứu pháp luật
| Mô hình LLM Thương Mại | Giá In/Out ($/1M) | Traditional RAG | Corrective RAG (CRAG) | Adaptive Agentic RAG | Mức Tiết Kiệm (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Google Gemini 1.5 Flash** | $0.075 / $0.300 | $0.00037 (9.5đ) | $0.00026 (6.5đ) | **$0.00028 (7.1đ)** | **-25.54%** |
| **OpenAI GPT-4o-mini** | $0.150 / $0.600 | $0.00074 (19.0đ) | $0.00051 (13.1đ) | **$0.00055 (14.1đ)** | **-25.54%** |
| **Google Gemini 1.5 Pro** | $1.250 / $5.000 | $0.00620 (158.1đ) | $0.00428 (109.2đ) | **$0.00461 (117.6đ)** | **-25.58%** |
| **OpenAI GPT-4o (Flagship)** | $2.500 / $10.000 | $0.01240 (316.1đ) | $0.00856 (218.3đ) | **$0.00923 (235.3đ)** | **-25.58%** |
| **Anthropic Claude 3.5 Sonnet** | $3.000 / $15.000 | $0.01814 (462.5đ) | $0.01238 (315.8đ) | **$0.01346 (343.1đ)** | **-25.81%** |

### 3. Dự phóng chi phí vận hành ở quy mô lớn
* **Quy mô 10,000 truy vấn** (Doanh nghiệp vừa): Trên GPT-4o-mini, Adaptive RAG tốn **141,167 VNĐ** (tiết kiệm **48,518 VNĐ** so với Baseline). Trên GPT-4o, Adaptive RAG tiết kiệm **808,643 VNĐ**.
* **Quy mô 100,000 truy vấn** (Cổng dịch vụ công quốc gia): Trên GPT-4o, Adaptive RAG tiết kiệm **8,086,433 VNĐ**; trên Claude 3.5 Sonnet tiết kiệm **11,940,962 VNĐ**.
* **Nguyên nhân kỹ thuật**: Adaptive RAG nhận diện câu hỏi chào hỏi / ngoài phạm vi để kích hoạt nhánh `DIRECT_REFUSAL`, hoàn toàn không tải context pháp luật (input tokens giảm còn 22 tokens); CRAG sử dụng Strip Refinement để cắt gọt tài liệu nhiễu trước khi sinh lời.

---

## 🗄️ CƠ SỞ DỮ LIỆU LƯU TRỮ LỊCH SỬ TRUY VẤN (SQLITE STORAGE)

Hệ thống tích hợp cơ sở dữ liệu SQLite nhúng tại [`data/history/query_history.db`](file:///d:/Filehoc/KLCN/agentic-rag/data/history/query_history.db) phục vụ ghi nhận toàn bộ truy vấn, câu trả lời, nhánh điều phối, căn cứ trích dẫn, latency và chi phí:

### 1. Công cụ dòng lệnh quản lý lịch sử (`show_history.py`)
```bash
# Xem tổng quan thống kê (tổng câu, từ chối, phân bổ mô hình/nhánh, latency, tokens, cost):
python show_history.py --summary

# Xem danh sách các phiên hỏi đáp gần nhất:
python show_history.py --list --limit 10

# Tìm kiếm câu hỏi/câu trả lời theo từ khóa:
python show_history.py --search "thử việc"

# Xem chi tiết một phiên hỏi đáp cụ thể theo ID:
python show_history.py --view 1

# Xuất dữ liệu lịch sử ra JSON hoặc CSV phục vụ phân tích:
python show_history.py --export-json history.json
python show_history.py --export-csv history.csv

# Chấm điểm / gửi phản hồi đánh giá của người dùng cho câu trả lời:
python show_history.py --rate 1 --score 5 --feedback "Căn cứ Điều 25 rất chính xác"
```

### 2. Tự động ghi nhận từ các CLI Runners
Cả 3 script [`run_rag_baseline.py`](file:///d:/Filehoc/KLCN/agentic-rag/run_rag_baseline.py), [`run_crag.py`](file:///d:/Filehoc/KLCN/agentic-rag/run_crag.py), và [`run_adaptive.py`](file:///d:/Filehoc/KLCN/agentic-rag/run_adaptive.py) đều tự động lưu lịch sử vào database (sử dụng cờ `--no-history` nếu muốn tắt lưu trữ).

---

## 🛡️ HƯỚNG DẪN CHẠY BỘ KIỂM THỬ TỰ ĐỘNG (UNIT & INTEGRATION TESTS)

Dự án duy trì hệ thống kiểm thử toàn diện với **264+ bài test** tự động (Zero Regression):

```bash
# 1. Chạy TOÀN BỘ bài test của toàn dự án:
pytest tests/ -v

# 2. Chạy kiểm thử hệ thống lưu trữ lịch sử SQLite:
pytest tests/test_query_history.py -v

# 3. Chạy các bài test của Traditional RAG Baseline:
pytest tests/rag tests/retriever tests/context tests/generator tests/citation tests/guards tests/embedding tests/vector_store -v

# 4. Chạy các bài test của Corrective RAG (CRAG):
pytest tests/crag tests/test_corrective_evaluator.py tests/test_corrective_loop.py tests/test_corrective_pipeline.py tests/test_query_rewriter.py -v

# 5. Chạy các bài test của Adaptive Agentic RAG:
pytest tests/adaptive tests/test_query_complexity_classifier.py tests/test_query_decomposer.py -v
```

---

## 📁 CẤU TRÚC THƯ MỤC DỰ ÁN TOÀN DIỆN

```text
agentic-rag/
├── RAG/                         # Hệ thống Traditional RAG Baseline (Đóng băng v1)
│   ├── retriever/               # Dense Retriever (Cosine Similarity Top-5)
│   ├── context/                 # Context Builder & Token Limiter
│   ├── generator/               # Legal Generator Prompt
│   ├── citation/                # Citation Resolver & Source URL Linker
│   ├── guards/                  # Pre-guard & Post-guard an toàn pháp lý
│   ├── corrective/              # Corrective RAG (Evaluator, Rewriter, Loop)
│   └── pipeline/                # Pipeline Traditional RAG hoàn chỉnh
├── CRAG/                        # Mô-đun mở rộng Corrective RAG
│   ├── evaluator/               # Retrieval Grader đa tiêu chí
│   ├── transformation/          # Query Refinement & Rewriting
│   ├── refinement/              # Knowledge Striping & Denoising
│   └── search/                  # Web Search Fallback Interface
├── Adaptive_RAG/                # Hệ thống Adaptive Agentic RAG
│   ├── classifier/              # Query Complexity Classifier (Rule + LLM)
│   ├── decomposer/              # Query Decomposition Engine
│   └── orchestrator/            # Bộ điều phối định tuyến thích ứng
├── Data_Processing/             # Tiền xử lý văn bản quy phạm pháp luật
├── storage/                     # Phân hệ lưu trữ CSDL Lịch sử truy vấn (SQLite)
│   ├── schema.py                # Schema bản ghi hỏi đáp & telemetry
│   └── query_history.py         # Quản trị SQLite DB an toàn giao dịch
├── data/
│   ├── chroma_db/               # CSDL Vector ChromaDB (1,390 chunks đã nạp sẵn)
│   └── history/                 # CSDL Lịch sử truy vấn (query_history.db)
├── evaluation/                  # Khung đối chuẩn và đánh giá khoa học
│   ├── dataset/                 # 80 câu hỏi pháp lý chuẩn hóa (legal_qa.json)
│   ├── answer_evaluator/        # Bộ đánh giá câu trả lời tự động
│   ├── metrics/                 # Hàm tính toán Recall, MRR, Correctness, Faithfulness
│   ├── runner/                  # Script chạy benchmark tự động
│   └── cost_calculator.py       # Công cụ tính toán quy đổi chi phí Token trên LLM thương mại
├── reports/                     # Toàn bộ báo cáo nghiệm thu kỹ thuật (Markdown + JSON)
│   ├── rag/                     # Báo cáo RAG-00 đến RAG-10 & CRAG-01 đến CRAG-07
│   ├── crag/                    # Báo cáo RAG-11 đến RAG-14
│   ├── adaptive/                # Báo cáo RAG-15 đến RAG-18
│   └── experiment_latest/       # Báo cáo thực nghiệm tổng hợp & Bảng quy đổi Token
├── tests/                       # Toàn bộ bài kiểm thử tự động
├── run_rag_baseline.py          # CLI chạy Traditional RAG Baseline (có lưu lịch sử)
├── run_crag.py                  # CLI chạy Corrective RAG (có lưu lịch sử)
├── run_adaptive.py              # CLI chạy Adaptive Agentic RAG (có lưu lịch sử)
├── show_history.py              # CLI tra cứu & quản lý lịch sử truy vấn
├── requirements.txt             # Danh mục thư viện Python chuẩn
├── HUONG_DAN_CHAY_THUC_NGHIEM.md # Sổ tay hướng dẫn chạy thực nghiệm toàn diện
└── README.md                    # Tài liệu hướng dẫn chính của dự án
```

---

## 📑 DANH MỤC TÀI LIỆU & BÁO CÁO NGHIỆM THU CHI TIẾT

* **Sổ tay thực nghiệm toàn diện (3 mô hình)**: [`HUONG_DAN_CHAY_THUC_NGHIEM.md`](file:///d:/Filehoc/KLCN/agentic-rag/HUONG_DAN_CHAY_THUC_NGHIEM.md)
* **Bảng tính chi phí Token trên LLM thương mại**: [`reports/experiment_latest/BANG_TINH_CHI_PHI_TOKEN_LLM.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/experiment_latest/BANG_TINH_CHI_PHI_TOKEN_LLM.md)
* **Báo cáo thực nghiệm tổng hợp mới nhất**: [`reports/experiment_latest/LATEST-EXPERIMENT-REPORT.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/experiment_latest/LATEST-EXPERIMENT-REPORT.md)
* **Văn bản đóng băng Traditional RAG Baseline**: [`reports/rag/TRADITIONAL-RAG-BASELINE-FROZEN.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/rag/TRADITIONAL-RAG-BASELINE-FROZEN.md)
* **Báo cáo đối sánh Baseline vs CRAG**: [`reports/rag/CRAG-07-COMPARISON.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/rag/CRAG-07-COMPARISON.md)
* **Báo cáo nghiệm thu Corrective RAG**: [`reports/crag/RAG-14-CRAG-EVALUATION.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/crag/RAG-14-CRAG-EVALUATION.md)
* **Báo cáo nghiệm thu Adaptive Agentic RAG**: [`reports/adaptive/RAG-18-ADAPTIVE-EVALUATION.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/adaptive/RAG-18-ADAPTIVE-EVALUATION.md)
