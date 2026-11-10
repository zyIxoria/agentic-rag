"""traditional_rag.py - Triển khai tích hợp toàn diện Traditional RAG Pipeline (TASK RAG-07).

Hiện thực hóa quy trình hỏi đáp pháp luật tuyến tính, tất định, không có logic thích ứng ẩn:
Question -> Dense Retrieval -> Pre-Guard -> Context Builder -> LLM Generator -> Citation Resolver -> Post-Guard -> RAGResponse.
"""

from __future__ import annotations
import time
import logging
from typing import Optional, Dict, Any, List

from RAG.pipeline.config import PipelineConfig, default_pipeline_config
from RAG.schemas.pipeline_schema import RAGResponse
from RAG.retriever.dense_retriever import DenseTopKRetriever
from RAG.context.builder import LegalContextBuilder
from RAG.context.config import ContextConfig
from RAG.generator.base import BaseLegalGenerator
from RAG.generator.factory import get_generator
from RAG.citation.resolver import CitationResolver
from RAG.guards.refusal_guard import RefusalGuard
from RAG.guards.config import GuardConfig
from RAG.guards.scope_guard import SharedScopeGuard
from RAG.guards.document_grounding_gate import NamedLegalDocumentResolver
from RAG.guards.evidence_gate import PreGenerationEvidenceGate
from RAG.guards.qa_alignment_guard import PostGenerationQAAlignmentGuard

logger = logging.getLogger("RAG.pipeline.traditional_rag")


