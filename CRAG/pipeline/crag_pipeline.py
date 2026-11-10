"""
CRAG Pipeline.
Đường ống xử lý hoàn chỉnh của Corrective RAG (CRAG).
Tích hợp: Retrieval -> Document Grading -> Strip & Filter / Web Fallback -> Generation -> Citation.
"""

from __future__ import annotations
import time
import re
import logging
from typing import Optional, Dict, Any, List

from RAG.pipeline.config import PipelineConfig, default_pipeline_config
from RAG.retriever.dense_retriever import DenseTopKRetriever
from RAG.retriever.schema import RetrievedChunk
from RAG.generator.base import BaseLegalGenerator
from RAG.generator.factory import get_generator
from RAG.citation.resolver import CitationResolver
from RAG.guards.refusal_guard import RefusalGuard
from RAG.guards.config import GuardConfig
from RAG.guards.scope_guard import SharedScopeGuard
from RAG.guards.document_grounding_gate import NamedLegalDocumentResolver
from RAG.guards.evidence_gate import PreGenerationEvidenceGate
from RAG.guards.qa_alignment_guard import PostGenerationQAAlignmentGuard

from CRAG.config import CRAGConfig, crag_config
from CRAG.evaluator.schema import ActionTrigger, GradeVerdict, RetrievalGradingResult
from CRAG.evaluator.semantic_grader import SemanticDocumentGrader
from CRAG.refinement.stripper import KnowledgeStripper
from CRAG.refinement.recomposer import KnowledgeRecomposer
from CRAG.refinement.schema import RefinedContext
from CRAG.transformation.query_rewriter import LegalQueryRewriter
from CRAG.search.web_searcher import LegalWebSearcher
from CRAG.search.schema import SearchResponse
from CRAG.pipeline.schema import CRAGResponse, CRAGTelemetry

logger = logging.getLogger("CRAG.pipeline.crag_pipeline")


