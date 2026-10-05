"""faithfulness_metrics.py - Đánh giá tính trung thực (Faithfulness) dựa trên ngữ cảnh thu hồi."""

from __future__ import annotations
import re
from typing import Any, Dict, List


def evaluate_faithfulness(
    generated_answer: str,
    retrieved_chunks: List[Any],
    refused: bool,
) -> Dict[str, Any]:
    """Đánh giá xem nội dung câu trả lời có được bảo chứng (grounded) 100% bởi context thu hồi không.
    
    Phân loại:
    - SUPPORTED: Toàn bộ điều luật và thông tin được rút ra trực tiếp từ các chunk thu hồi.
    - PARTIALLY_SUPPORTED: Một phần thông tin có trong context, nhưng có chi tiết hoặc suy luận ngoài context.
    - UNSUPPORTED: Khẳng định những điều luật hoặc dữ kiện hoàn toàn không có trong context (ảo giác / bịa đặt).
    """
    if refused:
        return {
            "status": "SUPPORTED",
            "score": 1.0,
            "is_faithful": True,
            "unsupported_claim_count": 0,
            "total_claim_count": 0,
            "reason": "Hệ thống từ chối chuẩn mực, không đưa ra khẳng định pháp lý ngoài ngữ cảnh.",
        }

    if not retrieved_chunks:
        return {
            "status": "UNSUPPORTED",
            "score": 0.0,
            "is_faithful": False,
            "unsupported_claim_count": 1,
            "total_claim_count": 1,
            "reason": "Trả lời khi ngữ cảnh thu hồi hoàn toàn rỗng.",
        }

    # Gộp toàn bộ văn bản và metadata của các chunk thu hồi
    context_corpus = " ".join(
        f"{c.metadata.get('document_id', '')} {c.metadata.get('article_number', '')} {c.content}"
        for c in retrieved_chunks
    ).lower()

    # 1. Kiểm tra các số hiệu Điều luật được nhắc tới trong câu trả lời
    mentioned_articles = set(re.findall(r"điều\s+(\d+)", generated_answer.lower()))
    retrieved_articles = set(re.findall(r"điều\s+(\d+)", context_corpus))

    unsupported_articles = mentioned_articles - retrieved_articles

    # 2. Kiểm tra các câu/mệnh đề chính trong câu trả lời
    sentences = [s.strip() for s in re.split(r"[.\n;]", generated_answer) if len(s.strip()) > 15]
    if not sentences:
        sentences = [generated_answer.strip()]

    supported_sentences = 0
    unsupported_sentences = 0

    for sent in sentences:
        words = [w for w in re.findall(r"\w+", sent.lower()) if len(w) >= 3]
        if not words:
            continue
        # Tỷ lệ từ có mặt trong context
        present_count = sum(1 for w in words if w in context_corpus)
        overlap = present_count / len(words)
        if overlap >= 0.70:
            supported_sentences += 1
        else:
            unsupported_sentences += 1

    total_claims = len(sentences)
    support_ratio = supported_sentences / total_claims if total_claims else 1.0

    # Phân loại dựa trên vi phạm Điều luật và tỷ lệ hỗ trợ
    if unsupported_articles:
        status = "UNSUPPORTED"
        score = 0.0
        reason = f"Viện dẫn Điều luật không hề xuất hiện trong context: {list(unsupported_articles)}"
    elif support_ratio >= 0.75:
        status = "SUPPORTED"
        score = 1.0
        reason = "Toàn bộ khẳng định và Điều luật đều được trích xuất trung thực từ các chunk thu hồi."
    elif support_ratio >= 0.40:
        status = "PARTIALLY_SUPPORTED"
        score = 0.5
        reason = "Có một số suy diễn từ vựng hoặc chi tiết không tìm thấy nguyên văn trong ngữ cảnh."
    else:
        status = "UNSUPPORTED"
        score = 0.0
        reason = "Phần lớn nội dung câu trả lời không xuất hiện trong các đoạn văn bản thu hồi."

    return {
        "status": status,
        "score": score,
        "is_faithful": status == "SUPPORTED",
        "support_ratio": round(support_ratio, 4),
        "unsupported_claim_count": unsupported_sentences + len(unsupported_articles),
        "total_claim_count": total_claims + len(mentioned_articles),
        "unsupported_articles": list(unsupported_articles),
        "reason": reason,
    }
