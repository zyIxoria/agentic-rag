"""test_retrieval_improvement.py - Bộ kiểm thử hồi quy tự động (Automated Regression Tests).

Kiểm chứng nghiêm ngặt 8 tình huống bắt buộc theo đặc tả kỹ thuật:
1. Câu hỏi 'Tôi nghỉ việc...' không được trả lời lạc đề dựa trên ngữ cảnh giấy phép lao động nước ngoài.
2. Hệ thống phân biệt được 3 chế độ: Trợ cấp thôi việc, Trợ cấp mất việc làm, Trợ cấp thất nghiệp; không khẳng định khi thiếu thông tin.
3. Mọi trích dẫn (citations) sinh ra phải tồn tại thực sự trong ngữ cảnh/nguồn đã truy xuất.
4. Khi ngữ cảnh hoàn toàn không liên quan, hệ thống kích hoạt từ chối (refused=True) hoặc yêu cầu làm rõ.
5. Query rewriting / expansion bảo tồn ý định gốc của người dùng.
6. Hybrid retrieval dùng chung dữ liệu và không làm biến đổi collection baseline.
7. Baseline V0 (Traditional RAG) chạy độc lập, nguyên bản và tái lập được kết quả.
8. Báo cáo lỗi rõ ràng khi đầu vào không hợp lệ hoặc thiếu dữ liệu, không âm thầm trả về kết quả giả.
"""

import pytest
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from RAG.pipeline.improved_rag import ImprovedRAGPipeline
from RAG.pipeline.config import PipelineConfig
from RAG.retriever.query_expansion import LegalQueryExpander
from RAG.retriever.hybrid_retriever import HybridRetriever
from RAG.retriever.bm25_retriever import BM25OkapiRetriever
from RAG.retriever.reranker import LegalCrossReranker
from RAG.retriever.relevance_gate import RelevanceGate, GateVerdict
from RAG.retriever.schema import RetrievedChunk
from RAG.prompts.legal_prompts import STANDARD_REFUSAL_ANSWER


@pytest.fixture(scope="module")
def mock_config():
    return PipelineConfig(LLM_PROVIDER="mock")


def test_01_target_query_no_foreign_work_permit_chunks(mock_config):
    """Tình huống 1: Câu hỏi 'Tôi nghỉ việc...' không được lấy các văn bản giấy phép lao động nước ngoài."""
    query = "Tôi nghỉ việc thì có được nhận trợ cấp không?"
    pipeline = ImprovedRAGPipeline(version="V4", config=mock_config)
    res = pipeline.answer(query, top_k=5)

    # Đảm bảo không có chunk nào thuộc văn bản GPLĐ cho người nước ngoài trong Top-5
    for chunk in res.retrieved_chunks:
        doc_id = chunk.metadata.get("document_id", "")
        title = (chunk.metadata.get("article_title") or "").lower()
        assert "ND_219_2025" not in doc_id or "giấy phép lao động" not in title, (
            f"Phát hiện văn bản giấy phép lao động nước ngoài trong V4: {chunk.chunk_id} - {title}"
        )

    # Đảm bảo có chứa quy định về trợ cấp thôi việc hoặc mất việc làm (Điều 46 BLLĐ hoặc Điều 8 NĐ 145)
    matched_articles = [
        str(c.metadata.get("article_number", "")) for c in res.retrieved_chunks
    ]
    assert any("46" in a or "8" in a for a in matched_articles), (
        f"Không tìm thấy Điều 46 hoặc Điều 8 trong kết quả V4: {matched_articles}"
    )


def test_02_distinguish_three_allowances_and_handle_ambiguity(mock_config):
    """Tình huống 2: Phân biệt rõ Trợ cấp thôi việc, Mất việc làm và Thất nghiệp khi câu hỏi mơ hồ."""
    query = "Tôi nghỉ việc thì có được nhận trợ cấp không?"
    pipeline = ImprovedRAGPipeline(version="V4", config=mock_config)
    res = pipeline.answer(query, top_k=5)

    assert res.metadata.get("is_ambiguous") is True, "Hệ thống phải nhận diện câu hỏi là mơ hồ."
    
    # Kiểm tra nội dung câu trả lời có phân biệt rõ 3 loại trợ cấp
    answer_text = res.answer.lower()
    assert "trợ cấp thôi việc" in answer_text, "Câu trả lời phải nhắc đến Trợ cấp thôi việc."
    assert "trợ cấp mất việc làm" in answer_text, "Câu trả lời phải nhắc đến Trợ cấp mất việc làm."
    assert "trợ cấp thất nghiệp" in answer_text, "Câu trả lời phải nhắc đến Trợ cấp thất nghiệp."
    assert "tự ý bỏ việc" in answer_text, "Phải lưu ý trường hợp không được hưởng (tự ý bỏ việc)."


