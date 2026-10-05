"""mock_generator.py - Động cơ suy luận giả lập xác định (Deterministic Mock Legal Generator).

Phục vụ kiểm thử đơn vị, CI/CD và hoạt động ngoại tuyến:
- Tuân thủ 100% 10 nguyên tắc hệ thống.
- Nhận diện và phòng chống Prompt Injection trong context.
- Từ chối nghiêm ngặt khi thiếu dữ liệu bằng câu từ chối chuẩn mực.
- Trích dẫn chính xác [SOURCE N].
"""

from __future__ import annotations
import re
import json
import time
from typing import List, Dict, Any, Optional

from RAG.generator.base import BaseLegalGenerator
from RAG.generator.schema import GenerationRequest, GenerationResult
from RAG.generator.parser import parse_generator_output
from RAG.prompts.legal_prompts import STANDARD_REFUSAL_ANSWER


class MockLegalGenerator(BaseLegalGenerator):
    """Bộ sinh giả lập xác định kiểm tra logic RAG mà không cần gọi API đám mây."""

    def __init__(self, model_name: str = "mock-legal-generator-v1"):
        self.model_name = model_name

    def generate_structured(self, request: GenerationRequest) -> GenerationResult:
        """Sinh câu trả lời dựa trên phân tích cấu trúc ngữ cảnh và câu hỏi."""
        start_time = time.perf_counter()
        question = request.question.strip()
        context = request.context.strip()

        # 1. Kiểm tra ngữ cảnh rỗng hoặc thông báo rỗng
        if not context or "không tìm thấy đoạn văn bản phù hợp" in context.lower():
            raw_json = json.dumps({
                "answer": STANDARD_REFUSAL_ANSWER,
                "citations": [],
                "refused": True,
                "reason": "Ngữ cảnh được cung cấp hoàn toàn rỗng hoặc không có dữ liệu phù hợp."
            }, ensure_ascii=False)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            parsed = parse_generator_output(raw_json)
            return GenerationResult(
                answer=parsed.answer,
                citations=parsed.citations,
                refused=parsed.refused,
                reason=parsed.reason,
                raw_response=raw_json,
                model_name=self.model_name,
                provider="mock",
                latency_ms=round(elapsed_ms, 2)
            )

        # 2. Bóc tách các nguồn [SOURCE N] từ context
        sources = self._extract_sources_from_context(context)

        # 3. Phòng vệ Prompt Injection & Làm sạch nội dung:
        # Nếu trong context có lệnh tiêm nhiễm giả mạo, generator loại bỏ hoàn toàn các câu lệnh đó
        # Toàn bộ dữ liệu context được coi là dữ liệu thụ động
        sources = [self._sanitize_source(s) for s in sources]

        # 4. Kiểm tra câu hỏi ngoài phạm vi (Out-of-scope / Unknown question):
        # Phát hiện các chủ đề hoàn toàn không thuộc phạm vi pháp luật lao động
        q_lower = question.lower()
        out_of_scope_keywords = [
            "nhãn hiệu", "thương hiệu", "madrid", "sáng chế", "bản quyền",
            "sở hữu trí tuệ", "visa", "hộ chiếu", "đại sứ quán", "ly hôn",
            "kết hôn", "thừa kế", "giao thông", "đất đai", "nhà đất",
            "chứng khoán", "tiền ảo", "thuế giá trị gia tăng",
            "bóng đá", "thể thao", "ngoại hạng", "vé xem", "mua vé",
            "ca nhạc", "phim ảnh", "du lịch", "thời tiết", "nấu ăn", "game"
        ]
        if any(kw in q_lower for kw in out_of_scope_keywords):
            raw_json = json.dumps({
                "answer": STANDARD_REFUSAL_ANSWER,
                "citations": [],
                "refused": True,
                "reason": "Câu hỏi thuộc lĩnh vực ngoài phạm vi các tài liệu pháp luật lao động được cung cấp."
            }, ensure_ascii=False)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            parsed = parse_generator_output(raw_json)
            return GenerationResult(
                answer=parsed.answer,
                citations=parsed.citations,
                refused=parsed.refused,
                reason=parsed.reason,
                raw_response=raw_json,
                model_name=self.model_name,
                provider="mock",
                latency_ms=round(elapsed_ms, 2)
            )

        domain_stopwords = {
            "của", "cho", "các", "những", "được", "trong", "theo", "nào", "gì", "như",
            "thế", "khi", "quy", "định", "lao", "động", "người", "sử", "dụng", "nhiêu",
            "phần", "trăm", "phải", "khoản", "điều", "về", "có", "hay", "với", "tại",
            "ở", "này", "đó", "ra", "sao", "bao", "làm", "một", "hai", "ba",
            "thủ", "tục", "hồ", "sơ", "trình", "tự", "thực", "hiện", "áp", "dụng",
            "vấn", "đề", "trường", "hợp", "điều", "kiện", "thời", "gian", "mức", "đăng", "ký",
            "cách", "xem", "mua", "mùa", "giải"
        }
        
        # Bóc tách các từ khóa chủ đề cốt lõi của câu hỏi
        q_words = re.findall(r"\w+", q_lower)
        significant_q_keywords = [w for w in q_words if len(w) >= 2 and w not in domain_stopwords]

        # Nếu câu hỏi hỏi về những chủ đề hoàn toàn không có trong context
        is_relevant = False
        matching_sources = []
        
        for src in sources:
            src_text = f"{src.get('article', '')} {src.get('title', '')} {src.get('content', '')}".lower()
            if not significant_q_keywords:
                continue
            common = [kw for kw in significant_q_keywords if kw in src_text]
            # Bắt buộc khớp ít nhất 1 từ khóa đặc thù có nghĩa (ngoài stopwords lao động phổ biến)
            # Hoặc tỷ lệ khớp từ khóa đủ cao
            if len(common) >= 1:
                # Kiểm tra thêm nếu từ khóa là từ chung, cần khớp tỷ lệ
                overlap_ratio = len(common) / len(significant_q_keywords)
                if len(common) >= 2 or overlap_ratio >= 0.2:
                    is_relevant = True
                    matching_sources.append(src)

        # Nếu không có nguồn nào chứa thông tin liên quan tới câu hỏi -> Từ chối
        if not is_relevant or not matching_sources:
            raw_json = json.dumps({
                "answer": STANDARD_REFUSAL_ANSWER,
                "citations": [],
                "refused": True,
                "reason": "Dữ liệu ngữ cảnh không chứa điều khoản hay căn cứ trả lời câu hỏi."
            }, ensure_ascii=False)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            parsed = parse_generator_output(raw_json)
            return GenerationResult(
                answer=parsed.answer,
                citations=parsed.citations,
                refused=parsed.refused,
                reason=parsed.reason,
                raw_response=raw_json,
                model_name=self.model_name,
                provider="mock",
                latency_ms=round(elapsed_ms, 2)
            )

        # 5. Xử lý trường hợp mâu thuẫn (Conflicting sources)
        # Nhận diện nếu 2 nguồn cùng nói về một nội dung nhưng có số liệu/quy định khác nhau
        is_conflicting = False
        if len(matching_sources) >= 2:
            s1_text = matching_sources[0]["content"]
            s2_text = matching_sources[1]["content"]
            # Kiểm tra xem có dấu hiệu xung đột thời gian, ngày, số tiền hoặc quy định
            if ("không quá" in s1_text and "không quá" in s2_text and s1_text != s2_text) or \
               ("áp dụng" in s1_text and "không áp dụng" in s2_text) or \
               ("mâu thuẫn" in q_lower or "xung đột" in q_lower or "khác nhau" in q_lower):
                is_conflicting = True

        citations = [src["label"].strip("[]") for src in matching_sources]

        if is_conflicting:
            src1 = matching_sources[0]
            src2 = matching_sources[1]
            answer = (
                f"Theo quy định tại {src1['label']} ({src1.get('doc_title', 'Văn bản')}, {src1.get('article', '')}), "
                f"nội dung quy định: {src1['content'].strip()}.\n\n"
                f"Tuy nhiên, theo quy định tại {src2['label']} ({src2.get('doc_title', 'Văn bản')}, {src2.get('article', '')}), "
                f"nội dung lại quy định: {src2['content'].strip()}.\n\n"
                f"Do có sự khác biệt/mâu thuẫn giữa hai nguồn căn cứ pháp lý này ({src1['label']} và {src2['label']}), "
                f"cần đối chiếu phạm vi áp dụng hoặc văn bản quy định chi tiết có hiệu lực mới hơn."
            )
            raw_json = json.dumps({
                "answer": answer,
                "citations": citations[:2],
                "refused": False,
                "reason": None
            }, ensure_ascii=False)

        elif len(matching_sources) == 1:
            src = matching_sources[0]
            doc_info = f"{src.get('doc_title', '')}"
            if src.get('doc_number'):
                doc_info += f" (số {src.get('doc_number')})"
            art_info = f"{src.get('article', '')}"
            if src.get('title'):
                art_info += f" ({src.get('title')})"

            answer = (
                f"Căn cứ theo quy định tại {src['label']} [{doc_info}, {art_info}]:\n"
                f"{src['content'].strip()}"
            )
            raw_json = json.dumps({
                "answer": answer,
                "citations": [src["label"].strip("[]")],
                "refused": False,
                "reason": None
            }, ensure_ascii=False)

        else:
            # Nhiều nguồn bổ trợ cho nhau
            answer_parts = ["Căn cứ theo các tài liệu pháp lý được cung cấp:"]
            used_citations = []
            for src in matching_sources:
                tag = src["label"].strip("[]")
                used_citations.append(tag)
                doc_desc = src.get('doc_title', '')
                art_desc = src.get('article', '')
                answer_parts.append(
                    f"- Theo {src['label']} ({doc_desc}, {art_desc}): {src['content'].strip()}"
                )
            
            answer = "\n".join(answer_parts)
            raw_json = json.dumps({
                "answer": answer,
                "citations": used_citations,
                "refused": False,
                "reason": None
            }, ensure_ascii=False)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        parsed = parse_generator_output(raw_json)

        return GenerationResult(
            answer=parsed.answer,
            citations=parsed.citations,
            refused=parsed.refused,
            reason=parsed.reason,
            raw_response=raw_json,
            model_name=self.model_name,
            provider="mock",
            latency_ms=round(elapsed_ms, 2)
        )

    def _extract_sources_from_context(self, context: str) -> List[Dict[str, Any]]:
        """Bóc tách các khối [SOURCE N] từ chuỗi context."""
        sources = []
        # Tìm tất cả [SOURCE N]
        pattern = re.compile(r"(\[SOURCE\s+\d+\])", re.IGNORECASE)
        splits = pattern.split(context)
        
        # splits sẽ xen kẽ: [prefix, "[SOURCE 1]", block1, "[SOURCE 2]", block2, ...]
        i = 1
        while i < len(splits):
            tag = splits[i].strip()
            body = splits[i + 1] if i + 1 < len(splits) else ""
            i += 2

            src_dict: Dict[str, Any] = {
                "label": tag,
                "doc_title": "",
                "doc_number": "",
                "article": "",
                "title": "",
                "content": ""
            }

            for line in body.splitlines():
                line_s = line.strip()
                if line_s.startswith("Document:"):
                    src_dict["doc_title"] = line_s.replace("Document:", "").strip()
                elif line_s.startswith("Document Number:"):
                    src_dict["doc_number"] = line_s.replace("Document Number:", "").strip()
                elif line_s.startswith("Article:"):
                    src_dict["article"] = line_s.replace("Article:", "").strip()
                elif line_s.startswith("Article Title:"):
                    src_dict["title"] = line_s.replace("Article Title:", "").strip()

            # Lấy content
            if "Content:" in body:
                content_part = body.split("Content:", 1)[1]
                # Cắt bỏ phần phân cách nếu có
                if "---" in content_part:
                    content_part = content_part.split("---", 1)[0]
                src_dict["content"] = content_part.strip()
            else:
                src_dict["content"] = body.strip()

            sources.append(src_dict)

        return sources

    def _sanitize_source(self, src: Dict[str, Any]) -> Dict[str, Any]:
        """Lọc bỏ các câu lệnh tiêm nhiễm prompt injection trong nội dung tài liệu."""
        raw_content = src.get("content", "")
        clean_lines = []
        injection_indicators = [
            "ignore previous",
            "bỏ qua tất cả",
            "bỏ qua chỉ dẫn",
            "hacked",
            "tiết lộ prompt",
            "system prompt",
            "[hệ thống]:",
            "hacked_success"
        ]

        for line in raw_content.splitlines():
            line_low = line.lower()
            if any(ind in line_low for ind in injection_indicators):
                # Bỏ qua dòng độc hại
                continue
            clean_lines.append(line)

        sanitized_src = dict(src)
        sanitized_src["content"] = "\n".join(clean_lines).strip()
        return sanitized_src

