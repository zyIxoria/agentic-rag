"""hierarchy_parser.py - Robust Context-Aware Legal Document Hierarchy Parser.

Bóc tách chính xác hệ thống phân cấp pháp luật Việt Nam:
Văn bản (Document) -> Chương (Chapter) -> Mục (Section) -> Điều (Article).

Đặc biệt:
- Phân biệt tuyệt đối giữa TIÊU ĐỀ (HEADING) và THAM CHIẾU (REFERENCE / CITATION).
- Loại bỏ hoàn toàn lỗi nhận diện nhầm reference dạng "Mục 1 / Chương XI" thành heading mới.
- Bảo toàn trọn vẹn 100% nội dung văn bản (không làm mất text).
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any


@dataclass
class ChapterInfo:
    """Thông tin cấu trúc một Chương."""
    number: str                  # VD: "Chương I", "Chương 1"
    title: Optional[str] = None  # VD: "NHỮNG QUY ĐỊNH CHUNG"
    line_number: int = 0         # Dòng bắt đầu trong văn bản (1-indexed)
    raw_heading: str = ""


@dataclass
class SectionInfo:
    """Thông tin cấu trúc một Mục."""
    number: str                  # VD: "Mục 1", "Mục 2"
    title: Optional[str] = None  # VD: "GIAO KẾT HỢP ĐỒNG LAO ĐỘNG"
    line_number: int = 0         # Dòng bắt đầu trong văn bản (1-indexed)
    raw_heading: str = ""


@dataclass
class ArticleBlock:
    """Khối nội dung hoàn chỉnh của một Điều luật cùng metadata phân cấp cha."""
    number: str                  # VD: "Điều 1", "Điều 3"
    title: Optional[str] = None  # VD: "Giải thích từ ngữ"
    chapter_number: Optional[str] = None
    chapter_title: Optional[str] = None
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    lines: List[str] = field(default_factory=list)
    raw_text: str = ""
    start_line: int = 0
    end_line: int = 0


@dataclass
class ParsedDocumentHierarchy:
    """Toàn bộ kết quả bóc tách cấu trúc phân cấp của một văn bản."""
    document_id: str
    preamble_lines: List[str] = field(default_factory=list)
    chapters: List[ChapterInfo] = field(default_factory=list)
    sections: List[SectionInfo] = field(default_factory=list)
    articles: List[ArticleBlock] = field(default_factory=list)
    appendix_lines: List[str] = field(default_factory=list)


class HierarchyParser:
    """Bộ phân tích cấu trúc phân cấp văn bản pháp luật hỗ trợ ngữ cảnh (Context-Aware)."""

    def __init__(self):
        # Regex nhận diện ứng viên Chương (hỗ trợ số La Mã và số Ả Rập, cả hoa lẫn thường)
        self.re_chuong_cand = re.compile(
            r'^(?:Chương|CHƯƠNG|chương)\s+([IVXLCDMivxlcdm]+|\d+)\b(.*)$'
        )
        # Regex nhận diện ứng viên Mục (hỗ trợ số Ả Rập và số La Mã, cả hoa lẫn thường)
        self.re_muc_cand = re.compile(
            r'^(?:Mục|MỤC|mục)\s+([IVXLCDMivxlcdm]+|\d+)\b(.*)$'
        )
        # Regex nhận diện Điều luật
        self.re_dieu_heading = re.compile(
            r'^(?:Điều|ĐIỀU|điều)\s+(\d+)\b(.*)$'
        )
        # Regex nhận diện Phụ lục / Danh mục / Biểu mẫu
        self.re_appendix_start = re.compile(
            r'^(?:(?:PHỤ\s+LỤC|Phụ\s+lục|phụ\s+lục)(?:\s+[IVXLCDMivxlcdm\d]+)?|(?:DANH\s+MỤC|Danh\s+mục)\s*$|(?:DANH\s+MỤC|Danh\s+mục)\s+[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ]|(?:MẪU\s+SỐ|Mẫu\s+số)\s+\d+)\b'
        )

        # Regex phát hiện hậu tố tham chiếu (Reference qualifiers)
        # Nếu sau chữ "Chương X" hoặc "Mục Y" xuất hiện các từ này -> 100% là REFERENCE
        self.re_ref_suffix = re.compile(
            r'^(?:\s*của\b|\s*này\b|\s*và\b|\s*đến\b|\s*hoặc\b|\s*trừ\b|\s*được\b|\s*là\b|\s*quy\s+định\b|\s*áp\s+dụng\b)',
            re.IGNORECASE
        )

        # Cụm từ dẫn nhập tham chiếu ở cuối dòng trước
        self.ref_introducers = (
            "quy định tại", "hướng dẫn tại", "nêu tại", "theo quy định tại",
            "theo", "trong", "tại mục", "tại chương", "tại điều", "tại khoản",
            "khoản", "điều", "mục", "chương", "trừ trường hợp", "tại", "mẫu số",
            "kèm theo", "ban hành kèm theo", "ghi tại"
        )
        self.ref_phrase_ends = (
            "quy định tại", "hướng dẫn tại", "nêu tại", "theo quy định tại",
            "theo", "trong", "trừ trường hợp", "ban hành kèm theo", "kèm theo"
        )

        # Dấu kết thúc câu hợp lệ
        self.terminal_punct = ('.', ':', ';', '!', '?', '”', '"', ')')

    def is_chapter_reference(
        self,
        line: str,
        match: re.Match,
        prev_line: str,
        lines: List[str],
        current_idx: int,
        inside_article: bool
    ) -> bool:
        """Xác định xem một dòng khớp 'Chương X' là tham chiếu (Reference) hay tiêu đề thật (Heading)."""
        rest = match.group(2).strip()

        # 1. Kiểm tra hậu tố tham chiếu trên cùng dòng
        if self.re_ref_suffix.match(rest):
            return True

        # 2. Kiểm tra dòng có kết thúc bằng dấu phẩy hoặc chấm phẩy không (dấu nối mệnh đề)
        if line.endswith((',', ';')):
            return True

        # 3. Kiểm tra câu văn bị ngắt dòng từ dòng trước (Line-wrap continuation)
        if prev_line:
            prev_clean = prev_line.strip()
            # Nếu dòng trước không kết thúc bằng dấu chấm/hai chấm và kết thúc bằng từ dẫn chiếu
            if not prev_clean.endswith(self.terminal_punct):
                prev_lower = prev_clean.lower()
                if any(prev_lower.endswith(intro) or intro in prev_lower[-30:] for intro in self.ref_introducers):
                    return True

        # 4. Kiểm tra ngữ cảnh vị trí:
        # Trong cấu trúc luật Việt Nam, một Chương KHÔNG THỂ bắt đầu ở giữa các Khoản của một Điều đang chạy.
        # Nếu đang ở trong một Điều (inside_article == True):
        if inside_article:
            # Kiểm tra xem các dòng tiếp theo có phải là tiêu đề chương hợp lệ và tiếp đó là Điều mới không?
            # Nếu dòng tiếp theo là số khoản (VD: "2. ") hoặc nội dung câu thông thường -> đó là reference!
            next_lines = [lines[k].strip() for k in range(current_idx + 1, min(len(lines), current_idx + 6)) if lines[k].strip()]
            if next_lines:
                first_next = next_lines[0]
                # Nếu dòng tiếp theo là khoản "2. ", "3. " -> Điều luật vẫn đang chạy, đây là reference!
                if re.match(r'^\d+\.\s', first_next):
                    return True
                # Nếu dòng tiếp theo bắt đầu bằng chữ thường -> câu văn đang chạy tiếp
                if first_next and first_next[0].islower():
                    return True

        return False

    def is_section_reference(
        self,
        line: str,
        match: re.Match,
        prev_line: str,
        lines: List[str],
        current_idx: int,
        inside_article: bool
    ) -> bool:
        """Xác định xem một dòng khớp 'Mục X' là tham chiếu (Reference) hay tiêu đề thật (Heading)."""
        rest = match.group(2).strip()

        # 1. Hậu tố tham chiếu
        if self.re_ref_suffix.match(rest):
            return True

        if line.endswith((',', ';')):
            # Ngoại lệ: Tiêu đề Mục dài bị ngắt dòng có dấu phẩy ở giữa
            # Ta chỉ coi là ref nếu sau dấu phẩy là câu văn thường, không phải từ viết hoa
            pass

        # 2. Dòng trước dẫn chiếu
        if prev_line:
            prev_clean = prev_line.strip()
            if not prev_clean.endswith(self.terminal_punct):
                prev_lower = prev_clean.lower()
                if any(prev_lower.endswith(intro) or intro in prev_lower[-30:] for intro in self.ref_introducers):
                    return True

        # 3. Nằm trong Điều luật đang chạy
        if inside_article:
            next_lines = [lines[k].strip() for k in range(current_idx + 1, min(len(lines), current_idx + 6)) if lines[k].strip()]
            if next_lines:
                first_next = next_lines[0]
                if re.match(r'^\d+\.\s', first_next) or (first_next and first_next[0].islower()):
                    return True

        return False

    def is_appendix_start(
        self,
        clean_line: str,
        prev_line: str,
        lines: List[str],
        current_idx: int,
        current_art_num: int = 0
    ) -> bool:
        """Xác định xem dòng hiện tại có phải là điểm bắt đầu của phần Phụ lục / Danh mục ở cuối văn bản không."""
        m = self.re_appendix_start.match(clean_line)
        if not m:
            return False

        rest = clean_line[m.end():].strip()
        # 1. Nếu trên cùng dòng có các cụm từ vị ngữ / liên từ câu văn thường -> trích dẫn trong câu, không phải heading
        # Ví dụ: "Phụ lục I ban hành kèm theo Thông tư này..."
        if rest:
            if re.match(r'^(?:ban\s+hành\s+kèm\s+theo|kèm\s+theo|quy\s+định\s+tại|được\s+quy\s+định|tại\b|và\b|trong\b|của\b|đối\s+với\b)', rest, re.IGNORECASE):
                return False

        # 2. Kiểm tra dòng trước: nếu câu dở dang đang dẫn chiếu
        if prev_line:
            prev_clean = prev_line.strip()
            if not prev_clean.endswith(self.terminal_punct):
                prev_lower = prev_clean.lower()
                if any(prev_lower.endswith(intro) or intro in prev_lower[-30:] or re.search(r'(?:khoản|điều|điểm|mẫu)\s+\d*$', prev_lower) for intro in self.ref_introducers):
                    return False

        # 3. Kiểm tra các dòng kế tiếp: nếu tiếp theo là khoản (2., 3.) hoặc điểm (a), b)) hoặc chữ thường
        next_lines = [lines[k].strip() for k in range(current_idx + 1, min(len(lines), current_idx + 6)) if lines[k].strip()]
        if next_lines:
            first_next = next_lines[0]
            if re.match(r'^\d+\.\s+', first_next) or re.match(r'^[a-zđ]\)\s+', first_next):
                return False
            if first_next and first_next[0].islower():
                return False

        # 4. Kiểm tra cấu trúc tiến (Structural forward look-ahead):
        # Phụ lục ở cuối văn bản KHÔNG THỂ xuất hiện trước các Chương hoặc Điều còn lại của đạo luật
        scan_limit = min(len(lines), current_idx + 150)
        for k in range(current_idx + 1, scan_limit):
            lk = lines[k].strip()
            if self.re_chuong_cand.match(lk):
                return False
            m_art = self.re_dieu_heading.match(lk)
            if m_art:
                art_num = int(m_art.group(1))
                art_rest = m_art.group(2).strip()
                if (not art_rest or art_rest.startswith(('.', ':'))) and art_num > current_art_num:
                    return False

        return True

    def is_real_article_heading(
        self,
        clean_line: str,
        prev_line: str,
        lines: List[str],
        current_idx: int,
        current_art_num: int = 0
    ) -> Tuple[bool, Optional[str], Optional[str], int]:
        """Xác định xem dòng hiện tại có phải là tiêu đề Điều luật thật hay là tham chiếu (Citation).
        
        Ưu tiên tuyệt đối Article Heading trước citation detection theo nguyên tắc cấu trúc.
        Trả về: (is_real_heading, article_number_str, article_title_str, lines_consumed)
        """
        # Trường hợp 1: "Điều X. Tiêu đề" trên cùng 1 dòng
        m_dieu = self.re_dieu_heading.match(clean_line)
        lines_consumed = 1

        if not m_dieu:
            # Trường hợp 2: Dòng hiện tại là "Điều" / "ĐIỀU", dòng tiếp theo là "22. Tiêu đề"
            if clean_line in ("Điều", "ĐIỀU", "điều") and current_idx + 1 < len(lines):
                next_clean = lines[current_idx + 1].strip()
                m_next = re.match(r'^(\d+)\b(.*)$', next_clean)
                if m_next:
                    m_dieu = m_next
                    lines_consumed = 2
            if not m_dieu:
                return False, None, None, 1

        num = int(m_dieu.group(1))
        rest = m_dieu.group(2).strip()

        # 1. Bắt buộc phải có dấu phân cách hợp lệ (. : - – —) hoặc là dòng ngắt tiêu đề tiếp theo
        # Nếu sau số điều là các từ nối mà không có dấu phân cách: "Điều 169 của Bộ luật...", "Điều 12 Nghị định này..."
        if rest and not rest.startswith(('.', ':', '-', '–', '—')):
            return False, None, None, 1

        # 2. Dòng kết thúc bằng dấu chấm phẩy ';' (danh sách liệt kê viện dẫn)
        if clean_line.endswith(';'):
            return False, None, None, 1

        # 3. Dòng trước là câu dở dang đang viện dẫn trực tiếp:
        # VD trong TT_10_2020: "...theo quy định tại khoản 1 \n Điều 142 . \n Điều 2."
        if prev_line:
            prev_clean = prev_line.strip()
            if not prev_clean.endswith(self.terminal_punct):
                prev_lower = prev_clean.lower()
                if any(prev_lower.endswith(intro) for intro in self.ref_phrase_ends) or re.search(r'(?:khoản|điều|điểm)\s+\d+$', prev_lower):
                    return False, None, None, 1

        # 4. Trích xuất tiêu đề Điều (hỗ trợ cả tiêu đề ngắt nhiều dòng trước dòng trống)
        title_parts = []
        if rest:
            first_title = re.sub(r'^[.:\-\s–—]+', '', rest).strip()
            if first_title:
                title_parts.append(first_title)

        scan_idx = current_idx + lines_consumed
        while scan_idx < len(lines):
            nxt = lines[scan_idx].strip()
            if not nxt:
                break
            if re.match(r'^(?:Điều|ĐIỀU|điều|Chương|CHƯƠNG|chương|Mục|MỤC|mục|\d+\.|[a-zđ]\))\b', nxt):
                break

            should_continue_title = False
            if not title_parts:
                should_continue_title = True
            else:
                last_part = title_parts[-1]
                if last_part.endswith((',', ':', '-')) or re.search(r'\b(?:của|về|và|đối\s+với|trong|cho)\s*$', last_part, re.IGNORECASE):
                    should_continue_title = True
                elif nxt and nxt[0].islower():
                    should_continue_title = True

            if not should_continue_title:
                break

            title_parts.append(nxt)
            lines_consumed += 1
            scan_idx += 1
            if len(title_parts) >= 4:
                break

        clean_title = " ".join(title_parts).strip() if title_parts else None
        if clean_title == "":
            clean_title = None

        return True, f"Điều {num}", clean_title, lines_consumed

    def _extract_heading_title(
        self,
        lines: List[str],
        current_idx: int,
        rest: str
    ) -> Tuple[Optional[str], int]:
        """Trích xuất tiêu đề Chương hoặc Mục (có thể nằm cùng dòng hoặc các dòng tiếp theo)."""
        title_parts = []
        clean_rest = re.sub(r'^[.:\-\s]+', '', rest).strip()

        if clean_rest:
            title_parts.append(clean_rest)
            return " ".join(title_parts).strip(), current_idx

        # Tiêu đề nằm ở các dòng tiếp theo (trước khi gặp Mục/Điều mới hoặc dòng trống kép)
        scan_idx = current_idx + 1
        while scan_idx < len(lines):
            line_str = lines[scan_idx].strip()
            if not line_str:
                if title_parts:
                    break
                scan_idx += 1
                continue

            # Nếu gặp điểm mốc phân cấp khác -> dừng thu thập tiêu đề
            if (self.re_dieu_heading.match(line_str) or 
                self.re_muc_cand.match(line_str) or 
                self.re_chuong_cand.match(line_str)):
                break

            title_parts.append(line_str)
            scan_idx += 1

            # Tiêu đề chương thường không dài quá 4 dòng
            if len(title_parts) >= 4:
                break

        full_title = " ".join(title_parts).strip() if title_parts else None
        return full_title, scan_idx - 1

    def parse(self, raw_text: str, document_id: str = "DOC") -> ParsedDocumentHierarchy:
        """Phân tích toàn bộ văn bản thành cấu trúc phân cấp."""
        doc = ParsedDocumentHierarchy(document_id=document_id)
        raw_lines = raw_text.split('\n')
        total_lines = len(raw_lines)

        current_chapter: Optional[ChapterInfo] = None
        current_section: Optional[SectionInfo] = None
        current_article: Optional[ArticleBlock] = None

        idx = 0
        while idx < total_lines:
            line = raw_lines[idx]
            clean_line = line.strip()

            if not clean_line:
                if current_article:
                    current_article.lines.append(line)
                elif not current_chapter:
                    doc.preamble_lines.append(line)
                idx += 1
                continue

            # Lấy dòng trước đó (bỏ qua dòng trống)
            prev_line = ""
            for p in range(idx - 1, max(-1, idx - 10), -1):
                if raw_lines[p].strip():
                    prev_line = raw_lines[p].strip()
                    break

            inside_article = (current_article is not None)
            curr_art_num = 0
            if current_article and current_article.number:
                m_num = re.search(r'\d+', current_article.number)
                if m_num:
                    curr_art_num = int(m_num.group(0))

            # --- 0. KIỂM TRA PHỤ LỤC / DANH MỤC / BIỂU MẪU Ở CUỐI VĂN BẢN ---
            if (len(doc.articles) > 0 or current_article is not None) and self.is_appendix_start(clean_line, prev_line, raw_lines, idx, curr_art_num):
                if current_article:
                    current_article.end_line = idx
                    current_article.raw_text = "\n".join(current_article.lines).strip()
                    doc.articles.append(current_article)
                    current_article = None
                doc.appendix_lines = raw_lines[idx:]
                break

            # --- 1. KIỂM TRA CHƯƠNG ---
            m_chuong = self.re_chuong_cand.match(clean_line)
            if m_chuong:
                is_ref = self.is_chapter_reference(
                    clean_line, m_chuong, prev_line, raw_lines, idx, inside_article
                )
                if not is_ref:
                    # Đây là HEADING thật của Chương!
                    # Đóng Điều hiện tại nếu có
                    if current_article:
                        current_article.end_line = idx
                        current_article.raw_text = "\n".join(current_article.lines).strip()
                        doc.articles.append(current_article)
                        current_article = None

                    num = m_chuong.group(1)
                    rest = m_chuong.group(2).strip()
                    title, new_idx = self._extract_heading_title(raw_lines, idx, rest)

                    current_chapter = ChapterInfo(
                        number=f"Chương {num}",
                        title=title,
                        line_number=idx + 1,
                        raw_heading=clean_line
                    )
                    doc.chapters.append(current_chapter)
                    current_section = None  # Reset Mục khi sang Chương mới
                    idx = max(idx + 1, new_idx + 1)
                    continue
                else:
                    # Là REFERENCE -> Giữ nguyên text, append vào Điều đang chạy hoặc preamble
                    if current_article:
                        current_article.lines.append(line)
                    else:
                        doc.preamble_lines.append(line)
                    idx += 1
                    continue

            # --- 2. KIỂM TRA MỤC ---
            m_muc = self.re_muc_cand.match(clean_line)
            if m_muc:
                is_ref = self.is_section_reference(
                    clean_line, m_muc, prev_line, raw_lines, idx, inside_article
                )
                if not is_ref:
                    # Đây là HEADING thật của Mục!
                    if current_article:
                        current_article.end_line = idx
                        current_article.raw_text = "\n".join(current_article.lines).strip()
                        doc.articles.append(current_article)
                        current_article = None

                    num = m_muc.group(1)
                    rest = m_muc.group(2).strip()
                    title, new_idx = self._extract_heading_title(raw_lines, idx, rest)

                    current_section = SectionInfo(
                        number=f"Mục {num}",
                        title=title,
                        line_number=idx + 1,
                        raw_heading=clean_line
                    )
                    doc.sections.append(current_section)
                    idx = max(idx + 1, new_idx + 1)
                    continue
                else:
                    # Là REFERENCE -> Giữ nguyên text
                    if current_article:
                        current_article.lines.append(line)
                    else:
                        doc.preamble_lines.append(line)
                    idx += 1
                    continue

            # --- 3. KIỂM TRA ĐIỀU ---
            is_real_art, art_num_str, art_title_str, lines_consumed = self.is_real_article_heading(
                clean_line, prev_line, raw_lines, idx, curr_art_num
            )
            if is_real_art:
                # Đóng Điều trước đó
                if current_article:
                    current_article.end_line = idx
                    current_article.raw_text = "\n".join(current_article.lines).strip()
                    doc.articles.append(current_article)

                current_article = ArticleBlock(
                    number=art_num_str,
                    title=art_title_str,
                    chapter_number=current_chapter.number if current_chapter else None,
                    chapter_title=current_chapter.title if current_chapter else None,
                    section_number=current_section.number if current_section else None,
                    section_title=current_section.title if current_section else None,
                    start_line=idx + 1,
                    lines=[raw_lines[i] for i in range(idx, idx + lines_consumed)]
                )
                idx += lines_consumed
                continue

            # --- 4. CÁC NỘI DUNG THƯỜNG ---
            if current_article:
                current_article.lines.append(line)
            else:
                doc.preamble_lines.append(line)

            idx += 1

        # Đóng điều cuối cùng
        if current_article:
            current_article.end_line = total_lines
            current_article.raw_text = "\n".join(current_article.lines).strip()
            doc.articles.append(current_article)

        return doc
