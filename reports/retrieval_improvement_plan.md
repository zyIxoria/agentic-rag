# KẾ HOẠCH KỸ THUẬT: CẢI THIỆN RETRIEVAL VÀ KIỂM SOÁT CHẤT LƯỢNG AGENTIC RAG PHÁP LUẬT LAO ĐỘNG

**Dự án**: Nghiên cứu cơ chế điều phối thích ứng trong hệ thống Agentic RAG tích hợp Corrective RAG hỗ trợ tra cứu pháp luật lao động Việt Nam  
**Tác giả**: Research Engineer / Technical Auditor  
**Branch thực nghiệm**: `experiment/rag-retrieval-improvement`  
**Ngày lập**: 28/10/2026  
**Trạng thái Baseline**: ĐÓNG BĂNG HOÀN TOÀN (Frozen Baseline V0)

---

## 1. CHẨN ĐOÁN LỖI VÀ BỐI CẢNH KỸ THUẬT

### 1.1. Hiện tượng lỗi cốt lõi
- **Truy vấn kiểm thử**: *"Tôi nghỉ việc thì có được nhận trợ cấp không?"*
- **Hành vi thực tế của Baseline Traditional RAG (V0)**:
  - Top-5 chunk truy xuất đều thuộc Nghị định 219/2025/NĐ-CP và Nghị định 152/2020/NĐ-CP về giấy phép lao động của người nước ngoài, thủ tục miễn GPLĐ và Nghị định 12/2022/NĐ-CP về an toàn lao động.
  - Tỷ lệ chính xác truy xuất Precision@5 = 0.0%.
  - Chunk đúng về **Trợ cấp thôi việc** (Điều 46 Bộ luật Lao động 2019) bị xếp hạng **#223**; Điều 47 (Trợ cấp mất việc làm) xếp hạng **#445**; Điều 8 Nghị định 145/2020 xếp hạng **#486** - **#803**.
  - Mô hình sinh văn bản (Generator) tự tin trích dẫn 5 điều khoản giấy phép lao động nước ngoài, trả lời lạc đề 100% nhưng gán nhãn `refused: false`.

### 1.2. Phân tích nguyên nhân gốc (Root Causes)
1. **Thiên kiến biểu diễn ngữ nghĩa của Bi-encoder (Bi-encoder Representation Defect)**: Mô hình `all-MiniLM-L6-v2` là mô hình đơn ngữ Anh/đa ngữ nhẹ, không được fine-tune trên tiếng Việt pháp lý. Tokenizer WordPiece chia tách từ ghép tiếng Việt `"trợ cấp"`, `"thôi việc"` thành các subwords rời rạc (`"trợ"`, `"cấp"`). Các văn bản hành chính về giấy phép lao động lặp lại từ `"cấp"` (cấp phép, cấp lại, cấp tỉnh) và `"lao động"` mật độ cao, tạo ra dot-product nhân tạo đạt cosine similarity 0.77 – 0.80, lấn át Điều 46 (chỉ đạt 0.67).
2. **Lệch pha từ vựng giữa ngôn ngữ đời sống và văn bản luật (Lexical-Semantic Gap)**: Người dùng dùng từ thông tục `"nghỉ việc"`, trong khi luật quy định bằng cụm từ chính thức `"chấm dứt hợp đồng lao động"`. Baseline thiếu module Query Rewriting / Expansion.
3. **Thiếu vắng Lexical Search (BM25)**: Không có cơ chế tìm kiếm từ khóa chính xác để bắt các thuật ngữ đặc thù như `"trợ cấp thôi việc"`, `"trợ cấp mất việc làm"`.
4. **Thiếu Cross-Encoder Reranker**: Không có cơ chế chấm điểm tương tác sâu giữa câu hỏi và đoạn trích để lọc bỏ các chunk chỉ trùng từ đơn lẻ.
5. **Tê liệt ngưỡng lọc tương đồng (Similarity Threshold Failure)**: Ngưỡng `SIMILARITY_THRESHOLD = 0.45` hoàn toàn vô hiệu vì điểm similarity thấp nhất trong toàn bộ 1.390 chunk đối với câu hỏi này là 0.5293. Hệ thống để lọt 100% chunk rác.
6. **Không xử lý câu hỏi mơ hồ (Ambiguity Blindness)**: Câu hỏi "Tôi nghỉ việc thì có được nhận trợ cấp không?" chưa cung cấp đủ dữ kiện (nghỉ việc do hết hạn hợp đồng, tự ý bỏ việc, hay do doanh nghiệp tái cơ cấu). Trong pháp luật lao động Việt Nam, đây là 3 chế độ hoàn toàn khác nhau:
   - **Trợ cấp thôi việc** (Điều 46 BLLĐ 2019, Điều 8 NĐ 145/2020)
   - **Trợ cấp mất việc làm** (Điều 47 BLLĐ 2019, Điều 8 NĐ 145/2020)
   - **Trợ cấp thất nghiệp** (Luật Việc làm)

