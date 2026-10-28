# HƯỚNG DẪN CHẠY MÔ HÌNH TRADITIONAL RAG BASELINE

> [!NOTE]
> Toàn bộ tài liệu hướng dẫn thực nghiệm của dự án (bao gồm cả **Traditional RAG Baseline**, **Corrective RAG (CRAG)** và **Adaptive Agentic RAG**) đã được hợp nhất thành 1 tài liệu chuẩn hóa duy nhất tại:
> 
> 👉 **[`HUONG_DAN_CHAY_THUC_NGHIEM.md`](HUONG_DAN_CHAY_THUC_NGHIEM.md)**

---

### Lệnh chạy nhanh Traditional RAG Baseline:

```powershell
# 1. Khởi động chế độ chat tương tác liên tục:
python run_rag_baseline.py

# 2. Tra cứu nhanh 1 câu hỏi cụ thể:
python run_rag_baseline.py --query "Thời giờ làm việc bình thường của người lao động là bao nhiêu?"

# 3. Tùy chỉnh tham số Top-K và ngưỡng similarity:
python run_rag_baseline.py --query "Quy định về thử việc" --top-k 5 --threshold 0.45
```

*Vui lòng tham khảo [`HUONG_DAN_CHAY_THUC_NGHIEM.md`](HUONG_DAN_CHAY_THUC_NGHIEM.md) để xem đầy đủ hướng dẫn chạy benchmark và toàn bộ hệ thống.*
