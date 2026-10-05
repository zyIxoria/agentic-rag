"""run_rag_baseline.py - Script tương tác chạy mô hình Traditional RAG Baseline.

Hỗ trợ:
- Chế độ dòng lệnh tương tác (Interactive Chat): python run_rag_baseline.py
- Chế độ một câu hỏi (Single Query): python run_rag_baseline.py --query "Thời gian thử việc tối đa là bao lâu?"
- Tùy chọn cấu hình: --provider [mock|openai|gemini], --top-k [int], --threshold [float]
"""

from __future__ import annotations
import argparse
import os
import sys
import time
from pathlib import Path

# Đảm bảo UTF-8 encoding trên console Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Thêm project root vào sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from RAG.pipeline.config import PipelineConfig
from RAG.pipeline.traditional_rag import TraditionalRAGPipeline


def print_banner():
    banner = """
================================================================================
           TRADITIONAL RAG BASELINE - HỎI ĐÁP PHÁP LUẬT LAO ĐỘNG
                         (Baseline Version: Traditional-RAG-v1)
================================================================================
Kiến trúc: Question -> Dense Retrieval (MiniLM) -> Pre-Guard -> LLM -> Citation
Corpus:    1,390 chunks pháp lý (Dataset V2.1 - 15 văn bản quy phạm)
Gõ 'exit', 'quit', hoặc 'q' để thoát.
================================================================================
"""
    print(banner)


def print_response(res):
    print("\n" + "-" * 80)
    print(f"📌 CÂU HỎI: {res.question}")
    print("-" * 80)
    print("⚖️  CÂU TRẢ LỜI:")
    print(res.answer)
    print("-" * 80)
    print("📊 THÔNG SỐ VẬN HÀNH:")
    print(f"   • Trạng thái từ chối (Refused) : {res.refused} {f'({res.refusal_reason})' if res.refused else ''}")
    print(f"   • Số chunks thu hồi (Top-K)    : {len(res.retrieved_chunks)}")
    print(f"   • Số trích dẫn hợp lệ          : {len(res.citations)}")
    print(f"   • Độ trễ thu hồi (Retrieval)   : {res.retrieval_latency:.2f} ms")
    print(f"   • Độ trễ sinh mẫu (Generation) : {res.generation_latency:.2f} ms")
    print(f"   • Tổng độ trễ toàn chuỗi       : {res.latency:.2f} ms")
    print(f"   • Mô hình LLM                  : {res.model_name} ({res.provider})")
    
    if res.retrieved_chunks:
        print("\n🔍 CÁC ĐOẠN VĂN BẢN ĐÃ THU HỒI:")
        for idx, c in enumerate(res.retrieved_chunks, start=1):
            doc = c.metadata.get("document_id", "")
            art = c.metadata.get("article_number", "")
            title = c.metadata.get("document_title", "")
            score = c.score
            print(f"   [{idx}] {doc} - {art} (Score: {score:.4f}) | {c.chunk_id}")
    print("-" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Chạy Traditional RAG Baseline Hỏi Đáp Pháp Luật Lao Động")
    parser.add_argument("--query", "-q", type=str, default=None, help="Câu hỏi pháp lý cần tra cứu trực tiếp")
    parser.add_argument("--provider", "-p", type=str, default="mock", choices=["mock", "openai", "gemini", "auto"],
                        help="Nhà cung cấp LLM: 'mock' (mặc định ngoại tuyến), 'openai', 'gemini'")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Số lượng chunk thu hồi (mặc định: 5)")
    parser.add_argument("--threshold", "-t", type=float, default=0.45, help="Ngưỡng tương đồng tối thiểu (mặc định: 0.45)")
    parser.add_argument("--model", "-m", type=str, default=None, help="Tên mô hình LLM cụ thể")

    args = parser.parse_args()

    # Cấu hình pipeline
    config = PipelineConfig(
        TOP_K=args.top_k,
        SIMILARITY_THRESHOLD=args.threshold,
        LLM_PROVIDER=args.provider,
        LLM_MODEL=args.model,
        TEMPERATURE=0.0,
        ENABLE_PRE_GUARD=True,
        ENABLE_POST_GUARD=True,
    )

    print(f"Đang khởi tạo Traditional RAG Pipeline (Provider: {args.provider}, Top-K: {args.top_k})...")
    pipeline = TraditionalRAGPipeline(config=config)
    print("Khởi tạo thành công!\n")

    if args.query:
        # Chạy câu hỏi đơn từ tham số dòng lệnh
        res = pipeline.answer(args.query)
        print_response(res)
    else:
        # Chạy chế độ tương tác liên tục
        print_banner()
        while True:
            try:
                user_query = input("💬 Nhập câu hỏi pháp lý của bạn: ").strip()
                if not user_query:
                    continue
                if user_query.lower() in ("exit", "quit", "q"):
                    print("Tạm biệt!")
                    break

                res = pipeline.answer(user_query)
                print_response(res)

            except KeyboardInterrupt:
                print("\nĐã ngắt chương trình.")
                break
            except Exception as e:
                print(f"❌ Đã xảy ra lỗi: {e}\n")


if __name__ == "__main__":
    main()
