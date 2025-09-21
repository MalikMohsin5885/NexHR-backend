import logging
from decimal import Decimal
from pathlib import Path

import stripe
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from rest_framework import viewsets
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from .models import (
    SalaryStructure, Payroll, Payslip, EmployeeAttendance, LeaveRecord, Notification,
    EmployeeBankInfo, Loan, Expense, BulkPaymentLog
)
from .serializers import (
    SalaryStructureSerializer, PayrollSerializer, PayslipSerializer,
    EmployeeAttendanceSerializer, LeaveRecordSerializer, NotificationSerializer,
    EmployeeBankInfoSerializer, LoanSerializer, ExpenseSerializer, BulkPaymentLogSerializer
)
from .utils import (
    calc_attendance_leave_deductions, calculate_tax, calculate_statutory_deductions,
    generate_payslip_pdf, send_payslip_email,
    process_bulk_payment, apply_loan_deductions
)
from .permissions import IsAdmin, IsFinance, IsHR, IsEmployeeSelf

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


# ---------------- CSRF EXEMPT HELPER ----------------
def csrf_exempt_class(view):
    """Exempt CSRF for all ViewSet actions."""
    from django.utils.decorators import method_decorator
    decorator = method_decorator(csrf_exempt)
    view.dispatch = decorator(view.dispatch)
    return view


