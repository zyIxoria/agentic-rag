"""test_corrective_pipeline.py - Kiểm thử tích hợp toàn diện (E2E Integration Test) cho Corrective RAG (TASK CRAG-04 & CRAG-06).

Thực thi trên dữ liệu thật (Real ChromaDB Vector Store + Real ONNX Embeddings + Mock/Real Pipeline):
- Question -> Retriever -> Evaluator -> Rewriter -> Retriever -> Evaluator -> Context Builder -> Generator -> Citation/Refusal -> CRAGResponse.
- Kiểm tra cả ca trả lời thành công, ca ngoài phạm vi và ca thiếu căn cứ pháp lý.
"""

import pytest
from pathlib import Path

from RAG.corrective.corrective_rag import CorrectiveRAGPipeline
from RAG.corrective.schemas import CRAGResponse, EvaluationStatus
from RAG.corrective.config import CRAGConfig
from RAG.vector_store.chroma_store import PersistentChromaStore
from RAG.embedding.embeddings import get_embedding_provider
from RAG.retriever.dense_retriever import DenseTopKRetriever


@pytest.fixture(scope="module")
def real_crag_pipeline() -> CorrectiveRAGPipeline:
    """Khởi tạo pipeline với Retriever thật từ ChromaDB và all-MiniLM-L6-v2 ONNX."""
    config = CRAGConfig(
        TOP_K=5,
        SIMILARITY_THRESHOLD=0.45,
        LLM_PROVIDER="mock",
        CHROMA_PERSIST_DIRECTORY="data/chroma_db",
        COLLECTION_NAME="legal_labor_baseline_minilm"
    )

    chroma_store = PersistentChromaStore(persist_directory=config.CHROMA_PERSIST_DIRECTORY)
    embedding_provider = get_embedding_provider()
    chroma_store.load_collection(
        name=config.COLLECTION_NAME,
        expected_dimension=embedding_provider.dimension,
        expected_model=embedding_provider.model_name
    )

    retriever = DenseTopKRetriever(
        vector_store=chroma_store,
        embedding_provider=embedding_provider,
    )

    return CorrectiveRAGPipeline(
        config=config,
        retriever=retriever
    )


class TestCorrectivePipelineIntegration:
    """Tập kiểm thử tích hợp thực tế toàn chuỗi CRAG Pipeline."""

    def test_01_real_e2e_answerable_question(self, real_crag_pipeline: CorrectiveRAGPipeline):
        """TEST 1: Chạy thực tế câu hỏi pháp lý hợp lệ qua toàn bộ pipeline."""
        question = "Thời giờ làm việc bình thường của người lao động được quy định tối đa bao nhiêu giờ trong một ngày và một tuần?"
        
        response: CRAGResponse = real_crag_pipeline.answer(question)

        # Kiểm tra tính toàn vẹn của CRAGResponse
        assert isinstance(response, CRAGResponse)
        assert response.question == question
        assert response.refused is False
        assert len(response.answer) > 0
        assert len(response.citations) > 0
        assert len(response.retrieved_chunks) > 0
        assert response.latency > 0
        assert response.latency_ms > 0
        assert response.initial_evaluation.status in (EvaluationStatus.SUFFICIENT, EvaluationStatus.PARTIAL)
        assert response.retry_count in (0, 1)

    def test_02_real_e2e_out_of_scope_question(self, real_crag_pipeline: CorrectiveRAGPipeline):
        """TEST 2: Chạy thực tế câu hỏi ngoài phạm vi (Out-of-Scope) -> Bắt buộc Refusal."""
        question = "Cách mua vé xem trực tiếp các trận bóng đá giải Ngoại hạng Anh mùa giải 2026 dành cho khách du lịch?"

        response: CRAGResponse = real_crag_pipeline.answer(question)

        assert isinstance(response, CRAGResponse)
        assert response.refused is True
        assert response.citations == []
        assert "không tìm thấy đủ căn cứ" in response.answer.lower()
        assert response.final_evaluation.status == EvaluationStatus.INSUFFICIENT
        assert response.corrective_triggered is True
        assert response.retry_count == 1

    def test_03_real_e2e_insufficient_evidence_question(self, real_crag_pipeline: CorrectiveRAGPipeline):
        """TEST 3: Chạy thực tế câu hỏi đòi hỏi luật ngoài corpus (Category F: Luật BHXH) -> Bắt buộc Refusal."""
        question = "Tỷ lệ hưởng lương hưu tối đa của lao động nữ tham gia bảo hiểm xã hội bắt buộc theo Luật Bảo hiểm xã hội 2014 là bao nhiêu phần trăm?"

        response: CRAGResponse = real_crag_pipeline.answer(question)

        assert isinstance(response, CRAGResponse)
        assert response.refused is True
        assert response.citations == []
        assert response.final_evaluation.status == EvaluationStatus.INSUFFICIENT
        assert response.corrective_triggered is True
        assert response.retry_count == 1

    def test_04_trace_dictionary_serialization(self, real_crag_pipeline: CorrectiveRAGPipeline):
        """TEST 4: Kiểm tra cấu trúc Trace Dict được xuất ra phục vụ phân tích thực nghiệm."""
        question = "Người lao động được nghỉ bao nhiêu ngày khi kết hôn?"
        response: CRAGResponse = real_crag_pipeline.answer(question)

        trace = response.to_dict()

        assert "original_query" in trace
        assert "initial_retrieval" in trace
        assert "initial_evaluation" in trace
        assert "corrective_triggered" in trace
        assert "final_evaluation" in trace
        assert "retry_count" in trace
        assert "latency_ms" in trace
        assert "citations" in trace
