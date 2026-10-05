"""citation_metrics.py - Đánh giá độ chính xác, độ bao phủ và tính hợp lệ của trích dẫn pháp lý."""

from __future__ import annotations
import re
from typing import Any, Dict, List, Set, Tuple


def evaluate_citations(
    citations: List[Any],
    retrieved_chunks: List[Any],
    gold_sources: List[Dict[str, Any]],
    refused: bool,
    requires_refusal: bool,
) -> Dict[str, Any]:
    """Đánh giá chất lượng trích dẫn: Coverage, Precision, Accuracy, Invalid Rate."""
    if refused:
        return {
            "has_citation": False,
            "citation_coverage": 1.0 if requires_refusal else 0.0,
            "citation_precision": 1.0 if requires_refusal else 0.0,
            "citation_accuracy": 1.0 if requires_refusal else 0.0,
            "invalid_citation_rate": 0.0,
            "total_citations": 0,
            "valid_citations": 0,
            "gold_matching_citations": 0,
            "invalid_citations": 0,
            "reason": "Hệ thống từ chối an toàn, không có trích dẫn được sinh ra.",
        }

    total_cits = len(citations)
    if total_cits == 0:
        return {
            "has_citation": False,
            "citation_coverage": 0.0,
            "citation_precision": 0.0,
            "citation_accuracy": 0.0,
            "invalid_citation_rate": 0.0,
            "total_citations": 0,
            "valid_citations": 0,
            "gold_matching_citations": 0,
            "invalid_citations": 0,
            "reason": "Câu trả lời không cung cấp bất kỳ trích dẫn pháp lý nào.",
        }

    # Tập hợp các Điều luật trong retrieved_chunks
    retrieved_articles: Set[str] = set()
    for c in retrieved_chunks:
        doc = c.metadata.get("document_id", "")
        art = c.metadata.get("article_number", "") or ""
        if art:
            retrieved_articles.add(f"{doc}_{art}".lower().replace(" ", ""))
            # Thêm biến thể số hiệu Điều thuần túy (VD: "điều125")
            num_match = re.search(r"điều\s*(\d+)", art.lower())
            if num_match:
                retrieved_articles.add(f"điều{num_match.group(1)}")

    # Tập hợp các Điều luật trong gold_sources
    gold_articles: Set[str] = set()
    for gs in gold_sources:
        doc = gs.get("document_id", "")
        art = gs.get("article_number", "") or ""
        if art:
            gold_articles.add(f"{doc}_{art}".lower().replace(" ", ""))
            num_match = re.search(r"điều\s*(\d+)", art.lower())
            if num_match:
                gold_articles.add(f"điều{num_match.group(1)}")

    valid_cits = 0
    gold_matching_cits = 0
    invalid_cits = 0

    for cit in citations:
        cit_str = str(cit).lower().replace(" ", "")

        # Kiểm tra trích dẫn có trỏ tới retrieved chunk hay không
        points_to_retrieved = any(ra in cit_str for ra in retrieved_articles)

        # Kiểm tra trích dẫn có trỏ tới gold sources hay không
        matches_gold = any(ga in cit_str for ga in gold_articles)

        if points_to_retrieved:
            valid_cits += 1
            if matches_gold:
                gold_matching_cits += 1
        else:
            invalid_cits += 1

    precision = gold_matching_cits / total_cits if total_cits else 0.0
    accuracy = 1.0 if (total_cits > 0 and invalid_cits == 0 and gold_matching_cits > 0) else 0.0
    invalid_rate = invalid_cits / total_cits if total_cits else 0.0

    return {
        "has_citation": True,
        "citation_coverage": 1.0,
        "citation_precision": round(precision, 4),
        "citation_accuracy": round(accuracy, 4),
        "invalid_citation_rate": round(invalid_rate, 4),
        "total_citations": total_cits,
        "valid_citations": valid_cits,
        "gold_matching_citations": gold_matching_cits,
        "invalid_citations": invalid_cits,
        "reason": f"Tổng cộng {total_cits} trích dẫn, {gold_matching_cits} khớp với nguồn vàng, {invalid_cits} không hợp lệ.",
    }
