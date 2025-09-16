from decimal import Decimal
from io import BytesIO
from django.core.mail import EmailMessage
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .models import TaxBracket, StatutoryDeduction


def calc_attendance_leave_deductions(payroll):
    return Decimal("0.00")


def calculate_tax(income):
    brackets = TaxBracket.objects.all().order_by("min_income")
    tax = Decimal("0.00")

    for b in brackets:
        if b.max_income and income > b.max_income:
            taxable = b.max_income - b.min_income
        else:
            taxable = max(0, income - b.min_income)
        tax += taxable * (b.rate / 100)
        if b.max_income and income <= b.max_income:
            break
    return tax.quantize(Decimal("0.01"))


def calculate_statutory_deductions(gross):
    deductions = StatutoryDeduction.objects.filter(is_mandatory=True)
    total = Decimal("0.00")
    for d in deductions:
        total += gross * (d.rate / 100)
    return total.quantize(Decimal("0.01"))


def generate_payslip_pdf(payroll):
    """
    Generate a detailed PDF payslip with breakdown.
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 800, "Payslip")
    p.setFont("Helvetica", 12)

    p.drawString(100, 770, f"Employee: {payroll.employee.get_full_name() or payroll.employee.email}")
    p.drawString(100, 750, f"Payroll ID: {payroll.id}")
    p.drawString(100, 730, f"Period: {payroll.period_start} to {payroll.period_end}")

    y = 700
    p.setFont("Helvetica-Bold", 12)
    p.drawString(100, y, "Earnings & Deductions")
    y -= 20
    p.setFont("Helvetica", 12)

    p.drawString(120, y, f"Gross Salary: {payroll.gross_salary}"); y -= 20
    p.drawString(120, y, f"Tax Deducted: {payroll.tax_amount}"); y -= 20
    p.drawString(120, y, f"Statutory Deductions: {payroll.statutory_deductions}"); y -= 20
    p.drawString(120, y, f"Other Deductions: {payroll.salary_structure.deductions}"); y -= 20
    p.drawString(120, y, f"Total Deductions: {payroll.total_deductions}"); y -= 20

    p.setFont("Helvetica-Bold", 12)
    p.drawString(120, y, f"Net Salary: {payroll.net_salary}")

    y -= 40
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(100, y, "This is a system-generated payslip. No signature required.")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer


def send_payslip_email(payroll, pdf_buffer):
    subject = "Your Payslip is Ready"
    body = (
        f"Dear {payroll.employee.get_full_name() or payroll.employee.username},\n\n"
        f"Your salary has been processed successfully.\n"
        f"Period: {payroll.period_start} to {payroll.period_end}\n"
        f"Gross: {payroll.gross_salary}\n"
        f"Tax: {payroll.tax_amount}\n"
        f"Statutory Deductions: {payroll.statutory_deductions}\n"
        f"Net: {payroll.net_salary}\n\n"
        f"Please find your detailed payslip attached.\n\n"
        f"Regards,\nNexHR Payroll Team"
    )
    email = EmailMessage(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [payroll.employee.email],
    )
    email.attach(f"payslip_{payroll.id}.pdf", pdf_buffer.getvalue(), "application/pdf")
    email.send()
