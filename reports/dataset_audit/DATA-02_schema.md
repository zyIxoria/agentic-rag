# THIẾT KẾ SCHEMA LEGAL DATASET V2 — TASK DATA-02
**Dự án:** Nghiên cứu cơ chế điều phối thích ứng trong hệ thống Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam  
**Mục tiêu:** Thiết kế và kiểm chuẩn Schema V2 tiêu chuẩn cho dữ liệu pháp luật lao động Việt Nam, khắc phục triệt để các khiếm khuyết của Dataset V1.  
**Thời điểm thực hiện:** 09/09/2026  
**Trạng thái kiểm thử:** 12/12 Unit Tests PASSED. Dataset V1 giữ nguyên vẹn 100%.

---

## 1. Nguyên tắc thiết kế cốt lõi (Core Design Principles)

Schema Legal Dataset V2 được xây dựng dựa trên 6 nguyên tắc lập pháp và kỹ thuật RAG:

1. **Bảo toàn đầy đủ cấu trúc lập pháp 6 cấp (Full Legal Hierarchy Preservation):**  
   $$\text{Văn bản} \longrightarrow \text{Chương} \longrightarrow \text{Mục} \longrightarrow \text{Điều} \longrightarrow \text{Khoản} \longrightarrow \text{Điểm}$$
   Khắc phục điểm mù của V1 vốn hoàn toàn bỏ sót cấp "Mục" (Section) và cấp "Điểm" (Point).

2. **Không ép buộc trường không tồn tại (Zero Mandatory Hallucination):**  
   Các văn bản không có Chương (như Thông tư, Quyết định), Điều không chia Khoản, hoặc Khoản không chia Điểm sẽ nhận giá trị `null`. Hệ thống **không được tự bịa** các chuỗi giả lập như `"Chưa xác định"`, `"0"`, `"Đã biết"` như ở V1.

3. **Từ chối dứt khoát dữ liệu sai (Fail-Fast Validation):**  
   Mọi bản ghi thiếu thông tin bắt buộc (`chunk_id`, `document_id`, `document_title`, `content`, `parent_document`, `chunk_index`) hoặc vi phạm phân cấp logic (như có Điểm nhưng không có Điều/Khoản) sẽ bị ném lỗi `ValidationError` ngay lập tức, không âm thầm sửa sai (no silent corruption).

4. **Hỗ trợ chuyên biệt cho Phụ lục & Bảng biểu (First-class Appendix & Table/Form Support):**  
   Các bảng danh mục lớn (như danh mục nghề nặng nhọc của Thông tư 11/2020) và biểu mẫu hành chính (Nghị định 152/2020, 219/2025) được gán `content_type` (`table`, `form`, `appendix`) và liên kết trực tiếp tới văn bản mẹ mà không bị gán ép vào Điều luật trước đó.

5. **Giải quyết triệt để vấn đề đụng độ ID (Globally Unique Primary Key):**  
   `chunk_id` là khóa chính duy nhất toàn cục, bảo đảm an toàn 100% khi upsert vào bất kỳ Vector Database nào (Chroma, Qdrant, Milvus, Weaviate).

6. **Bảo toàn liên kết ngữ cảnh (Parent-Child Traceability):**  
   Các trường `parent_document` và `parent_article` cho phép tái tạo cây phả hệ pháp lý, phục vụ kỹ thuật Parent-Document Retrieval hoặc Hierarchical Retrieval trong Corrective RAG.

---

## 2. Đặc tả 21 trường chuẩn của Schema V2 (21-Field Specification)

Mỗi chunk V2 xuất ra tệp JSON tuân thủ chính xác 21 trường cốt lõi:

