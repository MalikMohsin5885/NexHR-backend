from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SalaryStructureViewSet, PayrollViewSet, PayslipViewSet,
    AttendanceViewSet, LeaveRecordViewSet, NotificationViewSet, 
    create_checkout_session, stripe_webhook,
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
    path("<int:payroll_id>/checkout/", create_checkout_session, name="stripe-checkout"),
    path("webhook/stripe/", stripe_webhook, name="stripe-webhook"),
    

]
