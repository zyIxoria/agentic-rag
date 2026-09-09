"""metadata_restorer.py - Legal Document Metadata Restoration & Propagation.

Cung cấp công cụ khôi phục và chuẩn hóa toàn diện metadata từ kho dữ liệu thô (raw corpus)
vào Legal Dataset V2 theo yêu cầu của TASK DATA-07:
1. Trích xuất và làm sạch metadata văn bản:
   - document_id
   - document_number (Số hiệu văn bản)
   - document_title (Tên/tiêu đề chính thức của văn bản)
   - document_type (Loại văn bản: Bộ luật, Nghị định, Thông tư, Quyết định)
   - source_url (Đường dẫn tra cứu chính thức)
   - issue_date (Ngày ban hành văn bản)
   - effective_from (Ngày bắt đầu có hiệu lực)
   - effective_to (Ngày hết hiệu lực - mặc định null nếu còn hiệu lực)
   - legal_status (Tình trạng hiệu lực)
2. Nguyên tắc nghiêm ngặt:
   - KHÔNG tự bịa (invent) metadata.
   - Nếu raw data không có, rỗng, hoặc là placeholder ("Đã biết", "Chưa xác định", "0") -> ghi nhận null (None).
3. Đảm bảo tính nhất quán (Consistency):
   - Mọi chunk thuộc cùng một văn bản đều kế thừa chính xác và đồng nhất các trường metadata cấp văn bản.
"""

from __future__ import annotations
import os
import re
import json
import glob
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Tuple, List

from Data_Processing.models_v2 import sanitize_null, NULL_PLACEHOLDERS


