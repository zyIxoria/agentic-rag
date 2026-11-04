"""temporal_filter.py - Cơ chế lọc tài liệu theo thời điểm và tình trạng hiệu lực (Temporal Legal Filtering).

Hỗ trợ hệ thống RAG giải quyết các bài toán áp dụng pháp luật theo từng thời kỳ:
1. Phân tích ngữ cảnh thời gian (Temporal Intent Extraction) từ truy vấn người dùng (VD: "năm 2022", "tháng 7/2024", "hiện nay").
2. Đối chiếu thời điểm hiệu lực (effective_from, effective_to) và tình trạng pháp lý (legal_status) của từng chunk.
3. Loại bỏ các văn bản chưa có hiệu lực hoặc đã hết hiệu lực tại thời điểm tra cứu.
"""

from __future__ import annotations
import re
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Union, Tuple

from RAG.retriever.schema import RetrievedChunk

logger = logging.getLogger(__name__)


def parse_legal_date(val: Any) -> Optional[date]:
    """Chuyển đổi chuỗi ngày tháng pháp lý (DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY) sang datetime.date."""
    if not val or not isinstance(val, str):
        return None
    clean = val.strip()
    if not clean or clean.lower() in ["none", "null", "unknown", "đã biết", "không xác định"]:
        return None

    # DD/MM/YYYY hoặc D/M/YYYY
    m1 = re.search(r'\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b', clean)
    if m1:
        d, m, y = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
        try:
            return date(y, m, d)
        except ValueError:
            return None

    # YYYY-MM-DD
    m2 = re.search(r'\b(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})\b', clean)
    if m2:
        y, m, d = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        try:
            return date(y, m, d)
        except ValueError:
            return None

    return None


class TemporalLegalFilter:
    """Bộ lọc văn bản quy phạm pháp luật theo thời điểm và trạng thái hiệu lực."""

    def __init__(self, default_as_of_date: Optional[date] = None):
        self.default_as_of_date = default_as_of_date

    @staticmethod
    def extract_temporal_intent(query: str) -> Tuple[Optional[date], Optional[str]]:
        """Bóc tách ý định thời gian (Temporal Intent) từ câu hỏi tự nhiên tiếng Việt.
        
        Returns:
            Tuple (target_date, temporal_keyword):
            - target_date: Ngày làm căn cứ lọc (date object) hoặc None nếu không có yếu tố thời gian.
            - temporal_keyword: Từ khóa thời gian phát hiện được (VD: 'năm 2022', 'hiện nay').
        """
        if not query:
            return None, None

        q_lower = query.lower()

        # 1. Phát hiện cụm từ chỉ hiện tại: "hiện nay", "hiện tại", "bây giờ", "mới nhất", "hiện hành"
        if any(w in q_lower for w in ["hiện nay", "hiện tại", "bây giờ", "thời điểm này", "mới nhất", "hiện hành"]):
            return date.today(), "hiện hành"

        # 2. Phát hiện ngày cụ thể: "ngày DD tháng MM năm YYYY" hoặc "DD/MM/YYYY"
        m_full = re.search(r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})', q_lower)
        if m_full:
            d, m, y = int(m_full.group(1)), int(m_full.group(2)), int(m_full.group(3))
            try:
                return date(y, m, d), m_full.group(0)
            except ValueError:
                pass

        m_slash = re.search(r'\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b', q_lower)
        if m_slash:
            d, m, y = int(m_slash.group(1)), int(m_slash.group(2)), int(m_slash.group(3))
            try:
                return date(y, m, d), m_slash.group(0)
            except ValueError:
                pass

        # 3. Phát hiện tháng cụ thể: "tháng MM năm YYYY" hoặc "tháng MM/YYYY"
        m_month = re.search(r'tháng\s+(\d{1,2})(?:\s*[/.-]\s*|\s+năm\s+)(\d{4})', q_lower)
        if m_month:
            m, y = int(m_month.group(1)), int(m_month.group(2))
            try:
                return date(y, m, 1), m_month.group(0)
            except ValueError:
                pass

        # 4. Phát hiện năm cụ thể: "năm YYYY" hoặc "vào năm YYYY"
        m_year = re.search(r'(?:vào\s+)?năm\s+(\d{4})', q_lower)
        if m_year:
            y = int(m_year.group(1))
            try:
                return date(y, 12, 31), m_year.group(0)
            except ValueError:
                pass

        return None, None

    @staticmethod
    def is_chunk_valid_at_date(
        chunk_metadata: Dict[str, Any],
        target_date: date,
        strict_status: bool = False
    ) -> bool:
        """Kiểm tra một chunk có đang phát sinh hiệu lực tại thời điểm target_date hay không."""
        eff_from_str = chunk_metadata.get("effective_from")
        eff_to_str = chunk_metadata.get("effective_to")
        status = (chunk_metadata.get("legal_status") or "").strip()

        eff_from = parse_legal_date(eff_from_str)
        eff_to = parse_legal_date(eff_to_str)

        # 1. Nếu thời điểm tra cứu trước ngày bắt đầu có hiệu lực -> CHƯA CÓ HIỆU LỰC
        if eff_from and target_date < eff_from:
            return False

        # 2. Nếu thời điểm tra cứu sau ngày hết hiệu lực -> ĐÃ HẾT HIỆU LỰC
        if eff_to and target_date > eff_to:
            return False

        # 3. Nếu kiểm tra ở thời điểm hiện tại/tương lai và có trạng thái Hết hiệu lực
        if strict_status and status in ["Hết hiệu lực", "bãi bỏ"]:
            return False

        # 4. Nếu trạng thái ghi rõ 'Chưa có hiệu lực' tại thời điểm tra cứu
        if status == "Chưa có hiệu lực" and (eff_from is None or target_date < eff_from):
            return False

        return True

    def filter_chunks(
        self,
        chunks: List[RetrievedChunk],
        as_of_date: Optional[Union[str, date]] = None,
        required_status: Optional[str] = None
    ) -> List[RetrievedChunk]:
        """Lọc danh sách RetrievedChunk theo thời điểm hiệu lực và tình trạng pháp lý."""
        if not chunks:
            return []

        target_d: Optional[date] = None
        if isinstance(as_of_date, date):
            target_d = as_of_date
        elif isinstance(as_of_date, str):
            target_d = parse_legal_date(as_of_date)
        elif self.default_as_of_date:
            target_d = self.default_as_of_date

        filtered: List[RetrievedChunk] = []

        for c in chunks:
            meta = c.metadata or {}

            # 1. Lọc theo trạng thái bắt buộc nếu có
            if required_status:
                c_status = (meta.get("legal_status") or "").strip()
                if c_status != required_status:
                    continue

            # 2. Lọc theo thời điểm hiệu lực
            if target_d:
                if not self.is_chunk_valid_at_date(meta, target_d):
                    continue

            filtered.append(c)

        # Cập nhật lại rank sau khi lọc
        for idx, c in enumerate(filtered, start=1):
            c.rank = idx

        return filtered

