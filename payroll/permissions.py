from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "ADMIN"

class IsFinance(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "FINANCE"

class IsHR(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "HR"

class IsEmployeeSelf(BasePermission):
    """Employee can only view their own payroll/payslip"""
    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and obj.employee == request.user
