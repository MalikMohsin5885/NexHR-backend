# payroll/utils.py
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pathlib import Path

from .models import Payroll, EmployeeAttendance, LeaveRecord, SalaryStructure

WEEKEND = {5, 6}  # Saturday(5), Sunday(6)

def working_days(start: date, end: date) -> int:
    d = start
    count = 0
    while d <= end:
        if d.weekday() not in WEEKEND:
            count += 1
        d += timedelta(days=1)
    return count

def calc_attendance_leave_deductions(payroll: Payroll) -> Decimal:
    """
    Simple business rules:
    - Per-day rate = basic_pay / working_days in period (Mon–Fri)
    - Approved leave:
        * leave_type contains 'UNPAID' -> deducted
        * otherwise (paid leave) -> no deduction
    - Absent days (no attendance & not approved paid leave) -> deducted
    """
    if not payroll.salary_structure:
        return Decimal("0.00")

    s: SalaryStructure = payroll.salary_structure
    wd = working_days(payroll.period_start, payroll.period_end) or 1
    per_day = (s.basic_pay / Decimal(wd)).quantize(Decimal("0.01"))

    # Attendance days actually worked (work_hours > 0)
    worked_dates = set(
        EmployeeAttendance.objects.filter(
            employee=payroll.employee,
            date__gte=payroll.period_start,
            date__lte=payroll.period_end,
            work_hours__gt=0
        ).values_list("date", flat=True)
    )

    # Approved leaves
    leaves = LeaveRecord.objects.filter(
        employee=payroll.employee,
        status="APPROVED",
        from_date__lte=payroll.period_end,
        to_date__gte=payroll.period_start,
    )

    paid_leave_dates = set()
    unpaid_leave_dates = set()
    for lv in leaves:
        d = max(lv.from_date, payroll.period_start)
        e = min(lv.to_date, payroll.period_end)
        cur = d
        while cur <= e:
            if cur.weekday() not in WEEKEND:
                if "UNPAID" in lv.leave_type.upper():
                    unpaid_leave_dates.add(cur)
                else:
                    paid_leave_dates.add(cur)
            cur += timedelta(days=1)

    # Total working calendar dates in period
    period_dates = []
    d = payroll.period_start
    while d <= payroll.period_end:
        if d.weekday() not in WEEKEND:
            period_dates.append(d)
        d += timedelta(days=1)
    period_dates = set(period_dates)

    # Absent = working day not worked, not paid leave, not unpaid leave
    absent_dates = period_dates - worked_dates - paid_leave_dates - unpaid_leave_dates

    unpaid_count = len(unpaid_leave_dates) + len(absent_dates)
    deduction = (per_day * Decimal(unpaid_count)).quantize(Decimal("0.01"))
    return deduction

def generate_payslip_pdf(payroll: Payroll) -> str:
    """
    Creates a PDF at media/payslips/payslip_<id>.pdf
    Returns the relative MEDIA URL (e.g., /media/payslips/payslip_1.pdf)
    """
    media_dir = Path(settings.MEDIA_ROOT) / "payslips"
    media_dir.mkdir(parents=True, exist_ok=True)

    filename = f"payslip_{payroll.id}.pdf"
    filepath = media_dir / filename

    c = canvas.Canvas(str(filepath), pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Payslip")
    y -= 30

    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Employee: {payroll.employee.get_full_name() or payroll.employee.email}")
    y -= 18
    c.drawString(50, y, f"Period: {payroll.period_start} to {payroll.period_end}")
    y -= 18
    c.drawString(50, y, f"Generated on: {timezone.now().date()}")
    y -= 24

    s = payroll.salary_structure
    basic = s.basic_pay if s else Decimal("0.00")
    allowances = s.allowances if s else Decimal("0.00")
    fixed_deductions = s.deductions if s else Decimal("0.00")
    tax = s.tax if s else Decimal("0.00")

    c.drawString(50, y, f"Basic Pay: {basic}")
    y -= 18
    c.drawString(50, y, f"Allowances: {allowances}")
    y -= 18
    c.drawString(50, y, f"Fixed Deductions: {fixed_deductions}")
    y -= 18
    c.drawString(50, y, f"Attendance/Leave Deductions: {payroll.total_deductions}")
    y -= 18
    c.drawString(50, y, f"Tax: {tax}")
    y -= 18
    c.drawString(50, y, f"Net Salary: {payroll.net_salary}")
    y -= 30

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, y, "This is a system generated payslip.")
    c.showPage()
    c.save()

    return f"{settings.MEDIA_URL}payslips/{filename}"
