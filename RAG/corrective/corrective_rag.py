"""corrective_rag.py - Triển khai đường ống Corrective RAG (CRAG) Pipeline hoàn chỉnh.

Quy trình xử lý chuẩn (Pháp lý lao động Việt Nam):
User Question
    ↓
Query Embedding & Dense Retrieval Top-K #1
    ↓
Retrieval Evaluator #1
    ↓
┌───────────────────────┴───────────────────────┐
│                                               │
SUFFICIENT                                 PARTIAL / INSUFFICIENT
│                                               │
│                                               ▼
│                                         Query Rewriter
│                                               │
│                                               ▼
│                                         Query Embedding & Retrieval #2
│                                               │
│                                               ▼
│                                         Retrieval Evaluator #2
│                                               │
└───────────────────────┬───────────────────────┘
                        ↓
            Check Evidence Sufficiency
            ┌───────────┴───────────┐
            │                       │
      Has Evidence            Still Insufficient
            ↓                       ↓
     Context Builder           Explicit Refusal
            ↓                       ↓
      LLM Generator             CRAGResponse
            ↓
     Citation / Guards
            ↓
       CRAGResponse
"""

from __future__ import annotations
import time
import logging
from typing import Optional, Dict, Any, List

from RAG.corrective.config import CRAGConfig, default_crag_config
from RAG.corrective.schemas import EvaluationStatus, RetrievalEvaluation, CRAGResponse
from RAG.corrective.evaluator import RetrievalEvaluator
from RAG.corrective.rewriter import QueryRewriter
from RAG.retriever.dense_retriever import DenseTopKRetriever
from RAG.retriever.schema import RetrievedChunk
from RAG.context.builder import LegalContextBuilder
from RAG.context.config import ContextConfig
from RAG.generator.base import BaseLegalGenerator
from RAG.generator.factory import get_generator
from RAG.citation.resolver import CitationResolver
from RAG.guards.refusal_guard import RefusalGuard
from RAG.guards.config import GuardConfig
from RAG.prompts.legal_prompts import STANDARD_REFUSAL_ANSWER

logger = logging.getLogger("RAG.corrective.pipeline")


