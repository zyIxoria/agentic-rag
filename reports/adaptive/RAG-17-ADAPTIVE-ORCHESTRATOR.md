# BÁO CÁO CÀI ĐẶT ADAPTIVE ORCHESTRATOR & MULTI-HOP DISPATCHER - ADAPTIVE RAG

## 1. TỔNG QUAN NHIỆM VỤ (TASK RAG-17)
- **Tên nhiệm vụ**: Xây dựng Bộ điều phối thích ứng thông minh (Adaptive Orchestrator) và Bộ phân phối truy xuất đa chặng (Multi-Hop Retrieval Dispatcher).
- **Mục tiêu**: Hợp nhất toàn bộ các phân hệ đã phát triển:
  - Bộ phân loại câu hỏi (Classifier - RAG-15).
  - Bộ phân rã câu hỏi con (Decomposer - RAG-16).
  - Traditional RAG Pipeline (Baseline - RAG-07).
  - Corrective RAG Pipeline (CRAG - RAG-14).
  - Bộ tổng hợp tri thức đa chặng (Multi-Hop Synthesizer).
- **Cơ sở khoa học**: Thay vì sử dụng một kiến trúc RAG cứng nhắc (Fixed Pipeline), Adaptive Agentic RAG phân tích đặc tính câu hỏi người dùng và lựa chọn con đường xử lý tối ưu nhất về cả độ chính xác, độ trung thực và độ trễ.

---

## 2. KIẾN TRÚC ĐIỀU PHỐI (ADAPTIVE ROUTING WORKFLOW)

```text
                           [User Question]
                                  │
                                  ▼
                   [Hybrid Query Classifier]
                                  │
         ┌────────────┬───────────┴───────────┬─────────────┐
         ▼            ▼                       ▼             ▼
   DIRECT_ANSWER  DIRECT_REFUSAL        TRADITIONAL_RAG  CORRECTIVE_RAG
         │            │                       │             │
    (Greeting)  (Out-of-Scope)           (Single-Hop)   (Procedural)
         │            │                       │             │
         ▼            ▼                       │             │
  [Instant Text]  [Safe Refusal]              │             │
  (Latency ~0ms)  (Latency ~0ms)              │             │
                                              ▼             ▼
                                        [Traditional]    [CRAG]
                                           Pipeline     Pipeline
                                              │             │
                                              ├─────────────┘
                                              ▼
                                        [Final Answer]
                                              ▲
                                              │
                                   [Multi-Hop Synthesizer]
                                              │
                                    Merged Deduplicated
                                       Legal Context
                                              │
                                  ┌───────────┴───────────┐
                                  ▼                       ▼
                            [SubQuery 1]            [SubQuery 2]
                                  ▲                       ▲
                                  └───────────┬───────────┘
                                              │
                                   [DECOMPOSE_AGENTIC]
                                 (Multi-Hop / Multi-Doc /
                                   Complex Conditions)
```

### 2.1. 5 Nhánh điều phối chuyên biệt
1. **`DIRECT_ANSWER`**: Dành cho câu hỏi chào hỏi, giới thiệu trợ lý ảo. Không cần nhúng véc-tơ, không tốn thời gian truy xuất ($\text{Latency} \approx 0\text{ ms}$).
2. **`DIRECT_REFUSAL`**: Dành cho câu hỏi phát hiện từ khóa ngoài phạm vi (CCCD, nồng độ cồn xe máy, visa du lịch, bóng đá, nấu ăn...). Từ chối an toàn tại cửa ngõ, triệt tiêu 100% ảo giác và bảo vệ ngân sách tính toán.
3. **`TRADITIONAL_RAG`**: Dành cho câu hỏi tra cứu khái niệm hoặc một điều luật cụ thể. Chạy thẳng qua Traditional RAG Pipeline (1 lượt retrieval nhanh).
4. **`CORRECTIVE_RAG`**: Dành cho câu hỏi về trình tự, thủ tục các bước. Kích hoạt Document Grader và Strip & Filter để loại bỏ các khoản gây nhiễu ngữ cảnh.
5. **`DECOMPOSE_AGENTIC`**: Dành cho câu hỏi đa văn bản (so sánh Luật & Nghị định) hoặc đa điều kiện xung đột (kỷ luật sa thải vs bảo vệ thai sản). Phân rã thành các truy vấn con nguyên tử, thực thi truy xuất song song, khử trùng lặp và tổng hợp qua `MultiHopSynthesizer`.

---

## 3. KẾT QUẢ KIỂM THỬ (UNIT TESTS)
Toàn bộ 6 test cases trong `tests/adaptive/test_adaptive_orchestrator.py` đều đạt kết quả xuất sắc:
1. `test_orchestrator_direct_answer`: Phản hồi tức thì với câu hỏi chào hỏi, không gọi retriever.
2. `test_orchestrator_direct_refusal`: Từ chối an toàn ngay tại cửa ngõ khi câu hỏi ngoài phạm vi.
3. `test_orchestrator_traditional_rag`: Điều phối chính xác câu hỏi tra cứu đơn lẻ về Traditional RAG.
4. `test_orchestrator_corrective_rag`: Điều phối câu hỏi quy trình, thủ tục về CRAG.
5. `test_orchestrator_decompose_agentic`: Điều phối câu hỏi liên văn bản về luồng phân rã và tổng hợp đa chặng.
6. `test_orchestrator_empty_query_fail_fast`: Xử lý an toàn câu hỏi rỗng.
