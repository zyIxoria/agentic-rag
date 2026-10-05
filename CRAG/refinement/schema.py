"""
CRAG Knowledge Refinement Schemas.
Định nghĩa cấu trúc dữ liệu cho Knowledge Strip và Refined Context.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class KnowledgeStrip:
    """
    Một dải tri thức (Strip) phân rã từ RetrievedChunk (câu hoặc khoản pháp lý).
    """
    strip_id: str
    chunk_id: str
    content: str
    score: float
    is_retained: bool
    source_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RefinedDocument:
    """
    Tài liệu sau khi đã trải qua bước Strip & Filter.
    """
    chunk_id: str
    source_index: int
    original_content: str
    refined_content: str
    strips: List[KnowledgeStrip]
    metadata: Dict[str, Any]
    retained_strips_count: int
    discarded_strips_count: int


@dataclass
class RefinedContext:
    """
    Toàn bộ ngữ cảnh sau khi tinh lọc tri thức, sẵn sàng cấp cho Generator.
    """
    documents: List[RefinedDocument]
    raw_context_text: str
    original_char_count: int
    refined_char_count: int
    compression_ratio: float
    total_strips_retained: int
    total_strips_discarded: int
