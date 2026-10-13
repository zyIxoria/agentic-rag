"""tests/test_query_history.py - Unit tests cho hệ thống lưu trữ lịch sử truy vấn SQLite."""

import json
from pathlib import Path
import tempfile
import pytest

from storage.query_history import QueryHistoryDatabase
from storage.schema import HistoryFilter, QueryHistoryRecord


@pytest.fixture
def temp_db(tmp_path):
    """Fixture tạo SQLite DB tạm thời cho test."""
    db_path = tmp_path / "test_history.db"
    db = QueryHistoryDatabase(db_path=db_path)
    return db


def test_init_db(temp_db):
    """Kiểm tra khởi tạo database và bảng query_history."""
    assert temp_db.db_path.exists()
    stats = temp_db.get_statistics()
    assert stats.total_queries == 0
    assert stats.total_refusals == 0


def test_save_and_get_record(temp_db):
    """Kiểm tra lưu bản ghi và truy vấn lại theo ID."""
    rec = QueryHistoryRecord(
        session_id="session_001",
        model_name="Adaptive-Agentic-RAG",
        provider="mock",
        query="Thời giờ làm việc bình thường là bao nhiêu giờ?",
        intent="LEGAL_DIRECT_DEF",
        complexity="SIMPLE_SINGLE_HOP",
        route_taken="CORRECTIVE_RAG",
        routing_reason="Độ tin cậy vừa phải",
        answer="Căn cứ Điều 105 Bộ luật Lao động 2019, thời giờ làm việc không quá 08 giờ/ngày.",
        citations=[{"document_title": "Bộ luật Lao động 2019", "article_number": "105"}],
        retrieved_chunks=[{"chunk_id": "BLLD_Điều105_1", "score": 0.85}],
        is_refused=False,
        retrieval_latency_ms=120.5,
        generation_latency_ms=1.2,
        total_latency_ms=121.7,
        input_tokens=450,
        output_tokens=120,
        total_tokens=570,
        estimated_cost_usd=0.00014,
    )

    rec_id = temp_db.save_record(rec)
    assert rec_id > 0

    fetched = temp_db.get_record(rec_id)
    assert fetched is not None
    assert fetched.id == rec_id
    assert fetched.session_id == "session_001"
    assert fetched.model_name == "Adaptive-Agentic-RAG"
    assert fetched.query == "Thời giờ làm việc bình thường là bao nhiêu giờ?"
    assert len(fetched.citations) == 1
    assert fetched.citations[0]["article_number"] == "105"
    assert fetched.is_refused is False
    assert fetched.total_tokens == 570


def test_filter_and_search(temp_db):
    """Kiểm tra chức năng tìm kiếm và lọc lịch sử."""
    r1 = QueryHistoryRecord(
        session_id="sess_A",
        model_name="Traditional-RAG",
        query="Quy định về thời gian thử việc?",
        answer="Thời gian thử việc do hai bên thỏa thuận...",
        is_refused=False,
    )
    r2 = QueryHistoryRecord(
        session_id="sess_A",
        model_name="CRAG",
        query="Thủ tục ly hôn tại tòa án?",
        answer="Nội dung không thuộc thẩm quyền tra cứu pháp luật lao động.",
        is_refused=True,
        refusal_reason="Ngoài phạm vi",
    )
    r3 = QueryHistoryRecord(
        session_id="sess_B",
        model_name="Adaptive-Agentic-RAG",
        query="Tiền lương làm thêm giờ vào ban đêm?",
        answer="Theo Điều 98 BLLĐ 2019...",
        is_refused=False,
    )

    temp_db.save_record(r1)
    temp_db.save_record(r2)
    temp_db.save_record(r3)

    # Lọc theo session
    res_sess = temp_db.get_history(HistoryFilter(session_id="sess_A"))
    assert len(res_sess) == 2

    # Lọc theo trạng thái từ chối
    res_ref = temp_db.get_history(HistoryFilter(is_refused=True))
    assert len(res_ref) == 1
    assert res_ref[0].model_name == "CRAG"

    # Tìm kiếm theo từ khóa
    res_kw = temp_db.get_history(HistoryFilter(search_keyword="thêm giờ"))
    assert len(res_kw) == 1
    assert res_kw[0].query == "Tiền lương làm thêm giờ vào ban đêm?"


