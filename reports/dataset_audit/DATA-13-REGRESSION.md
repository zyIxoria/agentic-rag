# DATA-13 REGRESSION REPORT: FIX ARTICLE FALSE-MERGE & APPENDIX BOUNDARY

* **Task ID**: `DATA-13`
* **Target**: Legal Dataset V2 (`output_v2/legal_dataset_v2.json`, `output_v2/legal_dataset_v2.jsonl`)
* **Version**: `Dataset V2.1`
* **Status**: `PASS`
* **Auditor**: Antigravity AI Pair Programmer
* **Date**: September 9, 2026

---

## 1. Executive Summary

Trong đợt đánh giá toàn diện `DATA-V2-AUDIT`, hệ thống đã phát hiện 3 lỗi BLOCKING nghiêm trọng về false-merge Điều luật, 1 lỗi MEDIUM về ranh giới phụ lục sai khiến Điều 13 Thông tư 09/2020 bị biến thành phụ lục, và 2 vấn đề LOW về ghost heading / micro table-header chunks.

Task `DATA-13` đã giải quyết triệt để tận gốc (root cause) toàn bộ các lỗi trên theo đúng nguyên tắc cấu trúc lập pháp Việt Nam:
1. **Article Heading có ưu tiên tuyệt đối trước citation/reference detection**. Bất kỳ Điều luật nào có định dạng tiêu đề hợp lệ và/hoặc có nội dung/khoản luật sẽ không bao giờ bị merge vào Điều trước đó, ngay cả khi tiêu đề chứa các từ như "áp dụng", "quy định", "thực hiện".
2. **Ranh giới Phụ lục (Appendix Boundary) được bảo vệ bằng cấu trúc tiến (Structural Forward Look-ahead)**: Việc viện dẫn văn bản hoặc phụ lục trong thân điều khoản (in-text citation) tuyệt đối không được kích hoạt mở một Appendix mới khi văn bản luật vẫn còn các Chương/Điều luật tiếp theo.
3. **Ghost headings từ ngắt dòng crawler và micro table-headers** đã được xử lý triệt để mà không làm mất bất kỳ ký tự văn bản pháp luật nào.

Kết quả rebuild `Dataset V2.1`:
* **0 ID Collisions** (1,390/1,390 unique chunk IDs).
* **0 Monster Chunks** (> 800 tokens).
* **100% Deterministic Rebuild** (SHA-256 hoàn toàn trùng khớp qua nhiều lần build độc lập).
* **100% Tests Passing** (130/130 unit và regression tests).

---

## 2. Root Cause Analysis

### 2.1. Lỗi False-Merge Điều luật (Điều 125 BLLĐ, Điều 85 NĐ 145, Điều 6 NĐ 219)
* **Nguyên nhân gốc rễ**: Trong `chunker_v2.py`, phương thức `_is_citation_article()` kiểm tra regex `self.re_ref_suffix.match(title)`. Biểu thức này chứa các từ khóa như `áp\s+dụng\b` và `quy\s+định\b`.
* **Hệ quả**:
  * Điều 125 BLLĐ 2019 có tiêu đề *"Áp dụng hình thức xử lý kỷ luật sa thải"*, khớp với `áp dụng`.
  * Điều 85 NĐ 145/2020 có tiêu đề *"Quy định của người sử dụng lao động..."*, khớp với `quy định`.
  * Điều 6 NĐ 219/2025 có tiêu đề *"Quy định về giao dịch điện tử..."*, khớp với `quy định`.
  * `_is_citation_article()` trả về `True`, kích hoạt khối gộp (merge) toàn bộ nội dung của các Điều này vào chunk của Điều trước đó (Điều 124, Điều 84, Điều 5).
* **Giải pháp khắc phục**: Thiết lập nguyên tắc cấu trúc: Một `ArticleBlock` có tiêu đề hợp lệ và/hoặc có các khoản luật (`art_node.clauses`) được xác định là Điều luật thực tế (`Real Article`), lập tức trả về `False` trong `_is_citation_article()`, nghiêm cấm merge. Đồng thời bổ sung `is_real_article_heading()` trong `hierarchy_parser.py` để thẩm định cấu trúc đầu dòng ngay từ tầng phân cấp.

