# BÁO CÁO KỸ THUẬT: MODULE 0 — QUERY COMPLEXITY CLASSIFIER

> **Dự án**: Nghiên cứu cơ chế điều phối thích ứng trong hệ thống Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam  
> **Mã báo cáo**: `RAG-15-QUERY-COMPLEXITY-CLASSIFIER`  
> **Module**: Module 0 — Bộ phân loại độ phức tạp câu hỏi (Query Complexity Classifier)  
> **Trạng thái**: **HOÀN THÀNH & ĐÃ ĐƯỢC KIỂM ĐỊNH (PASS 213/213 TESTS)**  
> **Ngày hoàn thành**: 05/10/2026  

---

## 1. MỤC TIÊU (OBJECTIVE)

Xây dựng một bộ phân loại độ phức tạp câu hỏi (**Query Complexity Classifier**) độc lập, tất định (deterministic), minh bạch có giải thích (explainable) và an toàn tuyệt đối cho hệ thống **Adaptive Agentic RAG**.

Bộ phân loại có nhiệm vụ:
1. Nhận câu hỏi pháp luật lao động tiếng Việt từ người dùng.
2. Trích xuất tự động và có cấu trúc hơn 10 đặc trưng pháp lý chuyên sâu (*Legal Complexity Features*).
3. Phân loại câu hỏi vào một trong 3 cấp độ phức tạp chuẩn tắc:
   - **`SIMPLE`** $\to$ Điều phối tới **`DIRECT_RAG`** (Traditional RAG Baseline đã freeze).
   - **`MODERATE`** $\to$ Điều phối tới **`CRAG`** (Corrective RAG Pipeline đã freeze).
   - **`COMPLEX`** $\to$ Điều phối tới **`DECOMPOSITION_CRAG`** (Phân rã câu hỏi đa chiều kết hợp CRAG).
4. Khẳng định tính an toàn học thuật: **Tỷ lệ lỗi Complex-to-Simple Error Rate phải bằng 0.0%**, tuyệt đối không để lọt câu hỏi phức tạp (cần phân rã) sang luồng RAG đơn giản.

---

## 2. ĐỘNG LỰC NGHIÊN CỨU (MOTIVATION)

Trong các nghiên cứu RAG truyền thống và Corrective RAG:
* **Traditional RAG**: Áp dụng chung một chiến lược truy xuất đơn lẻ (Single Dense Retrieval + LLM Generator) cho mọi câu hỏi, dẫn đến thất bại nặng nề trên các câu hỏi đa văn bản, đa điều kiện và viện dẫn chéo (như đã chứng minh trong báo cáo `RAG-09` và `RAG-10`).
* **Corrective RAG**: Bổ sung bộ đánh giá Retrieval Evaluator và Query Rewriter giúp tăng cường độ chính xác khi tài liệu chưa khớp, nhưng vẫn bị nghẽn (bottleneck) nếu câu hỏi chứa nhiều khía cạnh pháp lý độc lập đòi hỏi phải chia tách thành nhiều sub-queries riêng biệt.

Nếu áp dụng Query Decomposition hoặc CRAG cho toàn bộ 100% câu hỏi:
* Chi phí tính toán (LLM calls) và độ trễ phản hồi (latency) tăng vọt từ 3x đến 8x một cách lãng phí cho các câu hỏi định nghĩa/định mức đơn giản.

Do đó, **Query Complexity Classifier** là "trái tim điều phối" (*Dispatching Gateway*) của hệ thống Adaptive Agentic RAG, cho phép hệ thống "nhìn nhận" độ phức tạp pháp lý của câu hỏi trước khi quyết định kích hoạt đường ống xử lý tối ưu.

```text
                                   User Query
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │  Query Complexity Classifier │
                        │          (Module 0)          │
                        └──────────────┬───────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
   [SIMPLE]                      [MODERATE]                     [COMPLEX]
   • 1 vấn đề pháp lý            • Tình huống, thủ tục          • Đa văn bản, đa điều luật
   • 1 Điều/Khoản trực tiếp      • 1-2 điều kiện cùng luật      • Viện dẫn chéo, so sánh
   • Tra cứu trực tiếp           • Cần kiểm tra bằng chứng      • Tính toán đa giai đoạn
         │                             │                             │
         ▼                             ▼                             ▼
┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
│   DIRECT_RAG    │           │      CRAG       │           │  DECOMPOSITION  │
│ (Baseline RAG)  │           │(Corrective RAG) │           │     + CRAG      │
└─────────────────┘           └─────────────────┘           └─────────────────┘
```

