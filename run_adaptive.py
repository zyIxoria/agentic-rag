"""run_adaptive.py - Script tương tác chạy mô hình Adaptive Agentic RAG.

Hỗ trợ:
- Chế độ dòng lệnh tương tác (Interactive Chat): python run_adaptive.py
- Chế độ một câu hỏi (Single Query): python run_adaptive.py --query "Thời gian thử việc tối đa là bao lâu?"
- Hiển thị dấu vết điều phối thích ứng (Adaptive Routing Trace):
  + Phân loại ý định & độ phức tạp câu hỏi
  + Nhánh định tuyến (DIRECT_ANSWER / DIRECT_REFUSAL / TRADITIONAL_RAG / CORRECTIVE_RAG / DECOMPOSE_AGENTIC)
  + Kế hoạch phân rã câu hỏi (Sub-queries plan) và kết quả tra cứu từng chặng
  + Tổng hợp đa chặng và trích dẫn pháp lý chính xác
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
from CRAG.config import CRAGConfig
from Adaptive_RAG.config import AdaptiveRAGConfig
from Adaptive_RAG.pipeline.adaptive_pipeline import AdaptiveRAGPipeline
from Adaptive_RAG.classifier.schema import RoutingDecision


def print_banner():
    banner = """
================================================================================
         ADAPTIVE AGENTIC RAG - HỎI ĐÁP PHÁP LUẬT LAO ĐỘNG VIỆT NAM
                 (Adaptive Multi-Routing & Decomposition Engine)
================================================================================
Kiến trúc: Query -> Hybrid Complexity Classifier (7 Intents, Complexity Score)
                 -> Dynamic Routing:
                    ├── [DIRECT_ANSWER]     : Phản hồi chào hỏi/xã giao (0 ms retrieval)
                    ├── [DIRECT_REFUSAL]    : Từ chối câu hỏi ngoài phạm vi (0 ms)
                    ├── [TRADITIONAL_RAG]   : Tra cứu đơn lẻ 1 điều luật (Top-K Dense)
                    ├── [CORRECTIVE_RAG]    : Tra cứu thủ tục & Lọc nhiễu / Web Fallback
                    └── [DECOMPOSE_AGENTIC] : Phân rã đa chặng -> Tra cứu song song -> Tổng hợp
