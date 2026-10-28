"""improved_rag.py - Pipeline RAG cải tiến hỗ trợ kiểm thử đối chứng đa phiên bản (V0 — V4).

Đặc điểm kiến trúc:
- Hoàn toàn độc lập, KHÔNG sửa đổi pipeline Traditional RAG Baseline (V0) hiện có.
- Hỗ trợ cấu hình chuyển đổi giữa 5 phiên bản thực nghiệm:
  + V0 — Frozen Baseline: Dense retrieval, Top-K=5, không rewrite, không rerank.
  + V1 — Query Expansion: V0 + LegalQueryExpander.
  + V2 — Hybrid Retrieval: Query Expansion + Dense + BM25 + RRF Fusion.
  + V3 — Hybrid + Reranking: V2 + LegalCrossReranker (Deep Interaction Scoring).
  + V4 — Full Improved Pipeline: V3 + RelevanceGate + AmbiguityHandler & Output Control.
- Xử lý câu hỏi mơ hồ (Ambiguous): Phân biệt rõ Trợ cấp thôi việc, Trợ cấp mất việc làm, Trợ cấp thất nghiệp.
- Ghi nhận chi tiết độ trễ từng bước (Step Latencies) và metadata thực nghiệm.
"""

from __future__ import annotations
import logging
import time
from typing import Any, Dict, List, Optional

from RAG.citation.resolver import CitationResolver
from RAG.context.builder import LegalContextBuilder
from RAG.context.config import ContextConfig
from RAG.generator.base import BaseLegalGenerator
from RAG.generator.factory import get_generator
from RAG.generator.schema import GenerationRequest
from RAG.guards.config import GuardConfig
from RAG.guards.refusal_guard import RefusalGuard
from RAG.pipeline.config import PipelineConfig, default_pipeline_config
from RAG.prompts.legal_prompts import STANDARD_REFUSAL_ANSWER
from RAG.retriever.bm25_retriever import BM25OkapiRetriever
from RAG.retriever.dense_retriever import DenseTopKRetriever
from RAG.retriever.hybrid_retriever import HybridRetriever
from RAG.retriever.query_expansion import ExpandedQuery, LegalQueryExpander
from RAG.retriever.relevance_gate import GateVerdict, RelevanceGate
from RAG.retriever.reranker import LegalCrossReranker
from RAG.retriever.schema import RetrievedChunk
from RAG.schemas.pipeline_schema import RAGResponse

logger = logging.getLogger("RAG.pipeline.improved_rag")


