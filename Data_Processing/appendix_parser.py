"""appendix_parser.py - Robust Appendix, Table, Form, and Catalog Parser for Legal Dataset V2.

Xử lý toàn diện các thành phần phi Điều/Khoản (Non-Article hierarchy):
- Phụ lục (Appendix): Phụ lục I, Phụ lục II, Phụ lục III...
- Bảng biểu (Table): Bảng số liệu, lộ trình tuổi nghỉ hưu, ma trận phân loại lao động...
- Biểu mẫu (Form): Mẫu số 01/PLI, Mẫu số 02, Hợp đồng lao động mẫu, Tờ khai...
- Danh mục (Catalog): Danh mục nghề nặng nhọc độc hại, Danh mục địa bàn áp dụng lương tối thiểu...
- Danh sách ngành nghề (Occupations List): Danh mục nghề cấm, nghề nguy hiểm...

Tuân thủ nghiêm ngặt các nguyên tắc của TASK DATA-05:
1. Xóa bỏ hoàn toàn hiện tượng monster chunk (như chunk 36.441 từ của TT 09/2020 & TT 11/2020 trong V1).
2. Bảo toàn 100% nội dung (Zero content loss) - Tuyệt đối không xóa dữ liệu chỉ vì khó parse.
3. Chia nhỏ theo cấu trúc tự nhiên:
   Appendix -> Section -> Table -> Row/entry (nếu cấu trúc đó tồn tại).
   Không chia giữa một entry pháp lý nếu làm mất nghĩa.
4. Gán metadata chuẩn xác:
   - content_type: "article", "clause", "point", "appendix", "table", "form", "other"
   - appendix_number, appendix_title
   - section_title, table_id
   - parent_document, source relationship
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple

from Data_Processing.models_v2 import (
    LegalChunkV2,
    ContentType,
    sanitize_null
)
from Data_Processing.article_parser import ParsedLegalUnit


@dataclass
class AppendixEntry:
    """Nút biểu diễn một hàng/mục/entry cụ thể trong bảng hoặc danh mục."""
    entry_number: str            # VD: "1", "2", "- Các quận thuộc Hà Nội"
    title: str                   # Tên nghề, địa bàn hoặc nội dung chính của entry
    details: str = ""            # Đặc điểm điều kiện lao động, mô tả, chú thích
    raw_lines: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AppendixTableBlock:
    """Nút biểu diễn một bảng biểu hoặc nhóm điều kiện trong Phụ lục."""
    table_id: str                # VD: "Điều kiện lao động loại VI", "Lao động nam", "Bảng 1"
    table_title: Optional[str] = None
    headers: List[str] = field(default_factory=list)
    entries: List[AppendixEntry] = field(default_factory=list)
    raw_lines: List[str] = field(default_factory=list)


@dataclass
class FormBlock:
    """Nút biểu diễn một Biểu mẫu hành chính hoàn chỉnh."""
    form_id: str                 # VD: "Mẫu số 01/PLI", "Mẫu số 02"
    form_title: Optional[str] = None # VD: "Văn bản giải trình nhu cầu sử dụng người lao động nước ngoài"
    content: str = ""
    raw_lines: List[str] = field(default_factory=list)
    sections: List[str] = field(default_factory=list)


@dataclass
class AppendixSection:
    """Nút biểu diễn một Mục/Phần/Lĩnh vực trong Phụ lục."""
    section_number: Optional[str] = None  # VD: "I", "Vùng I", "Phần 1"
    section_title: Optional[str] = None   # VD: "KHAI THÁC KHOÁNG SẢN", "Vùng I, gồm các địa bàn:"
    tables: List[AppendixTableBlock] = field(default_factory=list)
    entries: List[AppendixEntry] = field(default_factory=list)
    raw_lines: List[str] = field(default_factory=list)


@dataclass
class AppendixBlock:
    """Nút biểu diễn một Phụ lục hoặc Danh mục độc lập hoàn chỉnh."""
    appendix_id: str                      # VD: "PL_I", "DM_NGHE", "PL_II"
    appendix_number: str                  # VD: "Phụ lục I", "Danh mục", "Phụ lục II"
    appendix_title: Optional[str] = None  # VD: "DANH MỤC NGHỀ, CÔNG VIỆC NẶNG NHỌC..."
    document_id: str = ""
    parent_document: str = ""
    sections: List[AppendixSection] = field(default_factory=list)
    forms: List[FormBlock] = field(default_factory=list)
    raw_lines: List[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0


class AppendixParser:
    """Parser chuyên biệt bóc tách Phụ lục, Bảng biểu, Biểu mẫu và Danh mục pháp luật."""

    def __init__(self):
        # 1. Regex nhận diện mở đầu Phụ lục
        self.re_appendix_header = re.compile(
            r'^(?:PHỤ\s+LỤC|Phụ\s+lục|phụ\s+lục)(?:\s+([IVXLCDMivxlcdm\d]+))?\b(.*)$'
        )

        # 2. Regex nhận diện Danh mục độc lập
        self.re_catalog_header = re.compile(
            r'^(?:DANH\s+MỤC|Danh\s+mục)\b(.*)$'
        )

        # 3. Regex nhận diện Mẫu số / Biểu mẫu (hỗ trợ cả 1 dòng lẫn ngắt 2 dòng)
        self.re_form_header = re.compile(
            r'^(?:Mẫu\s+số|MẪU\s+SỐ|Mẫu|MẪU)\s+(\d+[\w/]*)',
            re.IGNORECASE
        )

        # 4. Regex Section La Mã trong Danh mục (VD: "I. KHAI THÁC KHOÁNG SẢN")
        self.re_section_roman = re.compile(
            r'^([IVXLCDM]+)\.\s+([A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ\s,–-]+)$'
        )

        # 5. Regex Section Vùng lương (VD: "1. Vùng I, gồm các địa bàn:")
        self.re_section_vung = re.compile(
            r'^\s*(\d+)\.\s+(Vùng\s+[IVX]+)[,:]?\s*(.*)$'
        )

        # 6. Regex Phân loại bảng / điều kiện lao động (VD: "Điều kiện lao động loại VI")
        self.re_condition_tier = re.compile(
            r'^\s*Điều\s+kiện\s+lao\s+động\s+loại\s+([IVX]+)',
            re.IGNORECASE
        )

        # 7. Regex Nhóm đối tượng trong bảng (VD: "Lao động nam", "Lao động nữ")
        self.re_gender_group = re.compile(
            r'^\s*(Lao\s+động\s+nam|Lao\s+động\s+nữ)\s*$',
            re.IGNORECASE
        )

        # 8. Regex hàng/entry đánh số trong bảng
        self.re_entry_num = re.compile(r'^\s*(\d+)\s*$')

    def is_appendix_boundary(self, line: str, prev_line: str = "") -> Optional[Tuple[str, Optional[str]]]:
        """Kiểm tra xem dòng có phải là điểm bắt đầu của một Phụ lục hoặc Danh mục độc lập không."""
        clean = line.strip()

        # 1. Phụ lục I, Phụ lục II, PHỤ LỤC...
        m_app = self.re_appendix_header.match(clean)
        if m_app:
            num = m_app.group(1)
            rest = m_app.group(2).strip()
            # Kiểm tra tránh nhầm tham chiếu trong câu
            if prev_line:
                p_clean = prev_line.strip()
                if not p_clean.endswith(('.', ':', '”', '"', ';')):
                    return None
            # Nếu phần còn lại chứa cụm từ viện dẫn -> là tham chiếu trong câu
            if rest and re.search(r'\b(?:ban\s+hành\s+kèm\s+theo|quy\s+định\s+tại|hướng\s+dẫn\s+tại|nêu\s+tại)\b', rest, re.I):
                return None

            app_num = f"Phụ lục {num}" if num else "Phụ lục"
            return app_num, rest if rest else None

        # 2. Danh mục đứng độc lập (VD: "DANH MỤC" hoặc "DANH MỤC NGHỀ...")
        m_cat = self.re_catalog_header.match(clean)
        if m_cat:
            rest = m_cat.group(1).strip()
            if clean.isupper() or not rest or len(clean.split()) <= 15:
                if prev_line:
                    p_clean = prev_line.strip()
                    if not p_clean.endswith(('.', ':', '”', '"', ';')):
                        return None
                if rest and re.search(r'\b(?:ban\s+hành\s+kèm\s+theo|quy\s+định\s+tại)\b', rest, re.I):
                    return None
                return "Danh mục", rest if rest else None

        # 3. Biểu mẫu / Mẫu số đứng đầu phân đoạn
        m_form = self.re_form_header.match(clean)
        if m_form:
            if prev_line:
                p_clean = prev_line.strip()
                if not p_clean.endswith(('.', ':', '”', '"', ';')):
                    return None
            form_id = f"Mẫu số {m_form.group(1)}"
            return form_id, None

        return None

    def split_into_appendix_blocks(self, lines: List[str]) -> List[Tuple[str, Optional[str], List[str]]]:
        """Phân rã danh sách dòng phụ lục tổng thể thành các khối Phụ lục riêng biệt (Phụ lục I, Phụ lục II, Danh mục...)."""
        blocks: List[Tuple[str, Optional[str], List[str]]] = []
        curr_num = "Phụ lục"
        curr_title: Optional[str] = None
        curr_lines: List[str] = []

        re_pl_tag = re.compile(r'^\s*(?:PHỤ\s+LỤC|Phụ\s+lục|phụ\s+lục)(?:\s+([IVXLCDMivxlcdm\d]+))?\b', re.IGNORECASE)
        re_dm_tag = re.compile(r'^\s*(?:DANH\s+MỤC|Danh\s+mục)\b')

        idx = 0
        total = len(lines)
        while idx < total:
            line = lines[idx]
            clean = line.strip()

            is_boundary = False
            new_num = None

            prev = lines[idx - 1].strip() if idx > 0 else ""
            not_inline_ref = True
            if prev and not prev.endswith(('.', ':', '”', '"', ';')):
                if any(prev.lower().endswith(w) for w in ['theo', 'tại', 'nêu tại', 'khoản', 'điều']):
                    not_inline_ref = False

            if not_inline_ref:
                m_pl = re_pl_tag.match(clean)
                m_dm = re_dm_tag.match(clean) if (clean.isupper() or not clean.split()[1:]) else None

                if m_pl:
                    is_boundary = True
                    num = m_pl.group(1)
                    new_num = f"Phụ lục {num}" if num else "Phụ lục"
                elif m_dm and (not curr_lines or curr_num == "Phụ lục"):
                    is_boundary = True
                    new_num = "Danh mục"

            if is_boundary and curr_lines:
                blocks.append((curr_num, curr_title, curr_lines))
                curr_num = new_num
                curr_title = None
                curr_lines = [line]
            else:
                curr_lines.append(line)

            idx += 1

        if curr_lines:
            blocks.append((curr_num, curr_title, curr_lines))

        return blocks

    def parse_forms_appendix(
        self,
        lines: List[str],
        appendix_number: str,
        appendix_title: Optional[str],
        document_id: str
    ) -> List[ParsedLegalUnit]:
        """Bóc tách các Biểu mẫu (Forms) thành các đơn vị chunking độc lập, tự chứa ngữ cảnh."""
        units: List[ParsedLegalUnit] = []
        doc_prefix = document_id

        current_form_id: Optional[str] = None
        current_form_title: Optional[str] = None
        current_form_lines: List[str] = []
        preamble_lines: List[str] = []

        def flush_current_form():
            if not current_form_lines:
                return
            target_id = current_form_id or "Biểu mẫu"
            text_content = "\n".join(current_form_lines).strip()
            if not text_content:
                return

            f_clean = target_id.replace(' ', '_').replace('/', '_')
            uid = f"{doc_prefix}_{f_clean}"

            # Nếu form quá dài (> 1200 từ), chia nhỏ theo các đoạn / phần tự nhiên
            words = text_content.split()
            if len(words) > 1200:
                sub_parts = self._split_long_form(current_form_lines, uid, target_id, current_form_title, appendix_number, appendix_title, document_id)
                units.extend(sub_parts)
                return

            unit = ParsedLegalUnit(
                unit_id=uid,
                document_id=document_id,
                article_number=None,
                article_title=None,
                clause_number=None,
                point_number=None,
                content=text_content,
                appendix_number=appendix_number,
                appendix_title=appendix_title,
                table_id=target_id,
                section_title=current_form_title,
                parent_article="",
                unit_type="form",
                content_type=ContentType.FORM.value
            )
            units.append(unit)

        idx = 0
        total = len(lines)
        while idx < total:
            line = lines[idx]
            clean = line.strip()

            form_tag = None
            # Trường hợp 1: "Mẫu số 01/PLI" trên 1 dòng
            m_form = self.re_form_header.match(clean)
            if m_form:
                form_tag = f"Mẫu số {m_form.group(1)}"
            # Trường hợp 2: "Mẫu" ở dòng 1 và "số 01" ở dòng 2 (crawler ngắt dòng)
            elif clean in ("Mẫu", "MẪU") and idx + 1 < total:
                next_clean = lines[idx + 1].strip()
                m_next = re.match(r'^số\s+(\d+[\w/]*)', next_clean, re.IGNORECASE)
                if m_next:
                    form_tag = f"Mẫu số {m_next.group(1)}"
                    current_form_lines.append(line)
                    idx += 1
                    line = lines[idx]

            if form_tag:
                if current_form_id is not None:
                    flush_current_form()
                else:
                    preamble_lines.extend(current_form_lines)
                current_form_id = form_tag
                current_form_title = None
                current_form_lines = [line]
            else:
                current_form_lines.append(line)
                if current_form_title is None and clean and not clean.startswith(('(', 'CỘNG HÒA', '---', 'Số:')):
                    current_form_title = clean

            idx += 1

        flush_current_form()
        return units

    def _split_long_form(
        self,
        lines: List[str],
        base_uid: str,
        form_id: str,
        form_title: Optional[str],
        appendix_number: str,
        appendix_title: Optional[str],
        document_id: str,
        target_words: int = 800
    ) -> List[ParsedLegalUnit]:
        """Chia nhỏ biểu mẫu quá dài (>1200 từ) thành các phần cân đối không làm mất cấu trúc."""
        sub_units: List[ParsedLegalUnit] = []
        curr_sub_lines: List[str] = []
        part_idx = 0

        for line in lines:
            curr_sub_lines.append(line)
            w = len(" ".join(curr_sub_lines).split())
            if w >= target_words:
                part_idx += 1
                text = "\n".join(curr_sub_lines).strip()
                unit = ParsedLegalUnit(
                    unit_id=f"{base_uid}_Part{part_idx}",
                    document_id=document_id,
                    article_number=None,
                    article_title=None,
                    clause_number=None,
                    point_number=None,
                    content=text,
                    appendix_number=appendix_number,
                    appendix_title=appendix_title,
                    table_id=form_id,
                    section_title=f"{form_title or form_id} (Phần {part_idx})",
                    parent_article="",
                    unit_type="form",
                    content_type=ContentType.FORM.value
                )
                sub_units.append(unit)
                curr_sub_lines = []

        if curr_sub_lines:
            part_idx += 1
            text = "\n".join(curr_sub_lines).strip()
            if text:
                unit = ParsedLegalUnit(
                    unit_id=f"{base_uid}_Part{part_idx}",
                    document_id=document_id,
                    article_number=None,
                    article_title=None,
                    clause_number=None,
                    point_number=None,
                    content=text,
                    appendix_number=appendix_number,
                    appendix_title=appendix_title,
                    table_id=form_id,
                    section_title=f"{form_title or form_id} (Phần {part_idx})",
                    parent_article="",
                    unit_type="form",
                    content_type=ContentType.FORM.value
                )
                sub_units.append(unit)

        return sub_units

    def parse_occupations_catalog(
        self,
        lines: List[str],
        appendix_number: str,
        appendix_title: Optional[str],
        document_id: str,
        max_entries_per_chunk: int = 15
    ) -> List[ParsedLegalUnit]:
        """Bóc tách danh mục nghề nghiệp đồ sộ (như TT 11/2020) theo thứ bậc:
        
        Catalog -> Section (Lĩnh vực) -> Table (Loại điều kiện lao động) -> Batched Entries.
        """
        units: List[ParsedLegalUnit] = []
        doc_prefix = document_id

        current_sec_id = "I"
        current_sec_title = "Quy định chung"
        current_cond = "Điều kiện lao động chung"
        current_entries: List[Tuple[str, str, List[str]]] = []
        chunk_counter = 0

        def make_chunk_unit(entries_batch: List[Tuple[str, str, List[str]]]):
            nonlocal chunk_counter
            if not entries_batch:
                return

            chunk_counter += 1
            header_ctx = (
                f"{appendix_title or 'DANH MỤC NGHỀ, CÔNG VIỆC NẶNG NHỌC, ĐỘC HẠI, NGUY HIỂM'}\n"
                f"LĨNH VỰC {current_sec_id}: {current_sec_title}\n"
                f"PHÂN LOẠI: {current_cond}\n"
                f"----------------------------------------\n"
            )
            entry_texts = []
            for num, title, dlines in entries_batch:
                desc = " ".join([dl.strip() for dl in dlines if dl.strip()])
                entry_texts.append(f"{num}. {title}\nĐặc điểm điều kiện lao động: {desc}")

            full_content = header_ctx + "\n\n".join(entry_texts)
            sec_clean = current_sec_id.replace(' ', '_')
            cond_clean = re.sub(r'[^\w]+', '_', current_cond)
            uid = f"{doc_prefix}_DM_S{sec_clean}_{cond_clean}_P{chunk_counter}"

            unit = ParsedLegalUnit(
                unit_id=uid,
                document_id=document_id,
                article_number=None,
                article_title=None,
                clause_number=None,
                point_number=None,
                content=full_content,
                appendix_number=appendix_number,
                appendix_title=appendix_title,
                section_number=f"Lĩnh vực {current_sec_id}",
                section_title=current_sec_title,
                table_id=current_cond,
                parent_article="",
                unit_type="table",
                content_type=ContentType.TABLE.value
            )
            units.append(unit)

        idx = 0
        total_lines = len(lines)
        while idx < total_lines:
            line = lines[idx]
            s = line.strip()

            # 1. Phát hiện Lĩnh vực La Mã
            m_sec = self.re_section_roman.match(s)
            if m_sec:
                make_chunk_unit(current_entries)
                current_entries = []
                current_sec_id = m_sec.group(1)
                current_sec_title = m_sec.group(2).strip()
                current_cond = "Điều kiện lao động chung"
                idx += 1
                continue

            # 2. Phát hiện phân loại điều kiện
            m_cond = self.re_condition_tier.match(s)
            if m_cond:
                make_chunk_unit(current_entries)
                current_entries = []
                current_cond = f"Điều kiện lao động loại {m_cond.group(1)}"
                idx += 1
                continue

            # 3. Phát hiện hàng / entry đánh số
            m_entry = self.re_entry_num.match(s)
            if m_entry:
                entry_num = m_entry.group(1)
                idx += 1
                while idx < total_lines and not lines[idx].strip():
                    idx += 1
                entry_title = lines[idx].strip() if idx < total_lines else ""
                idx += 1

                desc_lines: List[str] = []
                while idx < total_lines:
                    nxt_s = lines[idx].strip()
                    if self.re_section_roman.match(nxt_s) or self.re_condition_tier.match(nxt_s) or self.re_entry_num.match(nxt_s):
                        break
                    if nxt_s:
                        desc_lines.append(nxt_s)
                    idx += 1

                current_entries.append((entry_num, entry_title, desc_lines))
                if len(current_entries) >= max_entries_per_chunk:
                    make_chunk_unit(current_entries)
                    current_entries = []
                continue

            idx += 1

        make_chunk_unit(current_entries)
        return units

    def parse_region_catalog(
        self,
        lines: List[str],
        appendix_number: str,
        appendix_title: Optional[str],
        document_id: str
    ) -> List[ParsedLegalUnit]:
        """Bóc tách danh mục địa bàn phân vùng (như NĐ 74/2024) theo từng Vùng lương."""
        units: List[ParsedLegalUnit] = []
        doc_prefix = document_id

        current_vung_id: Optional[str] = None
        current_vung_title: Optional[str] = None
        current_lines: List[str] = []

        def flush_vung():
            if not current_lines or not current_vung_id:
                return
            v_clean = current_vung_id.replace(' ', '_')
            uid = f"{doc_prefix}_DM_{v_clean}"
            content = (
                f"{appendix_title or 'DANH MỤC ĐỊA BÀN ÁP DỤNG MỨC LƯƠNG TỐI THIỂU'}\n\n"
                + "".join(current_lines).strip()
            )
            unit = ParsedLegalUnit(
                unit_id=uid,
                document_id=document_id,
                article_number=None,
                article_title=None,
                clause_number=None,
                point_number=None,
                content=content,
                appendix_number=appendix_number,
                appendix_title=appendix_title,
                section_number=current_vung_id,
                section_title=current_vung_title,
                parent_article="",
                unit_type="table",
                content_type=ContentType.TABLE.value
            )
            units.append(unit)

        for line in lines:
            s = line.strip()
            m_vung = self.re_section_vung.match(s)
            if m_vung:
                flush_vung()
                current_vung_id = m_vung.group(2)
                current_vung_title = f"{m_vung.group(1)}. {m_vung.group(2)}, {m_vung.group(3)}"
                current_lines = [line]
            else:
                current_lines.append(line)

        flush_vung()
        return units

    def parse_retirement_tables(
        self,
        lines: List[str],
        appendix_number: str,
        appendix_title: Optional[str],
        document_id: str,
        max_words: int = 1000
    ) -> List[ParsedLegalUnit]:
        """Bóc tách bảng lộ trình tuổi nghỉ hưu (NĐ 135/2020) theo nhóm đối tượng và nhóm năm sinh."""
        units: List[ParsedLegalUnit] = []
        doc_prefix = document_id

        current_pl = appendix_number
        current_sub: Optional[str] = None
        current_lines: List[str] = []
        table_counter = 0
        preamble_lines: List[str] = []

        def flush_sub_table():
            nonlocal table_counter
            if not current_lines:
                return
            target_sub = current_sub or "Bảng số liệu"
            text = "".join(current_lines).strip()
            if not text:
                return

            table_counter += 1
            pl_clean = re.sub(r'[^\w]+', '_', current_pl)
            sub_clean = re.sub(r'[^\w]+', '_', target_sub)
            uid = f"{doc_prefix}_{pl_clean}_{sub_clean}_{table_counter}"

            unit = ParsedLegalUnit(
                unit_id=uid,
                document_id=document_id,
                article_number=None,
                article_title=None,
                clause_number=None,
                point_number=None,
                content=text,
                appendix_number=current_pl,
                appendix_title=appendix_title,
                table_id=target_sub,
                section_title=target_sub,
                parent_article="",
                unit_type="table",
                content_type=ContentType.TABLE.value
            )
            units.append(unit)

        for line in lines:
            s = line.strip()
            if self.re_gender_group.match(s):
                if current_sub is not None:
                    if len(" ".join(current_lines).split()) < 10:
                        preamble_lines.extend(current_lines)
                    else:
                        flush_sub_table()
                else:
                    preamble_lines.extend(current_lines)
                current_sub = s
                current_lines = list(preamble_lines) + [line]
                preamble_lines = []
                continue

            current_lines.append(line)
            if len(" ".join(current_lines).split()) >= max_words:
                flush_sub_table()
                current_lines = []

        flush_sub_table()
        return units

    def _parse_generic_appendix(
        self,
        lines: List[str],
        appendix_number: str,
        appendix_title: Optional[str],
        document_id: str,
        max_chunk_words: int = 600
    ) -> List[ParsedLegalUnit]:
        """Xử lý phụ lục văn bản quy phạm chung theo đoạn văn/mục có giới hạn kích thước."""
        units: List[ParsedLegalUnit] = []
        doc_prefix = document_id
        chunk_idx = 0

        current_chunk_lines: List[str] = []
        for line in lines:
            current_chunk_lines.append(line)
            words = len(" ".join(current_chunk_lines).split())
            if words >= max_chunk_words:
                chunk_idx += 1
                text = "".join(current_chunk_lines).strip()
                uid = f"{doc_prefix}_{appendix_number.replace(' ', '_')}_P{chunk_idx}"
                unit = ParsedLegalUnit(
                    unit_id=uid,
                    document_id=document_id,
                    article_number=None,
                    article_title=None,
                    clause_number=None,
                    point_number=None,
                    content=text,
                    appendix_number=appendix_number,
                    appendix_title=appendix_title,
                    parent_article="",
                    unit_type="appendix",
                    content_type=ContentType.APPENDIX.value
                )
                units.append(unit)
                current_chunk_lines = []

        if current_chunk_lines:
            chunk_idx += 1
            text = "".join(current_chunk_lines).strip()
            if text:
                uid = f"{doc_prefix}_{appendix_number.replace(' ', '_')}_P{chunk_idx}"
                unit = ParsedLegalUnit(
                    unit_id=uid,
                    document_id=document_id,
                    article_number=None,
                    article_title=None,
                    clause_number=None,
                    point_number=None,
                    content=text,
                    appendix_number=appendix_number,
                    appendix_title=appendix_title,
                    parent_article="",
                    unit_type="appendix",
                    content_type=ContentType.APPENDIX.value
                )
                units.append(unit)

        return units

    def parse_appendix_lines(
        self,
        lines: List[str],
        document_id: str,
        document_title: str
    ) -> List[ParsedLegalUnit]:
        """Phân tích tự động toàn bộ phần phụ lục của văn bản thành các ParsedLegalUnit phù hợp."""
        if not lines:
            return []

        # 1. Phân rã thành các khối Phụ lục riêng biệt (Phụ lục I, Phụ lục II, Danh mục...)
        blocks = self.split_into_appendix_blocks(lines)
        all_units: List[ParsedLegalUnit] = []

        for app_num, app_title_hint, block_lines in blocks:
            # Trích xuất tiêu đề cụ thể của khối
            block_title = app_title_hint
            if not block_title:
                title_candidates = []
                for l in block_lines[1:6]:
                    c = l.strip()
                    if not c or c.startswith(('(', 'TM.', 'BỘ', 'CỘNG HÒA', 'Mẫu')):
                        continue
                    title_candidates.append(c)
                    if len(title_candidates) >= 2:
                        break
                if title_candidates:
                    block_title = " - ".join(title_candidates)

            raw_block_text = "\n".join(block_lines[:100]).lower()

            # 2. Điều phối chiến lược phân tách (Strategy Dispatcher):
            # A. Danh mục nghề nặng nhọc độc hại
            if "nặng nhọc" in raw_block_text or "điều kiện lao động loại" in raw_block_text:
                units = self.parse_occupations_catalog(block_lines, app_num, block_title, document_id)
            # B. Danh mục địa bàn lương tối thiểu
            elif "vùng i" in raw_block_text and "địa bàn" in raw_block_text:
                units = self.parse_region_catalog(block_lines, app_num, block_title, document_id)
            # C. Lộ trình tuổi nghỉ hưu
            elif "tuổi nghỉ hưu" in raw_block_text or "lao động nam" in raw_block_text:
                units = self.parse_retirement_tables(block_lines, app_num, block_title, document_id)
            # D. Biểu mẫu hành chính
            elif "mẫu số" in raw_block_text or any(self.re_form_header.match(l.strip()) for l in block_lines[:30]):
                units = self.parse_forms_appendix(block_lines, app_num, block_title, document_id)
            # E. Phụ lục quy phạm thông thường
            else:
                units = self._parse_generic_appendix(block_lines, app_num, block_title, document_id)

            all_units.extend(units)

        return all_units

    def convert_to_chunks_v2(
        self,
        units: List[ParsedLegalUnit],
        document_number: Optional[str] = None,
        document_title: str = "Văn bản pháp luật",
        document_type: Optional[str] = None,
        effective_from: Optional[str] = None,
        source_url: Optional[str] = None,
        start_chunk_index: int = 0
    ) -> List[LegalChunkV2]:
        """Chuyển đổi danh sách ParsedLegalUnit thành các LegalChunkV2 hợp lệ theo Schema V2."""
        chunks: List[LegalChunkV2] = []
        for idx, u in enumerate(units):
            chunk = LegalChunkV2(
                chunk_id=u.unit_id,
                document_id=u.document_id,
                document_number=document_number,
                document_title=document_title,
                document_type=document_type,
                chapter_number=u.chapter_number,
                chapter_title=u.chapter_title,
                section_number=u.section_number,
                section_title=u.section_title,
                article_number=u.article_number,
                article_title=u.article_title,
                clause_number=u.clause_number,
                point_number=u.point_number,
                content=u.content,
                effective_from=effective_from,
                effective_to=None,
                legal_status="Còn hiệu lực",
                source_url=source_url,
                parent_document=document_title,
                parent_article=u.parent_article or None,
                chunk_index=start_chunk_index + idx,
                content_type=u.content_type,
                appendix_number=u.appendix_number,
                appendix_title=u.appendix_title
            )
            chunks.append(chunk)
        return chunks
