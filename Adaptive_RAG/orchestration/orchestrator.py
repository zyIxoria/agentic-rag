"""
Adaptive RAG Orchestrator.
Bộ điều phối thích ứng đa luồng (Adaptive Multi-Routing Orchestrator)
kết hợp Tác tử Trung tâm (Central ReAct Agent), Cơ chế phản hồi 2 chiều (Dynamic Feedback Loop)
và Đánh giá độ tin cậy sau truy xuất (Post-Retrieval Confidence Evaluation).
"""

from __future__ import annotations
import time
import logging
from typing import Optional, Dict, Any, List

from RAG.pipeline.traditional_rag import TraditionalRAGPipeline
from RAG.pipeline.config import PipelineConfig
from RAG.retriever.dense_retriever import DenseTopKRetriever
from RAG.retriever.schema import RetrievedChunk
from RAG.generator.factory import get_generator
from RAG.generator.base import BaseLegalGenerator
from RAG.citation.resolver import CitationResolver
from CRAG.pipeline.crag_pipeline import CRAGPipeline
from CRAG.config import CRAGConfig
from CRAG.search.web_searcher import LegalWebSearcher

from Adaptive_RAG.config import AdaptiveRAGConfig, adaptive_config
from Adaptive_RAG.classifier.schema import (
    ClassificationResult,
    ComplexityLevel,
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
from Adaptive_RAG.orchestration.feedback_evaluator import (
    PostRetrievalConfidenceEvaluator,
    ConfidenceLevel,
    EscalationTarget,
    PostRetrievalEvaluation,
)
from Adaptive_RAG.agent.central_agent import CentralAgentController, AgentResponse
from Adaptive_RAG.agent.tool_registry import LegalToolRegistry
from RAG.guards.scope_guard import SharedScopeGuard
from RAG.guards.document_grounding_gate import NamedLegalDocumentResolver
from RAG.guards.evidence_gate import PreGenerationEvidenceGate
from RAG.guards.qa_alignment_guard import PostGenerationQAAlignmentGuard

logger = logging.getLogger("Adaptive_RAG.orchestration.orchestrator")


class AdaptiveOrchestrator:
    """
    Bộ điều phối thích ứng thông minh (Adaptive Agentic Brain):
    1. Tiếp nhận câu hỏi và phân loại độ phức tạp tức thì qua HybridQueryClassifier.
    2. Điều phối theo 5 nhánh chuyên biệt:
       - DIRECT_ANSWER: Phản hồi chào hỏi/xã giao (0 ms retrieval).
       - DIRECT_REFUSAL: Từ chối dứt khoát câu hỏi ngoài phạm vi (0 ms retrieval/generation).
       - TRADITIONAL_RAG: Baseline 1 điều luật, kiểm định chất lượng sau truy xuất (Post-Retrieval Gate).
       - CORRECTIVE_RAG: CRAG cho câu hỏi thủ tục, loại bỏ nhiễu nội bộ, web search fallback.
       - DECOMPOSE_AGENTIC: Phân rã câu hỏi đa chặng $\to$ Tra cứu có kiểm định chất lượng $\to$ Tổng hợp.
    3. Cơ chế phản hồi 2 chiều (Dynamic Feedback Loop):
       - Tự động nâng cấp (Escalate) từ TRADITIONAL_RAG sang CRAG/DECOMPOSE nếu retrieval bị lạc đề hoặc rỗng.
       - Tự động kích hoạt Web Search Fallback cho các sub-queries bị thiếu văn bản trong DECOMPOSE_AGENTIC.
    4. Tích hợp Central ReAct Agent & Symbolic Calculator cho câu hỏi định lượng tính toán số học.
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

        # Đánh giá phản hồi 2 chiều sau truy xuất (Dynamic Feedback Loop)
        self.post_evaluator = PostRetrievalConfidenceEvaluator(crag_cfg=self.crag_config)

        # Tác tử trung tâm & Công cụ tìm kiếm
        search_prov = self.crag_config.SEARCH_PROVIDER if self.crag_config else None
        self.web_searcher = LegalWebSearcher(provider=search_prov)
        self.tool_registry = LegalToolRegistry(
            retriever=self.retriever,
            web_searcher=self.web_searcher,
        )
        self.agent_controller = CentralAgentController(
            tool_registry=self.tool_registry,
            generator=self.generator,
        )

        # Các chốt chặn đa tầng (Multi-tier Safety Guards)
        self.scope_guard = SharedScopeGuard()
        self.document_resolver = NamedLegalDocumentResolver()
        self.evidence_gate = PreGenerationEvidenceGate()
        self.qa_alignment_guard = PostGenerationQAAlignmentGuard()

    def answer(
        self,
        query: str,
        chat_history: Optional[Any] = None,
    ) -> AdaptiveRAGResponse:
        """Phương thức chuẩn hóa giao diện tương thích với TraditionalRAG và CRAG."""
        return self.route_and_execute(query, chat_history=chat_history)

    def route_and_execute(
        self,
        query: str,
        chat_history: Optional[Any] = None,
    ) -> AdaptiveRAGResponse:
        """
        Thực hiện toàn bộ quy trình: Phân loại ý định $\to$ Định tuyến $\to$ Kiểm định 2 chiều $\to$ Thực thi $\to$ Phản hồi.
        Hỗ trợ nhận thức ngữ cảnh hội thoại đa lượt qua chat_history.
        """
        t_start = time.perf_counter()
        if not query or not query.strip():
            raise ValueError("Câu hỏi người dùng không được rỗng hoặc chỉ chứa khoảng trắng.")

        clean_query = query.strip()

        # CHỐT CHẶN TIER 1: Scope & Intent Boundary Gate (Shared Scope Guard)
        if getattr(self.config, "ENABLE_TIER1_SHARED_SCOPE_GATE", True):
            scope_res = self.scope_guard.check_scope(clean_query)
            if scope_res.trigger_refusal:
                t_total_ms = (time.perf_counter() - t_start) * 1000.0
                tier1_classification = ClassificationResult(
                    query=clean_query,
                    intent=QueryIntent.OUT_OF_SCOPE,
                    complexity=ComplexityLevel.DIRECT,
                    suggested_route=RoutingDecision.DIRECT_REFUSAL,
                    confidence=1.0,
                    reasoning=f"Tier 1 Scope Guard: {scope_res.refusal_reason}",
                )
                trace = OrchestrationTrace(
                    query=clean_query,
                    classification=tier1_classification,
                    route_chosen=RoutingDecision.DIRECT_REFUSAL,
                    original_route=RoutingDecision.DIRECT_REFUSAL,
                    total_latency_ms=round(t_total_ms, 2),
                )
                return AdaptiveRAGResponse(
                    question=clean_query,
                    answer=scope_res.refusal_message or "Câu hỏi thuộc lĩnh vực ngoài phạm vi pháp luật lao động.",
                    citations=[],
                    retrieved_chunks=[],
                    route_taken=RoutingDecision.DIRECT_REFUSAL,
                    classification=tier1_classification,
                    trace=trace,
                    latency_ms=round(t_total_ms, 2),
                    refused=True,
                    refusal_reason=scope_res.refusal_reason,
                )

        # CHỐT CHẶN TIER 2: Document Coverage & Grounding Gate
        if getattr(self.config, "ENABLE_TIER2_DOCUMENT_GROUNDING_GATE", True):
            doc_res = self.document_resolver.resolve(clean_query)
            if doc_res.trigger_refusal:
                t_total_ms = (time.perf_counter() - t_start) * 1000.0
                tier2_classification = ClassificationResult(
                    query=clean_query,
                    intent=QueryIntent.OUT_OF_SCOPE if not doc_res.is_supported else QueryIntent.LEGAL_INSUFFICIENT,
                    complexity=ComplexityLevel.DIRECT,
                    suggested_route=RoutingDecision.DIRECT_REFUSAL,
                    confidence=1.0,
                    reasoning=f"Tier 2 Document Grounding Gate: {doc_res.refusal_reason}",
                )
                trace = OrchestrationTrace(
                    query=clean_query,
                    classification=tier2_classification,
                    route_chosen=RoutingDecision.DIRECT_REFUSAL,
                    original_route=RoutingDecision.DIRECT_REFUSAL,
                    total_latency_ms=round(t_total_ms, 2),
                )
                return AdaptiveRAGResponse(
                    question=clean_query,
                    answer=doc_res.refusal_message or "Hiện tại hệ thống chưa hỗ trợ tra cứu văn bản này.",
                    citations=[],
                    retrieved_chunks=[],
                    route_taken=RoutingDecision.DIRECT_REFUSAL,
                    classification=tier2_classification,
                    trace=trace,
                    latency_ms=round(t_total_ms, 2),
                    refused=True,
                    refusal_reason=doc_res.refusal_reason,
                )

        # BƯỚC 1: Phân loại độ phức tạp & ý định câu hỏi (có ngữ cảnh hội thoại)
        t_route_0 = time.perf_counter()
        classification = self.classifier.classify(clean_query, chat_history=chat_history)
        route = classification.suggested_route
        t_routing_ms = (time.perf_counter() - t_route_0) * 1000.0

        trace = OrchestrationTrace(
            query=clean_query,
            classification=classification,
            route_chosen=route,
            original_route=route,
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

        # 2.3. KIỂM TRA ĐẶC BIỆT: Câu hỏi định lượng tính toán số học
        # Chuyển quyền xử lý cho Central Autonomous Agent (Symbolic Legal Calculator)
        q_lower = clean_query.lower()
        is_calc_required = any(
            kw in q_lower
            for kw in [
                "làm thêm", "tăng ca", "thêm giờ", "bồi thường tai nạn",
                "trợ cấp thôi việc", "trợ cấp mất việc", "thôi việc được bao nhiêu",
                "thất nghiệp được bao nhiêu", "trợ cấp thất nghiệp",
            ]
        ) and any(kw in q_lower for kw in ["bao nhiêu", "tính", "được nhận", "hưởng", "lương", "đồng", "triệu"])

        if is_calc_required and route not in [RoutingDecision.DIRECT_ANSWER, RoutingDecision.DIRECT_REFUSAL]:
            logger.info("Phát hiện câu hỏi định lượng tính toán số học. Chuyển quyền điều phối cho Central Agent!")
            t_agent_0 = time.perf_counter()
            agent_res: AgentResponse = self.agent_controller.run(clean_query)
            t_exec_ms = (time.perf_counter() - t_agent_0) * 1000.0
            t_total_ms = (time.perf_counter() - t_start) * 1000.0

            trace.agent_steps = [s.__dict__ if hasattr(s, "__dict__") else s for s in agent_res.steps]
            trace.execution_latency_ms = round(t_exec_ms, 2)
            trace.total_latency_ms = round(t_total_ms, 2)

            return AdaptiveRAGResponse(
                question=clean_query,
                answer=agent_res.answer,
                citations=agent_res.citations,
                retrieved_chunks=[],
                route_taken=RoutingDecision.DECOMPOSE_AGENTIC,
                classification=classification,
                trace=trace,
                latency_ms=round(t_total_ms, 2),
                refused=False,
            )

        # 2.4. Nhánh TRADITIONAL_RAG (kết hợp Post-Retrieval Confidence Gate & Escalation)
        if route == RoutingDecision.TRADITIONAL_RAG:
            t_exec_0 = time.perf_counter()
            
            # Thực hiện truy xuất thử nghiệm
            top_k = self.pipeline_config.TOP_K if self.pipeline_config else 3
            initial_chunks = self.retriever.retrieve(clean_query, top_k=top_k)

            # Đánh giá phản hồi 2 chiều sau truy xuất
            post_eval: PostRetrievalEvaluation = self.post_evaluator.evaluate(
                query=clean_query,
                chunks=initial_chunks,
                is_multi_hop_query=len(classification.detected_conditions) > 0,
            )

            # KIỂM ĐỊNH NÂNG CẤP (DYNAMIC ESCALATION):
            if post_eval.recommended_action == EscalationTarget.ESCALATE_TO_CRAG:
                logger.warning(
                    f"Dynamic Feedback Loop: Đánh giá confidence {post_eval.confidence_level.value}. "
                    f"Tự động ESCALATE từ TRADITIONAL_RAG sang CORRECTIVE_RAG! (Lý do: {post_eval.reason})"
                )
                trace.escalated = True
                trace.escalation_reason = post_eval.reason
                route = RoutingDecision.CORRECTIVE_RAG
                trace.route_chosen = route

            elif post_eval.recommended_action == EscalationTarget.ESCALATE_TO_DECOMPOSE:
                logger.warning(
                    f"Dynamic Feedback Loop: Đánh giá confidence {post_eval.confidence_level.value}. "
                    f"Tự động ESCALATE từ TRADITIONAL_RAG sang DECOMPOSE_AGENTIC! (Lý do: {post_eval.reason})"
                )
                trace.escalated = True
                trace.escalation_reason = post_eval.reason
                route = RoutingDecision.DECOMPOSE_AGENTIC
                trace.route_chosen = route

            else:
                # Độ tin cậy CAO -> Thực thi hoàn tất qua Traditional Pipeline
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
                    escalated=False,
                )

        # 2.5. Nhánh CORRECTIVE_RAG (Được định tuyến trực tiếp hoặc do ESCALATE chuyển sang)
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
                escalated=trace.escalated,
                escalation_reason=trace.escalation_reason,
            )

        # 2.6. Nhánh DECOMPOSE_AGENTIC (Được định tuyến trực tiếp hoặc do ESCALATE chuyển sang)
        if route == RoutingDecision.DECOMPOSE_AGENTIC:
            t_exec_0 = time.perf_counter()
            plan: DecompositionPlan = self.decomposer.decompose(clean_query)
            trace.plan = plan

            sub_records: List[SubQueryExecutionRecord] = []
            for sub_q in plan.sub_queries:
                t_sub_0 = time.perf_counter()
                chunks = self.retriever.retrieve(query=sub_q.text, top_k=3)
                action_taken = "DENSE_RETRIEVAL"

                # Sub-chunk quality validation & dynamic recovery
                sub_eval: PostRetrievalEvaluation = self.post_evaluator.evaluate_subquery(sub_q.text, chunks)
                if sub_eval.recommended_action == EscalationTarget.WEB_SEARCH_SUBQUERY:
                    logger.info(f"Sub-query '{sub_q.text}' có confidence thấp ({sub_eval.confidence_level.value}). Kích hoạt Web Search Fallback!")
                    web_resp = self.web_searcher.search(query=sub_q.text, top_k=2)
                    action_taken = "DENSE_RETRIEVAL_ESCALATED_WEB_SEARCH"
                    for idx, w_res in enumerate(web_resp.results, start=1):
                        chunks.append(
                            RetrievedChunk(
                                chunk_id=f"WEB_FALLBACK_SUB_{sub_q.id}_{idx}",
                                content=f"[{w_res.source_name}] {w_res.title}: {w_res.snippet}",
                                score=w_res.score,
                                rank=len(chunks) + 1,
                                metadata={
                                    "document_name": w_res.source_name,
                                    "title": w_res.title,
                                    "source": w_res.url,
                                    "article": "Trích lục Web Search",
                                },
                            )
                        )

                sub_elapsed = (time.perf_counter() - t_sub_0) * 1000.0
                sub_records.append(
                    SubQueryExecutionRecord(
                        sub_query=sub_q,
                        retrieved_chunks=chunks,
                        action_taken=action_taken,
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

            # CHỐT CHẶN TIER 3: Pre-Generation Evidence Gate trên tập bằng chứng tổng hợp
            if getattr(self.config, "ENABLE_TIER3_PRE_GEN_EVIDENCE_GATE", True):
                evidence_res = self.evidence_gate.evaluate(clean_query, all_chunks)
                if evidence_res.trigger_refusal:
                    return AdaptiveRAGResponse(
                        question=clean_query,
                        answer=evidence_res.refusal_message or "Căn cứ cơ sở dữ liệu hiện hành, hệ thống không tìm thấy đủ chứng cứ pháp lý để khẳng định câu trả lời.",
                        citations=[],
                        retrieved_chunks=all_chunks,
                        route_taken=route,
                        classification=classification,
                        trace=trace,
                        latency_ms=round(t_total_ms, 2),
                        refused=True,
                        refusal_reason=evidence_res.refusal_reason,
                        escalated=trace.escalated,
                        escalation_reason=trace.escalation_reason,
                    )

            # CHỐT CHẶN TIER 4: Post-Generation QA Alignment Guard
            final_syn_answer = syn_answer
            final_syn_refused = False
            final_syn_reason = None
            if getattr(self.config, "ENABLE_TIER4_QA_ALIGNMENT_GUARD", True):
                qa_res = self.qa_alignment_guard.evaluate_answer(clean_query, syn_answer, all_chunks)
                if qa_res.trigger_refusal:
                    final_syn_answer = "Căn cứ cơ sở dữ liệu hiện hành, hệ thống không tìm thấy đủ chứng cứ pháp lý để khẳng định câu trả lời."
                    final_syn_refused = True
                    final_syn_reason = qa_res.refusal_reason
                    valid_citations = []
                elif qa_res.pruned_answer:
                    final_syn_answer = qa_res.pruned_answer

            return AdaptiveRAGResponse(
                question=clean_query,
                answer=final_syn_answer,
                citations=valid_citations,
                retrieved_chunks=all_chunks,
                route_taken=route,
                classification=classification,
                trace=trace,
                latency_ms=round(t_total_ms, 2),
                refused=final_syn_refused,
                refusal_reason=final_syn_reason,
                escalated=trace.escalated,
                escalation_reason=trace.escalation_reason,
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
            escalated=trace.escalated,
            escalation_reason=trace.escalation_reason,
        )
