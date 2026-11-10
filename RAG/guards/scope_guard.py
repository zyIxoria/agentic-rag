"""scope_guard.py - Tier 1: Scope & Intent Boundary Gate (Shared Scope Guard).

Cung cấp chốt chặn phạm vi độc lập dùng chung cho Traditional RAG và CRAG (và đồng bộ với Module 0 Adaptive RAG).
- Phân loại toàn câu (Holistic Classification): VALID_LABOR, OUT_OF_SCOPE, AMBIGUOUS.
- Nhận diện các lĩnh vực phi lao động (Hình sự, Đất đai, Hôn nhân gia đình, Giao thông, v.v.).
- Bảo vệ các câu hỏi đời thường nhưng thực chất về quan hệ lao động (sếp, công ty, trừ lương, đuổi ngang...).
"""

from __future__ import annotations
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger("RAG.guards.scope_guard")


class ScopeCheckResult(BaseModel):
    """Kết quả kiểm tra phạm vi và ý định từ Tier 1 Scope Guard."""

    is_valid_labor: bool = Field(default=True, description="True nếu câu hỏi thuộc phạm vi pháp luật lao động")
    intent: str = Field(default="VALID_LABOR", description="Nhãn ý định: VALID_LABOR, OUT_OF_SCOPE, AMBIGUOUS")
    trigger_refusal: bool = Field(default=False, description="True nếu cần dừng luồng xử lý và từ chối/yêu cầu làm rõ")
    refusal_reason: Optional[str] = Field(default=None, description="Lý do từ chối kỹ thuật")
    refusal_message: Optional[str] = Field(default=None, description="Thông điệp phản hồi chuẩn mực cho người dùng")
    detected_domain: Optional[str] = Field(default=None, description="Lĩnh vực phi lao động được phát hiện (nếu có)")


