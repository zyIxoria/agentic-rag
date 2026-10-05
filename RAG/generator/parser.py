"""parser.py - Bộ phân tích cú pháp đầu ra có cấu trúc (Robust Structured Output Parser).

Đảm bảo xử lý tin cậy mọi dạng phản hồi từ LLM:
- JSON chuẩn từ API Structured Output.
- JSON nằm trong khối markdown (```json ... ```).
- JSON lỗi nhỏ hoặc kèm văn bản dẫn dắt bên ngoài.
- Fallback khi LLM chỉ trả về văn bản thuần.
- Chuẩn hóa citations và kiểm tra tính nhất quán của trạng thái từ chối (refused).
"""

from __future__ import annotations
import json
import re
import logging
from typing import Dict, Any, List, Optional
from RAG.generator.schema import LegalAnswer
from RAG.prompts.legal_prompts import STANDARD_REFUSAL_ANSWER

logger = logging.getLogger(__name__)

# Regex tìm kiếm các thẻ trích dẫn [SOURCE N] hoặc SOURCE N
SOURCE_TAG_REGEX = re.compile(r"\[?\bSOURCE\s+(\d+)\b\]?", re.IGNORECASE)


def extract_citations_from_text(text: str) -> List[str]:
    """Trích xuất tất cả các nhãn SOURCE N xuất hiện trong văn bản theo thứ tự xuất hiện."""
    matches = SOURCE_TAG_REGEX.findall(text)
    seen = set()
    citations = []
    for num in matches:
        tag = f"SOURCE {num}"
        if tag not in seen:
            seen.add(tag)
            citations.append(tag)
    return citations


