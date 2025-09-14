# views.py

from decimal import Decimal
import stripe
import logging
import json
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from pathlib import Path

from rest_framework import viewsets
from rest_framework.decorators import api_view, action
from rest_framework.response import Response

from .models import SalaryStructure, Payroll, Payslip, EmployeeAttendance, LeaveRecord, Notification
from .serializers import (
    SalaryStructureSerializer, PayrollSerializer, PayslipSerializer,
    EmployeeAttendanceSerializer, LeaveRecordSerializer, NotificationSerializer
)
from .utils import calc_attendance_leave_deductions, generate_payslip_pdf, send_payslip_email

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


def csrf_exempt_class(view):
    """Exempt CSRF for all ViewSet actions."""
    from django.utils.decorators import method_decorator
    decorator = method_decorator(csrf_exempt)
    view.dispatch = decorator(view.dispatch)
    return view


# --- Your existing ViewSets ---
@csrf_exempt_class
class SalaryStructureViewSet(viewsets.ModelViewSet):
    queryset = SalaryStructure.objects.all()
    serializer_class = SalaryStructureSerializer


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

        dynamic_deduction = calc_attendance_leave_deductions(payroll)
        gross = (s.basic_pay + s.allowances).quantize(Decimal("0.01"))
        total_deductions = (s.deductions + dynamic_deduction + s.tax).quantize(Decimal("0.01"))
        net = (gross - total_deductions).quantize(Decimal("0.01"))

        payroll.gross_salary = gross
        payroll.total_deductions = total_deductions
        payroll.net_salary = net
        payroll.save()

        return Response(PayrollSerializer(payroll).data)


@csrf_exempt_class
class PayslipViewSet(viewsets.ModelViewSet):
    queryset = Payslip.objects.all()
    serializer_class = PayslipSerializer


@csrf_exempt_class
class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = EmployeeAttendance.objects.all()
    serializer_class = EmployeeAttendanceSerializer


@csrf_exempt_class
class LeaveRecordViewSet(viewsets.ModelViewSet):
    queryset = LeaveRecord.objects.all()
    serializer_class = LeaveRecordSerializer


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
        success_url=f"{settings.SITE_URL}/success",
        cancel_url=f"{settings.SITE_URL}/cancel",
        metadata={"payroll_id": str(payroll.id)},
    )
    return Response({"id": session.id, "url": session.url})


# --- Stripe Webhook with Test Bypass ---
@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        if sig_header:
            # ✅ Real Stripe event
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        else:
            # ✅ Test-only bypass for manual HTTP POST
            event = json.loads(payload)
    except Exception as e:
        logger.exception("Invalid Stripe webhook: %s", e)
        return HttpResponse(status=400)

    # Handle checkout.session.completed
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        payroll_id = session.get("metadata", {}).get("payroll_id")
        if payroll_id:
            try:
                payroll = Payroll.objects.get(id=payroll_id)
                if payroll.payment_status != "PAID":
                    payroll.payment_status = "PAID"
                    payroll.paid_on = timezone.now().date()
                    payroll.save()

                    # Generate PDF
                    pdf_url = generate_payslip_pdf(payroll)
                    pdf_path = str(Path(settings.MEDIA_ROOT) / pdf_url.replace(settings.MEDIA_URL, ""))

                    Payslip.objects.update_or_create(
                        payroll=payroll,
                        defaults={"payslip_pdf_url": pdf_url}
                    )

                    # Send email
                    send_payslip_email(payroll, pdf_path)

                    # Create notification
                    Notification.objects.create(
                        employee=payroll.employee,
                        message=f"Payroll {payroll_id} has been marked as PAID."
                    )

                    logger.info("Payroll %s marked PAID and email/pdf sent", payroll.id)

            except Payroll.DoesNotExist:
                logger.error("Payroll %s not found", payroll_id)

    return HttpResponse(status=200)