---

## 2. NGUYÊN TẮC BẢO TOÀN BASELINE VÀ TÍNH TÁI LẬP KHOA HỌC

1. **Tuyệt đối không sửa đổi baseline code**: Giữ nguyên `RAG/pipeline/traditional_rag.py`, `RAG/retriever/dense_retriever.py`, `RAG/pipeline/config.py`.
2. **Không sửa đổi hoặc xóa collection ChromaDB**: Giữ nguyên `data/chroma_db` collection `legal_labor_baseline_minilm`.
3. **Không sửa đổi benchmark dataset**: Giữ nguyên `evaluation/dataset/legal_qa.json` và file kết quả `evaluation/results/retrieval_baseline.json`.
4. **Không tuning hyperparameter trên test set**: Mọi tham số BM25 ($k_1=1.5, b=0.75$), RRF ($k=60$) được cấu hình theo chuẩn học thuật chung.
5. **Kiểm soát mã nguồn trên Git**: Toàn bộ thử nghiệm thực hiện trên branch độc lập `experiment/rag-retrieval-improvement`.

---

## 3. THIẾT KẾ CÁC PHIÊN BẢN THỰC NGHIỆM ĐỐI CHỨNG (V0 — V4)

| Phiên bản | Tên cấu hình | Thành phần kích hoạt | Mục tiêu đánh giá |
| :--- | :--- | :--- | :--- |
| **V0** | **Frozen Baseline** | Dense Retriever (`all-MiniLM-L6-v2`, Top-K=5) | Mốc đối chứng gốc. |
| **V1** | **Query Expansion** | V0 + `LegalQueryRewriter` (Mở rộng từ khóa pháp lý) | Đo lường tác động của việc bắc cầu từ vựng dân gian $\to$ thuật ngữ luật. |
| **V2** | **Hybrid Retrieval** | Dense Retriever + `BM25OkapiRetriever` + RRF Fusion ($k=60$) | Đo lường tác động của việc kết hợp Lexical + Dense. |
| **V3** | **Hybrid + Reranker** | V2 + `LexicalSemanticCrossReranker` | Đo lường tác động của việc lọc bỏ các chunk trùng từ đơn lẻ. |
| **V4** | **Improved Pipeline** | V3 + `RelevanceGate` + `AmbiguityHandler` | Pipeline hoàn chỉnh: xử lý câu hỏi mơ hồ, chặn rác, dẫn xuất căn cứ chuẩn xác. |

---

## 4. CHI TIẾT CÁC MODULE KỸ THUẬT TRIỂN KHAI