def test_update_feedback(temp_db):
    """Kiểm tra cập nhật đánh giá rating và phản hồi."""
    rec = QueryHistoryRecord(
        model_name="Traditional-RAG",
        query="Thử việc tối đa bao nhiêu ngày?",
        answer="Tối đa 180 ngày đối với người quản lý doanh nghiệp.",
    )
    rec_id = temp_db.save_record(rec)

    ok = temp_db.update_feedback(rec_id, user_rating=5, user_feedback="Câu trả lời rất chính xác và đầy đủ.")
    assert ok is True

    updated = temp_db.get_record(rec_id)
    assert updated.user_rating == 5
    assert updated.user_feedback == "Câu trả lời rất chính xác và đầy đủ."


def test_statistics(temp_db):
    """Kiểm tra tổng hợp chỉ số thống kê."""
    r1 = QueryHistoryRecord(
        model_name="Traditional-RAG",
        query="Q1",
        answer="A1",
        is_refused=False,
        total_latency_ms=100.0,
        total_tokens=1000,
        estimated_cost_usd=0.001,
    )
    r2 = QueryHistoryRecord(
        model_name="Adaptive-Agentic-RAG",
        route_taken="DIRECT_REFUSAL",
        query="Q2",
        answer="Từ chối",
        is_refused=True,
        total_latency_ms=50.0,
        total_tokens=200,
        estimated_cost_usd=0.0001,
    )
    temp_db.save_record(r1)
    temp_db.save_record(r2)

    stats = temp_db.get_statistics()
    assert stats.total_queries == 2
    assert stats.total_refusals == 1
    assert stats.refusal_rate == 0.5
    assert stats.queries_by_model["Traditional-RAG"] == 1
    assert stats.queries_by_model["Adaptive-Agentic-RAG"] == 1
    assert stats.queries_by_route["DIRECT_REFUSAL"] == 1
    assert stats.avg_total_latency_ms == 75.0
    assert stats.avg_total_tokens == 600.0


def test_export_json_and_csv(temp_db, tmp_path):
    """Kiểm tra chức năng xuất file JSON và CSV."""
    rec = QueryHistoryRecord(
        model_name="Adaptive-Agentic-RAG",
        query="Xuất khẩu lao động cần điều kiện gì?",
        answer="Cần hợp đồng hợp lệ...",
        total_latency_ms=150.0,
    )
    temp_db.save_record(rec)

    json_file = tmp_path / "history.json"
    n_json = temp_db.export_to_json(json_file)
    assert n_json == 1
    assert json_file.exists()

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["query"] == "Xuất khẩu lao động cần điều kiện gì?"

    csv_file = tmp_path / "history.csv"
    n_csv = temp_db.export_to_csv(csv_file)
    assert n_csv == 1
    assert csv_file.exists()


def test_delete_and_clear(temp_db):
    """Kiểm tra xóa bản ghi và xóa sạch database."""
    r1 = temp_db.save_record(QueryHistoryRecord(model_name="M1", query="Q1", answer="A1"))
    r2 = temp_db.save_record(QueryHistoryRecord(model_name="M2", query="Q2", answer="A2"))
    assert temp_db.get_statistics().total_queries == 2

    # Xóa 1 bản ghi
    assert temp_db.delete_record(r1) is True
    assert temp_db.get_statistics().total_queries == 1
    assert temp_db.get_record(r1) is None

    # Xóa toàn bộ
    cleared = temp_db.clear_history()
    assert cleared == 1
    assert temp_db.get_statistics().total_queries == 0


def test_log_rag_response_adapter(temp_db):
    """Kiểm tra adapter log_rag_response nạp RAGResponse."""
    from RAG.schemas.pipeline_schema import RAGResponse
    from RAG.citation.schema import LegalCitation
    from RAG.retriever.schema import RetrievedChunk

    rag_res = RAGResponse(
        question="Thời gian nghỉ giữa giờ là bao lâu?",
        answer="Theo Điều 109 BLLĐ 2019, người lao động được nghỉ giữa giờ ít nhất 30 phút.",
        citations=[LegalCitation(
            source_id="1",
            source_number=1,
            document_title="Bộ luật Lao động 2019",
            article_number="109",
            formatted_citation="[Bộ luật Lao động 2019, Điều 109]",
            is_valid=True,
        )],
        retrieved_chunks=[RetrievedChunk(
            chunk_id="BLLD_Điều109_1",
            rank=1,
            score=0.88,
            metadata={"document_id": "BLLD_2019", "article_number": "109"},
            content="Làm việc theo ca được nghỉ giữa giờ...",
        )],
        retrieval_latency=110.0,
        generation_latency=15.0,
        latency=125.0,
        model_name="mock-legal",
        provider="mock",
        refused=False,
    )

    rec_id = temp_db.log_rag_response(rag_res, session_id="rag_sess_1")
    assert rec_id > 0

    record = temp_db.get_record(rec_id)
    assert record.model_name == "Traditional-RAG"
    assert record.session_id == "rag_sess_1"
    assert record.query == "Thời gian nghỉ giữa giờ là bao lâu?"
    assert len(record.citations) == 1
    assert record.citations[0]["article_number"] == "109"
    assert len(record.retrieved_chunks) == 1
    assert record.retrieved_chunks[0]["chunk_id"] == "BLLD_Điều109_1"
    assert record.is_refused is False


