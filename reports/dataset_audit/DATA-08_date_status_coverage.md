# BÁO CÁO KIỂM TOÁN VÀ ĐỘ PHỦ METADATA NGÀY THÁNG & TÌNH TRẠNG HIỆU LỰC (TASK DATA-08)

**Dự án**: Nghiên cứu cơ chế điều phối thích ứng trong hệ thống Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam.  
**Nhiệm vụ**: TASK DATA-08 — Fix Effective Date and Legal Status Metadata.  
**Ngày thực hiện**: 09/09/2026.  
**Trạng thái**: Hoàn thành (100% Tests Passed - 108/108 Unit Tests).

---

## 1. TỔNG QUAN & MỤC TIÊU

Trong Dataset V1 (`KhoaLuan_Data_HoanChinh.json`), các trường siêu dữ liệu thời gian và hiệu lực pháp lý gặp các vấn đề nghiêm trọng:
- **`effective_date` = 0%**: Toàn bộ 2,765 chunks trong V1 đều có `Thoi_diem_hieu_luc = ""` (rỗng 100%) do crawler gán nhầm hoặc đọc trường rỗng `ngay_hieu_luc: ""` trong file meta.
- **`tinh_trang_hieu_luc` thiếu hoặc parse sai**: Dữ liệu crawler chứa các giá trị rác/placeholder như `"Đã biết"` hoặc `"Chưa xác định"`, gây sai lệch trạng thái pháp lý.
- **Thiếu sự phân biệt rõ ràng giữa các mốc thời gian**: Dễ dẫn đến việc nhầm lẫn giữa ngày ban hành (`issue_date`) và ngày có hiệu lực (`effective_from`).

**TASK DATA-08** giải quyết triệt để các vấn đề trên theo các nguyên tắc cốt lõi:
1. **Phân biệt tuyệt đối 4 trường metadata**:
   - `issue_date` (`ngay_ban_hanh`): Ngày ký ban hành văn bản.
   - `effective_from` (`ngay_hieu_luc`): Ngày văn bản bắt đầu có hiệu lực thi hành.
   - `effective_to` (`ngay_het_hieu_luc`): Ngày văn bản hết hiệu lực (mặc định `null` nếu còn hiệu lực).
   - `legal_status` (`tinh_trang_hieu_luc`): Tình trạng pháp lý chuẩn mực (`Còn hiệu lực`, `Hết hiệu lực`, `unknown`).
2. **Quy tắc nghiêm ngặt về tính toàn vẹn (Critical Integrity Rule)**:
   - **Không tự tạo (invent) ngày hiệu lực**: Nếu raw corpus không có thông tin, bắt buộc ghi nhận `null`.
   - **Không chuyển đổi text status thành date**: Các nhãn như `"Đã biết"` tuyệt đối không được ép kiểu thành ngày tháng.
   - **Không dùng một field cho nhiều nghĩa**: Tuyệt đối không gán `issue_date` sang `effective_from` khi thiếu ngày hiệu lực.
   - **Chuẩn hóa trạng thái không xác định**: Nếu raw corpus thiếu thông tin hiệu lực, ghi nhận `legal_status = "unknown"`.

---

## 2. BẢNG CHI TIẾT METADATA CỦA TOÀN BỘ 15 VĂN BẢN TRONG CORPUS

Dưới đây là kết quả phục hồi và chuẩn hóa metadata từ kho văn bản thô (`data_corpus_raw/`):

