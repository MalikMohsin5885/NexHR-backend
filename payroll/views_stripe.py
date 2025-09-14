import stripe
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now
from django.core.mail import EmailMessage
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .models import Payroll, Payslip

stripe.api_key = settings.STRIPE_SECRET_KEY


def generate_payslip_pdf(payroll):
    """
    Generate a simple PDF payslip in memory using ReportLab.
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 800, f"Payslip for {payroll.employee.get_full_name()}")
    p.setFont("Helvetica", 12)
    p.drawString(100, 770, f"Employee: {payroll.employee.email}")
    p.drawString(100, 750, f"Payroll ID: {payroll.id}")
    p.drawString(100, 730, f"Salary: {payroll.amount}")
    p.drawString(100, 710, f"Status: {payroll.payment_status}")
    p.drawString(100, 690, f"Paid On: {payroll.paid_on}")
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer


def send_payslip_email(payroll, payslip_pdf):
    """
    Send payslip email with PDF attachment.
    """
    subject = "Your Payslip is Ready"
    body = (
        f"Dear {payroll.employee.get_full_name() or payroll.employee.username},\n\n"
        f"Your salary has been paid successfully.\n"
        f"You can find your payslip attached.\n\n"
        f"Regards,\nNexHR Payroll Team"
    )
    email = EmailMessage(
        subject,
        body,
        settings.GMAIL_USER,  # from
        [payroll.employee.email],  # to
    )
    email.attach(f"payslip_{payroll.id}.pdf", payslip_pdf.getvalue(), "application/pdf")
    email.send()


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # ✅ Handle payment success
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        payroll_id = session.get("metadata", {}).get("payroll_id")

        if payroll_id:
            try:
                payroll = Payroll.objects.get(id=payroll_id)
                payroll.payment_status = "PAID"
                payroll.paid_on = now().date()
                payroll.save()

                # Generate PDF
                pdf_buffer = generate_payslip_pdf(payroll)

                # Create a Payslip record (if not already exists)
                payslip, created = Payslip.objects.get_or_create(
                    payroll=payroll,
                    defaults={"payslip_pdf_url": f"https://dummy-payslips.com/{payroll.id}.pdf"}
                )

                # Send email with PDF attachment
                send_payslip_email(payroll, pdf_buffer)

                print(f"✅ Payroll {payroll.id} marked as PAID, payslip generated & emailed")

            except Payroll.DoesNotExist:
                print(f"❌ Payroll {payroll_id} not found")

    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        print(f"❌ Payment failed: {payment_intent['id']}")

    return JsonResponse({"status": "success"})
