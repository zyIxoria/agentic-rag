# BẢNG QUY ĐỔI CHI PHÍ TOKEN TRÊN CÁC LLM THƯƠNG MẠI

> **Tỷ giá áp dụng:** 1 USD = 25,500 VNĐ

> **Nguồn dữ liệu:** Kết quả đo đạc thực nghiệm trên toàn bộ 80 câu hỏi kiểm định (Benchmark RAG-08) thuộc 7 danh mục độ phức tạp pháp luật lao động Việt Nam.

## 1. Thống Kê Tiêu Thụ Token Thực Tế (Benchmark 80 Câu)
| Mô hình | Mean Input Tokens | Mean Output Tokens | Mean Total Tokens | Tổng Token (80 câu) | Tiết kiệm so với Baseline |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Traditional RAG (Baseline)** | 611.0 | 1,087.0 | **1,698.1** | 135,845 | Baseline (Gốc) |
| **Corrective RAG (CRAG)** | 610.4 | 703.5 | **1,313.9** | 105,111 | **-22.62%** |
| **Adaptive Agentic RAG** | 512.4 | 794.6 | **1,307.0** | 104,556 | **-23.03%** |

## 2. Chi Phí Trung Bình Cho 1 Câu Hỏi Tra Cứu (USD & VNĐ)
| Nhà Cung Cấp & Mô Hình LLM | Giá In/Out ($/1M) | Traditional RAG | Corrective RAG (CRAG) | Adaptive Agentic RAG | Tiết kiệm chi phí (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Gemini 1.5 Flash** (Google DeepMind) | $0.075 / $0.300 | $0.00037 (9.5đ) | $0.00026 (6.5đ) | **$0.00028 (7.1đ)** | **-25.54%** |
| **GPT-4o-mini** (OpenAI) | $0.150 / $0.600 | $0.00074 (19.0đ) | $0.00051 (13.1đ) | **$0.00055 (14.1đ)** | **-25.54%** |
| **Gemini 1.5 Pro** (Google DeepMind) | $1.250 / $5.000 | $0.00620 (158.1đ) | $0.00428 (109.2đ) | **$0.00461 (117.6đ)** | **-25.58%** |
| **GPT-4o** (OpenAI) | $2.500 / $10.000 | $0.01240 (316.1đ) | $0.00856 (218.3đ) | **$0.00923 (235.3đ)** | **-25.58%** |
| **Claude 3.5 Sonnet** (Anthropic) | $3.000 / $15.000 | $0.01814 (462.5đ) | $0.01238 (315.8đ) | **$0.01346 (343.1đ)** | **-25.81%** |

## 3. Dự Phóng Chi Phí Khi Vận Hành Hệ Thống Ở Quy Mô Lớn
### Quy mô 10,000 Truy Vấn Pháp Lý (Mức độ phòng ban / doanh nghiệp vừa)
| Mô hình LLM | Traditional RAG | Corrective RAG (CRAG) | Adaptive Agentic RAG | Chênh lệch tiết kiệm |
| :--- | :---: | :---: | :---: | :---: |
| **Gemini 1.5 Flash** | $3.72 (94,843đ) | $2.57 | **$2.77** (70,583đ) | Tiết kiệm **24,260 VNĐ** |
| **GPT-4o-mini** | $7.44 (189,685đ) | $5.14 | **$5.54** (141,167đ) | Tiết kiệm **48,518 VNĐ** |
| **Gemini 1.5 Pro** | $61.99 (1,580,710đ) | $42.80 | **$46.13** (1,176,388đ) | Tiết kiệm **404,322 VNĐ** |
| **GPT-4o** | $123.98 (3,161,420đ) | $85.61 | **$92.27** (2,352,777đ) | Tiết kiệm **808,643 VNĐ** |
| **Claude 3.5 Sonnet** | $181.38 (4,625,266đ) | $123.83 | **$134.56** (3,431,170đ) | Tiết kiệm **1,194,096 VNĐ** |

### Quy mô 100,000 Truy Vấn Pháp Lý (Mức độ Cổng Dịch vụ công / Hệ thống Quốc gia)
| Mô hình LLM | Traditional RAG | Corrective RAG (CRAG) | Adaptive Agentic RAG | Chênh lệch tiết kiệm |
| :--- | :---: | :---: | :---: | :---: |
| **Gemini 1.5 Flash** | $37.19 (948,426đ) | $25.68 | **$27.68** (705,833đ) | Tiết kiệm **242,593 VNĐ** |
| **GPT-4o-mini** | $74.39 (1,896,852đ) | $51.36 | **$55.36** (1,411,666đ) | Tiết kiệm **485,186 VNĐ** |
| **Gemini 1.5 Pro** | $619.89 (15,807,099đ) | $428.04 | **$461.33** (11,763,883đ) | Tiết kiệm **4,043,216 VNĐ** |
| **GPT-4o** | $1,239.77 (31,614,199đ) | $856.08 | **$922.66** (23,527,766đ) | Tiết kiệm **8,086,433 VNĐ** |
| **Claude 3.5 Sonnet** | $1,813.83 (46,252,665đ) | $1,238.34 | **$1,345.56** (34,311,703đ) | Tiết kiệm **11,940,962 VNĐ** |

## 4. Phân Tích Ý Nghĩa Kỹ Thuật & Nghiên Cứu
1. **Tại sao Traditional RAG tiêu tốn token cao nhất (1,698 tokens/câu)?**
   - Pipeline baseline nhồi nhét toàn bộ Top-5 chunks thô vào prompt mà không có cơ chế lọc bỏ đoạn nhiễu.
   - Khi câu hỏi yêu cầu từ chối (ngoài phạm vi hoặc thiếu bằng chứng), LLM vẫn phải đọc toàn bộ 5 chunks và sinh ra câu trả lời dài dòng không cần thiết.

2. **Tại sao Corrective RAG tiết kiệm được 22.62% tokens?**
   - CRAG trang bị bộ lọc Strip Refinement (loại bỏ các câu văn bản pháp luật không liên quan trực tiếp đến truy vấn) trước khi đưa vào context sinh câu trả lời.
   - Nhờ đó, số lượng output tokens giảm mạnh từ 1,087 tokens xuống còn 703 tokens.

3. **Tại sao Adaptive Agentic RAG tiết kiệm được 23.03% tokens & tối ưu chi phí input?**
   - Bộ điều phối **Query Complexity Classifier** nhận diện các câu hỏi ngoài phạm vi hoặc chào hỏi để kích hoạt nhánh `DIRECT_REFUSAL` hoặc `DIRECT_ANSWER`, hoàn toàn **bỏ qua bước nạp context văn bản pháp lý** (input tokens chỉ vỏn vẹn 22 tokens).
   - Đối với các câu hỏi phức tạp cần phân rã (`DECOMPOSE_AGENTIC`), mặc dù có thêm các câu hỏi con nhưng tổng chi phí toàn hệ thống vẫn thấp hơn 25.6% so với việc truyền context cồng kềnh như Traditional RAG.