@dataclass
class DocumentMetadata:
    """Dataclass chứa siêu dữ liệu cấp văn bản quy phạm pháp luật đã được phục hồi và chuẩn hóa."""
    document_id: str
    document_number: Optional[str]
    document_title: str
    document_type: str
    source_url: Optional[str]
    issue_date: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    legal_status: Optional[str] = "unknown"
    issuing_authority: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Xuất metadata ra dictionary."""
        return asdict(self)


class DocumentMetadataRestorer:
    """Bộ phục hồi và đồng bộ hóa siêu dữ liệu văn bản pháp luật."""

    def __init__(self):
        # Regex trích xuất ngày tháng theo định dạng DD/MM/YYYY
        self.re_date = re.compile(r'(\d{1,2}/\d{1,2}/\d{4})')
        # Regex tìm khối tiêu đề văn bản chính thức sau từ khóa loại văn bản
        self.re_title_block = re.compile(
            r'(?:NGHỊ\s+ĐỊNH|THÔNG\s+TƯ|QUYẾT\s+ĐỊNH|BỘ\s+LUẬT|LUẬT)\s*\n+(.*?)(?=\n+\s*(?:Căn\s+cứ|Chính\s+phủ|Bộ\s+trưởng|Thủ\s+tướng|Điều\s+1|Chương\s+I|\(\s*Kèm\s+theo))',
            re.DOTALL | re.IGNORECASE
        )

    def clean_document_number(self, raw_so_hieu: Any) -> Optional[str]:
        """Làm sạch số hiệu văn bản, loại bỏ các dòng nhiễu do crawler sinh ra."""
        if not raw_so_hieu or not isinstance(raw_so_hieu, str):
            return None
        clean = raw_so_hieu.strip()
        if not clean or clean.lower() in NULL_PLACEHOLDERS:
            return None

        # Lấy dòng đầu tiên trước khi gặp ký tự xuống dòng hoặc nhãn "Loại văn bản:"
        first_line = clean.split('\n')[0].strip()
        # Loại bỏ tiền tố "Số:" hoặc "Số"
        first_line = re.sub(r'^(?:Số:|Số)\s*', '', first_line, flags=re.IGNORECASE).strip()
        # Loại bỏ khoảng trắng thừa giữa các ký tự phân tách số hiệu
        first_line = re.sub(r'\s+', '', first_line)

        return sanitize_null(first_line)

    def extract_document_type(
        self,
        raw_so_hieu: str,
        raw_loai: str,
        doc_id: str
    ) -> str:
        """Nhận diện chính xác loại văn bản quy phạm pháp luật."""
        # 1. Kiểm tra trường loai_van_ban nếu có sẵn
        if raw_loai and isinstance(raw_loai, str) and raw_loai.strip():
            clean_loai = raw_loai.strip()
            if clean_loai.lower() not in NULL_PLACEHOLDERS:
                if doc_id.startswith("BLLD"):
                    return "Bộ luật"
                return clean_loai

        # 2. Bóc tách từ cụm "Loại văn bản: ..." nằm trong so_hieu do crawler gộp
        if raw_so_hieu and isinstance(raw_so_hieu, str):
            m = re.search(r'Loại\s+văn\s+bản:\s*([^\n]+)', raw_so_hieu, re.IGNORECASE)
            if m:
                extracted = m.group(1).strip()
                if extracted and extracted.lower() not in NULL_PLACEHOLDERS:
                    if doc_id.startswith("BLLD"):
                        return "Bộ luật"
                    return extracted

        # 3. Phán đoán dựa trên tiền tố doc_id hoặc cấu trúc số hiệu
        if doc_id.startswith("BLLD"):
            return "Bộ luật"
        elif doc_id.startswith("ND_") or "/NĐ-CP" in str(raw_so_hieu):
            return "Nghị định"
        elif doc_id.startswith("TT_") or "/TT-" in str(raw_so_hieu):
            return "Thông tư"
        elif doc_id.startswith("QD_") or "/QĐ-" in str(raw_so_hieu):
            return "Quyết định"

        return "Văn bản quy phạm"

    def parse_and_validate_date(self, val: Any) -> Optional[str]:
        """Kiểm tra và bóc tách ngày hợp lệ từ chuỗi ngày tháng hoặc dữ liệu thô.
        
        Quy tắc nghiêm ngặt theo TASK DATA-08:
        - Tuyệt đối không chuyển đổi text status (VD: 'Đã biết', 'Chưa xác định') thành date.
        - Trả về None nếu rỗng hoặc là placeholder.
        - Kiểm tra tính hợp lệ của ngày tháng thực tế (ngày 1-31, tháng 1-12, năm nhuận).
        - Chấp nhận DD/MM/YYYY hoặc YYYY-MM-DD.
        """
        if not val or not isinstance(val, str):
            return None
        clean = val.strip()
        if not clean or clean.lower() in NULL_PLACEHOLDERS:
            return None

        # 1. Match DD/MM/YYYY hoặc D/M/YYYY
        m1 = re.search(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', clean)
        if m1:
            d, m, y = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
            try:
                datetime(y, m, d)
                return f"{d:02d}/{m:02d}/{y:04d}"
            except ValueError:
                return None

        # 2. Match YYYY-MM-DD
        m2 = re.search(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', clean)
        if m2:
            y, m, d = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
            try:
                datetime(y, m, d)
                return f"{y:04d}-{m:02d}-{d:02d}"
            except ValueError:
                return None

        return None

    def extract_dates(
        self,
        raw_ban_hanh: Any,
        raw_hieu_luc: Any
    ) -> Tuple[Optional[str], Optional[str]]:
        """Bóc tách ngày ban hành (issue_date) và ngày có hiệu lực (effective_from).
        
        Quy tắc theo TASK DATA-08:
        - issue_date: Chỉ lấy từ phần ngày ban hành của văn bản (ngay_ban_hanh).
        - effective_from: Chỉ lấy từ trường ngay_hieu_luc hoặc từ nhãn 'Ngày hiệu lực: <date>' nếu có ngày hợp lệ.
        - Tuyệt đối KHÔNG gán issue_date thành effective_from (hoàn toàn phân biệt, decoupled).
        - Tuyệt đối KHÔNG chuyển đổi text status (như 'Đã biết') thành date.
        - Không tự tạo/bịa đặt ngày hiệu lực nếu raw corpus không có -> trả về None (null).
        """
        issue_date: Optional[str] = None
        effective_from: Optional[str] = None

        if raw_ban_hanh and isinstance(raw_ban_hanh, str):
            # Tách phần ngày ban hành và phần ngày hiệu lực (nếu crawler gộp)
            parts = re.split(r'Ngày\s+hiệu\s+lực:', raw_ban_hanh, flags=re.IGNORECASE)
            ban_hanh_part = parts[0].strip()
            issue_date = self.parse_and_validate_date(ban_hanh_part)

            if len(parts) > 1:
                eff_part = parts[1].strip()
                effective_from = self.parse_and_validate_date(eff_part)

        # Nếu chưa tìm thấy effective_from và có trường raw_hieu_luc riêng
        if not effective_from and raw_hieu_luc and isinstance(raw_hieu_luc, str):
            effective_from = self.parse_and_validate_date(raw_hieu_luc)

        return issue_date, effective_from

    def extract_legal_status(self, raw_status: Any) -> str:
        """Chuẩn hóa tình trạng hiệu lực pháp lý theo TASK DATA-08.
        
        Quy tắc:
        - Nếu có trạng thái pháp lý cụ thể (Còn hiệu lực, Hết hiệu lực, Hết hiệu lực một phần, Chưa có hiệu lực, Ngưng hiệu lực), trả về trạng thái đó.
        - Nếu raw status rỗng, thiếu, hoặc là placeholder ('Đã biết', 'Chưa xác định', None, '0') -> ghi nhận 'unknown'.
        - Tuyệt đối không tự suy đoán.
        """
        if not raw_status or not isinstance(raw_status, str):
            return "unknown"
        clean = raw_status.strip()
        if not clean or clean.lower() in NULL_PLACEHOLDERS:
            return "unknown"
        return clean

    def extract_official_title(
        self,
        raw_text: str,
        doc_id: str,
        doc_type: str,
        doc_number: Optional[str]
    ) -> str:
        """Khôi phục tiêu đề đầy đủ, chính thức của văn bản từ phần đầu văn bản thô."""
        # Riêng Bộ luật Lao động
        if doc_id.startswith("BLLD"):
            num_part = f" số {doc_number}" if doc_number else ""
            return f"Bộ luật Lao động 2019{num_part}"

        # Tìm khối nội dung tên văn bản sau danh xưng loại văn bản
        m = self.re_title_block.search(raw_text[:2500])
        if m:
            title_content = m.group(1).strip()
            title_content = re.sub(r'\s+', ' ', title_content)
            # Loại bỏ các ghi chú mở ngoặc nếu có ở đầu tiêu đề
            title_content = re.sub(r'^\([^)]+\)\s*', '', title_content).strip()
            num_str = f" số {doc_number}" if doc_number else ""
            return f"{doc_type}{num_str} {title_content}".strip()

        # Fallback có căn cứ: Tên loại + số hiệu
        num_str = f" số {doc_number}" if doc_number else ""
        return f"{doc_type}{num_str}".strip()

    def restore_metadata(
        self,
        raw_meta: Dict[str, Any],
        raw_text: str,
        doc_id: str
    ) -> DocumentMetadata:
        """Phục hồi toàn bộ siêu dữ liệu cấp văn bản từ raw_meta và raw_text."""
        raw_so_hieu = raw_meta.get("so_hieu") or raw_meta.get("document_number")
        doc_number = self.clean_document_number(raw_so_hieu)
        doc_type = self.extract_document_type(
            raw_so_hieu or "",
            raw_meta.get("loai_van_ban") or raw_meta.get("document_type") or "",
            doc_id
        )
        issue_date, effective_from = self.extract_dates(
            raw_meta.get("ngay_ban_hanh") or raw_meta.get("issue_date"),
            raw_meta.get("ngay_hieu_luc") or raw_meta.get("effective_from")
        )
        legal_status = self.extract_legal_status(
            raw_meta.get("tinh_trang_hieu_luc") or raw_meta.get("legal_status")
        )
        source_url = sanitize_null(raw_meta.get("source") or raw_meta.get("source_url"))
        issuing_authority = sanitize_null(raw_meta.get("co_quan_ban_hanh") or raw_meta.get("issuing_authority"))

        # Nếu document_title đã có sẵn hợp lệ thì giữ lại, nếu chưa có thì bóc tách từ raw_text
        existing_title = raw_meta.get("document_title")
        if existing_title and isinstance(existing_title, str) and existing_title.strip() and existing_title.strip() != doc_id:
            document_title = existing_title.strip()
        else:
            document_title = self.extract_official_title(raw_text, doc_id, doc_type, doc_number)

        return DocumentMetadata(
            document_id=doc_id,
            document_number=doc_number,
            document_title=document_title,
            document_type=doc_type,
            source_url=source_url,
            issue_date=issue_date,
            effective_from=effective_from,
            effective_to=None,
            legal_status=legal_status,
            issuing_authority=issuing_authority
        )

    def restore_from_files(self, meta_path: str, txt_path: str) -> DocumentMetadata:
        """Phục hồi siêu dữ liệu trực tiếp từ đường dẫn file meta.json và file .txt."""
        doc_id = os.path.basename(txt_path).replace(".txt", "")
        raw_meta: Dict[str, Any] = {}
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as fp:
                raw_meta = json.load(fp)

        raw_text = ""
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as fp:
                raw_text = fp.read()

        return self.restore_metadata(raw_meta, raw_text, doc_id)

    def build_corpus_catalog(self, raw_dir: str) -> Dict[str, DocumentMetadata]:
        """Quét toàn bộ thư mục raw corpus và xây dựng danh mục DocumentMetadata cho mọi văn bản."""
        catalog: Dict[str, DocumentMetadata] = {}
        txt_files = sorted(glob.glob(os.path.join(raw_dir, "*.txt")))

        for txt_path in txt_files:
            fname = os.path.basename(txt_path)
            doc_id = fname.replace(".txt", "")
            meta_path = os.path.join(raw_dir, f"{doc_id}_meta.json")
            doc_meta = self.restore_from_files(meta_path, txt_path)
            catalog[doc_id] = doc_meta

        return catalog

    def propagate_to_chunk_dict(
        self,
        chunk_dict: Dict[str, Any],
        doc_meta: DocumentMetadata
    ) -> Dict[str, Any]:
        """Lan truyền (propagate) nhất quán siêu dữ liệu cấp văn bản vào dictionary của từng chunk."""
        chunk_dict["document_id"] = doc_meta.document_id
        chunk_dict["document_number"] = doc_meta.document_number
        chunk_dict["document_title"] = doc_meta.document_title
        chunk_dict["document_type"] = doc_meta.document_type
        chunk_dict["source_url"] = doc_meta.source_url
        chunk_dict["issue_date"] = doc_meta.issue_date
        chunk_dict["effective_from"] = doc_meta.effective_from
        chunk_dict["effective_to"] = doc_meta.effective_to
        chunk_dict["legal_status"] = doc_meta.legal_status or "unknown"
        chunk_dict["parent_document"] = doc_meta.document_id

        return chunk_dict
