"""refusal_metrics.py - Đánh giá cơ chế từ chối (Refusal) cho các câu hỏi thiếu căn cứ và ngoài phạm vi."""

from __future__ import annotations
from typing import Any, Dict


def evaluate_refusal(
    refused: bool,
    requires_refusal: bool,
    refusal_reason: str = "",
) -> Dict[str, Any]:
    """Đánh giá chi tiết hành vi từ chối của hệ thống RAG.
    
    Phân loại trạng thái:
    - CORRECT_REFUSAL: requires_refusal=True và hệ thống từ chối chính xác.
    - INCORRECT_REFUSAL / FALSE_REFUSAL: requires_refusal=False nhưng hệ thống từ chối nhầm (do retrieval yếu).
    - UNSUPPORTED_ANSWER / FALSE_ANSWER: requires_refusal=True nhưng hệ thống vẫn cố tình trả lời bịa đặt.
    - CORRECT_ANSWER: requires_refusal=False và hệ thống tạo sinh câu trả lời.
    """
    if requires_refusal:
        if refused:
            status = "CORRECT_REFUSAL"
            is_refusal_accurate = True
            is_false_answer = False
            is_false_refusal = False
            reason = "Hệ thống từ chối chính xác câu hỏi ngoài phạm vi hoặc thiếu chứng cứ."
        else:
            status = "UNSUPPORTED_ANSWER"
            is_refusal_accurate = False
            is_false_answer = True
            is_false_refusal = False
            reason = "Hệ thống cố tình tạo câu trả lời khi không có căn cứ pháp lý hợp lệ (False Answer)."
    else:
        if refused:
            status = "INCORRECT_REFUSAL"
            is_refusal_accurate = False
            is_false_answer = False
            is_false_refusal = True
            reason = f"Hệ thống từ chối nhầm câu hỏi hợp lệ (False Refusal): {refusal_reason or 'Điểm thu hồi thấp'}"
        else:
            status = "CORRECT_ANSWER"
            is_refusal_accurate = True
            is_false_answer = False
            is_false_refusal = False
            reason = "Hệ thống tiếp nhận và tạo sinh câu trả lời cho câu hỏi hợp lệ."

    return {
        "status": status,
        "is_refusal_accurate": is_refusal_accurate,
        "is_false_answer": is_false_answer,
        "is_false_refusal": is_false_refusal,
        "reason": reason,
    }