| STT | Mã văn bản (`doc_id`) | Số hiệu (`document_number`) | Loại văn bản | Ngày ban hành (`issue_date`) | Ngày hiệu lực (`effective_from`) | Ngày hết HL (`effective_to`) | Tình trạng pháp lý (`legal_status`) |
|:---:|:---|:---|:---|:---:|:---:|:---:|:---|
| 1 | **BLLD_2019** | 45/2019/QH14 | Bộ luật | 20/11/2019 | **01/01/2021** | `null` | **Còn hiệu lực** |
| 2 | **ND_12_2022** | 12/2022/NĐ-CP | Nghị định | 17/01/2022 | `null` | `null` | `unknown` |
| 3 | **ND_135_2020** | 135/2020/NĐ-CP | Nghị định | 18/11/2020 | `null` | `null` | `unknown` |
| 4 | **ND_145_2020** | 145/2020/NĐ-CP | Nghị định | 14/12/2020 | `null` | `null` | `unknown` |
| 5 | **ND_152_2020** | 152/2020/NĐ-CP | Nghị định | 30/12/2020 | `null` | `null` | `unknown` |
| 6 | **ND_219_2025** | 219/2025/NĐ-CP | Nghị định | 07/08/2025 | `null` | `null` | `unknown` |
| 7 | **ND_70_2023** | 70/2023/NĐ-CP | Nghị định | 18/09/2023 | `null` | `null` | `unknown` |
| 8 | **ND_74_2024** | 74/2024/NĐ-CP | Nghị định | 30/06/2024 | `null` | `null` | `unknown` |
| 9 | **ND_83_2022** | 83/2022/NĐ-CP | Nghị định | 18/10/2022 | `null` | `null` | `unknown` |
| 10 | **ND_99_2024** | 99/2024/NĐ-CP | Nghị định | 26/07/2024 | `null` | `null` | `unknown` |
| 11 | **QD_992_2025** | 992/QĐ-TTg | Quyết định | 22/05/2025 | `null` | `null` | `unknown` |
| 12 | **TT_09_2020** | 09/2020/TT-BLĐTBXH | Thông tư | 12/11/2020 | `null` | `null` | `unknown` |
| 13 | **TT_10_2020** | 10/2020/TT-BLĐTBXH | Thông tư | 12/11/2020 | `null` | `null` | `unknown` |
| 14 | **TT_11_2020** | 11/2020/TT-BLĐTBXH | Thông tư | 12/11/2020 | `null` | `null` | `unknown` |
| 15 | **TT_20_2023** | 20/2023/TT-BCT | Thông tư | 08/11/2023 | `null` | `null` | `unknown` |

---

## 3. THỐNG KÊ ĐỘ PHỦ (METADATA COVERAGE SUMMARY)

| Chỉ số kiểm toán | Số lượng văn bản | Tỷ lệ (%) | Đánh giá & Ghi chú |
|:---|:---:|:---:|:---|
| **Tổng số văn bản quy phạm** | 15 / 15 | 100% | Toàn bộ corpus pháp luật lao động hiện có. |
| **Độ phủ Ngày ban hành (`issue_date`)** | **15 / 15** | **100.0%** | 100% văn bản khôi phục được ngày ban hành cụ thể (DD/MM/YYYY). |
| **Độ phủ Ngày hiệu lực (`effective_from`)** | **1 / 15** | **6.67%** | Phục hồi thành công cho BLLD_2019 (`01/01/2021`). 14 văn bản còn lại raw meta chứa `"Đã biết"` nên gán `null`. |
| **Độ phủ Ngày hết hiệu lực (`effective_to`)** | **0 / 15** | **0.0%** | Toàn bộ 15 văn bản hiện chưa có thông tin hết hiệu lực -> ghi nhận chuẩn `null`. |
| **Tình trạng pháp lý đã xác định (`known`)** | **1 / 15** | **6.67%** | BLLD_2019 xác định chính thức là `"Còn hiệu lực"`. |
| **Tình trạng pháp lý chưa rõ (`unknown`)** | **14 / 15** | **93.33%** | 14 văn bản có raw status là `"Đã biết"` -> chuẩn hóa thành `"unknown"`. |

---

## 4. BÁO CÁO DANH SÁCH VĂN BẢN THIẾU DỮ LIỆU HIỆU LỰC TRONG RAW CORPUS

Theo yêu cầu: *"Đồng thời report document nào thiếu dữ liệu"*, danh sách 14 văn bản trong raw corpus thiếu thông tin ngày hiệu lực và tình trạng pháp lý được kiểm kê chi tiết:

1. `ND_12_2022` (Nghị định 12/2022/NĐ-CP)
2. `ND_135_2020` (Nghị định 135/2020/NĐ-CP)
3. `ND_145_2020` (Nghị định 145/2020/NĐ-CP)
4. `ND_152_2020` (Nghị định 152/2020/NĐ-CP)
5. `ND_219_2025` (Nghị định 219/2025/NĐ-CP)
6. `ND_70_2023` (Nghị định 70/2023/NĐ-CP)
7. `ND_74_2024` (Nghị định 74/2024/NĐ-CP)
8. `ND_83_2022` (Nghị định 83/2022/NĐ-CP)
9. `ND_99_2024` (Nghị định 99/2024/NĐ-CP)
10. `QD_992_2025` (Quyết định 992/QĐ-TTg)
11. `TT_09_2020` (Thông tư 09/2020/TT-BLĐTBXH)
12. `TT_10_2020` (Thông tư 10/2020/TT-BLĐTBXH)
13. `TT_11_2020` (Thông tư 11/2020/TT-BLĐTBXH)
14. `TT_20_2023` (Thông tư 20/2023/TT-BCT)

