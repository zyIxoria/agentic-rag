"""
CRAG Query Transformation Schemas.
Định nghĩa cấu trúc dữ liệu cho câu truy vấn sau biến đổi (Query Transformation / Rewriting).
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TransformedQuery:
    """
    Kết quả biến đổi câu hỏi người dùng thành truy vấn tìm kiếm tối ưu cho Search Engine.
    """
    original_query: str
    search_query: str
    keywords: List[str] = field(default_factory=list)
    identified_articles: List[str] = field(default_factory=list)
    identified_documents: List[str] = field(default_factory=list)
    intent: Optional[str] = None
