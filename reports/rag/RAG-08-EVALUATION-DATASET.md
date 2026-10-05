# BÁO CÁO RAG-08: XÂY DỰNG BỘ DỮ LIỆU ĐÁNH GIÁ PHÁP LUẬT LAO ĐỘNG (LEGAL RAG EVALUATION BENCHMARK)

---

## 1. TỔNG QUAN NHIỆM VỤ

Bộ dữ liệu đối chuẩn (Evaluation Benchmark) RAG-08 được thiết kế và xây dựng độc lập, khách quan nhằm phục vụ việc đánh giá hiệu năng thu hồi và tạo sinh của mô hình **Traditional RAG Baseline**, đồng thời được cố định (frozen) để tái sử dụng xuyên suốt cho các hệ thống tiếp theo:
* **Traditional RAG Baseline**
* **Corrective RAG (CRAG)**
* **Adaptive Agentic RAG**

Theo tôn chỉ của dự án:
1. **Không thay đổi benchmark giữa các hệ thống** (đảm bảo tính công bằng và so sánh khoa học).
2. **Không dùng câu hỏi tự sinh (synthetic) mà không kiểm chứng nguồn pháp lý**.
3. **100% căn cứ pháp lý vàng (Gold Sources) phải truy vết chính xác tới chunk_id trong Dataset V2.1**.

---

## 2. QUY CÁCH VÀ CẤU TRÚC DỮ LIỆU

### 2.1. File cấu trúc
```text
evaluation/
├── dataset/
│   ├── schema.json          # JSON Schema Draft-07 chuẩn hóa dữ liệu benchmark
│   └── legal_qa.json        # Bộ dữ liệu 80 câu hỏi kiểm định chất lượng cao
└── tests/
    └── test_dataset.py      # Test suite kiểm tra schema, traceability, coverage, no-duplicates
```

### 2.2. Schema chuẩn của mỗi câu hỏi (`evaluation/dataset/schema.json`)
```json
{
  "question_id": "Q001",
  "question": "Người sử dụng lao động có được đơn phương chấm dứt hợp đồng lao động khi người lao động đang mang thai không?",
  "category": "single_article",
  "gold_sources": [
    {
      "document_id": "BLLD_2019",
      "article_number": "Điều 137",
      "chunk_ids": [
        "BLLD_2019_Điều137_c1"
      ]
    }
  ],
  "reference_answer": "Căn cứ Điều 137 Bộ luật Lao động 2019, người sử dụng lao động không được thực hiện quyền đơn phương chấm dứt hợp đồng lao động đối với người lao động vì lý do kết hôn, mang thai, nghỉ thai sản, nuôi con dưới 12 tháng tuổi...",
  "requires_refusal": false
}
```

---

## 3. PHÂN BỐ DANH MỤC CÂU HỎI (QUESTION CATEGORIES)

Bộ dữ liệu gồm **80 câu hỏi** (vượt chỉ tiêu tối thiểu 50 câu, đạt mục tiêu khuyến nghị 80 câu), phân bổ toàn diện trên 7 danh mục:

| Nhóm | Tên Danh Mục | Số Lượng | Tỷ Lệ (%) | Yêu Cầu Từ Chối (`requires_refusal`) | Mục Đích Đánh Giá Đối Chuẩn |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **A** | `single_article` | 18 | 22.5% | `False` | Khả năng thu hồi chính xác 1 Điều luật duy nhất giải đáp trọn vẹn câu hỏi. |
| **B** | `single_doc_multi_chunk` | 12 | 15.0% | `False` | Khả năng thu hồi nhiều chunk thuộc cùng một văn bản (khác Điều hoặc cùng Điều dài). |
| **C** | `multi_document` | 12 | 15.0% | `False` | Khả năng thu hồi kết hợp giữa Bộ luật Lao động 2019 với Nghị định / Thông tư hướng dẫn. |
| **D** | `cross_reference` | 10 | 12.5% | `False` | Khả năng xử lý mối quan hệ dẫn chiếu, viện dẫn giữa các điều khoản khác nhau. |
| **E** | `complex_conditions` | 12 | 15.0% | `False` | Câu hỏi tình huống phức tạp đòi hỏi tổng hợp nhiều điều kiện pháp lý để kết luận. |
| **F** | `insufficient_evidence` | 8 | 10.0% | `True` | Câu hỏi thuộc lĩnh vực lao động nhưng nội dung hoặc chi tiết không có trong Corpus V2.1 (yêu cầu từ chối trung thực). |
| **G** | `out_of_scope` | 8 | 10.0% | `True` | Câu hỏi hoàn toàn ngoài phạm vi luật lao động (Luật Hàng không, Giao thông, v.v.) (yêu cầu từ chối an toàn). |
| **TỔNG** | **7 Danh Mục** | **80** | **100%** | **16 / 80 (20.0%)** | **Toàn diện mọi góc độ RAG** |

