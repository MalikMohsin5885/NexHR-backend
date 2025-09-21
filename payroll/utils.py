from decimal import Decimal
from io import BytesIO
from datetime import datetime
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
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
            taxable = max(Decimal("0.00"), Decimal(income) - Decimal(b.min_income))
        tax += Decimal(taxable) * (Decimal(b.rate) / Decimal("100"))
        if b.max_income and income <= b.max_income:
            break
    return Decimal(tax).quantize(Decimal("0.01"))


def calculate_statutory_deductions(gross):
    deductions = StatutoryDeduction.objects.filter(is_mandatory=True)
    total = Decimal("0.00")
    for d in deductions:
        total += Decimal(gross) * (Decimal(d.rate) / Decimal("100"))
    return total.quantize(Decimal("0.01"))


def generate_payslip_pdf(payroll):
    """
    Generate a detailed PDF payslip, save to MEDIA_ROOT, 
    and return (buffer, url).
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 800, "Payslip")
    p.setFont("Helvetica", 12)

    p.drawString(100, 770, f"Employee: {getattr(payroll.employee, 'get_full_name', lambda: payroll.employee.email)() or payroll.employee.email}")
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
    other_deductions = payroll.salary_structure.deductions if payroll.salary_structure else 0
    p.drawString(120, y, f"Other Deductions: {other_deductions}"); y -= 20
    p.drawString(120, y, f"Total Deductions: {payroll.total_deductions}"); y -= 20

    p.setFont("Helvetica-Bold", 12)
    p.drawString(120, y, f"Net Salary: {payroll.net_salary}")

    y -= 40
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(100, y, "This is a system-generated payslip. No signature required.")

    p.showPage()
    p.save()
    buffer.seek(0)

    # --- Save to MEDIA_ROOT/payslips ---
    payslip_dir = os.path.join(settings.MEDIA_ROOT, "payslips")
    os.makedirs(payslip_dir, exist_ok=True)
    filename = f"payslip_{payroll.id}.pdf"
    file_path = os.path.join(payslip_dir, filename)

    with open(file_path, "wb") as f:
        f.write(buffer.getvalue())

    # Relative URL for model
    url = f"{settings.MEDIA_URL}payslips/{filename}"

    return buffer, url


def send_payslip_email(payroll, pdf_buffer):
    subject = "Your Payslip is Ready"
    body = (
        f"Dear {payroll.employee.fname} {payroll.employee.lname or ''},\n\n"
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
    settings.EMAIL_HOST_USER,   # instead of settings.GMAIL_USER
    [payroll.employee.email],
)
    # Attach the in-memory PDF
    email.attach(f"payslip_{payroll.id}.pdf", pdf_buffer.getvalue(), "application/pdf")
    email.send()


def save_payslip_to_storage(payroll, pdf_buffer):
    """
    Persist the PDF buffer to MEDIA storage and return a URL.
    Creates directories as needed via default_storage.
    """
    filename = f"payslips/payslip_{payroll.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    file_obj = ContentFile(pdf_buffer.getvalue())
    saved_path = default_storage.save(filename, file_obj)

    if hasattr(default_storage, "url"):
        return default_storage.url(saved_path)
    # Fallback for local file storage
    return f"{settings.MEDIA_URL}{saved_path}"