Corpus:    1,390 chunks pháp lý (Dataset V2.1 - 15 văn bản quy phạm)
Gõ 'exit', 'quit', hoặc 'q' để thoát.
================================================================================
"""
    print(banner)


def print_adaptive_response(res):
    print("\n" + "=" * 80)
    print(f"📌 CÂU HỎI: {res.question}")
    print("=" * 80)

    # 1. Thông tin điều phối thích ứng
    clf = res.classification
    route_name = res.route_taken.value if hasattr(res.route_taken, "value") else str(res.route_taken)
    intent_name = clf.intent.value if hasattr(clf.intent, "value") else str(clf.intent)
    complexity_name = clf.complexity.value if hasattr(clf.complexity, "value") else str(clf.complexity)

    print("🧠 TIẾN TRÌNH ĐIỀU PHỐI THÍCH ỨNG (ADAPTIVE ROUTING TRACE):")
    print(f"   • Ý định câu hỏi (Intent)       : {intent_name}")
    print(f"   • Mức độ phức tạp (Complexity)  : {complexity_name} (Độ tin cậy: {clf.confidence:.2f})")
    print(f"   • Nhánh điều phối (Route Taken) : [{route_name}]")
    print(f"   • Lý do điều phối               : {clf.reasoning}")
    if clf.detected_documents:
        print(f"   • Văn bản phát hiện             : {', '.join(clf.detected_documents)}")
    if clf.detected_articles:
        print(f"   • Điều luật phát hiện           : {', '.join(clf.detected_articles)}")

    # 2. Chi tiết phân rã câu hỏi (nếu thuộc DECOMPOSE_AGENTIC)
    trace = res.trace
    if trace and trace.plan and trace.plan.sub_queries:
        print("\n🧩 KẾ HOẠCH PHÂN RÃ CÂU HỎI (SUB-QUERIES DECOMPOSITION):")
        strat = trace.plan.strategy.value if hasattr(trace.plan.strategy, "value") else str(trace.plan.strategy)
        print(f"   • Chiến lược phân rã (Strategy) : {strat}")
        for idx, sq in enumerate(trace.plan.sub_queries, start=1):
            entity_hint = f" [Mục tiêu: {sq.target_entity}]" if sq.target_entity else ""
            print(f"   [{idx}] {sq.text}{entity_hint}")

        if trace.sub_executions:
            print("\n   🔍 Kết quả tra cứu theo từng câu hỏi con:")
            for s_idx, s_rec in enumerate(trace.sub_executions, start=1):
                n_c = len(s_rec.retrieved_chunks)
                print(f"      - Chặng {s_idx} ({s_rec.latency_ms:.1f}ms): {n_c} chunks truy xuất cho '{s_rec.sub_query.text[:55]}...'")

    print("-" * 80)
    print("⚖️  CÂU TRẢ LỜI:")
    print(res.answer)
    print("-" * 80)

    # 3. Thông số vận hành & độ trễ
    print("📊 THÔNG SỐ VẬN HÀNH:")
    print(f"   • Trạng thái từ chối (Refused)  : {res.refused} {f'({res.refusal_reason})' if res.refused else ''}")
    print(f"   • Tổng số chunks truy xuất      : {len(res.retrieved_chunks)}")
    print(f"   • Số trích dẫn pháp lý          : {len(res.citations)}")
    if trace:
        print(f"   • Độ trễ phân loại (Classifier) : {trace.routing_latency_ms:.2f} ms")
        print(f"   • Độ trễ thực thi (Execution)   : {trace.execution_latency_ms:.2f} ms")
        print(f"   • Độ trễ tổng hợp (Synthesis)   : {trace.synthesis_latency_ms:.2f} ms")
    print(f"   • Tổng độ trễ toàn chuỗi        : {res.latency_ms:.2f} ms")

    # 4. Danh sách các đoạn văn bản truy xuất
    if res.retrieved_chunks:
        print("\n🔍 CÁC ĐOẠN VĂN BẢN ĐÃ TRUY XUẤT:")
        for idx, c in enumerate(res.retrieved_chunks, start=1):
            doc = c.metadata.get("document_id", "")
            art = c.metadata.get("article_number", "")
            score = c.score
            print(f"   [{idx}] {doc} - {art} (Score: {score:.4f}) | {c.chunk_id}")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Chạy Adaptive Agentic RAG Hỏi Đáp Pháp Luật Lao Động")
    parser.add_argument("--query", "-q", type=str, default=None, help="Câu hỏi pháp lý cần tra cứu trực tiếp")
    parser.add_argument("--provider", "-p", type=str, default="mock", choices=["mock", "openai", "gemini", "auto"],
                        help="Nhà cung cấp LLM: 'mock' (mặc định ngoại tuyến), 'openai', 'gemini'")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Số lượng chunk truy xuất (mặc định: 5)")
    parser.add_argument("--threshold", "-t", type=float, default=0.45, help="Ngưỡng tương đồng tối thiểu (mặc định: 0.45)")
    parser.add_argument("--max-sub-queries", type=int, default=4, help="Số lượng sub-query tối đa khi phân rã (mặc định: 4)")
    parser.add_argument("--model", "-m", type=str, default=None, help="Tên mô hình LLM cụ thể")

    args = parser.parse_args()

    pipeline_cfg = PipelineConfig(
        TOP_K=args.top_k,
        SIMILARITY_THRESHOLD=args.threshold,
        LLM_PROVIDER=args.provider,
        LLM_MODEL=args.model,
        TEMPERATURE=0.0,
        ENABLE_PRE_GUARD=True,
        ENABLE_POST_GUARD=True,
    )

    crag_cfg = CRAGConfig(
        TOP_K=args.top_k,
        EVAL_CONFIDENCE_THRESHOLD=0.6,
        MAX_CORRECTIVE_RETRIES=1,
    )

    adaptive_cfg = AdaptiveRAGConfig(
        ENABLE_DIRECT_ROUTING=True,
        MAX_SUB_QUERIES=args.max_sub_queries,
    )

    print(f"Đang khởi tạo Adaptive Agentic RAG Pipeline (Provider: {args.provider}, Top-K: {args.top_k})...")
    pipeline = AdaptiveRAGPipeline(
        config=adaptive_cfg,
        pipeline_config=pipeline_cfg,
        crag_config=crag_cfg,
    )
    print("Khởi tạo thành công!\n")

    if args.query:
        res = pipeline.answer(args.query)
        print_adaptive_response(res)
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
                print_adaptive_response(res)
            except KeyboardInterrupt:
                print("\n\nĐã nhận tín hiệu dừng. Tạm biệt!\n")
                break
            except Exception as e:
                print(f"\n❌ Lỗi khi xử lý câu hỏi: {e}\n")


if __name__ == "__main__":
    main()