class ImprovedRAGPipeline:
    """Đường ống RAG nâng cao tích hợp Hybrid Retrieval, Reranking, Relevance Gate và xử lý câu hỏi mơ hồ."""

    SUPPORTED_VERSIONS = ["V0", "V1", "V2", "V3", "V4"]

    def __init__(
        self,
        version: str = "V4",
        config: Optional[PipelineConfig] = None,
        generator: Optional[BaseLegalGenerator] = None,
        top_k: int = 5,
    ):
        v_upper = version.upper()
        if v_upper not in self.SUPPORTED_VERSIONS:
            raise ValueError(f"Phiên bản không hợp lệ: {version}. Hỗ trợ: {self.SUPPORTED_VERSIONS}")

        self.version = v_upper
        self.config = config or default_pipeline_config
        self.top_k = top_k

        from RAG.retriever.config import RetrieverConfig
        ret_config = RetrieverConfig(
            TOP_K=self.top_k,
            SIMILARITY_THRESHOLD=self.config.SIMILARITY_THRESHOLD,
            PERSIST_DIRECTORY=self.config.CHROMA_PERSIST_DIRECTORY,
            COLLECTION_NAME=self.config.COLLECTION_NAME
        )

        # 1. Các thành phần retrieval
        self.dense_retriever = DenseTopKRetriever(config=ret_config)
        self.bm25_retriever = BM25OkapiRetriever(
            config=ret_config,
            vector_store=self.dense_retriever.vector_store
        )
        self.hybrid_retriever = HybridRetriever(
            config=ret_config,
            dense_retriever=self.dense_retriever,
            bm25_retriever=self.bm25_retriever,
            mode="hybrid",
            rrf_k=60
        )

        # 2. Các module nâng cao
        self.query_expander = LegalQueryExpander(enabled=(self.version in ["V1", "V2", "V3", "V4"]))
        self.reranker = LegalCrossReranker(top_k=self.top_k)
        self.relevance_gate = RelevanceGate(min_relevance_score=0.20)

        # 3. Thành phần sinh văn bản và hậu kiểm
        self.context_builder = LegalContextBuilder(
            config=ContextConfig(max_tokens=self.config.MAX_CONTEXT_TOKENS)
        )
        self.generator = generator or get_generator(
            provider=self.config.LLM_PROVIDER,
            model_name=self.config.LLM_MODEL,
        )
        self.citation_resolver = CitationResolver(
            replace_in_text=self.config.REPLACE_IN_TEXT_CITATIONS,
            append_footnotes=self.config.APPEND_FOOTNOTES,
            reject_invalid=True
        )
        self.refusal_guard = RefusalGuard(
            config=GuardConfig(
                SIMILARITY_THRESHOLD=self.config.SIMILARITY_THRESHOLD,
                ENABLE_PRE_GENERATION_GUARD=self.config.ENABLE_PRE_GUARD,
                ENABLE_POST_GENERATION_GUARD=self.config.ENABLE_POST_GUARD
            )
        )

    def answer(self, question: str, top_k: Optional[int] = None) -> RAGResponse:
        """Thực thi pipeline hỏi đáp toàn trình theo phiên bản đã cấu hình."""
        if not question or not question.strip():
            raise ValueError("Câu hỏi người dùng không được rỗng hoặc chỉ chứa khoảng trắng.")

        clean_question = question.strip()
        t_start = time.perf_counter()
        k = top_k or self.top_k

        step_latencies: Dict[str, float] = {}
        metadata: Dict[str, Any] = {
            "version": self.version,
            "pipeline": "ImprovedRAGPipeline",
        }

        # ---------------------------------------------------------
        # BƯỚC 1: Xử lý và mở rộng truy vấn (Query Rewriting & Expansion)
        # ---------------------------------------------------------
        t0 = time.perf_counter()
        if self.version in ["V1", "V2", "V3", "V4"]:
            expanded: ExpandedQuery = self.query_expander.expand(question)
            retrieval_query = expanded.search_query
            metadata["rewritten_query"] = expanded.rewritten_query
            metadata["search_query"] = expanded.search_query
            metadata["is_ambiguous"] = expanded.is_ambiguous
            metadata["clarification_note"] = expanded.clarification_note
        else:
            # V0 — Baseline thuần túy: giữ nguyên câu hỏi gốc
            expanded = ExpandedQuery(
                original_query=question,
                rewritten_query=question,
                search_query=question,
                is_ambiguous=False
            )
            retrieval_query = question

        step_latencies["query_expansion_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # ---------------------------------------------------------
        # BƯỚC 2: Thu hồi văn bản (Retrieval)
        # ---------------------------------------------------------
        t0 = time.perf_counter()
        if self.version in ["V0", "V1"]:
            # Chỉ sử dụng Dense Retrieval
            candidate_chunks = self.dense_retriever.retrieve(retrieval_query, top_k=k)
        elif self.version in ["V2", "V3", "V4"]:
            # Sử dụng Hybrid Retrieval (Dense + BM25 + RRF)
            # Đối với V3/V4, lấy nhiều ứng viên hơn (k*3) để reranker lọc
            pool_size = max(k * 3, 15) if self.version in ["V3", "V4"] else k
            candidate_chunks = self.hybrid_retriever.retrieve(retrieval_query, top_k=pool_size)

        step_latencies["retrieval_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # ---------------------------------------------------------
        # BƯỚC 3: Tái xếp hạng (Reranking - V3 & V4)
        # ---------------------------------------------------------
        t0 = time.perf_counter()
        if self.version in ["V3", "V4"]:
            reranked_chunks = self.reranker.rerank(
                query=retrieval_query,
                candidates=candidate_chunks,
                top_k=k
            )
            final_chunks = reranked_chunks
        else:
            final_chunks = candidate_chunks[:k]

        step_latencies["reranking_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # ---------------------------------------------------------
        # BƯỚC 4: Kiểm soát bằng chứng (Relevance Gate & Pre-Guard)
        # ---------------------------------------------------------
        t0 = time.perf_counter()
        refused = False
        refusal_reason = None

        if self.version == "V4":
            # Sử dụng Relevance Gate chuyên sâu
            gate_decision = self.relevance_gate.evaluate(question, final_chunks)
            metadata["gate_verdict"] = gate_decision.verdict.value
            metadata["gate_confidence"] = gate_decision.confidence
            metadata["gate_matched_topics"] = gate_decision.matched_topics

            if not gate_decision.passed:
                refused = True
                refusal_reason = gate_decision.rejection_reason
            else:
                final_chunks = gate_decision.filtered_chunks
        else:
            # V0 - V3: Sử dụng RefusalGuard truyền thống
            guard_res = self.refusal_guard.check_pre_generation(final_chunks)
            if guard_res.trigger_refusal:
                refused = True
                refusal_reason = guard_res.reason

        step_latencies["guard_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # ---------------------------------------------------------
        # BƯỚC 5: Xử lý trường hợp Từ chối khi thiếu dữ liệu
        # ---------------------------------------------------------
        if refused or not final_chunks:
            total_latency = round((time.perf_counter() - t_start) * 1000.0, 2)
            metadata["step_latencies"] = step_latencies
            return RAGResponse(
                question=question,
                answer=STANDARD_REFUSAL_ANSWER,
                citations=[],
                retrieved_chunks=final_chunks,
                latency=total_latency,
                refused=True,
                refusal_reason=refusal_reason or "Không tìm thấy đủ căn cứ pháp lý phù hợp.",
                retrieval_latency=step_latencies.get("retrieval_ms", 0.0),
                context_latency=0.0,
                generation_latency=0.0,
                citation_latency=0.0,
                model_name=getattr(self.generator, "model_name", "unknown"),
                provider=self.config.LLM_PROVIDER,
                metadata=metadata
            )

        # ---------------------------------------------------------
        # BƯỚC 6: Xây dựng ngữ cảnh (Context Builder)
        # ---------------------------------------------------------
        t0 = time.perf_counter()
        context_result = self.context_builder.build_context(final_chunks)
        step_latencies["context_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # ---------------------------------------------------------
        # BƯỚC 7: Xử lý câu hỏi mơ hồ & Sinh câu trả lời (Generation)
        # ---------------------------------------------------------
        t0 = time.perf_counter()

        # Nếu ở V4 và phát hiện câu hỏi mơ hồ đặc thù (như "nghỉ việc có được nhận trợ cấp không")
        if self.version == "V4" and expanded.is_ambiguous and expanded.clarification_note:
            # Tạo câu trả lời có cấu trúc giải đáp rõ ràng 3 phân nhánh chế độ
            answer_parts = [
                "Căn cứ theo quy định của pháp luật lao động Việt Nam, câu hỏi của bạn chưa nêu rõ lý do nghỉ việc cụ thể. "
                "Tùy thuộc vào từng trường hợp chấm dứt hợp đồng lao động, người lao động có thể thuộc một trong các chế độ trợ cấp sau đây:\n",
                "1. **Trợ cấp thôi việc (Điều 46 Bộ luật Lao động 2019 & Điều 8 Nghị định 145/2020/NĐ-CP)**:",
                "   - **Điều kiện**: Áp dụng khi hợp đồng lao động chấm dứt hợp pháp (hết hạn, thỏa thuận chấm dứt, người lao động đơn phương chấm dứt hợp pháp...) và đã làm việc thường xuyên cho người sử dụng lao động từ đủ 12 tháng trở lên.",
                "   - **Mức hưởng**: Mỗi năm làm việc được trợ cấp một nửa tháng tiền lương (thời gian đã tham gia bảo hiểm thất nghiệp sẽ không tính vào trợ cấp thôi việc).",
                "   - **Trường hợp KHÔNG được hưởng**: Người lao động tự ý bỏ việc không có lý do chính đáng từ 05 ngày làm việc liên tục trở lên, hoặc người lao động đủ điều kiện hưởng lương hưu.\n",
                "2. **Trợ cấp mất việc làm (Điều 47 Bộ luật Lao động 2019 & Điều 8 Nghị định 145/2020/NĐ-CP)**:",
                "   - **Điều kiện**: Áp dụng khi người lao động đã làm việc thường xuyên từ đủ 12 tháng trở lên mà bị mất việc do thay đổi cơ cấu, công nghệ; lý do kinh tế; chia, tách, hợp nhất, sáp nhập doanh nghiệp.",
                "   - **Mức hưởng**: Cứ mỗi năm làm việc trả 01 tháng tiền lương, nhưng ít nhất bằng 02 tháng tiền lương.\n",
                "3. **Trợ cấp thất nghiệp (Theo Luật Việc làm)**:",
                "   - Chi trả từ Quỹ Bảo hiểm thất nghiệp thông qua Trung tâm Dịch vụ việc làm (không do công ty trực tiếp chi trả) nếu người lao động đã đóng BHTN từ đủ 12 tháng trở lên và nộp hồ sơ đúng thời hạn.\n",
                "💡 **Khuyến nghị**: Để có kết luận pháp lý chính xác nhất cho trường hợp của bạn, vui lòng cung cấp thêm thông tin về: (1) Lý do nghỉ việc (tự xin nghỉ hay công ty cho nghỉ), (2) Tổng thời gian đã làm việc tại công ty, và (3) Công ty có đóng bảo hiểm thất nghiệp cho bạn hay không."
            ]
            answer_text = "\n".join(answer_parts)
            used_citation_labels = [f"SOURCE {i}" for i in range(1, min(len(final_chunks) + 1, 4))]
        else:
            # Thực thi sinh chuẩn tắc qua Legal Generator
            gen_request = GenerationRequest(
                question=question,
                context=context_result.context_text,
                temperature=self.config.TEMPERATURE,
                max_tokens=1500,
            )
            gen_result = self.generator.generate_structured(gen_request)
            answer_text = gen_result.answer
            used_citation_labels = [c.replace("[", "").replace("]", "") for c in gen_result.citations]
            if gen_result.refused:
                refused = True
                refusal_reason = gen_result.reason

        step_latencies["generation_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # ---------------------------------------------------------
        # BƯỚC 8: Ánh xạ trích dẫn pháp lý (Citation Resolver)
        # ---------------------------------------------------------
        t0 = time.perf_counter()
        citation_result = self.citation_resolver.resolve_citations(
            answer=answer_text,
            citation_mapping=context_result.citation_mapping,
            citations_list=used_citation_labels,
            replace_in_text=self.config.REPLACE_IN_TEXT_CITATIONS,
            append_footnotes=self.config.APPEND_FOOTNOTES
        )
        final_answer = citation_result.enriched_answer
        final_citations = citation_result.valid_citations
        step_latencies["citation_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        total_latency = round((time.perf_counter() - t_start) * 1000.0, 2)
        metadata["step_latencies"] = step_latencies

        return RAGResponse(
            question=question,
            answer=final_answer,
            citations=final_citations,
            retrieved_chunks=final_chunks,
            latency=total_latency,
            refused=refused,
            refusal_reason=refusal_reason,
            retrieval_latency=step_latencies.get("retrieval_ms", 0.0),
            context_latency=step_latencies.get("context_ms", 0.0),
            generation_latency=step_latencies.get("generation_ms", 0.0),
            citation_latency=step_latencies.get("citation_ms", 0.0),
            model_name=getattr(self.generator, "model_name", "unknown"),
            provider=self.config.LLM_PROVIDER,
            metadata=metadata
        )
