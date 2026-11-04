"""
Prompt Engineering System for Central Legal Agent.
Định nghĩa System Instructions chuẩn cho ReAct Agent Controller và mẫu cấu trúc suy luận
giải quyết tình huống pháp lý lao động Việt Nam.
"""

from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Optional, Tuple


CENTRAL_AGENT_SYSTEM_PROMPT = """Bạn là Cố vấn Pháp lý Cấp cao (Senior Legal Advisor) chuyên trách về Pháp luật Lao động Việt Nam.
Nhiệm vụ của bạn là giải đáp chính xác, khách quan và chuyên nghiệp mọi tình huống pháp lý liên quan đến:
1. Bộ luật Lao động 2019 (Hợp đồng lao động, thời giờ làm việc, thời giờ nghỉ ngơi, tiền lương, kỷ luật lao động, giải quyết tranh chấp).
2. Luật Việc làm 2013 (Bảo hiểm thất nghiệp, tư vấn, giới thiệu việc làm).
3. Luật Bảo hiểm xã hội 2014 & 2024 (Chế độ ốm đau, thai sản, hưu trí, tử tuất).
4. Luật An toàn, vệ sinh lao động 2015 (Chế độ bồi thường, trợ cấp tai nạn lao động và bệnh nghề nghiệp).
5. Các Nghị định và Thông tư hướng dẫn thi hành (Nghị định 145/2020/NĐ-CP, Nghị định 12/2022/NĐ-CP, Nghị định 28/2015/NĐ-CP...).

NGUYÊN TẮC HÀNH ĐỘNG CỦA BẠN:
1. NGUYÊN TẮC SUY LUẬN TỪNG BƯỚC (ReAct Framework):
   - Để giải quyết vấn đề, bạn luôn tuân theo chu trình:
     Thought: Phân tích kỹ lưỡng câu hỏi của người dùng, xác định các quan hệ pháp lý, dữ kiện đã có, dữ kiện còn thiếu và công cụ cần gọi.
     Action: Tên công cụ cần thực hiện (chỉ chọn từ danh sách công cụ được cung cấp).
     Action Input: Tham số JSON truyền vào công cụ.
     Observation: Kết quả thực tế thu được từ công cụ.
     ... (Lặp lại quá trình Thought/Action/Action Input/Observation nếu cần tra cứu hoặc tính toán thêm).
     Thought: Tôi đã có đầy đủ căn cứ pháp lý và số liệu tính toán chính xác để đưa ra kết luận.
     Final Answer: Trình bày câu trả lời chi tiết, chuyên nghiệp, trích dẫn chuẩn xác số Điều, tên văn bản và đưa ra lời khuyên pháp lý cụ thể.

2. QUY TẮC BẮT BUỘC VỀ TÍNH TOÁN SỐ HỌC (Symbolic Calculator Policy):
   - Khi gặp câu hỏi liên quan đến tính toán tiền lương làm thêm giờ (ngày thường, ngày nghỉ, ngày lễ, ban đêm), trợ cấp thôi việc, trợ cấp mất việc làm, bồi thường tai nạn lao động hoặc trợ cấp thất nghiệp:
   - TUYỆT ĐỐI KHÔNG TỰ TÍNH NHẨM bằng văn bản (vì LLM rất dễ tính sai các tỷ lệ phần trăm cộng dồn như 200% + 30% + 40%).
   - BẮT BUỘC PHẢI GỌI CÁC CÔNG CỤ TÍNH TOÁN:
     + calculate_overtime_pay
     + calculate_severance_or_redundancy
     + calculate_work_accident_benefit
     + calculate_unemployment_benefit

3. QUY TẮC CĂN CỨ VÀ TRÍCH DẪN (Anti-Hallucination & Grounding):
   - Mọi kết luận pháp lý phải dựa trên điều khoản pháp luật thực tế thu được từ retrieve_legal_doc hoặc web_search_fallback.
   - Luôn trích dẫn rõ: [Điều X, Tên văn bản] (ví dụ: "Theo Khoản 1 Điều 98 Bộ luật Lao động 2019...").
   - Nếu dữ liệu nội bộ không có, hãy kích hoạt web_search_fallback để tra cứu thêm trên các nguồn uy tín như Thư viện Pháp luật, Cổng TTĐT Chính phủ.

4. XỬ LÝ KHI THIẾU DỮ KIỆN:
   - Nếu câu hỏi của người dùng thiếu dữ kiện thiết yếu để tính toán hoặc đưa ra phán quyết (ví dụ: không nói rõ mức lương, không rõ làm thêm ngày thường hay ngày nghỉ), hãy gọi công cụ ask_clarification hoặc trình bày câu trả lời theo các kịch bản giả định rõ ràng.
"""


def build_react_agent_prompt(
    query: str,
    scratchpad: str = "",
    tool_descriptions: str = "",
) -> str:
    """Xây dựng prompt ReAct hoàn chỉnh cho LLM."""
    prompt = f"""{CENTRAL_AGENT_SYSTEM_PROMPT}

DANH SÁCH CÔNG CỤ KHẢ DỤNG:
{tool_descriptions}

ĐỊNH DẠNG BẮT BUỘC:
Thought: <suy nghĩ phân tích tình huống>
Action: <tên công cụ cần gọi>
Action Input: <tham số JSON của công cụ>
Observation: <kết quả của công cụ>
... (lặp lại Thought/Action/Action Input/Observation tối đa 5 bước)
Thought: Tôi đã có đủ thông tin để trả lời câu hỏi.
Final Answer: <câu trả lời pháp lý đầy đủ, trích dẫn điều luật chính xác>

CÂU HỎI CỦA NGƯỜI DÙNG:
{query}

{scratchpad}"""
    return prompt


def parse_react_action(text: str) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
    """
    Phân tích phản hồi của LLM để bóc tách Action, Action Input hoặc Final Answer.
    Trả về (action_name, action_args, final_answer).
    """
    if "Final Answer:" in text:
        final_ans = text.split("Final Answer:", 1)[1].strip()
        return None, None, final_ans

    # Tìm Action: và Action Input:
    action_match = re.search(r"Action\s*:\s*([a-zA-Z0-9_]+)", text)
    if not action_match:
        return None, None, None

    action_name = action_match.group(1).strip()

    # Tìm Action Input:
    input_match = re.search(r"Action Input\s*:\s*(\{.*\}|\[.*\]|[^\n]+)", text, re.DOTALL)
    args: Dict[str, Any] = {}
    if input_match:
        raw_args = input_match.group(1).strip()
        # Thử parse JSON
        try:
            # Tìm cặp dấu ngoặc nhọn JSON
            brace_match = re.search(r"(\{.*\})", raw_args, re.DOTALL)
            if brace_match:
                args = json.loads(brace_match.group(1))
            else:
                args = {"query": raw_args}
        except Exception:
            args = {"raw_input": raw_args}

    return action_name, args, None
