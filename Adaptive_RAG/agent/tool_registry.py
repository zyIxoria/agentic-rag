"""
Tool Registry and Function Calling Schemas for Central Legal Agent.
Định nghĩa đặc tả công cụ chuẩn OpenAI Function Calling / Gemini Tool API
và cơ chế dispatch thực thi các công cụ tra cứu, tính toán số học, tìm kiếm live web.
"""

from __future__ import annotations
import json
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

from RAG.retriever.schema import RetrievedChunk
from Adaptive_RAG.tools.legal_calculator import (
    calculate_overtime_pay,
    calculate_severance_or_redundancy,
    calculate_work_accident_benefit,
    calculate_unemployment_benefit,
)
from CRAG.search.web_searcher import LegalWebSearcher

logger = logging.getLogger(__name__)


@dataclass
class ToolExecutionResult:
    """Kết quả thực thi một công cụ của Tác tử Trung tâm."""
    tool_name: str
    arguments: Dict[str, Any]
    success: bool
    data: Any
    output_text: str
    error: Optional[str] = None


# =============================================================================
# ĐẶC TẢ SCHEMA GỌI HÀM CHUẨN OPENAI / GEMINI API
# =============================================================================

LEGAL_TOOL_DEFINITIONS = [
    {
        "name": "retrieve_legal_doc",
        "description": (
            "Tra cứu các điều khoản pháp luật lao động, văn bản quy phạm từ kho dữ liệu nội bộ "
            "(Bộ luật Lao động 2019, Luật Việc làm 2013, Luật BHXH, Luật ATVSLĐ 2015, Nghị định 145/2020, Nghị định 12/2022). "
            "Sử dụng công cụ này đầu tiên khi cần tìm kiếm căn cứ pháp lý để giải quyết tình huống."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu truy vấn ngữ nghĩa hoặc từ khóa pháp lý (ví dụ: 'thời gian thử việc tối đa của người quản lý', 'điều kiện hưởng trợ cấp thôi việc').",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Số lượng điều khoản / chunks cần lấy về. Mặc định là 5.",
                    "default": 5,
                },
                "as_of_date": {
                    "type": "string",
                    "description": "Thời điểm hiệu lực cần áp dụng (định dạng YYYY-MM-DD), nếu người dùng hỏi về một thời điểm lịch sử cụ thể.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "calculate_overtime_pay",
        "description": (
            "Công cụ tính toán số học biểu tượng cho tiền lương làm thêm giờ ban ngày hoặc ban đêm "
            "theo đúng quy định tại Điều 98 Bộ luật Lao động 2019. Tự động áp dụng tỷ lệ 150%, 200%, 300% "
            "và cộng thêm 30% (làm đêm) + 20% (làm thêm giờ ban đêm) tránh hoàn toàn sai lệch tính nhẩm."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "hourly_wage": {
                    "type": "number",
                    "description": "Tiền lương giờ thực trả của công việc đang làm vào ngày làm việc bình thường (VNĐ/giờ).",
                },
                "hours": {
                    "type": "number",
                    "description": "Số giờ làm thêm cần tính.",
                },
                "day_type": {
                    "type": "string",
                    "enum": ["normal", "weekend", "holiday"],
                    "description": "Loại ngày làm việc: 'normal' (ngày thường), 'weekend' (ngày nghỉ hằng tuần), 'holiday' (ngày lễ, tết, ngày nghỉ có hưởng lương).",
                },
                "is_night": {
                    "type": "boolean",
                    "description": "True nếu làm thêm vào ban đêm (từ 22:00 đến 06:00 sáng hôm sau); False nếu làm ban ngày.",
                    "default": False,
                },
            },
            "required": ["hourly_wage", "hours", "day_type"],
        },
    },
    {
        "name": "calculate_severance_or_redundancy",
        "description": (
            "Công cụ tính toán số học biểu tượng cho trợ cấp thôi việc (Điều 46 BLLĐ 2019) hoặc "
            "trợ cấp mất việc làm (Điều 47 BLLĐ 2019). Tự động khấu trừ thời gian tham gia BHTN "
            "và áp dụng quy tắc làm tròn thời gian làm việc (từ đủ 1 đến 6 tháng tính 1/2 năm; trên 6 tháng tính 1 năm)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "avg_monthly_salary_6m": {
                    "type": "number",
                    "description": "Tiền lương bình quân theo hợp đồng lao động của 06 tháng liền kề trước khi thôi việc/mất việc làm (VNĐ).",
                },
                "total_months_worked": {
                    "type": "number",
                    "description": "Tổng thời gian thực tế người lao động đã làm việc cho người sử dụng lao động (tính theo tháng).",
                },
                "months_bhtn_participated": {
                    "type": "number",
                    "description": "Thời gian người lao động đã tham gia bảo hiểm thất nghiệp (BHTN) theo quy định của pháp luật (tính theo tháng). Mặc định là 0.",
                    "default": 0.0,
                },
                "allowance_type": {
                    "type": "string",
                    "enum": ["thoi_viec", "mat_viec"],
                    "description": "'thoi_viec' (Trợ cấp thôi việc - Điều 46, 0.5 tháng lương/năm) hoặc 'mat_viec' (Trợ cấp mất việc làm do thay đổi cơ cấu/sáp nhập - Điều 47, 1 tháng lương/năm, tối thiểu 2 tháng lương).",
                    "default": "thoi_viec",
                },
            },
            "required": ["avg_monthly_salary_6m", "total_months_worked"],
        },
    },
    {
        "name": "calculate_work_accident_benefit",
        "description": (
            "Công cụ tính toán tiền bồi thường hoặc trợ cấp tai nạn lao động, bệnh nghề nghiệp "
            "theo Điều 38 Luật An toàn, vệ sinh lao động 2015. Tính chính xác thang tỷ lệ suy giảm K%: "
            "suy giảm 5-10% = 1.5 tháng; 11-80% = 1.5 + (K-10)*0.4 tháng; >=81% = 30 tháng."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "monthly_salary": {
                    "type": "number",
                    "description": "Tiền lương làm căn cứ đóng bảo hiểm hoặc lương theo HĐLĐ của tháng liền kề trước khi bị TNLĐ (VNĐ).",
                },
                "impairment_percentage": {
                    "type": "number",
                    "description": "Tỷ lệ suy giảm khả năng lao động do Hội đồng Giám định Y khoa kết luận (từ 5% đến 100%).",
                },
                "is_worker_fault": {
                    "type": "boolean",
                    "description": "True nếu tai nạn xảy ra do lỗi hoàn toàn của chính người lao động (chỉ được nhận trợ cấp ít nhất 40% mức bồi thường). False nếu do lỗi NSDLĐ hoặc không do lỗi người lao động.",
                    "default": False,
                },
            },
            "required": ["monthly_salary", "impairment_percentage"],
        },
    },
    {
        "name": "calculate_unemployment_benefit",
        "description": (
            "Công cụ tính mức hưởng trợ cấp thất nghiệp hằng tháng và thời gian hưởng "
            "theo Điều 50 Luật Việc làm 2013 (60% mức lương bình quân 6 tháng đóng BHTN, khống chế trần 5 lần lương tối thiểu vùng)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "avg_monthly_salary_6m_bhtn": {
                    "type": "number",
                    "description": "Mức lương bình quân đóng BHTN của 06 tháng liền kề trước khi thất nghiệp (VNĐ).",
                },
                "months_bhtn_contributed": {
                    "type": "number",
                    "description": "Tổng số tháng đã đóng bảo hiểm thất nghiệp đủ điều kiện hưởng.",
                },
                "regional_minimum_wage": {
                    "type": "number",
                    "description": "Mức lương tối thiểu vùng tại thời điểm chấm dứt hợp đồng lao động để khống chế mức trần (ví dụ: 4.960.000 VNĐ cho Vùng I).",
                },
            },
            "required": ["avg_monthly_salary_6m_bhtn", "months_bhtn_contributed"],
        },
    },
    {
        "name": "web_search_fallback",
        "description": (
            "Tra cứu mở rộng trên Live Web thực tế (qua DuckDuckGo/Tavily/Serper) ưu tiên các trang "
            "pháp luật Việt Nam (thuvienphapluat.vn, luatvietnam.vn, moj.gov.vn, chinhphu.vn) "
            "khi kho dữ liệu nội bộ không có đủ thông tin hoặc khi cần xác minh văn bản mới ban hành."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Từ khóa tra cứu tìm kiếm trên Internet.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Số lượng kết quả tìm kiếm cần lấy về (mặc định 3).",
                    "default": 3,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "ask_clarification",
        "description": (
            "Yêu cầu người dùng làm rõ hoặc bổ sung dữ kiện khi câu hỏi thiếu thông tin cốt lõi "
            "(ví dụ: thiếu mức lương, thiếu số năm làm việc, thiếu tỷ lệ suy giảm, thiếu ca làm việc) "
            "để tránh võ đoán hoặc tính toán sai ngữ cảnh."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "missing_info": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách các thông tin/dữ kiện còn thiếu.",
                },
                "clarification_question": {
                    "type": "string",
                    "description": "Câu hỏi làm rõ gửi tới người dùng một cách lịch sự, nêu rõ các phương án giả định nếu có.",
                },
            },
            "required": ["missing_info", "clarification_question"],
        },
    },
]


