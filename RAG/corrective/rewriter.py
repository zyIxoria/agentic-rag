"""rewriter.py - Bộ viết lại truy vấn (Query Rewriter) trong Corrective RAG.

Nhiệm vụ:
- Làm rõ chủ thể pháp lý (Người lao động, Người sử dụng lao động, v.v.).
- Làm rõ hành vi pháp lý và thuật ngữ chuyên ngành (sa thải, nghỉ việc riêng, làm thêm giờ, thử việc).
- Làm rõ điều kiện và khung thời gian.
- Loại bỏ từ đệm đàm thoại mơ hồ.
- BẢO ĐẢM NGUYÊN TẮC: Tuyệt đối không tự bịa đặt số điều luật, tên nghị định hoặc con số pháp luật.
"""

from __future__ import annotations
import re
import logging
from typing import Optional, Dict, Any

from RAG.corrective.schemas import RetrievalEvaluation
from RAG.corrective.config import CRAGConfig, default_crag_config
from RAG.corrective.prompts import LEGAL_ABBREVIATIONS

logger = logging.getLogger("RAG.corrective.rewriter")

# Từ đệm đàm thoại cần loại bỏ
CONVERSATIONAL_PREFIXES = [
    r"^cho\s+(tôi|em|mình|chúng\s+tôi)\s+hỏi\s*(là|về)?",
    r"^(xin\s+)?cho\s+biết\s*(là|về)?",
    r"^ad(min)?\s+(cho\s+hỏi|ơi|cho\s+biết)",
    r"^làm\s+ơn\s+cho\s+hỏi",
    r"^thưa\s+luật\s+sư",
    r"^hỏi\s+về\s+việc",
]

CONVERSATIONAL_SUFFIXES = [
    r"\s*(được\s+không|thế\s+nào|ra\s+sao|như\s+thế\s+nào|hả\s+mọi\s+người|nhỉ|ạ|nhé|vậy\s+ạ)\s*[?.]*$",
    r"\s*vậy\s+ad\s*[?.]*$",
]

# Chuyển đổi ngôn ngữ đời thường thành thuật ngữ pháp lý chuẩn tắc
COLLOQUIAL_MAPPING = [
    (r"\bđuổi\s+việc\b", "xử lý kỷ luật sa thải"),
    (r"\bnghỉ\s+đẻ\b", "nghỉ thai sản"),
    (r"\btăng\s+ca\b", "làm thêm giờ"),
    (r"\bvề\s+hưu\b", "nghỉ hưu"),
    (r"\bnghỉ\s+già\b", "hưởng chế độ hưu trí"),
    (r"\bcưới\b", "kết hôn"),
    (r"\blấy\s+vợ\b", "kết hôn"),
    (r"\blấy\s+chồng\b", "kết hôn"),
    (r"\bnghỉ\s+khi\s+kết\s+hôn\b", "nghỉ việc riêng hưởng nguyên lương khi kết hôn"),
    (r"\bnghỉ\s+việc\s+riêng\s+khi\s+kết\s+hôn\b", "nghỉ việc riêng hưởng nguyên lương khi kết hôn"),
    (r"\bnghỉ\s+phép\s+năm\b", "nghỉ hằng năm hưởng nguyên lương"),
]


