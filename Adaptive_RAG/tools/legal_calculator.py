"""legal_calculator.py - Công cụ tính toán số học biểu tượng (Symbolic Legal Calculator).

Khắc phục triệt để điểm yếu chí mạng ở các câu hỏi định lượng (Category E):
1. Tính tiền lương làm thêm giờ (Điều 98 BLLĐ 2019):
   - Ngày thường (>= 150%)
   - Ngày nghỉ hàng tuần (>= 200%)
   - Ngày lễ, tết, ngày nghỉ có hưởng lương (>= 300%)
   - Làm việc vào ban đêm (+30%)
   - Làm thêm giờ ban đêm: ngày thường (210%), ngày nghỉ tuần (270%), lễ tết (390%)
2. Tính trợ cấp thôi việc (Điều 46 BLLĐ 2019):
   - 0.5 tháng lương / năm làm việc (đã trừ thời gian tham gia BHTN)
   - Quy tắc làm tròn thâm niên: 1-6 tháng = 0.5 năm; >6 tháng = 1.0 năm
3. Tính trợ cấp mất việc làm (Điều 47 BLLĐ 2019):
   - 1.0 tháng lương / năm làm việc, tối thiểu 2.0 tháng lương
4. Tính bồi thường & trợ cấp tai nạn lao động (Điều 38 Luật ATVSLĐ 2015):
   - 5% - 10%: 1.5 tháng lương
   - 11% - 80%: 1.5 + (Tỷ lệ - 10) * 0.4 tháng lương
   - >= 81% hoặc tử vong: ít nhất 30 tháng lương
   - Trợ cấp do lỗi người lao động: ít nhất 40% mức bồi thường
5. Tính trợ cấp thất nghiệp (Điều 50 Luật Việc làm 2013):
   - 60% mức lương bình quân 6 tháng đóng BHTN, thời gian hưởng từ 3 - 12 tháng
"""

from __future__ import annotations
import math
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field


class CalculationStep(BaseModel):
    """Mô tả từng bước tính toán có căn cứ pháp lý."""
    step_number: int
    description: str
    formula: str
    result_value: float


class LegalCalculationResult(BaseModel):
    """Kết quả tính toán pháp lý hoàn chỉnh."""
    calculation_type: str
    legal_basis: str
    summary: str
    total_amount_vnd: float
    total_months_salary: Optional[float] = None
    rate_percentage: Optional[float] = None
    steps: List[CalculationStep] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

    def to_formatted_text(self) -> str:
        """Định dạng kết quả tính toán thành văn bản giải trình chi tiết cho người dùng."""
        lines = [
            f"### KẾT QUẢ TÍNH TOÁN PHÁP LÝ: {self.calculation_type.upper()}",
            f"**Căn cứ pháp lý:** {self.legal_basis}",
            f"**Kết luận định lượng:** **{self.total_amount_vnd:,.0f} VNĐ**" + (
                f" ({self.total_months_salary:.2f} tháng lương)" if self.total_months_salary is not None else ""
            ) + (
                f" (Tỷ lệ áp dụng: {self.rate_percentage}%)" if self.rate_percentage is not None else ""
            ),
            "\n**Các bước diễn giải chi tiết:**"
        ]
        for s in self.steps:
            lines.append(f"{s.step_number}. {s.description}: `{s.formula}` = **{s.result_value:,.2f}**")

        if self.notes:
            lines.append("\n**Lưu ý pháp lý:**")
            for n in self.notes:
                lines.append(f"- {n}")

        return "\n".join(lines)


