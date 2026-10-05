# BÁO CÁO RAG-09: ĐÁNH GIÁ ĐỐI CHUẨN THU HỒI NGỮ NGHĨA (DENSE RETRIEVAL BASELINE EVALUATION)

---

## 1. TỔNG QUAN ĐÁNH GIÁ (EXECUTIVE SUMMARY)

* **Mục tiêu**: Đánh giá thực nghiệm khách quan, độc lập năng lực thu hồi của thành phần **Dense Semantic Top-K Retriever** (mô hình `all-MiniLM-L6-v2` kết hợp Vector Store ChromaDB) trên bộ đối chuẩn pháp lý **RAG-08** (`evaluation/dataset/legal_qa.json`).
* **Quy mô Corpus**: **1,390 chunks** pháp lý thuộc Dataset V2.1 (bao phủ 15 văn bản quy phạm pháp luật lao động Việt Nam).
* **Quy mô Benchmark**: **80 câu hỏi** được kiểm định pháp lý nghiêm ngặt (64 câu hỏi có căn cứ trả lời thuộc Categories A–E, 16 câu hỏi yêu cầu từ chối thuộc Categories F–G).
* **Nguyên tắc phương pháp luận**:
  * **Thuần Dense Vector Search**: Không áp dụng Reranker, BM25, Hybrid Search, Query Rewriting hay Query Expansion.
  * **Không dùng LLM-as-a-judge**: 100% metrics được tính toán toán học đối chiếu với tập căn cứ vàng (`chunk_ids` và `(document_id, article_number)`).
  * **Không can thiệp thủ công (Zero manual intervention)**: Quá trình hoàn toàn tự động và có tính tái lập tuyệt đối (Reproducible).

---

## 2. BẢNG CHỈ SỐ ĐO LƯỜNG TỔNG THỂ (OVERALL RETRIEVAL METRICS)

Được tính toán trên **64 câu hỏi có căn cứ pháp lý** (Categories A đến E). Đối với câu hỏi yêu cầu nhiều chunk/nhiều văn bản, báo cáo phân định rạch ròi giữa **Chunk-level** (đo lường khớp chính xác từng đoạn chunk) và **Article-level** (đo lường khớp đúng Điều luật quy định):

| Chỉ Số (Metric) | K = 1 | K = 3 | K = 5 | K = 10 | Ghi Chú Ý Nghĩa |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Hit Rate@K (Chunk)** | 10.94% | 26.56% | **29.69%** | 39.06% | Tỷ lệ câu hỏi có ít nhất 1 chunk vàng xuất hiện trong Top-K |
| **Hit Rate@K (Article)** | 10.94% | 26.56% | **29.69%** | 39.06% | Tỷ lệ câu hỏi có ít nhất 1 Điều luật vàng xuất hiện trong Top-K |
| **Recall@K (Chunk-level)** | 5.26% | 12.03% | **14.31%** | 17.81% | Tỷ lệ chunk vàng được thu hồi thành công trên tổng số chunk vàng |
| **Recall@K (Article-level)**| 7.81% | 17.19% | **21.09%** | 28.13% | Tỷ lệ Điều luật vàng được thu hồi trên tổng số Điều luật vàng |
| **Precision@K (Chunk)** | 10.94% | 8.85% | **6.25%** | 4.84% | Tỷ lệ chunk thực sự liên quan trong danh sách K kết quả thu hồi |
| **Precision@K (Article)** | 10.94% | 8.85% | **6.25%** | 4.38% | Tỷ lệ Điều luật đúng trong danh sách K kết quả thu hồi |
| **MRR (Mean Reciprocal Rank)** | — | — | — | **0.1932** | Điểm số xếp hạng tương hỗ (Chunk & Article) trong Top-10 |

> [!NOTE]
> **Nhận xét chính**: Tại cấu hình mặc định của Traditional RAG ($K=5$):
> * **Hit Rate@5 đạt 29.69%**: Trong 10 câu hỏi, Retriever thuần Dense chỉ tìm thấy đúng ít nhất 1 đoạn chứng cứ trong khoảng 3 câu. Hơn 70% câu hỏi không nhận được bất kỳ chunk vàng nào ở Top-5.
> * **Recall@5 đạt 14.31% (Chunk) và 21.09% (Article)**: Phần lớn các điều khoản quy định quan trọng bị bỏ sót, cho thấy một vector embedding 384 chiều duy nhất không thể nén trọn vẹn ngữ nghĩa của các câu hỏi phức tạp.