class SharedScopeGuard:
    """Chốt chặn ranh giới phạm vi và ý định (Tier 1 Guard)."""

    OUT_OF_SCOPE_DOMAINS: Dict[str, List[str]] = {
        "criminal": [
            r"\b(tội\s+phạm|phạt\s+tù|án\s+treo|truy\s+cứu\s+trách\s+nhiệm\s+hình\s+sự|bộ\s+luật\s+hình\s+sự)\b",
            r"\b(trộm\s+cắp\s+tài\s+sản|tổ\s+chức\s+đánh\s+bạc|cướp\s+giật|ma\s+túy|lừa\s+đảo\s+chiếm\s+đoạt)\b",
            r"\b(khởi\s+tố\s+vụ\s+án|bị\s+can|bị\s+cáo|viện\s+kiểm\s+sát|tạm\s+giam|lệnh\s+bắt)\b",
        ],
        "marriage_family_civil": [
            r"\b(ly\s+hôn|đơn\s+phương\s+ly\s+hôn|kết\s+hôn|đăng\s+ký\s+kết\s+hôn|hôn\s+nhân\s+và\s+gia\s+đình)\b",
            r"\b(quyền\s+nuôi\s+con\s+sau\s+ly\s+hôn|chia\s+tài\s+sản\s+chung|cấp\s+dưỡng\s+cho\s+con|con\s+ngoài\s+giá\s+thú)\b",
            r"\b(thừa\s+kế|di\s+chúc|phân\s+chia\s+di\s+sản|hàng\s+thừa\s+kế|di\s+sản\s+thừa\s+kế|di\s+chúc\s+miệng)\b",
            r"\b(hợp\s+đồng\s+thuê\s+nhà|hợp\s+đồng\s+mua\s+bán\s+nhà|đặt\s+cọc\s+mua\s+đất)\b",
        ],
        "land_real_estate": [
            r"\b(sổ\s+đỏ|sổ\s+hồng|giấy\s+chứng\s+nhận\s+quyền\s+sử\s+dụng\s+đất|luật\s+đất\s+đai)\b",
            r"\b(chuyển\s+mục\s+đích\s+sử\s+dụng\s+đất|đất\s+nông\s+nghiệp|đất\s+trồng\s+cây|đất\s+ở|tiền\s+sử\s+dụng\s+đất)\b",
            r"\b(thu\s+hồi\s+đất|đền\s+bù\s+giải\s+tỏa|bồi\s+thường\s+đất|tranh\s+chấp\s+ranh\s+giới\s+đất)\b",
            r"\b(công\s+chứng.*(hợp\s+đồng\s+mua\s+bán|chuyển\s+nhượng).*đất)\b",
        ],
        "corporate_commercial": [
            r"\b(thành\s+lập\s+công\s+ty|đăng\s+ký\s+kinh\s+doanh|phòng\s+đăng\s+ký\s+kinh\s+doanh|sở\s+kế\s+hoạch)\b",
            r"\b(công\s+ty\s+tnhh\s+2\s+thành\s+viên|công\s+ty\s+cổ\s+phần|đại\s+hội\s+đồng\s+cổ\s+đông|hội\s+đồng\s+quản\s+trị)\b",
            r"\b(phá\s+sản|mở\s+thủ\s+tục\s+phá\s+sản|mất\s+khả\s+năng\s+thanh\s+toán|chủ\s+nợ\s+nộp\s+đơn)\b",
            r"\b(trọng\s+tài\s+thương\s+mại|trung\s+tâm\s+trọng\s+tài|mua\s+bán\s+hàng\s+hóa\s+quốc\s+tế)\b",
        ],
        "tax_financial": [
            r"\b(thuế\s+giá\s+trị\s+gia\s+tăng|thuế\s+vat|hóa\s+đơn\s+vat|hóa\s+đơn\s+điện\s+tử)\b",
            r"\b(thuế\s+chuyển\s+nhượng\s+bất\s+động\s+sản|miễn\s+thuế\s+nhà\s+duy\s+nhất)\b",
            r"\b(thuế\s+trúng\s+thưởng|vietlott|xổ\s+số|tiền\s+ảo|bitcoin|crypto|chứng\s+khoán|cổ\s+phiếu)\b",
        ],
        "traffic_administrative": [
            r"\b(nồng\s+độ\s+cồn|thổi\s+nồng\s+độ\s+cồn|vượt\s+đèn\s+đỏ|bằng\s+lái\s+xe|giao\s+thông\s+đường\s+bộ)\b",
            r"\b(bảo\s+hiểm\s+xe\s+máy|bảo\s+hiểm\s+ô\s+tô|bảo\s+hiểm\s+thân\s+vỏ)\b",
            r"\b(hộ\s+chiếu|visa\s+schengen|đại\s+sứ\s+quán|xuất\s+nhập\s+cảnh)\b",
            r"\b(căn\s+cước\s+công\s+dân|cccd|đăng\s+ký\s+thường\s+trú|tạm\s+trú|hộ\s+khẩu)\b",
            r"\b(xe\s+mô\s+tô|xe\s+gắn\s+máy|đường\s+cao\s+tốc|tước\s+giấy\s+phép\s+lái\s+xe|lệ\s+phí\s+trước\s+bạ|xe\s+ô\s+tô\s+con)\b",
        ],
        "lifestyle_culinary_tech": [
            r"\b(ăn\s+gì|nấu\s+ăn|món\s+ngon|quán\s+ăn|nhà\s+hàng|phở\s+bò|bún\s+chả|cơm\s+tấm)\b",
            r"\b(thời\s+tiết|dự\s+báo\s+thời\s+tiết|nhiệt\s+độ|trời\s+mưa|bão\s+số)\b",
            r"\b(lập\s+trình|viết\s+code|python|javascript|react|sửa\s+máy\s+tính|cài\s+win)\b",
            r"\b(du\s+lịch|đi\s+phượt|khách\s+sạn|vé\s+máy\s+bay|vé\s+xem\s+phim)\b",
            r"\b(bóng\s+đá|world\s+cup|ngoại\s+hạng\s+anh|kết\s+quả\s+bóng\s+đá)\b",
            r"\b(quicksort|thuật\s+toán|độ\s+phức\s+tạp\s+thời\s+gian|nhật\s+thực|saros|thiên\s+văn\s+học|vitamin\s+c|acid\s+ascorbic|collagen)\b",
            r"\b(cptpp|hiệp\s+định\s+đối\s+tác\s+toàn\s+diện|môi\s+giới\s+bất\s+động\s+sản)\b",
            r"\b(toán\s+học|hình\s+cầu|khối\s+chóp|nghĩa\s+vụ\s+quân\s+sự|gọi\s+nhập\s+ngũ|transformer|mạng\s+nơ-ron|scaled\s+dot-product|attention)\b",
        ]
    }

    # Các từ khóa nhập nhằng cần kiểm tra ngữ cảnh quan hệ lao động
    AMBIGUOUS_PATTERNS = [
        r"^(hợp\s+đồng(\s+lao\s+động)?|tiền\s+lương|lương|nghỉ\s+việc|sa\s+thải|thử\s+việc|bảo\s+hiểm)$",
        r"^(em\s+muốn\s+hỏi|tư\s+vấn\s+giúp|cho\s+em\s+hỏi(\s+với)?|alo|chào\s+bạn)$",
    ]

    def __init__(self):
        """Khởi tạo và biên dịch các biểu thức chính quy."""
        self._compiled_domains: Dict[str, List[re.Pattern]] = {}
        for domain, pat_list in self.OUT_OF_SCOPE_DOMAINS.items():
            self._compiled_domains[domain] = [re.compile(p, re.IGNORECASE) for p in pat_list]

        self._compiled_ambiguous = [re.compile(p, re.IGNORECASE) for p in self.AMBIGUOUS_PATTERNS]

    def check_scope(self, query: str) -> ScopeCheckResult:
        """Kiểm tra phạm vi và ý định của câu hỏi người dùng."""
        if not query or not query.strip():
            return ScopeCheckResult(
                is_valid_labor=False,
                intent="AMBIGUOUS",
                trigger_refusal=True,
                refusal_reason="Câu hỏi rỗng.",
                refusal_message="Vui lòng nhập câu hỏi cần tư vấn pháp luật lao động.",
            )

        q_clean = query.strip()
        q_lower = q_clean.lower()
        words = q_clean.split()

        # 1. Kiểm tra câu hỏi quá cụt lủn hoặc nhập nhằng (AMBIGUOUS)
        if len(words) <= 2:
            for pat in self._compiled_ambiguous:
                if pat.search(q_lower):
                    logger.info("Tier 1 Scope Guard: Detected AMBIGUOUS short query '%s'", q_clean)
                    return ScopeCheckResult(
                        is_valid_labor=False,
                        intent="AMBIGUOUS",
                        trigger_refusal=True,
                        refusal_reason="Câu hỏi quá ngắn hoặc thiếu ngữ cảnh sự kiện cụ thể.",
                        refusal_message=(
                            f"Câu hỏi '{q_clean}' của bạn còn thiếu thông tin cụ thể. "
                            f"Vui lòng mô tả chi tiết tình huống (ví dụ: loại hợp đồng, thời gian làm việc, sự việc phát sinh) để hệ thống hỗ trợ chính xác."
                        ),
                    )

        # 2. Khử nhập nhằng từ vựng thực phẩm / giải trí
        if re.search(r"\blương\s+(thực|khô)\b", q_lower):
            return ScopeCheckResult(
                is_valid_labor=False,
                intent="OUT_OF_SCOPE",
                trigger_refusal=True,
                detected_domain="culinary",
                refusal_reason="Câu hỏi về lương thực/thực phẩm, không phải tiền lương quan hệ lao động.",
                refusal_message="Nội dung câu hỏi về lương thực/thực phẩm nằm ngoài phạm vi tư vấn pháp luật lao động.",
            )

        # 3. Quét các lĩnh vực phi lao động (OUT_OF_SCOPE)
        for domain, patterns in self._compiled_domains.items():
            for pat in patterns:
                if pat.search(q_lower):
                    # Kiểm tra ngoại lệ quan hệ lao động: Nếu có chủ thể và hành vi lao động
                    # (Ví dụ: "Công ty có phải thanh toán tiền cơm ca", "Sếp bắt giữ bằng lái xe gốc", "Con ruột kết hôn em có được nghỉ làm nhận lương")
                    has_labor_actor = bool(re.search(
                        r"\b(em|tôi|người\s+lao\s+động|lao\s+động\s+nữ|công\s+ty|doanh\s+nghiệp|sếp|chỗ\s+làm|nơi\s+làm|chủ\s*(quán|xưởng|nhà\s+hàng)?|xưởng|nhân\s+viên|thử\s+việc|đi\s+làm|phụ\s+bếp|thợ|công\s+nhân)\b",
                        q_lower
                    ))
                    has_labor_action = bool(re.search(
                        r"\b(lương|tiền\s+lương|trả\s+lương|nợ\s+lương|trừ\s+lương|nhận\s+(nguyên\s+)?lương|hưởng\s+(nguyên\s+)?lương|đuổi\s+việc|sa\s+thải|nghỉ\s+làm|nghỉ\s+việc|nghỉ\s+phép|nghỉ\s+việc\s+riêng|tai\s+nạn\s+lao\s+động|bồi\s+thường|giữ\s+(luôn\s+)?(bằng\s+lái|bản\s+gốc|giấy\s+tờ)|đúng\s+luật|hợp\s+đồng\s+lao\s+động|hợp\s+đồng|đóng\s+bảo\s+hiểm)\b",
                        q_lower
                    ))
                    
                    if has_labor_actor and has_labor_action:
                        # Đây là tình huống lao động đời thường hợp lệ (ví dụ: giữ bằng lái gốc, cơm ca, đuổi phụ bếp)
                        logger.info("Tier 1 Scope Guard: Rescued colloquial labor query '%s' from domain '%s'", q_clean, domain)
                        continue

                    # Nếu không có yếu tố lao động -> OUT_OF_SCOPE
                    logger.info("Tier 1 Scope Guard: Detected OUT_OF_SCOPE domain '%s' for query '%s'", domain, q_clean)
                    domain_names = {
                        "criminal": "Hình sự",
                        "marriage_family_civil": "Hôn nhân gia đình và Dân sự",
                        "land_real_estate": "Đất đai và Bất động sản",
                        "corporate_commercial": "Doanh nghiệp và Thương mại",
                        "tax_financial": "Thuế và Tài chính dân sự",
                        "traffic_administrative": "Giao thông và Quản lý hành chính",
                        "lifestyle_culinary_tech": "Đời sống, Ẩm thực và Công nghệ"
                    }
                    d_vn = domain_names.get(domain, domain)
                    refusal_msg = (
                        f"Câu hỏi của bạn thuộc lĩnh vực pháp luật {d_vn}, nằm ngoài phạm vi tư vấn pháp luật lao động Việt Nam. "
                        f"Hệ thống chỉ hỗ trợ giải đáp các quy định liên quan đến quan hệ lao động, tiền lương, thời giờ làm việc, kỷ luật, an toàn lao động và bảo hiểm xã hội."
                    )
                    return ScopeCheckResult(
                        is_valid_labor=False,
                        intent="OUT_OF_SCOPE",
                        trigger_refusal=True,
                        detected_domain=domain,
                        refusal_reason=f"Câu hỏi thuộc lĩnh vực {d_vn} ngoài phạm vi pháp luật lao động.",
                        refusal_message=refusal_msg,
                    )

        # 4. Câu hỏi hợp lệ
        return ScopeCheckResult(
            is_valid_labor=True,
            intent="VALID_LABOR",
            trigger_refusal=False,
        )