class QueryRewriter:
    """Bộ viết lại và tối ưu hóa truy vấn cho Corrective Retrieval."""

    def __init__(self, config: Optional[CRAGConfig] = None):
        self.config = config or default_crag_config

    def rewrite_query(
        self,
        original_query: str,
        retrieval_evaluation: Optional[RetrievalEvaluation] = None,
    ) -> str:
        """Viết lại câu hỏi ban đầu thành truy vấn tìm kiếm pháp lý rõ ràng, chính xác.
        
        Args:
            original_query: Câu hỏi gốc của người dùng.
            retrieval_evaluation: Kết quả đánh giá retrieval lần 1 (nếu có) để định hướng bổ sung.
            
        Returns:
            Chuỗi truy vấn đã được tối ưu hóa.
        """
        if not original_query or not original_query.strip():
            return original_query

        raw = original_query.strip()
        rewritten = raw

        # 1. Loại bỏ các từ đệm hội thoại đầu câu
        for prefix_pat in CONVERSATIONAL_PREFIXES:
            rewritten = re.sub(prefix_pat, "", rewritten, flags=re.IGNORECASE).strip()

        # 2. Loại bỏ các từ đệm hội thoại cuối câu
        for suffix_pat in CONVERSATIONAL_SUFFIXES:
            rewritten = re.sub(suffix_pat, "", rewritten, flags=re.IGNORECASE).strip()

        # 3. Chuẩn hóa viết tắt pháp luật lao động (NLĐ -> người lao động, NSDLĐ -> người sử dụng lao động)
        for abbr, full_phrase in LEGAL_ABBREVIATIONS.items():
            pattern = rf"\b{re.escape(abbr)}\b"
            rewritten = re.sub(pattern, full_phrase, rewritten, flags=re.IGNORECASE)

        # 4. Chuẩn hóa thuật ngữ đời thường thành thuật ngữ pháp lý
        for colloquial_pat, formal_phrase in COLLOQUIAL_MAPPING:
            rewritten = re.sub(colloquial_pat, formal_phrase, rewritten, flags=re.IGNORECASE)

        # 5. Làm rõ chủ thể nếu thiếu chủ thể pháp lý
        # Nếu câu hỏi nói về quyền lợi/nghĩa vụ mà không rõ chủ thể (NLĐ hay NSDLĐ)
        has_subject = any(sub in rewritten.lower() for sub in [
            "người lao động", "người sử dụng lao động", "doanh nghiệp",
            "công ty", "lao động", "cán bộ", "viên chức"
        ])
        if not has_subject:
            # Xác định chủ thể mặc định là người lao động đối với quyền lợi
            if any(term in rewritten.lower() for term in ["nghỉ", "lương", "sa thải", "thử việc", "làm thêm", "bồi thường", "bảo hiểm"]):
                rewritten = f"Quy định đối với người lao động về {rewritten.lower()}"

        # 6. Làm rõ điều kiện và khung thời gian nếu câu hỏi ngắn hoặc mơ hồ
        q_low = rewritten.lower()
        if "kết hôn" in q_low and "nghỉ việc riêng" not in q_low:
            rewritten = re.sub(r"(?i)\bkết hôn\b", "nghỉ việc riêng hưởng nguyên lương khi kết hôn", rewritten)

        # Chuẩn hóa cụm từ làm thêm giờ
        if "giờ làm thêm" in q_low and "làm thêm giờ" not in q_low:
            rewritten = re.sub(r"(?i)\bgiờ\s+làm\s+thêm\b", "làm thêm giờ", rewritten)
            q_low = rewritten.lower()

        if "làm thêm" in q_low and not any(t in q_low for t in ["ngày", "tháng", "năm"]):
            rewritten = f"{rewritten} trong một ngày, một tháng và một năm"

        # 7. Định hình câu hỏi thành truy vấn quy phạm pháp lý (Formal Legal Query)
        # Nếu câu hỏi chưa bắt đầu bằng cụm từ chỉ quy định chuẩn
        if not any(rewritten.lower().startswith(p) for p in ["quy định về", "quy định đối với", "điều kiện", "tiêu chuẩn", "thời giờ", "mức"]):
            # Chỉ thêm tiền tố nếu câu hỏi mang tính chất hỏi quy định
            if any(w in rewritten.lower() for w in ["bao nhiêu", "như thế nào", "khi nào", "gồm những", "được không", "phải"]):
                # Chuyển đổi "A được B bao nhiêu C" -> "Quy định về B của A"
                clean_clause = rewritten.strip("?. ")
                rewritten = f"Quy định về {clean_clause}"

        # Làm sạch khoảng trắng thừa và dấu chấm hỏi cuối câu cho truy vấn tìm kiếm véc-tơ
        rewritten = re.sub(r"\s+", " ", rewritten).strip(" ?.")

        # 8. BẢO VỆ CHỐNG HALLUCINATION (STRICT NEGATIVE CONSTRAINT CHECK):
        # Đảm bảo KHÔNG tự tiện thêm số Điều hoặc số hiệu Nghị định nếu câu hỏi ban đầu không có!
        rewritten = self._enforce_negative_constraints(original_query, rewritten)

        return rewritten

    def _enforce_negative_constraints(self, original_query: str, rewritten_query: str) -> str:
        """Đảm bảo không đưa thêm số điều, tên nghị định/thông tư nếu original_query không chứa."""
        orig_lower = original_query.lower()

        # Kiểm tra số Điều (ví dụ: Điều 115, Điều 107)
        article_matches = re.findall(r"(?i)\bĐiều\s+\d+\b", rewritten_query)
        for art in article_matches:
            if art.lower() not in orig_lower:
                # Loại bỏ số điều bị tự ý thêm vào
                rewritten_query = re.sub(rf"(?i)\b{re.escape(art)}\b", "", rewritten_query).strip()

        # Kiểm tra số Nghị định (ví dụ: Nghị định 145/2020)
        decree_matches = re.findall(r"(?i)\bNghị\s+định\s+(\d+/\d+|[a-zA-Z0-9\-_/]+)\b", rewritten_query)
        for dec in decree_matches:
            full_dec = f"Nghị định {dec}"
            if full_dec.lower() not in orig_lower:
                rewritten_query = re.sub(rf"(?i)\bNghị\s+định\s+{re.escape(dec)}\b", "", rewritten_query).strip()

        # Kiểm tra tên Thông tư
        circular_matches = re.findall(r"(?i)\bThông\s+tư\s+(\d+/\d+|[a-zA-Z0-9\-_/]+)\b", rewritten_query)
        for circ in circular_matches:
            full_circ = f"Thông tư {circ}"
            if full_circ.lower() not in orig_lower:
                rewritten_query = re.sub(rf"(?i)\bThông\s+tư\s+{re.escape(circ)}\b", "", rewritten_query).strip()

        # Làm sạch lại khoảng trắng
        rewritten_query = re.sub(r"\s+", " ", rewritten_query).strip()
        return rewritten_query
