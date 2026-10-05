# BÁO CÁO TÍCH HỢP TOÀN DIỆN CORRECTIVE RAG PIPELINE (CRAG-04)

## 1. MÔ TẢ ĐƯỜNG ỐNG ĐẦU CUỐI (END-TO-END PIPELINE)
Pipeline hoàn chỉnh của Corrective RAG được tích hợp tại `RAG/corrective/corrective_rag.py` với lớp trung tâm `CorrectiveRAGPipeline`.

### Giao diện thực thi chuẩn:
```python
pipeline = CorrectiveRAGPipeline(config=CRAGConfig(...))
response: CRAGResponse = pipeline.answer(question: str)
```

### Cấu trúc Trace giám sát trong `CRAGResponse`:
Để phục vụ việc phân tích chi tiết nguyên nhân kích hoạt và đo lường độ trễ từng phân hệ, đối tượng phản hồi lưu vết đầy đủ thông tin:
- `original_query`: Câu hỏi nguyên bản của người dùng.
- `initial_retrieval`: Danh sách các chunk thu hồi lần 1.
- `initial_evaluation`: Kết quả đánh giá chất lượng tài liệu lần 1 (`status`, `confidence`, `reason`).
- `corrective_triggered`: Cờ Boolean xác nhận có kích hoạt vòng lặp hiệu chỉnh hay không.
- `rewritten_query`: Câu truy vấn đã được viết lại bởi `QueryRewriter`.
- `corrective_retrieval`: Danh sách các chunk thu hồi lần 2.
- `final_evaluation`: Kết quả đánh giá tài liệu trước khi gửi sang Context Builder.
- `answer`: Câu trả lời dứt khoát hoặc câu từ chối chuẩn mực.
- `citations`: Danh sách trích dẫn pháp lý đã được giải nghĩa từ metadata thật.
- `refused`: `True` nếu hệ thống từ chối do thiếu căn cứ.
- `retry_count`: Số lần thử lại (0 hoặc 1).
- `latency_ms`: Tổng thời gian thực thi (ms).
- `retrieval_latency`, `eval_latency`, `rewrite_latency`, `generation_latency`, `citation_latency`: Độ trễ chi tiết của từng bước.

---

## 2. KẾT QUẢ KIỂM THỬ TÍCH HỢP THỰC TẾ (INTEGRATION TESTS)
Tập kiểm thử `tests/test_corrective_pipeline.py` chạy trực tiếp trên cơ sở dữ liệu véc-tơ bền vững ChromaDB (`legal_labor_baseline_minilm`, 1,390 chunks) và ONNX Runtime `all-MiniLM-L6-v2`:
- `test_01_real_e2e_answerable_question`: **PASSED** (Chạy thành công câu hỏi thời giờ làm việc bình thường; trả về trích dẫn Điều 105 BLLD 2019).
- `test_02_real_e2e_out_of_scope_question`: **PASSED** (Chạy câu hỏi mua vé Ngoại hạng Anh; kích hoạt rewrite, kiểm tra lại và từ chối an toàn với `refused=True`, `citations=[]`).
- `test_03_real_e2e_insufficient_evidence_question`: **PASSED** (Chạy câu hỏi tỷ lệ hưởng lương hưu theo Luật BHXH 2014; hệ thống phát hiện tài liệu ngoài corpus và từ chối an toàn).
- `test_04_trace_dictionary_serialization`: **PASSED** (Kiểm tra serialization toàn bộ trace ra Dictionary/JSON).