class CRAGPipeline:
    """
    Hệ thống Corrective RAG (CRAG) End-to-End:
    1. Dense Top-K Retrieval từ kho dữ liệu vector cơ sở.
    2. Retrieval Evaluator (Document Grader) đánh giá mức độ tin cậy và liên quan.
    3. Phân nhánh hành động động (Dynamic Action Dispatching):
       - REFINE: Tinh lọc tri thức nội bộ (Strip & Filter), loại bỏ nhiễu ngữ cảnh.
       - COMBINE_SEARCH: Tinh lọc tri thức nội bộ kết hợp tìm kiếm ngoài.
       - WEB_SEARCH: Tìm kiếm tri thức ngoài thay thế khi retrieval nội bộ sai hoàn toàn.
       - REFUSE: Từ chối dứt khoát câu hỏi ngoài phạm vi, tránh ảo giác LLM.
    4. Sinh câu trả lời bảo thủ có căn cứ pháp lý.
    5. Kiểm định tính toàn vẹn của trích dẫn và chốt chặn an toàn.
    """

    def __init__(
        self,
        pipeline_config: Optional[PipelineConfig] = None,
        crag_cfg: Optional[CRAGConfig] = None,
        retriever: Optional[DenseTopKRetriever] = None,
        grader: Optional[SemanticDocumentGrader] = None,
        stripper: Optional[KnowledgeStripper] = None,
        recomposer: Optional[KnowledgeRecomposer] = None,
        query_rewriter: Optional[LegalQueryRewriter] = None,
        web_searcher: Optional[LegalWebSearcher] = None,
        generator: Optional[BaseLegalGenerator] = None,
        citation_resolver: Optional[CitationResolver] = None,
        guard: Optional[RefusalGuard] = None,
    ):
        self.config = pipeline_config or default_pipeline_config
        self.crag_config = crag_cfg or crag_config

        # 1. Retriever (kế thừa chính xác từ Traditional RAG, hỗ trợ Hybrid/BM25)
        if retriever is not None:
            self.retriever = retriever
        else:
            from RAG.retriever.config import RetrieverConfig
            ret_config = RetrieverConfig(
                TOP_K=self.config.TOP_K,
                SIMILARITY_THRESHOLD=self.config.SIMILARITY_THRESHOLD,
                PERSIST_DIRECTORY=self.config.CHROMA_PERSIST_DIRECTORY,
                COLLECTION_NAME=self.config.COLLECTION_NAME,
            )
            ret_type = getattr(self.config, "RETRIEVER_TYPE", "dense").lower()
            if ret_type == "hybrid":
                from RAG.retriever.hybrid_retriever import HybridRetriever
                self.retriever = HybridRetriever(config=ret_config, mode="hybrid", rrf_k=60)
            elif ret_type == "bm25":
                from RAG.retriever.bm25_retriever import BM25OkapiRetriever
                self.retriever = BM25OkapiRetriever(config=ret_config)
            else:
                self.retriever = DenseTopKRetriever(config=ret_config)

        # 2. Document Grader (RAG-11)
        self.grader = grader or SemanticDocumentGrader(
            config=self.crag_config
        )

        # 3. Knowledge Stripper & Recomposer (RAG-12)
        self.stripper = stripper or KnowledgeStripper(
            strip_threshold=self.crag_config.STRIP_THRESHOLD
        )
        self.recomposer = recomposer or KnowledgeRecomposer(
            stripper=self.stripper,
            max_context_chars=self.crag_config.MAX_REFINED_CONTEXT_CHARS,
        )

        # 4. Query Rewriter & Web Searcher (RAG-13)
        self.query_rewriter = query_rewriter or LegalQueryRewriter()
        self.web_searcher = web_searcher or LegalWebSearcher(
            provider=self.crag_config.SEARCH_PROVIDER
        )

        # 5. Generator (RAG-05)
        if generator is not None:
            self.generator = generator
        else:
            self.generator = get_generator(
                provider=self.config.LLM_PROVIDER,
                model_name=self.config.LLM_MODEL,
            )

        # 6. Citation Resolver & Guard (RAG-06)
        self.citation_resolver = citation_resolver or CitationResolver(
            replace_in_text=self.config.REPLACE_IN_TEXT_CITATIONS,
            append_footnotes=self.config.APPEND_FOOTNOTES,
            reject_invalid=True,
        )
        self.guard = guard or RefusalGuard(
            config=GuardConfig(
                SIMILARITY_THRESHOLD=self.config.SIMILARITY_THRESHOLD,
                ENABLE_PRE_GENERATION_GUARD=False,  # CRAG thay thế pre-guard bằng Document Grader chuyên sâu
                ENABLE_POST_GENERATION_GUARD=self.config.ENABLE_POST_GUARD,
            )
        )

        # 7. Các chốt chặn đa tầng (Multi-tier Safety Guards)
        self.scope_guard = SharedScopeGuard()
        self.document_resolver = NamedLegalDocumentResolver()
        self.evidence_gate = PreGenerationEvidenceGate()
        self.qa_alignment_guard = PostGenerationQAAlignmentGuard()

    def answer(self, question: str) -> CRAGResponse:
        """
        Thực thi toàn bộ quy trình Corrective RAG cho một câu hỏi.
        """
        t_start = time.perf_counter()
        if not question or not question.strip():
            raise ValueError("Câu hỏi người dùng không được rỗng hoặc chỉ chứa khoảng trắng.")

        clean_question = question.strip()
        telemetry = CRAGTelemetry()

        # CHỐT CHẶN TIER 1: Scope & Intent Boundary Gate (Shared Scope Guard)
        if getattr(self.crag_config, "ENABLE_TIER1_SHARED_SCOPE_GATE", True):
            scope_res = self.scope_guard.check_scope(clean_question)
            if scope_res.trigger_refusal:
                telemetry.total_latency = round((time.perf_counter() - t_start) * 1000.0, 2)
                return CRAGResponse(
                    question=clean_question,
                    answer=scope_res.refusal_message or self.guard.config.REFUSAL_MESSAGE,
                    citations=[],
                    retrieved_chunks=[],
                    grading_result=None,
                    action_taken="REFUSE",
                    telemetry=telemetry,
                    refused=True,
                    refusal_reason=f"Hệ thống xác định {scope_res.refusal_reason}",
                )

        # CHỐT CHẶN TIER 2: Document Coverage & Grounding Gate
        doc_filter = None
        if getattr(self.crag_config, "ENABLE_TIER2_DOCUMENT_GROUNDING_GATE", True):
            doc_res = self.document_resolver.resolve(clean_question)
            if doc_res.trigger_refusal:
                telemetry.total_latency = round((time.perf_counter() - t_start) * 1000.0, 2)
                return CRAGResponse(
                    question=clean_question,
                    answer=doc_res.refusal_message or self.guard.config.REFUSAL_MESSAGE,
                    citations=[],
                    retrieved_chunks=[],
                    grading_result=None,
                    action_taken="DIRECT_REFUSAL_DOC",
                    telemetry=telemetry,
                    refused=True,
                    refusal_reason=doc_res.refusal_reason,
                )
            elif doc_res.has_specific_document and doc_res.filter_metadata:
                doc_filter = doc_res.filter_metadata

        # BƯỚC 1: Thu hồi véc-tơ (Dense Retrieval)
        t_ret_0 = time.perf_counter()
        retrieved_chunks = self.retriever.retrieve(
            query=clean_question,
            top_k=self.config.TOP_K,
            where=doc_filter,
        )
        telemetry.retrieval_latency = round((time.perf_counter() - t_ret_0) * 1000.0, 2)

        # BƯỚC 2: Chấm điểm tài liệu bằng Retrieval Evaluator (Document Grader)
        t_grade_0 = time.perf_counter()
        grading_result = self.grader.grade_documents(
            query=clean_question, chunks=retrieved_chunks
        )
        telemetry.grading_latency = round((time.perf_counter() - t_grade_0) * 1000.0, 2)

        action = grading_result.action

        # BƯỚC 3: Phân nhánh hành động
        # 3.1. HÀNH ĐỘNG REFUSE (Câu hỏi ngoài phạm vi rõ ràng)
        if action == ActionTrigger.REFUSE:
            telemetry.total_latency = round((time.perf_counter() - t_start) * 1000.0, 2)
            refusal_msg = self.guard.config.REFUSAL_MESSAGE
            return CRAGResponse(
                question=clean_question,
                answer=refusal_msg,
                citations=[],
                retrieved_chunks=retrieved_chunks,
                grading_result=grading_result,
                action_taken=action.value,
                telemetry=telemetry,
                refused=True,
                refusal_reason="Hệ thống xác định câu hỏi nằm ngoài phạm vi pháp luật lao động Việt Nam.",
            )

        refined_context: Optional[RefinedContext] = None
        search_res: Optional[SearchResponse] = None
        context_text = ""
        citation_mapping: Dict[str, Dict[str, Any]] = {}

        # 3.2. HÀNH ĐỘNG REFINE (Tài liệu nội bộ tin cậy -> Strip & Filter)
        if action == ActionTrigger.REFINE:
            t_ref_0 = time.perf_counter()
            refined_context = self.recomposer.recompose(
                chunks=retrieved_chunks, query=clean_question
            )
            telemetry.refinement_latency = round((time.perf_counter() - t_ref_0) * 1000.0, 2)
            context_text = refined_context.raw_context_text

            # Xây dựng citation mapping từ các doc được giữ lại
            for doc in refined_context.documents:
                source_key = f"SOURCE {doc.source_index}"
                citation_mapping[source_key] = doc.metadata

        # 3.3. HÀNH ĐỘNG COMBINE_SEARCH (Tài liệu nội bộ mơ hồ -> Kết hợp Web Search)
        elif action == ActionTrigger.COMBINE_SEARCH:
            t_trans_0 = time.perf_counter()
            transformed = self.query_rewriter.rewrite(clean_question)
            telemetry.transformation_latency = round(
                (time.perf_counter() - t_trans_0) * 1000.0, 2
            )

            t_search_0 = time.perf_counter()
            search_res = self.web_searcher.search(
                query=clean_question,
                transformed_query=transformed.search_query,
                top_k=self.crag_config.MAX_SEARCH_RESULTS,
            )
            telemetry.search_latency = round((time.perf_counter() - t_search_0) * 1000.0, 2)

            # Tái hợp nội bộ kèm tri thức ngoài
            t_ref_0 = time.perf_counter()
            ext_snippets = [
                {"title": r.title, "snippet": r.snippet, "url": r.url}
                for r in search_res.results
            ]
            refined_context = self.recomposer.recompose(
                chunks=retrieved_chunks,
                query=clean_question,
                external_snippets=ext_snippets,
            )
            telemetry.refinement_latency = round((time.perf_counter() - t_ref_0) * 1000.0, 2)
            context_text = refined_context.raw_context_text

            for doc in refined_context.documents:
                citation_mapping[f"SOURCE {doc.source_index}"] = doc.metadata
            web_start = len(refined_context.documents) + 1
            for ext_idx, ext in enumerate(ext_snippets, start=web_start):
                title = ext["title"]
                art_match = re.search(r"(?:Điều|Khoản)\s+\d+(?:[,\s]+(?:Điều\s+)?\d+)*", title, re.IGNORECASE)
                citation_mapping[f"SOURCE {ext_idx}"] = {
                    "document_title": title,
                    "document_id": "WEB_EXTERNAL",
                    "article_number": art_match.group(0).title() if art_match else None,
                    "article_title": "Nguồn tra cứu ngoài",
                    "source_url": ext["url"],
                }

        # 3.4. HÀNH ĐỘNG WEB_SEARCH (Tài liệu nội bộ sai lệch hoàn toàn -> Chỉ dùng Web Search)
        elif action == ActionTrigger.WEB_SEARCH:
            t_trans_0 = time.perf_counter()
            transformed = self.query_rewriter.rewrite(clean_question)
            telemetry.transformation_latency = round(
                (time.perf_counter() - t_trans_0) * 1000.0, 2
            )

            t_search_0 = time.perf_counter()
            search_res = self.web_searcher.search(
                query=clean_question,
                transformed_query=transformed.search_query,
                top_k=self.crag_config.MAX_SEARCH_RESULTS,
            )
            telemetry.search_latency = round((time.perf_counter() - t_search_0) * 1000.0, 2)

            t_ref_0 = time.perf_counter()
            ext_snippets = [
                {"title": r.title, "snippet": r.snippet, "url": r.url}
                for r in search_res.results
            ]
            refined_context = self.recomposer.recompose(
                chunks=[],
                query=clean_question,
                external_snippets=ext_snippets,
            )
            telemetry.refinement_latency = round((time.perf_counter() - t_ref_0) * 1000.0, 2)
            context_text = refined_context.raw_context_text

            for ext_idx, ext in enumerate(ext_snippets, start=1):
                title = ext["title"]
                art_match = re.search(r"(?:Điều|Khoản)\s+\d+(?:[,\s]+(?:Điều\s+)?\d+)*", title, re.IGNORECASE)
                citation_mapping[f"SOURCE {ext_idx}"] = {
                    "document_title": title,
                    "document_id": "WEB_EXTERNAL",
                    "article_number": art_match.group(0).title() if art_match else None,
                    "article_title": "Nguồn tra cứu ngoài",
                    "source_url": ext["url"],
                }

        # CHỐT CHẶN TIER 3: Pre-Generation Evidence Gate (Kiểm định bằng chứng trước sinh)
        if getattr(self.crag_config, "ENABLE_TIER3_PRE_GEN_EVIDENCE_GATE", True):
            # Nếu hành động là WEB_SEARCH và có kết quả ngoài thì ưu tiên tri thức ngoài đã recompose
            if not (action == ActionTrigger.WEB_SEARCH and search_res and search_res.results):
                evidence_res = self.evidence_gate.evaluate(clean_question, retrieved_chunks)
                if evidence_res.trigger_refusal:
                    telemetry.total_latency = round((time.perf_counter() - t_start) * 1000.0, 2)
                    return CRAGResponse(
                        question=clean_question,
                        answer=evidence_res.refusal_message or self.guard.config.REFUSAL_MESSAGE,
                        citations=[],
                        retrieved_chunks=retrieved_chunks,
                        grading_result=grading_result,
                        action_taken="REFUSE_UNSUPPORTED_EVIDENCE",
                        refined_context=refined_context,
                        search_response=search_res,
                        telemetry=telemetry,
                        refused=True,
                        refusal_reason=evidence_res.refusal_reason,
                    )

        # BƯỚC 4: Sinh câu trả lời bảo thủ (LLM Generation)
        t_gen_0 = time.perf_counter()
        gen_result = self.generator.generate(
            question=clean_question,
            context=context_text,
            temperature=self.config.TEMPERATURE,
        )
        telemetry.generation_latency = round((time.perf_counter() - t_gen_0) * 1000.0, 2)

        # BƯỚC 5: Xử lý và kiểm định trích dẫn (Citation Resolution)
        citation_result = self.citation_resolver.resolve_citations(
            answer=gen_result.answer,
            citation_mapping=citation_mapping,
            citations_list=gen_result.citations,
            replace_in_text=self.config.REPLACE_IN_TEXT_CITATIONS,
            append_footnotes=self.config.APPEND_FOOTNOTES,
        )

        # BƯỚC 6: Chốt chặn an toàn sau khi sinh (Post-Generation Guard & Tier 4 QA Alignment)
        post_guard_res = self.guard.check_post_generation(gen_result, citation_result, context_text=context_text)

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

        # TIER 4: Post-Generation QA Alignment Guard
        if getattr(self.crag_config, "ENABLE_TIER4_QA_ALIGNMENT_GUARD", True) and not final_refused:
            qa_res = self.qa_alignment_guard.evaluate_answer(clean_question, final_answer, retrieved_chunks)
            if qa_res.trigger_refusal:
                final_answer = self.guard.config.REFUSAL_MESSAGE
                final_refused = True
                final_reason = qa_res.refusal_reason
                final_citations = []
            elif qa_res.pruned_answer:
                final_answer = qa_res.pruned_answer

        telemetry.total_latency = round((time.perf_counter() - t_start) * 1000.0, 2)

        return CRAGResponse(
            question=clean_question,
            answer=final_answer,
            citations=final_citations,
            retrieved_chunks=retrieved_chunks,
            grading_result=grading_result,
            action_taken=action.value,
            refined_context=refined_context,
            search_response=search_res,
            telemetry=telemetry,
            refused=final_refused,
            refusal_reason=final_reason,
        )
