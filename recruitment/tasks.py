# api/tasks.py
from __future__ import annotations
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

# apps/recruit/tasks.py
from django.utils import timezone
from django.db import transaction
from django.db.models import Prefetch
from typing import List, Tuple
import numpy as np

from .models import JobDetails, JobApplication, CandidateSkill, CandidateExperience, CandidateEducation
from .embeddings import embed_text, cosine_sim, build_candidate_profile_text
from .summarize import summarize_candidate

@shared_task
def send_invitation_email_task(user_email, fname, temp_password):
    subject = "Welcome to NexHR - Your Account Details"
    message = f"""Hi {fname},

Your NexHR account has been created.

Login Email: {user_email}
Temporary Password: {temp_password}

Please log in and change your password as soon as possible.

Thanks,
NexHR Team
"""
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user_email],
        fail_silently=False,
    )
    
    

# ---- weights/thresholds you can tune
W_SIM = 0.50
W_SKILLS = 0.30
W_EXP = 0.20
SHORTLIST_THRESHOLD = 0.65   # final_score >= shortlist → mark as shortlisted

def _skills_coverage(job: JobDetails, app: JobApplication) -> float:
    # Expecting required skills in job.job_schema["requirements"]["skills"] or job.job_schema["must_have_skills"]
    req = []
    js = job.job_schema or {}
    # try some common keys
    for k in ("requirements", "must_have_skills", "required_skills"):
        v = js.get(k)
        if isinstance(v, list): req = v; break
        if isinstance(v, dict) and "skills" in v and isinstance(v["skills"], list):
            req = v["skills"]; break
    req = [s.strip().lower() for s in req if isinstance(s, str)]
    if not req: 
        return 1.0  # if no explicit required skills, treat as full coverage

    cand_skills = [s.strip().lower() for s in app.skills.values_list("name", flat=True)]
    if not cand_skills: 
        return 0.0
    matched = sum(1 for s in req if s in cand_skills)
    return matched / max(1, len(req))

def _experience_score(job: JobDetails, app: JobApplication) -> float:
    # compare candidate total yrs vs job.experience_level (int, expected min years)
    min_years = job.experience_level or 0
    years = 0.0
    for e in app.experiences.all():
        try:
            years += float(e.years_of_experience)
        except Exception:
            pass
    # cap to avoid over-influence
    years = min(years, min_years * 2 if min_years > 0 else years)
    if min_years <= 0:
        return 1.0 if years > 0 else 0.0
    # simple ratio, clip to [0,1]
    return max(0.0, min(1.0, years / float(min_years)))

@shared_task
def embed_job_description(job_id: int):
    try:
        job = JobDetails.objects.get(id=job_id)
        print("embed_job_description")
    except JobDetails.DoesNotExist:
        print(f"[Embed JD] Job {job_id} not found")
        return
    text = (job.description or "").strip()
    if not text:
        print(f"[Embed JD] Job {job_id} has empty description")
        return
    vec = embed_text(text)
    job.description_embedding = vec
    job.save(update_fields=["description_embedding"])
    print(f"[Embed JD] Embedded job {job_id}")

@shared_task
def embed_application_profile(app_id: int):
    try:
        app = JobApplication.objects.prefetch_related("skills", "experiences", "educations").get(id=app_id)
    except JobApplication.DoesNotExist:
        print(f"[Embed App] Application {app_id} not found")
        return
    profile_text = build_candidate_profile_text(app)
    vec = embed_text(profile_text)
    app.profile_embedding = vec
    app.save(update_fields=["profile_embedding"])
    print(f"[Embed App] Embedded application {app_id}")

@shared_task
def screen_job_after_deadline(job_id: int):
    """Run screening for a single job, ONLY if deadline passed."""
    try:
        job = JobDetails.objects.get(id=job_id)
    except JobDetails.DoesNotExist:
        print(f"[Screen] Job {job_id} not found")
        return

    now = timezone.now()
    if not job.job_deadline or now < job.job_deadline:
        print(f"[Screen] Job {job_id} not screened (deadline not reached)")
        return

    if job.description_embedding is None:
        print(f"[Screen] Job {job_id} has no embedding; embedding now...")
        embed_job_description(job_id)

    jd_vec = np.array(job.description_embedding or [0.0]*768, dtype=float)

    apps = JobApplication.objects.filter(job=job).prefetch_related(
        Prefetch("skills", queryset=CandidateSkill.objects.all()),
        Prefetch("experiences", queryset=CandidateExperience.objects.all()),
        Prefetch("educations", queryset=CandidateEducation.objects.all()),
    )

    print(f"[Screen] Starting screening for job {job_id} with {apps.count()} applications")

    for app in apps:
        if app.profile_embedding is None:
            embed_application_profile(app.id)

        cand_vec = np.array(app.profile_embedding or [0.0]*768, dtype=float)
        sim = cosine_sim(jd_vec, cand_vec)
        skills_cov = _skills_coverage(job, app)
        exp_score = _experience_score(job, app)

        final = (W_SIM * sim) + (W_SKILLS * skills_cov) + (W_EXP * exp_score)
        final = max(0.0, min(1.0, final))

        # Build a short breakdown for summary
        breakdown = {
            "semantic_similarity": round(sim, 4),
            "skills_coverage": round(skills_cov, 4),
            "experience_score": round(exp_score, 4),
            "final_score": round(final, 4),
        }

        # Optional Gemini summary (only if final >= threshold to save tokens)
        candidate_text = ""
        if final >= SHORTLIST_THRESHOLD:
            candidate_text = build_candidate_profile_text(app)
            summary = summarize_candidate(
                jd_text=(job.description or ""),
                candidate_text=candidate_text,
                breakdown=breakdown,
            )
        else:
            summary = ""

        # Decide status
        new_status = "shortlisted" if final >= SHORTLIST_THRESHOLD else "reviewed"

        with transaction.atomic():
            app.similarity_score = sim
            app.skills_coverage = skills_cov
            app.experience_score = exp_score
            app.final_score = final
            app.screening_summary = summary
            app.status = new_status
            app.save(update_fields=[
                "similarity_score","skills_coverage","experience_score",
                "final_score","screening_summary","status"
            ])

        # Minimal logging
        print(f"[Screen] App {app.id}: sim={sim:.3f}, skills={skills_cov:.2f}, exp={exp_score:.2f}, final={final:.3f}, status={new_status}")

    print(f"[Screen] Completed screening for job {job_id}")

@shared_task
def screen_all_due_jobs():
    """Periodic task: find all jobs whose deadlines have passed and run screening."""
    now = timezone.now()
    due_jobs = JobDetails.objects.filter(job_deadline__lte=now)
    for j in due_jobs.values_list("id", flat=True):
        screen_job_after_deadline.delay(j)