### 2.2. Lỗi Nhận diện sai Ranh giới Phụ lục (Điều 13 TT 09/2020)
* **Nguyên nhân gốc rễ**: Trong `hierarchy_parser.py`, phương thức `is_appendix_start()` chỉ kiểm tra dòng bắt đầu bằng `Phụ lục I` mà không thẩm định cấu trúc câu văn và cấu trúc toàn văn. Tại Điều 12 Khoản 1 của `TT_09_2020.txt`, dòng 317 bắt đầu bằng: *"Phụ lục I ban hành kèm theo Thông tư này..."*.
* **Hệ quả**: Parser ngắt dòng 317 thành điểm mở đầu của Appendix, cắt toàn bộ phần còn lại của Thông tư (bao gồm Chương V và Điều 13 *"Hiệu lực thi hành"*) vào `appendix_lines`. Do đó Điều 13 bị phân loại thành `content_type = appendix` và `article_number = null`.
* **Giải pháp khắc phục**:
  1. Thêm bộ lọc vị ngữ/liên từ trên cùng dòng: nếu sau `Phụ lục I` xuất hiện `ban hành kèm theo`, `quy định tại`, `được quy định` -> 100% là trích dẫn, không phải heading.
  2. Bổ sung kiểm tra liên tục câu: nếu dòng trước không kết thúc bằng dấu chấm và kết thúc bằng từ dẫn chiếu (`theo Mẫu số 06 tại`) -> không phải heading.
  3. Áp dụng **Structural Forward Look-ahead**: Một phụ lục ở cuối văn bản luật Việt Nam không thể bắt đầu khi phía sau nó vẫn còn các `Chương` hoặc các `Điều` luật kế tiếp (`Điều 13`).

### 2.3. Ghost Heading `Điều 142 .` (TT 10/2020)
* **Nguyên nhân**: Dòng 44 của `TT_10_2020.txt` chứa `Điều 142 .`, là phần đuôi bị ngắt dòng từ câu dẫn chiếu ở dòng 42: *"...theo quy định tại khoản 1"*. Parser cũ thấy `Điều 142` ở đầu dòng liền tạo một `ArticleBlock` ma.
* **Giải pháp**: `is_real_article_heading()` kiểm tra nếu dòng trước là câu dở dang kết thúc bằng cụm từ dẫn chiếu (`khoản 1`, `quy định tại`) và dòng hiện tại chỉ có `Điều <number> .` không có tiêu đề, không có nội dung tiếp nối -> xem như câu tiếp diễn, không tạo `ArticleBlock`. Toàn bộ text được bảo toàn trong Điều 1.

### 2.4. Micro Table-Header `Lao động nam` (ND 135/2020)
* **Nguyên nhân**: Trong `appendix_parser.py`, phương thức `parse_retirement_tables()` flush sub-table ngay khi gặp nhóm giới tính tiếp theo, dẫn đến trường hợp tiêu đề ngắn (<10 từ) bị đẩy ra thành chunk độc lập 4 tokens.
* **Giải pháp**: Đệm các dòng tiêu đề ngắn (<10 từ) vào `preamble_lines` và gắn liền vào phần thân bảng số liệu tiếp theo, loại bỏ hoàn toàn chunk mồ côi.

---

## 3. Files Modified