```json
{
  "chunk_id": "BLLD_2019_C3_S1_D13_K1",
  "document_id": "BLLD_2019",
  "document_number": "45/2019/QH14",
  "document_title": "Bộ luật Lao động 2019",
  "document_type": "Bộ luật",

  "chapter_number": "Chương III",
  "chapter_title": "Hợp đồng lao động",

  "section_number": "Mục 1",
  "section_title": "Giao kết hợp đồng lao động",

  "article_number": "Điều 13",
  "article_title": "Hợp đồng lao động",

  "clause_number": "Khoản 1",
  "point_number": null,

  "content": "1. Hợp đồng lao động là sự thỏa thuận giữa người lao động và người sử dụng lao động về việc làm có trả công, tiền lương, điều kiện lao động, quyền và nghĩa vụ của mỗi bên trong quan hệ lao động. Trường hợp hai bên thỏa thuận bằng tên gọi khác nhưng có nội dung thể hiện về việc làm có trả công, tiền lương và sự quản lý, điều hành, giám sát của một bên thì vẫn được coi là hợp đồng lao động.",

  "effective_from": "2021-01-01",
  "effective_to": null,
  "legal_status": "Còn hiệu lực",

  "source_url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-Luat-lao-dong-2019-333670.aspx",

  "parent_document": "BLLD_2019",
  "parent_article": "BLLD_2019_Điều13",

  "chunk_index": 46
}
```

### Bảng chi tiết 21 trường:

| STT | Tên trường (Field Name) | Kiểu dữ liệu | Nullable? | Ràng buộc & Quy tắc xác thực | Ví dụ giá trị |
| :---: | :--- | :---: | :---: | :--- | :--- |
| 1 | `chunk_id` | `string` | **NO** | Bắt buộc, độ dài $\ge 3$, không trùng lặp trong toàn bộ dataset. | `"BLLD_2019_C3_D13_K1"` |
| 2 | `document_id` | `string` | **NO** | Bắt buộc, mã định danh chuẩn của văn bản. | `"BLLD_2019"`, `"ND_12_2022"` |
| 3 | `document_number` | `string` | **YES** | Số hiệu văn bản chính thức. `null` nếu không xác định. | `"45/2019/QH14"`, `"12/2022/NĐ-CP"` |
| 4 | `document_title` | `string` | **NO** | Bắt buộc, tên gọi đầy đủ chính thức của văn bản. | `"Bộ luật Lao động 2019"` |
| 5 | `document_type` | `string` | **YES** | Loại văn bản pháp quy: Luật, Nghị định, Thông tư... | `"Bộ luật"`, `"Nghị định"` |
| 6 | `chapter_number` | `string` | **YES** | Số thứ tự chương (Chương I, II...). `null` nếu không có. | `"Chương III"` |
| 7 | `chapter_title` | `string` | **YES** | Tiêu đề chương. `null` nếu không có. | `"Hợp đồng lao động"` |
| 8 | `section_number` | `string` | **YES** | Số thứ tự mục (Mục 1, 2...). `null` nếu không có. | `"Mục 1"` |
| 9 | `section_title` | `string` | **YES** | Tiêu đề mục. `null` nếu không có. | `"Giao kết hợp đồng lao động"` |
| 10 | `article_number` | `string` | **YES** | Số thứ tự điều (Điều 1, 2...). `null` nếu là phụ lục độc lập. | `"Điều 13"`, `"Điều 124"` |
| 11 | `article_title` | `string` | **YES** | Tiêu đề điều luật. `null` nếu không có. | `"Hình thức xử lý kỷ luật lao động"` |
| 12 | `clause_number` | `string` | **YES** | Số thứ tự khoản (Khoản 1, 2...). `null` nếu không chia khoản. | `"Khoản 1"`, `"Khoản 4"` |
| 13 | `point_number` | `string` | **YES** | Ký hiệu điểm (Điểm a, b...). `null` nếu không chia điểm. | `"Điểm a"`, `"Điểm đ"` |
| 14 | `content` | `string` | **NO** | Bắt buộc, text nội dung quy phạm, bảng biểu hoặc mẫu đơn. | `"4. Sa thải."` |
| 15 | `effective_from` | `string` | **YES** | Ngày bắt đầu hiệu lực (YYYY-MM-DD hoặc DD/MM/YYYY). | `"2021-01-01"` |
| 16 | `effective_to` | `string` | **YES** | Ngày hết hiệu lực. Mặc định `null` khi còn hiệu lực. | `null` |
| 17 | `legal_status` | `string` | **YES** | Trạng thái hiệu lực (Còn hiệu lực, Hết hiệu lực...). | `"Còn hiệu lực"` |
| 18 | `source_url` | `string` | **YES** | Đường dẫn URL chính thức nguồn crawl dữ liệu. | `"https://thuvienphapluat.vn/..."` |
| 19 | `parent_document` | `string` | **NO** | Bắt buộc, mã liên kết tới văn bản nguồn. | `"BLLD_2019"` |
| 20 | `parent_article` | `string` | **YES** | Mã liên kết tới điều cha. `null` nếu là phụ lục riêng. | `"BLLD_2019_Điều13"` |
| 21 | `chunk_index` | `integer` | **NO** | Bắt buộc, số nguyên $\ge 0$, thứ tự xuất hiện trong văn bản. | `0`, `1`, `46`, `205` |

