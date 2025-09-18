from decimal import Decimal
import stripe
import logging
import json
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from rest_framework import viewsets
from rest_framework.decorators import api_view, action
from rest_framework.response import Response

from .models import (
    SalaryStructure, Payroll, Payslip,
    EmployeeAttendance, LeaveRecord, Notification,
    TaxBracket, StatutoryDeduction
)
from .serializers import (
    SalaryStructureSerializer, PayrollSerializer, PayslipSerializer,
    EmployeeAttendanceSerializer, LeaveRecordSerializer, NotificationSerializer,
    TaxBracketSerializer, StatutoryDeductionSerializer
)
from .utils import (
    calc_attendance_leave_deductions,
    generate_payslip_pdf,
    send_payslip_email,
    calculate_tax,
    calculate_statutory_deductions,
)

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


def csrf_exempt_class(view):
    from django.utils.decorators import method_decorator
    decorator = method_decorator(csrf_exempt)
    view.dispatch = decorator(view.dispatch)
    return view


# --- Salary Structures ---
@csrf_exempt_class
class SalaryStructureViewSet(viewsets.ModelViewSet):
    queryset = SalaryStructure.objects.all()
    serializer_class = SalaryStructureSerializer


# --- Tax & Statutory ---
@csrf_exempt_class
class TaxBracketViewSet(viewsets.ModelViewSet):
    queryset = TaxBracket.objects.all()
    serializer_class = TaxBracketSerializer


@csrf_exempt_class
class StatutoryDeductionViewSet(viewsets.ModelViewSet):
    queryset = StatutoryDeduction.objects.all()
    serializer_class = StatutoryDeductionSerializer


# --- Payrolls ---
@csrf_exempt_class
class PayrollViewSet(viewsets.ModelViewSet):
    queryset = Payroll.objects.all()
    serializer_class = PayrollSerializer

    @action(detail=True, methods=["post"], url_path="calculate")
    def calculate(self, request, pk=None):
        payroll = self.get_object()
        s = payroll.salary_structure
        if not s:
            return Response({"detail": "No SalaryStructure linked"}, status=400)

        gross = (s.basic_pay + s.allowances).quantize(Decimal("0.01"))
        tax_amount = calculate_tax(gross)
        statutory = calculate_statutory_deductions(gross)
        dynamic_deduction = calc_attendance_leave_deductions(payroll)

        total_deductions = (s.deductions + dynamic_deduction + tax_amount + statutory).quantize(Decimal("0.01"))
        net = (gross - total_deductions).quantize(Decimal("0.01"))

        payroll.gross_salary = gross
        payroll.tax_amount = tax_amount
        payroll.statutory_deductions = statutory
        payroll.total_deductions = total_deductions
        payroll.net_salary = net
        payroll.save()

        return Response(PayrollSerializer(payroll).data)

    # --- NEW: Download Payslip PDF ---
    @action(detail=True, methods=["get"], url_path="download-payslip")
    def download_payslip(self, request, pk=None):
        try:
            payroll = self.get_object()
            pdf_buffer, _ = generate_payslip_pdf(payroll)
            filename = f"payslip_{payroll.id}.pdf"
            return FileResponse(
                pdf_buffer,
                as_attachment=True,
                filename=filename,
                content_type="application/pdf",
            )
        except Exception as e:
            logger.exception("Error generating payslip: %s", e)
            return Response({"error": "Could not generate payslip"}, status=500)


# --- Payslips ---
@csrf_exempt_class
class PayslipViewSet(viewsets.ModelViewSet):
    queryset = Payslip.objects.all()
    serializer_class = PayslipSerializer


# --- Attendance ---
@csrf_exempt_class
class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = EmployeeAttendance.objects.all()
    serializer_class = EmployeeAttendanceSerializer


# --- Leaves ---
@csrf_exempt_class
class LeaveRecordViewSet(viewsets.ModelViewSet):
    queryset = LeaveRecord.objects.all()
    serializer_class = LeaveRecordSerializer


