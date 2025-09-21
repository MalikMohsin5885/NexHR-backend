from rest_framework import serializers
from .models import (
    SalaryStructure, Payroll, Payslip,
    EmployeeAttendance, LeaveRecord, Notification,
    TaxBracket, StatutoryDeduction
)


class SalaryStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryStructure
        fields = "__all__"


class PayrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payroll
        fields = "__all__"
        read_only_fields = ("paid_on", "paid_by", "approval_status", "approved_by", "tax_amount", "statutory_deductions")


class PayslipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payslip
        fields = "__all__"


class EmployeeAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeAttendance
        fields = "__all__"


class LeaveRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRecord
        fields = "__all__"


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"


class TaxBracketSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxBracket
        fields = "__all__"


class StatutoryDeductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatutoryDeduction
        fields = "__all__"