> [!NOTE]
> **Nguyên nhân gốc rễ**: Khi crawl dữ liệu từ Thư Viện Pháp Luật, bảng thuộc tính văn bản của trang web hiển thị nhãn `"Đã biết"` cho tài khoản vãng lai đối với tình trạng và ngày hiệu lực của các Nghị định/Thông tư. Do đó crawler đã thu về chuỗi `"Đã biết"`. Hệ thống V2 tuân thủ nghiêm ngặt nguyên tắc **KHÔNG tự bịa đặt metadata**, do đó chuyển đổi toàn bộ về `effective_from: null` và `legal_status: "unknown"`.

---

## 5. MẪU DỮ LIỆU ĐẦU RA (DATASET V2 CHUNK OUTPUT)

Mỗi chunk sinh ra từ các văn bản thiếu dữ liệu hiệu lực đều tuân thủ chính xác định dạng JSON theo đặc tả của TASK DATA-08:

```json
{
  "chunk_id": "ND_12_2022_D1_K1",
  "document_id": "ND_12_2022",
  "document_number": "12/2022/NĐ-CP",
  "document_title": "Nghị định số 12/2022/NĐ-CP QUY ĐỊNH XỬ PHẠT VI PHẠM HÀNH CHÍNH TRONG LĨNH VỰC LAO ĐỘNG, BẢO HIỂM XÃ HỘI, NGƯỜI LAO ĐỘNG VIỆT NAM ĐI LÀM VIỆC Ở NƯỚC NGOÀI THEO HỢP ĐỒNG",
  "document_type": "Nghị định",
  "chapter_number": "Chương I",
  "chapter_title": "NHỮNG QUY ĐỊNH CHUNG",
  "section_number": null,
  "section_title": null,
  "article_number": "Điều 1",
  "article_title": "Phạm vi điều chỉnh",
  "clause_number": "1",
  "point_number": null,
  "content": "Nghị định này quy định về hành vi vi phạm hành chính, hình thức xử phạt, mức xử phạt, biện pháp khắc phục hậu quả, thẩm quyền xử phạt, thẩm quyền lập biên bản vi phạm hành chính trong lĩnh vực lao động, bảo hiểm xã hội, người lao động Việt Nam đi làm việc ở nước ngoài theo hợp đồng.",
  "effective_from": null,
  "effective_to": null,
  "legal_status": "unknown",
  "source_url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-12-2022-ND-CP-xu-phat-vi-pham-hanh-chinh-lao-dong-bao-hiem-nguoi-lam-viec-nuoc-ngoai-479312.aspx",
  "parent_document": "ND_12_2022",
  "parent_article": "ND_12_2022_Điều1",
  "chunk_index": 0
}
```

---

## 6. KẾT QUẢ KIỂM THỬ (TEST SUITE VERIFICATION)

Bộ kiểm thử đơn vị tự động đã được thực thi thành công 100%:
- File kiểm thử chuyên biệt: `Data_Processing/test_date_status_v2.py` (6 test cases).
- Toàn bộ test suite: `Data_Processing/test_*.py` (**108 tests passing in 0.464s**).

Các ca kiểm thử trọng yếu được xác minh:
1. `test_01_valid_date_parsing_and_normalization`: Kiểm tra phân tích ngày hợp lệ (DD/MM/YYYY, D/M/YYYY, ISO YYYY-MM-DD, năm nhuận 29/02/2020) -> **PASSED**.
2. `test_02_missing_date_normalized_to_null`: Kiểm tra chuyển đổi `None`, rỗng, placeholder thành `null`, không tự tạo ngày -> **PASSED**.
3. `test_03_invalid_date_rejection_and_safety`: Bác bỏ ngày phi logic (32/01/2021, 29/02/2021 không nhuận, 15/13/2021, chuỗi text status) bằng `ValidationError` -> **PASSED**.
4. `test_04_effective_date_decoupled_from_issue_date`: Tách biệt độc lập `issue_date` và `effective_from`, ngăn ngừa gán chéo -> **PASSED**.
5. `test_05_unknown_legal_status_handling`: Kiểm tra chuẩn hóa trạng thái thành `"unknown"` và xuất đúng target dictionary -> **PASSED**.
6. `test_06_corpus_catalog_date_status_coverage`: Kiểm tra độ phủ và tính nhất quán trên toàn bộ 15 văn bản thật trong corpus -> **PASSED**.

---

## 7. BẢO TOÀN DỮ LIỆU GỐC V1

Mã băm SHA-256 của file dataset baseline V1 (`Data_Processing/KhoaLuan_Data_HoanChinh.json`) được xác minh độc lập:
- Hash: `7bdb170543734804c64945a02d5388a32399dd391ff3b2a3d029add1d3fe3fb4`
- Trạng thái: **Hoàn toàn nguyên vẹn (100% UNCHANGED)**.