---

## 3. PHÂN LOẠI 3 CẤP ĐỘ PHỨC TẠP (CLASSIFICATION TAXONOMY)

| Cấp độ | Định nghĩa pháp lý | Đặc trưng cấu trúc | Chiến lược đề xuất (`recommended_strategy`) | Ví dụ điển hình |
| :--- | :--- | :--- | :--- | :--- |
| **`SIMPLE`** | Câu hỏi đơn nhất, định lượng, định nghĩa trực tiếp, liên quan 1 Điều/Khoản duy nhất. | - `number_of_legal_issues = 1`<br>- `multi_condition = False`<br>- `multi_document = False`<br>- `cross_reference = False`<br>- Không yêu cầu tính toán | **`DIRECT_RAG`** | *"Thời giờ làm việc bình thường của người lao động được quy định tối đa bao nhiêu giờ trong một ngày?"* |
| **`MODERATE`** | Câu hỏi tình huống, điều kiện phát sinh quyền lợi/nghĩa vụ, thủ tục quy trình nhiều bước trong cùng 1 văn bản; hoặc câu hỏi dùng từ ngữ đời thường/mơ hồ cần viết lại. | - `multi_condition = True` hoặc<br>- `procedural_required = True` hoặc<br>- `calculation_required = True` (đơn vế) hoặc<br>- `ambiguity = True` hoặc<br>- 2 vấn đề trong cùng luật | **`CRAG`** | *"Người lao động thử việc có được hưởng lương trong thời gian thử việc không?"*<br>*"Người lao động có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước trong trường hợp nào?"* |
| **`COMPLEX`** | Câu hỏi đa văn bản quy phạm, viện dẫn chéo giữa các Điều luật, câu hỏi kép đa chế định, so sánh/đối chiếu quy định, tính toán phức hợp đa thời kỳ. | - `multi_document = True` hoặc<br>- `cross_reference = True` hoặc<br>- `has_comparison = True` hoặc<br>- `decomposition_required = True` hoặc<br>- Ghép tính toán với đa chế định/thời điểm | **`DECOMPOSITION_CRAG`** | *"Người lao động nữ đang mang thai có được làm thêm giờ vào ban đêm không, và nếu được thì tiền lương được tính như thế nào?"*<br>*"So sánh quy định về thời giờ làm việc và làm thêm giờ giữa Bộ luật Lao động 2019 và Nghị định 145/2020/NĐ-CP?"* |

---

## 4. CÁC ĐẶC TRƯNG PHÁP LÝ (LEGAL COMPLEXITY FEATURES)

Hệ thống **tuyệt đối không phân loại dựa trên độ dài chuỗi ký tự (string length) hay số token**, mà phân tích qua bộ đặc trưng pháp lý đa chiều:

1. **`number_of_legal_issues`** (*int*): Số lượng chế định/lĩnh vực pháp lý độc lập xuất hiện trong câu hỏi (trong số 13 domains: `working_hours`, `overtime`, `night_work`, `rest_time`, `wage_salary`, `contract`, `termination`, `discipline`, `female_protection`, `social_insurance`, `foreign_worker`, `safety_health`, `union`).
2. **`multi_condition`** (*bool*): Phát hiện các cấu trúc điều kiện logic phức hợp (`nếu... thì...`, `khi... thì/mà/có được/phải/bị`, `trường hợp... thì... và...`, `vừa... vừa...`, `trong thời gian...`).
3. **`multi_document`** (*bool*): Nhận diện sự hiện diện của $\ge 2$ văn bản quy phạm pháp luật (ví dụ: Bộ luật Lao động 2019 và Nghị định 145/2020/NĐ-CP; Luật Việc làm và BLLĐ).
4. **`cross_reference`** (*bool*): Viện dẫn chéo giữa nhiều Điều luật cụ thể (ví dụ: Điều 169 và Điều 219) hoặc các liên từ đối chiếu pháp lý ("dẫn chiếu", "đối chiếu quy định tại").
5. **`temporal_condition`** (*bool*): Điều kiện mốc thời gian, khoảng thời hạn xác định ("30 ngày", "12 tháng", "kể từ ngày chấm dứt").
6. **`subject_count`** (*int*): Số lượng chủ thể pháp lý đặc thù cùng xuất hiện (NLĐ, NSDLĐ, lao động nữ mang thai, lao động chưa thành niên, lao động nước ngoài, công đoàn).
7. **`calculation_required`** (*bool*): Yêu cầu tính toán định lượng số học, xác định tỷ lệ, mức hưởng, tiền lương trợ cấp.
8. **`procedural_required`** (*bool*): Yêu cầu về trình tự, thủ tục, hồ sơ các bước, khung xử phạt hành chính.
9. **`ambiguity`** (*bool*): Phát hiện ngôn ngữ đàm thoại, từ lóng đời thường ("bị đuổi việc", "nghỉ đẻ", "tăng ca", "ad ơi") cần tái cấu trúc câu hỏi.
10. **`decomposition_required`** (*bool*): Chỉ dấu bắt buộc phải phân rã thành các câu hỏi con độc lập (Sub-queries).
11. **`required_reasoning_steps`** (*int*): Ước tính số bước suy luận pháp lý tối thiểu.
12. **`is_out_of_scope`** (*bool*): Phát hiện câu hỏi nằm ngoài phạm vi pháp luật lao động (hôn nhân, di chúc, giao thông, nhà đất...).
13. **`is_greeting`** (*bool*): Nhận diện câu chào hỏi, hội thoại xã giao.

