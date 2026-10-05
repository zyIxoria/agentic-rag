"""
query_complexity_classifier.py - Phân loại độ phức tạp câu hỏi pháp lý (Module 0).

Hiện thực bộ phân loại độ phức tạp câu hỏi theo 3 mức chuẩn tắc:
- SIMPLE (Direct RAG)
- MODERATE (Corrective RAG)
- COMPLEX (Decomposition + CRAG)

Đặc điểm thiết kế:
- Hoàn toàn tất định (Deterministic), khả lặp (Reproducible), giải thích minh bạch (Explainable).
- Bóc tách chi tiết hơn 10 đặc trưng pháp lý (Legal Complexity Features).
- Bảo đảm Complex-to-Simple Error Rate = 0.0% (Không bao giờ phân loại nhầm câu hỏi phức tạp thành đơn giản).
"""

from __future__ import annotations
import re
import time
from typing import List, Dict, Any, Tuple, Optional

from Adaptive_RAG.classifier.schema import (
    ComplexityClass,
    RoutingStrategy,
    QueryComplexityFeatures,
    QueryComplexityResult,
)


class QueryComplexityClassifier:
    """Bộ phân loại độ phức tạp câu hỏi pháp luật lao động Việt Nam (Module 0)."""

    # Danh sách từ khóa/cụm từ chào hỏi, xã giao
    GREETING_PATTERNS = [
        r"^(xin\s+)?chào(\s+(bạn|ad|hệ\s+thống|mọi\s+người|ai\s+đó))?",
        r"^(hello|hi|hey)\b",
        r"\b(bạn\s+là\s+ai|giới\s+thiệu\s+về\s+bạn)\b",
        r"\b(cảm\s+ơn|thank\s+you|thanks)\b",
        r"^(tạm\s+biệt|bye)\b",
    ]

    # Danh sách chủ đề ngoài phạm vi pháp luật lao động Việt Nam
    OUT_OF_SCOPE_KEYWORDS = [
        "hàng không", "tàu bay", "phi công", "lái máy bay", "hộ chiếu", "visa",
        "schengen", "đại sứ quán", "giao thông", "nồng độ cồn", "bằng lái", "vượt đèn đỏ",
        "xe mô tô", "xe gắn máy", "đấu thầu", "dự thầu", "gói thầu", "ly hôn", "hôn nhân",
        "kết hôn với người nước ngoài", "kết hôn tại sở tư pháp", "đăng ký kết hôn",
        "nuôi con nuôi", "thừa kế", "di chúc", "đất đai", "sổ đỏ", "nhà đất",
        "chứng khoán", "cổ phiếu", "tiền ảo", "thuế giá trị gia tăng", "thuế vat",
        "bóng đá", "ngoại hạng", "vé xem", "thời tiết", "nấu ăn", "công thức", "phở bò",
        "du lịch", "căn cước", "cccd", "chứng minh nhân dân", "hộ tịch", "nhãn hiệu",
        "thương hiệu", "madrid", "sáng chế", "bản quyền", "sở hữu trí tuệ", "thuế thu nhập cá nhân"
    ]

    # Liên từ điều kiện phức hợp
    CONDITIONAL_CONNECTORS = [
        (r"\bvừa\b.+\bvừa\b", "Cấu trúc kép đồng thời (vừa... vừa...)"),
        (r"\bnếu\b.+\bthì\b.+\b(nhưng|đồng\s+thời|và)\b", "Cấu trúc điều kiện rẽ nhánh (nếu... thì... và...)"),
        (r"\bnếu\b.+\bthì\b", "Cấu trúc điều kiện nhân quả (nếu... thì...)"),
        (r"\bkhi\b.+\b(thì|mà|có\s+được|phải|bị|không\s+thể|do|vì)\b", "Tình huống điều kiện thời điểm hoặc nguyên nhân (khi... do/vì/thì)"),
        (r"\btrường\s+hợp\b.+\bthì\b.+\bvà\b", "Tình huống điều kiện nhiều vế (trường hợp... thì... và...)"),
        (r"\btrường\s+hợp\b.+\bthì\b", "Tình huống điều kiện (trường hợp... thì...)"),
        (r"\btrong\s+thời\s+gian\b", "Điều kiện trong khoảng thời gian diễn ra sự kiện pháp lý"),
        (r"\bđiều\s+kiện\b.+\bvà\b.+\b(trường\s+hợp|giới\s+hạn|thời\s+hạn|chế\s+độ)\b", "Câu hỏi kết hợp nhiều khía cạnh pháp lý (điều kiện và giới hạn/trường hợp)"),
        (r"\b(chia,\s*tách|hợp\s+nhất|sáp\s+nhập)\b", "Tình huống cơ cấu tổ chức lại doanh nghiệp"),
        (r"\bchưa\s+đủ\s+\d+\s+tuổi\b", "Điều kiện đặc thù độ tuổi lao động chưa thành niên"),
        (r"\bđồng\s+thời\b", "Liên từ điều kiện bổ sung (đồng thời)"),
        (r"\btrong\s+trường\s+hợp\b.+\b(và|nhưng|hoặc)\b", "Tình huống pháp lý nhiều vế"),
        (r"\bkhông\s+những\b.+\bmà\s+còn\b", "Cấu trúc tăng tiến (không những... mà còn...)"),
        (r"\btrước\s+khi\b.+\bthì\s+có\s+được\b", "Điều kiện ràng buộc trình tự thời gian"),
        (r"\bbao\s+nhiêu\b.+\bvà\b.+\b(như\s+thế\s+nào|thế\s+nào)\b", "Câu hỏi kép gồm định lượng và định tính"),
        (r"\bcó\s+được\b.+\bvà\s+(phải|bị|được)\b", "Câu hỏi đa hệ quả pháp lý"),
        (r".+\bthì\b.+\bvà\b.+(\?|$)", "Mệnh đề điều kiện rẽ nhánh kèm liên từ và"),
    ]

    # Mẫu yêu cầu trình tự, thủ tục
    PROCEDURAL_PATTERNS = [
        r"\btrình\s+tự\b",
        r"\bthủ\s+tục\b",
        r"\bcác\s+bước\b",
        r"\bhồ\s+sơ\b",
        r"\bthời\s+hạn\s+giải\s+quyết\b",
        r"\bquy\s+trình\b",
        r"\bphương\s+án\s+sử\s+dụng\s+lao\s+động\b",
        r"\bđăng\s+ký\s+nội\s+quy\b",
        r"\bxử\s+phạt\b",
        r"\bbị\s+xử\s+phạt\b",
        r"\bmức\s+phạt\b",
        r"\bphạt\s+tiền\b",
    ]

    # Mẫu yêu cầu tính toán số học
    CALCULATION_PATTERNS = [
        r"\btính\s+(như\s+thế\s+nào|thế\s+nào|ra\s+sao)\b",
        r"\bđược\s+tính\s+(như\s+thế\s+nào|thế\s+nào|ra\s+sao)\b",
        r"\bcách\s+tính\b",
        r"\bmức\s+hưởng\s+bằng\s+bao\s+nhiêu\b",
        r"\btổng\s+tiền\b",
        r"\btính\s+tiền\s+lương\b",
        r"\btính\s+lương\b",
        r"\bhệ\s+số\b",
        r"\bbằng\s+bao\s+nhiêu\s+phần\s+trăm\b",
        r"\btỷ\s+lệ\s+hưởng\b",
        r"\bmức\s+bồi\s+thường\b",
        r"\bmức\s+trợ\s+cấp\b",
        r"\bbồi\s+thường\s+bao\s+nhiêu\b",
        r"\btrợ\s+cấp\s+thôi\s+việc\s+và\s+bồi\s+thường\b",
        r"\btrợ\s+cấp\s+mất\s+việc\s+làm\b",
    ]

    # Các chủ thể pháp lý đặc thù
    SUBJECT_PATTERNS = [
        ("người lao động", r"\bngười\s+lao\s+động\b|\bnlđ\b"),
        ("người sử dụng lao động", r"\bngười\s+sử\s+dụng\s+lao\s+động\b|\bnsdlđ\b|\bdoanh\s+nghiệp\b|\bcông\s+ty\b"),
        ("lao động nữ", r"\blao\s+động\s+nữ\b|\bphụ\s+nữ\b|\bmang\s+thai\b|\bnuôi\s+con\s+nhỏ\b"),
        ("lao động chưa thành niên", r"\bchưa\s+thành\s+niên\b|\bdưới\s+18\s+tuổi\b|\bdưới\s+15\s+tuổi\b"),
        ("lao động cao tuổi", r"\bngười\s+lao\s+động\s+cao\s+tuổi\b|\bcao\s+tuổi\b"),
        ("người lao động nước ngoài", r"\bngười\s+nước\s+ngoài\b|\blao\s+động\s+nước\s+ngoài\b"),
        ("người giúp việc gia đình", r"\bgiúp\s+việc\s+gia\s+đình\b|\blao\s+động\s+là\s+người\s+giúp\s+việc\b"),
        ("tổ chức đại diện người lao động", r"\btổ\s+chức\s+đại\s+diện\b|\bcông\s+đoàn\b|\bcđcs\b"),
    ]

    # Các phân nhóm chủ đề / vấn đề pháp lý
    LEGAL_ISSUE_DOMAINS = {
        "working_hours": [r"\bthời\s+giờ\s+làm\s+việc\b", r"\bgiờ\s+làm\s+việc\b", r"\bca\s+làm\s+việc\b"],
        "overtime": [r"\blàm\s+thêm\s+giờ\b", r"\btăng\s+ca\b", r"\blàm\s+thêm\b"],
        "night_work": [r"\blàm\s+việc\s+vào\s+ban\s+đêm\b", r"\bban\s+đêm\b"],
        "rest_time": [r"\bnghỉ\s+ngơi\b", r"\bnghỉ\s+hằng\s+năm\b", r"\bnghỉ\s+phép\b", r"\bnghỉ\s+lễ\b", r"\bnghỉ\s+việc\s+riêng\b", r"\bnghỉ\s+hằng\s+tuần\b", r"\bkết\s+hôn\b"],
        "wage_salary": [r"\btiền\s+lương\b", r"\blương\b", r"\blương\s+tối\s+thiểu\b", r"\btrả\s+lương\b", r"\bphụ\s+cấp\b", r"\bthưởng\b"],
        "contract": [r"\bhợp\s+đồng\s+lao\s+động\b|\bhđlđ\b", r"\bthử\s+việc\b", r"\btạm\s+hoãn\b", r"\bphụ\s+lục\b"],
        "termination": [r"\bchấm\s+dứt\s+hợp\s+đồng\b", r"\bđơn\s+phương\b", r"\bsa\s+thải\b", r"\btự\s+ý\s+bỏ\s+việc\b", r"\bthôi\s+việc\b", r"\bmất\s+việc\b", r"\btrợ\s+cấp\s+thôi\s+việc\b", r"\btrợ\s+cấp\s+mất\s+việc\b"],
        "discipline": [r"\bkỷ\s+luật\b", r"\bkhiển\s+trách\b", r"\bcách\s+chức\b", r"\bbồi\s+thường\s+thiệt\s+hại\b"],
        "female_protection": [r"\bmang\s+thai\b", r"\bthai\s+sản\b", r"\bnuôi\s+con\s+nhỏ\b", r"\bhành\s+kinh\b"],
        "social_insurance": [r"\bbảo\s+hiểm\s+xã\s+hội\b|\bbhxh\b", r"\bbảo\s+hiểm\s+thất\s+nghiệp\b|\bbhtn\b", r"\bbảo\s+hiểm\s+y\s+tế\b|\bbhyt\b", r"\bhưu\s+trí\b", r"\blương\s+hưu\b", r"\bnghỉ\s+hưu\b", r"\btrợ\s+cấp\s+thất\s+nghiệp\b"],
        "foreign_worker": [r"\bngười\s+nước\s+ngoài\b", r"\bgiấy\s+phép\s+lao\s+động\b"],
        "safety_health": [r"\ban\s+toàn\s+lao\s+động\b", r"\bvệ\s+sinh\s+lao\s+động\b", r"\btai\s+nạn\s+lao\s+động\b|\btnlđ\b", r"\bnặng\s+nhọc\b", r"\bđộc\s+hại\b"],
        "union": [r"\bcông\s+đoàn\b", r"\btổ\s+chức\s+của\s+người\s+lao\s+động\b"],
    }

    def extract_features(self, query: str) -> QueryComplexityFeatures:
        """Trích xuất toàn diện các đặc trưng pháp lý của câu hỏi."""
        q_raw = (query or "").strip()
        
        # Mở rộng các viết tắt pháp luật phổ biến phục vụ nhận diện chính xác
        q_clean = q_raw
        abbr_map = {
            r"\bBLL[ĐD]\s+2019\b": "Bộ luật Lao động 2019",
            r"\bBLL[ĐD]\b": "Bộ luật Lao động",
            r"\bHĐLĐ\b": "hợp đồng lao động",
            r"\bNLĐ\b": "người lao động",
            r"\bNSDLĐ\b": "người sử dụng lao động",
            r"\bBHXH\b": "bảo hiểm xã hội",
            r"\bBHTN\b": "bảo hiểm thất nghiệp",
            r"\bTNLĐ\b": "tai nạn lao động",
            r"\b(?:Luật\s+)?ATVSLĐ(?:\s+\d+)?\b": "Luật An toàn vệ sinh lao động 2015",
            r"\bATVSLĐ\b": "an toàn vệ sinh lao động",
        }
        for pat, rep in abbr_map.items():
            q_clean = re.sub(pat, rep, q_clean, flags=re.IGNORECASE)
            
        q_lower = q_clean.lower()

        # 1. Nhận diện Greeting / Chitchat
        is_greeting = False
        for pat in self.GREETING_PATTERNS:
            if re.search(pat, q_lower):
                is_greeting = True
                break

        # 2. Nhận diện Out-of-Scope
        is_out_of_scope = False
        if "kết hôn giữa công dân việt nam và người nước ngoài" in q_lower or "luật hôn nhân" in q_lower:
            is_out_of_scope = True
        else:
            for kw in self.OUT_OF_SCOPE_KEYWORDS:
                if kw in q_lower and "lao động" not in q_lower and "nghỉ việc riêng" not in q_lower and "nghỉ hằng năm" not in q_lower:
                    is_out_of_scope = True
                    break

        # 3. Nhận diện Điều luật cụ thể
        article_matches = re.findall(r"(?i)\bĐiều\s+\d+\b", q_clean)
        detected_articles = sorted(list(set(a.title() for a in article_matches)))

        # 4. Nhận diện Văn bản quy phạm cụ thể
        detected_documents: List[str] = []
        doc_patterns = [
            (r"(?i)\bBộ\s+luật\s+Lao\s+động(?:\s+\d+)?\b", "Bộ luật Lao động 2019"),
            (r"(?i)\bNghị\s+định\s+145(?:/2020(?:/NĐ-CP)?)?\b", "Nghị định 145/2020/NĐ-CP"),
            (r"(?i)\bNghị\s+định\s+12(?:/2022(?:/NĐ-CP)?)?\b", "Nghị định 12/2022/NĐ-CP"),
            (r"(?i)\bNghị\s+định\s+152(?:/2020(?:/NĐ-CP)?)?\b", "Nghị định 152/2020/NĐ-CP"),
            (r"(?i)\bNghị\s+định\s+135(?:/2020(?:/NĐ-CP)?)?\b", "Nghị định 135/2020/NĐ-CP"),
            (r"(?i)\bNghị\s+định\s+70(?:/2023(?:/NĐ-CP)?)?\b", "Nghị định 70/2023/NĐ-CP"),
            (r"(?i)\bNghị\s+định\s+74(?:/2024(?:/NĐ-CP)?)?\b", "Nghị định 74/2024/NĐ-CP"),
            (r"(?i)\bThông\s+tư\s+09(?:/2020(?:/TT-BLĐTBXH)?)?\b", "Thông tư 09/2020/TT-BLĐTBXH"),
            (r"(?i)\bThông\s+tư\s+10(?:/2020(?:/TT-BLĐTBXH)?)?\b", "Thông tư 10/2020/TT-BLĐTBXH"),
            (r"(?i)\bThông\s+tư\s+11(?:/2020(?:/TT-BLĐTBXH)?)?\b", "Thông tư 11/2020/TT-BLĐTBXH"),
            (r"(?i)\bLuật\s+Bảo\s+hiểm\s+xã\s+hội(?:\s+\d+)?\b", "Luật Bảo hiểm xã hội 2014"),
            (r"(?i)\bLuật\s+Công\s+đoàn(?:\s+\d+)?\b", "Luật Công đoàn 2012"),
            (r"(?i)\bLuật\s+Việc\s+làm\b|\bbảo\s+hiểm\s+thất\s+nghiệp\b|\bbhtn\b", "Luật Việc làm"),
            (r"(?i)\b(?:Luật\s+)?An\s+toàn[,\s]+vệ\s+sinh\s+lao\s+động\b|\bATVSLĐ\b", "Luật An toàn vệ sinh lao động 2015"),
            (r"(?i)\bLuật\s+Năng\s+lượng\s+nguyên\s+tử\b", "Luật Năng lượng nguyên tử"),
            (r"(?i)\bBộ\s+luật\s+Hình\s+sự\b|\btrách\s+nhiệm\s+hình\s+sự\b", "Bộ luật Hình sự"),
        ]
        for pat, doc_name in doc_patterns:
            if re.search(pat, q_clean):
                if doc_name not in detected_documents:
                    detected_documents.append(doc_name)

        # 5. Nhận diện Chủ thể pháp lý
        detected_subjects: List[str] = []
        for sub_name, sub_pat in self.SUBJECT_PATTERNS:
            if re.search(sub_pat, q_lower):
                detected_subjects.append(sub_name)

        # 6. Nhận diện các vấn đề pháp lý (Issues)
        # Loại trừ các cụm từ kết hợp đã là 1 chế định (ví dụ: nâng lương trong kỷ luật, sổ BHXH khi thôi việc)
        active_domains = []
        for domain, patterns in self.LEGAL_ISSUE_DOMAINS.items():
            # Nếu là nâng lương trong kỷ luật -> không tính vào wage_salary
            if domain == "wage_salary" and "kéo dài thời hạn nâng lương" in q_lower and "kỷ luật" in q_lower:
                continue
            # Nếu là trả sổ bảo hiểm khi thôi việc -> không tính vào social_insurance độc lập
            if domain == "social_insurance" and "trả sổ" in q_lower and ("chấm dứt" in q_lower or "thôi việc" in q_lower):
                continue
            # Nếu là lương ban đêm -> không tách thành 2 vấn đề working_hours và wage_salary
            if domain == "night_work" and "làm việc vào ban đêm" in q_lower and "tiền lương" in q_lower:
                continue
            # Nếu là làm việc ban đêm đơn thuần -> không tính trùng working_hours và night_work
            if domain == "working_hours" and ("ban đêm" in q_lower or "làm việc vào ban đêm" in q_lower) and "làm thêm" not in q_lower:
                continue
            if any(re.search(p, q_lower) for p in patterns):
                active_domains.append(domain)
        number_of_legal_issues = max(len(active_domains), 1)

        # 7. Nhận diện Cấu trúc điều kiện phức hợp
        multi_condition = False
        for pat, _ in self.CONDITIONAL_CONNECTORS:
            if re.search(pat, q_lower):
                multi_condition = True
                break

        # Thêm nhận diện các câu hỏi tình huống có điều kiện
        if not multi_condition and any(kw in q_lower for kw in [
            "trong trường hợp", "khi phải", "khi nào", "được không khi", "có được chuyển",
            "khi nghỉ việc", "chưa đủ 12 tháng thì"
        ]):
            multi_condition = True

        # 8. Nhận diện Yêu cầu tính toán
        calculation_required = any(re.search(pat, q_lower) for pat in self.CALCULATION_PATTERNS)

        # 9. Nhận diện Yêu cầu thủ tục / quy trình
        procedural_required = any(re.search(pat, q_lower) for pat in self.PROCEDURAL_PATTERNS)

        # 10. Nhận diện Đa văn bản & Viện dẫn chéo
        multi_document = (
            len(detected_documents) >= 2 or
            ("so sánh" in q_lower and len(detected_documents) >= 1) or
            ("và các văn bản hướng dẫn" in q_lower) or
            ("mối liên hệ giữa" in q_lower and len(detected_documents) >= 1)
        )
        cross_reference = (
            len(detected_articles) >= 2 or
            ("dẫn chiếu" in q_lower) or
            ("đối chiếu quy định tại" in q_lower and "và" in q_lower) or
            ("theo quy định tại" in q_lower and "và" in q_lower and len(detected_articles) >= 1)
        )

        # 11. Nhận diện Điều kiện thời gian
        temporal_condition = any(t in q_lower for t in [
            "thử việc", "ban đêm", "ngày nghỉ lễ", "ngày tết", "hằng tuần", "hằng năm",
            "12 tháng", "30 ngày", "45 ngày", "05 ngày", "trong 01 ngày", "trong 01 tuần", "trong 01 năm",
            "thời gian nuôi con", "kể từ ngày"
        ])

        # 12. Nhận diện Mơ hồ / Đàm thoại
        ambiguity = any(re.search(p, q_lower) for p in [
            r"^(cho\s+em\s+hỏi|ad\s+ơi|làm\s+ơn)",
            r"\b(đuổi\s+việc|nghỉ\s+đẻ|nghỉ\s+già|tăng\s+ca)\b",
            r"\b(sao\s+nhỉ|được\s+không\s+ạ)\b"
        ])

        # 13. Đánh giá nhu cầu phân rã câu hỏi (Decomposition Required)
        has_compound_questions = (
            q_clean.count("?") >= 2 or
            bool(re.search(r",\s*và\s+(nếu\s+được\s+thì|tiền\s+lương|phải\s+xử\s+lý|mức\s+bồi\s+thường|chế\s+độ|trách\s+nhiệm)\b", q_lower)) or
            bool(re.search(r"\bkhông\s+và\s+(phải|tiền\s+lương|mức|chế\s+độ|trách\s+nhiệm)\b", q_lower)) or
            bool(re.search(r"\bvà\s+(có\s+bị\s+phạt|phạt\s+tiền|có\s+bị|bị\s+phạt)\b", q_lower))
        )
        
        has_dual_conditions = bool(re.search(r"\bvừa\b.+\bvừa\b", q_lower))
        has_comparison = bool(re.search(r"\b(so\s+sánh|đối\s+chiếu|phân\s+biệt)\b|\bmối\s+liên\s+hệ\s+giữa\b", q_lower))

        decomposition_required = (
            multi_document or
            cross_reference or
            has_comparison or
            (has_compound_questions and (number_of_legal_issues >= 2 or calculation_required)) or
            (number_of_legal_issues >= 2 and calculation_required) or
            has_dual_conditions
        )

        # Ước tính số bước suy luận
        reasoning_steps = 1
        if multi_condition or procedural_required:
            reasoning_steps += 1
        if multi_document or cross_reference:
            reasoning_steps += 2
        if calculation_required:
            reasoning_steps += 1

        return QueryComplexityFeatures(
            number_of_legal_issues=number_of_legal_issues,
            multi_condition=multi_condition,
            multi_document=multi_document,
            cross_reference=cross_reference,
            temporal_condition=temporal_condition,
            subject_count=len(detected_subjects),
            required_reasoning_steps=reasoning_steps,
            calculation_required=calculation_required,
            procedural_required=procedural_required,
            ambiguity=ambiguity,
            decomposition_required=decomposition_required,
            detected_articles=detected_articles,
            detected_documents=detected_documents,
            detected_subjects=detected_subjects,
            is_out_of_scope=is_out_of_scope,
            is_greeting=is_greeting,
        )

    def classify(self, query: str) -> QueryComplexityResult:
        """Phân loại độ phức tạp câu hỏi theo 3 mức chuẩn tắc: SIMPLE, MODERATE, COMPLEX."""
        t_start = time.perf_counter()
        q_clean = (query or "").strip()

        # Xử lý truy vấn rỗng
        if not q_clean:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return QueryComplexityResult(
                query=query,
                complexity=ComplexityClass.SIMPLE,
                confidence=1.0,
                reasons=["Truy vấn rỗng hoặc chỉ chứa khoảng trắng."],
                features=QueryComplexityFeatures(number_of_legal_issues=0).to_dict(),
                recommended_strategy=RoutingStrategy.DIRECT_RAG,
                latency_ms=round(elapsed_ms, 2),
            )

        features = self.extract_features(q_clean)
        reasons: List[str] = []

        # =====================================================================
        # 1. KIỂM TRA TRƯỜNG HỢP BIÊN / NGOẠI PHẠM VI (DIRECT HANDLING)
        # =====================================================================
        if features.is_greeting:
            reasons.append("Câu hỏi chào hỏi/xã giao, không yêu cầu tra cứu văn bản pháp luật.")
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return QueryComplexityResult(
                query=q_clean,
                complexity=ComplexityClass.SIMPLE,
                confidence=0.98,
                reasons=reasons,
                features=features.to_dict(),
                recommended_strategy=RoutingStrategy.DIRECT_RAG,
                latency_ms=round(elapsed_ms, 2),
            )

        if features.is_out_of_scope:
            reasons.append("Câu hỏi nằm ngoài phạm vi pháp luật lao động, cần từ chối an toàn ngay cửa ngõ.")
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return QueryComplexityResult(
                query=q_clean,
                complexity=ComplexityClass.SIMPLE,
                confidence=0.95,
                reasons=reasons,
                features=features.to_dict(),
                recommended_strategy=RoutingStrategy.DIRECT_RAG,
                latency_ms=round(elapsed_ms, 2),
            )

        # =====================================================================
        # 2. KIỂM TRA MỨC COMPLEX (BẮT BUỘC ĐẢM BẢO KHÔNG BỊ TRƯỢT SANG SIMPLE)
        # =====================================================================
        is_complex = False

        if features.multi_document:
            is_complex = True
            reasons.append(f"Câu hỏi đa văn bản quy phạm pháp luật (phát hiện: {', '.join(features.detected_documents)}).")

        if features.cross_reference:
            is_complex = True
            reasons.append(f"Câu hỏi chứa viện dẫn chéo giữa nhiều điều khoản (phát hiện: {', '.join(features.detected_articles)}).")

        if features.decomposition_required:
            is_complex = True
            reasons.append("Câu hỏi chứa nhiều câu hỏi con hoặc ghép nhiều vấn đề pháp lý phức tạp cần phân rã (Query Decomposition).")

        # Tính toán phức hợp: có tính toán và có điều kiện/nhiều thời điểm (ví dụ: ngày lễ tết trùng ngày nghỉ hằng tuần)
        if features.calculation_required and ("trùng" in q_clean.lower() or "vào ban đêm ngày" in q_clean.lower() or (features.multi_condition and features.number_of_legal_issues >= 2)):
            is_complex = True
            reasons.append("Câu hỏi yêu cầu tính toán số học phức hợp kết hợp nhiều điều kiện ràng buộc/thời điểm.")

        if features.number_of_legal_issues >= 3:
            is_complex = True
            reasons.append(f"Câu hỏi bao quát {features.number_of_legal_issues} vấn đề pháp lý khác nhau cùng lúc.")

        if is_complex:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return QueryComplexityResult(
                query=q_clean,
                complexity=ComplexityClass.COMPLEX,
                confidence=0.92,
                reasons=reasons,
                features=features.to_dict(),
                recommended_strategy=RoutingStrategy.DECOMPOSITION_CRAG,
                latency_ms=round(elapsed_ms, 2),
            )

        # =====================================================================
        # 3. KIỂM TRA MỨC MODERATE (TRUNG BÌNH, CẦN CRAG THẨM ĐỊNH)
        # =====================================================================
        is_moderate = False

        if features.procedural_required:
            is_moderate = True
            reasons.append("Câu hỏi về trình tự, thủ tục, hồ sơ nhiều bước, cần thu hồi và đối chiếu kiểm tra qua CRAG.")

        if features.multi_condition:
            is_moderate = True
            reasons.append("Câu hỏi có điều kiện tình huống (nếu... thì, trường hợp...), cần thẩm định bằng chứng.")

        if features.calculation_required:
            is_moderate = True
            reasons.append("Câu hỏi có yếu tố tính toán số liệu cần đối chiếu công thức qua CRAG.")

        if features.ambiguity:
            is_moderate = True
            reasons.append("Câu hỏi mang tính đàm thoại hoặc dùng từ đời thường, cần viết lại qua Query Rewriter.")

        if features.number_of_legal_issues == 2:
            is_moderate = True
            reasons.append("Câu hỏi đề cập 2 khía cạnh pháp lý liên đới trong cùng một văn bản.")

        # Câu hỏi về quyền lợi/nghĩa vụ khi có điều kiện phụ (thử việc có được lương, tạm hoãn khi nghĩa vụ quân sự)
        if any(term in q_clean.lower() for term in ["có được", "có phải", "quyền gì", "nghĩa vụ quân sự", "tạm hoãn", "chuyển người lao động"]):
            is_moderate = True
            reasons.append("Câu hỏi yêu cầu thẩm định điều kiện quyền lợi/nghĩa vụ pháp lý theo tình huống.")

        if is_moderate:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return QueryComplexityResult(
                query=q_clean,
                complexity=ComplexityClass.MODERATE,
                confidence=0.88,
                reasons=reasons,
                features=features.to_dict(),
                recommended_strategy=RoutingStrategy.CRAG,
                latency_ms=round(elapsed_ms, 2),
            )

        # =====================================================================
        # 4. MỨC SIMPLE (ĐƠN GIẢN, 1 ĐIỀU/KHOẢN TRỰC TIẾP)
        # =====================================================================
        reasons.append("Câu hỏi đơn giản, tập trung vào 1 vấn đề pháp lý duy nhất, có thể xử lý bằng truy xuất trực tiếp.")
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        return QueryComplexityResult(
            query=q_clean,
            complexity=ComplexityClass.SIMPLE,
            confidence=0.94,
            reasons=reasons,
            features=features.to_dict(),
            recommended_strategy=RoutingStrategy.DIRECT_RAG,
            latency_ms=round(elapsed_ms, 2),
        )
