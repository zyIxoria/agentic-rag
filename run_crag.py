"""run_crag.py - Script tương tác chạy mô hình Corrective RAG (CRAG).

Hỗ trợ:
- Chế độ dòng lệnh tương tác (Interactive Chat): python run_crag.py
- Chế độ một câu hỏi (Single Query): python run_crag.py --query "Thời gian thử việc tối đa là bao lâu?"
- Tùy chọn cấu hình: --provider [mock|openai|gemini], --top-k [int], --confidence-threshold [float]
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

from RAG.corrective.config import CRAGConfig
from RAG.corrective.corrective_rag import CorrectiveRAGPipeline
from RAG.pipeline.config import PipelineConfig
from storage.query_history import QueryHistoryDatabase


def print_banner():
    banner = """
================================================================================
           CORRECTIVE RAG (CRAG) - HỎI ĐÁP PHÁP LUẬT LAO ĐỘNG
                         (Pipeline: Corrective-RAG-v1)
================================================================================
Kiến trúc: Question -> Retrieval #1 -> Retrieval Evaluator #1
                     -> (Nếu thiếu) Query Rewriter -> Retrieval #2 -> Evaluator #2
                     -> Evidence Filter -> Context Builder -> LLM Generator -> Citation
Corpus:    1,390 chunks pháp lý (Dataset V2.1 - 15 văn bản quy phạm)
Gõ 'exit', 'quit', hoặc 'q' để thoát.
================================================================================
"""
    print(banner)


def print_crag_response(res):
    print("\n" + "=" * 80)
    print(f"📌 CÂU HỎI GỐC: {res.original_query}")
    print("=" * 80)
    
    print("🔄 TIẾN TRÌNH CORRECTIVE RAG (CRAG TRACE):")
    init_status = res.initial_evaluation.status.value if res.initial_evaluation else "N/A"
    init_conf = res.initial_evaluation.confidence if res.initial_evaluation else 0.0
    print(f"   • Đánh giá truy xuất vòng 1  : {init_status} (Độ tin cậy: {init_conf:.2f})")
    print(f"   • Kích hoạt hiệu chỉnh (CRAG): {'CÓ (Triggered)' if res.corrective_triggered else 'KHÔNG (Direct Pass)'}")
    
    if res.corrective_triggered:
        print(f"   • Câu hỏi viết lại (Rewritten): \"{res.rewritten_query}\"")
        final_status = res.final_evaluation.status.value if res.final_evaluation else "N/A"
        final_conf = res.final_evaluation.confidence if res.final_evaluation else 0.0
        print(f"   • Đánh giá truy xuất vòng 2  : {final_status} (Độ tin cậy: {final_conf:.2f})")
        print(f"   • Số lần thử lại (Retries)   : {res.retry_count}")

    print("-" * 80)
    print("⚖️  CÂU TRẢ LỜI:")
    print(res.answer)
    print("-" * 80)
    print("📊 THÔNG SỐ VẬN HÀNH:")
    print(f"   • Trạng thái từ chối (Refused) : {res.refused} {f'({res.refusal_reason})' if res.refused else ''}")
    print(f"   • Số chunks truy xuất (Top-K)  : {len(res.retrieved_chunks)}")
    print(f"   • Số trích dẫn pháp lý         : {len(res.citations)}")
    print(f"   • Độ trễ truy xuất (Retrieval) : {res.retrieval_latency:.2f} ms")
    print(f"   • Độ trễ đánh giá (Evaluator)  : {res.eval_latency:.2f} ms")
    print(f"   • Độ trễ viết lại (Rewriter)   : {res.rewrite_latency:.2f} ms")
    print(f"   • Độ trễ ngữ cảnh & sinh lời   : {res.generation_latency:.2f} ms")
    print(f"   • Tổng độ trễ toàn chuỗi       : {res.latency:.2f} ms")
    print(f"   • Mô hình LLM                  : {res.model_name} ({res.provider})")

    if res.retrieved_chunks:
        print("\n🔍 CÁC ĐOẠN VĂN BẢN ĐÃ TRUY XUẤT:")
        for idx, c in enumerate(res.retrieved_chunks, start=1):
            doc = c.metadata.get("document_id", "")
            art = c.metadata.get("article_number", "")
            score = c.score
            print(f"   [{idx}] {doc} - {art} (Score: {score:.4f}) | {c.chunk_id}")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Chạy Corrective RAG (CRAG) Hỏi Đáp Pháp Luật Lao Động")
    parser.add_argument("--query", "-q", type=str, default=None, help="Câu hỏi pháp lý cần tra cứu trực tiếp")
    parser.add_argument("--provider", "-p", type=str, default="mock", choices=["mock", "openai", "gemini", "auto"],
                        help="Nhà cung cấp LLM: 'mock' (mặc định ngoại tuyến), 'openai', 'gemini'")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Số lượng chunk truy xuất (mặc định: 5)")
    parser.add_argument("--confidence-threshold", "-c", type=float, default=0.6,
                        help="Ngưỡng đánh giá truy xuất tự tin (mặc định: 0.6)")
    parser.add_argument("--model", "-m", type=str, default=None, help="Tên mô hình LLM cụ thể")
    parser.add_argument("--no-history", action="store_true", help="Không lưu trữ phiên hỏi đáp vào cơ sở dữ liệu")

    args = parser.parse_args()

    pipeline_cfg = PipelineConfig(
        TOP_K=args.top_k,
        LLM_PROVIDER=args.provider,
        LLM_MODEL=args.model,
        TEMPERATURE=0.0,
        ENABLE_PRE_GUARD=True,
        ENABLE_POST_GUARD=True,
    )

    crag_cfg = CRAGConfig(
        pipeline=pipeline_cfg,
        TOP_K=args.top_k,
        EVAL_CONFIDENCE_THRESHOLD=args.confidence_threshold,
        MAX_CORRECTIVE_RETRIES=1,
    )

    history_db = QueryHistoryDatabase() if not args.no_history else None

    print(f"Đang khởi tạo Corrective RAG Pipeline (Provider: {args.provider}, Top-K: {args.top_k})...")
    pipeline = CorrectiveRAGPipeline(config=crag_cfg)
    print("Khởi tạo thành công!\n")

    if args.query:
        res = pipeline.answer(args.query)
        print_crag_response(res)
        if history_db:
            rec_id = history_db.log_crag_response(res)
            print(f"💾 [Lịch sử] Đã ghi nhận truy vấn vào CSDL (Record ID: #{rec_id})\n")
    else:
        print_banner()
        while True:
            try:
                user_input = input("Nhập câu hỏi pháp luật (hoặc 'exit'): ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit", "q"):
                    print("\nĐã thoát chương trình. Tạm biệt!\n")
                    break
                res = pipeline.answer(user_input)
                print_crag_response(res)
                if history_db:
                    rec_id = history_db.log_crag_response(res)
                    print(f"💾 [Lịch sử] Đã ghi nhận truy vấn vào CSDL (Record ID: #{rec_id})\n")
            except KeyboardInterrupt:
                print("\n\nĐã nhận tín hiệu dừng. Tạm biệt!\n")
                break
            except Exception as e:
                print(f"\n❌ Lỗi khi xử lý câu hỏi: {e}\n")


if __name__ == "__main__":
    main()
