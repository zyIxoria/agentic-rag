"""show_history.py - Công cụ dòng lệnh (CLI) tra cứu và quản lý lịch sử truy vấn hỏi đáp pháp luật.

Sử dụng:
  python show_history.py --summary                       # Xem tổng hợp thống kê toàn bộ lịch sử
  python show_history.py --list [--limit 10]             # Xem danh sách các câu hỏi gần nhất
  python show_history.py --search "thử việc"             # Tìm kiếm câu hỏi/câu trả lời theo từ khóa
  python show_history.py --view <id>                     # Xem chi tiết một phiên hỏi đáp cụ thể
  python show_history.py --export-json history.json      # Xuất dữ liệu ra file JSON
  python show_history.py --export-csv history.csv        # Xuất dữ liệu ra file CSV
  python show_history.py --rate <id> --score 5           # Chấm điểm / phản hồi câu trả lời
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

# Đảm bảo UTF-8 encoding trên console Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from storage.query_history import QueryHistoryDatabase
from storage.schema import HistoryFilter


def print_summary(db: QueryHistoryDatabase):
    stats = db.get_statistics()
    print("=" * 80)
    print("           TỔNG HỢP THỐNG KÊ LỊCH SỬ TRUY VẤN HỎI ĐÁP PHÁP LUẬT")
    print("=" * 80)
    print(f"📌 Tổng số câu hỏi đã phục vụ     : {stats.total_queries}")
    print(f"🚫 Số câu từ chối (Refused)       : {stats.total_refusals} ({stats.refusal_rate * 100:.2f}%)")
    print(f"⏱️  Độ trễ trung bình (Mean Latency): {stats.avg_total_latency_ms:.2f} ms")
    print(f"📊 Tokens trung bình / câu        : {stats.avg_total_tokens:.1f} tokens")
    print(f"💰 Chi phí quy đổi ước tính (USD) : ${stats.total_estimated_cost_usd:.6f}")
    
    print("\n🔹 Phân bổ theo Mô hình (Model Distribution):")
    if stats.queries_by_model:
        for m, cnt in stats.queries_by_model.items():
            pct = (cnt / stats.total_queries) * 100 if stats.total_queries else 0
            print(f"   • {m:<25}: {cnt:>4} lượt ({pct:>5.1f}%)")
    else:
        print("   (Chưa có dữ liệu)")

    print("\n🔹 Phân bổ theo Nhánh điều phối (Adaptive Route Distribution):")
    if stats.queries_by_route:
        for r, cnt in stats.queries_by_route.items():
            pct = (cnt / stats.total_queries) * 100 if stats.total_queries else 0
            print(f"   • [{r:<18}]: {cnt:>4} lượt ({pct:>5.1f}%)")
    else:
        print("   (Chưa có dữ liệu)")

    if stats.feedback_stats:
        print("\n⭐ Phản hồi người dùng (Feedback):")
        for rating, cnt in stats.feedback_stats.items():
            print(f"   • Đánh giá {rating} sao/điểm: {cnt} lượt")
    print("=" * 80)


def print_list(db: QueryHistoryDatabase, filter_opt: HistoryFilter):
    records = db.get_history(filter_opt)
    if not records:
        print(" Không tìm thấy bản ghi lịch sử nào phù hợp.")
        return

    print("=" * 95)
    print(f"{'ID':<4} | {'THỜI GIAN':<19} | {'MÔ HÌNH':<18} | {'NHÁNH':<16} | {'CÂU HỎI'}")
    print("-" * 95)
    for r in records:
        ts = r.timestamp[:19].replace("T", " ")
        model = r.model_name[:18]
        route = (r.route_taken or "-")[:16]
        q_snippet = r.query if len(r.query) <= 32 else r.query[:30] + "..."
        ref_mark = " [REFUSED]" if r.is_refused else ""
        print(f"{r.id:<4} | {ts:<19} | {model:<18} | {route:<16} | {q_snippet}{ref_mark}")
    print("=" * 95)
    print(f"Hiển thị {len(records)} bản ghi gần nhất.")


def print_view(db: QueryHistoryDatabase, record_id: int):
    rec = db.get_record(record_id)
    if not rec:
        print(f"❌ Không tìm thấy bản ghi ID #{record_id} trong cơ sở dữ liệu.")
        return

    print("=" * 80)
    print(f"                 CHI TIẾT LỊCH SỬ TRUY VẤN - BẢN GHI #{rec.id}")
    print("=" * 80)
    print(f"⏱️  Thời điểm        : {rec.timestamp}")
    print(f"💬 Phiên (Session)  : {rec.session_id or 'N/A'}")
    print(f"🤖 Mô hình AI       : {rec.model_name} (Provider: {rec.provider})")
    print(f"🧠 Ý định (Intent)  : {rec.intent or 'N/A'}")
    print(f"📈 Độ phức tạp      : {rec.complexity or 'N/A'}")
    print(f"🔀 Nhánh điều phối  : {rec.route_taken or 'N/A'}")
    if rec.routing_reason:
        print(f"💡 Lý do điều phối  : {rec.routing_reason}")
    if rec.sub_queries:
        print(f"🧩 Sub-queries ({len(rec.sub_queries)}):")
        for sq in rec.sub_queries:
            print(f"     - {sq}")

    print("\n" + "-" * 80)
    print(f"📌 CÂU HỎI:\n{rec.query}")
    print("-" * 80)
    print(f"⚖️  CÂU TRẢ LỜI:\n{rec.answer}")
    print("-" * 80)

    if rec.is_refused:
        print(f"🚫 TRẠNG THÁI TỪ CHỐI: CÓ (Lý do: {rec.refusal_reason or 'Thiếu căn cứ'})")

    if rec.citations:
        print(f"\n📚 CĂN CỨ TRÍCH DẪN ({len(rec.citations)}):")
        for idx, cit in enumerate(rec.citations, start=1):
            if isinstance(cit, dict):
                fmt = cit.get("formatted_citation") or f"{cit.get('document_title', '')} - Điều {cit.get('article_number', '')}"
                print(f"   [{idx}] {fmt}")
            else:
                print(f"   [{idx}] {cit}")

    if rec.retrieved_chunks:
        print(f"\n🔍 CÁC CHUNKS TRUY XUẤT ({len(rec.retrieved_chunks)}):")
        for idx, c in enumerate(rec.retrieved_chunks, start=1):
            if isinstance(c, dict):
                print(f"   [{idx}] {c.get('chunk_id')} (Score: {c.get('score', 0):.4f})")
            else:
                print(f"   [{idx}] {c}")

    print("\n📊 THÔNG SỐ VẬN HÀNH:")
    print(f"   • Độ trễ truy xuất   : {rec.retrieval_latency_ms:.2f} ms")
    print(f"   • Độ trễ sinh mẫu    : {rec.generation_latency_ms:.2f} ms")
    print(f"   • Tổng độ trễ        : {rec.total_latency_ms:.2f} ms")
    print(f"   • Tokens ước tính    : {rec.total_tokens} (In: {rec.input_tokens}, Out: {rec.output_tokens})")
    print(f"   • Chi phí ước tính   : ${rec.estimated_cost_usd:.6f}")

    if rec.user_rating is not None or rec.user_feedback:
        print(f"\n⭐ PHẢN HỒI NGƯỜI DÙNG:")
        print(f"   • Điểm đánh giá      : {rec.user_rating} / 5")
        if rec.user_feedback:
            print(f"   • Nhận xét           : {rec.user_feedback}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Tra cứu và quản trị cơ sở dữ liệu lịch sử hỏi đáp pháp luật.")
    parser.add_argument("--summary", action="store_true", help="Hiển thị tổng hợp thống kê lịch sử")
    parser.add_argument("--list", action="store_true", help="Liệt kê danh sách các câu hỏi gần nhất")
    parser.add_argument("--limit", type=int, default=20, help="Số lượng bản ghi tối đa khi liệt kê (mặc định 20)")
    parser.add_argument("--view", type=int, default=None, help="Xem chi tiết một bản ghi theo ID")
    parser.add_argument("--search", type=str, default=None, help="Tìm kiếm câu hỏi/câu trả lời theo từ khóa")
    parser.add_argument("--model", type=str, default=None, help="Lọc theo tên mô hình (Traditional-RAG, CRAG, Adaptive-Agentic-RAG)")
    parser.add_argument("--route", type=str, default=None, help="Lọc theo nhánh điều phối")
    parser.add_argument("--export-json", type=str, default=None, help="Đường dẫn file để xuất dữ liệu JSON")
    parser.add_argument("--export-csv", type=str, default=None, help="Đường dẫn file để xuất dữ liệu CSV")
    parser.add_argument("--rate", type=int, default=None, help="ID bản ghi cần chấm điểm")
    parser.add_argument("--score", type=int, default=None, help="Điểm đánh giá (1-5)")
    parser.add_argument("--feedback", type=str, default=None, help="Nhận xét phản hồi")
    parser.add_argument("--clear", action="store_true", help="Xóa sạch toàn bộ lịch sử (Yêu cầu xác nhận)")
    args = parser.parse_args()

    db = QueryHistoryDatabase()

    if args.summary:
        print_summary(db)
        return

    if args.view is not None:
        print_view(db, args.view)
        return

    if args.rate is not None:
        if args.score is None and args.feedback is None:
            print("❌ Vui lòng cung cấp ít nhất một trong hai tùy chọn: --score [1-5] hoặc --feedback 'nội dung'")
            return
        ok = db.update_feedback(args.rate, user_rating=args.score, user_feedback=args.feedback)
        if ok:
            print(f" Đã cập nhật đánh giá thành công cho bản ghi #{args.rate}!")
        else:
            print(f"❌ Không tìm thấy bản ghi #{args.rate} để cập nhật.")
        return

    if args.export_json:
        n = db.export_to_json(args.export_json)
        print(f" Đã xuất {n} bản ghi lịch sử ra file JSON: {args.export_json}")
        return

    if args.export_csv:
        n = db.export_to_csv(args.export_csv)
        print(f" Đã xuất {n} bản ghi lịch sử ra file CSV: {args.export_csv}")
        return

    if args.clear:
        confirm = input("⚠️ BẠN CÓ CHẮC CHẮN MUỐN XÓA TOÀN BỘ LỊCH SỬ TRUY VẤN? (yes/no): ")
        if confirm.strip().lower() == "yes":
            deleted = db.clear_history()
            print(f" Đã xóa sạch {deleted} bản ghi trong cơ sở dữ liệu.")
        else:
            print("Đã hủy thao tác.")
        return

    # Mặc định hoặc khi có --list hoặc --search
    filter_opt = HistoryFilter(
        limit=args.limit,
        search_keyword=args.search,
        model_name=args.model,
        route_taken=args.route,
    )
    print_list(db, filter_opt)


if __name__ == "__main__":
    main()
