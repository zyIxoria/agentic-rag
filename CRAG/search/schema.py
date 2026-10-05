"""
CRAG Search Schemas.
Định nghĩa cấu trúc dữ liệu cho kết quả tra cứu ngoại bộ (Web Search Fallback).
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class WebSearchResult:
    """Một mẩu kết quả tìm kiếm ngoại bộ."""
    title: str
    snippet: str
    url: str
    source_name: str = "Web Search"
    score: float = 1.0


@dataclass
class SearchResponse:
    """Toàn bộ phản hồi từ Web Search Fallback Engine."""
    query: str
    transformed_query: str
    results: List[WebSearchResult]
    latency: float
    provider: str
    total_found: int = 0
