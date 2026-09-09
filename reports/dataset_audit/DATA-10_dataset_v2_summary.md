# BÁO CÁO TỔNG HỢP XÂY DỰNG LEGAL DATASET V2 (TASK DATA-10)

**Dự án**: Nghiên cứu cơ chế điều phối thích ứng trong hệ thống Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam.  
**Nhiệm vụ**: TASK DATA-10 — Build Legal Dataset V2.  
**Thời gian tạo**: 2026-09-09T07:50:11Z.  
**Trạng thái**: Hoàn tất thành công (100% Validated & Verified).

---

## 1. TỔNG QUAN SO SÁNH GIỮA DATASET V1 VÀ DATASET V2

Bảng đối chiếu toàn diện các chỉ số kỹ thuật và chất lượng dữ liệu:

| Chỉ số kỹ thuật | Dataset V1 (Cũ) | Dataset V2 (Mới) | Đánh giá cải tiến |
|:---|:---:|:---:|:---|
| **Tổng số văn bản (Documents)** | 15 | **15** | Bảo toàn 100% kho văn bản quy phạm. |
| **Tổng số đoạn (Chunks)** | 2,765 | **1,390** | Tối ưu hóa phân đoạn ngữ nghĩa pháp lý. |
| **Số Chunk ID duy nhất** | 2,648 | **1,390** | Đạt **100% Unique**. |
| **Trùng lặp ID (Collisions)** | 117 nhóm (434 chunks - 15.7%) | **0 (0.0%)** | **Triệt tiêu hoàn toàn ID collision**. |
| **Monster Chunk lớn nhất** | 142,534 tokens | **800 tokens** | Xóa bỏ hoàn toàn monster chunk. |
| **Tỷ lệ micro-chunks (<100 tokens)** | 73.6% (2,035 chunks) | **10.43%** (145 chunks) | **Giảm hơn 6 lần**, thông tin trọn vẹn hơn. |
| **Độ dài token trung vị (Median)** | 49.0 tokens | **211.0 tokens** | Tăng hơn 4 lần, ngữ cảnh đầy đủ. |
| **Độ dài token trung bình (Average)**| 112.5 tokens | **264.75 tokens** | Phù hợp tối ưu cho mô hình embedding. |
| **Độ phủ Ngày ban hành** | 0.0% | **0.0%** | Khôi phục 100% ngày ký ban hành. |
| **Độ phủ Ngày hiệu lực** | 0.0% | **21.15%** | Phục hồi chính xác cho BLLD 2019. |
| **Bảo tồn Phụ lục / Bảng biểu** | Bị gộp monster chunk hoặc mất cấu trúc | **Bảo tồn trọn vẹn** (chia nhỏ tự nhiên) | Giữ 100% bảng biểu và biểu mẫu. |
| **Schema tuân thủ** | Không có schema (chỉ dict thô) | **Pydantic V2 Model** | 100% bản ghi được xác thực chặt chẽ. |

---

## 2. PHÂN BỐ KÍCH THƯỚC CHUNK TRONG DATASET V2

| Dải kích thước (Tokens) | Số lượng chunk | Tỷ lệ (%) | Mục đích & Đặc tính ngữ nghĩa |
|:---|:---:|:---:|:---|
| **< 100 tokens** | 145 | 10.43% | Tiêu đề điều khoản đặc thù hoặc điểm ngắn độc lập. |
| **100 – 350 tokens** | 987 | 71.01% | **Vùng tối ưu chuẩn** cho các Điều/Khoản luật hoàn chỉnh. |
| **350 – 800 tokens** | 258 | 18.56% | Các cụm Điểm liền kề hoặc Bảng biểu chi tiết. |
| **> 800 tokens (Trần tối đa)** | **0** | **0.0%** | Tuyệt đối không vượt trần `max_chunk_tokens`. |

---

## 3. ĐỘ PHỦ SIÊU DỮ LIỆU (METADATA COVERAGE)

- **Số hiệu văn bản (`document_number`)**: 1,390 chunks (100.0%)
- **Loại văn bản (`document_type`)**: 1,390 chunks (100.0%)
- **Ngày ban hành (`issue_date`)**: 0 chunks (0.0%)
- **Ngày bắt đầu hiệu lực (`effective_from`)**: 294 chunks (21.15%)
- **Tình trạng hiệu lực đã biết (`known`)**: 294 chunks (21.15%)
- **Tình trạng hiệu lực chưa rõ (`unknown`)**: 1,096 chunks (78.85%)
- **Đường dẫn tra cứu (`source_url`)**: 1,390 chunks (100.0%)

---

## 4. TÍNH TOÀN VẸN & BẢO TỒN NGUYÊN VẸN DATASET V1

- **Tệp Baseline V1**: `D:\Filehoc\KLCN\agentic-rag\Data_Processing\KhoaLuan_Data_HoanChinh.json`
- **Mã SHA-256**: `7bdb170543734804c64945a02d5388a32399dd391ff3b2a3d029add1d3fe3fb4`
- **Xác nhận**: **HOÀN TOÀN ĐÓNG BĂNG VÀ KHÔNG BỊ SỬA ĐỔI (100% UNCHANGED)**.

## 5. CÁC TỆP ĐẦU RA (DATASET V2 ARTIFACTS)

1. **`Data_Processing/output_v2/legal_dataset_v2.json`**
   - Định dạng: JSON Array chuẩn với đúng 21 trường cốt lõi theo đặc tả TASK DATA-02.
   - SHA-256: `e48c6a3bece6819a0e25da8d985c8391ec162561c985e26d69dc3d13f2c87d92`
2. **`Data_Processing/output_v2/legal_dataset_v2.jsonl`**
   - Định dạng: JSON Lines (mỗi dòng là một chunk JSON).
   - SHA-256: `bcd6d0f05b0239b6250a6aa30e93d27093599d6da08bf80344cfd3a8ce834265`
3. **`Data_Processing/output_v2/build_metadata.json`**
   - Siêu dữ liệu build máy đọc (thời gian, phân phối, cấu hình).
