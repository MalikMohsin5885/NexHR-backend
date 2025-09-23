# payroll/permissions.py
from rest_framework.permissions import BasePermission

class RolePermission(BasePermission):
    """Generic helper for role-based checks."""
    allowed_roles = []

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.roles.filter(name__in=self.allowed_roles).exists()


class IsAdmin(RolePermission):
    allowed_roles = ["ADMIN"]


class IsFinance(RolePermission):
    allowed_roles = ["FINANCE"]


class IsHR(RolePermission):
    allowed_roles = ["HR"]


class IsEmployeeSelf(BasePermission):
    """Employee can only view their own object (payroll, payslip, etc)."""

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and getattr(obj, "employee", None) == request.user
