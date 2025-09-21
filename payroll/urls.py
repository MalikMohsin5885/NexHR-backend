from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SalaryStructureViewSet, PayrollViewSet, PayslipViewSet,
    AttendanceViewSet, LeaveRecordViewSet, NotificationViewSet, 
    create_checkout_session, stripe_webhook, confirm_checkout,
)

router = DefaultRouter()
router.register(r'salary-structures', SalaryStructureViewSet)
router.register(r'payrolls', PayrollViewSet)
router.register(r'payslips', PayslipViewSet)
router.register(r'attendance', AttendanceViewSet)
router.register(r'leaves', LeaveRecordViewSet)
router.register(r'notifications', NotificationViewSet)

urlpatterns = [
    path("", include(router.urls)),
    # checkout session (create)
    path("<int:payroll_id>/checkout/", create_checkout_session, name="stripe-checkout"),
    # confirm-checkout for immediate processing after redirect
    path("confirm-checkout/", confirm_checkout, name="confirm-checkout"),
    # stripe webhook endpoint
    path("stripe/webhook/", stripe_webhook, name="stripe-webhook"),
]
