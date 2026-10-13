"""storage/query_history.py - Quản lý Cơ sở dữ liệu lưu trữ lịch sử truy vấn hỏi đáp pháp luật.

Sử dụng SQLite nhúng nhẹ, bền vững, an toàn giao dịch và không phụ thuộc dịch vụ ngoài.
Mặc định lưu trữ tại: data/history/query_history.db
"""

from __future__ import annotations
import contextlib
import csv
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Union

from storage.schema import (
    HistoryFilter,
    HistoryStatistics,
    QueryHistoryRecord,
)

logger = logging.getLogger("query_history")


class QueryHistoryDatabase:
    """Quản trị cơ sở dữ liệu SQLite lưu trữ lịch sử truy vấn và câu trả lời."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        if db_path is None:
            project_root = Path(__file__).resolve().parent.parent
            self.db_dir = project_root / "data" / "history"
            self.db_path = self.db_dir / "query_history.db"
        else:
            self.db_path = Path(db_path)
            self.db_dir = self.db_path.parent

        self.db_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    @contextlib.contextmanager
    def _connection(self):
        """Context manager đảm bảo đóng connection an toàn ngay sau khi thực thi."""
        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=10.0,
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Khởi tạo schema và các index tối ưu hóa truy vấn."""
        with self._lock:
            with self._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS query_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        timestamp TEXT NOT NULL,
                        model_name TEXT NOT NULL,
                        provider TEXT NOT NULL DEFAULT 'mock',
                        query TEXT NOT NULL,
                        intent TEXT,
                        complexity TEXT,
                        route_taken TEXT,
                        routing_reason TEXT,
                        answer TEXT NOT NULL,
                        citations TEXT,
                        retrieved_chunks TEXT,
                        sub_queries TEXT,
                        is_refused INTEGER NOT NULL DEFAULT 0,
                        refusal_reason TEXT,
                        retrieval_latency_ms REAL DEFAULT 0.0,
                        generation_latency_ms REAL DEFAULT 0.0,
                        total_latency_ms REAL DEFAULT 0.0,
                        input_tokens INTEGER DEFAULT 0,
                        output_tokens INTEGER DEFAULT 0,
                        total_tokens INTEGER DEFAULT 0,
                        estimated_cost_usd REAL DEFAULT 0.0,
                        user_rating INTEGER,
                        user_feedback TEXT,
                        metadata TEXT
                    )
                """)

                # Chỉ mục tăng tốc tìm kiếm và tổng hợp
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_qh_timestamp ON query_history(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_qh_model ON query_history(model_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_qh_session ON query_history(session_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_qh_route ON query_history(route_taken)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_qh_refused ON query_history(is_refused)")
                conn.commit()

    @staticmethod
    def _estimate_tokens_and_cost(query: str, answer: str, context_chunks: List[Any]) -> tuple[int, int, int, float]:
        """Ước tính số lượng tokens và chi phí quy đổi theo chuẩn GPT-4o-mini."""
        q_words = len(query.split())
        ctx_words = sum(len(str(c).split()) for c in context_chunks)
        ans_words = len(answer.split())

        in_toks = int((q_words + ctx_words) * 1.3)
        out_toks = int(ans_words * 1.3)
        tot_toks = in_toks + out_toks

        # Giá GPT-4o-mini: $0.15/1M in, $0.60/1M out
        cost_usd = (in_toks / 1_000_000) * 0.15 + (out_toks / 1_000_000) * 0.60
        return in_toks, out_toks, tot_toks, round(cost_usd, 6)

    def save_record(self, record: QueryHistoryRecord) -> int:
        """Lưu một bản ghi truy vấn vào cơ sở dữ liệu."""
        with self._lock:
            with self._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO query_history (
                        session_id, timestamp, model_name, provider, query,
                        intent, complexity, route_taken, routing_reason,
                        answer, citations, retrieved_chunks, sub_queries,
                        is_refused, refusal_reason,
                        retrieval_latency_ms, generation_latency_ms, total_latency_ms,
                        input_tokens, output_tokens, total_tokens, estimated_cost_usd,
                        user_rating, user_feedback, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.session_id,
                    record.timestamp,
                    record.model_name,
                    record.provider,
                    record.query,
                    record.intent,
                    record.complexity,
                    record.route_taken,
                    record.routing_reason,
                    record.answer,
                    json.dumps(record.citations, ensure_ascii=False),
                    json.dumps(record.retrieved_chunks, ensure_ascii=False),
                    json.dumps(record.sub_queries, ensure_ascii=False),
                    1 if record.is_refused else 0,
                    record.refusal_reason,
                    record.retrieval_latency_ms,
                    record.generation_latency_ms,
                    record.total_latency_ms,
                    record.input_tokens,
                    record.output_tokens,
                    record.total_tokens,
                    record.estimated_cost_usd,
                    record.user_rating,
                    record.user_feedback,
                    json.dumps(record.metadata, ensure_ascii=False),
                ))
                conn.commit()
                return cursor.lastrowid

    def get_record(self, record_id: int) -> Optional[QueryHistoryRecord]:
        """Lấy chi tiết một bản ghi theo ID."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM query_history WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def get_history(self, filter_opts: Optional[HistoryFilter] = None) -> List[QueryHistoryRecord]:
        """Truy vấn danh sách lịch sử có hỗ trợ lọc, tìm kiếm và phân trang."""
        opts = filter_opts or HistoryFilter()
        clauses = []
        params = []

        if opts.session_id:
            clauses.append("session_id = ?")
            params.append(opts.session_id)

        if opts.model_name:
            clauses.append("model_name = ?")
            params.append(opts.model_name)

        if opts.route_taken:
            clauses.append("route_taken = ?")
            params.append(opts.route_taken)

        if opts.is_refused is not None:
            clauses.append("is_refused = ?")
            params.append(1 if opts.is_refused else 0)

        if opts.search_keyword:
            clauses.append("(query LIKE ? OR answer LIKE ?)")
            keyword = f"%{opts.search_keyword}%"
            params.extend([keyword, keyword])

        if opts.start_time:
            clauses.append("timestamp >= ?")
            params.append(opts.start_time)

        if opts.end_time:
            clauses.append("timestamp <= ?")
            params.append(opts.end_time)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM query_history {where_sql} ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([opts.limit, opts.offset])

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [self._row_to_record(r) for r in rows]

    def update_feedback(
        self,
        record_id: int,
        user_rating: Optional[int] = None,
        user_feedback: Optional[str] = None,
    ) -> bool:
        """Cập nhật đánh giá hoặc phản hồi của người dùng cho câu trả lời."""
        updates = []
        params = []

        if user_rating is not None:
            updates.append("user_rating = ?")
            params.append(user_rating)

        if user_feedback is not None:
            updates.append("user_feedback = ?")
            params.append(user_feedback)

        if not updates:
            return False

        params.append(record_id)
        with self._lock:
            with self._connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE query_history SET {', '.join(updates)} WHERE id = ?",
                    params,
                )
                conn.commit()
                return cursor.rowcount > 0

    def delete_record(self, record_id: int) -> bool:
        """Xóa một bản ghi theo ID."""
        with self._lock:
            with self._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM query_history WHERE id = ?", (record_id,))
                conn.commit()
                return cursor.rowcount > 0

    def clear_history(self, session_id: Optional[str] = None) -> int:
        """Xóa toàn bộ lịch sử hoặc theo session_id."""
        with self._lock:
            with self._connection() as conn:
                cursor = conn.cursor()
                if session_id:
                    cursor.execute("DELETE FROM query_history WHERE session_id = ?", (session_id,))
                else:
                    cursor.execute("DELETE FROM query_history")
                conn.commit()
                return cursor.rowcount

    def get_statistics(self) -> HistoryStatistics:
        """Tổng hợp các chỉ số vận hành và thống kê từ lịch sử."""
        with self._connection() as conn:
            cursor = conn.cursor()

            # Tổng số truy vấn và từ chối
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_refused = 1 THEN 1 ELSE 0 END) as total_refused,
                    AVG(total_latency_ms) as avg_latency,
                    AVG(total_tokens) as avg_tokens,
                    SUM(estimated_cost_usd) as total_cost
                FROM query_history
            """)
            overall = cursor.fetchone()
            total = overall["total"] or 0
            refused = overall["total_refused"] or 0
            avg_lat = overall["avg_latency"] or 0.0
            avg_tok = overall["avg_tokens"] or 0.0
            tot_cost = overall["total_cost"] or 0.0

            # Phân bổ theo mô hình
            cursor.execute("SELECT model_name, COUNT(*) as cnt FROM query_history GROUP BY model_name")
            by_model = {r["model_name"]: r["cnt"] for r in cursor.fetchall()}

            # Phân bổ theo nhánh điều phối
            cursor.execute("SELECT route_taken, COUNT(*) as cnt FROM query_history WHERE route_taken IS NOT NULL GROUP BY route_taken")
            by_route = {r["route_taken"]: r["cnt"] for r in cursor.fetchall()}

            # Phản hồi người dùng
            cursor.execute("SELECT user_rating, COUNT(*) as cnt FROM query_history WHERE user_rating IS NOT NULL GROUP BY user_rating")
            feedback = {str(r["user_rating"]): r["cnt"] for r in cursor.fetchall()}

            return HistoryStatistics(
                total_queries=total,
                total_refusals=refused,
                refusal_rate=round(refused / total, 4) if total > 0 else 0.0,
                queries_by_model=by_model,
                queries_by_route=by_route,
                avg_total_latency_ms=round(avg_lat, 2),
                avg_total_tokens=round(avg_tok, 1),
                total_estimated_cost_usd=round(tot_cost, 6),
                feedback_stats=feedback,
            )

    def export_to_json(self, filepath: Union[str, Path], session_id: Optional[str] = None) -> int:
        """Xuất lịch sử ra file JSON."""
        filter_opt = HistoryFilter(session_id=session_id, limit=1_000_000)
        records = self.get_history(filter_opt)
        data = [r.model_dump() for r in records]

        out_path = Path(filepath)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return len(data)

    def export_to_csv(self, filepath: Union[str, Path], session_id: Optional[str] = None) -> int:
        """Xuất lịch sử ra file CSV."""
        filter_opt = HistoryFilter(session_id=session_id, limit=1_000_000)
        records = self.get_history(filter_opt)

        out_path = Path(filepath)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "id", "timestamp", "session_id", "model_name", "provider", "query",
            "intent", "complexity", "route_taken", "is_refused", "refusal_reason",
            "total_latency_ms", "total_tokens", "estimated_cost_usd", "answer"
        ]

        with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                row = {k: getattr(r, k) for k in fieldnames}
                writer.writerow(row)
        return len(records)

    # =========================================================================
    # CÁC PHƯƠNG THỨC TIỆN ÍCH TỰ ĐỘNG NẠP KẾT QUẢ TỪ PIPELINES
    # =========================================================================

    def log_rag_response(
        self,
        res: Any,
        session_id: Optional[str] = None,
        user_rating: Optional[int] = None,
        user_feedback: Optional[str] = None,
    ) -> int:
        """Tự động phân tích và lưu trữ đối tượng RAGResponse của Traditional RAG."""
        retrieved_raw = getattr(res, "retrieved_chunks", [])
        retrieved_list = []
        for c in retrieved_raw:
            c_dict = {
                "chunk_id": getattr(c, "chunk_id", ""),
                "score": getattr(c, "score", 0.0),
                "document_id": getattr(c, "metadata", {}).get("document_id", "") if hasattr(c, "metadata") else "",
                "article_number": getattr(c, "metadata", {}).get("article_number", "") if hasattr(c, "metadata") else "",
            }
            retrieved_list.append(c_dict)

        citations_raw = getattr(res, "citations", [])
        citations_list = [
            c.model_dump() if hasattr(c, "model_dump") else (c if isinstance(c, dict) else {"citation": str(c)})
            for c in citations_raw
        ]

        in_tok, out_tok, tot_tok, cost_usd = self._estimate_tokens_and_cost(
            query=res.question,
            answer=res.answer,
            context_chunks=retrieved_raw,
        )

        rec = QueryHistoryRecord(
            session_id=session_id,
            model_name="Traditional-RAG",
            provider=getattr(res, "provider", "mock"),
            query=res.question,
            answer=res.answer,
            citations=citations_list,
            retrieved_chunks=retrieved_list,
            is_refused=bool(res.refused),
            refusal_reason=getattr(res, "refusal_reason", None),
            retrieval_latency_ms=getattr(res, "retrieval_latency", 0.0),
            generation_latency_ms=getattr(res, "generation_latency", 0.0),
            total_latency_ms=getattr(res, "latency", 0.0),
            input_tokens=in_tok,
            output_tokens=out_tok,
            total_tokens=tot_tok,
            estimated_cost_usd=cost_usd,
            user_rating=user_rating,
            user_feedback=user_feedback,
        )
        return self.save_record(rec)

    def log_crag_response(
        self,
        res: Any,
        session_id: Optional[str] = None,
        user_rating: Optional[int] = None,
        user_feedback: Optional[str] = None,
    ) -> int:
        """Tự động phân tích và lưu trữ đối tượng CRAGResponse của Corrective RAG."""
        citations_raw = getattr(res, "citations", [])
        citations_list = [
            c.model_dump() if hasattr(c, "model_dump") else (c if isinstance(c, dict) else {"citation": str(c)})
            for c in citations_raw
        ]

        retrieved_raw = getattr(res, "retrieved_chunks", [])
        retrieved_list = []
        for c in retrieved_raw:
            c_dict = {
                "chunk_id": getattr(c, "chunk_id", ""),
                "score": getattr(c, "score", 0.0),
            }
            retrieved_list.append(c_dict)

        telemetry = getattr(res, "telemetry", None)
        telemetry = getattr(res, "telemetry", None)
        tot_lat = getattr(telemetry, "total_latency", getattr(res, "latency", 0.0)) if telemetry else getattr(res, "latency", 0.0)
        ret_lat = getattr(telemetry, "retrieval_latency", getattr(res, "retrieval_latency", 0.0)) if telemetry else getattr(res, "retrieval_latency", 0.0)
        gen_lat = getattr(telemetry, "generation_latency", getattr(res, "generation_latency", 0.0)) if telemetry else getattr(res, "generation_latency", 0.0)

        q_text = getattr(res, "question", getattr(res, "original_query", ""))
        action_val = getattr(res, "action_taken", "CORRECTIVE_RAG" if getattr(res, "corrective_triggered", False) else "DIRECT_PASS")
        rewritten = getattr(res, "rewritten_query", None)
        sub_queries = [rewritten] if rewritten else []

        in_tok, out_tok, tot_tok, cost_usd = self._estimate_tokens_and_cost(
            query=q_text,
            answer=res.answer,
            context_chunks=retrieved_raw,
        )

        rec = QueryHistoryRecord(
            session_id=session_id,
            model_name="CRAG",
            provider=getattr(res, "provider", "mock"),
            query=q_text,
            route_taken=action_val,
            routing_reason=f"Corrective triggered: {getattr(res, 'corrective_triggered', False)}",
            answer=res.answer,
            citations=citations_list,
            retrieved_chunks=retrieved_list,
            sub_queries=sub_queries,
            is_refused=bool(res.refused),
            refusal_reason=getattr(res, "refusal_reason", None),
            retrieval_latency_ms=ret_lat,
            generation_latency_ms=gen_lat,
            total_latency_ms=tot_lat,
            input_tokens=in_tok,
            output_tokens=out_tok,
            total_tokens=tot_tok,
            estimated_cost_usd=cost_usd,
            user_rating=user_rating,
            user_feedback=user_feedback,
        )
        return self.save_record(rec)

    def log_adaptive_response(
        self,
        res: Any,
        session_id: Optional[str] = None,
        user_rating: Optional[int] = None,
        user_feedback: Optional[str] = None,
    ) -> int:
        """Tự động phân tích và lưu trữ đối tượng AdaptiveRAGResponse của Adaptive Agentic RAG."""
        citations_raw = getattr(res, "citations", [])
        citations_list = [
            c.model_dump() if hasattr(c, "model_dump") else (c if isinstance(c, dict) else {"citation": str(c)})
            for c in citations_raw
        ]

        retrieved_raw = getattr(res, "retrieved_chunks", [])
        retrieved_list = []
        for c in retrieved_raw:
            c_dict = {
                "chunk_id": getattr(c, "chunk_id", ""),
                "score": getattr(c, "score", 0.0),
            }
            retrieved_list.append(c_dict)

        trace = getattr(res, "trace", None)
        sub_queries = []
        if trace and hasattr(trace, "plan") and trace.plan:
            sub_queries = [getattr(sq, "sub_query", str(sq)) for sq in getattr(trace.plan, "sub_queries", [])]

        route_val = res.route_taken.value if hasattr(res.route_taken, "value") else str(res.route_taken)
        intent_val = (
            res.classification.intent.value
            if hasattr(res, "classification") and hasattr(res.classification, "intent")
            else None
        )
        comp_val = (
            res.classification.complexity.value
            if hasattr(res, "classification") and hasattr(res.classification, "complexity")
            else None
        )

        in_tok, out_tok, tot_tok, cost_usd = self._estimate_tokens_and_cost(
            query=res.question,
            answer=res.answer,
            context_chunks=retrieved_raw,
        )

        # Nếu đi qua nhánh DIRECT_REFUSAL hoặc DIRECT_ANSWER, input tokens cực thấp
        if route_val in ("DIRECT_REFUSAL", "DIRECT_ANSWER"):
            in_tok = int(len(res.question.split()) * 1.3)
            tot_tok = in_tok + out_tok
            cost_usd = round((in_tok / 1_000_000) * 0.15 + (out_tok / 1_000_000) * 0.60, 6)

        rec = QueryHistoryRecord(
            session_id=session_id,
            model_name="Adaptive-Agentic-RAG",
            provider="mock",
            query=res.question,
            intent=intent_val,
            complexity=comp_val,
            route_taken=route_val,
            routing_reason=getattr(res, "routing_reason", None),
            answer=res.answer,
            citations=citations_list,
            retrieved_chunks=retrieved_list,
            sub_queries=sub_queries,
            is_refused=bool(res.refused),
            refusal_reason=getattr(res, "refusal_reason", None),
            retrieval_latency_ms=getattr(trace, "execution_latency_ms", 0.0) if trace else 0.0,
            generation_latency_ms=getattr(trace, "synthesis_latency_ms", 0.0) if trace else 0.0,
            total_latency_ms=getattr(res, "latency_ms", 0.0),
            input_tokens=in_tok,
            output_tokens=out_tok,
            total_tokens=tot_tok,
            estimated_cost_usd=cost_usd,
            user_rating=user_rating,
            user_feedback=user_feedback,
        )
        return self.save_record(rec)

    def _row_to_record(self, row: sqlite3.Row) -> QueryHistoryRecord:
        citations = []
        if row["citations"]:
            try:
                citations = json.loads(row["citations"])
            except Exception:
                pass

        chunks = []
        if row["retrieved_chunks"]:
            try:
                chunks = json.loads(row["retrieved_chunks"])
            except Exception:
                pass

        sub_q = []
        if row["sub_queries"]:
            try:
                sub_q = json.loads(row["sub_queries"])
            except Exception:
                pass

        meta = {}
        if row["metadata"]:
            try:
                meta = json.loads(row["metadata"])
            except Exception:
                pass

        return QueryHistoryRecord(
            id=row["id"],
            session_id=row["session_id"],
            timestamp=row["timestamp"],
            model_name=row["model_name"],
            provider=row["provider"],
            query=row["query"],
            intent=row["intent"],
            complexity=row["complexity"],
            route_taken=row["route_taken"],
            routing_reason=row["routing_reason"],
            answer=row["answer"],
            citations=citations,
            retrieved_chunks=chunks,
            sub_queries=sub_q,
            is_refused=bool(row["is_refused"]),
            refusal_reason=row["refusal_reason"],
            retrieval_latency_ms=row["retrieval_latency_ms"],
            generation_latency_ms=row["generation_latency_ms"],
            total_latency_ms=row["total_latency_ms"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            total_tokens=row["total_tokens"],
            estimated_cost_usd=row["estimated_cost_usd"],
            user_rating=row["user_rating"],
            user_feedback=row["user_feedback"],
            metadata=meta,
        )
