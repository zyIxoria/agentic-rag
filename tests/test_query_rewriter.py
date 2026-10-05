"""test_query_rewriter.py - Bộ kiểm thử đơn vị cho Query Rewriter (TASK CRAG-02 & CRAG-05).

Kiểm thử 7 trường hợp bắt buộc:
1. Query rõ ràng -> bảo toàn nội dung cốt lõi
2. Query mơ hồ -> làm rõ thành thuật ngữ pháp lý
3. Query thiếu chủ thể -> bổ sung chủ thể pháp lý phù hợp
4. Query thiếu điều kiện -> làm rõ điều kiện hưởng/áp dụng
5. Query cần làm rõ thời gian -> bổ sung khung thời gian
6. Query đã đủ thông tin -> không rewrite quá mức
7. Tuyệt đối không hallucinate số điều hoặc tên nghị định
"""

import re
import pytest

from RAG.corrective.rewriter import QueryRewriter
from RAG.corrective.schemas import RetrievalEvaluation, EvaluationStatus


class TestQueryRewriter:
    """Tập kiểm thử đơn vị cho Query Rewriter theo đặc tả kỹ thuật CRAG."""

    @pytest.fixture
    def rewriter(self) -> QueryRewriter:
        return QueryRewriter()

    def test_01_clear_query_preserves_intent(self, rewriter: QueryRewriter):
        """TEST 1: Query rõ ràng -> bảo toàn trọn vẹn ý định tìm kiếm."""
        original = "Quy định về thời giờ làm việc bình thường của người lao động tối đa trong một ngày và một tuần?"
        rewritten = rewriter.rewrite_query(original)

        assert "thời giờ làm việc bình thường" in rewritten.lower()
        assert "người lao động" in rewritten.lower()
        assert "ngày" in rewritten.lower()
        assert "tuần" in rewritten.lower()

    def test_02_ambiguous_conversational_query_clarified(self, rewriter: QueryRewriter):
        """TEST 2: Query mơ hồ, mang tính chat đàm thoại -> làm rõ thành thuật ngữ chuẩn."""
        original = "Cho em hỏi ad ơi, người lao động bị đuổi việc thì cần lý do gì ạ?"
        rewritten = rewriter.rewrite_query(original)

        # Đã loại bỏ các từ đệm hội thoại
        assert "cho em hỏi" not in rewritten.lower()
        assert "ad ơi" not in rewritten.lower()
        assert "ạ" not in rewritten.lower().split()
        # Chuyển đuổi việc -> kỷ luật sa thải
        assert "sa thải" in rewritten.lower()

    def test_03_missing_subject_made_explicit(self, rewriter: QueryRewriter):
        """TEST 3: Query thiếu chủ thể -> bổ sung chủ thể rõ ràng (người lao động)."""
        original = "Thời gian nghỉ thai sản tối đa là mấy tháng?"
        rewritten = rewriter.rewrite_query(original)

        # Phải bổ sung chủ thể người lao động
        assert "người lao động" in rewritten.lower()
        assert "nghỉ thai sản" in rewritten.lower()

    def test_04_missing_condition_clarified(self, rewriter: QueryRewriter):
        """TEST 4: Query thiếu điều kiện (nghỉ khi cưới) -> làm rõ điều kiện (nghỉ việc riêng hưởng nguyên lương khi kết hôn)."""
        original = "Người lao động được nghỉ bao nhiêu ngày khi kết hôn?"
        rewritten = rewriter.rewrite_query(original)

        assert "người lao động" in rewritten.lower()
        assert "nghỉ việc riêng" in rewritten.lower()
        assert "kết hôn" in rewritten.lower()
        assert "hưởng nguyên lương" in rewritten.lower()

    def test_05_timeframe_clarified(self, rewriter: QueryRewriter):
        """TEST 5: Query cần làm rõ thời gian (làm thêm giờ) -> làm rõ khung thời gian."""
        original = "Số giờ làm thêm tối đa của người lao động?"
        rewritten = rewriter.rewrite_query(original)

        assert "làm thêm giờ" in rewritten.lower()
        assert any(t in rewritten.lower() for t in ["ngày", "tháng", "năm"])

    def test_06_already_sufficient_query_not_overwritten(self, rewriter: QueryRewriter):
        """TEST 6: Query đã đủ thông tin pháp lý -> không rewrite quá mức."""
        original = "Quy định về mức lương tối thiểu vùng áp dụng đối với người lao động làm việc theo hợp đồng lao động."
        rewritten = rewriter.rewrite_query(original)

        # Độ dài không bị phình to bất thường
        assert abs(len(rewritten) - len(original)) < 30
        assert "lương tối thiểu" in rewritten.lower()
        assert "người lao động" in rewritten.lower()

    def test_07_no_hallucination_of_article_or_decree_number(self, rewriter: QueryRewriter):
        """TEST 7: Tuyệt đối không được hallucinate số Điều, tên Nghị định, Thông tư nếu câu gốc không có."""
        queries = [
            "Người lao động được nghỉ bao nhiêu ngày khi kết hôn?",
            "Quy định về thời giờ làm việc bình thường?",
            "Thời hạn báo trước khi đơn phương chấm dứt hợp đồng lao động?",
            "Mức bồi thường tai nạn lao động cho người lao động?",
            "Tiêu chuẩn lao động chưa thành niên?"
        ]

        for q in queries:
            rewritten = rewriter.rewrite_query(q)
            # Kiểm tra không có mẫu "Điều <số>"
            assert not re.search(r"(?i)\bĐiều\s+\d+\b", rewritten), f"Phát hiện hallucinate số Điều trong: {rewritten}"
            # Kiểm tra không có mẫu "Nghị định <số>"
            assert not re.search(r"(?i)\bNghị\s+định\s+\d+\b", rewritten), f"Phát hiện hallucinate số Nghị định trong: {rewritten}"
            # Kiểm tra không có mẫu "Thông tư <số>"
            assert not re.search(r"(?i)\bThông\s+tư\s+\d+\b", rewritten), f"Phát hiện hallucinate số Thông tư trong: {rewritten}"