# --- Notifications ---
@csrf_exempt_class
class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer


# --- Stripe Checkout Session ---
@csrf_exempt
@api_view(["POST"])
def create_checkout_session(request, payroll_id):
    try:
        payroll = Payroll.objects.get(id=payroll_id)
    except Payroll.DoesNotExist:
        return Response({"error": "Payroll not found"}, status=404)

    if payroll.payment_status == "PAID":
        return Response({"error": "Already paid"}, status=400)

    amount_cents = int(Decimal(payroll.net_salary) * 100)
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"Payroll for {payroll.employee.email}"},
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=f"{settings.SITE_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.SITE_URL}/cancel",
        metadata={"payroll_id": str(payroll.id)},
    )
    return Response({"id": session.id, "url": session.url})


# --- Hybrid: Confirm Checkout (Immediate Payslip) ---
@csrf_exempt
@api_view(["POST"])
def confirm_checkout(request):
    """
    Called from frontend after redirect to success_url.
    Verifies payment with Stripe API, then generates payslip instantly.
    """
    session_id = request.data.get("session_id")
    if not session_id:
        return Response({"error": "Missing session_id"}, status=400)

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        payroll_id = session.metadata.get("payroll_id")

        if session.payment_status == "paid" and payroll_id:
            payroll = Payroll.objects.get(id=payroll_id)
            if payroll.payment_status != "PAID":
                payroll.payment_status = "PAID"
                payroll.paid_on = timezone.now().date()
                payroll.save()

                pdf_buffer, pdf_url = generate_payslip_pdf(payroll)
                Payslip.objects.update_or_create(
                    payroll=payroll,
                    defaults={"payslip_pdf_url": pdf_url}
                )
                send_payslip_email(payroll, pdf_buffer)

                Notification.objects.create(
                    employee=payroll.employee,
                    message=f"Payroll {payroll_id} has been marked as PAID. Payslip emailed."
                )

            return Response({"status": "Payslip generated and emailed"})

        return Response({"status": "Payment not completed"}, status=400)

    except Exception as e:
        logger.exception("Error confirming checkout: %s", e)
        return Response({"error": "Failed to confirm checkout"}, status=500)


# --- Stripe Webhook (Fallback for Production) ---
@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)

    try:
        if sig_header and endpoint_secret:
            # validate signature
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        else:
            # fallback for local testing when no signature header is present
            try:
                event = json.loads(payload.decode("utf-8"))
            except Exception:
                event = json.loads(payload)
    except Exception as e:
        logger.exception("Invalid Stripe webhook: %s", e)
        return HttpResponse(status=400)

    # Now handle the event
    event_type = event.get("type")
    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        payroll_id = session.get("metadata", {}).get("payroll_id")
        if payroll_id:
            try:
                payroll = Payroll.objects.get(id=payroll_id)
                # process even if already PAID but payslip missing
                needs_processing = payroll.payment_status != "PAID" or not hasattr(payroll, "payslip")
                if payroll.payment_status != "PAID":
                    payroll.payment_status = "PAID"
                    payroll.paid_on = timezone.now().date()
                    payroll.save()

                if needs_processing:
                    pdf_buffer, pdf_url = generate_payslip_pdf(payroll)
                    Payslip.objects.update_or_create(
                        payroll=payroll,
                        defaults={"payslip_pdf_url": pdf_url}
                    )
                    send_payslip_email(payroll, pdf_buffer)
                    Notification.objects.create(
                        employee=payroll.employee,
                        message=f"Payroll {payroll_id} has been marked as PAID. Payslip emailed."
                    )
                    logger.info("Payroll %s processed: PAID + payslip/email", payroll.id)

            except Payroll.DoesNotExist:
                logger.error("Payroll %s not found", payroll_id)

    elif event_type == "payment_intent.payment_failed":
        payment_intent = event.get("data", {}).get("object", {})
        logger.warning("Payment failed: %s", payment_intent.get("id"))

    return HttpResponse(status=200)
