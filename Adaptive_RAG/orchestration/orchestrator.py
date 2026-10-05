"""
Adaptive RAG Orchestrator.
Bộ điều phối thích ứng đa luồng (Adaptive Multi-Routing Orchestrator).
"""

from __future__ import annotations
import time
import logging
from typing import Optional, Dict, Any, List

from RAG.pipeline.traditional_rag import TraditionalRAGPipeline
from RAG.retriever.dense_retriever import DenseTopKRetriever
from RAG.generator.factory import get_generator
from RAG.generator.base import BaseLegalGenerator
from RAG.citation.resolver import CitationResolver
from CRAG.pipeline.crag_pipeline import CRAGPipeline

from Adaptive_RAG.config import AdaptiveRAGConfig, adaptive_config
from Adaptive_RAG.classifier.schema import (
    ClassificationResult,
    QueryIntent,
    RoutingDecision,
)
from Adaptive_RAG.classifier.hybrid_classifier import HybridQueryClassifier
from Adaptive_RAG.decomposition.schema import DecompositionPlan
from Adaptive_RAG.decomposition.legal_decomposer import LegalQueryDecomposer
from Adaptive_RAG.orchestration.schema import (
    AdaptiveRAGResponse,
    OrchestrationTrace,
    SubQueryExecutionRecord,
)
from Adaptive_RAG.orchestration.synthesizer import MultiHopSynthesizer

logger = logging.getLogger("Adaptive_RAG.orchestration.orchestrator")