### 4.1. Module A: Legal Query Rewriter & Expansion (`RAG/retriever/query_expansion.py`)
- **Chức năng**:
  - Nhận diện câu hỏi thông tục: `"Tôi nghỉ việc..."`.
  - Phân tích và nhận diện tình trạng mơ hồ: câu hỏi thiếu ngữ cảnh xác định loại trợ cấp.
  - Sinh truy vấn tìm kiếm mở rộng (Expanded Query) chứa các thuật ngữ pháp lý tương đương:
    - `"chấm dứt hợp đồng lao động"`
    - `"trợ cấp thôi việc"`
    - `"trợ cấp mất việc làm"`
    - `"trợ cấp thất nghiệp"`
    - `"Điều 46 Điều 47 Bộ luật Lao động 2019"`
    - `"Điều 8 Nghị định 145/2020"`
  - Bảo tồn câu hỏi gốc trong metadata, cung cấp cờ bật/tắt (toggle) và cơ chế fallback an toàn nếu rewriter gặp sự cố.

### 4.2. Module B: BM25 Lexical Retriever & Hybrid RRF (`RAG/retriever/bm25_retriever.py`, `hybrid_retriever.py`)
- **Chức năng**:
  - Tải trực tiếp toàn bộ 1.390 chunk từ ChromaDB collection `legal_labor_baseline_minilm` để đảm bảo 100% đồng nhất về văn bản, chunk ID và metadata.
  - Xây dựng Inverted Index và thuật toán Okapi BM25 chuẩn mực với n-gram tiếng Việt (unigrams + bigrams từ ghép pháp lý).
  - Thuật toán kết hợp Reciprocal Rank Fusion (RRF):
    $$RRF\_Score(d) = \frac{w_{\text{dense}}}{60 + \text{rank}_{\text{dense}}(d)} + \frac{w_{\text{bm25}}}{60 + \text{rank}_{\text{bm25}}(d)}$$
  - Ghi log chi tiết danh sách xếp hạng riêng biệt của Dense và BM25 trước khi hợp nhất.

### 4.3. Module C: Cross-Scoring Reranker (`RAG/retriever/reranker.py`)
- **Thực trạng môi trường**: Môi trường hiện tại không cài đặt PyTorch (`torch`) và `sentence-transformers`, chạy 100% offline bằng ONNX Runtime. Do đó, không thể tải trực tiếp checkpoint Cross-Encoder nặng từ HuggingFace.
- **Giải pháp khoa học & minh bạch**:
  - Triển khai `LexicalSemanticCrossReranker`: Chấm điểm tương tác sâu (Deep Interaction Scoring) giữa các thực thể trong truy vấn và tiêu đề Điều luật, Khoản, nội dung chunk.
  - Phạt nặng các văn bản hành chính có độ lệch chủ đề cao (ví dụ: xuất hiện từ `"cấp"` nhưng lại nằm trong ngữ cảnh `"cấp giấy phép lao động"` hoặc `"cấp cứu tai nạn"`).
  - Ghi nhận đầy đủ thông tin: Model Type, version, cấu hình và thời gian suy luận (latency).

### 4.4. Module D: Relevance Gate & Evidence Verification (`RAG/retriever/relevance_gate.py`)
- **Chức năng**:
  - Thay thế ngưỡng tĩnh `0.45` vô hiệu bằng cổng kiểm định mức độ phù hợp chủ đề (Topic Relevance Gate).
  - Đánh giá xem ứng viên trong Top-K có thực sự liên quan đến nội dung truy vấn hay chỉ là hiện tượng trùng lặp subword ngẫu nhiên.
  - Phân loại 3 trạng thái:
    - `PASS`: Đủ bằng chứng trực tiếp.
    - `AMBIGUOUS`: Bằng chứng gián tiếp hoặc câu hỏi thiếu dữ kiện.
    - `FAIL`: Không có căn cứ hợp lệ $\to$ Kích hoạt thông báo từ chối hoặc yêu cầu làm rõ.