# ---------------- Salary Structure ----------------
@csrf_exempt_class
class SalaryStructureViewSet(viewsets.ModelViewSet):
    queryset = SalaryStructure.objects.all()
    serializer_class = SalaryStructureSerializer
    permission_classes = [IsAuthenticated, IsFinance | IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.roles.filter(name__in=["ADMIN", "FINANCE"]).exists():
            return SalaryStructure.objects.all()
        return SalaryStructure.objects.none()


# ---------------- Payroll ----------------
@csrf_exempt_class
class PayrollViewSet(viewsets.ModelViewSet):
    queryset = Payroll.objects.all()
    serializer_class = PayrollSerializer
    permission_classes = [IsAuthenticated, IsFinance | IsAdmin | IsHR | IsEmployeeSelf]

    def get_queryset(self):
        user = self.request.user
        if user.roles.filter(name__in=["ADMIN", "FINANCE", "HR"]).exists():
            return Payroll.objects.all()
        return Payroll.objects.filter(employee=user)

    def perform_create(self, serializer):
        if not self.request.user.roles.filter(name__in=["ADMIN", "FINANCE"]).exists():
            raise PermissionDenied("Only Finance/Admin can create payroll records.")
        serializer.save()

    @action(detail=True, methods=["post"], url_path="calculate", permission_classes=[IsFinance | IsAdmin])
    def calculate(self, request, pk=None):
        payroll = self.get_object()
        s = payroll.salary_structure
        if not s:
            return Response({"detail": "No SalaryStructure linked"}, status=400)

        dynamic_deduction = calc_attendance_leave_deductions(payroll)
        gross = (s.basic_pay + s.allowances).quantize(Decimal("0.01"))

        # Apply tax & statutory deductions
        tax_amount = calculate_tax(gross)
        statutory = calculate_statutory_deductions(gross)

        # Apply loan deductions
        loan_deduction = apply_loan_deductions(payroll.employee, gross)

        total_deductions = (s.deductions + dynamic_deduction + tax_amount + statutory + loan_deduction).quantize(Decimal("0.01"))
        net = (gross - total_deductions).quantize(Decimal("0.01"))

        payroll.gross_salary = gross
        payroll.tax_amount = tax_amount
        payroll.statutory_deductions = statutory
        payroll.total_deductions = total_deductions
        payroll.net_salary = net
        payroll.save()

        return Response(PayrollSerializer(payroll).data)


# ---------------- Payslip ----------------
@csrf_exempt_class
class PayslipViewSet(viewsets.ModelViewSet):
    queryset = Payslip.objects.all()
    serializer_class = PayslipSerializer
    permission_classes = [IsAuthenticated, IsEmployeeSelf | IsFinance | IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.roles.filter(name__in=["ADMIN", "FINANCE", "HR"]).exists():
            return Payslip.objects.all()
        return Payslip.objects.filter(payroll__employee=user)


# ---------------- Attendance ----------------
@csrf_exempt_class
class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = EmployeeAttendance.objects.all()
    serializer_class = EmployeeAttendanceSerializer
    permission_classes = [IsAuthenticated, IsHR | IsAdmin | IsEmployeeSelf]

    def get_queryset(self):
        user = self.request.user
        if user.roles.filter(name__in=["ADMIN", "HR"]).exists():
            return EmployeeAttendance.objects.all()
        return EmployeeAttendance.objects.filter(employee=user)


# ---------------- Leave ----------------
@csrf_exempt_class
class LeaveRecordViewSet(viewsets.ModelViewSet):
    queryset = LeaveRecord.objects.all()
    serializer_class = LeaveRecordSerializer
    permission_classes = [IsAuthenticated, IsHR | IsAdmin | IsEmployeeSelf]

    def get_queryset(self):
        user = self.request.user
        if user.roles.filter(name__in=["ADMIN", "HR"]).exists():
            return LeaveRecord.objects.all()
        return LeaveRecord.objects.filter(employee=user)


# ---------------- Notification ----------------
@csrf_exempt_class
class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsEmployeeSelf | IsHR | IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.roles.filter(name__in=["ADMIN", "HR"]).exists():
            return Notification.objects.all()
        return Notification.objects.filter(employee=user)


# ---------------- Employee Bank Info ----------------
@csrf_exempt_class
class EmployeeBankInfoViewSet(viewsets.ModelViewSet):
    queryset = EmployeeBankInfo.objects.all()
    serializer_class = EmployeeBankInfoSerializer
    permission_classes = [IsAuthenticated, IsFinance | IsAdmin | IsEmployeeSelf]

    def get_queryset(self):
        user = self.request.user
        if user.roles.filter(name__in=["ADMIN", "FINANCE"]).exists():
            return EmployeeBankInfo.objects.all()
        return EmployeeBankInfo.objects.filter(employee=user)


# ---------------- Loan ----------------
@csrf_exempt_class
class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated, IsFinance | IsAdmin | IsEmployeeSelf]

    def get_queryset(self):
        user = self.request.user
        if user.roles.filter(name__in=["ADMIN", "FINANCE"]).exists():
            return Loan.objects.all()
        return Loan.objects.filter(employee=user)

    @action(detail=True, methods=["post"], url_path="approve", permission_classes=[IsFinance | IsAdmin])
    def approve(self, request, pk=None):
        loan = self.get_object()
        loan.status = "APPROVED"
        loan.approved_on = timezone.now().date()
        loan.save()
        return Response({"detail": "Loan approved."})


# ---------------- Expense ----------------
@csrf_exempt_class
class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, IsFinance | IsAdmin | IsEmployeeSelf]

    def get_queryset(self):
        user = self.request.user
        if user.roles.filter(name__in=["ADMIN", "FINANCE"]).exists():
            return Expense.objects.all()
        return Expense.objects.filter(employee=user)

    @action(detail=True, methods=["post"], url_path="approve", permission_classes=[IsFinance | IsAdmin])
    def approve(self, request, pk=None):
        expense = self.get_object()
        expense.status = "APPROVED"
        expense.reviewed_on = timezone.now().date()
        expense.save()
        return Response({"detail": "Expense approved."})


# ---------------- Bulk Payments ----------------
@csrf_exempt_class
class BulkPaymentViewSet(viewsets.ModelViewSet):
    queryset = BulkPaymentLog.objects.all()
    serializer_class = BulkPaymentLogSerializer
    permission_classes = [IsAuthenticated, IsFinance | IsAdmin]

    def perform_create(self, serializer):
        bulk_payment = serializer.save(created_by=self.request.user)
        process_bulk_payment(bulk_payment)


# ---------------- Stripe Integration ----------------
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


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
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
                    payroll.save()

                    # Generate payslip PDF
                    pdf_url = generate_payslip_pdf(payroll)
                    pdf_path = str(Path(settings.MEDIA_ROOT) / pdf_url.replace(settings.MEDIA_URL, ""))

                    Payslip.objects.update_or_create(
                        payroll=payroll,
                        defaults={"payslip_pdf_url": pdf_url}
                    )

                    send_payslip_email(payroll, pdf_path)
                    Notification.objects.create(
                        employee=payroll.employee,
                        message=f"Payroll {payroll_id} has been marked as PAID."
                    )

            except Payroll.DoesNotExist:
                logger.error("Payroll %s not found", payroll_id)

    return HttpResponse(status=200)
