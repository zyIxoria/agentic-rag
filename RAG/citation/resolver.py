"""resolver.py - Bộ ánh xạ và chuẩn hóa trích dẫn pháp lý (Legal Citation Resolver).

Chuyển đổi các nhãn nguồn nội bộ [SOURCE N] thành trích dẫn pháp lý thực tế:
- Ánh xạ 100% từ metadata thực của retrieved chunks / citation_mapping.
- Tuyệt đối không cho phép LLM bịa đặt số hiệu, điều khoản hay URL.
- REJECT INVALID CITATION: Loại bỏ hoàn toàn các nguồn không tồn tại (VD: [SOURCE 99]).
- Hỗ trợ thay thế trực tiếp trong văn bản (in-text replacement) và sinh danh mục tham chiếu (footnotes).
"""

from __future__ import annotations
import re
import logging
from typing import Dict, Any, List, Optional, Set, Tuple

from RAG.citation.schema import LegalCitation, CitationResolutionResult

logger = logging.getLogger(__name__)

# Regex tìm kiếm thẻ [SOURCE N] hoặc SOURCE N
SOURCE_TAG_REGEX = re.compile(r"\[?\bSOURCE\s+(\d+)\b\]?", re.IGNORECASE)


def format_legal_citation(meta: Dict[str, Any]) -> str:
    """Tạo chuỗi trích dẫn pháp lý chuẩn mực từ metadata thực tế.
    
    Quy tắc cấu trúc:
    - Cơ sở: [{document_title}, {article_number}]
    - Nếu có Khoản: [{document_title}, {article_number}, {clause_number}]
    - Nếu có Điểm: [{document_title}, {article_number}, {clause_number}, {point_number}]
    
    Args:
        meta: Từ điển chứa siêu dữ liệu của chunk.
        
    Returns:
        Chuỗi trích dẫn pháp lý chuẩn (VD: '[Bộ luật Lao động 2019, Điều 125]').
    """
    doc_title = meta.get("document_title") or meta.get("parent_document") or "Văn bản pháp luật"
    doc_title = doc_title.strip()

    art = meta.get("article_number")
    clause = meta.get("clause_number")
    point = meta.get("point_number")

    parts = [doc_title]
    if art:
        art_clean = str(art).strip()
        if not art_clean.lower().startswith("điều"):
            art_clean = f"Điều {art_clean}"
        parts.append(art_clean)

    if clause:
        clause_clean = str(clause).strip()
        if not clause_clean.lower().startswith("khoản"):
            clause_clean = f"Khoản {clause_clean}"
        parts.append(clause_clean)

    if point:
        point_clean = str(point).strip()
        if not point_clean.lower().startswith("điểm"):
            point_clean = f"Điểm {point_clean}"
        parts.append(point_clean)

    return f"[{', '.join(parts)}]"


