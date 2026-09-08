"""schema_v2.py - Schema Specification and Validation Helpers for Legal Dataset V2.

Cung cấp giao diện xác thực, JSON schema chuẩn và các tiện ích chuyển đổi
cho Legal Dataset V2.
"""

from __future__ import annotations
import json
from typing import Dict, Any, List, Tuple, Optional
from pydantic import ValidationError

from Data_Processing.models_v2 import (
    LegalChunkV2,
    DocumentType,
    LegalStatus,
    ContentType,
    sanitize_null
)

# JSON Schema chuẩn xuất tự động từ Pydantic V2 model
LEGAL_CHUNK_V2_JSON_SCHEMA: Dict[str, Any] = LegalChunkV2.model_json_schema()


def validate_chunk(data: Dict[str, Any]) -> LegalChunkV2:
    """Xác thực một bản ghi chunk đơn lẻ theo Schema V2.
    
    Args:
        data: Dictionary chứa các trường của chunk.
        
    Returns:
        LegalChunkV2: Đối tượng chunk đã được xác thực và chuẩn hóa.
        
    Raises:
        ValidationError: Nếu dữ liệu không hợp lệ hoặc thiếu trường bắt buộc.
    """
    return LegalChunkV2.model_validate(data)


def validate_dataset(
    chunks: List[Dict[str, Any]],
    check_unique_ids: bool = True
) -> Tuple[List[LegalChunkV2], List[Dict[str, Any]]]:
    """Xác thực toàn bộ danh sách chunks trong dataset V2.
    
    Kiểm tra tính hợp lệ của từng bản ghi và tính duy nhất toàn cục của chunk_id.
    
    Args:
        chunks: Danh sách các dictionary biểu diễn chunk.
        check_unique_ids: Nếu True, kiểm tra trùng lặp chunk_id.
        
    Returns:
        Tuple (valid_chunks, errors):
        - valid_chunks: Danh sách các LegalChunkV2 hợp lệ.
        - errors: Danh sách các lỗi phát hiện kèm chỉ mục và nguyên nhân.
    """
    valid_chunks: List[LegalChunkV2] = []
    errors: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()

    for idx, chunk_data in enumerate(chunks):
        try:
            chunk_obj = LegalChunkV2.model_validate(chunk_data)

            if check_unique_ids:
                if chunk_obj.chunk_id in seen_ids:
                    errors.append({
                        "index": idx,
                        "chunk_id": chunk_obj.chunk_id,
                        "error_type": "DUPLICATE_CHUNK_ID",
                        "message": f"Trùng lặp chunk_id '{chunk_obj.chunk_id}' đã tồn tại trước đó."
                    })
                    continue
                seen_ids.add(chunk_obj.chunk_id)

            valid_chunks.append(chunk_obj)

        except ValidationError as e:
            errors.append({
                "index": idx,
                "chunk_id": chunk_data.get("chunk_id", f"unknown_at_index_{idx}"),
                "error_type": "VALIDATION_ERROR",
                "details": e.errors(include_url=False)
            })
        except Exception as e:
            errors.append({
                "index": idx,
                "chunk_id": chunk_data.get("chunk_id", f"unknown_at_index_{idx}"),
                "error_type": "UNEXPECTED_ERROR",
                "message": str(e)
            })

    return valid_chunks, errors


def create_chunk_v2(
    chunk_id: str,
    document_id: str,
    document_title: str,
    content: str,
    parent_document: str,
    chunk_index: int,
    document_number: Optional[str] = None,
    document_type: Optional[str] = None,
    chapter_number: Optional[str] = None,
    chapter_title: Optional[str] = None,
    section_number: Optional[str] = None,
    section_title: Optional[str] = None,
    article_number: Optional[str] = None,
    article_title: Optional[str] = None,
    clause_number: Optional[str] = None,
    point_number: Optional[str] = None,
    effective_from: Optional[str] = None,
    effective_to: Optional[str] = None,
    legal_status: Optional[str] = None,
    source_url: Optional[str] = None,
    parent_article: Optional[str] = None,
    content_type: str = "text",
    **extra: Any
) -> LegalChunkV2:
    """Hàm khởi tạo nhanh (Factory function) cho LegalChunkV2 với các giá trị mặc định chuẩn."""
    return LegalChunkV2(
        chunk_id=chunk_id,
        document_id=document_id,
        document_number=document_number,
        document_title=document_title,
        document_type=document_type,
        chapter_number=chapter_number,
        chapter_title=chapter_title,
        section_number=section_number,
        section_title=section_title,
        article_number=article_number,
        article_title=article_title,
        clause_number=clause_number,
        point_number=point_number,
        content=content,
        effective_from=effective_from,
        effective_to=effective_to,
        legal_status=legal_status,
        source_url=source_url,
        parent_document=parent_document,
        parent_article=parent_article,
        chunk_index=chunk_index,
        content_type=content_type,
        **extra
    )


def export_dataset_v2(
    chunks: List[LegalChunkV2],
    filepath: str,
    indent: int = 2,
    target_format_only: bool = True
) -> None:
    """Xuất danh sách LegalChunkV2 ra tệp JSON chuẩn với xử lý null chính xác.
    
    Args:
        chunks: Danh sách các LegalChunkV2.
        filepath: Đường dẫn tệp đích.
        indent: Khoảng thụt dòng (mặc định 2).
        target_format_only: Nếu True, xuất đúng 21 trường cốt lõi theo đặc tả DATA-02.
    """
    if target_format_only:
        data = [c.to_target_dict() for c in chunks]
    else:
        data = [c.model_dump() for c in chunks]

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
