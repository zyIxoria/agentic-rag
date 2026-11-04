"""test_legal_calculator.py - Unit test cho công cụ tính toán số học biểu tượng (Symbolic Legal Calculator).

Kiểm thử toàn diện 4 nhóm nghiệp vụ định lượng:
1. Tiền lương làm thêm giờ ban ngày, ban đêm, ngày thường, ngày nghỉ tuần, ngày lễ tết.
2. Trợ cấp thôi việc (Điều 46) và trợ cấp mất việc làm (Điều 47).
3. Bồi thường và trợ cấp tai nạn lao động (Điều 38 Luật ATVSLĐ 2015).
4. Trợ cấp thất nghiệp (Điều 50 Luật Việc làm 2013).
"""

from __future__ import annotations
import unittest

from Adaptive_RAG.tools.legal_calculator import (
    SymbolicLegalCalculator,
    LegalCalculationResult,
)


class TestSymbolicLegalCalculator(unittest.TestCase):
    """Bộ kiểm thử cho SymbolicLegalCalculator."""

    # =========================================================================
    # 1. KIỂM THỬ TIỀN LƯƠNG LÀM THÊM GIỜ (Điều 98 BLLĐ 2019)
    # =========================================================================
    def test_overtime_normal_day_daytime(self):
        """Làm thêm giờ ngày thường ban ngày: tỷ lệ 150%."""
        res = SymbolicLegalCalculator.calculate_overtime_pay(
            hourly_wage=50_000,
            hours=4,
            day_type="normal",
            is_night=False,
            is_overtime=True,
        )
        self.assertEqual(res.rate_percentage, 150.0)
        # 50,000 * 1.5 * 4 = 300,000
        self.assertEqual(res.total_amount_vnd, 300_000)

    def test_overtime_weekend_daytime(self):
        """Làm thêm giờ ngày nghỉ hàng tuần ban ngày: tỷ lệ 200%."""
        res = SymbolicLegalCalculator.calculate_overtime_pay(
            hourly_wage=50_000,
            hours=8,
            day_type="weekend",
            is_night=False,
            is_overtime=True,
        )
        self.assertEqual(res.rate_percentage, 200.0)
        # 50,000 * 2.0 * 8 = 800,000
        self.assertEqual(res.total_amount_vnd, 800_000)

    def test_overtime_holiday_daytime(self):
        """Làm thêm giờ ngày lễ tết ban ngày: tỷ lệ 300%."""
        res = SymbolicLegalCalculator.calculate_overtime_pay(
            hourly_wage=50_000,
            hours=8,
            day_type="holiday",
            is_night=False,
            is_overtime=True,
        )
        self.assertEqual(res.rate_percentage, 300.0)
        # 50,000 * 3.0 * 8 = 1,200,000
        self.assertEqual(res.total_amount_vnd, 1_200_000)

    def test_normal_work_at_night(self):
        """Làm việc ca đêm bình thường (không làm thêm giờ): tỷ lệ 130%."""
        res = SymbolicLegalCalculator.calculate_overtime_pay(
            hourly_wage=50_000,
            hours=8,
            day_type="normal",
            is_night=True,
            is_overtime=False,
        )
        self.assertEqual(res.rate_percentage, 130.0)
        # 50,000 * 1.3 * 8 = 520,000
        self.assertEqual(res.total_amount_vnd, 520_000)

    def test_overtime_normal_day_at_night(self):
        """Làm thêm giờ vào ban đêm ngày thường: 150% + 30% + 20%*150% = 210%."""
        res = SymbolicLegalCalculator.calculate_overtime_pay(
            hourly_wage=50_000,
            hours=3,
            day_type="normal",
            is_night=True,
            is_overtime=True,
        )
        self.assertEqual(res.rate_percentage, 210.0)
        # 50,000 * 2.1 * 3 = 315,000
        self.assertEqual(res.total_amount_vnd, 315_000)

    def test_overtime_weekend_at_night(self):
        """Làm thêm giờ vào ban đêm ngày nghỉ tuần: 200% + 30% + 20%*200% = 270%."""
        res = SymbolicLegalCalculator.calculate_overtime_pay(
            hourly_wage=50_000,
            hours=4,
            day_type="weekend",
            is_night=True,
            is_overtime=True,
        )
        self.assertEqual(res.rate_percentage, 270.0)
        # 50,000 * 2.7 * 4 = 540,000
        self.assertEqual(res.total_amount_vnd, 540_000)

    def test_overtime_holiday_at_night(self):
        """Làm thêm giờ vào ban đêm ngày lễ tết: 300% + 30% + 20%*300% = 390%."""
        res = SymbolicLegalCalculator.calculate_overtime_pay(
            hourly_wage=100_000,
            hours=5,
            day_type="holiday",
            is_night=True,
            is_overtime=True,
        )
        self.assertEqual(res.rate_percentage, 390.0)
        # 100,000 * 3.9 * 5 = 1,950,000
        self.assertEqual(res.total_amount_vnd, 1_950_000)

    # =========================================================================
    # 2. KIỂM THỬ TRỢ CẤP THÔI VIỆC & MẤT VIỆC LÀM (Điều 46, 47 BLLĐ 2019)
    # =========================================================================
    def test_severance_allowance_exact_years(self):
        """Trợ cấp thôi việc 3 năm làm việc không tham gia BHTN: 3 * 0.5 = 1.5 tháng lương."""
        res = SymbolicLegalCalculator.calculate_severance_or_redundancy(
            avg_monthly_salary_6m=10_000_000,
            total_months_worked=36,
            months_bhtn_participated=0,
            allowance_type="thoi_viec",
        )
        self.assertEqual(res.total_months_salary, 1.5)
        self.assertEqual(res.total_amount_vnd, 15_000_000)

    def test_severance_allowance_rounding_half_year(self):
        """Thời gian dư 4 tháng lẻ (1-6 tháng): làm tròn thành 1/2 năm."""
        # 24 tháng làm việc, tham gia BHTN 8 tháng -> còn lại 16 tháng = 1 năm 4 tháng -> làm tròn 1.5 năm -> 0.75 tháng lương
        res = SymbolicLegalCalculator.calculate_severance_or_redundancy(
            avg_monthly_salary_6m=12_000_000,
            total_months_worked=24,
            months_bhtn_participated=8,
            allowance_type="thoi_viec",
        )
        self.assertEqual(res.total_months_salary, 0.75)
        # 12,000,000 * 0.75 = 9,000,000
        self.assertEqual(res.total_amount_vnd, 9_000_000)

    def test_redundancy_allowance_minimum_guarantee(self):
        """Trợ cấp mất việc làm: 1 năm làm việc tính ra 1 tháng nhưng phải áp trần tối thiểu 2 tháng lương."""
        res = SymbolicLegalCalculator.calculate_severance_or_redundancy(
            avg_monthly_salary_6m=10_000_000,
            total_months_worked=12,
            months_bhtn_participated=0,
            allowance_type="mat_viec",
        )
        self.assertEqual(res.total_months_salary, 2.0)
        self.assertEqual(res.total_amount_vnd, 20_000_000)

    # =========================================================================
    # 3. KIỂM THỬ BỒI THƯỜNG TAI NẠN LAO ĐỘNG (Điều 38 Luật ATVSLĐ 2015)
    # =========================================================================
    def test_accident_compensation_5_to_10_percent(self):
        """Suy giảm 8% KNLĐ: ít nhất 1.5 tháng tiền lương."""
        res = SymbolicLegalCalculator.calculate_work_accident_benefit(
            monthly_salary=8_000_000,
            impairment_percentage=8.0,
            is_worker_fault=False,
        )
        self.assertEqual(res.total_months_salary, 1.5)
        self.assertEqual(res.total_amount_vnd, 12_000_000)

    def test_accident_compensation_14_percent(self):
        """Suy giảm 14% KNLĐ: 1.5 + (14 - 10) * 0.4 = 1.5 + 1.6 = 3.1 tháng tiền lương."""
        res = SymbolicLegalCalculator.calculate_work_accident_benefit(
            monthly_salary=10_000_000,
            impairment_percentage=14.0,
            is_worker_fault=False,
        )
        self.assertEqual(res.total_months_salary, 3.1)
        self.assertEqual(res.total_amount_vnd, 31_000_000)

    def test_accident_compensation_81_percent_or_above(self):
        """Suy giảm 81% KNLĐ: ít nhất 30 tháng tiền lương."""
        res = SymbolicLegalCalculator.calculate_work_accident_benefit(
            monthly_salary=10_000_000,
            impairment_percentage=81.0,
            is_worker_fault=False,
        )
        self.assertEqual(res.total_months_salary, 30.0)
        self.assertEqual(res.total_amount_vnd, 300_000_000)

    def test_accident_allowance_worker_fault(self):
        """Tai nạn do lỗi của chính người lao động: trợ cấp ít nhất 40% mức bồi thường."""
        # 14% suy giảm KNLĐ -> mức bồi thường 3.1 tháng -> do lỗi NLĐ: 3.1 * 40% = 1.24 tháng lương
        res = SymbolicLegalCalculator.calculate_work_accident_benefit(
            monthly_salary=10_000_000,
            impairment_percentage=14.0,
            is_worker_fault=True,
        )
        self.assertEqual(res.total_months_salary, 1.24)
        self.assertEqual(res.total_amount_vnd, 12_400_000)

    # =========================================================================
    # 4. KIỂM THỬ TRỢ CẤP THẤT NGHIỆP (Điều 50 Luật Việc làm 2013)
    # =========================================================================
    def test_unemployment_benefit_24_months(self):
        """Đóng BHTN 24 tháng: hưởng 3 tháng trợ cấp, mức 60% lương bình quân."""
        res = SymbolicLegalCalculator.calculate_unemployment_benefit(
            avg_monthly_salary_6m_bhtn=10_000_000,
            months_bhtn_contributed=24,
        )
        self.assertEqual(res.total_months_salary, 3.0)
        # 6,000,000/tháng x 3 tháng = 18,000,000
        self.assertEqual(res.total_amount_vnd, 18_000_000)


if __name__ == "__main__":
    unittest.main()