def parse_generator_output(raw_output: str) -> LegalAnswer:
    """Phân tích văn bản phản hồi từ LLM thành đối tượng LegalAnswer có cấu trúc.
    
    Args:
        raw_output: Chuỗi phản hồi thô từ LLM.
        
    Returns:
        Đối tượng LegalAnswer hợp lệ.
    """
    if not raw_output or not raw_output.strip():
        return LegalAnswer(
            answer=STANDARD_REFUSAL_ANSWER,
            citations=[],
            refused=True,
            reason="Phản hồi từ mô hình rỗng."
        )

    clean_text = raw_output.strip()

    # 1. Trích xuất JSON từ khối markdown ```json ... ``` hoặc ``` ... ```
    json_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text, re.IGNORECASE)
    if json_block_match:
        json_candidate = json_block_match.group(1).strip()
    else:
        # Tìm khối { ... } lớn nhất
        brace_start = clean_text.find("{")
        brace_end = clean_text.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            json_candidate = clean_text[brace_start:brace_end + 1].strip()
        else:
            json_candidate = clean_text

    # 2. Thử parse qua json.loads
    parsed_dict: Optional[Dict[str, Any]] = None
    try:
        parsed_dict = json.loads(json_candidate)
    except Exception as e:
        logger.debug("json.loads thất bại với json_candidate: %s. Thử regex fallback.", e)
        # Thử regex trích xuất các trường cơ bản
        parsed_dict = _regex_parse_json(json_candidate)

    if parsed_dict and isinstance(parsed_dict, dict):
        answer = str(parsed_dict.get("answer", "")).strip()
        raw_citations = parsed_dict.get("citations", [])
        refused = bool(parsed_dict.get("refused", False))
        reason = parsed_dict.get("reason")
        if reason is not None:
            reason = str(reason).strip()

        # Chuẩn hóa citations
        citations: List[str] = []
        if isinstance(raw_citations, list):
            for c in raw_citations:
                c_str = str(c).strip().strip("[]")
                # Chuẩn hóa về dạng 'SOURCE N'
                m = re.search(r"SOURCE\s+(\d+)", c_str, re.IGNORECASE)
                if m:
                    norm = f"SOURCE {m.group(1)}"
                    if norm not in citations:
                        citations.append(norm)
                elif c_str:
                    if c_str not in citations:
                        citations.append(c_str)
        elif isinstance(raw_citations, str):
            citations = extract_citations_from_text(raw_citations)

        # Nếu trong text có trích dẫn [SOURCE N] mà citations bị bỏ sót, tự động bổ sung
        text_citations = extract_citations_from_text(answer)
        for tc in text_citations:
            if tc not in citations:
                citations.append(tc)

        # Kiểm tra tính nhất quán của trạng thái từ chối (Refusal check)
        refusal_keywords = [
            "không tìm thấy đủ căn cứ",
            "không đủ căn cứ pháp lý",
            "không có thông tin trong ngữ cảnh",
            "dữ liệu được cung cấp không đề cập",
            STANDARD_REFUSAL_ANSWER.lower(),
        ]
        answer_lower = answer.lower()
        if any(kw in answer_lower for kw in refusal_keywords):
            refused = True
            # Nếu answer chưa có đúng câu chuẩn mực, đảm bảo có câu chuẩn mực
            if STANDARD_REFUSAL_ANSWER not in answer:
                answer = f"{STANDARD_REFUSAL_ANSWER}\n\n{answer}".strip()

        if refused:
            citations = []
            if not answer or STANDARD_REFUSAL_ANSWER.lower() not in answer.lower():
                answer = STANDARD_REFUSAL_ANSWER

        return LegalAnswer(
            answer=answer,
            citations=citations,
            refused=refused,
            reason=reason
        )

    # 3. Fallback hoàn toàn cho văn bản thô (khi không parse được JSON)
    logger.warning("Không thể parse cấu trúc JSON từ LLM output. Kích hoạt fallback văn bản thô.")
    raw_answer = clean_text
    citations = extract_citations_from_text(raw_answer)
    refused = False
    reason = None

    refusal_keywords = [
        "không tìm thấy đủ căn cứ",
        "không đủ căn cứ",
        "không có thông tin",
        STANDARD_REFUSAL_ANSWER.lower(),
    ]
    if any(kw in raw_answer.lower() for kw in refusal_keywords):
        refused = True
        raw_answer = STANDARD_REFUSAL_ANSWER
        citations = []
        reason = "Phát hiện nội dung từ chối trong phản hồi thô."

    return LegalAnswer(
        answer=raw_answer,
        citations=citations,
        refused=refused,
        reason=reason
    )


def _regex_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """Trích xuất cứu cánh bằng biểu thức chính quy nếu chuỗi JSON bị lỗi cú pháp nhỏ."""
    result: Dict[str, Any] = {}
    
    # Tìm answer
    answer_match = re.search(r'"answer"\s*:\s*"((?:\\.|[^"\\])*)"', text, re.DOTALL)
    if answer_match:
        try:
            result["answer"] = json.loads(f'"{answer_match.group(1)}"')
        except Exception:
            result["answer"] = answer_match.group(1).encode().decode("unicode_escape", errors="ignore")
    else:
        return None

    # Tìm citations
    citations_match = re.search(r'"citations"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    if citations_match:
        items = re.findall(r'"([^"]+)"', citations_match.group(1))
        result["citations"] = items
    else:
        result["citations"] = []

    # Tìm refused
    refused_match = re.search(r'"refused"\s*:\s*(true|false)', text, re.IGNORECASE)
    if refused_match:
        result["refused"] = refused_match.group(1).lower() == "true"
    else:
        result["refused"] = False

    # Tìm reason
    reason_match = re.search(r'"reason"\s*:\s*(?:"((?:\\.|[^"\\])*)"|null)', text, re.DOTALL)
    if reason_match:
        if reason_match.group(1):
            try:
                result["reason"] = json.loads(f'"{reason_match.group(1)}"')
            except Exception:
                result["reason"] = reason_match.group(1)
        else:
            result["reason"] = None
    else:
        result["reason"] = None

    return result