| File | Component | Modifications |
|:---|:---|:---|
| [`Data_Processing/hierarchy_parser.py`](file:///d:/Filehoc/KLCN/agentic-rag/Data_Processing/hierarchy_parser.py) | Document Hierarchy Parser | • Bổ sung `is_real_article_heading()` với quy tắc ưu tiên cấu trúc tiêu đề Điều.<br>• Nâng cấp `is_appendix_start()` với kiểm tra câu tiếp diễn và Structural Forward Look-ahead.<br>• Mở rộng `ref_introducers` và `ref_phrase_ends`. |
| [`Data_Processing/chunker_v2.py`](file:///d:/Filehoc/KLCN/agentic-rag/Data_Processing/chunker_v2.py) | Legal Chunker V2 | • Sửa tận gốc `_is_citation_article()`: Không bao giờ merge Điều luật có title/clauses.<br>• Loại bỏ sự phụ thuộc mù quáng vào regex keyword ("áp dụng", "quy định"). |
| [`Data_Processing/appendix_parser.py`](file:///d:/Filehoc/KLCN/agentic-rag/Data_Processing/appendix_parser.py) | Appendix / Table Parser | • Sửa `parse_retirement_tables()`: gom header nhóm giới tính ngắn (<10 từ) vào bảng nội dung, triệt tiêu micro-chunk. |
| [`Data_Processing/test_hierarchy_parser.py`](file:///d:/Filehoc/KLCN/agentic-rag/Data_Processing/test_hierarchy_parser.py) | Hierarchy Unit Tests | • Cập nhật assertion test tích hợp BLLD 2019 từ 227 về 220 Điều thực tế (loại bỏ 7 citation nhầm lẫn). |
| [`Data_Processing/test_data_13_regression.py`](file:///d:/Filehoc/KLCN/agentic-rag/Data_Processing/test_data_13_regression.py) | Regression Test Suite | • Tạo mới 7 bài test kiểm thử hồi quy độc lập cho toàn bộ các ca lỗi DATA-13. |
| [`reports/dataset_audit/DATA-13-REGRESSION.json`](file:///d:/Filehoc/KLCN/agentic-rag/reports/dataset_audit/DATA-13-REGRESSION.json) | Audit Data Report | • Báo cáo dữ liệu máy đọc so sánh Before vs After. |
| [`reports/dataset_audit/DATA-13-REGRESSION.md`](file:///d:/Filehoc/KLCN/agentic-rag/reports/dataset_audit/DATA-13-REGRESSION.md) | Audit Markdown Report | • Báo cáo chi tiết kỹ thuật cho người thẩm định. |

---

## 4. Before / After Metrics Comparison

| Chỉ số / Đặc tính | Baseline V2 (Before) | Dataset V2.1 (After DATA-13) | Biến thiên | Trạng thái |
|:---|:---:|:---:|:---:|:---:|
| **Số lượng văn bản (Documents)** | 15 | 15 | 0 | Giữ nguyên 100% |
| **Tổng số đoạn (Chunks)** | 1,385 | **1,390** | +5 chunks | Tối ưu hóa phân đoạn |
| **Số lượng Chunk ID duy nhất** | 1,385 | **1,390** | +5 | **100% Unique** |
| **Trùng lặp ID (Collisions)** | 0 (0.0%) | **0 (0.0%)** | 0 | **Hoàn hảo** |
| **Kích thước token nhỏ nhất** | 4 tokens | **26 tokens** | +22 tokens | Loại bỏ micro header |
| **Kích thước token lớn nhất** | 800 tokens | **800 tokens** | 0 | Giữ vững trần token |
| **Kích thước token trung vị** | 210.0 tokens | **211.0 tokens** | +1.0 | Ngữ cảnh đầy đủ |
| **Kích thước token trung bình** | 264.4 tokens | **264.75 tokens** | +0.35 | Tối ưu embedding |
| **Chunks < 50 tokens** | 36 (2.60%) | **34 (2.45%)** | -2 chunks | Giảm phân mảnh |
| **Chunks < 100 tokens** | 147 (10.61%) | **145 (10.43%)** | -2 chunks | Cải thiện độ trọn vẹn |
| **Monster chunks (>800 tokens)** | 0 (0.0%) | **0 (0.0%)** | 0 | **Triệt tiêu hoàn toàn** |
| **Lỗi False-merge Điều luật** | 3 lỗi (BLOCKING) | **0 lỗi** | -3 | **Đã sửa dứt điểm** |
| **Lỗi phân loại Phụ lục** | 1 lỗi (MEDIUM) | **0 lỗi** | -1 | **Đã sửa dứt điểm** |
| **Ghost Heading Chunks** | 1 chunk (TT10) | **0 chunk** | -1 | **Đã sửa dứt điểm** |
| **Micro Table-Header Chunks** | 1 chunk (ND135) | **0 chunk** | -1 | **Đã sửa dứt điểm** |

---

## 5. Article Regression Results

| Mã văn bản & Điều luật | Hiện trạng trước fix (Before) | Hiện trạng sau fix (After) | Chunks tạo ra | Tiêu đề ghi nhận | Trạng thái |
|:---|:---|:---|:---:|:---|:---:|
| **BLLD 2019 — Điều 125** | Bị merge sai vào chunk Điều 124 (`BLLD_2019_Điều124_163`) | Tách biệt hoàn toàn, thành 2 chunk độc lập | 2 chunks | *Áp dụng hình thức xử lý kỷ luật sa thải* | **PASS** |
| **NĐ 145/2020 — Điều 85** | Bị merge sai vào chunk Điều 84 (`ND_145_2020_Điều84_169`) | Tách biệt hoàn toàn, thành 2 chunk độc lập | 2 chunks | *Quy định của người sử dụng lao động về phòng, chống quấy rối tình dục tại nơi làm việc* | **PASS** |
| **NĐ 219/2025 — Điều 6** | Bị merge sai vào chunk Điều 5 (`ND_219_2025_Điều5_7`) | Tách biệt hoàn toàn, thành 2 chunk độc lập | 2 chunks | *Quy định về giao dịch điện tử trong cấp, cấp lại, gia hạn giấy phép lao động và giấy xác nhận không thuộc diện cấp giấy phép lao động* | **PASS** |

### Chi tiết các chunk được khôi phục:
1. `BLLD_2019_Điều125_Khoản1_167` (tokens: 289): Toàn văn Khoản 1 & 2 về áp dụng hình thức xử lý kỷ luật sa thải.
2. `BLLD_2019_Điều125_Khoản3_168` (tokens: 226): Toàn văn Khoản 3 & 4 về thời hạn và tái phạm.
3. `ND_145_2020_Điều85_Khoản1_173` (tokens: 260): Nội quy lao động về quấy rối tình dục tại nơi làm việc.
4. `ND_145_2020_Điều85_Khoản2_174` (tokens: 248): Khiếu nại, tố cáo và xử lý quấy rối tình dục.
5. `ND_219_2025_Điều6_Khoản1_8` (tokens: 254): Giao dịch điện tử cấp phép lao động qua Cổng Dịch vụ công quốc gia.
6. `ND_219_2025_Điều6_Khoản3_P1_9` (tokens: 312): Hồ sơ điện tử và xác nhận không thuộc diện cấp giấy phép.

---

## 6. Appendix Regression Results

| Văn bản & Điều luật | Hiện trạng trước fix (Before) | Hiện trạng sau fix (After) | Phân loại | Metadata phân cấp cha | Trạng thái |
|:---|:---|:---|:---:|:---|:---:|
| **TT 09/2020 — Điều 13** | `content_type = appendix`, `article_number = null` | `content_type = clause / point`, `article_number = Điều 13` | Article | `chapter_number: Chương V`, `chapter_title: ĐIỀU KHOẢN THI HÀNH` | **PASS** |

### Chi tiết chunk Điều 13 Thông tư 09/2020:
* **Chunk 1**: `TT_09_2020_Điều13_Khoản1_18`
  * `article_number`: `"Điều 13"`
  * `article_title`: `"Hiệu lực thi hành"`
  * `content`: `"Điều 13. Hiệu lực thi hành\n1. Thông tư này có hiệu lực thi hành kể từ ngày 15 tháng 3 năm 2021."`
* **Chunk 2**: `TT_09_2020_Điều13_Khoản2_P1_19`
  * `article_number`: `"Điều 13"`
  * `article_title`: `"Hiệu lực thi hành"`
  * `content`: Quy định bãi bỏ các Thông tư 10/2013 và 11/2013 kèm danh mục công việc nhẹ và công việc cấm sử dụng lao động chưa thành niên.
* **Phần Phụ lục thật**: Bắt đầu chính xác tại dòng 411 (`PHỤ LỤC I`), gồm 1,660 dòng đính kèm các Biểu mẫu từ Mẫu số 01 đến Mẫu số 06.

---

## 7. Low-Priority Cleanup Results

### 7.1. Ghost Heading TT 10/2020
* **Vấn đề**: Trước đây sinh ra chunk ma `TT_10_2020_Điều142_...` (4 tokens) do dòng trích dẫn `Điều 142 .` bị ngắt dòng sau cụm `theo quy định tại khoản 1`.
* **Kết quả**: Không còn bất kỳ chunk nào mang `article_number = "Điều 142"`. Cụm từ trích dẫn được lưu trữ trọn vẹn trong chunk nội dung của Điều 1. Số lượng ghost chunk = 0.
* **Trạng thái**: **PASS**.

### 7.2. Micro Table-Header ND 135/2020
* **Vấn đề**: Trước đây sinh ra chunk 4 tokens chỉ chứa chữ `Lao động nam`.
* **Kết quả**: Tiêu đề nhóm giới tính ngắn (<10 từ) được gom trực tiếp vào bảng lộ trình nghỉ hưu tương ứng. Không còn bất kỳ chunk nào chỉ có `Lao động nam` đứng riêng lẻ.
* **Trạng thái**: **PASS**.

---

## 8. Full Test Results

Hệ thống kiểm thử bao gồm toàn bộ test suite hiện có của dự án và test suite mới viết cho `DATA-13`:

```text
Command: python -m unittest discover -s Data_Processing -p "test_*.py"
Ran 130 tests in 1.613s
OK
```

### Danh mục test modules:
1. `test_data_13_regression.py` (7 tests): **7/7 PASSED** (Kiểm thử chuyên biệt các ca lỗi DATA-13).
2. `test_chunker_v2.py` (12 tests): **12/12 PASSED**.
3. `test_hierarchy_parser.py` (12 tests): **12/12 PASSED**.
4. `test_article_parser.py` (26 tests): **26/26 PASSED**.
5. `test_appendix_parser.py` (19 tests): **19/19 PASSED**.
6. `test_build_dataset_v2.py` (10 tests): **10/10 PASSED**.
7. `test_chunk_id_collisions.py` (8 tests): **8/8 PASSED**.
8. `test_schema_v2.py` (18 tests): **18/18 PASSED**.
9. `test_date_status_v2.py` (10 tests): **10/10 PASSED**.
10. `test_metadata_restorer.py` (8 tests): **8/8 PASSED**.

---

## 9. Determinism Result

Quy trình rebuild dataset đã được kiểm tra tính tất định qua 2 lần thực thi độc lập:

| Lần chạy | Timestamp | Số chunks | SHA-256 (`legal_dataset_v2.json`) | Trùng khớp |
|:---:|:---:|:---:|:---|:---:|
| **Run 1** | 2026-09-09T07:49:59Z | 1,390 | `e48c6a3bece6819a0e25da8d985c8391ec162561c985e26d69dc3d13f2c87d92` | BASELINE |
| **Run 2** | 2026-09-09T07:50:11Z | 1,390 | `e48c6a3bece6819a0e25da8d985c8391ec162561c985e26d69dc3d13f2c87d92` | **100% MATCH** |

* SHA-256 của `legal_dataset_v2.jsonl`: `bcd6d0f05b0239b6250a6aa30e93d27093599d6da08bf80344cfd3a8ce834265`.
* Tính tất định (Determinism): **PASS**.

---

## 10. Remaining Warnings

1. **Missing `issue_date` in Raw Corpus**: 15/15 văn bản thô hiện tại trong crawler thiếu metadata ngày ban hành trực tiếp từ raw web headers (đã được ghi nhận trong `DATA-08` và `DATA-V2-AUDIT`, không thuộc phạm vi xử lý của parser heading).
2. **Chunks < 50 tokens (34 chunks - 2.45%)**: Toàn bộ 34 chunks này đều là các Điểm luật đặc thù rất ngắn hoặc các quy định chuyển tiếp độc lập có ý nghĩa pháp lý nguyên bản (ví dụ: các điều khoản bãi bỏ, phạm vi hẹp). Không còn chunk rác hoặc ghost heading.

---

## 11. Final Verdict

Tất cả các tiêu chí **MUST PASS** và **SHOULD PASS** của `DATA-13` đều đã đạt 100%:

```text
[PASS]
```

### Khuyến nghị bước tiếp theo:
Dataset V2.1 đã hoàn toàn sạch sẽ, bảo toàn trọn vẹn cấu trúc pháp lý, phân biệt hoàn hảo giữa Heading và Citation, sẵn sàng chuyển giao sang **DATA-14 VALIDATION**. Tuyệt đối không tiến hành embedding hay RAG khi chưa có chỉ thị tiếp theo.
