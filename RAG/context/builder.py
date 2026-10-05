"""builder.py - Trình đóng gói ngữ cảnh pháp lý (Legal Context Builder).

Tuân thủ nghiêm ngặt các nguyên tắc của TASK RAG-04:
- Định dạng nguồn rõ ràng: [SOURCE 1], [SOURCE 2], ...
- Giữ nguyên vẹn 100% nội dung đoạn luật (Tuyệt đối không rewrite, không summarize).
- Bảo toàn thứ tự thu hồi (Retrieval Rank Order) và điểm tương đồng nội bộ.
- Khử trùng lặp ID (Deduplication): Giữ lại bản ghi đầu tiên khi cùng chunk_id xuất hiện nhiều lần.
- Kiểm soát ngân sách token (MAX_CONTEXT_TOKENS): Cắt bỏ nguyên vẹn theo thứ hạng, không cắt ngang giữa chừng.
- Xây dựng bản đồ trích dẫn (citation mapping) để LLM và citation formatter trích dẫn chính xác.
"""

from __future__ import annotations
import math
import logging
from typing import List, Dict, Any, Optional, Set

from RAG.retriever.schema import RetrievedChunk
from RAG.context.schema import ContextSource, BuildContextResult
from RAG.context.config import ContextConfig, default_context_config

logger = logging.getLogger(__name__)


def count_estimated_tokens(text: str, token_multiplier: float = 1.3) -> int:
    """Ước tính số token cho chuỗi văn bản dựa trên số từ tiếng Việt và hệ số subword."""
    if not text or not text.strip():
        return 0
    words = len(text.strip().split())
    return int(math.ceil(words * token_multiplier))


