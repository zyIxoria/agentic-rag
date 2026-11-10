# BÁO CÁO AUDIT NGUYÊN NHÂN FALSE ANSWER RATE TRÊN BỘ KIỂM THỬ TỪ CHỐI (REFUSAL SET)

> **Mã báo cáo:** AUDIT-REFUSAL-20261110  
> **Tập dữ liệu kiểm định:** Benchmark-300 (50 câu hỏi yêu cầu từ chối an toàn: 25 `insufficient_evidence` + 25 `out_of_scope`)  
> **Đối tượng đánh giá:** Traditional RAG, Corrective RAG (CRAG), Adaptive Agentic RAG  
> **Tệp dữ liệu chi tiết kèm theo:** [`false_answer_audit.csv`](file:///d:/Filehoc/KLCN/agentic-rag/false_answer_audit.csv), [`error_distribution.json`](file:///d:/Filehoc/KLCN/agentic-rag/error_distribution.json)

---

## 1. TỔNG QUAN HIỆN TRẠNG VÀ PHÁT HIỆN CỐT LÕI

Trong thực nghiệm đánh giá toàn diện Benchmark-300, trên bộ kiểm thử 50 câu hỏi bắt buộc phải từ chối an toàn (`requires_refusal = True`), tỷ lệ trả lời bừa / ảo giác khẳng định (**False Answer Rate**) của cả 3 hệ thống ghi nhận ở mức báo động:

| Hệ thống | Tổng số câu từ chối | Số câu trả lời bừa (False Answer) | Tỷ lệ trả lời bừa (False Answer Rate) | Tỷ lệ từ chối đúng (Refusal Accuracy) |
| :--- | :---: | :---: | :---: | :---: |
| **Traditional RAG** | 50 | **37 / 50** | **74.00%** | 26.00% (13/50) |
| **Corrective RAG (CRAG)** | 50 | **32 / 50** | **64.00%** | 36.00% (18/50) |
| **Adaptive Agentic RAG** | 50 | **31 / 50** | **62.00%** | **38.00%** (19/50) |

### Phân tích bóc tách theo 2 phân nhóm kiểm thử:

1. **Nhóm `insufficient_evidence` (25 câu hỏi thiếu chứng cứ trong kho dữ liệu):**
   * Cả 3 hệ thống **trả lời bừa 23 / 25 câu (tỷ lệ lỗi 92.00%)**.
   * Chỉ có **2 câu duy nhất được từ chối (Q227, Q233)**. Đáng chú ý, 2 câu này được từ chối **không phải vì hệ thống nhận biết thiếu dữ liệu**, mà do câu hỏi chứa từ khóa kích hoạt ngoài phạm vi ngẫu nhiên: Q227 chứa từ *"sáng chế"* (trùng bộ lọc Sở hữu trí tuệ) và Q233 chứa từ *"cổ phiếu"* (trùng bộ lọc Chứng khoán).
   * **Kết luận:** Hệ thống hiện tại có **0% năng lực tự thân nhận diện việc thiếu bằng chứng pháp lý (Zero True Insufficient Evidence Detection)** khi câu hỏi thuộc quan hệ lao động.

2. **Nhóm `out_of_scope` (25 câu hỏi ngoài phạm vi pháp luật lao động):**
   * **Traditional RAG:** Trả lời bừa **14 / 25 câu (56.00%)** do hoàn toàn không có bộ lọc phân loại phạm vi đầu vào.
   * **CRAG:** Trả lời bừa **9 / 25 câu (36.00%)** do bộ lọc từ khóa trong `SemanticDocumentGrader` bị lọt các chủ đề mới.
   * **Adaptive Agentic RAG:** Trả lời bừa **8 / 25 câu (32.00%)** do `HybridQueryClassifier` phân loại nhầm các câu hỏi Khoa học, Hình sự, Thuật toán, Y tế thành câu hỏi pháp luật phức tạp (`LEGAL_CONDITIONAL` / `LEGAL_DIRECT_DEF`).

---

## 2. PHÂN LOẠI VÀ THỐNG KÊ 6 NHÓM NGUYÊN NHÂN LỖI (A - F)

Theo phương pháp truy vết đa tầng (Multi-tier Traceability), một trường hợp trả lời bừa là hệ quả dây chuyền qua nhiều tầng xử lý. Bảng dưới đây thể hiện số lượng và tỷ lệ xuất hiện của từng nhóm lỗi trên 100 lượt trả lời bừa được ghi nhận:

| Mã lỗi | Nhóm nguyên nhân lỗi | Traditional RAG (n=37) | CRAG (n=32) | Adaptive RAG (n=31) | Tổng lượt xuất hiện (N=100) | Tỷ lệ xuất hiện |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **A** | **Scope Classification Error** *(Nhận diện sai phạm vi)* | 14 *(bỏ qua phân loại)* | 9 (28.1%) | 8 (25.8%) | 31 | 31.0% |
| **B** | **Routing Error** *(Router bỏ qua chỉ thị từ chối)* | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 | 0.0% |
| **C** | **Retrieval Error** *(Dense Retriever ảo giác điểm số)* | 37 (100.0%) | 32 (100.0%) | 31 (100.0%) | 100 | 100.0% |
| **D** | **Evidence Validation Error** *(Chấp nhận tài liệu không hỗ trợ)* | 37 (100.0%) | 32 (100.0%) | 31 (100.0%) | 100 | 100.0% |
| **E** | **Generation Error** *(Generator tự suy diễn/khẳng định)* | 37 (100.0%) | 32 (100.0%) | 31 (100.0%) | 100 | 100.0% |
| **F** | **Refusal Guard Error** *(Chốt chặn sau sinh bị qua mặt)* | 37 (100.0%) | 32 (100.0%) | 31 (100.0%) | 100 | 100.0% |

---

## 3. TRUY VẾT CHI TIẾT THEO TỪNG NHÓM NGUYÊN NHÂN

### Lỗi A: Scope Classification Error (Nhận diện sai phạm vi câu hỏi)
* **Cơ chế phát sinh:**
  Trong `HybridQueryClassifier`, bộ quy tắc lọc ngoài phạm vi (`OUT_OF_SCOPE_PATTERNS`) dựa trên danh sách từ khóa cố định (`nhãn hiệu`, `bóng đá`, `visa`, `nấu ăn`, `ly hôn`, `thời tiết`). Khi người dùng hỏi các câu hỏi kiến thức ngoài ngành nhưng không chứa đúng các từ khóa này, bộ phân loại rơi vào nhánh `_classify_legal_complexity()` mặc định.
* **Các trường hợp điển hình:**
  * **Q240 (Thuật toán QuickSort):** Câu hỏi: *"Thuật toán sắp xếp QuickSort có độ phức tạp thời gian trường hợp xấu nhất là bao nhiêu?"* -> Classifier thấy cấu trúc so sánh/điều kiện, phân loại nhầm thành `intent=LEGAL_CONDITIONAL`, `complexity=COMPLEX_MULTI_HOP`, gợi ý điều phối `route=DECOMPOSE_AGENTIC`.
  * **Q235 (Bộ luật Hình sự):** Câu hỏi: *"Mức hình phạt tù cao nhất đối với tội trộm cắp tài sản theo BLHS..."* -> Classifier thấy *"Mức hình phạt..."* -> Phân loại nhầm thành `intent=LEGAL_DIRECT_DEF`, gợi ý điều phối `CORRECTIVE_RAG`.
  * **Q241 (Toán học):** Câu hỏi: *"Công thức toán học tính diện tích hình cầu..."* -> Classifier gán `LEGAL_DIRECT_DEF`.
  * **Q242 (Vật lý):** Câu hỏi: *"Nguyên nhân vật lý gây ra hiện tượng nhật thực toàn phần..."* -> Classifier gán `LEGAL_DIRECT_DEF`.
  * **Q243 (Y học):** Câu hỏi: *"Vitamin C (Acid Ascorbic) có vai trò sinh học gì đối với cơ thể người..."* -> Classifier gán `LEGAL_CONDITIONAL`.
  * **Q246 (Y tế chuyên môn):** Câu hỏi: *"Điều kiện và tiêu chuẩn chuyên môn để một người được cấp chứng chỉ hành nghề khám bệnh, chữa bệnh..."* -> Classifier gán `LEGAL_DIRECT_DEF`.
  * **Q248 (Hiệp định quốc tế):** Câu hỏi: *"Hiệp định Đối tác Toàn diện và Tiến bộ xuyên Thái Bình Dương (CPTPP) có bao nhiêu quốc gia thành viên..."* -> Classifier gán `LEGAL_DIRECT_DEF`.
  * **Q250 (Trí tuệ nhân tạo):** Câu hỏi: *"Trong kiến trúc mạng nơ-ron Transformer, cơ chế Self-Attention được tính toán..."* -> Classifier gán `LEGAL_DIRECT_DEF`.

### Lỗi B: Routing Error (Định tuyến sai)
* **Kết quả audit:** Ghi nhận **0 lỗi (0.0%)**.
* **Đánh giá:** Khi `HybridQueryClassifier` đã xác định được `OUT_OF_SCOPE`, `AdaptiveOrchestrator` luôn tuân thủ 100% việc chuyển sang nhánh `DIRECT_REFUSAL` và trả về thông báo từ chối lập tức với độ trễ 0 ms. Lỗi không nằm ở khâu Router bỏ qua nhãn, mà nằm ở khâu Classifier gán nhãn sai ngay từ đầu (Lỗi A).

### Lỗi C: Retrieval Error (Ảo giác điểm số tương đồng ngữ nghĩa)
* **Cơ chế phát sinh:**
  `DenseTopKRetriever` dùng mô hình embedding không gian liên tục. Khi gặp câu hỏi `insufficient_evidence` hoặc `out_of_scope`:
  * Đối với `insufficient_evidence` (ví dụ Q065 về Luật Công đoàn 2012): Các từ ngữ *"công đoàn"*, *"doanh nghiệp"*, *"đóng"*, *"tiền lương"* có mật độ xuất hiện rất dày đặc trong Bộ luật Lao động 2019 và Nghị định 145/2020. Do đó, Dense Retriever tính ra điểm tương đồng cosine lên tới **0.7789** (cho chunk `ND_12_2022_Điều43_Khoản1_179`) và **0.7720** (cho chunk `ND_145_2020_Điều114_Khoản2_P3_262`).
  * Đối với `out_of_scope` (ví dụ Q240 về QuickSort): Dense Retriever vẫn trả về các chunk luật với điểm tương đồng **0.5786** (`LUAT_BHXH_2024_Điều18`) và **0.5778** (`BLLD_2019_Điều124`).
  * Vì ngưỡng `SIMILARITY_THRESHOLD` trong hệ thống đặt ở mức **0.45**, toàn bộ các chunk không liên quan này đều vượt ngưỡng và được coi là "hợp lệ".

### Lỗi D: Evidence Validation Error (Chấp nhận tài liệu không hỗ trợ)
* **Traditional RAG:**
  * Cấu hình thực nghiệm `ENABLE_PRE_GUARD=False`. Kể cả khi bật Pre-Guard, ngưỡng lọc chỉ so sánh `max_score < 0.45`, trong khi điểm các chunk sai đều từ 0.55 - 0.78, nên Pre-Guard không có tác dụng.
  * Hệ thống hoàn toàn thiếu cơ chế **Document-Level Grounding Check** (kiểm tra xem văn bản pháp luật được hỏi trong câu hỏi có thực sự nằm trong 19 văn bản của corpus hay không).
* **Corrective RAG (CRAG):**
  * `SemanticDocumentGrader`: Khi các chunk bị điểm thấp hoặc không khớp nội dung, Grader xác định `GradeVerdict.INCORRECT` hoặc `AMBIGUOUS`.
  * Thay vì chuyển sang hành động `ActionTrigger.REFUSE`, logic hiện tại của CRAG lại tự động chuyển sang `ActionTrigger.WEB_SEARCH` hoặc `ActionTrigger.COMBINE_SEARCH`!
  * Mock Web Searcher trả về snippet giả lập, và hệ thống tiếp tục nạp vào Generator thay vì dừng lại.
* **Adaptive Agentic RAG:**
  * `PostRetrievalConfidenceEvaluator`: Khi thẩm định sau truy xuất thấy chất lượng kém (`LOW` / `INCORRECT`), phương thức `evaluate()` tự động đề xuất `recommended_action = EscalationTarget.ESCALATE_TO_CRAG`.
  * Hệ thống không có nhánh `EscalationTarget.REFUSE` sau bước truy xuất. Do đó, việc thiếu căn cứ chỉ làm tăng độ phức tạp của luồng (leo thang sang CRAG hoặc Decompose) chứ không dẫn đến từ chối.

### Lỗi E: Generation Error (Generator suy diễn khẳng định câu trả lời)
* **Cơ chế phát sinh:**
  Trong `MockLegalGenerator` (cũng như hành vi thông thường của các LLM không có guardrail chặt chẽ):
  * Điều kiện kiểm tra liên quan tại dòng 128:
    ```python
    if len(common) >= 2 or (overlap_ratio >= 0.5 and len(significant_q_keywords) <= 2):
        is_relevant = True
        matching_sources.append(src)
    ```
  * Chỉ cần có 2 từ chung (như *"lao động"*, *"lương"*, *"thời hạn"*, *"điều kiện"*), generator kết luận context có liên quan và tiến hành tổng hợp câu trả lời khẳng định:
    > *"Theo quy định của pháp luật lao động hiện hành về nội dung bạn đang tra cứu: 1. Theo Điều 43 Nghị định 12/2022... 2. Theo Điều 114 Nghị định 145/2020..."*
  * Generator không kiểm tra xem câu hỏi hỏi về văn bản nào, và nội dung chunk có thực sự giải đáp được con số/thời hạn được hỏi hay không.

### Lỗi F: Refusal Guard Error (Chốt chặn sau sinh bị qua mặt)
* **Cơ chế phát sinh:**
  Tại `RefusalGuard.check_post_generation()`:
  1. Kiểm tra trích dẫn (`REJECT_UNSUPPORTED_ANSWERS`): Guard chỉ kiểm tra xem các ký hiệu `[SOURCE 1]`, `[SOURCE 2]` trong câu trả lời có nằm trong bảng ánh xạ `citation_mapping` của context builder hay không. Vì Generator trích dẫn chính các chunk sai được cung cấp, trích dẫn được đánh giá là **100% hợp lệ**.
  2. Kiểm tra tính trung thực (`RealTimeHallucinationVerifier`): Guard kiểm tra xem câu trả lời có bịa đặt so với context hay không. Vì Generator tóm tắt trung thực nội dung của chunk sai, câu trả lời đạt điểm **Faithfulness = 1.0 (trung thực với ngữ cảnh sai)**.
  3. **Lỗ hổng cốt tử:** Guard hoàn toàn thiếu bước **Question-Answer Alignment / Relevance Check** (kiểm tra xem câu trả lời có thực sự trả lời đúng câu hỏi của người dùng hay đang nói sang một vấn đề khác).

---

## 4. BẢNG TRUY VẾT CÁC CÂU HỎI ĐIỂN HÌNH

Dưới đây là trích đoạn các ca lỗi tiêu biểu được trích xuất từ [`false_answer_audit.csv`](file:///d:/Filehoc\KLCN\agentic-rag\false_answer_audit.csv):

| QID | Phân loại | Câu hỏi tóm tắt | Classifier Intent | Routing / Action | Chunks truy xuất tiêu biểu (Score) | Nguyên nhân không từ chối | Nhóm lỗi |
| :---: | :---: | :--- | :---: | :---: | :--- | :--- | :---: |
| **Q065** | `insufficient` | Mức đóng kinh phí công đoàn theo Luật Công đoàn 2012? | `LEGAL_DIRECT_DEF` | `CORRECTIVE_RAG` / `WEB_SEARCH` | `ND_12_2022_Điều43` (0.779), `ND_145_2020_Điều114` (0.772) | DenseRetriever ảo giác điểm số cao; Generator ghép Điều 43 NĐ 12 trả lời thay vì từ chối thiếu văn bản. | **C + D + E + F** |
| **Q066** | `insufficient` | Tỷ lệ hưởng lương hưu tối đa của lao động nữ theo Luật BHXH 2014? | `LEGAL_DIRECT_DEF` | `CORRECTIVE_RAG` / `REFINE` | `LUAT_BHXH_2024_Điều141` (0.781), `BLLD_2019_Điều169` (0.765) | Kho dữ liệu chỉ có Luật BHXH 2024 (chưa có Luật 2014); hệ thống lấy Điều 141 Luật 2024 trả lời bừa. | **C + D + E + F** |
| **Q067** | `insufficient` | Trợ cấp một lần suy giảm 15% do tai nạn LĐ theo Luật ATVSLĐ 2015? | `LEGAL_DIRECT_DEF` | `CORRECTIVE_RAG` / `COMBINE_SEARCH` | `BLLD_2019_Điều38` (0.742), `BLLD_2019_Điều39` (0.738) | Luật ATVSLĐ 2015 không có trong corpus; hệ thống trích BLLĐ 2019 về trách nhiệm NSDLĐ để trả lời bừa. | **C + D + E + F** |
| **Q234** | `out_of_scope` | Xe mô tô đi vào đường cao tốc bị phạt bao nhiêu? | `LEGAL_CONDITIONAL` | `DECOMPOSE_AGENTIC` / `WEB_SEARCH` | `ND_12_2022_Điều43` (0.591), `LUAT_BHXH_2024_Điều18` (0.584) | Classifier không có từ khóa giao thông cao tốc; gán nhầm thành câu hỏi đa điều kiện; sinh câu trả lời luật LĐ. | **A + C + D + E + F** |
| **Q235** | `out_of_scope` | Mức phạt tù cao nhất với tội trộm cắp tài sản theo BLHS? | `LEGAL_DIRECT_DEF` | `CORRECTIVE_RAG` / `WEB_SEARCH` | `BLLD_2019_Điều125` (0.612), `BLLD_2019_Điều124` (0.605) | Câu hỏi hình sự bị nhầm thành định nghĩa pháp luật; hệ thống trích điều khoản kỷ luật sa thải BLLĐ để trả lời. | **A + C + D + E + F** |
| **Q238** | `out_of_scope` | Lệ phí trước bạ khi đăng ký nhà đất? | `LEGAL_DIRECT_DEF` | `CORRECTIVE_RAG` / `WEB_SEARCH` | `ND_145_2020_Điều114` (0.583), `BLLD_2019_Điều105` (0.579) | Câu hỏi đất đai/thuế bị phân loại nhầm thành pháp luật lao động; trả lời bừa từ quy định tiền lương. | **A + C + D + E + F** |
| **Q240** | `out_of_scope` | Độ phức tạp xấu nhất của thuật toán QuickSort? | `LEGAL_CONDITIONAL` | `DECOMPOSE_AGENTIC` / `WEB_SEARCH` | `LUAT_BHXH_2024_Điều18` (0.579), `BLLD_2019_Điều124` (0.578) | Câu hỏi tin học/thuật toán bị nhầm thành `LEGAL_CONDITIONAL`; hệ thống phân rã và trả lời bằng Điều 124 BLLĐ. | **A + C + D + E + F** |
| **Q242** | `out_of_scope` | Nguyên nhân vật lý gây nhật thực toàn phần? | `LEGAL_DIRECT_DEF` | `CORRECTIVE_RAG` / `WEB_SEARCH` | `LUAT_BHXH_2024_Điều18` (0.564), `BLLD_2019_Điều105` (0.558) | Câu hỏi thiên văn/vật lý bị gán `LEGAL_DIRECT_DEF`; trả lời bừa từ ngữ cảnh luật BHXH. | **A + C + D + E + F** |

---

## 5. KẾT LUẬN VÀ BÀI HỌC KIẾN TRÚC

1. **Vấn đề cốt lõi của RAG pháp lý:** Tỷ lệ trả lời bừa cao (62% - 74%) không xuất phát từ việc mô hình LLM kém thông minh, mà xuất phát từ **sự thiếu vắng các chốt chặn phủ định (Negative Gates)** ở cả 3 giai đoạn: Trước truy xuất (Pre-retrieval), Sau truy xuất (Post-retrieval) và Sau sinh câu trả lời (Post-generation).
2. **Ảo giác điểm số Dense Retrieval:** Việc phụ thuộc đơn thuần vào ngưỡng tương đồng cosine là sai lầm trong miền pháp luật chuyên sâu. Vector embedding luôn tìm thấy điểm tương đồng từ vựng bề mặt (lexical overlap), tạo ra điểm số giả tạo khiến hệ thống lầm tưởng là có căn cứ.
3. **Sự nhầm lẫn giữa "Tìm kiếm ngoài" và "Từ chối an toàn":** Trong CRAG và Adaptive RAG, cơ chế fallback hiện tại ưu tiên tìm kiếm ngoài (Web Search) hoặc nâng cấp luồng (Escalation) hơn là từ chối. Điều này dẫn đến việc câu hỏi thiếu dữ liệu bị biến thành câu hỏi sinh ảo giác.
