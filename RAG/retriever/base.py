"""base.py - Lớp cơ sở trừu tượng cho Retriever trong Traditional RAG Baseline."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional

from RAG.retriever.schema import RetrievedChunk


class BaseRetriever(ABC):
    """Giao diện trừu tượng chuẩn mực cho phân hệ thu hồi thông tin pháp lý."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        """Thu hồi danh sách Top-K chunks phù hợp nhất với câu hỏi người dùng.
        
        Args:
            query: Câu hỏi hoặc văn bản truy vấn.
            top_k: Số lượng kết quả tối đa cần lấy (nếu None sẽ dùng cấu hình mặc định).
            score_threshold: Ngưỡng điểm tương đồng tối thiểu (nếu None sẽ dùng cấu hình).
            
        Returns:
            List[RetrievedChunk]: Danh sách các đoạn văn bản pháp lý đã được xếp hạng từ 1..K.
        """
        pass
