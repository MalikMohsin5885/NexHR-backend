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

import os
from .models import JobDetails, JobApplication, CandidateSkill, CandidateExperience, CandidateEducation
from .embeddings import embed_text, cosine_sim, build_candidate_profile_text
from .summarize import summarize_candidate

# from recruitment.tasks import gemini_model

try:
    import google.generativeai as genai
except Exception:
    genai = None

# ✅ Configure Gemini once
api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
if api_key and genai:
    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel("gemini-2.5-flash")  # or "gemini-1.5-flash"
else:
    gemini_model = None


@shared_task
def test_task():
    print("✅ Celery task executed successfully!")
    return "ok"


@shared_task
def send_invitation_email_task(user_email, fname, temp_password):
    print(f"Sending invitation email to {user_email}")
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

def _skills_coverage(job, app):
    req = [s.name.strip().lower() for s in job.required_skills.all()]
    print("Required skills:", req)
    cand_skills = [s.strip().lower() for s in app.skills.values_list("name", flat=True)]
    print("Candidate skills:", cand_skills)

    if not req:
        print("No required skills → returning 1.0")
        return 1.0
    if not cand_skills:
        print("No candidate skills → returning 0.0")
        return 0.0

    matched = 0
    for req_skill in req:
        if req_skill in cand_skills:
            matched += 1
            print(f"✅ Exact match: {req_skill}")
            continue

        prompt = f"The required skill is '{req_skill}'. Candidate has these skills: {cand_skills}. Reply yes or no."
        try:
            if gemini_model:
                resp = gemini_model.generate_content(prompt)
                answer = resp.text.strip().lower()
                print(f"🤖 Gemini response for '{req_skill}':", answer)
                if "yes" in answer:
                    matched += 1
            else:
                print("[SkillMatch] Gemini not configured")
        except Exception as e:
            print(f"[SkillMatch] Gemini error for '{req_skill}': {e}")

    coverage = matched / max(1, len(req))
    print("Matched skills:", matched)
    print("Coverage:", coverage)
    return coverage


# def _experience_score(job: JobDetails, app: JobApplication) -> float:
#     """
#     Compare candidate's total years of experience with job's required experience_level.
#     Returns a score between 0 and 1.
#     """
#     required_years = job.experience_level or 0
#     total_years = 0.0

#     print(f"[DEBUG] Job requires {required_years} years")
#     print(f"[DEBUG] Candidate: {app.candidate_fname} {app.candidate_lname}")

#     for exp in app.experiences.all():
#         try:
#             years = float(exp.years_of_experience)
#             total_years += years
#             print(f"[DEBUG] Added {years} years from {exp.company_name}")
#         except Exception as e:
#             print(f"[ERROR] Invalid years_of_experience for {exp}: {e}")

#     print(f"[DEBUG] Candidate total experience: {total_years}")

#     # Avoid over-influence (cap candidate years to 2× required)
#     if required_years > 0:
#         total_years = min(total_years, required_years * 2)
#     else:
#         return 1.0 if total_years > 0 else 0.0

#     score = max(0.0, min(1.0, total_years / float(required_years)))
#     print(f"[DEBUG] Final experience score: {score}")
#     return score


