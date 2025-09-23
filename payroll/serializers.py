# payroll/serializers.py
from rest_framework import serializers
from .models import (
    SalaryStructure, Payroll, Payslip,
    EmployeeAttendance, LeaveRecord, Notification,
    EmployeeBankInfo, Loan, Expense, BulkPaymentLog,
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


# Finance extensions
class EmployeeBankInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeBankInfo
        fields = "__all__"


class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = "__all__"
        read_only_fields = ["status", "approved_on", "requested_on", "employee"]


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = "__all__"
        read_only_fields = ["status", "reviewed_on", "employee"]


class BulkPaymentLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkPaymentLog
        fields = "__all__"
        read_only_fields = ["created_by", "status", "created_on"]


class TaxBracketSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxBracket
        fields = "__all__"


class StatutoryDeductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatutoryDeduction
        fields = "__all__"