class AdaptiveOrchestrator:
    """
    Bộ điều phối thích ứng thông minh (Adaptive Agentic Brain):
    1. Tiếp nhận câu hỏi và phân loại độ phức tạp tức thì qua HybridQueryClassifier.
    2. Định tuyến theo 5 nhánh chuyên biệt:
       - DIRECT_ANSWER: Phản hồi chào hỏi/xã giao (0 ms retrieval).
       - DIRECT_REFUSAL: Từ chối dứt khoát câu hỏi ngoài phạm vi (0 ms retrieval/generation).
       - TRADITIONAL_RAG: Chuyển tiếp tới Baseline cho câu hỏi đơn giản 1 điều luật.
       - CORRECTIVE_RAG: Chuyển tiếp tới CRAG cho câu hỏi thủ tục, loại bỏ nhiễu nội bộ.
       - DECOMPOSE_AGENTIC: Phân rã câu hỏi đa chặng $\to$ Tra cứu song song $\to$ Tổng hợp.
    3. Ghi lại đầy đủ dấu vết điều phối (Orchestration Trace) phục vụ giải trình học thuật.
    """

    def __init__(
        self,
        config: Optional[AdaptiveRAGConfig] = None,
        pipeline_config: Optional[PipelineConfig] = None,
        crag_config: Optional[CRAGConfig] = None,
        classifier: Optional[HybridQueryClassifier] = None,
        decomposer: Optional[LegalQueryDecomposer] = None,
        traditional_pipeline: Optional[TraditionalRAGPipeline] = None,
        crag_pipeline: Optional[CRAGPipeline] = None,
        retriever: Optional[DenseTopKRetriever] = None,
        generator: Optional[BaseLegalGenerator] = None,
        citation_resolver: Optional[CitationResolver] = None,
    ):
        self.config = config or adaptive_config
        self.pipeline_config = pipeline_config
        self.crag_config = crag_config
        self.classifier = classifier or HybridQueryClassifier(config=self.config)
        self.decomposer = decomposer or LegalQueryDecomposer(config=self.config)

        # Pipelines hạ tầng
        if traditional_pipeline is not None:
            self.traditional_pipeline = traditional_pipeline
        else:
            self.traditional_pipeline = TraditionalRAGPipeline(
                config=self.pipeline_config,
                retriever=retriever,
                generator=generator,
                citation_resolver=citation_resolver,
            )

        if crag_pipeline is not None:
            self.crag_pipeline = crag_pipeline
        else:
            self.crag_pipeline = CRAGPipeline(
                pipeline_config=self.pipeline_config,
                crag_cfg=self.crag_config,
                retriever=retriever or self.traditional_pipeline.retriever,
                generator=generator or self.traditional_pipeline.generator,
                citation_resolver=citation_resolver or self.traditional_pipeline.citation_resolver,
            )

        self.retriever = retriever or self.traditional_pipeline.retriever
        self.generator = generator or self.traditional_pipeline.generator
        self.citation_resolver = (
            citation_resolver or self.traditional_pipeline.citation_resolver
        )

        # Bộ tổng hợp đa chặng
        self.synthesizer = MultiHopSynthesizer(
            generator=self.generator,
            citation_resolver=self.citation_resolver,
        )

    def route_and_execute(self, query: str) -> AdaptiveRAGResponse:
        """
        Thực hiện toàn bộ quy trình: Phân loại ý định $\to$ Định tuyến $\to$ Thực thi $\to$ Phản hồi.
        """
        t_start = time.perf_counter()
        if not query or not query.strip():
            raise ValueError("Câu hỏi người dùng không được rỗng hoặc chỉ chứa khoảng trắng.")

        clean_query = query.strip()

        # BƯỚC 1: Phân loại độ phức tạp & ý định câu hỏi (Tốc độ < 1ms)
        t_route_0 = time.perf_counter()
        classification = self.classifier.classify(clean_query)
        route = classification.suggested_route
        t_routing_ms = (time.perf_counter() - t_route_0) * 1000.0

        trace = OrchestrationTrace(
            query=clean_query,
            classification=classification,
            route_chosen=route,
            routing_latency_ms=round(t_routing_ms, 2),
        )

        # BƯỚC 2: Điều phối theo nhánh tối ưu
        # 2.1. Nhánh DIRECT_ANSWER (Chào hỏi / Thông tin hệ thống)
        if route == RoutingDecision.DIRECT_ANSWER:
            t_total_ms = (time.perf_counter() - t_start) * 1000.0
            trace.total_latency_ms = round(t_total_ms, 2)
            answer_text = (
                "Xin chào! Tôi là trợ lý ảo hỗ trợ tra cứu pháp luật lao động Việt Nam. "
                "Bạn có thể đặt các câu hỏi về hợp đồng lao động, thời gian thử việc, "
                "tiền lương, thời giờ làm việc, kỷ luật lao động và các chế độ liên quan."
            )
            return AdaptiveRAGResponse(
                question=clean_query,
                answer=answer_text,
                citations=[],
                retrieved_chunks=[],
                route_taken=route,
                classification=classification,
                trace=trace,
                latency_ms=round(t_total_ms, 2),
                refused=False,
            )

        # 2.2. Nhánh DIRECT_REFUSAL (Ngoài phạm vi pháp luật lao động)
        if route == RoutingDecision.DIRECT_REFUSAL:
            t_total_ms = (time.perf_counter() - t_start) * 1000.0
            trace.total_latency_ms = round(t_total_ms, 2)
            refusal_text = (
                "Xin lỗi, câu hỏi của bạn nằm ngoài phạm vi chuyên môn về pháp luật lao động Việt Nam. "
                "Hệ thống chỉ hỗ trợ tra cứu các quy định trong Bộ luật Lao động và các văn bản hướng dẫn thi hành liên quan."
            )
            return AdaptiveRAGResponse(
                question=clean_query,
                answer=refusal_text,
                citations=[],
                retrieved_chunks=[],
                route_taken=route,
                classification=classification,
                trace=trace,
                latency_ms=round(t_total_ms, 2),
                refused=True,
                refusal_reason=classification.reasoning,
            )

        # 2.3. Nhánh TRADITIONAL_RAG (Câu hỏi đơn giản 1 điều luật)
        if route == RoutingDecision.TRADITIONAL_RAG:
            t_exec_0 = time.perf_counter()
            trad_res = self.traditional_pipeline.answer(clean_query)
            t_exec_ms = (time.perf_counter() - t_exec_0) * 1000.0
            t_total_ms = (time.perf_counter() - t_start) * 1000.0

            trace.execution_latency_ms = round(t_exec_ms, 2)
            trace.total_latency_ms = round(t_total_ms, 2)

            return AdaptiveRAGResponse(
                question=clean_query,
                answer=trad_res.answer,
                citations=trad_res.citations,
                retrieved_chunks=trad_res.retrieved_chunks,
                route_taken=route,
                classification=classification,
                trace=trace,
                latency_ms=round(t_total_ms, 2),
                refused=trad_res.refused,
                refusal_reason=trad_res.refusal_reason,
            )

        # 2.4. Nhánh CORRECTIVE_RAG (Câu hỏi thủ tục, cần lọc nhiễu dải tri thức)
        if route == RoutingDecision.CORRECTIVE_RAG:
            t_exec_0 = time.perf_counter()
            crag_res = self.crag_pipeline.answer(clean_query)
            t_exec_ms = (time.perf_counter() - t_exec_0) * 1000.0
            t_total_ms = (time.perf_counter() - t_start) * 1000.0

            trace.execution_latency_ms = round(t_exec_ms, 2)
            trace.total_latency_ms = round(t_total_ms, 2)

            return AdaptiveRAGResponse(
                question=clean_query,
                answer=crag_res.answer,
                citations=crag_res.citations,
                retrieved_chunks=crag_res.retrieved_chunks,
                route_taken=route,
                classification=classification,
                trace=trace,
                latency_ms=round(t_total_ms, 2),
                refused=crag_res.refused,
                refusal_reason=crag_res.refusal_reason,
            )

        # 2.5. Nhánh DECOMPOSE_AGENTIC (Câu hỏi đa chặng, đa văn bản, đa điều kiện)
        if route == RoutingDecision.DECOMPOSE_AGENTIC:
            t_exec_0 = time.perf_counter()
            plan: DecompositionPlan = self.decomposer.decompose(clean_query)
            trace.plan = plan

            sub_records: List[SubQueryExecutionRecord] = []
            for sub_q in plan.sub_queries:
                t_sub_0 = time.perf_counter()
                chunks = self.retriever.retrieve(query=sub_q.text, top_k=3)
                sub_elapsed = (time.perf_counter() - t_sub_0) * 1000.0

                sub_records.append(
                    SubQueryExecutionRecord(
                        sub_query=sub_q,
                        retrieved_chunks=chunks,
                        action_taken="DENSE_RETRIEVAL",
                        latency_ms=round(sub_elapsed, 2),
                    )
                )

            t_exec_ms = (time.perf_counter() - t_exec_0) * 1000.0
            trace.sub_executions = sub_records
            trace.execution_latency_ms = round(t_exec_ms, 2)

            # BƯỚC 3: Tổng hợp đa chặng (Multi-Hop Synthesis)
            t_syn_0 = time.perf_counter()
            syn_answer, valid_citations, all_chunks, syn_latency_ms = (
                self.synthesizer.synthesize(
                    original_query=clean_query,
                    plan=plan,
                    sub_records=sub_records,
                )
            )
            trace.synthesis_latency_ms = round(syn_latency_ms, 2)
            t_total_ms = (time.perf_counter() - t_start) * 1000.0
            trace.total_latency_ms = round(t_total_ms, 2)

            return AdaptiveRAGResponse(
                question=clean_query,
                answer=syn_answer,
                citations=valid_citations,
                retrieved_chunks=all_chunks,
                route_taken=route,
                classification=classification,
                trace=trace,
                latency_ms=round(t_total_ms, 2),
                refused=False,
            )

        # Fallback an toàn về CRAG
        crag_fallback = self.crag_pipeline.answer(clean_query)
        t_total_ms = (time.perf_counter() - t_start) * 1000.0
        return AdaptiveRAGResponse(
            question=clean_query,
            answer=crag_fallback.answer,
            citations=crag_fallback.citations,
            retrieved_chunks=crag_fallback.retrieved_chunks,
            route_taken=RoutingDecision.CORRECTIVE_RAG,
            classification=classification,
            trace=trace,
            latency_ms=round(t_total_ms, 2),
            refused=crag_fallback.refused,
            refusal_reason=crag_fallback.refusal_reason,
        )
