"""answer_metrics.py - Đánh giá tính chính xác của câu trả lời (Answer Correctness)."""

from __future__ import annotations
import re
from typing import Any, Dict, List, Set, Tuple


def _normalize_tokens(text: str) -> List[str]:
    """Tách từ và chuẩn hóa chuỗi tiếng Việt phục vụ tính toán F1."""
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    stopwords = {
        "và", "hoặc", "của", "cho", "các", "những", "được", "trong", "theo",
        "tại", "với", "có", "là", "thì", "mà", "ở", "này", "đó", "ra", "sao",
        "bao", "nhiêu", "như", "thế", "nào", "gì", "khi", "quy", "định", "pháp", "luật"
    }
    return [w for w in clean.split() if len(w) >= 2 and w not in stopwords]


def _compute_f1(pred_tokens: List[str], ref_tokens: List[str]) -> float:
    """Tính token-level F1 score giữa câu trả lời sinh ra và câu trả lời mẫu."""
    if not pred_tokens or not ref_tokens:
        return 0.0
    pred_set = set(pred_tokens)
    ref_set = set(ref_tokens)
    common = pred_set & ref_set
    if not common:
        return 0.0
    precision = len(common) / len(pred_set)
    recall = len(common) / len(ref_set)
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)


def evaluate_answer_correctness(
    generated_answer: str,
    reference_answer: str,
    gold_sources: List[Dict[str, Any]],
    refused: bool,
    requires_refusal: bool,
    citations: List[Any],
) -> Dict[str, Any]:
    """Đánh giá Answer Correctness theo căn cứ pháp lý vàng và câu trả lời tham chiếu.
    
    Phân loại:
    - CORRECT: Điểm 1.0
    - PARTIALLY_CORRECT: Điểm 0.5
    - INCORRECT: Điểm 0.0
    """
    # 1. Trường hợp câu hỏi yêu cầu từ chối (insufficient_evidence hoặc out_of_scope)
    if requires_refusal:
        if refused:
            return {
                "status": "CORRECT",
                "score": 1.0,
                "reason": "Hệ thống từ chối thành công câu hỏi ngoài phạm vi hoặc thiếu chứng cứ.",
                "f1_score": 1.0,
                "gold_article_recall": 1.0,
            }
        else:
            return {
                "status": "INCORRECT",
                "score": 0.0,
                "reason": "Hệ thống tự bịa câu trả lời khi đáng lẽ phải từ chối (False Answer).",
                "f1_score": 0.0,
                "gold_article_recall": 0.0,
            }

    # 2. Trường hợp câu hỏi hợp lệ nhưng hệ thống từ chối (False Refusal)
    if refused:
        return {
            "status": "INCORRECT",
            "score": 0.0,
            "reason": "Từ chối nhầm câu hỏi hợp lệ do không thu hồi được văn bản liên quan (False Refusal).",
            "f1_score": 0.0,
            "gold_article_recall": 0.0,
        }

    # 3. Câu hỏi có đáp án và hệ thống trả lời
    gold_articles: Set[str] = set()
    for gs in gold_sources:
        doc = gs.get("document_id", "")
        art = gs.get("article_number", "") or ""
        if art:
            gold_articles.add(f"{doc}_{art}".lower().replace(" ", ""))

    # Kiểm tra các điều luật xuất hiện trong câu trả lời hoặc danh mục citation
    ans_lower = generated_answer.lower().replace(" ", "")
    matched_articles: Set[str] = set()
    for ga in gold_articles:
        # Tách kiểm tra số điều (VD: 'điều125')
        art_num = ga.split("_")[-1]
        if ga in ans_lower or art_num in ans_lower:
            matched_articles.add(ga)

    for cit in citations:
        cit_str = str(cit).lower().replace(" ", "")
        for ga in gold_articles:
            art_num = ga.split("_")[-1]
            if ga in cit_str or art_num in cit_str:
                matched_articles.add(ga)

    article_recall = len(matched_articles) / len(gold_articles) if gold_articles else 0.0

    # Tính F1 từ vựng
    pred_tokens = _normalize_tokens(generated_answer)
    ref_tokens = _normalize_tokens(reference_answer)
    f1 = _compute_f1(pred_tokens, ref_tokens)

    # Phân loại độ chính xác
    if article_recall >= 1.0 and f1 >= 0.20:
        status = "CORRECT"
        score = 1.0
        reason = "Viện dẫn đầy đủ các Điều luật vàng và bao phủ chuẩn xác nội dung kết luận pháp lý."
    elif article_recall > 0.0 or f1 >= 0.35:
        status = "PARTIALLY_CORRECT"
        score = 0.5
        reason = "Viện dẫn đúng một phần Điều luật hoặc nội dung có liên quan nhưng chưa đầy đủ."
    else:
        status = "INCORRECT"
        score = 0.0
        reason = "Viện dẫn sai lệch Điều luật hoặc nội dung trả lời không khớp với căn cứ vàng."

    return {
        "status": status,
        "score": score,
        "reason": reason,
        "f1_score": round(f1, 4),
        "gold_article_recall": round(article_recall, 4),
        "matched_articles": list(matched_articles),
    }
