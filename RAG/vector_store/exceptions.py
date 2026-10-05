"""exceptions.py - Các ngoại lệ chuẩn cho hệ thống Vector Store.

Cung cấp các lớp ngoại lệ phục vụ nguyên tắc FAIL FAST và kiểm tra tính tương thích
của vector database.
"""

from __future__ import annotations


class VectorStoreError(Exception):
    """Ngoại lệ cơ sở cho toàn bộ các lỗi liên quan đến Vector Store."""
    pass


class DimensionMismatchError(VectorStoreError, ValueError):
    """Ngoại lệ kích thước vector không khớp với kích thước của collection (FAIL FAST).
    
    Được kích hoạt khi:
    - Nạp vector có số chiều khác với embedding_dimension của collection.
    - Tải collection có embedding_dimension khác với cấu hình mong đợi.
    """
    pass


class CompatibilityError(VectorStoreError, ValueError):
    """Ngoại lệ dữ liệu hoặc mô hình không tương thích với collection.
    
    Được kích hoạt khi:
    - embedding_model của collection khác với model hiện tại.
    - dataset_version của collection không tương thích với dataset nạp vào.
    """
    pass


class CollectionNotFoundError(VectorStoreError, KeyError):
    """Ngoại lệ khi không tìm thấy collection trong Vector Store."""
    pass


class CollectionAlreadyExistsError(VectorStoreError, ValueError):
    """Ngoại lệ khi collection đã tồn tại nhưng không được phép ghi đè."""
    pass


class DuplicateIDError(VectorStoreError, ValueError):
    """Ngoại lệ khi phát hiện trùng lặp ID trong cùng một lượt nạp dữ liệu."""
    pass
