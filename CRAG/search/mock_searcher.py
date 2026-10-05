"""
CRAG Mock Legal Web Searcher.
Cung cấp nguồn tri thức ngoại bộ pháp lý giả lập phục vụ kiểm thử, tái lập thực nghiệm và chạy offline.
"""

import time
import re
from typing import List, Dict, Any
from CRAG.search.base import BaseWebSearcher
from CRAG.search.schema import SearchResponse, WebSearchResult


class MockLegalWebSearcher(BaseWebSearcher):
    """
    Searcher giả lập chứa các văn bản và án lệ, giải thích hướng dẫn thi hành
    thường được tra cứu từ Thư viện Pháp luật, Cổng TTĐT Chính phủ khi hệ thống nội bộ
    không có hoặc bị thiếu dữ liệu (ví dụ: chế tài xử phạt theo Nghị định 12/2022/NĐ-CP).
    """

    MOCK_KNOWLEDGE_BASE = [
        {
            "title": "Nghị định 12/2022/NĐ-CP - Xử phạt vi phạm quy định về thử việc",
            "url": "https://thuvienphapluat.vn/van-ban/lao-dong/Nghi-dinh-12-2022-ND-CP-xu-phat-vi-pham-hanh-chinh-linh-vuc-lao-dong.aspx",
            "source_name": "Thư Viện Pháp Luật",
            "keywords": ["thử việc", "phạt tiền", "quá hạn", "12/2022", "xử phạt"],
            "snippet": (
                "Theo Điều 10 Nghị định 12/2022/NĐ-CP, người sử dụng lao động có hành vi "
                "yêu cầu thử việc quá thời gian quy định tại Điều 25 Bộ luật Lao động "
                "sẽ bị phạt tiền từ 2.000.000 đồng đến 5.000.000 đồng, đồng thời buộc trả đủ 100% tiền lương "
                "cho người lao động trong thời gian thử việc vượt quá quy định."
            ),
        },
        {
            "title": "Thời hạn và trình tự xử lý kỷ luật sa thải theo Bộ luật Lao động 2019",
            "url": "https://moj.gov.vn/qt/tintuc/Pages/nghien-cuu-trao-doi.aspx?ItemID=4521",
            "source_name": "Bộ Tư Pháp",
            "keywords": ["sa thải", "kỷ luật", "thời hiệu", "trình tự", "125"],
            "snippet": (
                "Thời hiệu xử lý kỷ luật lao động tối đa là 06 tháng kể từ ngày xảy ra hành vi vi phạm; "
                "trường hợp hành vi vi phạm liên quan trực tiếp đến tài chính, tài sản, tiết lộ bí mật "
                "thì thời hiệu xử lý kỷ luật lao động tối đa là 12 tháng (Điều 123 BLLĐ 2019). "
                "Việc sa thải phải có sự tham gia của tổ chức đại diện người lao động tại cơ sở."
            ),
        },
        {
            "title": "Hướng dẫn tính tiền lương làm thêm giờ ban đêm theo Điều 98 BLLĐ",
            "url": "https://chinhphu.vn/huong-dan-tien-luong-lam-them-gio-dieu-98",
            "source_name": "Cổng Thông Tin Điện Tử Chính Phủ",
            "keywords": ["làm thêm giờ", "tiền lương", "ban đêm", "98", "tính lương"],
            "snippet": (
                "Người lao động làm thêm giờ vào ban đêm được trả lương tính theo đơn giá tiền lương "
                "hoặc tiền lương thực trả theo công việc của ngày làm việc bình thường, cộng thêm ít nhất 30% "
                "lương làm việc ban ngày và 20% tiền lương làm thêm giờ ban ngày."
            ),
        },
        {
            "title": "Chế độ nghỉ thai sản và bảo lưu thời gian đóng bảo hiểm",
            "url": "https://baohiemxahoi.gov.vn/chinh-sach-bhxh/che-do-thai-san",
            "source_name": "Bảo Hiểm Xã Hội Việt Nam",
            "keywords": ["thai sản", "nghỉ thai sản", "bảo hiểm", "139", "trợ cấp"],
            "snippet": (
                "Lao động nữ được nghỉ thai sản trước và sau khi sinh con là 06 tháng; "
                "thời gian nghỉ trước khi sinh không quá 02 tháng. Trường hợp lao động nữ sinh đôi trở lên "
                "thì tính từ con thứ 2 trở đi, cứ mỗi con, người mẹ được nghỉ thêm 01 tháng (Điều 139 BLLĐ 2019)."
            ),
        },
        {
            "title": "Quy định về thời hạn báo trước khi đơn phương chấm dứt hợp đồng lao động",
            "url": "https://thuvienphapluat.vn/chinh-sach-phap-luat/thoi-han-bao-truoc-blld-2019",
            "source_name": "Thư Viện Pháp Luật",
            "keywords": ["đơn phương", "chấm dứt", "báo trước", "35", "36"],
            "snippet": (
                "Theo Điều 35 và 36 Bộ luật Lao động 2019, thời hạn báo trước khi đơn phương chấm dứt HĐLĐ: "
                "Ít nhất 45 ngày đối với HĐLĐ không xác định thời hạn; ít nhất 30 ngày đối với HĐLĐ từ 12-36 tháng; "
                "ít nhất 03 ngày làm việc đối với HĐLĐ dưới 12 tháng hoặc trường hợp bị ngược đãi, quấy rối tình dục."
            ),
        },
    ]

    def search(
        self, query: str, transformed_query: str = "", top_k: int = 3
    ) -> SearchResponse:
        start_time = time.perf_counter()
        target_text = (f"{query} {transformed_query}").lower()

        scored_results = []
        for item in self.MOCK_KNOWLEDGE_BASE:
            score = 0.0
            # Kiểm tra trùng khớp từ khóa
            for kw in item["keywords"]:
                if kw in target_text:
                    score += 0.3
            # Kiểm tra trùng khớp trong tiêu đề / snippet
            words = re.findall(r"\w+", target_text)
            for w in words:
                if len(w) > 2 and w in item["snippet"].lower():
                    score += 0.05

            if score > 0:
                scored_results.append((score, item))

        # Sắp xếp điểm giảm dần
        scored_results.sort(key=lambda x: x[0], reverse=True)

        results: List[WebSearchResult] = []
        for score, item in scored_results[:top_k]:
            results.append(
                WebSearchResult(
                    title=item["title"],
                    snippet=item["snippet"],
                    url=item["url"],
                    source_name=item["source_name"],
                    score=round(score, 4),
                )
            )

        # Nếu không có kết quả khớp trực tiếp, trả về mục mặc định uy tín nhất
        if not results:
            item = self.MOCK_KNOWLEDGE_BASE[0]
            results.append(
                WebSearchResult(
                    title=item["title"],
                    snippet=item["snippet"],
                    url=item["url"],
                    source_name=item["source_name"],
                    score=0.1,
                )
            )

        latency = time.perf_counter() - start_time
        return SearchResponse(
            query=query,
            transformed_query=transformed_query,
            results=results,
            latency=latency,
            provider="mock_legal_search",
            total_found=len(results),
        )