def test_log_crag_response_adapter(temp_db):
    """Kiểm tra adapter log_crag_response nạp CRAGResponse."""
    from CRAG.pipeline.schema import CRAGResponse, CRAGTelemetry
    from CRAG.evaluator.schema import RetrievalGradingResult, GradeVerdict, ActionTrigger

    crag_res = CRAGResponse(
        question="Học nghề không đóng học phí có phải làm việc cho người sử dụng lao động không?",
        answer="Căn cứ Điều 62 BLLĐ 2019, hai bên phải ký hợp đồng đào tạo nghề...",
        action_taken="REFINE",
        grading_result=RetrievalGradingResult(
            query="Học nghề không đóng học phí có phải làm việc cho người sử dụng lao động không?",
            overall_confidence=0.72,
            overall_verdict=GradeVerdict.CORRECT,
            recommended_action=ActionTrigger.REFINE,
            latency_ms=10.0,
        ),
        citations=[],
        retrieved_chunks=[],
        refused=False,
        telemetry=CRAGTelemetry(
            total_latency=150.0,
            retrieval_latency=130.0,
            grading_latency=10.0,
            generation_latency=10.0,
        ),
    )

    rec_id = temp_db.log_crag_response(crag_res, session_id="crag_sess_1")
    assert rec_id > 0

    record = temp_db.get_record(rec_id)
    assert record.model_name == "CRAG"
    assert record.route_taken == "REFINE"
    assert record.total_latency_ms == 150.0


def test_log_adaptive_response_adapter(temp_db):
    """Kiểm tra adapter log_adaptive_response nạp AdaptiveRAGResponse."""
    from Adaptive_RAG.orchestration.schema import (
        AdaptiveRAGResponse,
        OrchestrationTrace,
    )
    from Adaptive_RAG.classifier.schema import (
        ClassificationResult,
        ComplexityLevel,
        QueryIntent,
        RoutingDecision,
    )

    adapt_res = AdaptiveRAGResponse(
        question="So sánh hợp đồng xác định thời hạn và không xác định thời hạn?",
        answer="Hợp đồng xác định thời hạn có mốc kết thúc...",
        route_taken=RoutingDecision.DECOMPOSE_AGENTIC,
        classification=ClassificationResult(
            query="So sánh hợp đồng xác định thời hạn và không xác định thời hạn?",
            intent=QueryIntent.LEGAL_MULTI_DOCUMENT,
            complexity=ComplexityLevel.COMPLEX_MULTI_HOP,
            suggested_route=RoutingDecision.DECOMPOSE_AGENTIC,
            confidence=0.92,
            reasoning="So sánh hợp đồng",
        ),
        trace=OrchestrationTrace(
            query="So sánh hợp đồng xác định thời hạn và không xác định thời hạn?",
            classification=ClassificationResult(
                query="So sánh hợp đồng xác định thời hạn và không xác định thời hạn?",
                intent=QueryIntent.LEGAL_MULTI_DOCUMENT,
                complexity=ComplexityLevel.COMPLEX_MULTI_HOP,
                suggested_route=RoutingDecision.DECOMPOSE_AGENTIC,
                confidence=0.92,
                reasoning="So sánh hợp đồng",
            ),
            route_chosen=RoutingDecision.DECOMPOSE_AGENTIC,
            routing_latency_ms=0.5,
            execution_latency_ms=190.0,
            synthesis_latency_ms=19.5,
            total_latency_ms=210.0,
        ),
        citations=[],
        retrieved_chunks=[],
        latency_ms=210.0,
        refused=False,
    )

    rec_id = temp_db.log_adaptive_response(adapt_res, session_id="adapt_sess_1")
    assert rec_id > 0

    record = temp_db.get_record(rec_id)
    assert record.model_name == "Adaptive-Agentic-RAG"
    assert record.route_taken == "DECOMPOSE_AGENTIC"
    assert record.intent == "LEGAL_MULTI_DOC"
    assert record.complexity == "COMPLEX_MULTI_HOP"
    assert record.total_latency_ms == 210.0