class CorrectiveRAGPipeline:
    """Đường ống Corrective RAG (CRAG) độc lập, tự thẩm định và tự sửa chữa kết quả truy xuất."""

    def __init__(
        self,
        config: Optional[CRAGConfig] = None,
        retriever: Optional[DenseTopKRetriever] = None,
        evaluator: Optional[RetrievalEvaluator] = None,
        rewriter: Optional[QueryRewriter] = None,
        context_builder: Optional[LegalContextBuilder] = None,
        generator: Optional[BaseLegalGenerator] = None,
        citation_resolver: Optional[CitationResolver] = None,
        guard: Optional[RefusalGuard] = None,
    ):
        self.config = config or default_crag_config

        # 1. Khởi tạo Retriever (Tái sử dụng mô hình Embedding và Vector Store của baseline)
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

        # 2. Khởi tạo Evaluator & Rewriter (CRAG Modules)
        self.evaluator = evaluator or RetrievalEvaluator(config=self.config)
        self.rewriter = rewriter or QueryRewriter(config=self.config)

        # 3. Khởi tạo Context Builder
        if context_builder is not None:
            self.context_builder = context_builder
        else:
            self.context_builder = LegalContextBuilder(
                config=ContextConfig(
                    MAX_CONTEXT_TOKENS=self.config.MAX_CONTEXT_TOKENS
                )
            )

        # 4. Khởi tạo Generator
        if generator is not None:
            self.generator = generator
        else:
            self.generator = get_generator(
                provider=self.config.LLM_PROVIDER,
                model_name=self.config.LLM_MODEL
            )

        # 5. Khởi tạo Citation Resolver
        if citation_resolver is not None:
            self.citation_resolver = citation_resolver
        else:
            self.citation_resolver = CitationResolver(
                replace_in_text=self.config.REPLACE_IN_TEXT_CITATIONS,
                append_footnotes=self.config.APPEND_FOOTNOTES,
                reject_invalid=True
            )

        # 6. Khởi tạo Refusal Guard
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

    def answer(self, question: str) -> CRAGResponse:
        """Thực thi chu trình Corrective RAG hoàn chỉnh cho một câu hỏi."""
        t_start = time.perf_counter()

        if not question or not question.strip():
            raise ValueError("Câu hỏi người dùng không được rỗng hoặc chỉ chứa khoảng trắng.")

        clean_question = question.strip()

        # =====================================================================
        # BƯỚC 1: Retrieval lần 1 (Dense Semantic Search)
        # =====================================================================
        t_ret_0 = time.perf_counter()
        initial_retrieval = self.retriever.retrieve(
            query=clean_question,
            top_k=self.config.TOP_K
        )
        t_retrieval_ms = (time.perf_counter() - t_ret_0) * 1000.0

        # =====================================================================
        # BƯỚC 2: Thẩm định Retrieval lần 1 (Retrieval Evaluator)
        # =====================================================================
        t_eval_0 = time.perf_counter()
        initial_eval = self.evaluator.evaluate(
            query=clean_question,
            retrieved_documents=initial_retrieval
        )
        t_eval_ms = (time.perf_counter() - t_eval_0) * 1000.0

        corrective_triggered = False
        retry_count = 0
        rewritten_query: Optional[str] = None
        corrective_retrieval: List[RetrievedChunk] = []
        final_eval = initial_eval
        t_rewrite_ms = 0.0

        # =====================================================================
        # BƯỚC 3: Quyết định Corrective Loop (Tối đa 1 lần retry)
        # =====================================================================
        if initial_eval.status == EvaluationStatus.SUFFICIENT:
            # Ngữ cảnh đã đầy đủ căn cứ -> Không kích hoạt corrective
            final_chunks = [c for c in initial_retrieval if c.chunk_id in initial_eval.relevant_chunk_ids]
            if not final_chunks:
                final_chunks = initial_retrieval
        else:
            # Trạng thái là PARTIAL hoặc INSUFFICIENT -> Kích hoạt Corrective Retry (MAX 1)
            corrective_triggered = True
            retry_count = 1

            # 3.1. Viết lại truy vấn (Query Rewriting)
            t_rw_0 = time.perf_counter()
            rewritten_query = self.rewriter.rewrite_query(clean_question, initial_eval)
            t_rewrite_ms = (time.perf_counter() - t_rw_0) * 1000.0

            # 3.2. Thu hồi lần 2 với truy vấn đã được tối ưu hóa
            t_ret2_0 = time.perf_counter()
            corrective_retrieval = self.retriever.retrieve(
                query=rewritten_query,
                top_k=self.config.TOP_K
            )
            t_retrieval_ms += (time.perf_counter() - t_ret2_0) * 1000.0

            # 3.3. Thẩm định kết quả thu hồi lần 2
            t_eval2_0 = time.perf_counter()
            final_eval = self.evaluator.evaluate(
                query=rewritten_query,
                retrieved_documents=corrective_retrieval
            )
            t_eval_ms += (time.perf_counter() - t_eval2_0) * 1000.0

            # 3.4. Lựa chọn tập ngữ cảnh cuối cùng
            if final_eval.status == EvaluationStatus.SUFFICIENT:
                final_chunks = [c for c in corrective_retrieval if c.chunk_id in final_eval.relevant_chunk_ids]
                if not final_chunks:
                    final_chunks = corrective_retrieval
            elif final_eval.status == EvaluationStatus.PARTIAL:
                # Kết hợp các chunk hữu ích từ cả 2 lần thu hồi (loại trừ trùng lặp)
                seen_ids = set()
                combined_chunks: List[RetrievedChunk] = []
                for c in corrective_retrieval + initial_retrieval:
                    if c.chunk_id in final_eval.relevant_chunk_ids or c.chunk_id in initial_eval.relevant_chunk_ids:
                        if c.chunk_id not in seen_ids:
                            seen_ids.add(c.chunk_id)
                            combined_chunks.append(c)
                final_chunks = combined_chunks if combined_chunks else corrective_retrieval
            else:
                # final_eval.status == INSUFFICIENT
                # Nếu lần 1 có chunk phù hợp một phần, giữ lại chunk đó; ngược lại từ chối
                if initial_eval.status == EvaluationStatus.PARTIAL and initial_eval.relevant_chunk_ids:
                    final_chunks = [c for c in initial_retrieval if c.chunk_id in initial_eval.relevant_chunk_ids]
                else:
                    final_chunks = []

        # =====================================================================
        # BƯỚC 4: Kiểm tra thiếu căn cứ (Explicit Refusal)
        # =====================================================================
        if not final_chunks or (initial_eval.status == EvaluationStatus.INSUFFICIENT and final_eval.status == EvaluationStatus.INSUFFICIENT):
            t_total_ms = (time.perf_counter() - t_start) * 1000.0
            refusal_reason = (
                f"Không tìm thấy đủ căn cứ pháp lý trong cơ sở dữ liệu sau khi đánh giá và hiệu chỉnh truy vấn. "
                f"(Lần 1: {initial_eval.status.value}, Lần 2: {final_eval.status.value})"
            )

            self._log_crag_execution(
                question=clean_question,
                corrective_triggered=corrective_triggered,
                rewritten_query=rewritten_query,
                initial_eval=initial_eval,
                final_eval=final_eval,
                retry_count=retry_count,
                refused=True,
                latency=t_total_ms
            )

            return CRAGResponse(
                question=clean_question,
                original_query=clean_question,
                answer=STANDARD_REFUSAL_ANSWER,
                citations=[],
                retrieved_chunks=final_chunks or initial_retrieval,
                initial_retrieval=initial_retrieval,
                initial_evaluation=initial_eval,
                corrective_triggered=corrective_triggered,
                rewritten_query=rewritten_query,
                corrective_retrieval=corrective_retrieval,
                final_evaluation=final_eval,
                latency=round(t_total_ms, 2),
                latency_ms=round(t_total_ms, 2),
                refused=True,
                refusal_reason=refusal_reason,
                retry_count=retry_count,
                retrieval_latency=round(t_retrieval_ms, 2),
                eval_latency=round(t_eval_ms, 2),
                rewrite_latency=round(t_rewrite_ms, 2),
                context_latency=0.0,
                generation_latency=0.0,
                citation_latency=0.0,
                model_name=getattr(self.generator, "model_name", "mock"),
                provider=getattr(self.generator, "provider", "mock"),
                metadata={
                    "crag_phase": "explicit_refusal",
                    "initial_status": initial_eval.status.value,
                    "final_status": final_eval.status.value,
                }
            )

        # =====================================================================
        # BƯỚC 5: Đóng gói ngữ cảnh có cấu trúc (Context Building)
        # =====================================================================
        t_ctx_0 = time.perf_counter()
        ctx_result = self.context_builder.build_context(
            retrieved_chunks=final_chunks,
            max_tokens=self.config.MAX_CONTEXT_TOKENS
        )
        t_context_ms = (time.perf_counter() - t_ctx_0) * 1000.0

        # =====================================================================
        # BƯỚC 6: Sinh câu trả lời bằng LLM (LLM Generation)
        # =====================================================================
        t_gen_0 = time.perf_counter()
        gen_result = self.generator.generate(
            question=clean_question,
            context=ctx_result.context_text,
            temperature=self.config.TEMPERATURE
        )
        t_generation_ms = (time.perf_counter() - t_gen_0) * 1000.0

        # =====================================================================
        # BƯỚC 7: Ánh xạ và chuẩn hóa trích dẫn pháp lý (Citation Resolution)
        # =====================================================================
        t_cit_0 = time.perf_counter()
        citation_result = self.citation_resolver.resolve_citations(
            answer=gen_result.answer,
            citation_mapping=ctx_result.citation_mapping,
            citations_list=gen_result.citations,
            replace_in_text=self.config.REPLACE_IN_TEXT_CITATIONS,
            append_footnotes=self.config.APPEND_FOOTNOTES
        )
        t_citation_ms = (time.perf_counter() - t_cit_0) * 1000.0

        # =====================================================================
        # BƯỚC 8: Chốt chặn an toàn sau sinh (Post-Generation Guard)
        # =====================================================================
        post_guard_res = self.guard.check_post_generation(gen_result, citation_result)

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

        t_total_ms = (time.perf_counter() - t_start) * 1000.0

        # =====================================================================
        # BƯỚC 9: Ghi log có cấu trúc phục vụ giám sát và phân tích thực nghiệm
        # =====================================================================
        self._log_crag_execution(
            question=clean_question,
            corrective_triggered=corrective_triggered,
            rewritten_query=rewritten_query,
            initial_eval=initial_eval,
            final_eval=final_eval,
            retry_count=retry_count,
            refused=final_refused,
            latency=t_total_ms
        )

        return CRAGResponse(
            question=clean_question,
            original_query=clean_question,
            answer=final_answer,
            citations=final_citations,
            retrieved_chunks=final_chunks,
            initial_retrieval=initial_retrieval,
            initial_evaluation=initial_eval,
            corrective_triggered=corrective_triggered,
            rewritten_query=rewritten_query,
            corrective_retrieval=corrective_retrieval,
            final_evaluation=final_eval,
            latency=round(t_total_ms, 2),
            latency_ms=round(t_total_ms, 2),
            refused=final_refused,
            refusal_reason=final_reason,
            retry_count=retry_count,
            retrieval_latency=round(t_retrieval_ms, 2),
            eval_latency=round(t_eval_ms, 2),
            rewrite_latency=round(t_rewrite_ms, 2),
            context_latency=round(t_context_ms, 2),
            generation_latency=round(t_generation_ms, 2),
            citation_latency=round(t_citation_ms, 2),
            model_name=gen_result.model_name,
            provider=gen_result.provider,
            metadata={
                "corrective_triggered": corrective_triggered,
                "initial_status": initial_eval.status.value,
                "final_status": final_eval.status.value,
                "context_tokens": ctx_result.total_tokens,
                "sources_included": ctx_result.num_included,
            }
        )

    def _log_crag_execution(
        self,
        question: str,
        corrective_triggered: bool,
        rewritten_query: Optional[str],
        initial_eval: RetrievalEvaluation,
        final_eval: RetrievalEvaluation,
        retry_count: int,
        refused: bool,
        latency: float
    ) -> None:
        """Ghi log có cấu trúc phục vụ giám sát và phân tích thực nghiệm."""
        logger.info(
            "CRAG execution completed: "
            "question='%s' | corrective_triggered=%s | rewritten_query='%s' | "
            "initial_status=%s | initial_conf=%.2f | "
            "final_status=%s | final_conf=%.2f | "
            "retry_count=%d | refused=%s | latency=%.2fms",
            question,
            corrective_triggered,
            rewritten_query or "N/A",
            initial_eval.status.value,
            initial_eval.confidence,
            final_eval.status.value,
            final_eval.confidence,
            retry_count,
            refused,
            latency
        )
