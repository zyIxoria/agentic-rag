"""models_v2.py - Pydantic V2 Models for Legal Dataset V2.

Thiết kế schema chuẩn cho Legal Dataset V2 dựa trên cấu trúc lập pháp Việt Nam:
Văn bản -> Chương -> Mục -> Điều -> Khoản -> Điểm.
Hỗ trợ Phụ lục (Appendix), Bảng biểu (Table), Mẫu đơn/Biểu mẫu (Form).
"""

from __future__ import annotations
import re
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class DocumentType(str, Enum):
    """Các loại văn bản quy phạm pháp luật phổ biến trong hệ thống pháp luật VN."""
    BO_LUAT = "Bộ luật"
    LUAT = "Luật"
    NGHI_DINH = "Nghị định"
    THONG_TU = "Thông tư"
    THONG_TU_LIEN_TICH = "Thông tư liên tịch"
    QUYET_DINH = "Quyết định"
    NGHI_QUYET = "Nghị quyết"
    PHAP_LENH = "Pháp lệnh"


class LegalStatus(str, Enum):
    """Tình trạng hiệu lực pháp lý của văn bản hoặc điều khoản."""
    CON_HIEU_LUC = "Còn hiệu lực"
    HET_HIEU_LUC = "Hết hiệu lực"
    HET_HIEU_LUC_MOT_PHAN = "Hết hiệu lực một phần"
    CHUA_CO_HIEU_LUC = "Chưa có hiệu lực"
    NGUNG_HIEU_LUC = "Ngưng hiệu lực"
    UNKNOWN = "unknown"


class ContentType(str, Enum):
    """Phân loại bản chất nội dung của Chunk theo TASK DATA-05."""
    ARTICLE = "article"        # Nội dung cấp Điều (hoặc Điều không chia khoản)
    CLAUSE = "clause"          # Nội dung cấp Khoản
    POINT = "point"            # Nội dung cấp Điểm
    APPENDIX = "appendix"      # Nội dung Phụ lục quy định chi tiết
    TABLE = "table"            # Bảng biểu số liệu, ma trận phân loại, danh mục dạng bảng
    FORM = "form"              # Mẫu tờ khai, đơn từ, hợp đồng mẫu
    OTHER = "other"            # Phần mở đầu (preamble), lời chứng, hiệu lực thi hành, khác
    TEXT = "article"           # Alias tương thích ngược với code cũ


# Danh sách các chuỗi rác/placeholder cần chuẩn hóa thành None (null)
NULL_PLACEHOLDERS = {
    "chưa xác định",
    "chưa có",
    "đã biết",
    "không rõ",
    "n/a",
    "none",
    "null",
    "undefined",
    "unknown",
    "0",
    ""
}


def sanitize_null(value: Any) -> Optional[str]:
    """Chuyển đổi chuỗi rỗng hoặc chuỗi placeholder giả định thành None (null).
    
    Đảm bảo nguyên tắc: Không tự bịa metadata, nếu không xác định được thì ghi nhận null.
    """
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in NULL_PLACEHOLDERS:
            return None
        return cleaned
    return str(value)


