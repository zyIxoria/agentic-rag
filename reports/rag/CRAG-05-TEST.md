# BÁO CÁO KẾT QUẢ KIỂM THỬ VÀ HỒI QUY TOÀN HỆ THỐNG (CRAG-05)

## 1. TỔNG HỢP KẾT QUẢ KIỂM THỬ
Toàn bộ hệ thống kiểm thử gồm **163 test cases** đã được thực thi tự động qua `pytest` trên môi trường Python 3.13:

```text
============================ 163 passed in 15.14s =============================
```

### Phân loại chi tiết:
| Phân hệ kiểm thử | File kiểm thử | Số ca | Kết quả | Ghi chú |
|---|---|---|---|---|
| **Retrieval Evaluator** | `tests/test_corrective_evaluator.py` | 9 | **9/9 PASS** | Thẩm định chất lượng, distractor, schema invariants |
| **Query Rewriter** | `tests/test_query_rewriter.py` | 7 | **7/7 PASS** | Chuẩn hóa từ vựng, cấm hallucinate số điều |
| **Corrective Loop** | `tests/test_corrective_loop.py` | 5 | **5/5 PASS** | Chu trình C01 - C05, giới hạn MAX_RETRIES = 1 |
| **E2E Integration** | `tests/test_corrective_pipeline.py` | 4 | **4/4 PASS** | Tích hợp ChromaDB và ONNX thực tế |
| **Traditional RAG Pipeline** | `tests/rag/test_pipeline.py` | 9 | **9/9 PASS** | Baseline tiếp tục hoạt động độc lập |
| **Dense Retriever** | `tests/retriever/test_retriever.py` | 10 | **10/10 PASS** | Thu hồi véc-tơ Top-K, cosine similarity |
| **Persistent Vector Store** | `tests/vector_store/test_vector_store.py` | 14 | **14/14 PASS** | Quản lý ChromaDB 1,390 chunks |
| **Embedding Pipeline** | `tests/embedding/test_embedding.py` | 14 | **14/14 PASS** | all-MiniLM-L6-v2 ONNX, L2 norm |
| **LLM Generator** | `tests/generator/test_generator.py` | 11 | **11/11 PASS** | Mock & cloud generator, prompt injection guard |
| **Citation Mapping** | `tests/citation/test_citation.py` | 13 | **13/13 PASS** | Ánh xạ trích dẫn chuẩn [SOURCE N] |
| **Context Builder** | `tests/context/test_context_builder.py` | 13 | **13/13 PASS** | Đóng gói ngữ cảnh có cấu trúc |
| **Refusal Guard** | `tests/guards/test_refusal_guard.py` | 7 | **7/7 PASS** | Pre/Post generation safety guard |
| **Baseline Evaluation** | `tests/evaluation/test_baseline_eval.py` | 9 | **9/9 PASS** | Đánh giá correctness, faithfulness, refusal |
| **Legacy / Exploratory** | `tests/crag/`, `tests/adaptive/` | 38 | **38/38 PASS** | Bảo toàn các fixture kiểm thử mở rộng |
| **TỔNG CỘNG** | | **163** | **163/163 PASS (100%)** | **0 REGRESSION** |

---

## 2. XÁC NHẬN TÍNH NGUYÊN VẸN CỦA TRADITIONAL RAG BASELINE
1. **Không sửa đổi pipeline cũ**: Tuyệt đối không thay đổi mã nguồn tại `RAG/pipeline/traditional_rag.py`.
2. **Không sửa đổi cấu hình véc-tơ**: Giữ nguyên `legal_labor_baseline_minilm` (1,390 chunks, 384 dimensions, Cosine distance).
3. **Không phá vỡ kiểm định cũ**: 97/97 test gốc của baseline Traditional RAG tiếp tục vượt qua 100%, bảo đảm kết quả đối chiếu giữa 2 hệ thống là hoàn toàn khách quan, có thể tái lập (reproducible).
