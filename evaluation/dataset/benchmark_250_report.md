# BÁO CÁO THẨM ĐỊNH BỘ DỮ LIỆU ĐÁNH GIÁ PHÁP LUẬT LAO ĐỘNG BENCHMARK 250
**Dự án:** Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam  
**Ngày lập báo cáo:** 08/11/2026  
**Trạng thái kiểm định:** Đạt tiêu chuẩn chất lượng 100% (Automated Quality Gate Passed)  

---

## 1. Tổng quan Bộ dữ liệu Kiểm thử Benchmark-250

Bộ dữ liệu kiểm thử **Benchmark-250** được thiết kế và xây dựng có hệ thống nhằm đánh giá định lượng và so sánh hiệu năng của 3 kiến trúc xử lý ngôn ngữ pháp lý:
1. **Traditional RAG:** Truy xuất thông thường kết hợp trả lời từ đoạn văn trích xuất.
2. **Corrective RAG (CRAG):** Cơ chế chấm điểm tài liệu truy xuất, tự động viết lại truy vấn hoặc kích hoạt tìm kiếm ngoài/từ chối khi tài liệu không đủ độ tin cậy.
3. **Adaptive Agentic RAG:** Tác tử thông minh định tuyến câu hỏi (Router), phân rã câu hỏi phức tạp đa chặng (Sub-query Decomposition), điều phối công cụ tra cứu và tổng hợp liên văn bản.

### Số liệu thống kê cốt lõi
- **Tổng số câu hỏi:** 250 câu (mã định danh từ `Q001` đến `Q250`).
- **Câu hỏi có căn cứ trả lời:** 200 câu (80.0%).
- **Câu hỏi yêu cầu từ chối (Refusal):** 50 câu (20.0%).
  - *Thiếu căn cứ trong kho tư liệu:* 25 câu (10.0%).
  - *Nằm ngoài phạm vi pháp luật lao động:* 25 câu (10.0%).
- **Quy mô kho ngữ liệu đối chiếu:** 19 văn bản quy phạm pháp luật, 2.117 đoạn văn bản (chunks).
- **Tổng số chunk trích dẫn thực tế:** 297 unique chunks.
- **Tỷ lệ chunk ID hợp lệ:** 100% (0 chunk bị lỗi hoặc không tìm thấy).
- **Độ phủ văn bản:** 19/19 văn bản trong kho vector store đều được trích dẫn và kiểm thử.

---

## 2. Phân bổ Câu hỏi theo 7 Nhóm Đánh giá Tiêu chuẩn

Bộ câu hỏi được phân bổ chặt chẽ theo tỷ lệ mục tiêu đã hoạch định:

| STT | Nhóm câu hỏi (`category`) | Số lượng câu | Tỷ lệ (%) | Mục tiêu đánh giá hệ thống |
|:---:|:---|:---:|:---:|:---|
| 1 | `single_article` (Đơn điều luật) | 35 | 14.0% | Khả năng truy xuất chính xác một điều khoản pháp lý cụ thể từ câu hỏi trực tiếp. |
| 2 | `single_doc_multi_chunk` (Đơn VB - đa đoạn) | 35 | 14.0% | Khả năng tổng hợp thông tin nằm rải rác ở nhiều khoản, điểm khác nhau trong cùng một văn bản. |
| 3 | `multi_document` (Đa văn bản) | 45 | 18.0% | Đánh giá năng lực tích hợp, liên kết quy định giữa Luật, Nghị định và Thông tư hướng dẫn. |
| 4 | `cross_reference` (Dẫn chiếu chéo) | 35 | 14.0% | Kiểm thử khả năng lần theo quy định viện dẫn điều luật (quy tắc "áp dụng theo quy định tại..."). |
| 5 | `complex_conditions` (Điều kiện phức tạp) | 50 | 20.0% | Xử lý các quy định pháp luật có nhiều tầng điều kiện, ngoại lệ, loại trừ và điều kiện kết hợp. |
| 6 | `insufficient_evidence` (Thiếu căn cứ) | 25 | 10.0% | Đánh giá năng lực của CRAG/Agentic trong việc nhận biết ranh giới dữ liệu và từ chối trả lời bịa đặt (Anti-hallucination). |
| 7 | `out_of_scope` (Ngoài phạm vi) | 25 | 10.0% | Đánh giá Router của Agentic RAG trong việc nhận diện và từ chối các lĩnh vực phi lao động (hình sự, giao thông, kỹ thuật, v.v.). |
| **Tổng** | **Toàn bộ 7 nhóm** | **250** | **100.0%** | **Bộ dữ liệu chuẩn hóa toàn diện cho nghiên cứu Khoá luận.** |

---

## 3. Ma trận Phủ Văn bản Pháp luật (Document Coverage Matrix)

Kho ngữ liệu gồm 19 văn bản quy phạm pháp luật lao động được phân bổ số lượng chunk và lượt trích dẫn như sau:

| STT | Mã văn bản (`document_id`) | Tên gọi văn bản quy phạm pháp luật | Tổng số chunks | Lượt trích dẫn căn cứ | Trạng thái pháp lý |
|:---:|:---|:---|:---:|:---:|:---|
| 1 | `BLLD_2019` | Bộ luật Lao động số 45/2019/QH14 | 294 | 182 | Còn hiệu lực |
| 2 | `LUAT_ATVSLD_2015` | Luật An toàn, vệ sinh lao động số 84/2015/QH13 | 203 | 21 | Còn hiệu lực |
| 3 | `LUAT_BHXH_2014` | Luật Bảo hiểm xã hội số 58/2014/QH13 | 181 | 4 | Còn hiệu lực |
| 4 | `LUAT_BHXH_2024` | Luật Bảo hiểm xã hội số 41/2024/QH15 | 278 | 30 | Còn hiệu lực |
| 5 | `LUAT_VIEC_LAM_2013` | Luật Việc làm số 38/2013/QH13 | 65 | 12 | Còn hiệu lực |
| 6 | `ND_12_2022` | Nghị định 12/2022/NĐ-CP xử phạt vi phạm hành chính lao động, BHXH | 238 | 35 | Còn hiệu lực |
| 7 | `ND_135_2020` | Nghị định 135/2020/NĐ-CP quy định về tuổi nghỉ hưu | 22 | 17 | Còn hiệu lực |
| 8 | `ND_145_2020` | Nghị định 145/2020/NĐ-CP hướng dẫn Bộ luật Lao động | 267 | 52 | Còn hiệu lực |
| 9 | `ND_152_2020` | Nghị định 152/2020/NĐ-CP về người lao động nước ngoài làm việc tại VN | 108 | 36 | Còn hiệu lực |
| 10 | `ND_219_2025` | Nghị định 219/2025/NĐ-CP sửa đổi bổ sung về quản lý lao động nước ngoài | 91 | 9 | Còn hiệu lực |
| 11 | `ND_70_2023` | Nghị định 70/2023/NĐ-CP sửa đổi, bổ sung Nghị định 152/2020/NĐ-CP | 39 | 65 | Còn hiệu lực |
| 12 | `ND_74_2024` | Nghị định 74/2024/NĐ-CP quy định mức lương tối thiểu vùng | 15 | 9 | Còn hiệu lực |
| 13 | `ND_83_2022` | Nghị định 83/2022/NĐ-CP quy định về tiền lương và trợ cấp | 9 | 6 | Còn hiệu lực |
| 14 | `ND_99_2024` | Nghị định 99/2024/NĐ-CP hướng dẫn chế độ tài chính, chính sách lao động | 3 | 2 | Còn hiệu lực |
| 15 | `QD_992_2025` | Quyết định 992/QĐ-TTg về công bố danh mục ngành nghề ưu tiên hỗ trợ | 6 | 2 | Còn hiệu lực |
| 16 | `TT_09_2020` | Thông tư 09/2020/TT-BLĐTBXH hướng dẫn danh mục vùng, nghề nặng nhọc | 37 | 13 | Còn hiệu lực |
| 17 | `TT_10_2020` | Thông tư 10/2020/TT-BLĐTBXH hướng dẫn nội dung hợp đồng lao động, kỷ luật | 37 | 12 | Còn hiệu lực |
| 18 | `TT_11_2020` | Thông tư 11/2020/TT-BLĐTBXH danh mục nghề nguy hiểm cho lao động chưa thành niên | 209 | 4 | Còn hiệu lực |
| 19 | `TT_20_2023` | Thông tư 20/2023/TT-BLĐTBXH quy định mức điều chỉnh tiền lương đóng BHXH | 15 | 7 | Còn hiệu lực |

### Phân tích đặc thù hiệu lực và chuyển tiếp pháp luật
1. **Luật Bảo hiểm xã hội 2024 (`LUAT_BHXH_2024`):**
   - Đã được cập nhật trạng thái `"Còn hiệu lực"` trên toàn bộ hệ thống cơ sở dữ liệu và vector store (ChromaDB), có hiệu lực thi hành từ ngày **01/07/2025**.
   - Các câu hỏi khai thác chuyên sâu quy định mới của Luật BHXH 2024: Giảm số năm đóng BHXH tối thiểu để hưởng lương hưu xuống 15 năm (Điều 64); trợ cấp hưu trí xã hội cho người từ đủ 75 tuổi (Điều 21); chế độ thai sản khi người mẹ không đủ điều kiện đóng mà chồng tham gia (Điều 50); thanh toán BHXH một lần có điều kiện (Điều 70).
   - Mối quan hệ với `LUAT_BHXH_2014`: Giữ lại các câu hỏi đối chiếu chuyển tiếp hoặc phạm vi quy định riêng biệt mà Luật 2024 kế thừa/sửa đổi.