class TraditionalRAGPipeline:
    """Đường ống hỏi đáp pháp luật truyền thống (Traditional RAG Baseline).
    
    Quy tắc thiết kế nghiêm ngặt (No Hidden Intelligence):
    - 01 truy vấn -> 01 query embedding -> 01 dense retrieval -> 01 context build -> tối đa 01 LLM generation.
    - Không viết lại câu hỏi (No query rewriting).
    - Không phân rã câu hỏi (No query decomposition).
    - Không tự động thay đổi K (No dynamic K).
    - Không gọi bộ tái xếp hạng (No reranker).
    - Không gọi subagent bổ sung hoặc vòng lặp retry logic.
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        retriever: Optional[DenseTopKRetriever] = None,
        context_builder: Optional[LegalContextBuilder] = None,
        generator: Optional[BaseLegalGenerator] = None,
        citation_resolver: Optional[CitationResolver] = None,
        guard: Optional[RefusalGuard] = None,
    ):
        """Khởi tạo pipeline Traditional RAG với các phân hệ độc lập.
        
        Args:
            config: Cấu hình PipelineConfig.
            retriever: Bộ thu hồi DenseTopKRetriever (tự tạo nếu None).
            context_builder: Bộ dựng ngữ cảnh LegalContextBuilder (tự tạo nếu None).
            generator: Bộ sinh BaseLegalGenerator (tự tạo qua factory nếu None).
            citation_resolver: Bộ giải nghĩa trích dẫn CitationResolver (tự tạo nếu None).
            guard: Chốt chặn an toàn RefusalGuard (tự tạo nếu None).
        """
        self.config = config or default_pipeline_config

        # 1. Khởi tạo Retriever (RAG-03)
        if retriever is not None:
            self.retriever = retriever
        else:
            from RAG.retriever.config import RetrieverConfig
            ret_config = RetrieverConfig(
                TOP_K=self.config.TOP_K,
                SIMILARITY_THRESHOLD=self.config.SIMILARITY_THRESHOLD,
                PERSIST_DIRECTORY=self.config.CHROMA_PERSIST_DIRECTORY,
                COLLECTION_NAME=self.config.COLLECTION_NAME
            )
            self.retriever = DenseTopKRetriever(config=ret_config)

        # 2. Khởi tạo Guard (RAG-06)
        if guard is not None:
            self.guard = guard
        else:
            self.guard = RefusalGuard(
                config=GuardConfig(
                    SIMILARITY_THRESHOLD=self.config.SIMILARITY_THRESHOLD,
                    ENABLE_PRE_GENERATION_GUARD=self.config.ENABLE_PRE_GUARD,
                    ENABLE_POST_GENERATION_GUARD=self.config.ENABLE_POST_GUARD
                )
            )

        # 3. Khởi tạo Context Builder (RAG-04)
        if context_builder is not None:
            self.context_builder = context_builder
        else:
            self.context_builder = LegalContextBuilder(
                config=ContextConfig(
                    MAX_CONTEXT_TOKENS=self.config.MAX_CONTEXT_TOKENS
                )
            )

        # 4. Khởi tạo Generator (RAG-05)
        if generator is not None:
            self.generator = generator
        else:
            self.generator = get_generator(
                provider=self.config.LLM_PROVIDER,
                model_name=self.config.LLM_MODEL
            )

        # 5. Khởi tạo Citation Resolver (RAG-06)
        if citation_resolver is not None:
            self.citation_resolver = citation_resolver
        else:
            self.citation_resolver = CitationResolver(
                replace_in_text=self.config.REPLACE_IN_TEXT_CITATIONS,
                append_footnotes=self.config.APPEND_FOOTNOTES,
                reject_invalid=True
            )

        # 6. Khởi tạo các chốt chặn đa tầng (Multi-tier Safety Guards)
        self.scope_guard = SharedScopeGuard()
        self.document_resolver = NamedLegalDocumentResolver()
        self.evidence_gate = PreGenerationEvidenceGate()
        self.qa_alignment_guard = PostGenerationQAAlignmentGuard()

    def answer(self, question: str) -> RAGResponse:
        """Thực thi chuỗi hỏi đáp Traditional RAG hoàn chỉnh cho một câu hỏi.
        
        Args:
            question: Câu hỏi pháp lý của người dùng.
            
        Returns:
            RAGResponse chứa câu trả lời, trích dẫn, các chunk thu hồi và các chỉ số đo lường.
        """
        t_start = time.perf_counter()

        # 0. Tiền kiểm tra: Không chấp nhận câu hỏi rỗng
        if not question or not question.strip():
            raise ValueError("Câu hỏi người dùng không được rỗng hoặc chỉ chứa khoảng trắng.")

        clean_question = question.strip()

        # CHỐT CHẶN TIER 1: Scope & Intent Boundary Gate (Shared Scope Guard)
        if getattr(self.config, "ENABLE_TIER1_SHARED_SCOPE_GATE", True):
            scope_res = self.scope_guard.check_scope(clean_question)
            if scope_res.trigger_refusal:
                t_total_ms = (time.perf_counter() - t_start) * 1000.0
                refusal_ans = scope_res.refusal_message or self.guard.config.REFUSAL_MESSAGE
                self._log_execution(
                    query=clean_question,
                    top_k=self.config.TOP_K,
                    retrieved_chunks=[],
                    retrieval_latency=0.0,
                    context_size=0,
                    generation_latency=0.0,
                    total_latency=t_total_ms,
                    refused=True,
                    citations=[]
                )
                return RAGResponse(
                    question=clean_question,
                    answer=refusal_ans,
                    citations=[],
                    retrieved_chunks=[],
                    latency=round(t_total_ms, 2),
                    refused=True,
                    refusal_reason=scope_res.refusal_reason,
                    retrieval_latency=0.0,
                    context_latency=0.0,
                    generation_latency=0.0,
                    citation_latency=0.0,
                    model_name=getattr(self.generator, "model_name", "unknown"),
                    provider=getattr(self.generator, "provider", "unknown"),
                    metadata={
                        "tier1_scope_triggered": True,
                        "intent": scope_res.intent,
                        "detected_domain": scope_res.detected_domain,
                    }
                )

        # CHỐT CHẶN TIER 2: Document Coverage & Grounding Gate
        doc_filter = None
        if getattr(self.config, "ENABLE_TIER2_DOCUMENT_GROUNDING_GATE", True):
            doc_res = self.document_resolver.resolve(clean_question)
            if doc_res.trigger_refusal:
                t_total_ms = (time.perf_counter() - t_start) * 1000.0
                refusal_ans = doc_res.refusal_message or self.guard.config.REFUSAL_MESSAGE
                self._log_execution(
                    query=clean_question,
                    top_k=self.config.TOP_K,
                    retrieved_chunks=[],
                    retrieval_latency=0.0,
                    context_size=0,
                    generation_latency=0.0,
                    total_latency=t_total_ms,
                    refused=True,
                    citations=[]
                )
                return RAGResponse(
                    question=clean_question,
                    answer=refusal_ans,
                    citations=[],
                    retrieved_chunks=[],
                    latency=round(t_total_ms, 2),
                    refused=True,
                    refusal_reason=doc_res.refusal_reason,
                    retrieval_latency=0.0,
                    context_latency=0.0,
                    generation_latency=0.0,
                    citation_latency=0.0,
                    model_name=getattr(self.generator, "model_name", "unknown"),
                    provider=getattr(self.generator, "provider", "unknown"),
                    metadata={
                        "tier2_grounding_triggered": True,
                        "document_title": doc_res.document_title,
                    }
                )
            elif doc_res.has_specific_document and doc_res.filter_metadata:
                doc_filter = doc_res.filter_metadata

        # BƯỚC 1: Thu hồi véc-tơ (Dense Retrieval - 1 retrieval call duy nhất)
        t_ret_0 = time.perf_counter()
        retrieved_chunks = self.retriever.retrieve(
            query=clean_question,
            top_k=self.config.TOP_K,
            where=doc_filter,
        )
        t_retrieval_ms = (time.perf_counter() - t_ret_0) * 1000.0

        # BƯỚC 2: Chốt chặn Tier 3 Pre-Generation Evidence Gate
        if getattr(self.config, "ENABLE_TIER3_PRE_GEN_EVIDENCE_GATE", True):
            evidence_res = self.evidence_gate.evaluate(clean_question, retrieved_chunks)
            if evidence_res.trigger_refusal:
                t_total_ms = (time.perf_counter() - t_start) * 1000.0
                refusal_ans = evidence_res.refusal_message or self.guard.config.REFUSAL_MESSAGE

                self._log_execution(
                    query=clean_question,
                    top_k=self.config.TOP_K,
                    retrieved_chunks=retrieved_chunks,
                    retrieval_latency=t_retrieval_ms,
                    context_size=0,
                    generation_latency=0.0,
                    total_latency=t_total_ms,
                    refused=True,
                    citations=[]
                )

                return RAGResponse(
                    question=clean_question,
                    answer=refusal_ans,
                    citations=[],
                    retrieved_chunks=retrieved_chunks,
                    latency=round(t_total_ms, 2),
                    refused=True,
                    refusal_reason=evidence_res.refusal_reason,
                    retrieval_latency=round(t_retrieval_ms, 2),
                    context_latency=0.0,
                    generation_latency=0.0,
                    citation_latency=0.0,
                    model_name=getattr(self.generator, "model_name", "unknown"),
                    provider=getattr(self.generator, "provider", "unknown"),
                    metadata={
                        "tier3_evidence_triggered": True,
                        "composite_score": evidence_res.composite_evidence_score,
                        "best_chunk_score": evidence_res.best_chunk_score,
                        "coverage_bonus": evidence_res.coverage_bonus,
                        "conflict_resolution_trace": evidence_res.conflict_resolution_trace,
                        "top_k": self.config.TOP_K,
                        "chunks_count": len(retrieved_chunks),
                    }
                )
        else:
            # Fallback về kiểm tra pre-guard truyền thống
            pre_guard_res = self.guard.check_pre_generation(retrieved_chunks)
            if pre_guard_res.trigger_refusal:
                t_total_ms = (time.perf_counter() - t_start) * 1000.0
                refusal_ans = self.guard.config.REFUSAL_MESSAGE

                self._log_execution(
                    query=clean_question,
                    top_k=self.config.TOP_K,
                    retrieved_chunks=retrieved_chunks,
                    retrieval_latency=t_retrieval_ms,
                    context_size=0,
                    generation_latency=0.0,
                    total_latency=t_total_ms,
                    refused=True,
                    citations=[]
                )

                return RAGResponse(
                    question=clean_question,
                    answer=refusal_ans,
                    citations=[],
                    retrieved_chunks=retrieved_chunks,
                    latency=round(t_total_ms, 2),
                    refused=True,
                    refusal_reason=pre_guard_res.reason,
                    retrieval_latency=round(t_retrieval_ms, 2),
                    context_latency=0.0,
                    generation_latency=0.0,
                    citation_latency=0.0,
                    model_name=getattr(self.generator, "model_name", "unknown"),
                    provider=getattr(self.generator, "provider", "unknown"),
                    metadata={
                        "pre_guard_triggered": True,
                        "pre_guard_reason": pre_guard_res.reason,
                        "top_k": self.config.TOP_K,
                        "chunks_count": len(retrieved_chunks),
                    }
                )

        # BƯỚC 3: Đóng gói ngữ cảnh có cấu trúc (Context Building)
        t_ctx_0 = time.perf_counter()
        ctx_result = self.context_builder.build_context(
            retrieved_chunks=retrieved_chunks,
            max_tokens=self.config.MAX_CONTEXT_TOKENS
        )
        t_context_ms = (time.perf_counter() - t_ctx_0) * 1000.0

        # BƯỚC 4: Sinh câu trả lời bằng LLM (LLM Generation - 1 generation call duy nhất)
        t_gen_0 = time.perf_counter()
        gen_result = self.generator.generate(
            question=clean_question,
            context=ctx_result.context_text,
            temperature=self.config.TEMPERATURE
        )
        t_generation_ms = (time.perf_counter() - t_gen_0) * 1000.0

        # BƯỚC 5: Ánh xạ và chuẩn hóa trích dẫn pháp lý (Citation Resolution)
        t_cit_0 = time.perf_counter()
        citation_result = self.citation_resolver.resolve_citations(
            answer=gen_result.answer,
            citation_mapping=ctx_result.citation_mapping,
            citations_list=gen_result.citations,
            replace_in_text=self.config.REPLACE_IN_TEXT_CITATIONS,
            append_footnotes=self.config.APPEND_FOOTNOTES
        )
        t_citation_ms = (time.perf_counter() - t_cit_0) * 1000.0

        # BƯỚC 6: Chốt chặn an toàn sau khi sinh (Post-Generation Refusal Guard & Tier 4 QA Alignment)
        post_guard_res = self.guard.check_post_generation(gen_result, citation_result, context_text=ctx_result.context_text)

        if post_guard_res.trigger_refusal and not gen_result.refused:
            final_answer = self.guard.config.REFUSAL_MESSAGE
            final_refused = True
            final_reason = post_guard_res.reason
            final_citations = []
        else:
            final_answer = citation_result.enriched_answer
            final_refused = gen_result.refused
            final_reason = gen_result.reason
            final_citations = citation_result.valid_citations

        # TIER 4: Post-Generation QA Alignment Guard (Cắt tỉa nhận định phụ / Từ chối luận điểm sai)
        if getattr(self.config, "ENABLE_TIER4_QA_ALIGNMENT_GUARD", True) and not final_refused:
            qa_res = self.qa_alignment_guard.evaluate_answer(clean_question, final_answer, retrieved_chunks)
            if qa_res.trigger_refusal:
                final_answer = self.guard.config.REFUSAL_MESSAGE
                final_refused = True
                final_reason = qa_res.refusal_reason
                final_citations = []
            elif qa_res.pruned_answer:
                final_answer = qa_res.pruned_answer

        t_total_ms = (time.perf_counter() - t_start) * 1000.0

        # BƯỚC 7: Ghi log có cấu trúc (Structured Logging)
        self._log_execution(
            query=clean_question,
            top_k=self.config.TOP_K,
            retrieved_chunks=retrieved_chunks,
            retrieval_latency=t_retrieval_ms,
            context_size=ctx_result.total_tokens,
            generation_latency=t_generation_ms,
            total_latency=t_total_ms,
            refused=final_refused,
            citations=[c.formatted_citation for c in final_citations]
        )

        return RAGResponse(
            question=clean_question,
            answer=final_answer,
            citations=final_citations,
            retrieved_chunks=retrieved_chunks,
            latency=round(t_total_ms, 2),
            refused=final_refused,
            refusal_reason=final_reason,
            retrieval_latency=round(t_retrieval_ms, 2),
            context_latency=round(t_context_ms, 2),
            generation_latency=round(t_generation_ms, 2),
            citation_latency=round(t_citation_ms, 2),
            model_name=gen_result.model_name,
            provider=gen_result.provider,
            metadata={
                "top_k": self.config.TOP_K,
                "context_tokens": ctx_result.total_tokens,
                "sources_included": ctx_result.num_included,
                "sources_dropped": ctx_result.num_dropped,
                "invalid_citations_rejected": citation_result.invalid_citations,
            }
        )

    def _log_execution(
        self,
        query: str,
        top_k: int,
        retrieved_chunks: List[Any],
        retrieval_latency: float,
        context_size: int,
        generation_latency: float,
        total_latency: float,
        refused: bool,
        citations: List[str]
    ) -> None:
        """Ghi log có cấu trúc phục vụ giám sát và đánh giá hiệu năng."""
        chunk_ids = [c.chunk_id for c in retrieved_chunks]
        scores = [round(c.score, 4) for c in retrieved_chunks]

        logger.info(
            "TraditionalRAG execution completed: "
            "query='%s' | top_k=%d | chunk_ids=%s | scores=%s | "
            "retrieval_latency=%.2fms | context_size=%dtokens | "
            "generation_latency=%.2fms | total_latency=%.2fms | "
            "refused=%s | citations=%s",
            query,
            top_k,
            chunk_ids,
            scores,
            retrieval_latency,
            context_size,
            generation_latency,
            total_latency,
            refused,
            citations
        )
