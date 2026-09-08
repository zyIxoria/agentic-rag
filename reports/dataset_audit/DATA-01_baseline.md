# BÁO CÁO THIẾT LẬP BASELINE DATASET V1 — TASK DATA-01
**Dự án:** Nghiên cứu cơ chế điều phối thích ứng trong hệ thống Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam  
**Mục tiêu:** Đóng băng trạng thái (Freeze) và thiết lập chỉ số chuẩn (Baseline) cho dataset hiện tại trước khi thực hiện bất kỳ cải tiến tiền xử lý / chunking nào.  
**Thời điểm thực hiện:** 09/09/2026  
**Trạng thái tuân thủ:** READ-ONLY tuyệt đối trên mã nguồn và dữ liệu gốc. Không triển khai thành phần RAG, không tạo vector database, không tính toán embedding.

---

## 1. Giới thiệu & Xác thực tính toàn vẹn (Integrity & Checksum)

Để đảm bảo nguyên tắc kiểm thử độc lập và khả năng tái lập (reproducibility), toàn bộ các tệp dữ liệu thuộc Dataset V1 đã được tính toán mã băm SHA256 trước và sau khi thực hiện kiểm toán:

### 1.1. Dataset V1 Output Chunking File
- **Đường dẫn:** `Data_Processing/KhoaLuan_Data_HoanChinh.json`
- **Kích thước:** `2,781,988 bytes` (2.65 MB)
- **Tổng số chunks:** `2,765`
- **SHA-256 Hash:**  
  `7BDB170543734804C64945A02D5388A32399DD391FF3B2A3D029ADD1D3FE3FB4`
- **Trạng thái:** BẢO TOÀN NGUYÊN VẸN (0 byte thay đổi).

### 1.2. Danh sách 15 văn bản nguồn (Raw Corpus Files)

Toàn bộ 15 cặp file `.txt` và `_meta.json` tại `Data_Processing/data_corpus_raw/` được ghi nhận chữ ký SHA-256:

| Doc ID | File văn bản (.txt) | Kích thước (bytes) | SHA-256 (.txt) | Chunks tạo ra |
| :--- | :--- | :---: | :--- | :---: |
| **BLLD_2019** | `BLLD_2019.txt` | 261,507 | `3D134A8393F2E6E26584A501B0E6CDEFE...` | 884 |
| **ND_12_2022** | `ND_12_2022.txt` | 246,142 | `FF7CEA749568C74C91D35E7A83E3087C9...` | 323 |
| **ND_135_2020** | `ND_135_2020.txt` | 49,343 | `ADB0D882113443FA1141A2A39107B2526...` | 50 |
| **ND_145_2020** | `ND_145_2020.txt` | 264,261 | `946665A04233BE906ED856C0D6FB2C31E...` | 495 |
| **ND_152_2020** | `ND_152_2020.txt` | 166,493 | `1A1657EBB0DB35066DC789B3D667EB67B...` | 312 |
| **ND_219_2025** | `ND_219_2025.txt` | 99,685 | `583FC4A69062A2CC1F370734381B7EBE4...` | 205 |
| **ND_70_2023** | `ND_70_2023.txt` | 63,795 | `E9E311F687D9441263FE957CC648EA421...` | 35 |
| **ND_74_2024** | `ND_74_2024.txt` | 20,877 | `A4C58ED14070CD8CF9720FE1A304BE657...` | 22 |
| **ND_83_2022** | `ND_83_2022.txt` | 9,601 | `0F8E21A38A61178FA4F680AE8CD47BD9B...` | 21 |
| **ND_99_2024** | `ND_99_2024.txt` | 4,617 | `1ED174D211486420E7EFE2FACD252119A...` | 4 |
| **QD_992_2025** | `QD_992_2025.txt` | 7,858 | `A9B58473C45DDACF8565CC1BC84E86C08...` | 16 |
| **TT_09_2020** | `TT_09_2020.txt` | 57,357 | `085F938BA39C6475FCAB7FDC20AAF2982...` | 186 |
| **TT_10_2020** | `TT_10_2020.txt` | 46,416 | `4525961EAA4DA6DA4A86FEB4EF13A5031...` | 164 |
| **TT_11_2020** | `TT_11_2020.txt` | 770,547 | `674BC481B8775320D297659BD148FA3DC...` | 6 |
| **TT_20_2023** | `TT_20_2023.txt` | 15,924 | `34E14CA0B4D0EF4CA26D9B0D02C49D65B...` | 42 |

