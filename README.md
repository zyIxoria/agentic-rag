# HỆ THỐNG AGENTIC RAG HỎI ĐÁP PHÁP LUẬT LAO ĐỘNG VIỆT NAM

Đề tài nghiên cứu so sánh thực nghiệm giữa 3 kiến trúc:
1. **Traditional RAG Baseline (`Traditional-RAG-v1`)** - *[Đã hoàn thành & Đã đóng băng]*
2. **Corrective RAG (CRAG)** - *[Giai đoạn tiếp theo]*
3. **Adaptive Agentic RAG** - *[Giai đoạn cuối]*

---

## 📖 HƯỚNG DẪN SỬ DỤNG NHANH

* **Tài liệu hướng dẫn chi tiết**: Vui lòng xem tệp [`HUONG_DAN_CHAY_RAG_BASELINE.md`](file:///d:/Filehoc/KLCN/agentic-rag/HUONG_DAN_CHAY_RAG_BASELINE.md).
* **Chạy giao diện dòng lệnh tương tác (CLI Chat)**:
  ```bash
  python run_rag_baseline.py
  ```
* **Tra cứu nhanh 1 câu hỏi**:
  ```bash
  python run_rag_baseline.py --query "Thời gian thử việc tối đa của người quản lý doanh nghiệp là bao lâu?"
  ```
* **Chạy đánh giá Benchmark toàn chuỗi (RAG-10)**:
  ```bash
  python evaluation/runner/baseline_runner.py
  ```
* **Chạy toàn bộ 97 bài kiểm thử tự động**:
  ```bash
  python -m unittest discover -s tests -t . -v
  python -m unittest discover -s evaluation/tests -v
  ```

---

## 📂 CẤU TRÚC THƯ MỤC CHÍNH

* `RAG/`: Mã nguồn kiến trúc Traditional RAG (embedding, vector_store, retriever, context, generator, citation, guards, pipeline).
* `evaluation/`: Bộ đánh giá đối chuẩn (dataset, metrics, answer_evaluator, runner).
* `reports/rag/`: Các báo cáo nghiệm thu kỹ thuật và tài liệu đóng băng baseline từ RAG-00 đến RAG-10.
* `tests/`: Toàn bộ test suite kiểm thử đơn vị và tích hợp.
* `Data_Processing/`: Dữ liệu gốc Dataset V2.1 (1,390 chunks).
