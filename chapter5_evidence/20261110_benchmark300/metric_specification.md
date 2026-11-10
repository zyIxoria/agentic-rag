# BỘ QUY CHUẨN ĐO LƯỜNG VÀ ĐỊNH NGHĨA CHỈ SỐ (METRIC SPECIFICATION)
Áp dụng cho gói bằng chứng thực nghiệm Chương 5 (Benchmark 300 câu hỏi).

## 1. Các chỉ số truy xuất đoạn (Retrieval Metrics)
- **Chunk Recall@k:** Tỷ lệ đoạn chuẩn (gold chunks) xuất hiện trong top-k đoạn truy xuất:
  $$\text{Chunk Recall@k} = \frac{|\text{RetrievedChunks}_{1..k} \cap \text{GoldChunks}|}{|\text{GoldChunks}|}$$
- **Chunk Hit Rate@k:** Tỷ lệ câu hỏi tìm thấy ít nhất một đoạn chuẩn trong top-k:
  $$\text{Hit Rate@k} = \mathbb{I}(|\text{RetrievedChunks}_{1..k} \cap \text{GoldChunks}| > 0)$$
- **Article Recall@k:** Tỷ lệ Điều luật chuẩn (gold articles) có đoạn tương ứng trong top-k.
- **MRR (Mean Reciprocal Rank):** Thứ hạng nghịch đảo của đoạn chuẩn đầu tiên xuất hiện trong danh sách kết quả.

## 2. Các chỉ số chất lượng câu trả lời (Answer Quality Metrics)
- **Answer Correctness Score (Thang điểm [0..1]):**
  - **1.0 (Correct):** Trả lời đúng trọng tâm câu hỏi, viện dẫn chuẩn xác tên văn bản, số hiệu, Điều và Khoản pháp luật.
  - **0.5 (Partially Correct):** Trả lời đúng nội dung nhưng trích dẫn thiếu Điều khoản hoặc chỉ bao phủ được một phần các khía cạnh pháp lý bắt buộc.
  - **0.0 (Incorrect / Refusal Failure):** Trả lời sai bản chất pháp luật, trích dẫn sai văn bản, hoặc bịa đặt câu trả lời khi thiếu dữ liệu.
- **$C^+(A)$ (Coverage Rate):** Tỷ lệ câu hỏi đạt điểm lớn hơn 0 trên tập 250 câu có thể trả lời ($N_A = 250$).
- **$\bar{S}(A)$:** Điểm trung bình số học nhân 100 trên tập 250 câu có thể trả lời.
- **$\bar{S}(B)$:** Điểm trung bình số học nhân 100 trên toàn bộ 300 câu kiểm định (gồm cả 50 câu kiểm định từ chối).

## 3. Các chỉ số an toàn và bám ngữ cảnh (Safety & Grounding)
- **Refusal Accuracy:** Tỷ lệ hệ thống từ chối thành công khi gặp câu hỏi thiếu dữ liệu hoặc ngoài phạm vi ($N_{\text{refusal}} = 50$).
- **False Answer Rate:** Tỷ lệ hệ thống cố trả lời và gây ảo giác nguy hiểm ($1 - \text{Refusal Accuracy}$).
- **Faithfulness Rate:** Tỷ lệ câu trả lời không chứa thông tin mâu thuẫn hoặc bịa đặt ngoài các đoạn được cung cấp.

## 4. Các chỉ số thời gian và độ trễ (Latency Metrics)
- **Total Latency (ms):** Tổng thời gian thực thi end-to-end từ lúc nhận câu hỏi đến khi trả lời.
- **Routing Latency (ms):** Thời gian phân tích câu hỏi và quyết định nhánh định tuyến tại HybridQueryClassifier.