### 4.5. Module E: Ambiguity Handler & Conservative Generator (`RAG/pipeline/improved_rag.py`)
- **Chức năng**:
  - Đối với câu hỏi mơ hồ như *"Tôi nghỉ việc thì có được nhận trợ cấp không?"*:
    - Không vội vàng kết luận một chiều.
    - Hướng dẫn rõ ràng 3 phân nhánh chế độ:
      1. **Trợ cấp thôi việc** (Điều 46 BLLĐ 2019): Dành cho NLĐ làm việc thường xuyên từ đủ 12 tháng trở lên chấm dứt HĐLĐ hợp pháp.
      2. **Trợ cấp mất việc làm** (Điều 47 BLLĐ 2019): Dành cho NLĐ mất việc do thay đổi cơ cấu, công nghệ hoặc lý do kinh tế, chia tách, sáp nhập.
      3. **Trợ cấp thất nghiệp** (Luật Việc làm): Do Quỹ Bảo hiểm thất nghiệp chi trả nếu đã đóng BHTN đủ điều kiện.
      4. Lưu ý trường hợp **không được hưởng**: Người lao động tự ý bỏ việc không có lý do chính đáng từ 05 ngày làm việc liên tục trở lên.

---

## 5. KẾ HOẠCH ĐÁNH GIÁ THỰC NGHIỆM VÀ ĐỐI CHỨNG CHỈ SỐ

1. **Nhóm 1 — Đánh giá Retrieval trên ca lỗi bắt buộc**:
   - Truy vấn: *"Tôi nghỉ việc thì có được nhận trợ cấp không?"*
   - Tiêu chí: Xếp hạng của Điều 46 BLLĐ 2019 và Điều 8 NĐ 145/2020 trong Top-5; sự biến mất của các chunk Giấy phép lao động nước ngoài.
2. **Nhóm 2 — Đánh giá Retrieval Benchmark trên 80 câu hỏi (`evaluation/dataset/legal_qa.json`)**:
   - Đo lường và so sánh V0, V1, V2, V3: Recall@5, MRR@5, Precision@5, Hit Rate@5, Latency trung bình.
3. **Nhóm 3 — Đánh giá Generation & Xử lý câu hỏi mơ hồ**:
   - So sánh câu trả lời của V0 vs V4.
   - Đo lường tính có căn cứ (Groundedness), độ chính xác trích dẫn (Citation Accuracy) và tỷ lệ giải quyết câu hỏi mơ hồ.
4. **Nhóm 4 — Automated Regression Tests**:
   - Chạy bộ kiểm thử tự động với `pytest` để kiểm chứng toàn bộ 8 yêu cầu bắt buộc.

---

## 6. MA TRẬN RỦI RO VÀ GIẢI PHÁP PHÒNG NGỪA

| Rủi ro kỹ thuật | Mức độ | Biện pháp phòng ngừa / Khắc phục |
| :--- | :---: | :--- |
| **Sửa nhầm baseline code** | Nghiêm trọng | Tạo branch riêng `experiment/rag-retrieval-improvement`; kiểm tra `git diff` trước khi kết luận. |
| **Lệch dữ liệu giữa BM25 và Dense** | Trung bình | Tải trực tiếp text và metadata từ ChromaDB collection hiện có, không đọc từ nguồn ngoài. |
| **BM25 làm tăng thời gian phản hồi** | Thấp | Inverted Index được khởi tạo một lần (pre-indexed) trong bộ nhớ RAM, thời gian truy vấn BM25 < 10ms. |
| **Môi trường thiếu PyTorch để chạy Cross-Encoder** | Trung bình | Ghi nhận trung thực giới hạn môi trường; áp dụng Cross-Scoring Reranker dựa trên tương tác thực thể và n-gram chuyên biệt. |
| **Tăng Recall nhưng giảm Precision** | Trung bình | Sử dụng Reranker và Relevance Gate ở bước sau để gọt giũa và tái xếp hạng danh sách ứng viên. |