def test_03_citations_must_exist_in_retrieved_context(mock_config):
    """Tình huống 3: Mọi trích dẫn tạo ra phải khớp với tài liệu thực tế có trong ngữ cảnh."""
    query = "Thời giờ làm việc bình thường của người lao động được quy định tối đa bao nhiêu giờ trong một ngày và một tuần?"
    pipeline = ImprovedRAGPipeline(version="V4", config=mock_config)
    res = pipeline.answer(query, top_k=5)

    retrieved_chunk_ids = {c.chunk_id for c in res.retrieved_chunks}
    for cit in res.citations:
        assert cit.chunk_id in retrieved_chunk_ids, (
            f"Trích dẫn bịa đặt hoặc không nằm trong retrieved context: {cit.chunk_id}"
        )


def test_04_relevance_gate_refuses_when_no_relevant_evidence(mock_config):
    """Tình huống 4: Khi context bị ô nhiễm hoặc câu hỏi ngoài phạm vi, hệ thống phải từ chối."""
    irrelevant_query = "Thủ tục đăng ký kết hôn và phân chia tài sản thừa kế được quy định như thế nào?"
    pipeline = ImprovedRAGPipeline(version="V4", config=mock_config)
    res = pipeline.answer(irrelevant_query, top_k=5)

    assert res.refused is True, "Hệ thống phải từ chối khi không có căn cứ pháp luật lao động."
    assert STANDARD_REFUSAL_ANSWER in res.answer or "Không tìm thấy" in res.answer, (
        f"Câu trả lời từ chối không chuẩn mực: {res.answer}"
    )


def test_05_query_rewriter_preserves_intent():
    """Tình huống 5: Query rewriting / expansion không làm mất ý định gốc của người dùng."""
    expander = LegalQueryExpander(enabled=True)
    query = "Tôi nghỉ việc thì có được nhận trợ cấp không?"
    expanded = expander.expand(query)

    assert expanded.original_query == query, "Câu hỏi gốc phải được bảo tồn nguyên vẹn."
    assert "chấm dứt hợp đồng lao động" in expanded.search_query, "Phải mở rộng cụm từ 'chấm dứt hợp đồng lao động'."
    assert "trợ cấp thôi việc" in expanded.search_query, "Phải mở rộng cụm từ 'trợ cấp thôi việc'."
    assert expanded.is_ambiguous is True, "Phải gắn cờ is_ambiguous=True."


def test_06_hybrid_retrieval_does_not_modify_baseline_store(mock_config):
    """Tình huống 6: Hybrid retrieval dùng chung dữ liệu và không làm biến đổi collection baseline."""
    from RAG.retriever.config import RetrieverConfig
    ret_config = RetrieverConfig(
        PERSIST_DIRECTORY=mock_config.CHROMA_PERSIST_DIRECTORY,
        COLLECTION_NAME=mock_config.COLLECTION_NAME
    )
    hybrid = HybridRetriever(config=ret_config)
    count_before = hybrid.dense_retriever.vector_store.count()

    chunks = hybrid.retrieve("tiền lương thử việc", top_k=5)
    count_after = hybrid.dense_retriever.vector_store.count()

    assert len(chunks) == 5, "Hybrid retrieval phải trả về đúng Top-5."
    assert count_before == count_after == 1390, (
        f"Số lượng chunk bị thay đổi! Trước: {count_before}, Sau: {count_after}"
    )


def test_07_baseline_v0_is_strictly_preserved_and_reproducible(mock_config):
    """Tình huống 7: Chế độ baseline V0 vẫn chạy độc lập và tái lập được kết quả cũ."""
    query = "Tôi nghỉ việc thì có được nhận trợ cấp không?"
    v0_pipe = ImprovedRAGPipeline(version="V0", config=mock_config)
    res_v0 = v0_pipe.answer(query, top_k=5)

    top_chunk_id = res_v0.retrieved_chunks[0].chunk_id
    assert "ND_219_2025" in top_chunk_id or "Điều7" in top_chunk_id, (
        f"Baseline V0 không tái lập được kết quả cũ! Top 1 nhận được: {top_chunk_id}"
    )


def test_08_error_handling_and_no_silent_failures(mock_config):
    """Tình huống 8: Lỗi đầu vào phải được xử lý minh bạch (Fail-Fast với ValueError)."""
    pipeline = ImprovedRAGPipeline(version="V4", config=mock_config)
    
    # Chuỗi rỗng phải raise ValueError
    with pytest.raises(ValueError, match="không được rỗng"):
        pipeline.answer("")
    
    # Khoảng trắng phải raise ValueError
    with pytest.raises(ValueError, match="không được rỗng"):
        pipeline.answer("     ")