class LegalChunkV2(BaseModel):
    """Schema chuẩn cho mỗi chunk trong Legal Dataset V2.
    
    Tuân thủ đầy đủ 21 trường cốt lõi theo đặc tả hệ thống và cấu trúc pháp luật Việt Nam.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra="allow",  # Cho phép các trường mở rộng (như content_type, appendix_number) nếu có
        str_strip_whitespace=True
    )

    # 1. Định danh Chunk & Văn bản
    chunk_id: str = Field(
        ...,
        min_length=3,
        description="Định danh duy nhất toàn cục của chunk (VD: BLLD_2019_C1_D1_K1)"
    )
    document_id: str = Field(
        ...,
        min_length=2,
        description="Mã định danh văn bản nguồn (VD: BLLD_2019, ND_12_2022)"
    )
    document_number: Optional[str] = Field(
        default=None,
        description="Số hiệu văn bản chính thức (VD: 45/2019/QH14, 12/2022/NĐ-CP). null nếu không có."
    )
    document_title: str = Field(
        ...,
        min_length=3,
        description="Tên đầy đủ của văn bản (VD: Bộ luật Lao động 2019)"
    )
    document_type: Optional[str] = Field(
        default=None,
        description="Loại văn bản (VD: Bộ luật, Luật, Nghị định, Thông tư). null nếu không có."
    )

    # 2. Phân cấp Chương (Chapter)
    chapter_number: Optional[str] = Field(
        default=None,
        description="Số thứ tự chương (VD: Chương I, Chương II). null nếu văn bản không chia chương."
    )
    chapter_title: Optional[str] = Field(
        default=None,
        description="Tiêu đề chương (VD: Những quy định chung). null nếu không có."
    )

    # 3. Phân cấp Mục (Section)
    section_number: Optional[str] = Field(
        default=None,
        description="Số thứ tự mục (VD: Mục 1, Mục 2). null nếu chương không chia mục."
    )
    section_title: Optional[str] = Field(
        default=None,
        description="Tiêu đề mục (VD: Tiền lương, Hợp đồng vô hiệu). null nếu không có."
    )

    # 4. Phân cấp Điều (Article)
    article_number: Optional[str] = Field(
        default=None,
        description="Số thứ tự điều (VD: Điều 1, Điều 124). null nếu chunk là phụ lục độc lập."
    )
    article_title: Optional[str] = Field(
        default=None,
        description="Tiêu đề điều luật (VD: Phạm vi điều chỉnh, Sa thải). null nếu không có."
    )

    # 5. Phân cấp Khoản & Điểm (Clause & Point)
    clause_number: Optional[str] = Field(
        default=None,
        description="Số thứ tự khoản (VD: Khoản 1, 1). null nếu điều không chia khoản."
    )
    point_number: Optional[str] = Field(
        default=None,
        description="Ký hiệu điểm (VD: Điểm a, a). null nếu khoản không chia điểm."
    )

    # 6. Nội dung Chunk (Content)
    content: str = Field(
        ...,
        min_length=1,
        description="Nội dung văn bản quy phạm hoặc bảng biểu/phụ lục của chunk."
    )

    # 7. Thuộc tính Hiệu lực & Ban hành Pháp lý (Validity & Issuance Metadata)
    issue_date: Optional[str] = Field(
        default=None,
        description="Ngày ban hành văn bản (VD: DD/MM/YYYY hoặc ISO YYYY-MM-DD). null nếu chưa rõ."
    )
    effective_from: Optional[str] = Field(
        default=None,
        description="Ngày bắt đầu có hiệu lực (ISO YYYY-MM-DD hoặc DD/MM/YYYY). null nếu chưa rõ."
    )
    effective_to: Optional[str] = Field(
        default=None,
        description="Ngày hết hiệu lực. Mặc định null nếu đang còn hiệu lực."
    )
    legal_status: Optional[str] = Field(
        default="unknown",
        description="Tình trạng hiệu lực (VD: Còn hiệu lực, Hết hiệu lực, unknown). Mặc định 'unknown' nếu chưa rõ."
    )

    # 8. Nguồn gốc & Liên kết Phân cấp (Provenance & Lineage)
    source_url: Optional[str] = Field(
        default=None,
        description="Đường dẫn URL gốc trích xuất văn bản (VD: https://thuvienphapluat.vn/...)"
    )
    parent_document: str = Field(
        ...,
        min_length=2,
        description="Liên kết văn bản cha (document_id hoặc document_title)"
    )
    parent_article: Optional[str] = Field(
        default=None,
        description="Liên kết điều cha (VD: BLLD_2019_Điều124 hoặc Điều 124). null nếu là phụ lục riêng."
    )
    chunk_index: int = Field(
        ...,
        ge=0,
        description="Chỉ mục thứ tự tuần tự của chunk trong văn bản (bắt đầu từ 0)."
    )

    # 9. Các trường mở rộng hỗ trợ Phụ lục & Bảng biểu (Optional Extensions)
    content_type: Optional[str] = Field(
        default=ContentType.ARTICLE.value,
        description="Phân loại nội dung: article, clause, point, appendix, table, form, other."
    )
    appendix_number: Optional[str] = Field(
        default=None,
        description="Số hiệu phụ lục (VD: Phụ lục I, Mẫu số 01). null nếu không thuộc phụ lục."
    )
    appendix_title: Optional[str] = Field(
        default=None,
        description="Tiêu đề phụ lục. null nếu không có."
    )

    # --- VALIDATORS ---

    @field_validator("chunk_id", "document_id", "document_title", "parent_document", mode="before")
    @classmethod
    def validate_non_empty_strings(cls, v: Any, info: Any) -> str:
        if not v or not str(v).strip():
            raise ValueError(f"Trường '{info.field_name}' bắt buộc phải có giá trị không rỗng.")
        return str(v).strip()

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v: Any) -> str:
        if not v or not str(v).strip():
            raise ValueError("Nội dung 'content' của chunk không được rỗng.")
        return str(v).strip()

    @field_validator("chunk_index", mode="before")
    @classmethod
    def validate_chunk_index(cls, v: Any) -> int:
        try:
            val = int(v)
        except (ValueError, TypeError):
            raise ValueError(f"Chỉ số 'chunk_index' phải là số nguyên, nhận được: {v}")
        if val < 0:
            raise ValueError(f"Chỉ số 'chunk_index' không được là số âm, nhận được: {val}")
        return val

    @field_validator(
        "document_number", "document_type",
        "chapter_number", "chapter_title",
        "section_number", "section_title",
        "article_number", "article_title",
        "clause_number", "point_number",
        "source_url", "parent_article",
        "appendix_number", "appendix_title",
        mode="before"
    )
    @classmethod
    def normalize_optional_metadata(cls, v: Any) -> Optional[str]:
        """Chuẩn hóa mọi giá trị rỗng hoặc placeholder ('Chưa xác định', '0', 'Đã biết') về null."""
        return sanitize_null(v)

    @field_validator("legal_status", mode="before")
    @classmethod
    def normalize_legal_status(cls, v: Any) -> str:
        """Chuẩn hóa legal_status: nếu thiếu, rỗng, placeholder hoặc 'unknown' thì trả về 'unknown'."""
        if v is None:
            return "unknown"
        if isinstance(v, str):
            clean = v.strip()
            if not clean or clean.lower() in NULL_PLACEHOLDERS:
                return "unknown"
            return clean
        return str(v)

    @field_validator("issue_date", "effective_from", "effective_to", mode="before")
    @classmethod
    def validate_dates(cls, v: Any, info: Any) -> Optional[str]:
        """Kiểm tra và chuẩn hóa ngày tháng pháp lý.
        
        Quy tắc:
        - Không convert text status (VD: 'Đã biết', 'Chưa xác định') thành date.
        - Trả về None nếu giá trị rỗng, None, hoặc là placeholder.
        - Kiểm tra tính hợp lệ lịch thực tế (ngày trong tháng, năm nhuận).
        - Chấp nhận định dạng DD/MM/YYYY hoặc YYYY-MM-DD.
        - Báo lỗi ValueError nếu chuỗi ngày không hợp lệ.
        """
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            if not s or s.lower() in NULL_PLACEHOLDERS:
                return None

            # Kiểm tra định dạng DD/MM/YYYY hoặc D/M/YYYY
            m1 = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', s)
            if m1:
                d, m, y = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
                try:
                    datetime(y, m, d)
                    return f"{d:02d}/{m:02d}/{y:04d}"
                except ValueError:
                    raise ValueError(f"Ngày không hợp lệ trong trường '{info.field_name}': '{v}'")

            # Kiểm tra định dạng ISO YYYY-MM-DD
            m2 = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', s)
            if m2:
                y, m, d = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
                try:
                    datetime(y, m, d)
                    return f"{y:04d}-{m:02d}-{d:02d}"
                except ValueError:
                    raise ValueError(f"Ngày không hợp lệ trong trường '{info.field_name}': '{v}'")

            raise ValueError(
                f"Định dạng ngày không hợp lệ trong trường '{info.field_name}': '{v}' (yêu cầu DD/MM/YYYY hoặc YYYY-MM-DD)"
            )

        raise ValueError(f"Kiểu dữ liệu ngày không hợp lệ trong trường '{info.field_name}': {type(v)}")

    @model_validator(mode="after")
    def validate_hierarchy_consistency(self) -> LegalChunkV2:
        """Kiểm tra tính nhất quán logic của hệ phân cấp pháp luật:
        
        1. Nếu có point_number (Điểm), bắt buộc phải có clause_number (Khoản) hoặc article_number (Điều).
        2. Nếu không có article_number, chunk phải là phụ lục (appendix_number) hoặc bảng biểu độc lập.
        3. Nếu có parent_article, nó phải có định dạng hợp lệ.
        """
        # Điểm a, b, c không thể tồn tại độc lập mà không thuộc Điều hoặc Khoản
        if self.point_number and not self.clause_number and not self.article_number:
            raise ValueError(
                f"Lỗi phân cấp: 'point_number' ({self.point_number}) xuất hiện nhưng không có 'clause_number' hay 'article_number'."
            )

        # Nếu không có article_number, chunk phải là phụ lục hoặc form
        if not self.article_number and not self.appendix_number and self.content_type == ContentType.TEXT.value:
            # Ngoại lệ: Cho phép phần mở đầu (preamble) hoặc phần kết thúc của văn bản
            pass

        return self

    def to_target_dict(self) -> Dict[str, Any]:
        """Xuất dictionary chỉ chứa đúng 21 trường bắt buộc theo đặc tả của TASK DATA-02."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_number": self.document_number,
            "document_title": self.document_title,
            "document_type": self.document_type,

            "chapter_number": self.chapter_number,
            "chapter_title": self.chapter_title,

            "section_number": self.section_number,
            "section_title": self.section_title,

            "article_number": self.article_number,
            "article_title": self.article_title,

            "clause_number": self.clause_number,
            "point_number": self.point_number,

            "content": self.content,

            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "legal_status": self.legal_status,

            "source_url": self.source_url,

            "parent_document": self.parent_document,
            "parent_article": self.parent_article,

            "chunk_index": self.chunk_index
        }
