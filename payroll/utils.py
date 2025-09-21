from datetime import date, timedelta
from decimal import Decimal
import os
from io import BytesIO
import logging

from django.conf import settings
from django.utils import timezone
from django.core.mail import EmailMessage

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .models import (
    Payroll, EmployeeAttendance, LeaveRecord, SalaryStructure,
    TaxBracket, StatutoryDeduction, Loan, BulkPaymentLog, EmployeeBankInfo
)

logger = logging.getLogger(__name__)

# Weekends (Saturday=5, Sunday=6)
WEEKEND = {5, 6}


def working_days(start: date, end: date) -> int:
    d = start
    count = 0
    while d <= end:
        if d.weekday() not in WEEKEND:
            count += 1
        d += timedelta(days=1)
    return count


def calc_attendance_leave_deductions(payroll: Payroll) -> Decimal:
    if not payroll.salary_structure:
        return Decimal("0.00")

    s: SalaryStructure = payroll.salary_structure
    wd = working_days(payroll.period_start, payroll.period_end) or 1
    per_day = (s.basic_pay / Decimal(wd)).quantize(Decimal("0.01"))

    worked_dates = set(
        EmployeeAttendance.objects.filter(
            employee=payroll.employee,
            date__range=(payroll.period_start, payroll.period_end),
            work_hours__gt=0,
        ).values_list("date", flat=True)
    )

    leaves = LeaveRecord.objects.filter(
        employee=payroll.employee,
        status="APPROVED",
        from_date__lte=payroll.period_end,
        to_date__gte=payroll.period_start,
    )

    paid_leave_dates, unpaid_leave_dates = set(), set()
    for lv in leaves:
        d = max(lv.from_date, payroll.period_start)
        e = min(lv.to_date, payroll.period_end)
        while d <= e:
            if d.weekday() not in WEEKEND:
                if "UNPAID" in lv.leave_type.upper():
                    unpaid_leave_dates.add(d)
                else:
                    paid_leave_dates.add(d)
            d += timedelta(days=1)

    period_dates = {
        d
        for d in (
            payroll.period_start + timedelta(days=i)
            for i in range((payroll.period_end - payroll.period_start).days + 1)
        )
        if d.weekday() not in WEEKEND
    }

    absent_dates = period_dates - worked_dates - paid_leave_dates - unpaid_leave_dates
    unpaid_count = len(unpaid_leave_dates) + len(absent_dates)

    return (per_day * Decimal(unpaid_count)).quantize(Decimal("0.01"))


def calculate_tax(income: Decimal) -> Decimal:
    brackets = TaxBracket.objects.all().order_by("min_income")
    tax = Decimal("0.00")

    for b in brackets:
        if b.max_income and income > b.max_income:
            taxable = b.max_income - b.min_income
        else:
            taxable = max(Decimal("0.00"), income - Decimal(b.min_income))
        tax += Decimal(taxable) * (Decimal(b.rate) / Decimal("100"))
        if b.max_income and income <= b.max_income:
            break

    return tax.quantize(Decimal("0.01"))


def calculate_statutory_deductions(gross: Decimal) -> Decimal:
    deductions = StatutoryDeduction.objects.filter(is_mandatory=True)
    total = Decimal("0.00")
    for d in deductions:
        total += gross * (Decimal(d.rate) / Decimal("100"))
    return total.quantize(Decimal("0.01"))


def apply_loan_deductions(employee, gross: Decimal) -> Decimal:
    """Deduct active loan installments for an employee."""
    loans = Loan.objects.filter(employee=employee, status="APPROVED", remaining_balance__gt=0)
    total = Decimal("0.00")
    for loan in loans:
        installment = loan.installment
        if installment > loan.remaining_balance:
            installment = loan.remaining_balance
        loan.remaining_balance -= installment
        if loan.remaining_balance == 0:
            loan.status = "CLOSED"
        loan.save()
        total += installment
    return total.quantize(Decimal("0.01"))


def process_bulk_payment(bulk_payment: BulkPaymentLog):
    """Process bulk salary payouts (simulate Stripe Connect payouts)."""
    payrolls = Payroll.objects.filter(
        period_start=bulk_payment.period_start,
        period_end=bulk_payment.period_end,
        payment_status="PENDING",
    )
    total_paid = Decimal("0.00")

    for payroll in payrolls:
        try:
            bank_info = EmployeeBankInfo.objects.get(employee=payroll.employee)
        except EmployeeBankInfo.DoesNotExist:
            logger.warning("No bank info for %s", payroll.employee.email)
            continue

        # In real life, integrate Stripe Connect Payouts here
        payroll.payment_status = "PAID"
        payroll.paid_on = timezone.now().date()
        payroll.save()
        total_paid += payroll.net_salary

    bulk_payment.total_amount = total_paid
    bulk_payment.status = "COMPLETED"
    bulk_payment.save()


def generate_payslip_pdf(payroll: Payroll) -> str:
    payslip_dir = os.path.join(settings.MEDIA_ROOT, "payslips")
    os.makedirs(payslip_dir, exist_ok=True)
    filename = f"payslip_{payroll.id}.pdf"
    file_path = os.path.join(payslip_dir, filename)

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "Payslip")
    y -= 30

    full_name = getattr(payroll.employee, "get_full_name", lambda: payroll.employee.email)() or payroll.employee.email
    p.setFont("Helvetica", 11)
    p.drawString(50, y, f"Employee: {full_name}"); y -= 18
    p.drawString(50, y, f"Period: {payroll.period_start} to {payroll.period_end}"); y -= 18
    p.drawString(50, y, f"Generated on: {timezone.now().date()}"); y -= 24

    s = payroll.salary_structure
    p.drawString(50, y, f"Gross Salary: {payroll.gross_salary}"); y -= 18
    p.drawString(50, y, f"Tax Deducted: {payroll.tax_amount}"); y -= 18
    p.drawString(50, y, f"Statutory Deductions: {payroll.statutory_deductions}"); y -= 18
    p.drawString(50, y, f"Other Deductions: {s.deductions if s else 0}"); y -= 18
    p.drawString(50, y, f"Total Deductions: {payroll.total_deductions}"); y -= 18

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, f"Net Salary: {payroll.net_salary}"); y -= 30

    p.setFont("Helvetica-Oblique", 9)
    p.drawString(50, y, "This is a system-generated payslip.")
    p.showPage()
    p.save()

    with open(file_path, "wb") as f:
        f.write(buffer.getvalue())

    return f"{settings.MEDIA_URL}payslips/{filename}"


def send_payslip_email(payroll: Payroll, pdf_path: str):
    subject = "Your Payslip is Ready"
    body = (
        f"Dear {getattr(payroll.employee, 'get_full_name', lambda: payroll.employee.username)()},\n\n"
        f"Your salary has been processed successfully.\n"
        f"Period: {payroll.period_start} to {payroll.period_end}\n"
        f"Gross: {payroll.gross_salary}\n"
        f"Tax: {payroll.tax_amount}\n"
        f"Statutory Deductions: {payroll.statutory_deductions}\n"
        f"Net: {payroll.net_salary}\n\n"
        f"Please find your payslip attached.\n\n"
        f"Regards,\nNexHR Payroll Team"
    )
    email = EmailMessage(
        subject,
        body,
        settings.EMAIL_HOST_USER,
        [payroll.employee.email],
    )
    email.attach_file(pdf_path)
    email.send()
