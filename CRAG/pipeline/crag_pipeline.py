"""
CRAG Pipeline.
Đường ống xử lý hoàn chỉnh của Corrective RAG (CRAG).
Tích hợp: Retrieval -> Document Grading -> Strip & Filter / Web Fallback -> Generation -> Citation.
"""

from __future__ import annotations
import time
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

        # 1. Retriever (kế thừa chính xác từ Traditional RAG)
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

    def answer(self, question: str) -> CRAGResponse:
        """
        Thực thi toàn bộ quy trình Corrective RAG cho một câu hỏi.
        """
        t_start = time.perf_counter()
        if not question or not question.strip():
            raise ValueError("Câu hỏi người dùng không được rỗng hoặc chỉ chứa khoảng trắng.")

        clean_question = question.strip()
        telemetry = CRAGTelemetry()

        # BƯỚC 1: Thu hồi véc-tơ (Dense Retrieval)
        t_ret_0 = time.perf_counter()
        retrieved_chunks = self.retriever.retrieve(
            query=clean_question, top_k=self.config.TOP_K
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
                citation_mapping[f"SOURCE {ext_idx}"] = {
                    "document_title": ext["title"],
                    "document_id": "WEB_EXTERNAL",
                    "article_number": "Tra cứu ngoài",
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
                citation_mapping[f"SOURCE {ext_idx}"] = {
                    "document_title": ext["title"],
                    "document_id": "WEB_EXTERNAL",
                    "article_number": "Tra cứu ngoài",
                    "source_url": ext["url"],
                }

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

        # BƯỚC 6: Chốt chặn an toàn sau khi sinh (Post-Generation Guard)
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
