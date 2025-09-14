# payroll/utils.py
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pathlib import Path
from django.core.mail import EmailMessage

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
    Business rules:
    - Per-day rate = basic_pay / working_days
    - Approved leave with 'UNPAID' → deducted
    - Paid leave → not deducted
    - Absent (not worked, no leave) → deducted
    """
    if not payroll.salary_structure:
        return Decimal("0.00")

    s: SalaryStructure = payroll.salary_structure
    wd = working_days(payroll.period_start, payroll.period_end) or 1
    per_day = (s.basic_pay / Decimal(wd)).quantize(Decimal("0.01"))

    worked_dates = set(
        EmployeeAttendance.objects.filter(
            employee=payroll.employee,
            date__gte=payroll.period_start,
            date__lte=payroll.period_end,
            work_hours__gt=0
        ).values_list("date", flat=True)
    )

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

    period_dates = set(
        d for d in (payroll.period_start + timedelta(days=i)
        for i in range((payroll.period_end - payroll.period_start).days + 1))
        if d.weekday() not in WEEKEND
    )

    absent_dates = period_dates - worked_dates - paid_leave_dates - unpaid_leave_dates

    unpaid_count = len(unpaid_leave_dates) + len(absent_dates)
    deduction = (per_day * Decimal(unpaid_count)).quantize(Decimal("0.01"))
    return deduction


def generate_payslip_pdf(payroll: Payroll) -> str:
    """
    Creates a PDF at media/payslips/payslip_<id>.pdf
    Returns MEDIA URL (e.g., /media/payslips/payslip_1.pdf)
    """
    media_dir = Path(settings.MEDIA_ROOT) / "payslips"
    media_dir.mkdir(parents=True, exist_ok=True)

    filename = f"payslip_{payroll.id}.pdf"
    filepath = media_dir / filename

    c = canvas.Canvas(str(filepath), pagesize=A4)
    width, height = A4
    y = height - 50

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, y, "NexHR Official Payslip")
    y -= 40

    # Employee Info
    fname = getattr(payroll.employee, "fname", "") or ""
    lname = getattr(payroll.employee, "lname", "") or ""
    full_name = f"{fname} {lname}".strip() or payroll.employee.email

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Employee: {full_name}")
    y -= 20
    c.drawString(50, y, f"Email: {payroll.employee.email}")
    y -= 20
    c.drawString(50, y, f"Period: {payroll.period_start} to {payroll.period_end}")
    y -= 20
    c.drawString(50, y, f"Issued On: {timezone.now().strftime('%Y-%m-%d')}")
    y -= 40

    # Salary Breakdown
    s = payroll.salary_structure
    basic = s.basic_pay if s else Decimal("0.00")
    allowances = s.allowances if s else Decimal("0.00")
    fixed_deductions = s.deductions if s else Decimal("0.00")
    tax = s.tax if s else Decimal("0.00")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Salary Details")
    y -= 20

    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Basic Pay: ${basic}")
    y -= 18
    c.drawString(50, y, f"Allowances: ${allowances}")
    y -= 18
    c.drawString(50, y, f"Fixed Deductions: ${fixed_deductions}")
    y -= 18
    c.drawString(50, y, f"Attendance/Leave Deductions: ${payroll.total_deductions}")
    y -= 18
    c.drawString(50, y, f"Tax: ${tax}")
    y -= 18
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"Net Salary: ${payroll.net_salary}")
    y -= 40

    # Footer
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, y, "This is a system-generated payslip. For queries, contact HR.")
    c.showPage()
    c.save()

    return f"{settings.MEDIA_URL}payslips/{filename}"
def send_payslip_email(payroll: Payroll, pdf_path: str):
    """
    Send professional payslip email with PDF attachment.
    """
    fname = getattr(payroll.employee, "fname", "") or ""
    lname = getattr(payroll.employee, "lname", "") or ""
    full_name = f"{fname} {lname}".strip() or payroll.employee.email

    subject = f"NexHR Payslip | {payroll.period_start} - {payroll.period_end}"
    body = (
        f"Dear {full_name},\n\n"
        f"Attached is your official payslip for the period "
        f"{payroll.period_start} to {payroll.period_end}.\n\n"
        f"Net Salary: ${payroll.net_salary}\n\n"
        f"Best regards,\n"
        f"NexHR Payroll Team"
    )

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[payroll.employee.email],
    )
    email.attach_file(pdf_path)
    email.send()
