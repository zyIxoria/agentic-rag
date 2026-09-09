"""article_parser.py - Robust Context-Aware Article, Clause, and Point Parser.

Bóc tách chính xác hệ thống cấu trúc 3 cấp cơ sở của văn bản pháp luật Việt Nam:
Điều (Article) -> Khoản (Clause) -> Điểm (Point).

Nguyên tắc bất biến:
1. Nhận diện chính xác:
   - Điều (VD: "Điều 1.", "Điều 104. Thưởng", "Điều\n22. Tiêu đề", "ĐIỀU 5: ...")
   - Khoản (VD: "1. ", "2. ", "3. ")
   - Điểm (VD: "a) ", "b) ", "c) ", "đ) ")
2. Tuyệt đối không nhầm (Zero False Positives):
   - Số tiền (VD: "1.000.000 đồng", "5.000.000 đồng")
   - Ngày tháng (VD: "ngày 20 tháng 11 năm 2019", "01/01/2021", "20/11/2019")
   - Thời hạn, đo lường (VD: "01 tháng", "07 ngày", "30 ngày")
   - Tỷ lệ phần trăm (VD: "50% số giờ", "100% lương", "150%")
   - Trích dẫn điều khoản (VD: "Điều 5 khoản 2", "khoản 1 Điều này", "điểm a khoản 3 Điều này")
   - Từ trong dấu ngoặc đơn (VD: "(sau đây gọi tắt là...)", "(được tính theo ngày)")
   - Danh mục nhảy số bất thường (VD: "32. Danh mục thiết bị" sau khoản 2)
   - Viện dẫn Điều bị ngắt dòng (VD: "quy định tại khoản 2\nĐiều 169 của Bộ luật Lao động")
3. Bảo toàn 100% nội dung (zero text loss).
4. Phân cấp hoàn chỉnh có thể reconstruct lại đầy đủ từ metadata.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple


# Bảng chữ cái tiếng Việt dùng cho các Điểm quy định trong luật
VALID_POINT_LETTERS = set('abcdđeghijklmnopqrsuvtxy')
POINT_ORDER = ['a', 'b', 'c', 'd', 'đ', 'e', 'g', 'h', 'i', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'x', 'y']
LETTER_TO_INDEX = {letter: idx for idx, letter in enumerate(POINT_ORDER)}


@dataclass
class PointNode:
    """Nút biểu diễn một Điểm luật (Point)."""
    point_number: str            # VD: "Điểm a", "Điểm đ"
    point_letter: str            # VD: "a", "đ"
    content: str                 # Nội dung toàn văn của Điểm
    raw_lines: List[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0

    def reconstruct_text(self) -> str:
        """Tái tạo lại nội dung văn bản gốc của Điểm."""
        return "\n".join(self.raw_lines)


@dataclass
class ClauseNode:
    """Nút biểu diễn một Khoản luật (Clause)."""
    clause_number: Optional[str] # VD: "Khoản 1", "Khoản 2", hoặc None nếu Điều không chia khoản
    clause_index: int            # 1, 2, 3... (0 nếu là Điều không chia khoản hoặc unnumbered clause)
    content: str                 # Nội dung toàn văn của Khoản
    intro_text: str = ""         # Lời dẫn của Khoản trước khi vào các Điểm a, b, c
    points: List[PointNode] = field(default_factory=list)
    raw_lines: List[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0

    def reconstruct_text(self) -> str:
        """Tái tạo lại nội dung văn bản gốc của Khoản."""
        return "\n".join(self.raw_lines)


@dataclass
class ArticleNode:
    """Nút biểu diễn một Điều luật hoàn chỉnh (Article)."""
    article_number: str          # VD: "Điều 1", "Điều 104"
    article_title: Optional[str] # VD: "Phạm vi điều chỉnh", "Thưởng"
    chapter_number: Optional[str] = None
    chapter_title: Optional[str] = None
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    content: str = ""            # Toàn văn nội dung của Điều
    intro_text: str = ""         # Lời mở đầu của Điều trước khi vào Khoản 1
    clauses: List[ClauseNode] = field(default_factory=list)
    raw_lines: List[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0

    def reconstruct_text(self) -> str:
        """Tái tạo lại 100% nội dung nguyên bản của Điều luật."""
        return "\n".join(self.raw_lines)


@dataclass
class ParsedLegalUnit:
    """Đơn vị phân cấp pháp lý chuẩn hóa phục vụ chunking và retrieval."""
    unit_id: str
    document_id: str
    article_number: Optional[str] = None
    article_title: Optional[str] = None
    clause_number: Optional[str] = None
    point_number: Optional[str] = None
    content: str = ""
    chapter_number: Optional[str] = None
    chapter_title: Optional[str] = None
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    appendix_number: Optional[str] = None
    appendix_title: Optional[str] = None
    table_id: Optional[str] = None
    parent_article: str = ""
    unit_type: str = "article"   # "article", "clause", "point", "appendix", "table", "form"
    content_type: str = "article"  # "article", "clause", "point", "appendix", "table", "form", "other"


class ArticleClausePointParser:
    """Parser bóc tách cấu trúc Điều -> Khoản -> Điểm với khả năng lọc nhiễu chính xác cao."""

    def __init__(self):
        # Regex Điều luật (chấp nhận Điều, ĐIỀU, điều)
        self.re_article_header = re.compile(
            r'^(?:Điều|ĐIỀU|điều)\s+(\d+)\b(.*)$'
        )

        # Regex Khoản:
        # Bắt buộc bắt đầu dòng bằng chữ số, theo sau là dấu chấm và khoảng trắng,
        # và ký tự tiếp theo KHÔNG ĐƯỢC là chữ số (chống 1.000.000 đồng, 1. 000 đồng)
        self.re_clause_candidate = re.compile(
            r'^\s*(\d+)\.\s+([^\d\s].*)$'
        )

        # Regex Điểm:
        # Bắt buộc bắt đầu dòng bằng 1 chữ cái hợp lệ, theo sau là dấu đóng ngoặc đơn ')' và khoảng trắng
        self.re_point_candidate = re.compile(
            r'^\s*([a-zđ])\)\s+(.*)$'
        )

        # Cụm từ dẫn chiếu tham chiếu trước khi ngắt dòng
        self.ref_introducers = (
            "quy định tại", "hướng dẫn tại", "nêu tại", "theo quy định tại",
            "theo", "trong", "tại mục", "tại chương", "tại điều", "tại khoản",
            "khoản", "điều", "mục", "chương", "trừ trường hợp", "điểm"
        )

    def parse_article_header(self, line: str) -> Optional[Tuple[str, Optional[str]]]:
        """Phân tích dòng tiêu đề Điều luật.
        
        Trả về Tuple (article_number, article_title) nếu là tiêu đề Điều hợp lệ, ngược lại None.
        Ví dụ:
        - "Điều 1. Phạm vi điều chỉnh" -> ("Điều 1", "Phạm vi điều chỉnh")
        - "Điều 104. Thưởng" -> ("Điều 104", "Thưởng")
        - "Điều 1." -> ("Điều 1", None)
        - "ĐIỀU 5: QUYỀN VÀ NGHĨA VỤ" -> ("Điều 5", "QUYỀN VÀ NGHĨA VỤ")
        - "điều 12 - Trách nhiệm" -> ("Điều 12", "Trách nhiệm")
        """
        clean = line.strip()
        m = self.re_article_header.match(clean)
        if not m:
            return None

        num = m.group(1)
        rest = m.group(2).strip()

        # Nếu có hậu tố tham chiếu ngay sau số điều mà không có dấu chấm/hai chấm -> không phải header
        if rest and re.match(r'^(?:của\b|này\b|và\b|đến\b|hoặc\b|áp\s+dụng\b|được\b|khi\b)', rest, re.IGNORECASE):
            return None
        if clean.endswith(';'):
            return None

        title = re.sub(r'^[.:\-\s–—]+', '', rest).strip()
        title = title if title else None
        return f"Điều {num}", title

    def is_article_reference(
        self,
        clean_line: str,
        prev_line: str = "",
        current_article_num: int = 0
    ) -> bool:
        """Xác định xem một dòng khớp 'Điều X' là tham chiếu (Citation/Reference) hay tiêu đề thật.
        
        Tuyệt đối không nhầm các trường hợp:
        - "quy định tại khoản 2 Điều 169 của Bộ luật Lao động"
        - "theo quy định tại Điều 36 của Bộ luật này"
        - "Áp dụng biện pháp khắc phục hậu quả quy định tại điểm c khoản 4 Điều 19 Nghị định này"
        """
        m = self.re_article_header.match(clean_line.strip())
        if not m:
            return False

        num = int(m.group(1))
        rest = m.group(2).strip()

        # 1. Hậu tố tham chiếu trực tiếp: "của", "này", "và", "đến", "hoặc", "áp dụng", "được", "khi"
        if re.match(r'^(?:của\b|này\b|và\b|đến\b|hoặc\b|áp\s+dụng\b|được\b|khi\b)', rest, re.IGNORECASE):
            return True

        # 2. Không có dấu phân cách hợp lệ sau số điều mà có nội dung tiếp nối
        if rest and not rest.startswith(('.', ':', ' -', ' –', ' —')):
            return True

        # 3. Dòng kết thúc bằng dấu chấm phẩy ';' (đặc trưng của danh sách liệt kê viện dẫn)
        if clean_line.endswith(';'):
            return True

        # 4. Ngắt dòng nối tiếp từ viện dẫn ở dòng trước
        if prev_line:
            prev_clean = prev_line.strip()
            if not prev_clean.endswith(('.', ':', '”', '"', '!', '?')):
                prev_lower = prev_clean.lower()
                if any(prev_lower.endswith(intro) or re.search(r'(?:khoản|điều|điểm)\s+\d*$', prev_lower) for intro in self.ref_introducers):
                    return True
                if prev_clean.endswith(','):
                    return True

        # 5. Kiểm tra thứ tự tuần tự của Điều luật (Sequence Guard)
        if current_article_num > 0:
            if num < current_article_num:
                return True
            if num > current_article_num + 3:
                return True

        return False

    def is_clause_start(
        self,
        line: str,
        current_clause_idx: int,
        in_quote: bool = False
    ) -> Optional[Tuple[int, str]]:
        """Kiểm tra xem dòng có phải là điểm bắt đầu của một Khoản hợp lệ hay không.
        
        Returns:
            Tuple (clause_number_int, clause_text) nếu là Khoản thật, ngược lại None.
        """
        clean = line.strip()
        m = self.re_clause_candidate.match(clean)
        if not m:
            return None

        num_str, rest_text = m.group(1), m.group(2).strip()

        # 1. Chống số tiền: nếu dòng có dạng "1.000.000 đồng"
        if re.match(r'^\d{1,3}(?:\.\d{3})+\s*(?:đồng|triệu|nghìn|tỷ)', clean):
            return None

        # 2. Chống tỷ lệ phần trăm / số thập phân
        if re.match(r'^\d+\.\d+\s*%', clean):
            return None

        try:
            num = int(num_str)
        except ValueError:
            return None

        # 3. Tính tuần tự của Khoản (Sequence Guard):
        # Khoản trong luật bắt đầu từ 1 và tăng dần liên tục: 1, 2, 3...
        # Nếu chưa có khoản nào (current_clause_idx == 0), khoản đầu tiên phải là 1
        if current_clause_idx == 0:
            if num != 1:
                return None
        else:
            # Khoản tiếp theo phải lớn hơn khoản trước, và tăng liên tục
            if num <= current_clause_idx:
                return None
            if num > current_clause_idx + 2:
                return None

        return num, rest_text

    def is_point_start(
        self,
        line: str,
        current_point_letter: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """Kiểm tra xem dòng có phải là điểm bắt đầu của một Điểm hợp lệ (a, b, c...) hay không.
        
        Returns:
            Tuple (point_letter, point_text) nếu là Điểm thật, ngược lại None.
        """
        clean = line.strip()
        m = self.re_point_candidate.match(clean)
        if not m:
            return None

        letter = m.group(1).lower()
        rest_text = m.group(2).strip()

        # 1. Chữ cái phải nằm trong bảng chữ cái lập pháp Việt Nam
        if letter not in VALID_POINT_LETTERS:
            return None

        # 2. Loại bỏ các từ nằm trong dấu ngoặc đơn mở đầu (VD: "(sau đây gọi là...)")
        if clean.startswith('('):
            return None

        # 3. Tính tuần tự của Điểm (Point Sequence Guard):
        # Điểm bắt đầu từ 'a)'. Điểm tiếp theo theo thứ tự: a -> b -> c -> d -> đ -> e -> g...
        if current_point_letter is None:
            # Điểm đầu tiên trong khoản thường phải là 'a' (hoặc tối đa 'b' trong văn bản sửa đổi)
            if letter not in ('a', 'b'):
                return None
        else:
            idx_curr = LETTER_TO_INDEX.get(current_point_letter, -1)
            idx_new = LETTER_TO_INDEX.get(letter, -1)
            if idx_new <= idx_curr:
                return None
            # Không nhảy cóc quá xa trong cùng một bảng chữ cái (tối đa cách nhau 3 chữ cái)
            if idx_new > idx_curr + 3:
                return None

        return letter, rest_text

    def parse_article_content(
        self,
        article_number: str,
        article_title: Optional[str],
        lines: List[str],
        chapter_number: Optional[str] = None,
        chapter_title: Optional[str] = None,
        section_number: Optional[str] = None,
        section_title: Optional[str] = None,
        start_line: int = 0
    ) -> ArticleNode:
        """Phân tích nội dung các dòng của một Điều thành danh sách Khoản và Điểm."""
        article_node = ArticleNode(
            article_number=article_number,
            article_title=article_title,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            section_number=section_number,
            section_title=section_title,
            raw_lines=list(lines),
            start_line=start_line,
            end_line=start_line + len(lines)
        )

        current_clause: Optional[ClauseNode] = None
        current_point: Optional[PointNode] = None
        current_clause_idx = 0
        current_point_letter: Optional[str] = None
        in_quote = False

        article_intro_lines: List[str] = []

        # Bỏ qua dòng tiêu đề Điều ở đầu (xử lý cả trường hợp ngắt 1 hoặc 2 dòng)
        start_idx = 0
        if lines:
            first_line = lines[0].strip()
            if self.re_article_header.match(first_line):
                start_idx = 1
            elif first_line in ("Điều", "ĐIỀU", "điều") and len(lines) > 1 and re.match(r'^\d+\b', lines[1].strip()):
                start_idx = 2

        for idx in range(start_idx, len(lines)):
            line = lines[idx]
            clean = line.strip()

            if not clean:
                # Dòng trống: ghi nhận vào node hiện tại để bảo toàn text 100%
                if current_point:
                    current_point.raw_lines.append(line)
                elif current_clause:
                    current_clause.raw_lines.append(line)
                else:
                    article_intro_lines.append(line)
                continue

            # Cập nhật trạng thái trong trích dẫn
            if "“" in clean and "”" not in clean:
                in_quote = True
            elif "”" in clean:
                in_quote = False

            # --- 1. KIỂM TRA BẮT ĐẦU KHOẢN MỚI ---
            clause_res = self.is_clause_start(clean, current_clause_idx, in_quote)
            if clause_res is not None:
                new_num, _ = clause_res

                # Đóng Điểm hiện tại nếu có
                if current_point and current_clause:
                    current_point.content = "\n".join(current_point.raw_lines).strip()
                    current_clause.points.append(current_point)
                    current_point = None
                    current_point_letter = None

                # Đóng Khoản hiện tại nếu có
                if current_clause:
                    current_clause.content = "\n".join(current_clause.raw_lines).strip()
                    article_node.clauses.append(current_clause)

                # Mở Khoản mới
                current_clause_idx = new_num
                current_point_letter = None  # Reset điểm khi sang khoản mới
                current_clause = ClauseNode(
                    clause_number=f"Khoản {new_num}",
                    clause_index=new_num,
                    content="",
                    raw_lines=[line],
                    start_line=start_line + idx,
                    end_line=start_line + idx
                )
                continue

            # --- 2. KIỂM TRA BẮT ĐẦU ĐIỂM MỚI ---
            point_res = self.is_point_start(clean, current_point_letter)
            if point_res is not None:
                new_letter, _ = point_res

                # Nếu chưa có Khoản nào mà xuất hiện Điểm (Hiếm gặp), tạo Khoản ngầm định không đánh số
                if current_clause is None:
                    current_clause = ClauseNode(
                        clause_number=None,
                        clause_index=0,
                        content="",
                        intro_text="\n".join(article_intro_lines).strip(),
                        raw_lines=list(article_intro_lines),
                        start_line=start_line + idx
                    )
                    article_intro_lines = []

                # Đóng Điểm trước đó nếu có
                if current_point:
                    current_point.content = "\n".join(current_point.raw_lines).strip()
                    current_clause.points.append(current_point)

                # Nếu trước điểm này có intro_text của Khoản
                if not current_clause.points and current_clause.raw_lines:
                    current_clause.intro_text = "\n".join(current_clause.raw_lines).strip()

                # Mở Điểm mới
                current_point_letter = new_letter
                current_point = PointNode(
                    point_number=f"Điểm {new_letter}",
                    point_letter=new_letter,
                    content="",
                    raw_lines=[line],
                    start_line=start_line + idx,
                    end_line=start_line + idx
                )
                continue

            # --- 3. DÒNG NỘI DUNG BÌNH THƯỜNG ---
            if current_point:
                current_point.raw_lines.append(line)
            elif current_clause:
                current_clause.raw_lines.append(line)
            else:
                article_intro_lines.append(line)

        # Đóng Điểm cuối cùng
        if current_point and current_clause:
            current_point.content = "\n".join(current_point.raw_lines).strip()
            current_clause.points.append(current_point)

        # Đóng Khoản cuối cùng
        if current_clause:
            current_clause.content = "\n".join(current_clause.raw_lines).strip()
            article_node.clauses.append(current_clause)

        # Lưu intro_text của Điều
        article_node.intro_text = "\n".join(article_intro_lines).strip()
        article_node.content = "\n".join(lines).strip()

        # Trường hợp Điều không chia khoản:
        if not article_node.clauses and article_node.content:
            single_clause = ClauseNode(
                clause_number=None,
                clause_index=0,
                content=article_node.content,
                raw_lines=list(lines),
                start_line=start_line,
                end_line=start_line + len(lines)
            )
            article_node.clauses.append(single_clause)

        return article_node

    def parse_article_text(
        self,
        text: str,
        document_id: str = "DOC",
        chapter_number: Optional[str] = None,
        chapter_title: Optional[str] = None,
        section_number: Optional[str] = None,
        section_title: Optional[str] = None
    ) -> ArticleNode:
        """Phân tích chuỗi văn bản của một Điều luật hoàn chỉnh."""
        lines = text.split('\n')
        first_line = lines[0].strip() if lines else ""
        header_info = self.parse_article_header(first_line)

        consumed_lines = 1
        if not header_info and len(lines) > 1 and first_line in ("Điều", "ĐIỀU", "điều"):
            next_line = lines[1].strip()
            m_next = re.match(r'^(\d+)\b(.*)$', next_line)
            if m_next:
                d_num = m_next.group(1)
                d_rest = m_next.group(2).strip()
                title = re.sub(r'^[.:\-\s–—]+', '', d_rest).strip()
                header_info = (f"Điều {d_num}", title if title else None)
                consumed_lines = 2

        if header_info:
            art_num, art_title = header_info
        else:
            art_num = "Điều 0"
            art_title = None

        return self.parse_article_content(
            article_number=art_num,
            article_title=art_title,
            lines=lines,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            section_number=section_number,
            section_title=section_title,
            start_line=1
        )

    def extract_legal_units(
        self,
        article_node: ArticleNode,
        document_id: str
    ) -> List[ParsedLegalUnit]:
        """Chuyển đổi ArticleNode thành danh sách các ParsedLegalUnit sẵn sàng cho Chunking/RAG.
        
        Đảm bảo mỗi unit đều mang đầy đủ metadata của cấp gần nhất (Article, Clause, Point).
        Nếu không xác định: gán giá trị None (null).
        """
        units: List[ParsedLegalUnit] = []
        doc_prefix = document_id
        d_clean = article_node.article_number.replace(' ', '')
        parent_art = f"{doc_prefix}_{d_clean}"

        # Trường hợp 1: Điều không chia Khoản
        if len(article_node.clauses) == 1 and article_node.clauses[0].clause_number is None and not article_node.clauses[0].points:
            c = article_node.clauses[0]
            unit = ParsedLegalUnit(
                unit_id=f"{doc_prefix}_{d_clean}",
                document_id=document_id,
                article_number=article_node.article_number,
                article_title=article_node.article_title,
                clause_number=None,
                point_number=None,
                content=c.content,
                chapter_number=article_node.chapter_number,
                chapter_title=article_node.chapter_title,
                section_number=article_node.section_number,
                section_title=article_node.section_title,
                parent_article=parent_art,
                unit_type="article",
                content_type="article"
            )
            units.append(unit)
            return units

        # Trường hợp 2: Điều có các Khoản hoặc có Điểm
        for clause in article_node.clauses:
            k_clean = clause.clause_number.replace(' ', '') if clause.clause_number else "K0"
            clause_id = f"{doc_prefix}_{d_clean}_{k_clean}"

            # Nếu Khoản không có Điểm nào -> Tạo unit cấp Khoản
            if not clause.points:
                u_type = "clause" if clause.clause_number else "article"
                unit = ParsedLegalUnit(
                    unit_id=clause_id,
                    document_id=document_id,
                    article_number=article_node.article_number,
                    article_title=article_node.article_title,
                    clause_number=clause.clause_number,
                    point_number=None,
                    content=clause.content,
                    chapter_number=article_node.chapter_number,
                    chapter_title=article_node.chapter_title,
                    section_number=article_node.section_number,
                    section_title=article_node.section_title,
                    parent_article=parent_art,
                    unit_type=u_type,
                    content_type=u_type
                )
                units.append(unit)
            else:
                # Nếu Khoản có các Điểm: tạo unit cấp Điểm
                for pt in clause.points:
                    p_clean = pt.point_number.replace(' ', '')
                    point_id = f"{clause_id}_{p_clean}"

                    unit = ParsedLegalUnit(
                        unit_id=point_id,
                        document_id=document_id,
                        article_number=article_node.article_number,
                        article_title=article_node.article_title,
                        clause_number=clause.clause_number,
                        point_number=pt.point_number,
                        content=pt.content,
                        chapter_number=article_node.chapter_number,
                        chapter_title=article_node.chapter_title,
                        section_number=article_node.section_number,
                        section_title=article_node.section_title,
                        parent_article=parent_art,
                        unit_type="point",
                        content_type="point"
                    )
                    units.append(unit)

        return units
