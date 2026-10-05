"""
CRAG Knowledge Recomposer.
Tái lập ngữ cảnh tinh lọc từ các Knowledge Strips sống sót sau bước lọc.
"""

from typing import Any, Dict, List, Optional
from RAG.retriever.schema import RetrievedChunk
from CRAG.config import crag_config
from CRAG.refinement.schema import KnowledgeStrip, RefinedContext, RefinedDocument
from CRAG.refinement.stripper import KnowledgeStripper


class KnowledgeRecomposer:
    """
    Bộ tái cấu trúc ngữ cảnh tinh lọc:
    - Thu nhận các chunk đã được lọc bỏ nhiễu.
    - Định dạng chuẩn hóa [SOURCE N] tương thích với hệ thống sinh Generator và Citation.
    - Kiểm soát độ dài ngữ cảnh tối đa (MAX_REFINED_CONTEXT_CHARS).
    - Đo lường hệ số nén ngữ cảnh (Compression ratio) giúp chứng minh giá trị tinh lọc.
    """

    def __init__(
        self,
        stripper: Optional[KnowledgeStripper] = None,
        max_context_chars: int = None,
    ):
        self.stripper = stripper or KnowledgeStripper()
        self.max_context_chars = (
            max_context_chars
            if max_context_chars is not None
            else crag_config.MAX_REFINED_CONTEXT_CHARS
        )

    def recompose(
        self,
        chunks: List[RetrievedChunk],
        query: str,
        external_snippets: Optional[List[Dict[str, str]]] = None,
    ) -> RefinedContext:
        """
        Thực hiện toàn bộ quy trình: Bóc tách -> Lọc nhiễu -> Tái cấu trúc thành RefinedContext.
        """
        if not chunks and not external_snippets:
            return RefinedContext(
                documents=[],
                raw_context_text="",
                original_char_count=0,
                refined_char_count=0,
                compression_ratio=0.0,
                total_strips_retained=0,
                total_strips_discarded=0,
            )

        refined_docs: List[RefinedDocument] = []
        original_total_chars = 0
        total_retained = 0
        total_discarded = 0

        # 1. Tinh lọc từng chunk nội bộ
        for idx, chunk in enumerate(chunks, start=1):
            original_total_chars += len(chunk.content)
            refined_doc = self.stripper.refine_chunk(
                chunk=chunk, query=query, source_index=idx
            )
            refined_docs.append(refined_doc)
            total_retained += refined_doc.retained_strips_count
            total_discarded += refined_doc.discarded_strips_count

        # 2. Xây dựng văn bản có cấu trúc [SOURCE N]
        context_blocks: List[str] = []
        current_len = 0

        for doc in refined_docs:
            if not doc.refined_content.strip():
                continue

            meta = doc.metadata or {}
            doc_title = meta.get("document_title") or meta.get("document_id") or "Văn bản pháp luật"
            doc_number = meta.get("document_number") or ""
            art_num = meta.get("article_number") or ""
            art_title = meta.get("article_title") or ""

            header_lines = [f"[SOURCE {doc.source_index}]"]
            if doc_title:
                header_lines.append(f"Document: {doc_title}")
            if doc_number:
                header_lines.append(f"Document Number: {doc_number}")
            if art_num:
                header_lines.append(f"Article: {art_num}")
            if art_title:
                header_lines.append(f"Article Title: {art_title}")

            header_text = "\n".join(header_lines)
            block = f"{header_text}\nContent:\n{doc.refined_content}\n"

            # Kiểm soát độ dài ngữ cảnh
            if current_len + len(block) > self.max_context_chars:
                # Nếu vượt quá, cắt gọn và dừng
                allowed_space = self.max_context_chars - current_len
                if allowed_space > 200:
                    context_blocks.append(block[:allowed_space] + "\n...[TRUNCATED]")
                break

            context_blocks.append(block)
            current_len += len(block)

        # 3. Ghép tri thức từ Web Search (nếu có kích hoạt)
        if external_snippets:
            web_start_idx = len(refined_docs) + 1
            for ext_idx, ext in enumerate(external_snippets, start=web_start_idx):
                title = ext.get("title", "Tài liệu tra cứu ngoài")
                snippet = ext.get("snippet", "")
                url = ext.get("url", "")

                ext_block = (
                    f"[SOURCE {ext_idx}]\n"
                    f"Document: Tra cứu ngoài (Web Knowledge)\n"
                    f"Title: {title}\n"
                    f"Reference: {url}\n"
                    f"Content:\n{snippet}\n"
                )
                if current_len + len(ext_block) <= self.max_context_chars:
                    context_blocks.append(ext_block)
                    current_len += len(ext_block)

        raw_context = "\n".join(context_blocks).strip()
        refined_total_chars = len(raw_context)

        # Tính tỷ lệ giảm nhiễu (noise reduction ratio / compression ratio)
        compression_ratio = 0.0
        if original_total_chars > 0:
            compression_ratio = round(
                max(0.0, 1.0 - (refined_total_chars / original_total_chars)), 4
            )

        return RefinedContext(
            documents=refined_docs,
            raw_context_text=raw_context,
            original_char_count=original_total_chars,
            refined_char_count=refined_total_chars,
            compression_ratio=compression_ratio,
            total_strips_retained=total_retained,
            total_strips_discarded=total_discarded,
        )
