"""
Adaptive RAG Hybrid Query Classifier.
Phân loại ý định, phạm vi và độ phức tạp của câu hỏi bằng kỹ thuật lai (Hybrid Rule & Semantic Pattern Matching)
kết hợp phân tích ngữ cảnh hội thoại đa lượt (Multi-turn Conversational Context Awareness)
và khử nhập nhằng ngữ nghĩa (Semantic Disambiguation).
"""

from __future__ import annotations
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from Adaptive_RAG.config import AdaptiveRAGConfig, adaptive_config
from Adaptive_RAG.classifier.base import BaseQueryClassifier
from Adaptive_RAG.classifier.schema import (
    ClassificationResult,
    ComplexityLevel,
    QueryIntent,
    RoutingDecision,
)


class HybridQueryClassifier(BaseQueryClassifier):
    """
    Bộ phân loại câu hỏi kết hợp nhận diện thực thể pháp lý, cấu trúc cú pháp đa điều kiện,
    khử nhập nhằng từ vựng và nhận thức ngữ cảnh hội thoại (Multi-turn Context).
    """

    # 1. Nhóm từ khóa & mẫu câu chào hỏi, xã giao
    GREETING_PATTERNS = [
        r"^(xin\s+)?chào(\s+(bạn|ad|hệ\s+thống|mọi\s+người|ai\s+đó))?",
        r"^(hello|hi|hey)\b",
        r"\b(bạn\s+là\s+ai|giới\s+thiệu\s+về\s+bạn)\b",
        r"\b(cảm\s+ơn|thank\s+you|thanks)\b",
        r"^(tạm\s+biệt|bye)\b",
    ]

    # 2. Nhóm từ vựng & mẫu câu NGOẠI PHẠM VI (Out-of-Scope Domains)
    OUT_OF_SCOPE_DOMAINS: Dict[str, List[str]] = {
        "culinary": [  # Ẩm thực, ăn uống, nấu ăn
            r"\b(ăn\s+gì|hôm\s+nay\s+ăn|món\s+ăn|ăn\s+uống|uống\s+gì|quán\s+ăn|nhà\s+hàng|thực\s+đơn|món\s+ngon)\b",
            r"\b(nấu\s+ăn|công\s+thức\s+nấu|cách\s+làm\s+món|cách\s+nấu|nấu\s+món|hướng\s+dẫn\s+nấu)\b",
            r"\b(phở\s+bò|bún\s+chả|bún\s+bò|bún\s+riêu|cơm\s+tấm|lẩu|hải\s+sản|trà\s+sữa|cà\s+phê)\b",
            r"\blương\s+thực\b",  # Khử nhập nhằng "lương thực"
            r"\blương\s+khô\b",   # Khử nhập nhằng "lương khô"
        ],
        "tourism_entertainment": [  # Du lịch, giải trí, thể thao
            r"\b(du\s+lịch|đi\s+phượt|resort|homestay|khách\s+sạn|bãi\s+biển|tour\s+du\s+lịch)\b",
            r"\b(nghỉ\s+chơi|nghỉ\s+mát|nghỉ\s+dưỡng|đi\s+chơi|chơi\s+ở\s+đâu|chỗ\s+chơi)\b",
            r"\b(cuối\s+tuần\s+đi\s+đâu|chơi\s+gì\s+cuối\s+tuần|ở\s+đâu\s+cuối\s+tuần)\b",
            r"\b(rạp\s+chiếu\s+phim|xem\s+phim|vé\s+xem\s+phim|vé\s+ca\s+nhạc|hát\s+karaoke)\b",
            r"\b(bóng\s+đá|ngoại\s+hạng\s+anh|champions\s+league|world\s+cup|kết\s+quả\s+bóng\s+đá)\b",
            r"\b(game|chơi\s+game|trò\s+chơi\s+điện\s+tử|playstation|nintendo)\b",
        ],
        "weather": [  # Thời tiết
            r"\b(thời\s+tiết|dự\s+báo\s+thời\s+tiết|trời\s+mưa|trời\s+nắng|bão\s+số|nhiệt\s+độ\s+hôm\s+nay)\b",
        ],
        "tech_programming": [  # Lập trình, CNTT thông thường
            r"\b(lập\s+trình|viết\s+code|hàm\s+trong|bug\s+trong|ngôn\s+ngữ\s+lập\s+trình)\b",
            r"\b(python|javascript|java|c\+\+|golang|react|html|css|mysql|docker)\b",
            r"\b(cài\s+win|cài\s+windows|sửa\s+máy\s+tính|card\s+màn\s+hình|mua\s+iphone|điện\s+thoại)\b",
        ],
        "general_academics": [  # Toán học, phổ thông, sáng tác
            r"\b(giải\s+phương\s+trình|tính\s+đạo\s+hàm|tính\s+tích\s+phân|bài\s+toán|giải\s+bài\s+tập)\b",
            r"\b(sáng\s+tác\s+thơ|bài\s+thơ|phân\s+tích\s+bài\s+thơ|văn\s+mẫu|viết\s+văn)\b",
        ],
        "other_legal_domains": [  # Pháp luật ngoài phạm vi quan hệ lao động
            r"\b(ly\s+hôn|kết\s+hôn|đăng\s+ký\s+kết\s+hôn|hôn\s+nhân|quyền\s+nuôi\s+con|nuôi\s+con\s+nuôi|phân\s+chia\s+tài\s+sản\s+sau\s+ly\s+hôn)\b",
            r"\b(thừa\s+kế|di\s+chúc|sổ\s+đỏ|nhà\s+đất|đất\s+đai|mua\s+bán\s+nhà)\b",
            r"\b(hợp\s+đồng\s+thuê\s+nhà|hợp\s+đồng\s+mua\s+bán|hợp\s+đồng\s+đặt\s+cọc)\b",
            r"\b(nồng\s+độ\s+cồn|vượt\s+đèn\s+đỏ|bằng\s+lái|bảo\s+hiểm\s+xe\s+máy|bảo\s+hiểm\s+ô\s+tô|giao\s+thông)\b",
            r"\b(chứng\s+khoán|cổ\s+phiếu|tiền\s+ảo|bitcoin|crypto|đấu\s+thầu|thuế\s+vat|thuế\s+giá\s+trị\s+gia\s+tăng)\b",
            r"\b(visa\s+schengen|hộ\s+chiếu|đại\s+sứ\s+quán|hàng\s+không|tàu\s+bay)\b",
            r"\b(căn\s+cước\s+công\s+dân|cccd|hộ\s+tịch|sáng\s+chế|nhãn\s+hiệu|madrid)\b",
        ],
    }

    # Danh sách từ khóa ngoài phạm vi kế thừa để tương thích ngược
    OUT_OF_SCOPE_KEYWORDS = {
        "hàng không", "tàu bay", "phi công", "lái máy bay", "hộ chiếu", "visa",
        "schengen", "đại sứ quán", "giao thông", "nồng độ cồn", "bằng lái",
        "đấu thầu", "dự thầu", "gói thầu", "kết hôn", "ly hôn", "hôn nhân",
        "nuôi con nuôi", "thừa kế", "di chúc", "đất đai", "sổ đỏ", "nhà đất",
        "chứng khoán", "cổ phiếu", "tiền ảo", "thuế giá trị gia tăng", "thuế vat",
        "bóng đá", "thời tiết", "nấu ăn", "công thức", "phở bò", "du lịch",
        "căn cước", "cccd", "chứng minh nhân dân", "hộ tịch",
        "ăn gì", "hôm nay ăn", "ăn uống", "món ăn", "uống gì", "đi chơi",
        "chơi gì", "quán ăn", "nhà hàng", "thực đơn", "món ngon"
    }

    # 3. Nhóm chỉ dấu cốt lõi của Pháp luật Lao động (In-Scope Labor Law Indicators)
    LABOR_LAW_CORE_INDICATORS = [
        # Văn bản & điều khoản
        r"\bbộ\s+luật\s+lao\s+động\b", r"\bluật\s+lao\s+động\b", r"\bblld\b", r"\bnghị\s+định\s+145\b",
        r"\bnghị\s+định\s+12/2022\b", r"\bnghị\s+định\s+152\b", r"\bnghị\s+định\s+135\b",
        r"\bluật\s+bảo\s+hiểm\s+xã\s+hội\b", r"\bluật\s+việc\s+làm\b", r"\bluật\s+an\s+toàn\b",
        r"\bđiều\s+\d+\b",
        
        # Chủ thể quan hệ lao động
        r"\bngười\s+lao\s+động\b", r"\bngười\s+sử\s+dụng\s+lao\s+động\b", r"\bnsdlđ\b", r"\bnld\b",
        r"\bcông\s+nhân\b", r"\bnhân\s+viên\b", r"\bcông\s+đoàn\b", r"\bdoanh\s+nghiệp\b",
        
        # Hợp đồng & Chế độ làm việc
        r"\bhợp\s+đồng\s+lao\s+động\b", r"\bhđlđ\b", r"\bthử\s+việc\b", r"\bsa\s+thải\b",
        r"\bđơn\s+phương\s+chấm\s+dứt\b", r"\bchấm\s+dứt\s+hợp\s+đồng\b", r"\btạm\s+hoãn\s+hợp\s+đồng\b",
        r"\bthời\s+gian\s+thử\s+việc\b", r"\bhợp\s+đồng\s+thử\s+việc\b", r"\bchuyển\s+làm\s+công\s+việc\s+khác\b",
        
        # Tiền lương, phụ cấp, thưởng
        r"\btiền\s+lương\b", r"\blương\s+tối\s+thiểu\b", r"\blương\s+cơ\s+bản\b", r"\bbảng\s+lương\b",
        r"\btăng\s+lương\b", r"\btrả\s+lương\b", r"\bkhấu\s+trừ\s+lương\b", r"\bchậm\s+lương\b", r"\bnợ\s+lương\b",
        r"\blương\s+tháng\s+13\b", r"\bphụ\s+cấp\b", r"\btiền\s+thưởng\b", r"\bthưởng\s+tết\b",
        
        # Thời giờ làm việc, nghỉ ngơi
        r"\bthời\s+giờ\s+làm\s+việc\b", r"\bgiờ\s+làm\s+việc\b", r"\blàm\s+thêm\s+giờ\b", r"\btăng\s+ca\b",
        r"\blàm\s+việc\s+ban\s+đêm\b", r"\bca\s+đêm\b", r"\bnghỉ\s+giữa\s+ca\b",
        r"\bnghỉ\s+phép\b", r"\bnghỉ\s+phép\s+năm\b", r"\bnghỉ\s+hằng\s+năm\b", r"\bnghỉ\s+hàng\s+năm\b",
        r"\bnghỉ\s+lễ\b", r"\bnghỉ\s+tết\b", r"\bnghỉ\s+việc\s+riêng\b", r"\bnghỉ\s+không\s+lương\b",
        r"\bnghỉ\s+thai\s+sản\b", r"\bnghỉ\s+ốm\b", r"\bnghỉ\s+dưỡng\s+sức\b",
        
        # Kỷ luật & Trách nhiệm vật chất
        r"\bkỷ\s+luật\s+lao\s+động\b", r"\bxử\s+lý\s+kỷ\s+luật\b", r"\bkhiển\s+trách\b",
        r"\bkéo\s+dài\s+thời\s+hạn\s+nâng\s+lương\b", r"\bcách\s+chức\b", r"\btrách\s+nhiệm\s+vật\s+chất\b",
        r"\btạm\s+đình\s+chỉ\s+công\s+việc\b", r"\bbồi\s+thường\s+chi\s+phí\s+đào\s+tạo\b",
        
        # Chế độ BHXH & Trợ cấp
        r"\bbảo\s+hiểm\s+xã\s+hội\b", r"\bbhxh\b", r"\bbảo\s+hiểm\s+thất\s+nghiệp\b", r"\bbhtn\b",
        r"\btai\s+nạn\s+lao\s+động\b", r"\btnlđ\b", r"\btrợ\s+cấp\s+thôi\s+việc\b",
        r"\btrợ\s+cấp\s+mất\s+việc\b", r"\bchốt\s+sổ\s+bảo\s+hiểm\b", r"\btrả\s+sổ\s+bảo\s+hiểm\b",
        
        # Lao động nước ngoài
        r"\blao\s+động\s+nước\s+ngoài\b", r"\bgiấy\s+phép\s+lao\s+động\b",
    ]

    # 4. Nhóm mẫu câu hỏi TIẾP NỐI (Follow-up / Anaphora / Ellipsis Patterns)
    FOLLOW_UP_PATTERNS = [
        r"^(vậy|thế|thế\s+thì|còn|nếu\s+vậy|vậy\s+thì)\b",
        r"\b(trường\s+hợp\s+đó|trường\s+hợp\s+này|lúc\s+đó|việc\s+đó|điều\s+đó)\b",
        r"\b(như\s+vậy|như\s+thế)\s+có\s+(được|đúng|hợp\s+pháp|bị\s+phạt|phải)\b",
        r"^(có\s+)?cần\s+(phải\s+)?báo\s+trước\s+không\??$",
        r"^(thế\s+)?(công\s+ty|sếp|doanh\s+nghiệp)\s+có\s+phải\s+bồi\s+thường\s+không\??$",
        r"^nếu\s+người\s+lao\s+động\s+không\s+đồng\s+ý\s+thì\s+sao\??$",
        r"^(còn\s+)?nếu\s+(làm\s+(được|việc)?\s+)?\d+\s+năm\??$",
        r"^(thế\s+)?mức\s+phạt\s+(là\s+)?bao\s+nhiêu\??$",
        r"^(thời\s+hạn|thời\s+gian)\s+bao\s+(lâu|nhiêu\s+ngày)\??$",
        r"^(quy\s+định\s+ở|tại)\s+điều\s+(mấy|nào)\??$",
        r"^(thủ\s+tục|trình\s+tự)\s+(như\s+)?thế\s+nào\??$",
        r"^(hồ\s+sơ\s+)?gồm\s+những\s+gì\??$",
        r"^có\s+(được|phải|bị)\s+(không|sao\s+không)\??$",
        r"^thì\s+sao\??$",
    ]

    # 5. Mẫu câu điều kiện phức hợp
    CONDITIONAL_CONNECTORS = [
        r"\bvừa\b.+\bvừa\b",
        r"\bnếu\b.+\bthì\b.+\bnhưng\b",
        r"\bđồng\s+thời\b",
        r"\btrong\s+trường\s+hợp\b.+\bvà\b",
        r"\bkhông\s+những\b.+\bmà\s+còn\b",
        r"\btrước\s+khi\b.+\bthì\s+có\s+được\b",
        r"\bbao\s+nhiêu\b.+\bvà\b.+\bnhư\s+thế\s+nào\b",
        r"\bcó\s+được\b.+\bvà\s+(phải|bị)\b",
    ]

    # 6. Mẫu câu trình tự, thủ tục
    PROCEDURAL_PATTERNS = [
        r"\btrình\s+tự\b",
        r"\bthủ\s+tục\b",
        r"\bcác\s+bước\b",
        r"\bhồ\s+sơ\s+gồm\s+những\s+gì\b",
        r"\bthời\s+hạn\s+giải\s+quyết\b",
        r"\bquy\s+trình\b",
    ]

    @staticmethod
    def _extract_recent_user_queries(chat_history: Optional[Any]) -> List[str]:
        """Bóc tách danh sách các câu hỏi gần nhất của người dùng từ chat_history."""
        if not chat_history:
            return []
        queries: List[str] = []
        if isinstance(chat_history, list):
            for item in chat_history:
                if isinstance(item, dict):
                    role = item.get("role", "")
                    content = item.get("content", "")
                    if role in ("user", "human") and isinstance(content, str) and content.strip():
                        queries.append(content.strip())
                elif isinstance(item, (tuple, list)) and len(item) >= 2:
                    role, content = item[0], item[1]
                    if str(role).lower() in ("user", "human") and isinstance(content, str) and content.strip():
                        queries.append(content.strip())
                elif isinstance(item, str) and item.strip():
                    queries.append(item.strip())
        elif isinstance(chat_history, str) and chat_history.strip():
            queries.append(chat_history.strip())
        return queries

    def _is_explicitly_out_of_scope(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Kiểm tra câu hỏi có thuộc các chủ đề ngoài phạm vi hay không,
        kết hợp khử nhập nhằng ngữ nghĩa (Semantic Disambiguation).
        """
        q_lower = query.lower()

        # 1. Khử nhập nhằng từ vựng thực phẩm: "lương thực", "lương khô" (Dùng word boundary để tránh nhầm "lương không")
        if re.search(r"\blương\s+(thực|khô)\b", q_lower):
            return True, "Chủ đề lương thực/thực phẩm, không thuộc phạm vi tiền lương theo pháp luật lao động."

        # 2. Khử nhập nhằng du lịch/giải trí: "nghỉ chơi", "nghỉ mát", "nghỉ dưỡng", "nghỉ hè"
        if re.search(r"\bnghỉ\s+(chơi|mát|dưỡng|hè)\b", q_lower):
            has_labor_terms = any(t in q_lower for t in ["công ty", "người lao động", "tính lương", "hưởng lương", "hợp đồng"])
            if not has_labor_terms:
                return True, "Chủ đề du lịch/nghỉ ngơi/giải trí cá nhân, ngoài phạm vi pháp luật lao động."

        # 3. Khử nhập nhằng bảo hiểm dân sự ngoài lao động: "bảo hiểm xe", "bảo hiểm ô tô"
        if re.search(r"\bbảo\s+hiểm\s+(xe|ô\s+tô|xe\s+máy|nhân\s+thọ)\b", q_lower):
            return True, "Chủ đề bảo hiểm thương mại/dân sự, không thuộc phạm vi bảo hiểm xã hội/lao động."

        # 4. Quét các domain ngoài phạm vi
        for domain, patterns in self.OUT_OF_SCOPE_DOMAINS.items():
            for pat in patterns:
                if re.search(pat, q_lower):
                    # Ngoại lệ: Nếu câu hỏi thực chất là quyền lợi quan hệ lao động có nhắc đến đời sống
                    # (Ví dụ: "Công ty có phải thanh toán tiền cơm bữa ăn ca cho người lao động?")
                    has_strong_labor_terms = any(re.search(lp, q_lower) for lp in [
                        r"\bngười\s+lao\s+động\b", r"\bbộ\s+luật\s+lao\s+động\b", r"\bhợp\s+đồng\s+lao\s+động\b",
                        r"\btiền\s+lương\b", r"\bsa\s+thải\b", r"\bkỷ\s+luật\s+lao\s+động\b", r"\bbhxh\b"
                    ])
                    if has_strong_labor_terms and any(t in q_lower for t in ["quy định", "chế độ", "công ty có phải", "được hưởng"]):
                        continue
                    return True, f"Câu hỏi thuộc chủ đề '{domain}' ngoài phạm vi pháp luật lao động Việt Nam."

        return False, None

    def _is_labor_law_query(self, query: str) -> bool:
        """Kiểm tra xem một câu hỏi độc lập có thuộc phạm vi pháp luật lao động hay không."""
        q_clean = query.strip()
        q_lower = q_clean.lower()

        # Nếu đã bị phát hiện out-of-scope -> False
        is_out, _ = self._is_explicitly_out_of_scope(q_clean)
        if is_out:
            return False

        # Kiểm tra văn bản hoặc điều luật
        articles, docs = self._extract_legal_entities(q_clean)
        if articles or docs:
            return True

        # Kiểm tra các thuật ngữ pháp luật lao động cốt lõi
        for ind in self.LABOR_LAW_CORE_INDICATORS:
            if re.search(ind, q_lower):
                return True

        return False

    def _resolve_followup(
        self,
        clean_query: str,
        chat_history: Optional[Any]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Nhận diện và xử lý câu hỏi tiếp nối:
        - Nếu câu hiện tại là câu hỏi tiếp nối (anaphora/ellipsis) VÀ câu hỏi trước đó là câu hỏi pháp luật lao động:
          -> Cho phép kế thừa ngữ cảnh (in_scope).
        - Nếu câu hiện tại tự nó chuyển chủ đề (Topic Switch) sang ăn uống, thời tiết...:
          -> Tuyệt đối không ép vào ngữ cảnh cũ, coi là out_of_scope.
        """
        user_queries = self._extract_recent_user_queries(chat_history)
        if not user_queries:
            return False, None, None

        prev_q = user_queries[-1]

        # 1. Kiểm tra xem câu trước có phải là câu hỏi pháp luật lao động không
        if not self._is_labor_law_query(prev_q):
            return False, None, None

        # 2. Kiểm tra câu hiện tại có bị Out-of-Scope độc lập không (Topic Switch)
        is_out, out_reason = self._is_explicitly_out_of_scope(clean_query)
        if is_out:
            # Chuyển chủ đề đột ngột! (Ví dụ: "Hôm nay ăn gì?")
            return False, None, f"Chuyển chủ đề: {out_reason}"

        q_lower = clean_query.lower()

        # 3. Kiểm tra xem câu hiện tại có phải là câu hỏi tiếp nối (Follow-up) không
        is_followup = any(re.search(pat, q_lower) for pat in self.FOLLOW_UP_PATTERNS)

        # Câu hỏi ngắn (< 14 từ) có cấu trúc tiếp nối hoặc câu hỏi điều kiện
        words = q_lower.split()
        if not is_followup and len(words) <= 14:
            if any(q_lower.startswith(prefix) for prefix in ["vậy", "còn", "thế", "nếu", "trường hợp", "thế thì", "vậy thì", "lúc đó", "khi đó"]):
                is_followup = True
            elif any(suffix in q_lower for suffix in ["không?", "được không?", "thì sao?", "như thế nào?", "bao nhiêu?"]):
                if any(kw in q_lower for kw in ["báo trước", "bồi thường", "phạt", "ngày", "năm", "tháng", "thủ tục", "hồ sơ", "đồng ý", "làm sao"]):
                    is_followup = True

        if is_followup:
            return True, prev_q, f"Nhận diện câu hỏi tiếp nối hợp lệ dựa trên chủ đề pháp luật lao động ở lượt trước: '{prev_q}'"

        return False, None, None

    def _extract_legal_entities(self, query: str) -> Tuple[List[str], List[str]]:
        """Bóc tách số Điều luật và các văn bản quy phạm được viện dẫn."""
        articles = re.findall(r"điều\s+\d+", query, re.IGNORECASE)
        articles = [a.title() for a in articles]

        documents = []
        doc_matches = re.findall(
            r"(nghị\s+định\s+\d+/\d+(?:/nđ-cp)?|thông\s+tư\s+\d+/\d+(?:/tt-blđtbxh)?|bộ\s+luật\s+lao\s+động(?:\s+\d+)?)",
            query,
            re.IGNORECASE,
        )
        for d in doc_matches:
            documents.append(d.strip())

        return articles, documents

    def classify(
        self,
        query: str,
        chat_history: Optional[Any] = None,
    ) -> ClassificationResult:
        """
        Phân loại câu hỏi người dùng thành các mức độ phức tạp và hướng điều phối phù hợp.
        Hỗ trợ nhận thức ngữ cảnh hội thoại đa lượt qua chat_history.
        """
        t_start = time.perf_counter()
        q_clean = (query or "").strip()
        q_lower = q_clean.lower()

        # Xử lý truy vấn rỗng
        if not q_clean:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return ClassificationResult(
                query=q_clean,
                intent=QueryIntent.LEGAL_INSUFFICIENT,
                complexity=ComplexityLevel.DIRECT,
                suggested_route=RoutingDecision.DIRECT_REFUSAL,
                confidence=1.0,
                reasoning="Truy vấn rỗng hoặc chỉ chứa khoảng trắng.",
                latency_ms=round(elapsed_ms, 2),
            )

        # 1. Kiểm tra Greeting / Chit-chat
        for pattern in self.GREETING_PATTERNS:
            if re.search(pattern, q_lower):
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                return ClassificationResult(
                    query=q_clean,
                    intent=QueryIntent.GREETING_CHITCHAT,
                    complexity=ComplexityLevel.DIRECT,
                    suggested_route=RoutingDecision.DIRECT_ANSWER,
                    confidence=0.98,
                    reasoning="Câu hỏi mang tính xã giao/chào hỏi/cảm ơn thông thường, không yêu cầu tra cứu pháp luật.",
                    latency_ms=round(elapsed_ms, 2),
                )

        # 2. Phân tích Ngữ cảnh Hội thoại (Conversational Context Awareness)
        is_context_followup, prev_query, followup_reason = self._resolve_followup(q_clean, chat_history)
        if is_context_followup:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            # Nếu câu hỏi tiếp nối có điều kiện hoặc yêu cầu tính toán -> COMPLEX / MODERATE
            has_condition = any(w in q_lower for w in ["nếu", "trường hợp", "đồng ý", "bồi thường", "bao nhiêu"])
            if has_condition:
                return ClassificationResult(
                    query=q_clean,
                    intent=QueryIntent.LEGAL_CONDITIONAL,
                    complexity=ComplexityLevel.MODERATE_CORRECTIVE,
                    suggested_route=RoutingDecision.CORRECTIVE_RAG,
                    confidence=0.90,
                    reasoning=followup_reason or "Câu hỏi tiếp nối có điều kiện dựa trên ngữ cảnh trước.",
                    latency_ms=round(elapsed_ms, 2),
                )
            else:
                return ClassificationResult(
                    query=q_clean,
                    intent=QueryIntent.LEGAL_DIRECT_DEFINITION,
                    complexity=ComplexityLevel.SIMPLE_SINGLE_HOP,
                    suggested_route=RoutingDecision.TRADITIONAL_RAG,
                    confidence=0.92,
                    reasoning=followup_reason or "Câu hỏi tiếp nối trực tiếp dựa trên ngữ cảnh trước.",
                    latency_ms=round(elapsed_ms, 2),
                )

        # 3. Kiểm tra Ngoài phạm vi (Out-of-Scope with Semantic Disambiguation)
        is_out_of_scope, out_scope_reason = self._is_explicitly_out_of_scope(q_clean)
        if is_out_of_scope:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return ClassificationResult(
                query=q_clean,
                intent=QueryIntent.OUT_OF_SCOPE,
                complexity=ComplexityLevel.DIRECT,
                suggested_route=RoutingDecision.DIRECT_REFUSAL,
                confidence=0.96,
                reasoning=out_scope_reason or "Câu hỏi nằm ngoài phạm vi pháp luật lao động Việt Nam. Từ chối an toàn ngay tại cửa ngõ.",
                latency_ms=round(elapsed_ms, 2),
            )

        # 4. Bóc tách thực thể pháp lý
        articles, documents = self._extract_legal_entities(q_clean)

        # 5. Kiểm tra Multi-Document
        if len(documents) >= 2 or (len(documents) == 1 and len(articles) >= 2) or (
            "so sánh" in q_lower or "khác nhau" in q_lower or "sửa đổi" in q_lower
        ):
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return ClassificationResult(
                query=q_clean,
                intent=QueryIntent.LEGAL_MULTI_DOCUMENT,
                complexity=ComplexityLevel.COMPLEX_MULTI_HOP,
                suggested_route=RoutingDecision.DECOMPOSE_AGENTIC,
                confidence=0.90,
                reasoning="Câu hỏi liên quan đến nhiều văn bản quy phạm hoặc yêu cầu so sánh/dẫn chiếu chéo giữa Luật và Nghị định.",
                detected_articles=articles,
                detected_documents=documents,
                latency_ms=round(elapsed_ms, 2),
            )

        # 6. Kiểm tra Multi-Condition / Complex Conditions
        detected_conditions = []
        for cond_pat in self.CONDITIONAL_CONNECTORS:
            if re.search(cond_pat, q_lower):
                detected_conditions.append(cond_pat)

        num_question_marks = q_clean.count("?")
        has_compound_questions = (
            ("và" in q_lower and ("bao nhiêu" in q_lower or "thế nào" in q_lower))
            or ("đồng thời" in q_lower)
            or ("trong khi" in q_lower)
        )

        if detected_conditions or num_question_marks >= 2 or has_compound_questions:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return ClassificationResult(
                query=q_clean,
                intent=QueryIntent.LEGAL_CONDITIONAL,
                complexity=ComplexityLevel.COMPLEX_MULTI_HOP,
                suggested_route=RoutingDecision.DECOMPOSE_AGENTIC,
                confidence=0.88,
                reasoning="Câu hỏi chứa nhiều vế điều kiện phức hợp hoặc hỏi nhiều mục tiêu cùng lúc, cần phân rã thành sub-queries.",
                detected_articles=articles,
                detected_documents=documents,
                detected_conditions=detected_conditions,
                latency_ms=round(elapsed_ms, 2),
            )

        # 7. Kiểm tra Procedural (Quy trình, thủ tục các bước)
        is_procedural = any(re.search(p, q_lower) for p in self.PROCEDURAL_PATTERNS)
        if is_procedural:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return ClassificationResult(
                query=q_clean,
                intent=QueryIntent.LEGAL_PROCEDURAL,
                complexity=ComplexityLevel.MODERATE_CORRECTIVE,
                suggested_route=RoutingDecision.CORRECTIVE_RAG,
                confidence=0.85,
                reasoning="Câu hỏi về trình tự, thủ tục các bước, cần cơ chế Corrective RAG để lọc bỏ các khoản không liên quan.",
                detected_articles=articles,
                detected_documents=documents,
                latency_ms=round(elapsed_ms, 2),
            )

        # 8. Câu hỏi pháp lý đơn giản trực tiếp (Single-Hop)
        words = q_clean.split()
        if len(words) <= 18 and (len(articles) <= 1):
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return ClassificationResult(
                query=q_clean,
                intent=QueryIntent.LEGAL_DIRECT_DEFINITION,
                complexity=ComplexityLevel.SIMPLE_SINGLE_HOP,
                suggested_route=RoutingDecision.TRADITIONAL_RAG,
                confidence=0.90,
                reasoning="Câu hỏi tra cứu điều luật trực tiếp hoặc định nghĩa ngắn gọn, Traditional RAG xử lý nhanh và tối ưu nhất.",
                detected_articles=articles,
                detected_documents=documents,
                latency_ms=round(elapsed_ms, 2),
            )

        # 9. Mặc định: Phân về Corrective RAG để bảo đảm an toàn dữ liệu
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        return ClassificationResult(
            query=q_clean,
            intent=QueryIntent.LEGAL_DIRECT_DEFINITION,
            complexity=ComplexityLevel.MODERATE_CORRECTIVE,
            suggested_route=RoutingDecision.CORRECTIVE_RAG,
            confidence=0.80,
            reasoning="Câu hỏi pháp lý thông thường, sử dụng Corrective RAG để kiểm định mức độ phù hợp và lọc nhiễu.",
            detected_articles=articles,
            detected_documents=documents,
            latency_ms=round(elapsed_ms, 2),
        )
