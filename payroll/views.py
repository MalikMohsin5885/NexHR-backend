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
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

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
    save_payslip_to_storage,
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
class SalaryStructureViewSet(viewsets.ModelViewSet):
    queryset = SalaryStructure.objects.all()
    serializer_class = SalaryStructureSerializer
    permission_classes = [IsAuthenticated]


# --- Tax & Statutory ---
class TaxBracketViewSet(viewsets.ModelViewSet):
    queryset = TaxBracket.objects.all()
    serializer_class = TaxBracketSerializer
    permission_classes = [IsAuthenticated]


class StatutoryDeductionViewSet(viewsets.ModelViewSet):
    queryset = StatutoryDeduction.objects.all()
    serializer_class = StatutoryDeductionSerializer
    permission_classes = [IsAuthenticated]


# --- Payrolls ---
class PayrollViewSet(viewsets.ModelViewSet):
    queryset = Payroll.objects.all()
    serializer_class = PayrollSerializer
    permission_classes = [IsAuthenticated]

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

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        payroll = self.get_object()
        payroll.approval_status = "APPROVED"
        payroll.approved_by = request.user
        payroll.save(update_fields=["approval_status", "approved_by"])
        return Response(PayrollSerializer(payroll).data)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        payroll = self.get_object()
        payroll.approval_status = "REJECTED"
        payroll.approved_by = request.user
        payroll.save(update_fields=["approval_status", "approved_by"])
        return Response(PayrollSerializer(payroll).data)

    # --- NEW: Download Payslip PDF ---
    @action(detail=True, methods=["get"], url_path="download-payslip")
    def download_payslip(self, request, pk=None):
        try:
            payroll = self.get_object()
            pdf_buffer = generate_payslip_pdf(payroll)
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
class PayslipViewSet(viewsets.ModelViewSet):
    queryset = Payslip.objects.all()
    serializer_class = PayslipSerializer
    permission_classes = [IsAuthenticated]


# --- Attendance ---
class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = EmployeeAttendance.objects.all()
    serializer_class = EmployeeAttendanceSerializer
    permission_classes = [IsAuthenticated]


# --- Leaves ---
class LeaveRecordViewSet(viewsets.ModelViewSet):
    queryset = LeaveRecord.objects.all()
    serializer_class = LeaveRecordSerializer
    permission_classes = [IsAuthenticated]


# --- Notifications ---
class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]


# --- Stripe Checkout Session ---
@api_view(["POST"])
@permission_classes([IsAuthenticated])
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
        metadata={
            "payroll_id": str(payroll.id),
            "paid_by": str(request.user.id) if request.user and request.user.is_authenticated else "",
        },
    )
    return Response({"id": session.id, "url": session.url})


# --- Stripe Webhook ---
@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        if sig_header:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        else:
            event = json.loads(payload)
    except Exception as e:
        logger.exception("Invalid Stripe webhook: %s", e)
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        payroll_id = session.get("metadata", {}).get("payroll_id")
        if payroll_id:
            try:
                payroll = Payroll.objects.get(id=payroll_id)
                if payroll.payment_status != "PAID":
                    payroll.payment_status = "PAID"
                    payroll.paid_on = timezone.now().date()
                    paid_by = session.get("metadata", {}).get("paid_by")
                    if paid_by:
                        try:
                            from django.contrib.auth import get_user_model
                            User = get_user_model()
                            payroll.paid_by = User.objects.filter(id=paid_by).first()
                        except Exception:
                            payroll.paid_by = None
                    payroll.save()

                    pdf_buffer = generate_payslip_pdf(payroll)
                    pdf_url = save_payslip_to_storage(payroll, pdf_buffer)
                    Payslip.objects.update_or_create(
                        payroll=payroll,
                        defaults={"payslip_pdf_url": pdf_url}
                    )
                    send_payslip_email(payroll, pdf_buffer)

                    Notification.objects.create(
                        employee=payroll.employee,
                        message=f"Payroll {payroll_id} has been marked as PAID. Payslip emailed."
                    )

                    logger.info("Payroll %s marked PAID and detailed payslip emailed", payroll.id)

            except Payroll.DoesNotExist:
                logger.error("Payroll %s not found", payroll_id)

    return HttpResponse(status=200)