class SymbolicLegalCalculator:
    """Bộ công cụ tính toán số học biểu tượng theo quy chuẩn pháp luật lao động Việt Nam."""

    # -------------------------------------------------------------------------
    # 1. TÍNH TIỀN LƯƠNG LÀM THÊM GIỜ (Điều 98 BLLĐ 2019)
    # -------------------------------------------------------------------------
    @staticmethod
    def calculate_overtime_pay(
        hourly_wage: float,
        hours: float,
        day_type: Literal["normal", "weekend", "holiday"] = "normal",
        is_night: bool = False,
        is_overtime: bool = True,
        already_paid_normal_day_salary: bool = False,
    ) -> LegalCalculationResult:
        """Tính tiền lương làm thêm giờ theo Điều 98 Bộ luật Lao động 2019.
        
        Args:
            hourly_wage: Tiền lương giờ thực trả của ngày làm việc bình thường (VNĐ/giờ).
            hours: Số giờ làm việc thực tế.
            day_type: Loại ngày ('normal': ngày thường, 'weekend': ngày nghỉ hàng tuần, 'holiday': ngày lễ/tết/nghỉ có hưởng lương).
            is_night: Có làm việc vào ban đêm (từ 22h đêm đến 06h sáng hôm sau) hay không.
            is_overtime: Là làm thêm giờ (True) hay làm theo ca đêm bình thường (False).
            already_paid_normal_day_salary: Đối với ngày lễ tết, người lao động hưởng lương ngày đã được trả lương ngày lễ hay chưa.
        """
        if hourly_wage <= 0 or hours <= 0:
            raise ValueError("Tiền lương giờ và số giờ làm việc phải là số dương lớn hơn 0.")

        steps: List[CalculationStep] = []
        step_idx = 1
        legal_basis = "Điều 98 Bộ luật Lao động 2019"

        # Tỷ lệ làm thêm giờ ban ngày theo điểm a, b, c khoản 1 Điều 98
        day_rates = {
            "normal": 150.0,
            "weekend": 200.0,
            "holiday": 300.0,
        }
        day_rate = day_rates.get(day_type, 150.0)

        day_names = {
            "normal": "Ngày làm việc bình thường",
            "weekend": "Ngày nghỉ hằng tuần",
            "holiday": "Ngày nghỉ lễ, tết, ngày nghỉ có hưởng lương",
        }

        # Trường hợp 1: Làm việc ban ngày bình thường (không làm đêm)
        if not is_night:
            final_rate = day_rate if is_overtime else 100.0
            steps.append(
                CalculationStep(
                    step_number=step_idx,
                    description=f"Xác định tỷ lệ lương làm thêm giờ ({day_names[day_type]}) theo Khoản 1 Điều 98",
                    formula=f"{final_rate}%",
                    result_value=final_rate,
                )
            )
            step_idx += 1
        else:
            # Trường hợp 2: Có làm việc vào ban đêm (Khoản 2 và Khoản 3 Điều 98)
            # Theo Khoản 2 Điều 98: Phụ cấp làm đêm ít nhất = 30% lương giờ bình thường
            night_allowance_rate = 30.0

            if not is_overtime:
                # Làm ca đêm bình thường (không phải làm thêm giờ): 100% + 30% = 130%
                final_rate = 100.0 + night_allowance_rate
                steps.append(
                    CalculationStep(
                        step_number=step_idx,
                        description="Lương ca đêm theo ngày làm việc bình thường (Khoản 2 Điều 98: 100% + 30%)",
                        formula="100% + 30%",
                        result_value=final_rate,
                    )
                )
                step_idx += 1
            else:
                # Làm thêm giờ vào ban đêm (Khoản 3 Điều 98):
                # Công thức chuẩn: Tỷ lệ làm thêm ngày + 30% (làm đêm) + 20% của đơn giá ban ngày ngày tương ứng
                # - Ngày thường: 150% + 30% + (20% * 150% = 30%) = 210%
                # - Ngày nghỉ tuần: 200% + 30% + (20% * 200% = 40%) = 270%
                # - Ngày lễ tết: 300% + 30% + (20% * 300% = 60%) = 390%
                overtime_night_bonus_rate = 0.20 * day_rate
                final_rate = day_rate + night_allowance_rate + overtime_night_bonus_rate

                steps.append(
                    CalculationStep(
                        step_number=step_idx,
                        description=f"Tỷ lệ làm thêm giờ ban ngày ({day_names[day_type]} - Điểm { 'a' if day_type == 'normal' else ('b' if day_type == 'weekend' else 'c') } Khoản 1 Điều 98)",
                        formula=f"{day_rate}%",
                        result_value=day_rate,
                    )
                )
                step_idx += 1

                steps.append(
                    CalculationStep(
                        step_number=step_idx,
                        description="Tiền lương làm việc vào ban đêm cộng thêm theo Khoản 2 Điều 98",
                        formula="30%",
                        result_value=30.0,
                    )
                )
                step_idx += 1

                steps.append(
                    CalculationStep(
                        step_number=step_idx,
                        description=f"Tiền lương làm thêm giờ vào ban đêm cộng thêm 20% đơn giá ban ngày theo Khoản 3 Điều 98 (20% x {day_rate}%)",
                        formula=f"20% * {day_rate}%",
                        result_value=overtime_night_bonus_rate,
                    )
                )
                step_idx += 1

                steps.append(
                    CalculationStep(
                        step_number=step_idx,
                        description=f"Tổng tỷ lệ lương làm thêm giờ ban đêm ({day_names[day_type]})",
                        formula=f"{day_rate}% + 30% + {overtime_night_bonus_rate}%",
                        result_value=final_rate,
                    )
                )
                step_idx += 1

        total_pay = hourly_wage * (final_rate / 100.0) * hours
        steps.append(
            CalculationStep(
                step_number=step_idx,
                description=f"Tổng tiền lương làm thêm giờ ({hours} giờ x {hourly_wage:,.0f} đ/h x {final_rate}%)",
                formula=f"{hourly_wage:,.0f} * ({final_rate}/100) * {hours}",
                result_value=round(total_pay, 2),
            )
        )

        notes = [
            f"Thời gian ban đêm được tính từ 22 giờ đến 06 giờ sáng hôm sau (Điều 106 BLLĐ 2019).",
            f"Mức lương giờ tính làm thêm: {hourly_wage:,.0f} VNĐ/giờ.",
        ]
        if day_type == "holiday" and not already_paid_normal_day_salary:
            notes.append(
                "Lưu ý: Mức 300% (hoặc 390% nếu làm đêm) chưa bao gồm tiền lương ngày nghỉ lễ, tết có hưởng lương của người lao động hưởng lương ngày."
            )

        return LegalCalculationResult(
            calculation_type="Tiền lương làm thêm giờ / làm ban đêm",
            legal_basis=legal_basis,
            summary=f"Tiền lương làm thêm giờ cho {hours} giờ ({day_names[day_type]}, {'ban đêm' if is_night else 'ban ngày'}) là {total_pay:,.0f} VNĐ (tỷ lệ {final_rate}%).",
            total_amount_vnd=round(total_pay, 0),
            rate_percentage=final_rate,
            steps=steps,
            notes=notes,
        )

    # -------------------------------------------------------------------------
    # 2. TÍNH TRỢ CẤP THÔI VIỆC & MẤT VIỆC LÀM (Điều 46, Điều 47 BLLĐ 2019)
    # -------------------------------------------------------------------------
    @staticmethod
    def calculate_severance_or_redundancy(
        avg_monthly_salary_6m: float,
        total_months_worked: float,
        months_bhtn_participated: float = 0.0,
        months_already_severance_paid: float = 0.0,
        allowance_type: Literal["thoi_viec", "mat_viec"] = "thoi_viec",
    ) -> LegalCalculationResult:
        """Tính trợ cấp thôi việc (Điều 46) hoặc trợ cấp mất việc làm (Điều 47).
        
        Args:
            avg_monthly_salary_6m: Tiền lương bình quân theo HĐLĐ của 06 tháng liền kề trước khi nghỉ việc.
            total_months_worked: Tổng thời gian người lao động đã làm việc thực tế cho NSDLĐ (tính theo tháng).
            months_bhtn_participated: Thời gian người lao động đã tham gia bảo hiểm thất nghiệp (tháng).
            months_already_severance_paid: Thời gian làm việc đã được NSDLĐ chi trả trợ cấp thôi việc/mất việc làm trước đó (tháng).
            allowance_type: 'thoi_viec' (Trợ cấp thôi việc, Điều 46) hoặc 'mat_viec' (Trợ cấp mất việc làm, Điều 47).
        """
        if avg_monthly_salary_6m <= 0:
            raise ValueError("Tiền lương bình quân 6 tháng phải lớn hơn 0.")
        if total_months_worked < 0:
            raise ValueError("Tổng thời gian làm việc không được âm.")

        steps: List[CalculationStep] = []
        step_idx = 1

        is_mat_viec = allowance_type == "mat_viec"
        legal_basis = (
            "Điều 47 Bộ luật Lao động 2019 và Nghị định 145/2020/NĐ-CP"
            if is_mat_viec
            else "Điều 46 Bộ luật Lao động 2019 và Nghị định 145/2020/NĐ-CP"
        )
        type_name = "Trợ cấp mất việc làm" if is_mat_viec else "Trợ cấp thôi việc"

        # Bước 1: Tính thời gian làm việc thực tế để tính trợ cấp (Khoản 2 Điều 46, Khoản 2 Điều 47)
        qualifying_months = max(
            0.0, total_months_worked - months_bhtn_participated - months_already_severance_paid
        )
        steps.append(
            CalculationStep(
                step_number=step_idx,
                description="Tính thời gian làm việc để tính trợ cấp = Tổng thời gian làm việc thực tế - Thời gian tham gia BHTN - Thời gian đã chi trả trợ cấp",
                formula=f"{total_months_worked} - {months_bhtn_participated} - {months_already_severance_paid}",
                result_value=qualifying_months,
            )
        )
        step_idx += 1

        # Bước 2: Quy đổi thời gian sang năm và làm tròn theo Khoản 3 Điều 8 Nghị định 145/2020/NĐ-CP
        full_years = int(qualifying_months // 12)
        remaining_months = qualifying_months % 12

        if remaining_months == 0:
            rounded_years = float(full_years)
            round_desc = f"{full_years} năm tròn"
        elif 1 <= remaining_months <= 6:
            rounded_years = full_years + 0.5
            round_desc = f"{full_years} năm và {remaining_months} tháng lẻ (từ đủ 01 đến 06 tháng làm tròn thành 1/2 năm)"
        else:
            rounded_years = full_years + 1.0
            round_desc = f"{full_years} năm và {remaining_months} tháng lẻ (từ trên 06 tháng đến dưới 12 tháng làm tròn thành 01 năm)"

        steps.append(
            CalculationStep(
                step_number=step_idx,
                description=f"Quy đổi và làm tròn thời gian tính trợ cấp theo Nghị định 145/2020/NĐ-CP ({round_desc})",
                formula=f"Làm tròn({qualifying_months} tháng)",
                result_value=rounded_years,
            )
        )
        step_idx += 1

        # Bước 3: Tính số tháng tiền lương trợ cấp
        # Trợ cấp thôi việc: 1/2 tháng lương / năm
        # Trợ cấp mất việc: 1 tháng lương / năm, tối thiểu 2 tháng lương
        if not is_mat_viec:
            months_allowance = rounded_years * 0.5
            steps.append(
                CalculationStep(
                    step_number=step_idx,
                    description="Tính số tháng trợ cấp thôi việc (Mỗi năm làm việc được trợ cấp 1/2 tháng lương)",
                    formula=f"{rounded_years} năm * 0.5 tháng",
                    result_value=months_allowance,
                )
            )
            step_idx += 1
        else:
            raw_months = rounded_years * 1.0
            months_allowance = max(2.0, raw_months)
            steps.append(
                CalculationStep(
                    step_number=step_idx,
                    description="Tính số tháng trợ cấp mất việc làm (1 tháng/năm, tối thiểu 2 tháng tiền lương theo Khoản 1 Điều 47)",
                    formula=f"max(2.0, {rounded_years} năm * 1.0 tháng)",
                    result_value=months_allowance,
                )
            )
            step_idx += 1

        total_amount = avg_monthly_salary_6m * months_allowance
        steps.append(
            CalculationStep(
                step_number=step_idx,
                description=f"Tính tổng số tiền trợ cấp ({months_allowance:.2f} tháng lương x {avg_monthly_salary_6m:,.0f} đ/tháng)",
                formula=f"{avg_monthly_salary_6m:,.0f} * {months_allowance:.2f}",
                result_value=round(total_amount, 2),
            )
        )

        notes = [
            f"Tiền lương làm căn cứ tính: {avg_monthly_salary_6m:,.0f} VNĐ/tháng (bình quân 06 tháng liền kề trước khi nghỉ việc).",
            f"Thời gian tính trợ cấp sau khi khấu trừ BHTN: {qualifying_months:.1f} tháng $\\to$ làm tròn {rounded_years:.1f} năm.",
        ]
        if is_mat_viec and raw_months < 2.0:
            notes.append("Được áp dụng mức tối thiểu luật định: Ít nhất 02 tháng tiền lương.")

        return LegalCalculationResult(
            calculation_type=type_name,
            legal_basis=legal_basis,
            summary=f"{type_name} của người lao động là {total_amount:,.0f} VNĐ, tương đương {months_allowance:.2f} tháng tiền lương.",
            total_amount_vnd=round(total_amount, 0),
            total_months_salary=months_allowance,
            steps=steps,
            notes=notes,
        )

    # -------------------------------------------------------------------------
    # 3. TÍNH BỒI THƯỜNG / TRỢ CẤP TAI NẠN LAO ĐỘNG (Điều 38 Luật ATVSLĐ 2015)
    # -------------------------------------------------------------------------
    @staticmethod
    def calculate_work_accident_benefit(
        monthly_salary: float,
        impairment_percentage: float,
        is_worker_fault: bool = False,
    ) -> LegalCalculationResult:
        """Tính tiền bồi thường hoặc trợ cấp tai nạn lao động theo Điều 38 Luật ATVSLĐ 2015.
        
        Args:
            monthly_salary: Tiền lương làm căn cứ bồi thường (tiền lương tháng theo HĐLĐ).
            impairment_percentage: Tỷ lệ suy giảm khả năng lao động (%) từ 5% đến 100%.
            is_worker_fault: Nếu tai nạn do lỗi của chính người lao động thì nhận TRỢ CẤP ít nhất = 40% mức bồi thường.
        """
        if monthly_salary <= 0:
            raise ValueError("Tiền lương tháng phải lớn hơn 0.")
        if impairment_percentage < 5.0 or impairment_percentage > 100.0:
            raise ValueError(f"Tỷ lệ suy giảm khả năng lao động phải từ 5% đến 100%, nhận được: {impairment_percentage}%.")

        steps: List[CalculationStep] = []
        step_idx = 1
        legal_basis = "Điều 38 Luật An toàn, vệ sinh lao động 2015 và Thông tư 28/2021/TT-BLĐTBXH"

        # Điểm a và b Khoản 4 Điều 38
        if impairment_percentage >= 81.0:
            base_months = 30.0
            steps.append(
                CalculationStep(
                    step_number=step_idx,
                    description="Suy giảm KNLĐ từ 81% trở lên hoặc chết: Mức bồi thường tối thiểu là 30 tháng tiền lương (Điểm b Khoản 4 Điều 38)",
                    formula="30.0 tháng",
                    result_value=30.0,
                )
            )
            step_idx += 1
        elif 5.0 <= impairment_percentage <= 10.0:
            base_months = 1.5
            steps.append(
                CalculationStep(
                    step_number=step_idx,
                    description=f"Suy giảm KNLĐ từ 5% đến 10% ({impairment_percentage}%): Mức bồi thường tối thiểu là 1.5 tháng tiền lương (Điểm a Khoản 4 Điều 38)",
                    formula="1.5 tháng",
                    result_value=1.5,
                )
            )
            step_idx += 1
        else:
            # 11% <= impairment_percentage <= 80%
            # Công thức: 1.5 tháng lương cho 10% đầu + 0.4 tháng lương cho mỗi 1% tăng thêm
            additional_pct = impairment_percentage - 10.0
            additional_months = additional_pct * 0.4
            base_months = 1.5 + additional_months

            steps.append(
                CalculationStep(
                    step_number=step_idx,
                    description=f"Mức cơ sở cho 10% suy giảm KNLĐ đầu tiên",
                    formula="1.5 tháng",
                    result_value=1.5,
                )
            )
            step_idx += 1

            steps.append(
                CalculationStep(
                    step_number=step_idx,
                    description=f"Phần tỷ lệ suy giảm vượt quá 10% ({additional_pct}%) nhân với 0.4 tháng lương / 1%",
                    formula=f"{additional_pct} * 0.4 tháng",
                    result_value=round(additional_months, 2),
                )
            )
            step_idx += 1

            steps.append(
                CalculationStep(
                    step_number=step_idx,
                    description=f"Tổng số tháng lương bồi thường (1.5 + {additional_pct} x 0.4)",
                    formula=f"1.5 + {additional_months:.2f}",
                    result_value=round(base_months, 2),
                )
            )
            step_idx += 1

        # Xử lý trường hợp có lỗi của người lao động (Khoản 5 Điều 38 -> Trợ cấp tối thiểu 40%)
        if is_worker_fault:
            actual_months = base_months * 0.40
            type_title = "Trợ cấp tai nạn lao động (do lỗi người lao động)"
            steps.append(
                CalculationStep(
                    step_number=step_idx,
                    description="Áp dụng Khoản 5 Điều 38: Tai nạn do lỗi của người lao động, người sử dụng lao động trợ cấp ít nhất 40% mức bồi thường",
                    formula=f"{base_months:.2f} tháng * 40%",
                    result_value=round(actual_months, 2),
                )
            )
            step_idx += 1
        else:
            actual_months = base_months
            type_title = "Bồi thường tai nạn lao động"

        total_payout = monthly_salary * actual_months
        steps.append(
            CalculationStep(
                step_number=step_idx,
                description=f"Tổng số tiền chi trả ({actual_months:.2f} tháng x {monthly_salary:,.0f} đ/tháng)",
                formula=f"{monthly_salary:,.0f} * {actual_months:.2f}",
                result_value=round(total_payout, 2),
            )
        )

        notes = [
            f"Tiền lương căn cứ: {monthly_salary:,.0f} VNĐ/tháng.",
            f"Tỷ lệ suy giảm khả năng lao động: {impairment_percentage}%.",
            f"Hình thức giải quyết: {type_title}.",
        ]

        return LegalCalculationResult(
            calculation_type=type_title,
            legal_basis=legal_basis,
            summary=f"Mức chi trả cho người lao động bị tai nạn lao động suy giảm {impairment_percentage}% KNLĐ ({'do lỗi NLĐ' if is_worker_fault else 'không do lỗi NLĐ'}) là {total_payout:,.0f} VNĐ ({actual_months:.2f} tháng lương).",
            total_amount_vnd=round(total_payout, 0),
            total_months_salary=round(actual_months, 2),
            steps=steps,
            notes=notes,
        )

    # -------------------------------------------------------------------------
    # 4. TÍNH TRỢ CẤP THẤT NGHIỆP (Điều 50 Luật Việc làm 2013)
    # -------------------------------------------------------------------------
    @staticmethod
    def calculate_unemployment_benefit(
        avg_monthly_salary_6m_bhtn: float,
        months_bhtn_contributed: float,
        regional_minimum_wage: Optional[float] = None,
    ) -> LegalCalculationResult:
        """Tính trợ cấp thất nghiệp theo Điều 50 Luật Việc làm 2013.
        
        Args:
            avg_monthly_salary_6m_bhtn: Mức bình quân tiền lương tháng đóng BHTN của 06 tháng liền kề trước khi thất nghiệp.
            months_bhtn_contributed: Số tháng đã đóng BHTN.
            regional_minimum_wage: Mức lương tối thiểu vùng (dùng để áp dụng trần tối đa không quá 5 lần lương tối thiểu vùng).
        """
        if avg_monthly_salary_6m_bhtn <= 0 or months_bhtn_contributed < 12.0:
            raise ValueError("Phải có thời gian đóng BHTN đủ từ 12 tháng trở lên và mức lương đóng BHTN > 0.")

        steps: List[CalculationStep] = []
        step_idx = 1
        legal_basis = "Điều 50 Luật Việc làm 2013"

        # Khoản 1 Điều 50: Mức hưởng hàng tháng bằng 60% mức bình quân lương 6 tháng
        raw_monthly_benefit = avg_monthly_salary_6m_bhtn * 0.60
        steps.append(
            CalculationStep(
                step_number=step_idx,
                description="Tính mức trợ cấp hàng tháng bằng 60% mức lương bình quân 6 tháng đóng BHTN (Khoản 1 Điều 50)",
                formula=f"{avg_monthly_salary_6m_bhtn:,.0f} * 60%",
                result_value=raw_monthly_benefit,
            )
        )
        step_idx += 1

        # Áp dụng trần tối đa 5 lần mức lương tối thiểu vùng nếu có
        capped_monthly_benefit = raw_monthly_benefit
        if regional_minimum_wage and regional_minimum_wage > 0:
            max_ceiling = regional_minimum_wage * 5.0
            if raw_monthly_benefit > max_ceiling:
                capped_monthly_benefit = max_ceiling
                steps.append(
                    CalculationStep(
                        step_number=step_idx,
                        description=f"Áp trần tối đa không quá 5 lần lương tối thiểu vùng (5 x {regional_minimum_wage:,.0f} đ)",
                        formula=f"min({raw_monthly_benefit:,.0f}, {max_ceiling:,.0f})",
                        result_value=capped_monthly_benefit,
                    )
                )
                step_idx += 1

        # Khoản 2 Điều 50: Đóng đủ 12 đến 36 tháng được hưởng 3 tháng; cứ đóng thêm đủ 12 tháng được thêm 1 tháng, tối đa 12 tháng
        if months_bhtn_contributed < 36.0:
            benefit_duration_months = 3
        else:
            extra_months = months_bhtn_contributed - 36.0
            extra_benefit_months = int(extra_months // 12)
            benefit_duration_months = min(12, 3 + extra_benefit_months)

        steps.append(
            CalculationStep(
                step_number=step_idx,
                description=f"Xác định thời gian hưởng trợ cấp thất nghiệp căn cứ theo {months_bhtn_contributed:.0f} tháng đóng BHTN (Khoản 2 Điều 50)",
                formula=f"3 tháng đầu (12-36 tháng đóng) + {benefit_duration_months - 3} tháng tăng thêm",
                result_value=float(benefit_duration_months),
            )
        )
        step_idx += 1

        total_benefit = capped_monthly_benefit * benefit_duration_months
        steps.append(
            CalculationStep(
                step_number=step_idx,
                description=f"Tổng số tiền trợ cấp thất nghiệp được hưởng ({benefit_duration_months} tháng x {capped_monthly_benefit:,.0f} đ/tháng)",
                formula=f"{capped_monthly_benefit:,.0f} * {benefit_duration_months}",
                result_value=total_benefit,
            )
        )

        notes = [
            f"Mức hưởng hàng tháng: {capped_monthly_benefit:,.0f} VNĐ/tháng.",
            f"Thời gian hưởng trợ cấp thất nghiệp: {benefit_duration_months} tháng liên tục.",
            "Trong thời gian hưởng TCTN, người lao động được hưởng chế độ BHYT do Quỹ BHTN đóng (Khoản 1 Điều 51).",
        ]

        return LegalCalculationResult(
            calculation_type="Trợ cấp thất nghiệp",
            legal_basis=legal_basis,
            summary=f"Trợ cấp thất nghiệp hàng tháng là {capped_monthly_benefit:,.0f} VNĐ/tháng trong thời gian {benefit_duration_months} tháng. Tổng mức hưởng là {total_benefit:,.0f} VNĐ.",
            total_amount_vnd=round(total_benefit, 0),
            total_months_salary=float(benefit_duration_months),
            steps=steps,
            notes=notes,
        )


# Convenience function aliases
calculate_overtime_pay = SymbolicLegalCalculator.calculate_overtime_pay
calculate_severance_or_redundancy = SymbolicLegalCalculator.calculate_severance_or_redundancy
calculate_work_accident_benefit = SymbolicLegalCalculator.calculate_work_accident_benefit
calculate_unemployment_benefit = SymbolicLegalCalculator.calculate_unemployment_benefit