2. **Lao động nước ngoài (`ND_152_2020`, `ND_70_2023`, `ND_219_2025`):**
   - Nghị định 70/2023/NĐ-CP và Nghị định 219/2025/NĐ-CP sửa đổi các tiêu chuẩn chuyên gia, lao động kỹ thuật, thủ tục báo cáo giải trình nhu cầu sử dụng lao động nước ngoài và các trường hợp không thuộc diện cấp giấy phép lao động.
   - Các câu hỏi trong nhóm `multi_document` và `complex_conditions` kết nối chính xác quy định nền tảng của NĐ 152/2020 với các nội dung sửa đổi, bổ sung mới nhất của NĐ 70/2023 và NĐ 219/2025.

3. **Tiền lương tối thiểu vùng (`ND_74_2024`):**
   - Nghị định 74/2024/NĐ-CP có hiệu lực từ 01/07/2024 (thay thế Nghị định 38/2022/NĐ-CP), quy định 4 vùng lương tối thiểu tháng và lương tối thiểu giờ. Bộ câu hỏi đã cập nhật 100% các mức lương hiện hành này.

---

## 4. Kết quả Kiểm định Chất lượng Tự động (Automated Quality Gate)

Hệ thống thẩm định mã nguồn (`builder.py` & `test_benchmark_250.py`) đã chạy kiểm tra tự động trên toàn bộ 250 câu hỏi:

1. **Kiểm tra Schema JSON:**
   - 250/250 câu hỏi tuân thủ 100% cấu trúc quy định tại `evaluation/dataset/schema.json` (Draft-07).
   - Các trường bắt buộc: `question_id`, `question`, `category`, `gold_sources`, `reference_answer`, `requires_refusal`.

2. **Kiểm tra Mã định danh (IDs):**
   - Không có ID bị khuyết tật hoặc trùng lặp. Chuỗi ID tuần tự: `Q001` -> `Q250`.
   - Không có câu hỏi nào bị trùng lặp ngữ nghĩa (exact string hoặc normalized text).

3. **Kiểm tra Truy nguyên Căn cứ (Traceability & Grounding):**
   - 200 câu hỏi trả lời được đều có ít nhất một nguồn căn cứ pháp lý rõ ràng.
   - 100% chunk IDs (tổng cộng 297 unique chunks) đều tìm thấy chính xác trong kho dữ liệu `legal_dataset_v2.json`. Số chunk lỗi = 0.

4. **Kiểm tra Chính sách Từ chối (Refusal Policy):**
   - Toàn bộ 50 câu hỏi thuộc nhóm `insufficient_evidence` và `out_of_scope` đều có `requires_refusal: true` và `gold_sources: []`.
   - `reference_answer` tuân thủ đúng câu trả lời từ chối quy chuẩn: *"Không tìm thấy đủ căn cứ pháp lý trong dữ liệu được cung cấp để đưa ra kết luận đáng tin cậy."*

---

## 5. Hướng dẫn Quy trình Rà soát Chuyên gia Pháp lý (Legal Expert Review)

Tệp Excel thẩm định chuyên biệt `evaluation/dataset/benchmark_250_review.xlsx` đã được tạo lập với các trường phục vụ quy trình đánh giá:
- **Cột trạng thái ban đầu:** Toàn bộ 250 dòng được đặt mặc định là `pending_review` (chờ chuyên gia duyệt).
- **Thông tin thẩm định cần chuyên gia điền:**
  - *Chuyên gia rà soát*: Họ và tên chuyên gia (Luật sư, Chuyên viên pháp chế, Giảng viên luật).
  - *Vai trò chuyên gia*: Đơn vị công tác, chức danh chuyên môn.
  - *Ngày rà soát*: Định dạng YYYY-MM-DD.
  - *Đánh giá tính chính xác pháp lý*: Thang điểm 1-5 (hoặc Đạt/Không đạt).
  - *Đánh giá tính đầy đủ căn cứ*: Thang điểm 1-5 (hoặc Đạt/Không đạt).
  - *Đánh giá tính tự nhiên của câu hỏi*: Thang điểm 1-5 (hoặc Đạt/Không đạt).
  - *Ghi chú / Ý kiến đóng góp*: Các đề xuất chỉnh lý từ ngữ hoặc bổ sung điều luật (nếu có).

---

## 6. Hướng dẫn Sử dụng Đánh giá Hiệu năng Hệ thống RAG

Bộ dữ liệu này sẵn sàng kết nối trực tiếp vào pipeline kiểm thử (`evaluation/`):
- **Traditional RAG:** Đo lường Recall@K, Context Precision, Faithfulness và Answer Relevance trên 200 câu hỏi có căn cứ.
- **Corrective RAG:** Đo lường tỷ lệ kích hoạt cơ chế sửa sai (Correction Trigger Rate), tỷ lệ lọc nhiễu đoạn văn và độ chính xác khi phát hiện câu hỏi `insufficient_evidence`.
- **Adaptive Agentic RAG:** Đánh giá độ chính xác phân loại định tuyến (Routing Accuracy) trên nhóm `out_of_scope` và hiệu quả phân rã truy vấn đa chặng (Sub-query Execution) trên nhóm `multi_document` và `complex_conditions`.

---
*Báo cáo được khởi tạo tự động bởi Antigravity Legal Evaluation Suite.*
