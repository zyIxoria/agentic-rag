"""
Adaptive RAG Pipeline.
Đường ống hoàn chỉnh của Adaptive Agentic RAG (TASK RAG-18).
"""

from __future__ import annotations
import logging
from typing import Optional

from RAG.pipeline.config import PipelineConfig, default_pipeline_config
from RAG.retriever.dense_retriever import DenseTopKRetriever
from RAG.generator.base import BaseLegalGenerator
from RAG.citation.resolver import CitationResolver
from CRAG.config import CRAGConfig
from Adaptive_RAG.config import AdaptiveRAGConfig, adaptive_config
from Adaptive_RAG.classifier.hybrid_classifier import HybridQueryClassifier
from Adaptive_RAG.decomposition.legal_decomposer import LegalQueryDecomposer
from Adaptive_RAG.orchestration.orchestrator import AdaptiveOrchestrator
from Adaptive_RAG.orchestration.schema import AdaptiveRAGResponse

logger = logging.getLogger("Adaptive_RAG.pipeline.adaptive_pipeline")


class AdaptiveRAGPipeline:
    """
    Đường ống cấp cao của hệ thống Adaptive Agentic RAG:
    - Tiếp nhận câu hỏi pháp lý từ người dùng.
    - Điều phối thích ứng động (Dynamic Adaptive Routing) qua AdaptiveOrchestrator.
    - Tối ưu hóa phản hồi, quản lý ngữ cảnh và bảo tồn truy vết trích dẫn pháp lý.
    """

    def __init__(
        self,
        config: Optional[AdaptiveRAGConfig] = None,
        pipeline_config: Optional[PipelineConfig] = None,
        crag_config: Optional[CRAGConfig] = None,
        classifier: Optional[HybridQueryClassifier] = None,
        decomposer: Optional[LegalQueryDecomposer] = None,
        retriever: Optional[DenseTopKRetriever] = None,
        generator: Optional[BaseLegalGenerator] = None,
        citation_resolver: Optional[CitationResolver] = None,
    ):
        self.config = config or adaptive_config
        self.orchestrator = AdaptiveOrchestrator(
            config=self.config,
            pipeline_config=pipeline_config,
            crag_config=crag_config,
            classifier=classifier,
            decomposer=decomposer,
            retriever=retriever,
            generator=generator,
            citation_resolver=citation_resolver,
        )

    def answer(self, question: str) -> AdaptiveRAGResponse:
        """
        Thực thi xử lý câu hỏi người dùng qua hệ thống Adaptive Agentic RAG.
        
        Args:
            question: Câu hỏi pháp lý của người dùng.
            
        Returns:
            AdaptiveRAGResponse chứa câu trả lời, trích dẫn, route đã chọn và telemetry chi tiết.
        """
        return self.orchestrator.route_and_execute(question)