---

## 2. Thống kê cốt lõi Dataset V1 (Core Dataset Statistics)

### 2.1. Tổng quan số lượng
- **Tổng số Documents:** **15** văn bản quy phạm pháp luật.
- **Tổng số Chunks:** **2,765** chunks.
- **Tổng số Ký tự (Characters):** **1,443,548** ký tự.
- **Tổng số Từ (Words):** **311,675** từ.
- **Tổng số Tokens ước tính:** **405,168** tokens (Hệ số quy đổi: $Tokens = Words \times 1.3$).

### 2.2. Phân bố số Chunks trên mỗi Document
- **Tối thiểu (Min):** `4` chunks (Nghị định 99/2024/NĐ-CP).
- **Tối đa (Max):** `884` chunks (Bộ luật Lao động 2019).
- **Trung bình (Mean):** `184.33` chunks / document.
- **Trung vị (Median):** `50.0` chunks / document.

```text
Phân bố chi tiết theo từng văn bản:
- BLLD_2019:    884 chunks (31.97%)
- ND_145_2020:  495 chunks (17.90%)
- ND_12_2022:   323 chunks (11.68%)
- ND_152_2020:  312 chunks (11.28%)
- ND_219_2025:  205 chunks (7.41%)
- TT_09_2020:   186 chunks (6.73%)
- TT_10_2020:   164 chunks (5.93%)
- ND_135_2020:   50 chunks (1.81%)
- TT_20_2023:    42 chunks (1.52%)
- ND_70_2023:    35 chunks (1.27%)
- ND_74_2024:    22 chunks (0.80%)
- ND_83_2022:    21 chunks (0.76%)
- QD_992_2025:   16 chunks (0.58%)
- TT_11_2020:     6 chunks (0.22%)  <-- Chứa chunk bất thường 142k tokens
- ND_99_2024:     4 chunks (0.14%)
```

---

## 3. Phân bố Token & Độ dài (Token Distribution Analysis)

Bảng phân bố thống kê chi tiết theo các mốc phân vị (Percentiles):

| Chỉ số (Metric) | Ký tự (Characters) | Số từ (Words) | Ước tính Tokens ($Words \times 1.3$) | Ý nghĩa thực tế |
| :--- | :---: | :---: | :---: | :--- |
| **Tối thiểu (Min)** | 11 | 3 | **4** | Chunk vụn: *"4. Sa thải."* |
| **Phân vị 25% (p25)** | 77 | 16 | **21.0** | 25% chunks ngắn hơn 21 tokens |
| **Trung vị (Median)** | 172 | 38 | **49.0** | 50% chunks ngắn hơn 49 tokens |
| **Trung bình (Mean)** | 522.08 | 112.72 | **146.53** | Bị kéo lệch bởi monster chunk |
| **Phân vị 75% (p75)** | 370 | 80 | **104.0** | 75% chunks ngắn hơn 104 tokens |
| **Phân vị 95% (p95)** | 1,141 | 247 | **321.8** | 95% chunks ngắn hơn 322 tokens |
| **Tối đa (Max)** | 507,616 | 109,641 | **142,533** | Phụ lục TT 11/2020 (Monster Chunk) |

### 3.1. Phân nhóm độ dài Tokens (Token Bins)

```text
========================================================================================
Khoảng Token                 Số Chunks       Tỷ lệ (%)       Nhận xét chất lượng
----------------------------------------------------------------------------------------
< 50 tokens                   1,398           50.56%         Quá ngắn, mất ngữ cảnh pháp lý
< 100 tokens (tổng gộp)       2,035           73.60%         Chiếm gần 3/4 dataset
> 500 tokens                     70            2.53%         Thường là các điều khoản dài/biểu mẫu
> 1000 tokens                    10            0.36%         Chứa bảng biểu, phụ lục danh mục
========================================================================================
```

