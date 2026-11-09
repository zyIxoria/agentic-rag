# BỘ ĐẶC TẢ PHƯƠNG PHÁP ĐO VÀ TÍNH TOÁN METRIC (METRIC SPECIFICATION)

Tài liệu này công bố chuẩn mực định nghĩa toán học, không gian mẫu, xử lý ngoại lệ và phương thức kiểm định của toàn bộ chỉ số thực nghiệm sử dụng trong Chương 5.

---

## 1. CHỈ SỐ TRUY XUẤT (RETRIEVAL METRICS)

### 1.1 Chunk Recall@K
* **Định nghĩa:** Tỷ lệ các đoạn trích vàng (gold chunks) được hệ thống thu hồi thành công trong Top-$K$ đoạn trích.
* **Công thức:**
  $$\text{Recall@}K = \frac{|\text{RetrievedChunks}_{1..K} \cap \text{GoldChunks}|}{|\text{GoldChunks}|}$$
* **Đơn vị:** Tỷ lệ $[0.0, 1.0]$.
* **Không gian mẫu:** Chỉ tính trên tập câu hỏi có thể trả lời được (Answerable Questions, $N=64$).
* **Xử lý ngoại lệ:** Nếu $|\text{GoldChunks}| = 0$ (câu hỏi từ chối), giá trị là `not_applicable` (loại khỏi mẫu số).

### 1.2 Article Recall@K
* **Định nghĩa:** Tỷ lệ các Điều luật vàng (gold articles) được bao phủ bởi các đoạn trích thu hồi trong Top-$K$.
* **Công thức:**
  $$\text{ArticleRecall@}K = \frac{|\text{RetrievedArticles}_{1..K} \cap \text{GoldArticles}|}{|\text{GoldArticles}|}$$
* **Đơn vị:** Tỷ lệ $[0.0, 1.0]$.
* **Không gian mẫu:** $N=64$.

### 1.3 Hit Rate@K
* **Định nghĩa:** Tỷ lệ câu hỏi mà hệ thống thu hồi được ít nhất 1 đoạn trích vàng trong Top-$K$.
* **Công thức:**
  $$\text{HitRate@}K = \frac{1}{N} \sum_{i=1}^N \mathbb{I}\left(|\text{RetrievedChunks}_{1..K}^{(i)} \cap \text{GoldChunks}^{(i)}| > 0\right)$$
* **Đơn vị:** Tỷ lệ $[0.0, 1.0]$.

### 1.4 Mean Reciprocal Rank (MRR)
* **Định nghĩa:** Giá trị trung bình của nghịch đảo thứ hạng xuất hiện đầu tiên của đoạn trích vàng.
* **Công thức:**
  $$\text{MRR} = \frac{1}{N} \sum_{i=1}^N \frac{1}{\text{rank}_i}$$
  trong đó $\text{rank}_i$ là thứ hạng ($1..K$) của gold chunk đầu tiên; nếu không có gold chunk nào trong Top-$K$, $\frac{1}{\text{rank}_i} = 0$.

---

## 2. CHỈ SỐ CHẤT LƯỢNG CÂU TRẢ LỜI (ANSWER QUALITY)

### 2.1 Overall Answer Correctness
* **Định nghĩa:** Đánh giá tính chính xác tổng thể của câu trả lời dựa trên đối chiếu với đáp án mẫu và căn cứ pháp lý vàng.
* **Phân lớp:**
  - **CORRECT (1.0):** Viện dẫn đầy đủ Điều luật vàng và kết luận đúng bản chất pháp lý.
  - **PARTIALLY_CORRECT (0.5):** Viện dẫn đúng một phần Điều luật hoặc thiếu một số điều kiện/mức phạt.
  - **INCORRECT (0.0):** Viện dẫn sai Điều luật hoặc trả lời sai lệch nội dung pháp lý.
* **Xử lý từ chối:** Với câu hỏi yêu cầu từ chối ($requires\_refusal = True$), nếu hệ thống từ chối thành công thì ghi nhận điểm 1.0 (CORRECT); nếu cố trả lời thì ghi nhận 0.0 (INCORRECT).

### 2.2 Strict Answer Correctness
* **Định nghĩa:** Tỷ lệ câu hỏi đạt mức độ chính xác tuyệt đối (chỉ tính điểm 1.0, không tính 0.5).

### 2.3 Faithfulness Rate (Độ trung thực)
* **Định nghĩa:** Tỷ lệ câu trả lời không chứa thông tin bịa đặt/ảo giác, được bảo chứng 100% bởi ngữ cảnh thu hồi.
* **Quy tắc kiểm định:**
  - Mọi số hiệu Điều luật trong câu trả lời phải xuất hiện trong ngữ cảnh cung cấp.
  - Mọi khẳng định thực tế phải có căn cứ suy diễn từ ngữ cảnh.
* **Lưu ý kiểm chứng:** Trong file `crag_evaluation.json`, bộ chấm lịch sử đã đối chiếu với `retrieved_chunks` ban đầu thay vì `refined_context` dẫn đến độ trung thực bị đánh tụt xuống 18.75% một cách giả tạo (đã được ghi nhận tại `unresolved_items.csv`).

---

## 3. CHỈ SỐ AN TOÀN VÀ TỪ CHỐI (SAFETY & REFUSAL)

### 3.1 Refusal Accuracy
* **Định nghĩa:** Tỷ lệ hệ thống từ chối thành công trên tập câu hỏi bắt buộc phải từ chối ($N=16$, gồm 8 câu thiếu căn cứ và 8 câu ngoài phạm vi).
* **Công thức:**
  $$\text{RefusalAccuracy} = \frac{\sum_{i \in \text{RefusalSet}} \mathbb{I}(\text{refused}_i == \text{True})}{|\text{RefusalSet}|}$$

### 3.2 False Answer Rate (Tỷ lệ trả lời bừa)
* **Định nghĩa:** Tỷ lệ câu hỏi lẽ ra phải từ chối nhưng hệ thống lại cố tình trả lời.
* **Công thức:**
  $$\text{FalseAnswerRate} = 1.0 - \text{RefusalAccuracy}$$
