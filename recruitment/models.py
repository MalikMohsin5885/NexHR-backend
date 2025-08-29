from django.db import models
from accounts.models import User, Company, Branch, Department
from django.utils import timezone
from pgvector.django import VectorField


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
    job_type = models.CharField(max_length=50)

    location_type = models.CharField(max_length=50) # e.g., Remote, On-site, Hybrid

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
    status = models.CharField(max_length=50)

    experience_level = models.CharField(max_length=50)
    # Store embeddings of job description
    description_embedding = VectorField(dimensions=768, null=True)  
    # (dim depends on the model, e.g. all-MiniLM-L6-v2 → 384, bge-large → 1024, OpenAI → 1536)

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
    
    # Store extracted plain text from resume for quick ref
    resume_text = models.TextField(blank=True, null=True)

    # Embedding of candidate profile (resume + cover letter + form fields)
    profile_embedding = VectorField(dimensions=768, null=True)

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