---

## 3. Các trường hợp cấu trúc đặc thù (Special Structural Cases)

### 3.1. Văn bản không chia Chương (Article without Chapter)
Nhiều Thông tư (như Thông tư 10/2020/TT-BLĐTBXH) hoặc Quyết định không có Chương mà đi trực tiếp vào các Điều luật:
- `chapter_number`: `null`
- `chapter_title`: `null`
- `section_number`: `null`
- `section_title`: `null`
- `article_number`: `"Điều 3"`
- `parent_article`: `"TT_10_2020_Điều3"`

### 3.2. Khoản không chia Điểm (Clause without Point)
Một Khoản luật chỉ có một đoạn văn hoàn chỉnh không phân nhánh điểm a, b, c:
- `clause_number`: `"Khoản 3"`
- `point_number`: `null`

### 3.3. Chunk thuộc Phụ lục độc lập (Appendix)
Giải quyết triệt để lỗi "Monster Chunk" của TT 11/2020 và các biểu mẫu của NĐ 152/2020:
- `article_number`: `null`
- `article_title`: `null`
- `clause_number`: `null`
- `point_number`: `null`
- `parent_article`: `null`
- `parent_document`: `"TT_11_2020"`
- `content_type` (extension): `"appendix"` hoặc `"table"`
- `appendix_number` (extension): `"Phụ lục I"`

### 3.4. Chunk định dạng Bảng biểu (Table) & Biểu mẫu (Form)
- Nội dung `content` được chuẩn hóa dưới dạng bảng Markdown:
  ```markdown
  | STT | Tên nghề, công việc | Đặc điểm điều kiện lao động |
  | --- | ------------------- | --------------------------- |
  | 1   | Khai thác than hầm lò| Nơi làm việc chật hẹp, thiếu dưỡng khí |
  ```
- `content_type`: `"table"` hoặc `"form"`.

### 3.5. Các Chunks thuộc cùng một Điều luật
Khi một Điều dài được chia thành nhiều chunk (theo từng Khoản hoặc theo kích thước token):
- Các chunks chia sẻ chung `document_id`, `article_number`, `article_title`, và `parent_article`.
- Các chunks phân biệt nhau qua `clause_number`, `chunk_id`, và có `chunk_index` tăng dần liên tục:
  - `chunk_index`: `200` $\rightarrow$ Khoản 1
  - `chunk_index`: `201` $\rightarrow$ Khoản 2
  - `chunk_index`: `202` $\rightarrow$ Khoản 3
  - `chunk_index`: `203` $\rightarrow$ Khoản 4

---

## 4. Cơ chế Xác thực & Chống Suy diễn (Validation & Anti-Hallucination)

### 4.1. Chuẩn hóa tự động các giá trị rác thành `null`
Hàm `sanitize_null()` trong `models_v2.py` phát hiện danh sách các chuỗi rác đã gây lỗi ở V1 và chuyển đổi về `None` (`null` trong JSON):
```python
NULL_PLACEHOLDERS = {
    "chưa xác định", "chưa có", "đã biết", "không rõ",
    "n/a", "none", "null", "undefined", "unknown", "0", ""
}
```
*Kết quả:* Khi crawler trả về `"Đã biết"` cho trạng thái hiệu lực hoặc `"Chưa xác định"` cho chương, Schema V2 sẽ ghi nhận chính xác là `null`, bảo đảm không đưa dữ liệu giả thuyết vào retrieval.