> [!WARNING]
> **Hiện tượng Over-fragmentation (Phân mảnh quá mức):**  
> Hơn một nửa dataset (**50.56%**, 1,398 chunks) có kích thước dưới 50 tokens. Các chunk này phần lớn chỉ là một dòng đơn lẻ hoặc một cụm từ cụt ngủn bị tách rời khỏi Điều luật gốc.

---

## 4. Phân tích Chunk lớn nhất (Largest Chunk Profile)

- **Mã Chunk (`ID_Chunk`):** `TT_11_2020_Chưaxácđịnh_Điều3_K3`
- **Văn bản nguồn:** Thông tư số 11/2020/TT-BLĐTBXH (Quy định Danh mục nghề, công việc nặng nhọc, độc hại, nguy hiểm)
- **Cấu trúc phân cấp ghi nhận:**  
  `Chương: "Chưa xác định"` | `Điều: "Điều 3"` | `Khoan: "3"`
- **Độ dài ký tự:** **507,616** ký tự
- **Số từ:** **109,641** từ
- **Tokens ước tính:** **~142,533** tokens
- **Trích đoạn 300 ký tự đầu:**
  > *"3. Thời gian người lao động làm các nghề, công việc ban hành kèm theo các Quyết định, Thông tư bị bãi bỏ theo quy định tại Khoản 2 Điều này vẫn được tính là thời gian làm các nghề, công việc nặng nhọc, độc hại, nguy hiểm hoặc đặc biệt nặng nhọc, độc hại, nguy hiểm cho đến ngày Thông tư này có hiệu lực..."*
- **Nguyên nhân kỹ thuật:**  
  Sau Khoản 3 Điều 3 của Thông tư 11/2020 là toàn bộ Phụ lục danh mục hàng nghìn ngành nghề độc hại được trình bày dạng bảng. Pipeline chunking hiện tại (`data_processing.py`) chỉ sử dụng regex tìm `Chương`, `Điều`, `Khoản`. Do toàn bộ phụ lục không có dòng nào bắt đầu bằng `Điều` hay `Khoản`, thuật toán tiếp tục append toàn bộ 500,000 ký tự phụ lục vào chunk của Khoản 3 Điều 3!
- **Tác động:** Không thể embed vào vector database; gây lỗi tràn bộ nhớ hoặc bị cắt cụt > 94% nội dung ở mọi mô hình embedding tiêu chuẩn.

---

## 5. Phân tích Trùng lặp (Duplicate Analysis)

### 5.1. Trùng lặp nội dung văn bản (Content Duplication)
- **Số lượng chunks trùng lặp nội dung tuyệt đối:** **105 chunks (3.80%)**
- **Số nhóm nội dung unique bị lặp:** **36 nhóm**
- **Số lượng chunks gần trùng lặp (Near-duplicates):** **128 chunks (4.63%)** (45 nhóm)
- **Các mẫu nội dung bị lặp phổ biến nhất:**
  1. Tiêu đề Điều: `"Điều 2. Đối tượng áp dụng"` xuất hiện **10 lần** ở 10 văn bản khác nhau.
  2. Tiêu đề Chương: `"Chương I QUY ĐỊNH CHUNG"` lặp **4 lần**, `"Chương I NHỮNG QUY ĐỊNH CHUNG"` lặp **4 lần**.
  3. Mẫu điều khoản hành chính: `"3. Chính phủ quy định chi tiết Điều này."` xuất hiện ở các Điều 12, 85, 96 BLLD 2019.
  4. Nội dung biểu mẫu chuyển tiếp: lặp nhiều lần giữa các phụ lục của NĐ 12/2022 và NĐ 219/2025.

### 5.2. Trùng lặp định danh khóa chính (ID Collisions)
- **Số mã `ID_Chunk` bị trùng lặp:** **117 mã ID khác nhau**
- **Tổng số chunks bị ảnh hưởng bởi đụng độ ID:** **434 chunks (15.70% toàn bộ dataset)**
- **Top 5 ID bị đụng độ nhiều nhất:**
  1. `ND_152_2020_ChươngIV_Điều29_K1`: Trùng lặp **18 lần**!
  2. `ND_152_2020_ChươngIV_Điều29_K2`: Trùng lặp **17 lần**!
  3. `ND_152_2020_ChươngIV_Điều29_K3`: Trùng lặp **13 lần**!
  4. `ND_12_2022_ChươngIV_Điều49_K0`: Trùng lặp **9 lần**!
  5. `TT_09_2020_ChươngV_Điều13_K1`: Trùng lặp **9 lần**!