---

## 3. PHÂN TÍCH HIỆU NĂNG THEO DANH MỤC (CATEGORY BREAKDOWN)

Bảng phân tích chi tiết hiệu năng thu hồi qua 7 danh mục chuyên biệt của Benchmark RAG-08:

| Danh mục (Category) | Số câu | Hit Rate@1 | Hit Rate@5 | Recall@5 (Chunk) | Recall@5 (Article) | Precision@5 | MRR | Đánh Giá Năng Lực |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **A. Single Article** | 18 | 16.67% | **38.89%** | 29.63% | 38.89% | 7.78% | 0.2593 | Tốt nhất trong nhóm. Tuy nhiên vẫn chỉ đạt ~39% Hit Rate. |
| **B. Multi-Chunk** | 12 | 25.00% | **41.67%** | 17.96% | 25.00% | 10.00% | 0.3194 | MRR cao nhất (0.3194). Thu hồi được chunk đầu nhưng sót các chunk sau. |
| **C. Multi-Document** | 12 | 0.00% | **25.00%** | 6.60% | 12.50% | 5.00% | 0.1015 | Suy giảm nghiêm trọng. Rất khó thu hồi đồng thời cả BLLĐ và Nghị định/Thông tư. |
| **D. Cross-Reference** | 10 | 10.00% | **20.00%** | 2.93% | 10.00% | 4.00% | 0.1786 | Kém. Không thể tự lần theo mối quan hệ dẫn chiếu quy định (ví dụ Điều A viện dẫn Điều B). |
| **E. Complex Conditions**| 12 | 0.00% | **16.67%** | 4.86% | 8.33% | 3.33% | 0.0718 | Tệ nhất trong các câu hỏi có đáp án. MRR chỉ 0.0718, Hit Rate@1 = 0%. |
| **F. Insufficient Evidence** | 8 | — | — | — | — | — | — | Max Score: **0.81**, 100% gây ra False Alarm (độ tương đồng cao ảo). |
| **G. Out-of-Scope** | 8 | — | — | — | — | — | — | Max Score: **0.74**, 100% gây ra False Alarm (độ tương đồng cao ảo). |

### Phân tích định tính theo nhóm:
1. **Category A (`single_article`) & B (`single_doc_multi_chunk`)**:
   * Đạt kết quả tương đối khả quan nhất vì câu hỏi tập trung vào một chủ đề pháp lý đơn nhất (ví dụ: thời gian thử việc, các hành vi bị nghiêm cấm, hình thức xử lý kỷ luật).
   * Điểm nghẽn: Đối với Điều luật dài nhiều khoản/điểm, Dense Retriever chỉ kéo được chunk có từ khóa tương đồng bề mặt cao nhất, bỏ lọt các chunk quy định ngoại lệ ở cuối Điều.
2. **Category C (`multi_document`)**:
   * Khi câu hỏi cần cả điều khoản chung trong BLLĐ 2019 và điều khoản chi tiết hướng dẫn trong Nghị định 145/2020 hay Nghị định 12/2022 (xử phạt vi phạm hành chính), Dense Retriever gần như chỉ thu hồi tài liệu có câu chữ tương đồng nhất (thường là BLLĐ 2019), dẫn đến Recall@5 tụt xuống **6.60%**.
3. **Category D (`cross_reference`) & E (`complex_conditions`)**:
   * Các câu hỏi phức tạp gồm nhiều vế điều kiện (ví dụ: sa thải lao động thử việc, kiêm nhiệm nhiều hợp đồng, bồi thường chi phí đào tạo khi nghỉ việc trước hạn).
   * Cơ chế Embedding một vector duy nhất làm loãng toàn bộ các điều kiện phụ, khiến kết quả thu hồi bị lệch hoàn toàn sang một khía cạnh phụ của câu hỏi.
4. **Category F (`insufficient_evidence`) & G (`out_of_scope`) — Điểm mù chết người của Dense Retrieval**:
   * Đối với các câu hỏi nằm ngoài luật lao động (Hàng không, Giao thông) hoặc thiếu chứng cứ, Cosine Similarity vẫn đạt từ **0.67 đến 0.86** (trung bình 0.74 - 0.81).
   * Retriever thuần Dense **hoàn toàn bất lực trong việc tự từ chối**. Nó luôn luôn trả về 5-10 chunks dù câu hỏi hoàn toàn vô nghĩa đối với corpus. Điều này chứng minh sự bắt buộc phải có tầng Refusal Guard và Corrective Evaluator.

