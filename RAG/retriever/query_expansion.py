"""query_expansion.py - Module viết lại và mở rộng truy vấn pháp lý (Legal Query Rewriter & Expansion).

Giải quyết triệt để vấn đề Lexical/Semantic Gap giữa ngôn ngữ giao tiếp đời sống và ngôn ngữ văn bản pháp luật:
- "nghỉ việc" -> "chấm dứt hợp đồng lao động", "thôi việc", "mất việc làm".
- "trợ cấp" -> "trợ cấp thôi việc", "trợ cấp mất việc làm", "trợ cấp thất nghiệp".
- Nhận diện các câu hỏi mơ hồ (Under-specified / Ambiguous queries) thiếu dữ kiện để phân nhánh chế độ.
- Bảo tồn nguyên vẹn câu hỏi gốc trong metadata.
- Hỗ trợ cơ chế dự phòng an toàn (Fallback) và cờ bật/tắt (Toggle).
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class ExpandedQuery:
    """Cấu trúc dữ liệu kết quả sau khi viết lại và mở rộng truy vấn."""
    original_query: str
    rewritten_query: str
    search_query: str
    is_ambiguous: bool
    ambiguity_types: List[str] = field(default_factory=list)
    clarification_note: Optional[str] = None
    expanded_terms: List[str] = field(default_factory=list)
    identified_articles: List[str] = field(default_factory=list)
    identified_documents: List[str] = field(default_factory=list)


class LegalQueryExpander:
    """Bộ phân tích và mở rộng câu hỏi ngôn ngữ tự nhiên sang truy vấn pháp lý chuyên ngành."""

    # Từ điển ánh xạ từ ngữ đời sống -> Thuật ngữ pháp lý chuẩn tắc
    COLLOQUIAL_LEGAL_MAPPING = {
        "nghỉ việc": [
            "chấm dứt hợp đồng lao động",
            "thôi việc",
            "mất việc làm",
            "nghỉ việc"
        ],
        "xin nghỉ việc": [
            "người lao động đơn phương chấm dứt hợp đồng lao động",
            "chấm dứt hợp đồng lao động",
            "thôi việc"
        ],
        "bị đuổi việc": [
            "kỷ luật sa thải",
            "người sử dụng lao động đơn phương chấm dứt hợp đồng lao động",
            "chấm dứt hợp đồng lao động"
        ],
        "sa thải": [
            "xử lý kỷ luật sa thải",
            "Điều 125 Bộ luật Lao động",
            "kỷ luật lao động"
        ],
        "trợ cấp": [
            "trợ cấp thôi việc",
            "trợ cấp mất việc làm",
            "trợ cấp thất nghiệp",
            "Điều 46",
            "Điều 47"
        ],
        "tiền thôi việc": [
            "trợ cấp thôi việc",
            "Điều 46 Bộ luật Lao động",
            "Điều 8 Nghị định 145"
        ],
        "tiền mất việc": [
            "trợ cấp mất việc làm",
            "Điều 47 Bộ luật Lao động",
            "Điều 8 Nghị định 145"
        ],
        "bảo hiểm thất nghiệp": [
            "trợ cấp thất nghiệp",
            "Luật Việc làm",
            "bảo hiểm xã hội"
        ],
        "tự ý bỏ việc": [
            "tự ý bỏ việc mà không có lý do chính đáng",
            "đơn phương chấm dứt hợp đồng lao động trái pháp luật",
            "không được hưởng trợ cấp thôi việc"
        ],
        "làm thêm giờ": [
            "tiền lương làm thêm giờ",
            "thời giờ làm việc",
            "Điều 98 Bộ luật Lao động"
        ],
        "tăng ca": [
            "làm thêm giờ",
            "tiền lương làm thêm giờ",
            "Điều 98 Bộ luật Lao động",
            "Điều 107"
        ],
        "thử việc": [
            "thời gian thử việc",
            "hợp đồng thử việc",
            "tiền lương thử việc",
            "Điều 25 Điều 26 Điều 27"
        ]
    }

    # Tiền tố và hậu tố giao tiếp thông tục cần làm sạch
    CONVERSATIONAL_PREFIXES = [
        r"^cho\s+(tôi|em|mình|chúng tôi)\s+(hỏi|biết)",
        r"^xin\s+(hỏi|cho biết)",
        r"^làm\s+ơn\s+cho\s+hỏi",
        r"^tôi\s+muốn\s+(hỏi|biết|tìm hiểu)",
        r"^theo\s+luật\s+thì",
        r"^dạ\s+cho\s+em\s+hỏi",
        r"^luật\s+sư\s+cho\s+hỏi",
    ]

    CONVERSATIONAL_SUFFIXES = [
        r"như\s+vậy\s+có\s+(đúng|hợp pháp|phạm luật)\s+không\??$",
        r"thì\s+có\s+được\s+(nhận\s+trợ\s+cấp|hưởng\s+tiền|hưởng\s+trợ\s+cấp)\s+không\??$",
        r"thì\s+xử\s+lý\s+thế\s+nào\??$",
        r"có\s+được\s+không\??$",
        r"được\s+quy\s+định\s+như\s+thế\s+nào\??$",
        r"phải\s+làm\s+sao\??$",
    ]

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def _extract_legal_entities(self, query: str) -> Tuple[List[str], List[str]]:
        """Bóc tách các số hiệu Điều luật và Văn bản cụ thể nếu có trong câu hỏi."""
        articles = re.findall(r"điều\s*(\d+)", query, re.IGNORECASE)
        articles = [f"Điều {a}" for a in articles]

        documents = []
        doc_patterns = [
            r"bộ\s+luật\s+lao\s+động(?:\s+2019)?",
            r"nghị\s+định\s+(\d+/\d+(?:/nđ-cp)?)",
            r"thông\s+tư\s+(\d+/\d+(?:/tt-blđtbxh)?)",
            r"luật\s+việc\s+làm",
            r"luật\s+bảo\s+hiểm\s+xã\s+hội"
        ]
        for pat in doc_patterns:
            matches = re.findall(pat, query, re.IGNORECASE)
            for m in matches:
                documents.append(m if isinstance(m, str) else str(m))

        return list(set(articles)), list(set(documents))

    def _check_ambiguity(self, query: str) -> Tuple[bool, List[str], Optional[str]]:
        """Kiểm tra xem câu hỏi có thuộc nhóm mơ hồ thiếu dữ kiện phân loại trợ cấp hay không."""
        q_lower = query.lower()
        has_nghi_viec = "nghỉ việc" in q_lower or "thôi việc" in q_lower or "chấm dứt" in q_lower
        has_tro_cap = "trợ cấp" in q_lower or "tiền" in q_lower

        # Nếu hỏi chung chung về "nghỉ việc có được nhận trợ cấp không" mà không nêu rõ lý do
        if has_nghi_viec and has_tro_cap:
            # Kiểm tra xem có nói rõ lý do không: sa thải, tái cơ cấu, thỏa thuận, hết hạn, bỏ việc
            has_specific_reason = any(r in q_lower for r in [
                "hết hạn", "tái cơ cấu", "sáp nhập", "giải thể", "sa thải",
                "bỏ việc", "thỏa thuận", "thai sản", "ốm đau", "đơn phương"
            ])
            has_specific_allowance = any(a in q_lower for a in [
                "thôi việc", "mất việc", "thất nghiệp"
            ])

            if not has_specific_reason and not has_specific_allowance:
                ambiguity_types = [
                    "Trợ cấp thôi việc (Điều 46 Bộ luật Lao động 2019)",
                    "Trợ cấp mất việc làm (Điều 47 Bộ luật Lao động 2019)",
                    "Trợ cấp thất nghiệp (Luật Việc làm / Quỹ BHXH)"
                ]
                clarification = (
                    "Câu hỏi của bạn chưa cung cấp rõ lý do nghỉ việc và thời gian tham gia bảo hiểm thất nghiệp. "
                    "Theo pháp luật lao động Việt Nam, khi nghỉ việc bạn có thể thuộc 1 trong 3 chế độ trợ cấp độc lập: "
                    "(1) Trợ cấp thôi việc, (2) Trợ cấp mất việc làm, hoặc (3) Trợ cấp thất nghiệp. "
                    "Lưu ý: Nếu tự ý bỏ việc từ 05 ngày làm việc liên tục trở lên mà không có lý do chính đáng thì không được nhận trợ cấp thôi việc."
                )
                return True, ambiguity_types, clarification

        return False, [], None

    def expand(self, query: str) -> ExpandedQuery:
        """Thực hiện viết lại và mở rộng truy vấn câu hỏi."""
        if not self.enabled or not query or not query.strip():
            # Fallback nguyên bản nếu tắt module hoặc chuỗi rỗng
            return ExpandedQuery(
                original_query=query,
                rewritten_query=query,
                search_query=query,
                is_ambiguous=False
            )

        original_query = query.strip()
        q_lower = original_query.lower()

        # 1. Kiểm tra tính mơ hồ
        is_ambiguous, ambiguity_types, clarification = self._check_ambiguity(original_query)

        # 2. Bóc tách thực thể
        articles, documents = self._extract_legal_entities(original_query)

        # 3. Làm sạch tiền tố và hậu tố giao tiếp để trích xuất core keywords
        cleaned = original_query
        for pat in self.CONVERSATIONAL_PREFIXES:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()

        # 4. Tìm kiếm các thuật ngữ pháp lý tương đương
        expanded_terms = []
        for colloquial, legal_terms in self.COLLOQUIAL_LEGAL_MAPPING.items():
            if colloquial in q_lower:
                expanded_terms.extend(legal_terms)

        # 5. Xây dựng câu truy vấn tìm kiếm pháp lý tối ưu (Search Query)
        # Kết hợp các từ khóa cốt lõi + thuật ngữ mở rộng
        search_components = []
        
        # Nếu có thực thể cụ thể, ưu tiên đưa lên đầu
        if articles:
            search_components.extend(articles)
        if documents:
            search_components.extend(documents)

        # Đưa các thuật ngữ mở rộng vào truy vấn
        if expanded_terms:
            search_components.extend(expanded_terms[:6])

        # Đưa nội dung đã làm sạch
        tokens = re.findall(r"\w+", cleaned)
        meaningful_tokens = [t for t in tokens if len(t) >= 2 and t.lower() not in {"tôi", "cho", "hỏi", "được", "không", "thì", "có"}]
        search_components.extend(meaningful_tokens[:5])

        # Đảm bảo context pháp luật lao động
        if not any("lao động" in sc.lower() for sc in search_components):
            search_components.append("Bộ luật Lao động")

        # Loại bỏ trùng lặp giữ nguyên thứ tự
        seen = set()
        final_terms = []
        for term in search_components:
            tl = term.lower().strip()
            if tl and tl not in seen:
                seen.add(tl)
                final_terms.append(term.strip())

        search_query_str = " ".join(final_terms)
        rewritten_query_str = f"{cleaned} ({', '.join(expanded_terms[:3])})" if expanded_terms else cleaned

        return ExpandedQuery(
            original_query=original_query,
            rewritten_query=rewritten_query_str,
            search_query=search_query_str,
            is_ambiguous=is_ambiguous,
            ambiguity_types=ambiguity_types,
            clarification_note=clarification,
            expanded_terms=expanded_terms,
            identified_articles=articles,
            identified_documents=documents
        )