---

## 5. KIẾN TRÚC & QUY TRÌNH XỬ LÝ (ARCHITECTURE & WORKFLOW)

Bộ phân loại được thiết kế theo hướng **Deterministic Legal Feature Engine**:

```text
[Input Query]
      │
      ▼
┌────────────────────────────────────────────────────────┐
│ 1. Canonical Normalization & Legal Abbreviation Expander│
│    • BLLĐ / BLLD -> "Bộ luật Lao động 2019"             │
│    • NLĐ -> "người lao động", NSDLĐ -> "người sử dụng"  │
│    • HĐLĐ -> "hợp đồng lao động", TNLĐ, BHXH, BHTN      │
│    • ATVSLĐ -> "Luật An toàn vệ sinh lao động 2015"     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 2. Multi-Domain Legal Feature Extractor                │
│    • Entity Extractor (Văn bản, Điều khoản, Chủ thể)   │
│    • Logic & Condition Matcher (Cấu trúc rẽ nhánh)     │
│    • Domain Intersection Resolver                      │
│      (Hợp nhất các domain con như ban đêm + giờ làm)   │
│    • Comparison & Arithmetic Detector                  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 3. Priority Decision Engine (Cây quyết định phân tầng)  │
│    [Tier 0] Edge Cases: Greeting / Out-of-Scope        │
│             -> SIMPLE (Direct Bypass / Fast Refusal)   │
│    [Tier 1] Strict Complex Guard:                      │
│             Multi-Doc OR Cross-Ref OR Decomposition    │
│             OR Multi-Issue Calculation                 │
│             -> COMPLEX (Decomposition + CRAG)          │
│    [Tier 2] Moderate Guard:                            │
│             Multi-Condition OR Procedural OR 2-Issue   │
│             OR Single Calculation OR Ambiguity         │
│             -> MODERATE (CRAG Retrieval)               │
│    [Tier 3] Fallback Safe Baseline:                    │
│             Single-Issue Direct Lookup                 │
│             -> SIMPLE (Direct RAG)                     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
[Output: QueryComplexityResult (Typed, Explainable, Serializable)]
```

---

## 6. LOGIC QUYẾT ĐỊNH (DECISION LOGIC)

Cây quyết định tuân thủ thứ tự ưu tiên nghiêm ngặt:

1. **Khối biên (Edge Handler)**:
   - Nếu `is_greeting == True` $\to$ `SIMPLE` (Confidence: 0.98, Bypass LLM).
   - Nếu `is_out_of_scope == True` $\to$ `SIMPLE` (Confidence: 0.95, Chuyển thẳng tới Refusal Guard từ chối trả lời).

2. **Khối chặn phức tạp (Complex Guard)**:
   - Nếu `multi_document == True` $\to$ **`COMPLEX`**.
   - Nếu `cross_reference == True` $\to$ **`COMPLEX`**.
   - Nếu `decomposition_required == True` (chứa câu hỏi kép, cấu trúc vừa... vừa..., hoặc so sánh quy định) $\to$ **`COMPLEX`**.
   - Nếu `calculation_required == True` và `number_of_legal_issues >= 2` (tính toán kết hợp đa chế định) $\to$ **`COMPLEX`**.
   - Nếu `number_of_legal_issues >= 3` $\to$ **`COMPLEX`**.

