import uuid
from django.db import models
from django.utils import timezone
from accounts.models import User, Company, Branch, Department


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Permission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UserRoles(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_roles")

    class Meta:
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user.name} - {self.role.name}"

class RolePermissions(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_permissions")

    class Meta:
        unique_together = ('role', 'permission')

    def __str__(self):
        return f"{self.role.name} - {self.permission.name}"
    
    
class RequiredSkill(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


class JobDetails(models.Model):
    id = models.AutoField(primary_key=True)
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_jobs')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs')

    job_title = models.CharField(max_length=255)
    # job_category = models.CharField(max_length=100)
    job_type = models.CharField(max_length=50)

    # ✅ Removed choices
    location_type = models.CharField(max_length=50)

    job_deadline = models.DateTimeField()
    location = models.TextField(blank=True)
    city = models.CharField(max_length=100, default='N/A', null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default='N/A', null=True)
    salary_from = models.DecimalField(max_digits=10, decimal_places=2)
    salary_to = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    period = models.CharField(max_length=50)  # e.g., Monthly, Annually
    description = models.TextField(max_length=500, null=True)
    requirements = models.TextField(max_length=500, null=True)
    status = models.CharField(max_length=50)

    # ✅ Removed choices
    experience_level = models.CharField(max_length=50)

    job_schema = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.job_title} at {self.company.name}"


class JobDetailSkill(models.Model):
    job = models.ForeignKey(JobDetails, on_delete=models.CASCADE, related_name='required_skills')
    required_skill = models.ForeignKey(RequiredSkill, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    


# Applications to jobs
class JobApplication(models.Model):
    id = models.AutoField(primary_key=True)
    job = models.ForeignKey(JobDetails, on_delete=models.CASCADE, related_name='applications')
    candidate_fname = models.CharField(max_length=255)
    candidate_lname = models.CharField(max_length=255, null=True)
    email = models.EmailField(null=True)
    phone = models.CharField(max_length=20, null=True)
    resume_url = models.TextField()

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('shortlisted', 'Shortlisted'),
        ('rejected', 'Rejected'),
        ('accepted', 'Accepted'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    applied_at = models.DateTimeField(default=timezone.now)
    gender = models.CharField(max_length=20)
    address = models.TextField()
    dob = models.DateField()
    cover_letter = models.TextField(null=True)

    def __str__(self):
        return f"{self.candidate_fname} {self.candidate_lname}"


# Candidate skills per application
class CandidateSkill(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    application_id = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name='skills')


# Candidate experience
class CandidateExperience(models.Model):
    id = models.AutoField(primary_key=True)
    application_id = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name='experiences')
    years_of_experience = models.DecimalField(max_digits=4, decimal_places=1)
    previous_job_titles = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)


# Candidate education
class CandidateEducation(models.Model):
    id = models.AutoField(primary_key=True)
    application_id = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name='educations')
    education_level = models.CharField(max_length=100)
    institution_name = models.CharField(max_length=255)
    degree_detail = models.CharField(max_length=255)
    grades = models.CharField(max_length=255)  # You may want to rename `cops` if this is a typo
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField()


# class FormField(models.Model):
#     FIELD_TYPES = (
#         ('text', 'Text'),
#         ('email', 'Email'),
#         ('number', 'Number'),
#         ('date', 'Date'),
#         ('file', 'File Upload'),
#         ('textarea', 'Textarea'),
#     )

#     id = models.AutoField(primary_key=True)
#     job = models.ForeignKey(JobDetails, on_delete=models.CASCADE, related_name='form_fields')
#     label = models.CharField(max_length=255)
#     field_type = models.CharField(max_length=50, choices=FIELD_TYPES)
#     field_key = models.SlugField()  # unique field name like `full_name`, `dob`
#     is_required = models.BooleanField(default=False)
#     order = models.PositiveIntegerField()

#     def __str__(self):
#         return f"{self.job.job_title} - {self.label}"



# class CandidateApplication(models.Model):
#     STATUS_CHOICES = (
#         ('pending', 'Pending'),
#         ('reviewed', 'Reviewed'),
#         ('shortlisted', 'Shortlisted'),
#         ('rejected', 'Rejected'),
#     )

#     id = models.AutoField(primary_key=True)
#     job = models.ForeignKey(JobDetails, on_delete=models.CASCADE, related_name='applications')
#     applied_at = models.DateTimeField(auto_now_add=True)
#     status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')

#     def __str__(self):
#         return f"Application for {self.job.job_title}"



# class CandidateFieldResponse(models.Model):
#     id = models.AutoField(primary_key=True)
#     application = models.ForeignKey(CandidateApplication, on_delete=models.CASCADE, related_name='field_responses')
#     field = models.ForeignKey(FormField, on_delete=models.CASCADE)
#     response = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return f"Response to {self.field.label}"



# class CandidateExperience(models.Model):
#     id = models.AutoField(primary_key=True)
#     application = models.ForeignKey(CandidateApplication, on_delete=models.CASCADE, related_name='experiences')
#     company_name = models.CharField(max_length=255)
#     job_title = models.CharField(max_length=255)
#     start_date = models.DateField()
#     end_date = models.DateField(blank=True, null=True)
#     description = models.TextField(blank=True)

#     def __str__(self):
#         return f"{self.job_title} at {self.company_name}"



# class CandidateEducation(models.Model):
#     id = models.AutoField(primary_key=True)
#     application = models.ForeignKey(CandidateApplication, on_delete=models.CASCADE, related_name='educations')
#     institution_name = models.CharField(max_length=255)
#     degree = models.CharField(max_length=255)
#     field_of_study = models.CharField(max_length=255)
#     start_date = models.DateField()
#     end_date = models.DateField(blank=True, null=True)
#     description = models.TextField(blank=True)

#     def __str__(self):
#         return f"{self.degree} at {self.institution_name}"