class LegalContextBuilder:
    """Lớp đóng gói danh sách RetrievedChunk thành cấu trúc Prompt Context cho LLM."""

    def __init__(self, config: Optional[ContextConfig] = None):
        """Khởi tạo LegalContextBuilder.
        
        Args:
            config: Cấu hình ContextConfig (nếu None sẽ dùng cấu hình mặc định).
        """
        self.config = config or default_context_config

    def format_source_block(self, source_number: int, chunk: RetrievedChunk) -> str:
        """Định dạng một đoạn văn bản pháp lý thành khối nguồn có cấu trúc rõ ràng.
        
        Mẫu cấu trúc:
        [SOURCE X]
        Document: <document_title>
        Document Number: <document_number>
        Article: <article_number>
        Article Title: <article_title>
        Clause: <clause_number>
        Point: <point_number>
        Content:
        <Toàn văn chunk.content nguyên bản>
        """
        meta = chunk.metadata or {}
        lines: List[str] = [f"[SOURCE {source_number}]"]

        # 1. Tên văn bản (Bắt buộc)
        doc_title = meta.get("document_title") or meta.get("parent_document") or "Văn bản pháp luật"
        lines.append(f"Document: {doc_title}")

        # 2. Số hiệu văn bản (nếu có)
        doc_number = meta.get("document_number")
        if doc_number and str(doc_number).strip():
            lines.append(f"Document Number: {doc_number}")

        # 3. Điều luật & Tiêu đề Điều (nếu có)
        art_number = meta.get("article_number")
        if art_number and str(art_number).strip():
            lines.append(f"Article: {art_number}")

        art_title = meta.get("article_title")
        if art_title and str(art_title).strip():
            lines.append(f"Article Title: {art_title}")

        # 4. Khoản & Điểm (nếu có)
        clause_num = meta.get("clause_number")
        if clause_num and str(clause_num).strip():
            lines.append(f"Clause: {clause_num}")

        point_num = meta.get("point_number")
        if point_num and str(point_num).strip():
            lines.append(f"Point: {point_num}")

        # 5. Nội dung nguyên bản không chỉnh sửa
        lines.append("Content:")
        lines.append(chunk.content.strip())

        return "\n".join(lines)

    def build_context(
        self,
        retrieved_chunks: List[RetrievedChunk],
        max_tokens: Optional[int] = None,
    ) -> BuildContextResult:
        """Chuyển đổi danh sách RetrievedChunk thành BuildContextResult với kiểm soát ngân sách token.
        
        Args:
            retrieved_chunks: Danh sách các đoạn luật thu hồi từ RAG-03.
            max_tokens: Ngưỡng trần token tùy chọn (nếu None sẽ dùng self.config.MAX_CONTEXT_TOKENS).
            
        Returns:
            BuildContextResult: Đối tượng chứa văn bản context, danh sách nguồn, và dropped sources.
        """
        effective_max_tokens = max_tokens if max_tokens is not None else self.config.MAX_CONTEXT_TOKENS
        if effective_max_tokens <= 0:
            raise ValueError(f"max_tokens phải là số nguyên dương > 0, nhận được: {effective_max_tokens}")

        # 1. Xử lý trường hợp mảng thu hồi rỗng
        if not retrieved_chunks:
            return BuildContextResult(
                context_text=self.config.EMPTY_CONTEXT_MESSAGE,
                sources=[],
                dropped_sources=[],
                total_tokens=count_estimated_tokens(self.config.EMPTY_CONTEXT_MESSAGE, self.config.TOKEN_MULTIPLIER),
                max_context_tokens=effective_max_tokens,
                num_retrieved=0,
                num_included=0,
                num_dropped=0,
                citation_mapping={},
            )

        # 2. Khử trùng lặp theo chunk_id (Keep first occurrence - bảo toàn thứ tự rank cao nhất)
        unique_chunks: List[RetrievedChunk] = []
        seen_ids: Set[str] = set()

        for chunk in retrieved_chunks:
            if chunk.chunk_id not in seen_ids:
                seen_ids.add(chunk.chunk_id)
                unique_chunks.append(chunk)
            else:
                logger.debug(f"Phát hiện chunk_id trùng lặp '{chunk.chunk_id}'. Giữ lại bản ghi đầu tiên.")

        # 3. Đóng gói tuần tự từng nguồn kèm kiểm soát ngân sách token
        included_sources: List[ContextSource] = []
        dropped_sources: List[RetrievedChunk] = []
        formatted_blocks: List[str] = []
        citation_mapping: Dict[str, Dict[str, Any]] = {}

        current_token_count = 0
        separator_tokens = count_estimated_tokens(self.config.SOURCE_SEPARATOR, self.config.TOKEN_MULTIPLIER)

        budget_exceeded = False

        for idx, chunk in enumerate(unique_chunks, start=1):
            if budget_exceeded:
                # Toàn bộ các chunk phía sau bị cắt bỏ
                dropped_sources.append(chunk)
                continue

            source_id = f"[SOURCE {idx}]"
            source_block_text = self.format_source_block(idx, chunk)
            block_tokens = count_estimated_tokens(source_block_text, self.config.TOKEN_MULTIPLIER)

            # Tính toán token nếu bổ sung khối nguồn này
            additional_tokens = block_tokens if not formatted_blocks else (separator_tokens + block_tokens)

            if current_token_count + additional_tokens <= effective_max_tokens:
                # Chấp nhận đưa vào context
                formatted_blocks.append(source_block_text)
                current_token_count += additional_tokens

                meta = chunk.metadata or {}
                source_obj = ContextSource(
                    source_id=source_id,
                    source_number=idx,
                    chunk_id=chunk.chunk_id,
                    score=chunk.score,
                    rank=chunk.rank,
                    document_title=meta.get("document_title") or meta.get("parent_document") or "Văn bản pháp luật",
                    document_number=meta.get("document_number"),
                    article_number=meta.get("article_number"),
                    article_title=meta.get("article_title"),
                    clause_number=meta.get("clause_number"),
                    point_number=meta.get("point_number"),
                    content=chunk.content,
                    metadata=meta,
                    token_count=block_tokens,
                )
                included_sources.append(source_obj)

                # Lưu vào citation mapping
                citation_mapping[source_id] = {
                    "source_id": source_id,
                    "source_number": idx,
                    "chunk_id": chunk.chunk_id,
                    "document_id": meta.get("document_id"),
                    "document_number": meta.get("document_number"),
                    "document_title": meta.get("document_title"),
                    "document_type": meta.get("document_type"),
                    "chapter_number": meta.get("chapter_number"),
                    "chapter_title": meta.get("chapter_title"),
                    "article_number": meta.get("article_number"),
                    "article_title": meta.get("article_title"),
                    "clause_number": meta.get("clause_number"),
                    "point_number": meta.get("point_number"),
                    "effective_from": meta.get("effective_from"),
                    "legal_status": meta.get("legal_status"),
                    "source_url": meta.get("source_url"),
                    "score": chunk.score,
                    "rank": chunk.rank,
                }
            else:
                # Vượt ngân sách token: Không cắt xén ngang chunk, đánh dấu ngắt và ghi nhận dropped
                budget_exceeded = True
                dropped_sources.append(chunk)
                logger.info(
                    f"Vượt ngưỡng MAX_CONTEXT_TOKENS ({current_token_count} + {additional_tokens} > {effective_max_tokens}). "
                    f"Cắt giảm từ nguồn '{source_id}' ({chunk.chunk_id})."
                )

        # 4. Ghép toàn bộ chuỗi văn bản ngữ cảnh
        if formatted_blocks:
            final_context_text = self.config.SOURCE_SEPARATOR.join(formatted_blocks)
            total_context_tokens = count_estimated_tokens(final_context_text, self.config.TOKEN_MULTIPLIER)
        else:
            final_context_text = self.config.EMPTY_CONTEXT_MESSAGE
            total_context_tokens = count_estimated_tokens(final_context_text, self.config.TOKEN_MULTIPLIER)

        return BuildContextResult(
            context_text=final_context_text,
            sources=included_sources,
            dropped_sources=dropped_sources,
            total_tokens=total_context_tokens,
            max_context_tokens=effective_max_tokens,
            num_retrieved=len(retrieved_chunks),
            num_included=len(included_sources),
            num_dropped=len(dropped_sources),
            citation_mapping=citation_mapping,
        )

    def build_context_str(
        self,
        retrieved_chunks: List[RetrievedChunk],
        max_tokens: Optional[int] = None,
    ) -> str:
        """Tiện ích trả về trực tiếp chuỗi văn bản ngữ cảnh."""
        result = self.build_context(retrieved_chunks, max_tokens=max_tokens)
        return result.context_text
