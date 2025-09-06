from django.db import models
from django.conf import settings


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


class Payroll(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payrolls"
    )
    salary_structure = models.ForeignKey(
        SalaryStructure, on_delete=models.SET_NULL, null=True, blank=True
    )
    period_start = models.DateField()
    period_end = models.DateField()
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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
    payslip_pdf_url = models.URLField(null=True, blank=True)
    issued_on = models.DateField(auto_now_add=True)

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
    leave_type = models.CharField(max_length=50)  # "UNPAID", "SICK", etc.
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