def _experience_score(job: JobDetails, app: JobApplication) -> float:
    required_years = job.experience_level or 0
    total_years = 0.0

    # Sum candidate experience
    for e in app.experiences.all():
        try:
            total_years += float(e.years_of_experience)
        except Exception:
            pass

    # If no requirement set
    if required_years <= 0:
        return 1.0 if total_years > 0 else 0.0

    # Cap candidate years at 2× required
    total_years = min(total_years, required_years * 2)

    # Ratio
    ratio = total_years / float(required_years)

    # 🔹 Apply tolerance scoring
    if ratio >= 1.0:
        # Fully qualified → full score
        return 1.0
    elif ratio >= 0.8:
        # Almost qualified → 0.7 to 0.9 range
        return 0.7 + (ratio - 0.8) * 1.5  # scales from 0.7 → 1.0
    else:
        # Below 80% → scale normally
        return max(0.0, ratio * 0.8)  # softer penalty




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

    # --- Ensure job has embedding ---
    if job.description_embedding is None:
        print(f"[Screen] Job {job_id} has no embedding; embedding now...")
        embed_job_description(job_id)
        job.refresh_from_db()  # re-fetch updated embedding

    if job.description_embedding is None:
        print(f"[Screen] Job {job_id} still missing embedding, aborting.")
        return

    jd_vec = np.array(job.description_embedding, dtype=float)

    # --- Prefetch related candidate data ---
    apps = JobApplication.objects.filter(job=job).prefetch_related(
        Prefetch("skills", queryset=CandidateSkill.objects.all()),
        Prefetch("experiences", queryset=CandidateExperience.objects.all()),
        Prefetch("educations", queryset=CandidateEducation.objects.all()),
    )

    print(f"[Screen] Starting screening for job {job_id} with {apps.count()} applications")

    for app in apps:
        # --- Ensure candidate embedding ---
        if app.profile_embedding is None:
            embed_application_profile(app.id)
            app.refresh_from_db()

        if app.profile_embedding is None:
            print(f"[Screen] App {app.id} missing embedding, skipping.")
            continue

        cand_vec = np.array(app.profile_embedding, dtype=float)

        # --- Calculate scores ---
        sim = cosine_sim(jd_vec, cand_vec)
        print("embedding similarity---->", sim)
        skills_cov = _skills_coverage(job, app)
        exp_score = _experience_score(job, app)

        final = (W_SIM * sim) + (W_SKILLS * skills_cov) + (W_EXP * exp_score)
        final = max(0.0, min(1.0, final))

        breakdown = {
            "semantic_similarity": round(sim, 4),
            "skills_coverage": round(skills_cov, 4),
            "experience_score": round(exp_score, 4),
            "final_score": round(final, 4),
        }

        # --- Candidate summary (optional) ---
        # if final >= SHORTLIST_THRESHOLD:
        #     candidate_text = build_candidate_profile_text(app)
        #     print("[Screen] Candidate profile text:", candidate_text[:200], "...")
        #     summary = summarize_candidate(
        #         jd_text=(job.description or ""),
        #         candidate_text=candidate_text,
        #         breakdown=breakdown,
        #     )
        #     print("[Screen] Gemini summary generated:", summary[:200], "...")
        # else:
        #     summary = ""
        #     print("[Screen] No summary generated (below threshold)")
        
        candidate_text = build_candidate_profile_text(app)
        print("[Screen] Candidate profile text:", candidate_text[:200], "...")
        summary = summarize_candidate(
            jd_text=(job.description or ""),
            candidate_text=candidate_text,
            breakdown=breakdown,
        )
        print("[Screen] Gemini summary generated:", str(summary)[:200], "...")

        # --- Decide status ---
        new_status = "shortlisted" if final >= SHORTLIST_THRESHOLD else "reviewed"

        # --- Save results atomically ---
        with transaction.atomic():
            app.similarity_score = sim
            app.skills_coverage = skills_cov
            app.experience_score = exp_score
            app.final_score = final
            app.screening_summary = summary
            app.status = new_status
            app.save(update_fields=[
                "similarity_score",
                "skills_coverage",
                "experience_score",
                "final_score",
                "screening_summary",
                "status",
            ])
        print("[Screen] Saved app", app.id, "summary length:", len(summary))

        print(f"[Screen] App {app.id}: sim={sim:.3f}, skills={skills_cov:.2f}, exp={exp_score:.2f}, final={final:.3f}, status={new_status}")

    print(f"[Screen] Completed screening for job {job_id}")




@shared_task
def screen_all_due_jobs():
    """Periodic task: find all jobs whose deadlines have passed and run screening."""
    now = timezone.now()
    due_jobs = JobDetails.objects.filter(job_deadline__lte=now)
    for j in due_jobs.values_list("id", flat=True):
        screen_job_after_deadline.delay(j)

