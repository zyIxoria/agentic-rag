"""
Adaptive RAG Multi-Hop Synthesizer.
Tổng hợp ngữ cảnh và điều phối sinh câu trả lời cho các câu hỏi đa chặng sau phân rã.
"""

from __future__ import annotations
import time
from typing import Any, Dict, List, Optional, Tuple

from RAG.retriever.schema import RetrievedChunk
from RAG.generator.base import BaseLegalGenerator
from RAG.citation.resolver import CitationResolver
from Adaptive_RAG.decomposition.schema import DecompositionPlan
from Adaptive_RAG.orchestration.schema import SubQueryExecutionRecord


class MultiHopSynthesizer:
    """
    Bộ tổng hợp tri thức đa chặng:
    1. Loại bỏ trùng lặp (Deduplicate) chunks giữa các sub-queries, bảo toàn điểm số tối đa.
    2. Sắp xếp và phân nhóm dải tri thức theo từng khía cạnh trong kế hoạch phân rã.
    3. Định dạng context có cấu trúc chuẩn [SOURCE N] kèm chỉ dẫn tổng hợp chuyên sâu.
    4. Sinh câu trả lời bảo thủ toàn diện và ánh xạ trích dẫn minh bạch.
    """

    def __init__(
        self,
        generator: BaseLegalGenerator,
        citation_resolver: CitationResolver,
    ):
        self.generator = generator
        self.citation_resolver = citation_resolver

    def deduplicate_chunks(
        self, sub_records: List[SubQueryExecutionRecord]
    ) -> List[RetrievedChunk]:
        """Loại bỏ trùng lặp chunks giữa các lượt tìm kiếm của sub-queries."""
        unique_chunks: Dict[str, RetrievedChunk] = {}

        for rec in sub_records:
            for chunk in rec.retrieved_chunks:
                cid = chunk.chunk_id
                if cid not in unique_chunks:
                    unique_chunks[cid] = chunk
                else:
                    # Giữ lại chunk có score cao hơn
                    if chunk.score > unique_chunks[cid].score:
                        unique_chunks[cid] = chunk

        # Sắp xếp giảm dần theo điểm tin cậy
        sorted_chunks = sorted(
            unique_chunks.values(), key=lambda c: c.score, reverse=True
        )
        return sorted_chunks

    def synthesize(
        self,
        original_query: str,
        plan: DecompositionPlan,
        sub_records: List[SubQueryExecutionRecord],
        max_context_chars: int = 4000,
    ) -> Tuple[str, List[Any], List[RetrievedChunk], float]:
        """
        Thực hiện tổng hợp câu trả lời từ các kết quả thực thi sub-queries.
        """
        t_start = time.perf_counter()

        # 1. Thu thập và khử trùng lặp chunks
        all_unique_chunks = self.deduplicate_chunks(sub_records)

        if not all_unique_chunks:
            return (
                "Hệ thống không tìm thấy đủ căn cứ pháp lý từ các quy định hiện hành để trả lời câu hỏi.",
                [],
                [],
                (time.perf_counter() - t_start) * 1000.0,
            )

        # 2. Xây dựng context tổng hợp có phân vùng theo sub-query
        context_blocks = []
        citation_mapping: Dict[str, Dict[str, Any]] = {}
        curr_source_idx = 1
        current_len = 0

        # Header chỉ dẫn tổng hợp
        context_blocks.append(
            f"=== YÊU CẦU TỔNG HỢP: {plan.synthesis_instruction} ==="
        )

        for rec in sub_records:
            sub_q = rec.sub_query
            context_blocks.append(f"\n--- [Khía cạnh tra cứu: {sub_q.text}] ---")

            for chunk in rec.retrieved_chunks:
                source_key = f"SOURCE {curr_source_idx}"
                meta = chunk.metadata or {}
                doc_title = (
                    meta.get("document_title")
                    or meta.get("document_id")
                    or "Văn bản pháp luật"
                )
                doc_num = meta.get("document_number") or ""
                art_num = meta.get("article_number") or ""
                art_title = meta.get("article_title") or ""

                block_lines = [
                    f"[{source_key}]",
                    f"Document: {doc_title}",
                ]
                if doc_num:
                    block_lines.append(f"Document Number: {doc_num}")
                if art_num:
                    block_lines.append(f"Article: {art_num}")
                if art_title:
                    block_lines.append(f"Article Title: {art_title}")
                block_lines.append("Content:")
                block_lines.append(chunk.content)

                block_str = "\n".join(block_lines) + "\n"

                if current_len + len(block_str) > max_context_chars:
                    break

                context_blocks.append(block_str)
                citation_mapping[source_key] = meta
                current_len += len(block_str)
                curr_source_idx += 1

        full_context_text = "\n".join(context_blocks)

        # 3. Gọi LLM sinh câu trả lời tổng hợp
        gen_result = self.generator.generate(
            question=original_query,
            context=full_context_text,
            temperature=0.0,
        )

        # 4. Giải nghĩa trích dẫn pháp lý
        cit_result = self.citation_resolver.resolve_citations(
            answer=gen_result.answer,
            citation_mapping=citation_mapping,
            citations_list=gen_result.citations,
            replace_in_text=True,
            append_footnotes=True,
        )

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        return (
            cit_result.enriched_answer,
            cit_result.valid_citations,
            all_unique_chunks,
            elapsed_ms,
        )
