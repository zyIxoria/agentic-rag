"""config_v2.py - Configurable Parameters for Legal-Aware Chunking V2.

Cung cấp cấu hình linh hoạt cho bộ chunker pháp lý (Legal-Aware Chunker),
cho phép điều chỉnh các ngưỡng tokens và hệ số mà không bị hard-code:
- target_chunk_tokens: Kích thước token mục tiêu lý tưởng cho 1 chunk
- max_chunk_tokens: Ngưỡng trần token tối đa (ngăn chặn triệt để monster chunks)
- min_chunk_tokens: Ngưỡng sàn token tối thiểu (hạn chế tối đa micro-chunks vô nghĩa)
- overlap_tokens: Số lượng tokens gối đầu khi phải chia nhỏ đoạn văn bản dài
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
import math
import re


@dataclass
class ChunkerConfigV2:
    """Cấu hình tham số cho Legal-Aware Chunker V2."""
    target_chunk_tokens: int = 350       # Kích thước mục tiêu lý tưởng (~270 từ)
    max_chunk_tokens: int = 800          # Ngưỡng trần tối đa (~615 từ)
    min_chunk_tokens: int = 100          # Ngưỡng sàn tối thiểu (~75 từ)
    overlap_tokens: int = 40             # Tokens overlap (~30 từ)
    token_multiplier: float = 1.3        # Hệ số ước lượng BPE subwords trên từ tiếng Việt
    preserve_full_points: bool = True    # Ưu tiên không cắt giữa chừng Điểm luật
    preserve_full_clauses: bool = True   # Ưu tiên giữ trọn Khoản nếu trong ngưỡng max
    include_intro_context: bool = True   # Kèm lời dẫn của Khoản vào các nhóm Điểm

    def __post_init__(self):
        """Xác thực tính hợp lệ của cấu hình."""
        if self.min_chunk_tokens <= 0:
            raise ValueError(f"min_chunk_tokens phải > 0, nhận được: {self.min_chunk_tokens}")
        if self.target_chunk_tokens < self.min_chunk_tokens:
            raise ValueError(
                f"target_chunk_tokens ({self.target_chunk_tokens}) không được nhỏ hơn min_chunk_tokens ({self.min_chunk_tokens})"
            )
        if self.max_chunk_tokens < self.target_chunk_tokens:
            raise ValueError(
                f"max_chunk_tokens ({self.max_chunk_tokens}) không được nhỏ hơn target_chunk_tokens ({self.target_chunk_tokens})"
            )
        if self.overlap_tokens < 0:
            raise ValueError(f"overlap_tokens không được là số âm: {self.overlap_tokens}")
        if self.overlap_tokens >= self.min_chunk_tokens:
            raise ValueError(
                f"overlap_tokens ({self.overlap_tokens}) phải nhỏ hơn min_chunk_tokens ({self.min_chunk_tokens})"
            )
        if self.token_multiplier <= 0:
            raise ValueError(f"token_multiplier phải > 0: {self.token_multiplier}")

    def count_tokens(self, text: str) -> int:
        """Ước lượng số token cho văn bản tiếng Việt dựa trên số từ nhân hệ số subword.
        
        Nếu văn bản rỗng, trả về 0.
        """
        if not text or not text.strip():
            return 0
        words = len(text.strip().split())
        return int(math.ceil(words * self.token_multiplier))

    def tokens_to_words(self, tokens: int) -> int:
        """Quy đổi số token sang số từ gần đúng."""
        return max(1, int(math.floor(tokens / self.token_multiplier)))

    def to_dict(self) -> Dict[str, Any]:
        """Xuất cấu hình ra dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChunkerConfigV2:
        """Khởi tạo cấu hình từ dictionary an toàn."""
        valid_keys = {
            "target_chunk_tokens", "max_chunk_tokens", "min_chunk_tokens",
            "overlap_tokens", "token_multiplier", "preserve_full_points",
            "preserve_full_clauses", "include_intro_context"
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys and v is not None}
        return cls(**filtered)


# Cấu hình mặc định toàn cục
DEFAULT_CHUNKER_CONFIG = ChunkerConfigV2()
