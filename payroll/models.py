from django.db import models
from django.conf import settings
from decimal import Decimal


class SalaryStructure(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="salary_structures"
    )
    basic_pay = models.DecimalField(max_digits=10, decimal_places=2)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Salary Structure for {self.employee.email}"


class TaxBracket(models.Model):
    min_income = models.DecimalField(max_digits=12, decimal_places=2)
    max_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    rate = models.DecimalField(max_digits=5, decimal_places=2)  # %

    def __str__(self):
        return f"{self.min_income} - {self.max_income or '∞'} @ {self.rate}%"


class StatutoryDeduction(models.Model):
    name = models.CharField(max_length=100)
    rate = models.DecimalField(max_digits=5, decimal_places=2)  # %
    is_mandatory = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class Payroll(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payrolls"
    )
    salary_structure = models.ForeignKey(
        SalaryStructure, on_delete=models.SET_NULL, null=True, blank=True
    )
    period_start = models.DateField()
    period_end = models.DateField()
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    statutory_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(
        max_length=20,
        choices=[("PENDING", "Pending"), ("PAID", "Paid"), ("FAILED", "Failed")],
        default="PENDING",
    )
    paid_on = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Payroll for {self.employee.email} ({self.period_start} - {self.period_end})"


class Payslip(models.Model):
    payroll = models.OneToOneField(Payroll, on_delete=models.CASCADE, related_name="payslip")
    issued_on = models.DateField(auto_now_add=True)
    payslip_pdf_url = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Payslip for {self.payroll}"


class EmployeeAttendance(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendances"
    )
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    work_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    photo = models.ImageField(upload_to="attendance_photos/", null=True, blank=True)
    geo_location = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.employee.email} - {self.date}"


class LeaveRecord(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leaves"
    )
    leave_type = models.CharField(max_length=50)
    from_date = models.DateField()
    to_date = models.DateField()
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leaves",
    )
    status = models.CharField(
        max_length=20,
        choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")],
        default="PENDING",
    )

    def __str__(self):
        return f"{self.employee.email} - {self.leave_type} ({self.status})"


class Notification(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.employee.email}"


# ---------------- FINANCE EXTENSIONS ----------------

class EmployeeBankInfo(models.Model):
    employee = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bank_info")
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=34)
    routing_number = models.CharField(max_length=20, blank=True, null=True)
    stripe_account_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.employee.email} - {self.bank_name}"


class Loan(models.Model):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loans")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    remaining_balance = models.DecimalField(max_digits=12, decimal_places=2)
    installment = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("CLOSED", "Closed")],
        default="PENDING"
    )
    requested_on = models.DateField(auto_now_add=True)
    approved_on = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Loan {self.id} for {self.employee.email} - {self.status}"


class Expense(models.Model):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expenses")
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=100, default="General")
    receipt = models.ImageField(upload_to="expense_receipts/", null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")],
        default="PENDING"
    )
    submitted_on = models.DateField(auto_now_add=True)
    reviewed_on = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Expense {self.title} - {self.status}"

class BulkPaymentLog(models.Model):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    period_start = models.DateField()
    period_end = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=[("PROCESSING", "Processing"), ("COMPLETED", "Completed"), ("FAILED", "Failed")],
        default="PROCESSING"
    )

    def __str__(self):
        return f"Bulk Payment {self.id} ({self.status})"
