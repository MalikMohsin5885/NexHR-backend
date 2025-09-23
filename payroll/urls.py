# payroll/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SalaryStructureViewSet, PayrollViewSet, PayslipViewSet,
    AttendanceViewSet, LeaveRecordViewSet, NotificationViewSet,
    EmployeeBankInfoViewSet, LoanViewSet, ExpenseViewSet, BulkPaymentViewSet,
    create_checkout_session, stripe_webhook
)

router = DefaultRouter()
router.register("salary-structures", SalaryStructureViewSet)
router.register("payrolls", PayrollViewSet)
router.register("payslips", PayslipViewSet)
router.register("attendance", AttendanceViewSet)
router.register("leaves", LeaveRecordViewSet)
router.register("notifications", NotificationViewSet)
router.register("bank-info", EmployeeBankInfoViewSet)
router.register("loans", LoanViewSet)
router.register("expenses", ExpenseViewSet)
router.register("bulk-payments", BulkPaymentViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("checkout/<int:payroll_id>/", create_checkout_session, name="create-checkout"),
    path("stripe/webhook/", stripe_webhook, name="stripe-webhook"),
]