class CitationResolver:
    """Lớp xử lý ánh xạ, xác thực và chuẩn hóa trích dẫn pháp lý."""

    def __init__(
        self,
        replace_in_text: bool = True,
        append_footnotes: bool = True,
        reject_invalid: bool = True
    ):
        """Khởi tạo CitationResolver.
        
        Args:
            replace_in_text: Có thay thế thẻ [SOURCE N] trong nội dung câu trả lời bằng trích dẫn pháp lý hay không.
            append_footnotes: Có đính kèm danh mục tham chiếu (Footnotes/References) ở cuối câu trả lời hay không.
            reject_invalid: Có loại bỏ hoàn toàn các thẻ trích dẫn không hợp lệ hay không.
        """
        self.replace_in_text = replace_in_text
        self.append_footnotes = append_footnotes
        self.reject_invalid = reject_invalid

    def resolve_citations(
        self,
        answer: str,
        citation_mapping: Dict[str, Dict[str, Any]],
        citations_list: Optional[List[str]] = None,
        replace_in_text: Optional[bool] = None,
        append_footnotes: Optional[bool] = None
    ) -> CitationResolutionResult:
        """Phân giải toàn bộ trích dẫn trong câu trả lời từ bản đồ citation_mapping.
        
        Args:
            answer: Câu trả lời chứa thẻ [SOURCE N].
            citation_mapping: Bản đồ ánh xạ từ '[SOURCE N]' sang metadata pháp lý.
            citations_list: Danh sách các nhãn nguồn từ generator (tùy chọn).
            replace_in_text: Ghi đè tùy chọn thay thế in-text.
            append_footnotes: Ghi đè tùy chọn đính kèm footnotes.
            
        Returns:
            CitationResolutionResult chứa văn bản đã làm giàu và danh sách trích dẫn hợp lệ.
        """
        do_replace = self.replace_in_text if replace_in_text is None else replace_in_text
        do_footnotes = self.append_footnotes if append_footnotes is None else append_footnotes

        # Chuẩn hóa citation_mapping để tra cứu dễ dàng cả hai dạng "[SOURCE N]" và "SOURCE N"
        normalized_map: Dict[str, Dict[str, Any]] = {}
        for k, v in citation_mapping.items():
            k_clean = k.strip().upper()
            normalized_map[k_clean] = v
            # Cũng hỗ trợ không có ngoặc vuông
            no_brackets = k_clean.strip("[]")
            normalized_map[no_brackets] = v

        # 1. Thu thập tất cả các nhãn nguồn xuất hiện trong answer và citations_list
        found_tags: List[str] = []
        seen_tags: Set[str] = set()

        for m in SOURCE_TAG_REGEX.finditer(answer):
            num = m.group(1)
            full_tag = f"[SOURCE {num}]"
            if full_tag not in seen_tags:
                seen_tags.add(full_tag)
                found_tags.append(full_tag)

        if citations_list:
            for c in citations_list:
                m = re.search(r"SOURCE\s+(\d+)", str(c), re.IGNORECASE)
                if m:
                    num = m.group(1)
                    full_tag = f"[SOURCE {num}]"
                    if full_tag not in seen_tags:
                        seen_tags.add(full_tag)
                        found_tags.append(full_tag)

        valid_citations: List[LegalCitation] = []
        invalid_citations: List[str] = []
        replacement_map: Dict[str, str] = {}

        # 2. Xác thực và ánh xạ từng thẻ nguồn
        for tag in found_tags:
            meta = normalized_map.get(tag) or normalized_map.get(tag.strip("[]"))
            m = re.search(r"\d+", tag)
            num = int(m.group(0)) if m else None

            if meta:
                # Trích dẫn HỢP LỆ -> Ánh xạ từ metadata thật
                legal_str = format_legal_citation(meta)
                citation_obj = LegalCitation(
                    source_id=tag,
                    source_number=num,
                    chunk_id=meta.get("chunk_id"),
                    document_title=meta.get("document_title") or meta.get("parent_document") or "Văn bản pháp luật",
                    document_number=meta.get("document_number"),
                    article_number=meta.get("article_number"),
                    article_title=meta.get("article_title"),
                    clause_number=meta.get("clause_number"),
                    point_number=meta.get("point_number"),
                    source_url=meta.get("source_url"),
                    formatted_citation=legal_str,
                    is_valid=True,
                    validation_error=None
                )
                valid_citations.append(citation_obj)
                replacement_map[tag] = legal_str
            else:
                # Trích dẫn KHÔNG HỢP LỆ (REJECT INVALID CITATION)
                logger.warning(
                    "Phát hiện trích dẫn không hợp lệ: '%s' (không tồn tại trong retrieved metadata). REJECT INVALID CITATION.",
                    tag
                )
                invalid_citations.append(tag)
                # Khi reject, loại bỏ thẻ khỏi văn bản
                replacement_map[tag] = ""

        # 3. Tạo văn bản làm giàu (Enriched Answer)
        enriched_text = answer
        if do_replace:
            # Thay thế theo thứ tự độ dài giảm dần để tránh conflict chuỗi con
            sorted_tags = sorted(replacement_map.keys(), key=len, reverse=True)
            for tag in sorted_tags:
                repl = replacement_map[tag]
                # Regex thay thế cả dạng [SOURCE N] và SOURCE N
                tag_num = re.search(r"\d+", tag).group(0)
                pattern = re.compile(rf"\[?SOURCE\s+{tag_num}\]?", re.IGNORECASE)
                enriched_text = pattern.sub(repl, enriched_text)

            # Dọn dẹp khoảng trắng kép hoặc dấu phẩy cô đơn sau khi loại bỏ invalid citation
            enriched_text = re.sub(r"[ \t]{2,}", " ", enriched_text)
            enriched_text = re.sub(r"\s+([,;.])", r"\1", enriched_text).strip()

        # 4. Tạo danh mục tham chiếu (Footnotes / References)
        footnotes: List[str] = []
        if valid_citations:
            for idx, cit in enumerate(valid_citations, start=1):
                fn_parts = [f"{cit.formatted_citation}"]
                if cit.article_title:
                    fn_parts.append(f"({cit.article_title})")
                if cit.source_url:
                    fn_parts.append(f"- URL: {cit.source_url}")
                footnotes.append(f"[{idx}] {' '.join(fn_parts)}")

        if do_footnotes and footnotes and not answer.startswith("Không tìm thấy đủ căn cứ pháp lý"):
            enriched_text = (
                f"{enriched_text}\n\n"
                f"### Căn Cứ Pháp Lý Tham Chiếu:\n" + "\n".join(footnotes)
            )

        return CitationResolutionResult(
            original_answer=answer,
            enriched_answer=enriched_text,
            valid_citations=valid_citations,
            invalid_citations=invalid_citations,
            has_invalid_citations=len(invalid_citations) > 0,
            citations_count=len(valid_citations),
            footnotes=footnotes
        )
