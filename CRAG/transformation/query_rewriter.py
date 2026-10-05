"""
CRAG Legal Query Rewriter.
Biến đổi câu hỏi tự nhiên dài dòng của người dùng thành từ khóa tìm kiếm pháp lý tối ưu.
"""

import re
from typing import List, Tuple
from CRAG.transformation.schema import TransformedQuery


class LegalQueryRewriter:
    """
    Bộ viết lại truy vấn (Query Rewriter):
    1. Bóc tách và bảo toàn các thực thể pháp lý (Điều luật, Số hiệu Nghị định/Thông tư).
    2. Loại bỏ các từ ngữ hội thoại, kính ngữ, đại từ xưng hô, câu hỏi phụ ("cho em hỏi", "sếp em bắt", "như vậy có đúng không").
    3. Trích xuất các cụm danh từ chủ chốt (Core Legal Entities).
    4. Bổ sung từ khóa neo ngữ cảnh ("pháp luật lao động" / "bộ luật lao động") nếu câu hỏi chưa có định danh.
    """

    CONVERSATIONAL_PREFIXES = [
        r"^cho\s+(tôi|em|mình|chúng tôi)\s+(hỏi|biết)",
        r"^xin\s+(hỏi|cho biết)",
        r"^làm\s+ơn\s+cho\s+hỏi",
        r"^tôi\s+muốn\s+(hỏi|biết|tìm hiểu)",
        r"^theo\s+bạn\s+thì",
        r"^em\s+muốn\s+hỏi",
    ]

    CONVERSATIONAL_SUFFIXES = [
        r"như\s+vậy\s+có\s+(đúng|hợp pháp|phạm luật)\s+không\??$",
        r"thì\s+xử\s+lý\s+thế\s+nào\??$",
        r"có\s+được\s+không\??$",
        r"quy\s+định\s+ở\s+đâu\??$",
        r"được\s+quy\s+định\s+như\s+thế\s+nào\??$",
        r"thì\s+sao\??$",
    ]

    STOPWORDS = {
        "là", "gì", "thế", "nào", "ở", "đâu", "khi", "nào", "bao", "nhiêu",
        "cho", "tôi", "em", "mình", "với", "về", "của", "và", "các", "những",
        "được", "bị", "có", "không", "phải", "thì", "trong", "trường", "hợp",
        "sếp", "công", "ty", "đi", "làm"
    }

    def _extract_legal_entities(self, query: str) -> Tuple[List[str], List[str]]:
        """Trích xuất số điều luật và số hiệu văn bản pháp luật."""
        articles = re.findall(r"điều\s+\d+", query, re.IGNORECASE)
        articles = [a.title() for a in articles]

        documents = []
        doc_matches = re.findall(
            r"(nghị\s+định\s+\d+/\d+(?:/nđ-cp)?|thông\s+tư\s+\d+/\d+(?:/tt-blđtbxh)?|bộ\s+luật\s+lao\s+động(?:\s+\d+)?)",
            query,
            re.IGNORECASE,
        )
        for d in doc_matches:
            documents.append(d.strip())

        return articles, documents

    def rewrite(self, query: str) -> TransformedQuery:
        """Thực hiện biến đổi câu hỏi người dùng thành search query tinh gọn."""
        cleaned = query.strip()

        # 1. Trích xuất thực thể
        articles, documents = self._extract_legal_entities(cleaned)

        # 2. Loại bỏ các tiền tố và hậu tố giao tiếp
        for prefix_pat in self.CONVERSATIONAL_PREFIXES:
            cleaned = re.sub(prefix_pat, "", cleaned, flags=re.IGNORECASE).strip()

        for suffix_pat in self.CONVERSATIONAL_SUFFIXES:
            cleaned = re.sub(suffix_pat, "", cleaned, flags=re.IGNORECASE).strip()

        # 3. Trích xuất các từ khóa cốt lõi
        tokens = re.findall(r"\w+", cleaned.lower())
        meaningful_tokens = [t for t in tokens if len(t) > 1 and t not in self.STOPWORDS]

        # 4. Xác định các cụm từ quan trọng (Key Phrases)
        key_phrases = []
        full_lower = cleaned.lower()
        phrase_candidates = [
            "thử việc", "thời gian thử việc", "hợp đồng thử việc",
            "sa thải", "kỷ luật sa thải", "đơn phương chấm dứt",
            "nghỉ thai sản", "chế độ thai sản", "tai nạn lao động",
            "tiền lương làm thêm giờ", "làm thêm giờ", "nghỉ hàng năm",
            "xử phạt vi phạm", "mức phạt tiền", "thời hiệu xử lý kỷ luật"
        ]
        for pc in phrase_candidates:
            if pc in full_lower:
                key_phrases.append(pc)

        # 5. Xây dựng search query
        search_terms = []
        if articles:
            search_terms.extend(articles)
        if documents:
            search_terms.extend(documents)
        if key_phrases:
            search_terms.extend(key_phrases)
        else:
            search_terms.extend(meaningful_tokens[:6])

        # Luôn đảm bảo ngữ cảnh "Bộ luật Lao động" nếu chưa có văn bản nào
        if not documents and not any("bộ luật lao động" in st.lower() for st in search_terms):
            search_terms.append("quy định pháp luật lao động")

        # Loại bỏ trùng lặp giữ nguyên thứ tự
        seen = set()
        final_terms = []
        for term in search_terms:
            tl = term.lower()
            if tl not in seen:
                seen.add(tl)
                final_terms.append(term)

        search_query_str = " ".join(final_terms)

        return TransformedQuery(
            original_query=query,
            search_query=search_query_str,
            keywords=meaningful_tokens,
            identified_articles=articles,
            identified_documents=documents,
            intent="legal_search"
        )
