"""test_temporal_filter.py - Unit tests cho cơ chế lọc theo thời điểm và tình trạng hiệu lực (Temporal Legal Filtering).

Kiểm thử:
1. parse_legal_date: các định dạng ngày tháng hợp lệ, không hợp lệ, null, text bẩn.
2. extract_temporal_intent: phát hiện các mẫu câu tự nhiên tiếng Việt (năm 2022, tháng 7/2024, ngày cụ thể, hiện nay).
3. is_chunk_valid_at_date: kiểm tra điều kiện logic hiệu lực (chưa có hiệu lực, đã hết hiệu lực, còn hiệu lực).
4. filter_chunks: kiểm thử tình huống thực tế đối chiếu Luật BHXH 2014 vs Luật BHXH 2024 tại 2 mốc thời gian (2023 vs 2026).
"""

from __future__ import annotations
import unittest
from datetime import date

from RAG.retriever.schema import RetrievedChunk
from RAG.retriever.temporal_filter import (
    parse_legal_date,
    TemporalLegalFilter,
)


class TestTemporalLegalFilter(unittest.TestCase):
    """Bộ kiểm thử cho phân hệ Temporal Legal Filtering."""

    def setUp(self):
        self.filter = TemporalLegalFilter()

    # =========================================================================
    # 1. Test parse_legal_date
    # =========================================================================
    def test_parse_legal_date_valid(self):
        """Kiểm tra parse các chuỗi ngày tháng chuẩn xác."""
        self.assertEqual(parse_legal_date("01/01/2021"), date(2021, 1, 1))
        self.assertEqual(parse_legal_date("1/7/2025"), date(2025, 7, 1))
        self.assertEqual(parse_legal_date("2021-01-01"), date(2021, 1, 1))
        self.assertEqual(parse_legal_date("20/11/2019"), date(2019, 11, 20))
        self.assertEqual(parse_legal_date("20-11-2019"), date(2019, 11, 20))

    def test_parse_legal_date_invalid_and_empty(self):
        """Kiểm tra xử lý chuỗi rác, rỗng hoặc giá trị không xác định."""
        self.assertIsNone(parse_legal_date(None))
        self.assertIsNone(parse_legal_date(""))
        self.assertIsNone(parse_legal_date("   "))
        self.assertIsNone(parse_legal_date("unknown"))
        self.assertIsNone(parse_legal_date("null"))
        self.assertIsNone(parse_legal_date("Đã biết"))
        self.assertIsNone(parse_legal_date("32/01/2021"))
        self.assertIsNone(parse_legal_date("Không xác định"))

    # =========================================================================
    # 2. Test extract_temporal_intent
    # =========================================================================
    def test_extract_temporal_intent_present(self):
        """Kiểm tra phát hiện từ khóa hiện tại."""
        queries = [
            "Quy định về thử việc hiện nay như thế nào?",
            "Mức lương tối thiểu hiện tại của người lao động",
            "Luật lao động mới nhất quy định ra sao?",
            "Thời điểm này người lao động được nghỉ bao nhiêu ngày phép?",
        ]
        today = date.today()
        for q in queries:
            target_date, kw = TemporalLegalFilter.extract_temporal_intent(q)
            self.assertEqual(target_date, today, f"Failed on query: {q}")
            self.assertIsNotNone(kw)

    def test_extract_temporal_intent_specific_year(self):
        """Kiểm tra phát hiện năm cụ thể."""
        target_date, kw = TemporalLegalFilter.extract_temporal_intent(
            "Vào năm 2022 tôi nghỉ việc thì nhận trợ cấp thế nào?"
        )
        self.assertEqual(target_date, date(2022, 12, 31))
        self.assertIn("2022", kw)

        target_date2, kw2 = TemporalLegalFilter.extract_temporal_intent(
            "Chế độ bảo hiểm năm 2026 áp dụng luật nào?"
        )
        self.assertEqual(target_date2, date(2026, 12, 31))
        self.assertIn("2026", kw2)

    def test_extract_temporal_intent_month_and_day(self):
        """Kiểm tra phát hiện tháng và ngày cụ thể."""
        target_date, kw = TemporalLegalFilter.extract_temporal_intent(
            "Hợp đồng ký vào tháng 7 năm 2024 có hiệu lực không?"
        )
        self.assertEqual(target_date, date(2024, 7, 1))

        target_date_day, _ = TemporalLegalFilter.extract_temporal_intent(
            "Sự việc xảy ra ngày 15 tháng 08 năm 2023 thì xử lý sao?"
        )
        self.assertEqual(target_date_day, date(2023, 8, 15))

        target_date_slash, _ = TemporalLegalFilter.extract_temporal_intent(
            "Áp dụng từ ngày 01/07/2025 đúng không?"
        )
        self.assertEqual(target_date_slash, date(2025, 7, 1))

    def test_extract_temporal_intent_none(self):
        """Kiểm tra trường hợp câu hỏi không có yếu tố thời gian."""
        target_date, kw = TemporalLegalFilter.extract_temporal_intent(
            "Người lao động có quyền đơn phương chấm dứt hợp đồng không?"
        )
        self.assertIsNone(target_date)
        self.assertIsNone(kw)

    # =========================================================================
    # 3. Test is_chunk_valid_at_date
    # =========================================================================
    def test_is_chunk_valid_at_date(self):
        """Kiểm tra logic so khớp ngày hiệu lực."""
        chunk_bhxh_2014 = {
            "effective_from": "01/01/2016",
            "effective_to": "30/06/2025",
            "legal_status": "Còn hiệu lực",
        }
        chunk_bhxh_2024 = {
            "effective_from": "01/07/2025",
            "effective_to": None,
            "legal_status": "Chưa có hiệu lực",
        }

        # Tại mốc năm 2023: Luật 2014 có hiệu lực, Luật 2024 chưa có hiệu lực
        d_2023 = date(2023, 6, 1)
        self.assertTrue(TemporalLegalFilter.is_chunk_valid_at_date(chunk_bhxh_2014, d_2023))
        self.assertFalse(TemporalLegalFilter.is_chunk_valid_at_date(chunk_bhxh_2024, d_2023))

        # Tại mốc năm 2026: Luật 2014 đã hết hiệu lực, Luật 2024 đang có hiệu lực
        d_2026 = date(2026, 1, 1)
        self.assertFalse(TemporalLegalFilter.is_chunk_valid_at_date(chunk_bhxh_2014, d_2026))
        self.assertTrue(TemporalLegalFilter.is_chunk_valid_at_date(chunk_bhxh_2024, d_2026))

    # =========================================================================
    # 4. Test filter_chunks
    # =========================================================================
    def test_filter_chunks_reindexing_and_exclusion(self):
        """Kiểm tra quy trình lọc danh sách chunk và cập nhật lại thứ hạng (rank)."""
        chunk1 = RetrievedChunk(
            chunk_id="BHXH_2014_D31",
            content="Điều kiện hưởng chế độ thai sản theo Luật BHXH 2014",
            score=0.92,
            distance=0.08,
            rank=1,
            metadata={
                "doc_id": "LUAT_BHXH_2014",
                "effective_from": "01/01/2016",
                "effective_to": "30/06/2025",
                "legal_status": "Còn hiệu lực",
            },
        )
        chunk2 = RetrievedChunk(
            chunk_id="BHXH_2024_D50",
            content="Điều kiện hưởng chế độ thai sản theo Luật BHXH 2024",
            score=0.88,
            distance=0.12,
            rank=2,
            metadata={
                "doc_id": "LUAT_BHXH_2024",
                "effective_from": "01/07/2025",
                "effective_to": None,
                "legal_status": "Chưa có hiệu lực",
            },
        )

        results_2023 = self.filter.filter_chunks([chunk1, chunk2], as_of_date=date(2023, 5, 1))
        self.assertEqual(len(results_2023), 1)
        self.assertEqual(results_2023[0].chunk_id, "BHXH_2014_D31")
        self.assertEqual(results_2023[0].rank, 1)

        results_2026 = self.filter.filter_chunks([chunk1, chunk2], as_of_date=date(2026, 1, 1))
        self.assertEqual(len(results_2026), 1)
        self.assertEqual(results_2026[0].chunk_id, "BHXH_2024_D50")
        self.assertEqual(results_2026[0].rank, 1)


if __name__ == "__main__":
    unittest.main()