---

## 4. CHẤT LƯỢNG VÀ TÍNH TRUY VẾT CỦA CĂN CỨ VÀNG (GOLD SOURCES)

* **Tổng số văn bản nguồn bao phủ**: Toàn bộ 15/15 văn bản pháp quy trong Dataset V2.1 (`BLLD_2019`, `ND_145_2020`, `ND_12_2022`, `ND_135_2020`, `ND_152_2020`, `ND_219_2025`, `ND_70_2023`, `ND_74_2024`, `ND_83_2022`, `ND_99_2024`, `QD_992_2025`, `TT_09_2020`, `TT_10_2020`, `TT_11_2020`, `TT_20_2023`).
* **Tổng số chunk tham chiếu vàng**: **295 chunks**.
* **Độ bao phủ trung bình**: **4.61 chunks / câu hỏi** có câu trả lời.
* **Tỷ lệ truy vết thành công (Traceability Rate)**: **100.0%** (295/295 chunk IDs đều tồn tại chính xác trong `Data_Processing/output_v2/legal_dataset_v2.json`).
* **Tính độc lập và duy nhất**:
  * Trùng lặp `question_id`: **0**.
  * Trùng lặp nội dung câu hỏi: **0**.

---

## 5. KẾT QUẢ KIỂM THỬ TỰ ĐỘNG (UNIT TESTING)

Đã xây dựng và thực thi bộ kiểm thử tự động `evaluation/tests/test_dataset.py`:
1. `test_schema_conformance`: Xác thực tính hợp chuẩn cấu trúc JSON Schema Draft-07 (PASS).
2. `test_dataset_size`: Xác thực kích thước dataset >= 50 câu (PASS - 80 câu).
3. `test_all_categories_represented`: Xác thực sự hiện diện đầy đủ của cả 7 categories (PASS).
4. `test_gold_sources_traceability`: Xác thực 100% `chunk_id` có trong Dataset V2.1 (PASS).
5. `test_refusal_questions_policy`: Xác thực nhóm F & G bắt buộc `requires_refusal=True` và có thông điệp từ chối chuẩn (PASS).
6. `test_unique_ids_and_questions`: Xác thực không trùng lặp ID hay văn bản câu hỏi (PASS).
7. `test_quality_and_field_integrity`: Kiểm tra độ dài, trường hợp chuỗi rỗng và kiểu dữ liệu (PASS).

Kết quả: **7/7 tests PASS (0.065s)**. Đồng thời toàn bộ **81/81 regression tests** của hệ thống RAG tiếp tục duy trì trạng thái **PASS (100%)**.

---

## 6. KẾT LUẬN

Bộ dữ liệu đánh giá đối chuẩn RAG-08 đã hoàn thành xuất sắc, sẵn sàng làm cơ sở khoa học để đánh giá:
1. Retrieval performance trong RAG-09 (Dense Retriever).
2. Generation performance trong RAG-10 (Traditional RAG Baseline).
3. Benchmark so sánh đa hệ thống cho CRAG và Adaptive Agentic RAG trong các giai đoạn tiếp theo.