class LegalToolRegistry:
    """
    Registry quản lý các công cụ của Tác tử Trung tâm, hỗ trợ xuất đặc tả
    cho OpenAI / Gemini API và dispatch thực thi an toàn.
    """

    def __init__(
        self,
        retriever: Optional[Any] = None,
        web_searcher: Optional[LegalWebSearcher] = None,
    ):
        self.retriever = retriever
        self.web_searcher = web_searcher or LegalWebSearcher()
        self._handlers: Dict[str, Callable] = {
            "retrieve_legal_doc": self._handle_retrieve_legal_doc,
            "calculate_overtime_pay": self._handle_calculate_overtime,
            "calculate_severance_or_redundancy": self._handle_calculate_severance,
            "calculate_work_accident_benefit": self._handle_calculate_work_accident,
            "calculate_unemployment_benefit": self._handle_calculate_unemployment,
            "web_search_fallback": self._handle_web_search,
            "ask_clarification": self._handle_ask_clarification,
        }

    @staticmethod
    def get_openai_tools() -> List[Dict[str, Any]]:
        """Trả về danh sách định dạng tools chuẩn OpenAI Function Calling."""
        return [
            {"type": "function", "function": tool_def}
            for tool_def in LEGAL_TOOL_DEFINITIONS
        ]

    @staticmethod
    def get_gemini_tools() -> List[Dict[str, Any]]:
        """Trả về danh sách định dạng tools chuẩn Gemini Function Declarations."""
        return LEGAL_TOOL_DEFINITIONS

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolExecutionResult:
        """
        Thực thi công cụ theo tên và tham số truyền vào với cơ chế bắt lỗi an toàn.
        """
        handler = self._handlers.get(tool_name)
        if not handler:
            err_msg = f"Công cụ '{tool_name}' không tồn tại trong hệ thống."
            logger.error(err_msg)
            return ToolExecutionResult(
                tool_name=tool_name,
                arguments=arguments,
                success=False,
                data=None,
                output_text=f"Lỗi: {err_msg}",
                error=err_msg,
            )

        try:
            return handler(arguments)
        except Exception as e:
            err_msg = f"Lỗi trong quá trình thực thi công cụ '{tool_name}': {str(e)}"
            logger.exception(err_msg)
            return ToolExecutionResult(
                tool_name=tool_name,
                arguments=arguments,
                success=False,
                data=None,
                output_text=f"Lỗi thực thi: {str(e)}",
                error=str(e),
            )

    # =========================================================================
    # TOOL HANDLERS
    # =========================================================================

    def _handle_retrieve_legal_doc(self, args: Dict[str, Any]) -> ToolExecutionResult:
        query = args.get("query", "").strip()
        top_k = int(args.get("top_k", 5))
        as_of_date = args.get("as_of_date")

        if not self.retriever:
            return ToolExecutionResult(
                tool_name="retrieve_legal_doc",
                arguments=args,
                success=False,
                data=[],
                output_text="Lỗi: Bộ truy xuất (retriever) chưa được cấu hình.",
                error="Retriever not initialized",
            )

        # Hỗ trợ lọc theo thời điểm hiệu lực nếu retriever là TemporalLegalRetriever
        if as_of_date and hasattr(self.retriever, "retrieve_temporal"):
            chunks = self.retriever.retrieve_temporal(query=query, top_k=top_k, as_of_date=as_of_date)
        else:
            chunks = self.retriever.retrieve(query=query, top_k=top_k)

        formatted_outputs = []
        for i, c in enumerate(chunks, 1):
            meta = getattr(c, "metadata", {}) or {}
            doc_name = meta.get("document_name") or getattr(c, "document_name", "Văn bản pháp luật")
            art = meta.get("article") or getattr(c, "article", "")
            title = meta.get("title") or getattr(c, "title", "")
            text = getattr(c, "content", "") or getattr(c, "text", "")
            score = getattr(c, "score", 0.0)
            formatted_outputs.append(
                f"[{i}] {doc_name} - {art} ({title}) [Score: {score:.3f}]:\n{text}"
            )

        output_str = "\n\n".join(formatted_outputs) if formatted_outputs else "Không tìm thấy điều khoản phù hợp."
        return ToolExecutionResult(
            tool_name="retrieve_legal_doc",
            arguments=args,
            success=True,
            data=chunks,
            output_text=output_str,
        )

    def _handle_calculate_overtime(self, args: Dict[str, Any]) -> ToolExecutionResult:
        res = calculate_overtime_pay(
            hourly_wage=float(args["hourly_wage"]),
            hours=float(args["hours"]),
            day_type=str(args["day_type"]),
            is_night=bool(args.get("is_night", False)),
        )
        return ToolExecutionResult(
            tool_name="calculate_overtime_pay",
            arguments=args,
            success=True,
            data=res,
            output_text=res.summary,
        )

    def _handle_calculate_severance(self, args: Dict[str, Any]) -> ToolExecutionResult:
        res = calculate_severance_or_redundancy(
            avg_monthly_salary_6m=float(args["avg_monthly_salary_6m"]),
            total_months_worked=float(args["total_months_worked"]),
            months_bhtn_participated=float(args.get("months_bhtn_participated", 0.0)),
            allowance_type=str(args.get("allowance_type", "thoi_viec")),
        )
        return ToolExecutionResult(
            tool_name="calculate_severance_or_redundancy",
            arguments=args,
            success=True,
            data=res,
            output_text=res.summary,
        )

    def _handle_calculate_work_accident(self, args: Dict[str, Any]) -> ToolExecutionResult:
        res = calculate_work_accident_benefit(
            monthly_salary=float(args["monthly_salary"]),
            impairment_percentage=float(args["impairment_percentage"]),
            is_worker_fault=bool(args.get("is_worker_fault", False)),
        )
        return ToolExecutionResult(
            tool_name="calculate_work_accident_benefit",
            arguments=args,
            success=True,
            data=res,
            output_text=res.summary,
        )

    def _handle_calculate_unemployment(self, args: Dict[str, Any]) -> ToolExecutionResult:
        reg_wage = args.get("regional_minimum_wage")
        reg_wage_float = float(reg_wage) if reg_wage is not None else None
        res = calculate_unemployment_benefit(
            avg_monthly_salary_6m_bhtn=float(args["avg_monthly_salary_6m_bhtn"]),
            months_bhtn_contributed=float(args["months_bhtn_contributed"]),
            regional_minimum_wage=reg_wage_float,
        )
        return ToolExecutionResult(
            tool_name="calculate_unemployment_benefit",
            arguments=args,
            success=True,
            data=res,
            output_text=res.summary,
        )

    def _handle_web_search(self, args: Dict[str, Any]) -> ToolExecutionResult:
        query = args.get("query", "").strip()
        top_k = int(args.get("top_k", 3))
        resp = self.web_searcher.search(query=query, top_k=top_k)

        formatted_results = []
        for i, item in enumerate(resp.results, 1):
            formatted_results.append(
                f"[{i}] {item.title} ({item.source_name})\nURL: {item.url}\nNội dung: {item.snippet}"
            )
        output_str = "\n\n".join(formatted_results) if formatted_results else "Không tìm thấy kết quả từ Web Search."

        return ToolExecutionResult(
            tool_name="web_search_fallback",
            arguments=args,
            success=True,
            data=resp,
            output_text=output_str,
        )

    def _handle_ask_clarification(self, args: Dict[str, Any]) -> ToolExecutionResult:
        missing = args.get("missing_info", [])
        question = args.get("clarification_question", "")
        summary = (
            f"[YÊU CẦU LÀM RÕ DỮ KIỆN]\n"
            f"Thông tin cần bổ sung: {', '.join(missing)}\n"
            f"Câu hỏi tới người dùng: {question}"
        )
        return ToolExecutionResult(
            tool_name="ask_clarification",
            arguments=args,
            success=True,
            data={"missing_info": missing, "clarification_question": question},
            output_text=summary,
        )