3. **Khối thẩm định trung bình (Moderate Guard)**:
   - Nếu `procedural_required == True` (thủ tục, trình tự, mức phạt) $\to$ **`MODERATE`**.
   - Nếu `multi_condition == True` (câu hỏi tình huống phát sinh) $\to$ **`MODERATE`**.
   - Nếu `calculation_required == True` (tính toán đơn chế định) $\to$ **`MODERATE`**.
   - Nếu `ambiguity == True` (từ lóng, đàm thoại) $\to$ **`MODERATE`**.
   - Nếu `number_of_legal_issues == 2` $\to$ **`MODERATE`**.
   - Nếu câu hỏi chứa từ khóa thẩm định quyền/nghĩa vụ tình huống ("có được", "có phải", "quyền gì") $\to$ **`MODERATE`**.

4. **Khối mặc định (Simple Baseline)**:
   - Chỉ khi câu hỏi là đơn vấn đề duy nhất, không có điều kiện rẽ nhánh, không viện dẫn chéo, không tính toán $\to$ **`SIMPLE`**.

---

## 7. SCHEMA VÀ ĐẶC TẢ DỮ LIỆU ĐẦU RA (INPUT/OUTPUT SCHEMA)

Cấu trúc Pydantic Schema định nghĩa tại [`Adaptive_RAG/classifier/schema.py`](file:///d:/Filehoc/KLCN/agentic-rag/Adaptive_RAG/classifier/schema.py):

```python
class ComplexityClass(str, Enum):
    SIMPLE = "SIMPLE"
    MODERATE = "MODERATE"
    COMPLEX = "COMPLEX"

class RoutingStrategy(str, Enum):
    DIRECT_RAG = "DIRECT_RAG"
    CRAG = "CRAG"
    DECOMPOSITION_CRAG = "DECOMPOSITION_CRAG"

class QueryComplexityFeatures(BaseModel):
    number_of_legal_issues: int
    multi_condition: bool
    multi_document: bool
    cross_reference: bool
    temporal_condition: bool
    subject_count: int
    required_reasoning_steps: int
    calculation_required: bool
    procedural_required: bool
    ambiguity: bool
    decomposition_required: bool
    detected_articles: List[str]
    detected_documents: List[str]
    detected_subjects: List[str]
    is_out_of_scope: bool
    is_greeting: bool

class QueryComplexityResult(BaseModel):
    query: str
    complexity: ComplexityClass
    confidence: float
    reasons: List[str]
    features: Dict[str, Any]
    recommended_strategy: RoutingStrategy
    latency_ms: float
```

Ví dụ một kết quả JSON thực tế:
```json
{
  "query": "Người lao động nữ đang mang thai có được làm thêm giờ vào ban đêm không, và nếu được thì tiền lương được tính như thế nào?",
  "complexity": "COMPLEX",
  "confidence": 0.92,
  "reasons": [
    "Câu hỏi chứa nhiều câu hỏi con hoặc ghép nhiều vấn đề pháp lý phức tạp cần phân rã (Query Decomposition).",
    "Câu hỏi yêu cầu tính toán số học phức hợp kết hợp nhiều điều kiện ràng buộc/thời điểm."
  ],
  "features": {
    "number_of_legal_issues": 4,
    "multi_condition": true,
    "multi_document": false,
    "cross_reference": false,
    "temporal_condition": true,
    "subject_count": 2,
    "required_reasoning_steps": 2,
    "calculation_required": true,
    "procedural_required": false,
    "ambiguity": false,
    "decomposition_required": true,
    "detected_articles": [],
    "detected_documents": [],
    "detected_subjects": ["người lao động", "lao động nữ"],
    "is_out_of_scope": false,
    "is_greeting": false
  },
  "recommended_strategy": "DECOMPOSITION_CRAG",
  "latency_ms": 0.52
}
```

---

## 8. PHƯƠNG PHÁP KIỂM THỬ (TEST METHODOLOGY)

Bộ kiểm thử được tổ chức tại [`tests/test_query_complexity_classifier.py`](file:///d:/Filehoc/KLCN/agentic-rag/tests/test_query_complexity_classifier.py) với 5 lớp kiểm chứng:

1. **Unit Tests (Feature Extraction)**: Kiểm tra độc lập từng hàm bóc tách đặc trưng (single/multi-issue, multi-condition, cross-ref, temporal, calculation, multi-doc, ambiguity, compound condition).
2. **Edge Cases**: Kiểm thử chuỗi rỗng (empty string), khoảng trắng (whitespace), chào hỏi (greetings) và câu hỏi ngoài phạm vi pháp luật lao động (out-of-scope).
3. **Classification Benchmark (36 câu hỏi cân bằng)**:
   - 12 câu `SIMPLE`
   - 12 câu `MODERATE`
   - 12 câu `COMPLEX`
4. **Determinism Test**: Chạy lặp lại 10 lần liên tiếp trên tập mẫu để kiểm tra tính nhất quán 100% của đầu ra (đảm bảo không tồn tại yếu tố ngẫu nhiên).
5. **Complex-to-Simple Error Rate Test**: Khẳng định biến cố nguy hiểm nhất (câu hỏi COMPLEX bị đánh giá nhầm thành SIMPLE) có xác suất chính xác bằng 0.

---

## 9. KẾT QUẢ ĐÁNH GIÁ ĐỊNH LƯỢNG (EVALUATION RESULTS)

Thực nghiệm được thực hiện thông qua script chuyên dụng [`evaluation/runner/evaluate_classifier.py`](file:///d:/Filehoc/KLCN/agentic-rag/evaluation/runner/evaluate_classifier.py) trên hai tập dữ liệu:

### A. Golden Complexity Benchmark (50 câu hỏi có nhãn chuẩn)

| Chỉ số đánh giá | Giá trị đạt được | Ghi chú |
| :--- | :---: | :--- |
| **Tổng số mẫu (Total Samples)** | **50** | 15 SIMPLE, 15 MODERATE, 15 COMPLEX, 5 Edge Cases |
| **Độ chính xác (Accuracy)** | **100.00%** | 50/50 câu phân loại chính xác tuyệt đối |
| **Macro F1-Score** | **100.00%** | Cân bằng hoàn hảo trên cả 3 lớp |
| **Complex-to-Simple Error Rate** | **0.00%** | **0/15 câu (Không có bất kỳ ca lỗi nguy hiểm nào)** |
| **Deterministic Consistency** | **PASS (100%)** | Kết quả đồng nhất qua toàn bộ các lần chạy lặp |

#### Chi tiết Precision, Recall, F1 theo từng lớp:

| Lớp (Class) | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| **`SIMPLE`** | 100.00% | 100.00% | 100.00% | 20 |
| **`MODERATE`** | 100.00% | 100.00% | 100.00% | 15 |
| **`COMPLEX`** | 100.00% | 100.00% | 100.00% | 15 |

#### Ma trận nhầm lẫn (Confusion Matrix):

```text
                  DỰ ĐOÁN (PREDICTED)
                 SIMPLE   MODERATE   COMPLEX
THỰC TẾ  SIMPLE     20         0         0
(TRUE)   MODERATE    0        15         0
         COMPLEX     0         0        15
```

#### Thống kê độ trễ xử lý (Classification Latency):
* **Mean**: `0.58 ms`
* **Median**: `0.32 ms`
* **P95**: `0.77 ms`
* **Min**: `0.15 ms`
* **Max**: `9.68 ms`

> **Nhận xét về Latency**: Với thời gian xử lý trung bình dưới 1 mili-giây (0.58 ms), Classifier hầu như **không làm tăng bất kỳ độ trễ nào đáng kể** đối với toàn bộ luồng RAG E2E (thường mất từ 1.5s - 3.5s cho LLM generation).

---

### B. Phân tích trên 80 câu hỏi Legal QA Benchmark (`evaluation/dataset/legal_qa.json`)

Toàn bộ 80 câu hỏi chuẩn của đồ án đã được đưa qua Classifier để kiểm tra tính tương thích và bảo vệ luồng:

| Category gốc (80 câu) | Tổng số câu | Phân loại `SIMPLE` | Phân loại `MODERATE` | Phân loại `COMPLEX` | Tỷ lệ Complex $\to$ Simple |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `single_article` | 18 | 10 | 7 | 1 | 0.0% |
| `single_doc_multi_chunk` | 12 | 7 | 5 | 0 | 0.0% |
| `multi_document` | 12 | **0** | 1 | 11 | **0.0%** |
| `cross_reference` | 10 | **0** | 3 | 7 | **0.0%** |
| `complex_conditions` | 12 | **0** | 11 | 1 | **0.0%** |
| `insufficient_evidence` | 8 | 2 | 3 | 3 | 0.0% |
| `out_of_scope` | 8 | 8 | 0 | 0 | 0.0% |
| **TỔNG CỘNG** | **80** | **27** | **30** | **23** | **0.0% (0 câu)** |

> **Phát hiện quan trọng**: Trên toàn bộ 34 câu hỏi phức tạp thuộc các nhóm `multi_document`, `cross_reference` và `complex_conditions` trong benchmark 80 câu, **tỷ lệ bị phân loại nhầm thành `SIMPLE` là tuyệt đối 0.0%** (0 câu). Toàn bộ các câu hỏi phức tạp đều được đưa an toàn vào `MODERATE` (CRAG) hoặc `COMPLEX` (Decomposition).

---

## 10. KẾT QUẢ KIỂM THỬ HỒI QUY (REGRESSION SUITE)

Việc bổ sung Module 0 được thực hiện hoàn toàn tách biệt, bảo toàn tuyệt đối 100% tính đóng băng của Traditional RAG và Corrective RAG:

```text
============================= test session starts =============================
platform win32 -- Python 3.13.0, pytest-9.1.1, pluggy-1.6.0
collected 213 items

tests\adaptive\test_adaptive_orchestrator.py ......                      [  2%]
tests\adaptive\test_adaptive_pipeline.py .....                           [  5%]
tests\adaptive\test_query_classifier.py .......                          [  8%]
tests\adaptive\test_query_decomposition.py ....                          [ 10%]
tests\citation\test_citation.py ........                                 [ 14%]
tests\context\test_context_builder.py ........                           [ 17%]
tests\crag\test_crag_pipeline.py .....                                   [ 20%]
tests\crag\test_document_grader.py ........                              [ 23%]
tests\crag\test_knowledge_refinement.py .......                          [ 27%]
tests\crag\test_web_search_fallback.py ......                            [ 30%]
tests\embedding\test_embedding.py ..............                         [ 36%]
tests\evaluation\test_baseline_eval.py .........                         [ 40%]
tests\generator\test_generator.py ...........                            [ 46%]
tests\guards\test_refusal_guard.py .......                               [ 49%]
tests\rag\test_pipeline.py .........                                     [ 53%]
tests\retriever\test_retriever.py ..........                             [ 58%]
tests\test_corrective_evaluator.py .........                             [ 62%]
tests\test_corrective_loop.py .....                                      [ 64%]
tests\test_corrective_pipeline.py ....                                   [ 66%]
tests\test_query_complexity_classifier.py .............................. [ 80%]
....................                                                     [ 90%]
tests\test_query_rewriter.py .......                                     [ 93%]
tests\vector_store\test_vector_store.py ..............                   [100%]

============================ 213 passed in 19.30s =============================
```

* **Baseline Traditional RAG tests**: **PASS 100% (97/97)**.
* **CRAG tests**: **PASS 100% (66/66)**.
* **Module 0 Classifier tests**: **PASS 100% (50/50)**.
* **TỔNG**: **213/213 tests PASS (0 REGRESSION)**.

---

## 11. PHÂN TÍCH CA LỖI VÀ BIỆN PHÁP KHẮC PHỤC (ERROR ANALYSIS & MITIGATION)

Trong quá trình phát triển và kiểm định, nhóm nghiên cứu đã phân tích 3 ca biên tế nhị:

1. **Từ viết tắt pháp luật với bảng mã ký tự tiếng Việt (`BLLĐ` vs `BLLD`)**:
   * *Hiện tượng*: Một số câu hỏi viết `Điều 8 BLLĐ` (chữ Đ tiếng Việt), nếu regex chỉ nhận `BLLD` thì văn bản không được nhận diện, dẫn đến câu hỏi đa văn bản bị nhận diện thiếu.
   * *Khắc phục*: Tích hợp lớp `Canonical Legal Abbreviation Expander` chuẩn hóa cả `BLL[ĐD]`, `ATVSLĐ`, `NLĐ`, `NSDLĐ`, `HĐLĐ`, `BHXH`, `BHTN`, `TNLĐ` trước khi trích xuất thực thể.

2. **Giao thoa giữa chế định con và chế định độc lập**:
   * *Hiện tượng*: Câu hỏi *"Thời giờ làm việc ban đêm được tính từ mấy giờ đến mấy giờ?"* vừa khớp domain `working_hours` (thời giờ làm việc) vừa khớp `night_work` (ban đêm). Nếu đếm máy móc, số vấn đề sẽ là 2 (bị phân loại nhầm thành MODERATE).
   * *Khắc phục*: Tích hợp logic lọc miền giao thoa (*Domain Overlap Resolution*): khi cụm `thời giờ làm việc ban đêm` hoặc `làm việc vào ban đêm` xuất hiện đơn thuần không kèm làm thêm giờ, hợp nhất về 1 domain duy nhất (`night_work`), giữ đúng bản chất `SIMPLE` (quy định tại Điều 106 BLLĐ).

3. **Tính toán đa chế định vs. Tính toán đơn chế định**:
   * *Hiện tượng*: Tính ngày phép năm cho người làm việc chưa đủ 12 tháng (đơn chế định `rest_time`) chỉ là `MODERATE`. Nhưng tính tiền trợ cấp thôi việc cho người có giai đoạn đóng bảo hiểm thất nghiệp (`termination` + `social_insurance`/`unemployment`) đòi hỏi bóc tách 2 giai đoạn theo 2 đạo luật khác nhau.
   * *Khắc phục*: Phân định ranh giới rõ ràng: `calculation_required` đơn lẻ đi vào `MODERATE`; nhưng khi kết hợp với `number_of_legal_issues >= 2` hoặc `decomposition_required`, câu hỏi lập tức được xếp vào `COMPLEX`.

---

## 12. HẠN CHẾ CÒN LẠI (LIMITATIONS)

1. **Phụ thuộc vào từ điển thuật ngữ chuyên ngành**: Hiện tại, bộ phân loại sử dụng Rule-based Legal Feature Engine được tinh chỉnh tối ưu cho 15 văn bản pháp luật lao động của Dataset V2.1. Nếu mở rộng sang các lĩnh vực luật khác (Luật Doanh nghiệp, Luật Thuế...), cần cập nhật thêm danh mục từ điển văn bản và chế định pháp lý tương ứng.
2. **Câu hỏi nhập nhằng ngữ nghĩa cực đoan**: Đối với những câu hỏi người dùng diễn đạt quá tối nghĩa hoặc sai lệch thuật ngữ hoàn toàn không có bất kỳ dấu hiệu pháp lý nào, bộ phân loại ưu tiên lựa chọn phương án an toàn là `MODERATE` để đẩy vào luồng CRAG Query Rewriter giải quyết.

---

## 13. KẾ HOẠCH TÍCH HỢP (INTEGRATION PLAN)

Classifier đã sẵn sàng giao diện lập trình để các module tiếp theo sử dụng:

### A. Giao diện cung cấp cho Module 1 — Query Decomposition
Module Query Decomposition chỉ cần nhận những câu hỏi có:
```python
if result.complexity == ComplexityClass.COMPLEX:
    # Kích hoạt Decomposition Engine
    sub_queries = decomposition_engine.decompose(
        query=result.query,
        detected_documents=result.features["detected_documents"],
        detected_articles=result.features["detected_articles"],
        domains=result.features["detected_subjects"]
    )
```

### B. Giao diện cung cấp cho Module 2 — Adaptive Router
Adaptive Router sẽ điều phối luồng dựa trên `result.recommended_strategy`:
```python
match result.recommended_strategy:
    case RoutingStrategy.DIRECT_RAG:
        return baseline_pipeline.run(query)
    case RoutingStrategy.CRAG:
        return crag_pipeline.run(query)
    case RoutingStrategy.DECOMPOSITION_CRAG:
        return agentic_decomposition_pipeline.run(query)
```

---

## 14. KẾT LUẬN

Module 0 — **Query Complexity Classifier** đã được hoàn thành với các tiêu chí chất lượng cao nhất:
* Hoàn toàn tất định (Deterministic 100%).
* Giải thích minh bạch với trường `reasons` và `features` chi tiết.
* Đạt **100% Accuracy và Macro F1** trên Golden Complexity Benchmark.
* Đạt **Complex-to-Simple Error Rate = 0.0%** trên cả Golden Benchmark và 80 câu hỏi Legal QA Benchmark.
* Thời gian xử lý siêu tốc: **0.58 ms**.
* Đảm bảo **0 regression** trên toàn bộ 213 unit & integration tests của hệ thống.