> [!CAUTION]
> **Hậu quả đụng độ ID đối với Vector Database:**  
> Công thức sinh ID: `{doc_id}_{Chuong}_{Dieu}_K{Khoan}` không tính đến trường hợp có nhiều biểu mẫu phụ lục cùng chứa các mục `1. `, `2. `. Nếu đưa dataset này vào ChromaDB/Qdrant/Milvus, **317 chunks sẽ bị ghi đè mất vĩnh viễn** hoặc gây Exception dừng nạp dữ liệu.

---

## 6. Độ phủ Metadata (Metadata Coverage)

Kiểm tra 11 trường thông tin theo yêu cầu:

| STT | Tên Metadata | Có trong Schema Chunk? | Coverage trong Chunks | Độ chính xác thực tế | Đánh giá & Rủi ro |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 1 | `document_id` | **NO** | 0.0% | N/A | Chỉ được gắn ngầm ở tiền tố của `ID_Chunk`. Không có field riêng để filter. |
| 2 | `document_number` | **NO** | 0.0% | N/A | Trong raw meta `so_hieu` bị dính text thừa HTML. Không được đưa vào chunk. |
| 3 | `document_title` | **YES** (`Van_ban`) | 100.0% | Kém | Có trường `Van_ban`, nhưng dính ký tự xuống dòng `\n` và text rác crawl. |
| 4 | `document_type` | **NO** | 0.0% | N/A | Trường `loai_van_ban` trong file raw rỗng 100%. Không có trong chunk. |
| 5 | `chapter` | **YES** (`Chuong`) | 100.0% (Hợp lệ 88.97%) | Kém | 11.03% là "Chưa xác định". Bị lỗi nhảy nhầm sang Chương XI ở BLLD 2019. |
| 6 | `article` | **YES** (`Dieu`) | 100.0% (Hợp lệ 99.17%) | Khá | 0.83% là "Chưa xác định". Nhận diện tốt tiền tố "Điều \d+". |
| 7 | `clause` | **YES** (`Khoan`) | 100.0% (Hợp lệ 77.83%) | Kém | 22.17% là "0". Bị nhận diện nhầm các số thứ tự biểu mẫu thành số Khoản. |
| 8 | `point` | **NO** | 0.0% | N/A | **MISSING**. Không có cơ chế bóc tách Điểm a, b, c. |
| 9 | `effective_date` | **YES** (`Thoi_diem_hieu_luc`) | **0.0%** (Rỗng 100%) | **0%** | Toàn bộ 2,765 chunks đều là chuỗi rỗng `""`. Hoàn toàn vô dụng. |
| 10 | `legal_status` | **NO** | 0.0% | N/A | **MISSING**. Không có trong chunk. Trong file raw 14/15 doc ghi `"Đã biết"`. |
| 11 | `source_url` | **NO** | 0.0% | N/A | Có trong raw metadata (`source`) nhưng bị pipeline chunking loại bỏ. |

---

## 7. Các Document có Metadata bị thiếu trong Raw Corpus

Kiểm tra toàn bộ 15 tệp `*_meta.json` trong `data_corpus_raw/`:

```text
====================================================================================================
Văn bản (Doc ID)      Các trường RỖNG hoàn toàn        Các trường DÍNH RÁC / SAI LỆCH
----------------------------------------------------------------------------------------------------
BLLD_2019             loai_van_ban, co_quan_ban_hanh,  so_hieu (dính \n), ngay_ban_hanh (dính ngày HL)
                      ngay_hieu_luc
ND_12_2022            loai_van_ban, co_quan_ban_hanh,  so_hieu (dính \n), ngay_ban_hanh,
                      ngay_hieu_luc                    tinh_trang_hieu_luc = 'Đã biết'
ND_135_2020           loai_van_ban, co_quan_ban_hanh,  so_hieu (dính \n), ngay_ban_hanh,
                      ngay_hieu_luc                    tinh_trang_hieu_luc = 'Đã biết'
ND_145_2020           loai_van_ban, co_quan_ban_hanh,  so_hieu (dính \n), ngay_ban_hanh,
                      ngay_hieu_luc                    tinh_trang_hieu_luc = 'Đã biết'
ND_152_2020           loai_van_ban, co_quan_ban_hanh,  so_hieu (dính \n), ngay_ban_hanh,
                      ngay_hieu_luc                    tinh_trang_hieu_luc = 'Đã biết'
ND_219_2025           loai_van_ban, co_quan_ban_hanh,  so_hieu (dính \n), ngay_ban_hanh,
                      ngay_hieu_luc                    tinh_trang_hieu_luc = 'Đã biết'
ND_70_2023            loai_van_ban, co_quan_ban_hanh,  so_hieu (dính \n), ngay_ban_hanh,
                      ngay_hieu_luc                    tinh_trang_hieu_luc = 'Đã biết'
ND_74_2024            loai_van_ban, co_quan_ban_hanh,  so_hieu (dính \n), ngay_ban_hanh,
                      ngay_hieu_luc                    tinh_trang_hieu_luc = 'Đã biết'
ND_83_2022            loai_van_ban, co_quan_ban_hanh,  so_hieu (dính \n), ngay_ban_hanh,
                      ngay_hieu_luc                    tinh_trang_hieu_luc = 'Đã biết'
ND_99_2024            loai_van_ban, co_quan_ban_hanh,  so_hieu (dính \n), ngay_ban_hanh,
                      ngay_hieu_luc                    tinh_trang_hieu_luc = 'Đã biết'
QD_992_2025           loai_van_ban, co_quan_ban_hanh,  so_hieu (dính \n), ngay_ban_hanh,
                      ngay_hieu_luc                    tinh_trang_hieu_luc = 'Đã biết'
TT_09_2020            loai_van_ban, co_quan_ban_hanh,  so_hieu (dính \n), ngay_ban_hanh,
                      ngay_hieu_luc                    tinh_trang_hieu_luc = 'Đã biết'
TT_10_2020            loai_van_ban, co_quan_ban_hanh,  so_hieu (dính \n), ngay_ban_hanh,
                      ngay_hieu_luc                    tinh_trang_hieu_luc = 'Đã biết'
TT_11_2020            loai_van_ban, co_quan_ban_hanh,  so_hieu (dính \n), ngay_ban_hanh,
                      ngay_hieu_luc                    tinh_trang_hieu_luc = 'Đã biết'
TT_20_2023            loai_van_ban, co_quan_ban_hanh,  so_hieu (dính \n), ngay_ban_hanh,
                      ngay_hieu_luc                    tinh_trang_hieu_luc = 'Đã biết'
====================================================================================================
```

---

## 8. Danh mục các Dị thường trong Chunks (Chunk Anomalies)

Hệ thống ghi nhận 7 nhóm dị thường đặc biệt nghiêm trọng:

### 8.1. [CRITICAL] Monster Chunk (Chunk khổng lồ)
- **Vị trí:** `TT_11_2020_Chưaxácđịnh_Điều3_K3`
- **Kích thước:** 507,616 ký tự (~142,533 tokens).
- **Hậu quả:** Làm gãy vỡ toàn bộ pipeline embedding và retrieval.

### 8.2. [CRITICAL] Đụng độ khóa ID (`ID_Chunk` Collision)
- **Vị trí:** 117 mã ID khác nhau, ảnh hưởng 434 chunks.
- **Điển hình:** `ND_152_2020_ChươngIV_Điều29_K1` lặp 18 lần; `ND_152_2020_ChươngIV_Điều29_K2` lặp 17 lần.
- **Hậu quả:** Gây mất dữ liệu khi nạp vào Vector DB (silent overwrite).