### 4.2. Từ chối bản ghi không hợp lệ (Fail-Fast Exceptions)
- Thiếu `chunk_id`, `document_id`, `document_title`, `content`, `parent_document` $\rightarrow$ Báo lỗi `ValidationError` kèm tên trường cụ thể.
- `content` chỉ chứa toàn khoảng trắng (`"   "`) $\rightarrow$ Báo lỗi.
- `chunk_index` âm hoặc không thể ép kiểu sang số nguyên $\rightarrow$ Báo lỗi.
- Vi phạm thứ bậc: có `point_number` (Điểm) nhưng không có cả `clause_number` lẫn `article_number` $\rightarrow$ Báo lỗi logic phân cấp `validate_hierarchy_consistency`.

---

## 5. Kết quả Kiểm thử Đơn vị (Unit Test Results)

Tệp kiểm thử: [`Data_Processing/test_schema_v2.py`](file:///d:/Filehoc/KLCN/agentic-rag/Data_Processing/test_schema_v2.py)

```text
======================================================================
TEST EXECUTION SUMMARY (Python 3.13 / unittest)
----------------------------------------------------------------------
test_01_full_article_chunk ................................... [PASS]
test_02_article_without_chapter .............................. [PASS]
test_03_clause_without_point ................................. [PASS]
test_04_point_level_chunk .................................... [PASS]
test_05_appendix_chunk ....................................... [PASS]
test_06_table_and_form_support ............................... [PASS]
test_07_chunks_belonging_to_same_article ..................... [PASS]
test_08_missing_metadata_normalized_to_null .................. [PASS]
test_09_invalid_records_rejected ............................. [PASS]
test_10_dataset_duplicate_id_detection ....................... [PASS]
test_11_target_dictionary_keys ............................... [PASS]
test_12_json_serialization_produces_literal_null ............. [PASS]
----------------------------------------------------------------------
Ran 12 tests in 0.002s — OK (100% Passed)
======================================================================
```

---

## 6. Đối chiếu So sánh Dataset V1 vs. Schema V2

| Tiêu chí | Dataset V1 (Hiện tại) | Schema V2 (Mới thiết kế) | Cải tiến mang lại |
| :--- | :--- | :--- | :--- |
| **Số trường metadata** | 7 trường phẳng | 21 trường chuẩn hóa | Bổ sung đầy đủ Mục, Điểm, Ngày hiệu lực, URL nguồn |
| **Phân cấp Mục (Section)** | Hoàn toàn MISSING | Có trường `section_number`, `section_title` | Cho phép lọc và định danh quy định theo Mục |
| **Phân cấp Điểm (Point)** | Hoàn toàn MISSING | Có trường `point_number` | Trích xuất chính xác đến Điểm a, b, c của từng Khoản |
| **Xử lý khi thiếu thông tin** | Bịa chuỗi `"Chưa xác định"`, `"0"` | Gán `null` (None) chuẩn | Không làm nhiễu hệ thống tính vector tương đồng |
| **Trùng lặp khóa ID** | 117 mã trùng (15.70% chunks) | Khóa `chunk_id` độc nhất toàn cục | Không bị mất dữ liệu khi upsert Vector Database |
| **Hỗ trợ Phụ lục / Bảng biểu** | Dồn vào Khoản trước (507k ký tự) | Phân tách độc lập, có `content_type` | Loại bỏ hoàn toàn lỗi Monster Chunk |
| **Liên kết phân cấp (Lineage)** | Không có liên kết cha-con | `parent_document`, `parent_article` | Sẵn sàng cho Corrective RAG & Hierarchical Search |
| **Kiểm chuẩn dữ liệu (Validation)** | Không có validation | Pydantic V2 Model validation | Ngăn chặn dữ liệu bẩn ngay từ khâu nạp |

---

## 7. Xác nhận Tính toàn vẹn Dataset V1

Sau khi tạo các tệp `models_v2.py`, `schema_v2.py`, `test_schema_v2.py` và báo cáo `DATA-02_schema.md`:

```text
Kiểm tra checksum Dataset V1 (KhoaLuan_Data_HoanChinh.json):
- File size:   2,781,988 bytes (Khớp 100%)
- SHA-256:     7bdb170543734804c64945a02d5388a32399dd391ff3b2a3d029add1d3fe3fb4 (Khớp 100%)
- Trạng thái:  Dataset V1 HOÀN TOÀN KHÔNG BỊ SỬA ĐỔI.
```