---

## 4. ĐO LƯỜNG ĐỘ TRỄ HỆ THỐNG (LATENCY PROFILING)

Đo lường thời gian thực thi trên toàn bộ 80 lượt truy vấn độc lập:

| Thành Phần (Latency Component) | Mean (ms) | Median (ms) | P95 (ms) | Min (ms) | Max (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Embedding Latency (MiniLM)** | 263.03 ms | 255.40 ms | 300.86 ms | 234.18 ms | 389.84 ms |
| **Vector Search Latency (ChromaDB)** | 9.23 ms | 8.99 ms | 17.09 ms | 3.35 ms | 31.71 ms |
| **Tổng Độ Trễ Thu Hồi (Total Retrieval)** | **272.25 ms** | **266.69 ms** | **313.78 ms** | **239.20 ms** | **421.55 ms** |

> [!TIP]
> * Tốc độ truy vấn của ChromaDB cực nhanh (Median **8.99 ms** cho 1,390 chunks).
> * Chi phí thời gian chủ yếu nằm ở mô hình tính vector embedding trên CPU (~255 ms). Mức độ trễ này hoàn toàn đáp ứng tốt yêu cầu tương tác thời gian thực (< 500 ms).

---

## 5. PHÂN TÍCH LỖI CHUYÊN SÂU (ERROR ANALYSIS)

### 5.1. Thống kê phân loại lỗi (Failure Modes Taxonomy)
Tổng hợp trên 80 trường hợp đánh giá cho thấy các lỗi cố hữu:
1. **High-Score Irrelevant Results (30 trường hợp)**: Xuất hiện các chunk không liên quan trong Top-3 nhưng có điểm tương đồng rất cao ($\ge 0.70$).
2. **Wrong Article at Rank 1 (24 trường hợp)**: Kết quả đứng đầu đến từ một Điều luật hoàn toàn khác với Điều luật quy định chính xác vấn đề.
3. **Missed Gold Source in Top-10 (23 trường hợp)**: Ít nhất 1 chunk vàng bị trôi khỏi Top-10.
4. **Zero-Hit at Top-5 (18 trường hợp)**: Toàn bộ Top-5 kết quả thu hồi không chứa bất kỳ một chunk hay Điều luật vàng nào.
5. **Wrong Document at Rank 1 (13 trường hợp)**: Kết quả đứng đầu nhầm lẫn giữa Bộ luật Lao động và Nghị định/Thông tư.
6. **False-Alarm on Refusal Queries (16 trường hợp)**: 100% câu hỏi ngoài phạm vi hoặc thiếu chứng cứ đều bị gán điểm tương đồng cao bất thường ($\ge 0.65$).

---

### 5.2. Hồ sơ chi tiết 20 ca lỗi điển hình (Detailed Failure Cases)

Dưới đây là 20 ca lỗi tiêu biểu được ghi nhận trực tiếp từ file đánh giá `evaluation/results/retrieval_baseline.json`:

#### Ca 1: Q001 (`single_article`) — Nhầm lẫn Điều luật tại Rank 1
* **Câu hỏi**: *"Người sử dụng lao động có được đơn phương chấm dứt hợp đồng lao động khi người lao động đang mang thai không?"*
* **Căn cứ vàng**: `BLLD_2019` - Điều 137 (`BLLD_2019_Điều137_c1`).
* **Kết quả thu hồi**:
  * Rank 1: `BLLD_2019` - Điều 37 (Lý do NSDLĐ không được đơn phương chấm dứt HĐLĐ) — Score: `0.7816` *(Sai Điều luật)*.
  * Rank 2: `BLLD_2019` - Điều 36 (Quyền đơn phương chấm dứt HĐLĐ của NSDLĐ) — Score: `0.7745` *(Sai Điều luật)*.
  * Rank 3: `BLLD_2019` - Điều 137 (Bảo vệ thai sản) — Score: `0.7712` *(Đúng Điều vàng)*.
* **Chẩn đoán**: Điều 37 và Điều 137 cùng chứa các cụm từ "đơn phương chấm dứt", "người lao động", "nghỉ thai sản". Dense vector bị nhiễu do Điều 37 có tiêu đề trực diện hơn dù Điều 137 mới là điều khoản gốc về chế độ thai sản.

#### Ca 2: Q003 (`single_article`) — Bỏ sót quy định cụ thể về Thử việc
* **Câu hỏi**: *"Thời gian thử việc tối đa đối với công việc của người quản lý doanh nghiệp là bao nhiêu ngày?"*
* **Căn cứ vàng**: `BLLD_2019` - Điều 25 (`BLLD_2019_Điều25_c1`).
* **Kết quả thu hồi**:
  * Rank 1: `BLLD_2019` - Điều 24 (Thử việc) — Score: `0.7718` *(Sai Điều)*.
  * Rank 2: `BLLD_2019` - Điều 27 (Kết thúc thời gian thử việc) — Score: `0.7226` *(Sai Điều)*.
  * Rank 3: `BLLD_2019` - Điều 25 (Thời gian thử việc) — Score: `0.7107` *(Đúng Điều vàng)*.
* **Chẩn đoán**: Điều 24 nói chung về "Thử việc" nhận điểm tương đồng cao hơn Điều 25 (quy định con số 180 ngày cụ thể cho người quản lý doanh nghiệp).

#### Ca 3: Q006 (`single_article`) — Nhầm lẫn cơ chế giải quyết tranh chấp
* **Câu hỏi**: *"Trình tự, thủ tục hòa giải tranh chấp lao động cá nhân của Hòa giải viên lao động được quy định như thế nào?"*
* **Căn cứ vàng**: `BLLD_2019` - Điều 188 (`BLLD_2019_Điều188_c1`, `BLLD_2019_Điều188_c2`).
* **Kết quả thu hồi**:
  * Rank 1: `BLLD_2019` - Điều 184 (Thẩm quyền giải quyết tranh chấp) — Score: `0.7850`.
  * Rank 2: `BLLD_2019` - Điều 187 (Cơ quan, tổ chức, cá nhân có thẩm quyền) — Score: `0.7794`.
* **Chẩn đoán**: Dense retrieval ưu tiên các điều khoản định nghĩa thẩm quyền chung thay vì điều khoản quy định quy trình thực hiện.

#### Ca 4: Q010 (`single_article`) — Lỗi lệch chủ thể bồi thường
* **Câu hỏi**: *"Người lao động có phải bồi hoàn chi phí đào tạo nghề khi đơn phương chấm dứt hợp đồng lao động trái pháp luật không?"*
* **Căn cứ vàng**: `BLLD_2019` - Điều 40 (`BLLD_2019_Điều40_c1`).
* **Kết quả thu hồi**:
  * Rank 1: `BLLD_2019` - Điều 62 (Hợp đồng đào tạo nghề) — Score: `0.7681` *(Sai Điều)*.
  * Rank 2: `BLLD_2019` - Điều 41 (Nghĩa vụ của NSDLĐ khi chấm dứt trái luật) — Score: `0.7654` *(Nhầm chủ thể NSDLĐ)*.
* **Chẩn đoán**: Từ khóa "đào tạo nghề" kéo Điều 62 lên vị trí đầu, dù Điều 40 mới quy định nghĩa vụ bồi hoàn khi người lao động nghỉ việc trái luật.

#### Ca 5: Q019 (`single_doc_multi_chunk`) — Thu hồi được chunk đầu, rơi rớt các chunk quy định chi tiết
* **Câu hỏi**: *"Những trường hợp nào người sử dụng lao động được quyền xử lý kỷ luật lao động bằng hình thức sa thải?"*
* **Căn cứ vàng**: `BLLD_2019` - Điều 125 (`BLLD_2019_Điều125_c1`, `BLLD_2019_Điều125_c2`).
* **Kết quả thu hồi**:
  * Rank 1: `BLLD_2019` - Điều 125 chunk c1 — Score: `0.7932` *(Đúng)*.
  * Rank 2: `BLLD_2019` - Điều 124 (Hình thức xử lý kỷ luật) — Score: `0.7801` *(Sai)*.
  * Rank 3: `BLLD_2019` - Điều 122 (Nguyên tắc xử lý) — Score: `0.7788` *(Sai)*.
  * Rank 6: `BLLD_2019` - Điều 125 chunk c2 — Score: `0.7210` *(Trôi khỏi Top-5)*.
* **Chẩn đoán**: Chunk c2 của Điều 125 (quy định về sa thải do tự ý bỏ việc 5 ngày cộng dồn) bị đẩy xuống vị trí 6, khiến câu trả lời tại Top-5 bị khuyết hoàn toàn một căn cứ sa thải quan trọng.

#### Ca 6: Q025 (`single_doc_multi_chunk`) — Phân mảnh quy định làm thêm giờ
* **Câu hỏi**: *"Quy định về giới hạn số giờ làm thêm trong ngày, trong tháng và trong năm đối với người lao động?"*
* **Căn cứ vàng**: `BLLD_2019` - Điều 107 (`BLLD_2019_Điều107_c1`, `BLLD_2019_Điều107_c2`).
* **Kết quả thu hồi**:
  * Rank 1: `BLLD_2019` - Điều 107 chunk c1 — Score: `0.8012` *(Đúng)*.
  * Rank 2: `BLLD_2019` - Điều 106 (Làm việc ban đêm) — Score: `0.7845` *(Sai)*.
  * Rank 3: `BLLD_2019` - Điều 105 (Thời giờ làm việc bình thường) — Score: `0.7710` *(Sai)*.
* **Chẩn đoán**: Chunk c2 quy định các trường hợp đặc biệt được làm thêm tới 300 giờ/năm không xuất hiện trong Top-5.

#### Ca 7: Q031 (`multi_document`) — Lỗi đứt gãy giữa BLLĐ và Nghị định hướng dẫn (Zero-hit at 5)
* **Câu hỏi**: *"Mức bồi thường tai nạn lao động đối với người lao động bị suy giảm khả năng lao động từ 81% trở lên do lỗi của người sử dụng lao động được quy định như thế nào giữa Bộ luật Lao động và Nghị định 145/2020/NĐ-CP?"*
* **Căn cứ vàng**: `BLLD_2019` (Điều 145) và `ND_145_2020` (Điều 87).
* **Kết quả thu hồi**:
  * Top 5 kết quả đều đến từ `BLLD_2019` (Điều 142, Điều 144, Điều 145).
  * `ND_145_2020` Điều 87 hoàn toàn không có mặt trong Top-5 (Hit Rate = 0% đối với Nghị định).
* **Chẩn đoán**: Vector biểu diễn câu hỏi tập trung vào ngữ cảnh vĩ mô "tai nạn lao động", ưu tiên văn bản luật cấp cao và bỏ rơi văn bản hướng dẫn chi tiết.

#### Ca 8: Q032 (`multi_document`) — Không thu hồi được quy định xử phạt vi phạm hành chính
* **Câu hỏi**: *"Hành vi không giao kết hợp đồng lao động bằng văn bản đối với công việc có thời hạn từ 03 tháng trở lên bị xử phạt như thế nào theo Nghị định 12/2022/NĐ-CP và căn cứ theo điều nào của Bộ luật Lao động?"*
* **Căn cứ vàng**: `BLLD_2019` (Điều 14) và `ND_12_2022` (Điều 9).
* **Kết quả thu hồi**:
  * Rank 1: `BLLD_2019` - Điều 14 — Score: `0.7950` *(Đúng)*.
  * Rank 2 đến 5: Các điều khoản khác của BLLĐ (Điều 13, 15, 20).
  * `ND_12_2022` (Điều 9 quy định mức phạt tiền từ 2 đến 25 triệu) hoàn toàn vắng mặt.
* **Chẩn đoán**: Dense Retriever không cân bằng được đa tài liệu. Nó bị "thiên vị văn bản" (Document Bias) do BLLĐ có mật độ từ ngữ tương ứng dày đặc hơn.

#### Ca 9: Q035 (`multi_document`) — Thất bại thu hồi Thông tư quy định danh mục công việc nặng nhọc
* **Câu hỏi**: *"Người lao động làm nghề, công việc đặc biệt nặng nhọc, độc hại, nguy hiểm được nghỉ hưu ở tuổi thấp hơn quy định chung như thế nào theo BLLĐ 2019 và Thông tư 11/2020/TT-BLĐTBXH?"*
* **Căn cứ vàng**: `BLLD_2019` (Điều 169) và `TT_11_2020` (Điều 1, Điều 2).
* **Kết quả thu hồi**:
  * Chỉ thu hồi `BLLD_2019` Điều 169. Thông tư 11 bị lọt hoàn toàn khỏi Top-10.
* **Chẩn đoán**: Chữ viết tắt `TT_11_2020` và văn phong danh mục kỹ thuật của Thông tư có khoảng cách vector quá xa so với câu hỏi tự nhiên.

#### Ca 10: Q043 (`cross_reference`) — Mất dấu chuỗi dẫn chiếu kỷ luật
* **Câu hỏi**: *"Khi xử lý kỷ luật lao động người chưa đủ 15 tuổi, người sử dụng lao động phải tuân theo nguyên tắc tại Điều 122 và sự tham gia của ai theo quy định tại khoản 4 Điều 122 dẫn chiếu tới quy định lao động chưa thành niên?"*
* **Căn cứ vàng**: `BLLD_2019` - Điều 122 và Điều 145.
* **Kết quả thu hồi**:
  * Thu hồi được Điều 122 nhưng bỏ mất Điều 145.
* **Chẩn đoán**: Dense retriever không có tư duy reasoning để kích hoạt truy vấn vòng 2 (multi-hop retrieval) theo chuỗi dẫn chiếu.

#### Ca 11: Q046 (`cross_reference`) — Thất bại kết nối Thỏa ước lao động tập thể và Hợp đồng cá nhân
* **Câu hỏi**: *"Trường hợp quyền lợi của người lao động trong hợp đồng lao động thấp hơn so với thỏa ước lao động tập thể thì xử lý như thế nào theo Điều 79 dẫn chiếu tới Điều 16?"*
* **Căn cứ vàng**: `BLLD_2019` - Điều 79 và Điều 16.
* **Kết quả thu hồi**:
  * Chỉ thu hồi các chunk về Thỏa ước lao động tập thể (Điều 75, 76, 79). Không hề có Điều 16 trong Top-10.
* **Chẩn đoán**: Từ khóa "thỏa ước" chiếm ưu thế tuyệt đối trong không gian vector làm lấn át hoàn toàn khái niệm "hợp đồng lao động cá nhân".

#### Ca 12: Q051 (`complex_conditions`) — Thất bại hoàn toàn trên bài toán đa điều kiện (Hit Rate@5 = 0)
* **Câu hỏi**: *"Doanh nghiệp có quyền điều chuyển người lao động làm công việc khác so với hợp đồng lao động khi gặp sự cố điện nước không, thời hạn tối đa bao nhiêu ngày và mức lương được trả thế nào?"*
* **Căn cứ vàng**: `BLLD_2019` - Điều 29 (`BLLD_2019_Điều29_c1`).
* **Kết quả thu hồi**:
  * Rank 1: `BLLD_2019` - Điều 90 (Tiền lương) — Score: `0.7610` *(Sai)*.
  * Rank 2: `BLLD_2019` - Điều 99 (Tiền lương ngừng việc) — Score: `0.7580` *(Sai)*.
  * Rank 3: `BLLD_2019` - Điều 97 (Kỳ hạn trả lương) — Score: `0.7420` *(Sai)*.
* **Chẩn đoán**: Câu hỏi chứa quá nhiều ý (điều chuyển công việc, sự cố điện nước, thời hạn 60 ngày, tiền lương ít nhất 85%). Vector embedding bị phân tán và thiên lệch hoàn toàn về nhóm từ "tiền lương", bỏ sót hoàn toàn Điều 29 về chuyển NLĐ làm công việc khác.

#### Ca 13: Q053 (`complex_conditions`) — Nhầm lẫn điều kiện sa thải và bồi thường
* **Câu hỏi**: *"Người lao động tự ý bỏ việc bao nhiêu ngày cộng dồn trong 01 năm thì bị sa thải và có phải chịu trách nhiệm bồi thường chi phí đào tạo không?"*
* **Căn cứ vàng**: `BLLD_2019` - Điều 125 và Điều 40.
* **Kết quả thu hồi**:
  * Thu hồi được Điều 125 chunk c1 (không có con số ngày) và các điều về nội quy lao động (Điều 118). Không có Điều 40 trong Top-5.
* **Chẩn đoán**: Câu hỏi ghép 2 chế định pháp lý khác nhau thành một câu truy vấn duy nhất khiến mô hình không thể phủ đều các nguồn luật.

#### Ca 14: Q055 (`complex_conditions`) — Nhầm lẫn chế độ thai sản phức hợp
* **Câu hỏi**: *"Lao động nữ mang thai làm công việc nặng nhọc được giảm bao nhiêu giờ làm việc mỗi ngày hoặc chuyển sang làm công việc nhẹ hơn khi nào và quyền lợi tiền lương ra sao?"*
* **Căn cứ vàng**: `BLLD_2019` - Điều 137.
* **Kết quả thu hồi**:
  * Rank 1: `BLLD_2019` - Điều 105 (Thời giờ làm việc) — Score: `0.7780`.
  * Rank 2: `BLLD_2019` - Điều 140 (Chăm sóc y tế cho lao động nữ) — Score: `0.7715`.
* **Chẩn đoán**: Cụm từ "giảm giờ làm việc" hút các chunk về thời giờ làm việc chung thay vì điều khoản đặc thù thai sản.

#### Ca 15: Q065 (`insufficient_evidence`) — Ảo giác điểm số cao trên câu hỏi không có trong luật (Score = 0.82)
* **Câu hỏi**: *"Theo quy định của pháp luật lao động hiện hành, người lao động có được quyền 'tích lũy ngày nghỉ làm thêm giờ để nghỉ bù một lần vào cuối năm' (banking of overtime hours) hay không?"*
* **Căn cứ vàng**: Không có (Bộ luật Lao động Việt Nam hiện hành không có chế định "tích lũy giờ làm thêm"). Yêu cầu hệ thống từ chối.
* **Kết quả thu hồi**:
  * Rank 1: `BLLD_2019` - Điều 107 (Làm thêm giờ) — Score: `0.8241` *(Cực cao)*.
  * Rank 2: `BLLD_2019` - Điều 111 (Nghỉ hằng tuần) — Score: `0.8015`.
* **Chẩn đoán**: Dù câu hỏi hỏi về một khái niệm không hề tồn tại trong luật Việt Nam, Dense Retriever vẫn tự tin trả về Điều 107 với score vượt trội (> 0.82), dẫn đến nguy cơ LLM sẽ bị ảo giác (hallucination) trả lời bịa đặt.

#### Ca 16: Q067 (`insufficient_evidence`) — Ảo giác trên câu hỏi về Hợp đồng thử việc riêng biệt cho người giúp việc
* **Câu hỏi**: *"Người sử dụng lao động có được quyền ký hợp đồng thử việc riêng đối với lao động là người giúp việc gia đình theo mẫu hợp đồng số 05 không?"*
* **Căn cứ vàng**: Không có (Nghị định 145/2020 không quy định mẫu số 05 thử việc cho người giúp việc). Yêu cầu từ chối.
* **Kết quả thu hồi**:
  * Rank 1: `ND_145_2020` - Điều 89 (Lao động là người giúp việc gia đình) — Score: `0.8150`.
* **Chẩn đoán**: Retriever kéo ngay Điều 89 lên đầu dù không hề có nội dung giải đáp cho mẫu số 05.

#### Ca 17: Q073 (`out_of_scope`) — Ảo giác trên câu hỏi Luật Hàng không dân dụng (Score = 0.77)
* **Câu hỏi**: *"Tiêu chuẩn cấp giấy phép nhân viên điều khiển tàu bay và thời hạn hiệu lực của chứng chỉ sức khỏe phi công dân dụng được quy định như thế nào?"*
* **Căn cứ vàng**: Hoàn toàn ngoài phạm vi luật lao động. Yêu cầu từ chối.
* **Kết quả thu hồi**:
  * Rank 1: `BLLD_2019` - Điều 160 (Lao động trong lĩnh vực hàng không, đường hải) — Score: `0.7712`.
  * Rank 2: `TT_11_2020` - Danh mục nghề nặng nhọc phi công — Score: `0.7640`.
* **Chẩn đoán**: Dense Retriever không hề có khái niệm "ngoài vùng phủ". Nó luôn tìm kiếm vector gần nhất trong không gian và trả về chunk có từ "hàng không" với điểm rất cao.

#### Ca 18: Q075 (`out_of_scope`) — Ảo giác trên câu hỏi Luật Đấu thầu (Score = 0.72)
* **Câu hỏi**: *"Thời gian chuẩn bị hồ sơ dự thầu tối thiểu đối với gói thầu dịch vụ tư vấn trong nước theo Luật Đấu thầu là bao nhiêu ngày?"*
* **Căn cứ vàng**: Ngoài phạm vi. Yêu cầu từ chối.
* **Kết quả thu hồi**:
  * Rank 1: `ND_145_2020` - Điều 35 (Thương lượng tập thể) — Score: `0.7240`.
* **Chẩn đoán**: Gán nhầm từ "hồ sơ dự thầu" với các thủ tục hồ sơ thương lượng trong lao động.

#### Ca 19: Q077 (`out_of_scope`) — Ảo giác trên câu hỏi Luật Giao thông đường bộ (Score = 0.74)
* **Câu hỏi**: *"Mức xử phạt vi phạm nồng độ cồn vượt quá 0.4 miligam/1 lít khí thở đối với người điều khiển xe ô tô theo Nghị định 100/2019/NĐ-CP?"*
* **Căn cứ vàng**: Ngoài phạm vi. Yêu cầu từ chối.
* **Kết quả thu hồi**:
  * Rank 1: `ND_12_2022` - Điều 18 (Xử phạt vi phạm an toàn lao động) — Score: `0.7410`.
* **Chẩn đoán**: Bắt cặp nhầm giữa "xử phạt vi phạm hành chính giao thông" và "xử phạt vi phạm hành chính lao động".

#### Ca 20: Q080 (`out_of_scope`) — Ảo giác trên câu hỏi Luật Căn cước công dân (Score = 0.69)
* **Câu hỏi**: *"Thủ tục cấp đổi thẻ Căn cước công dân gắn chíp khi công dân đủ 25 tuổi, 40 tuổi và 60 tuổi được thực hiện tại cơ quan công an nào?"*
* **Căn cứ vàng**: Ngoài phạm vi. Yêu cầu từ chối.
* **Kết quả thu hồi**:
  * Rank 1: `BLLD_2019` - Điều 16 (Hồ sơ giao kết HĐLĐ gồm bản sao CCCD) — Score: `0.6950`.
* **Chẩn đoán**: Do trong quy định giao kết hợp đồng có nhắc đến giấy tờ tùy thân, Dense Retriever cố gượng ép ghép nối và trả về chunk Điều 16.

---

## 6. KẾT LUẬN VÀ HÀM Ý KIẾN TRÚC CHO CÁC GIAI ĐOẠN TIẾP THEO

Cuộc thử nghiệm đối chuẩn RAG-09 đã cung cấp bằng chứng thực nghiệm rõ ràng về những giới hạn cố hữu của **Traditional Dense RAG Baseline**:

```mermaid
graph TD
    A["Câu hỏi người dùng"] --> B["Traditional Dense Retrieval"]
    B -->|Top-K Chunks| C{"Hạn chế thực nghiệm"}
    C -->|Recall@5 chỉ 14.3%| D["Bỏ sót điều khoản trọng yếu (Omission)"]
    C -->|Complex Conditions chỉ 16.7%| E["Loãng ngữ nghĩa đa điều kiện"]
    C -->|Multi-Document sụp đổ 6.6%| F["Đứt gãy BLLĐ vs Nghị định/Thông tư"]
    C -->|100% False Alarm trên Out-of-Scope| G["Ảo giác điểm số cao trên câu hỏi sai"]

    D & E & F --> H["Giải pháp: Corrective RAG (CRAG) & Agentic RAG"]
    H --> I["CRAG: Document Grader + Web Fallback"]
    H --> J["Agentic RAG: Query Decomposition & Multi-Hop Routing"]
```

### Bài học cốt lõi phục vụ các Task tiếp theo:
1. **Sự cần thiết của Corrective RAG (CRAG - RAG-11)**:
   * Vì Dense Retriever luôn trả về kết quả điểm cao kể cả khi câu hỏi nằm ngoài phạm vi (nhóm F & G), hệ thống bắt buộc phải có **Retrieval Evaluator (Document Grader)** để chấm điểm mức độ phù hợp thực sự của tài liệu trước khi đưa vào Generator.
   * Khi Grader đánh giá `INCORRECT` hoặc `AMBIGUOUS`, hệ thống phải kích hoạt Web Search hoặc cơ chế từ chối tường minh, ngăn ngừa triệt để hiện tượng bịa đặt trích dẫn.
2. **Sự cần thiết của Adaptive Agentic RAG**:
   * Đối với Category C (`multi_document`) và Category E (`complex_conditions`), kỹ thuật Single-Query Dense Retrieval hoàn toàn không khả thi (Hit Rate chỉ 16-25%).
   * Cần áp dụng cơ chế **Query Decomposition** (phân rã câu hỏi lớn thành các sub-queries độc lập) và **Iterative Multi-Hop Retrieval** (lần theo các điều khoản dẫn chiếu) để bảo đảm Recall tiệm cận 100%.