### 8.3. [HIGH] Vấn đề Micro-chunks thiếu ngữ cảnh (Contextless Micro-chunks)
- **Số lượng:** 1,398 chunks (< 50 tokens), 2,035 chunks (< 100 tokens).
- **Điển hình:**  
  - `BLLD_2019_ChươngVIII_Điều124_K4`: `"4. Sa thải."` (3 từ, 11 ký tự)
  - `BLLD_2019_ChươngVIII_Điều124_K1`: `"1. Khiển trách."` (3 từ, 15 ký tự)
  - `TT_09_2020_ChươngV_Điều13_K8`: `"8. Nuôi tằm."` (3 từ, 12 ký tự)
- **Hậu quả:** Khi người dùng hỏi *"Hình thức kỷ luật sa thải theo BLLD"*, chunk `"4. Sa thải."` không chứa các từ khóa ngữ cảnh về kỷ luật lao động hay BLLD, khiến vector search không thể tìm thấy.

### 8.4. [HIGH] Chunks chỉ chứa Tiêu đề Điều/Chương (Title-only Chunks)
- **Số lượng:** 396 chunks.
- **Điển hình:** `BLLD_2019_ChươngI_Điều2_K0` chứa `"Điều 2. Đối tượng áp dụng"`.
- **Hậu quả:** Tiêu đề bị tách rời khỏi nội dung của các Khoản quy định chi tiết.

### 8.5. [HIGH] Biến dạng chuyển tiếp Chương do tham chiếu chéo (Corrupted Chapter Transition)
- **Vị trí:** BLLD 2019, từ Điều 3 (Khoản 2 trở đi) đến hết Điều 8.
- **Nguyên nhân:** Câu văn *"Mục 1 \n Chương XI của Bộ luật này"* tại Khoản 1 Điều 3 kích hoạt regex `^(Chương\s+[IVXLCDM]+)`.
- **Hậu quả:** Điều 4 (Chính sách nhà nước về lao động), Điều 5 (Quyền và nghĩa vụ người lao động), Điều 6, 7, 8 thuộc Chương I nhưng bị metadata gán thành thuộc về **Chương XI**!

### 8.6. [MEDIUM] Dữ liệu biểu mẫu rác (Form Template Garbage)
- **Số lượng:** 59 chunks.
- **Điển hình:**  
  - `ND_219_2025_ChươngV_Điều36_K5`: `"5. Địa chỉ 3 :…………………………………………………………………………………………."`
  - `ND_152_2020_ChươngIV_Điều29_K5`: `"5. Điện thoại:................................................................. "`
- **Hậu quả:** Nhiễu vector database bằng các dòng kẻ chấm lửng vô nghĩa.

### 8.7. [MEDIUM] Cắt cụt giữa câu (Broken Sentences)
- **Số lượng:** 582 chunks (21.05%).
- **Nguyên nhân:** Regex ngắt đoạn khi gặp số thứ tự hoặc chữ Chương ở dòng sau mà không kiểm tra dấu chấm kết thúc câu của dòng trước.

---

## 9. Kết luận & Khuyến nghị kỹ thuật cho Task tiếp theo

1. **Về Dataset V1:** Dataset V1 hiện tại không thể sử dụng trực tiếp để xây dựng hệ thống RAG chất lượng cao do lỗi đụng độ ID, chunk khổng lồ, và mất ngữ cảnh ở các micro-chunk.
2. **Kế hoạch tiếp theo (Sau DATA-01):**
   - **DATA-02:** Sửa lỗi parser metadata trong crawler hoặc script backfill metadata từ các URL chính thức của Thư Viện Pháp Luật (lấy lại ngày ban hành, ngày hiệu lực, trạng thái văn bản, loại văn bản chuẩn xác).
   - **DATA-03:** Thiết kế lại thuật toán Chunking cấp Điều/Khoản kết hợp Context-Enrichment (luôn gộp tiêu đề Điều vào từng Khoản; tách riêng Phụ lục và Bảng biểu bằng bộ phân tách chuyên dụng; giới hạn độ dài chunk từ 150 - 600 tokens; sinh ID duy nhất gồm UUID hoặc hash nội dung).
   - **DATA-04:** Chạy kiểm thử đối soát giữa Dataset V1 (baseline này) và Dataset V2 sau khi sửa để xác nhận khắc phục 100% các dị thường trên.
