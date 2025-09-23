# test_screening.py
import re
import numpy as np

# Import our skill pipeline
from skill_pipeline import (
    load_skill_extractor,
    extract_skills,
    load_embedder,
    embed_texts,
    load_ontology_skills,
    normalize_skills_with_ontology,
)

# ============================================================
# CONFIG
# ============================================================
W_SIM = 0.50
W_SKILLS = 0.30
W_EXP = 0.20
SHORTLIST_THRESHOLD = 0.65

# ============================================================
# MODELS (load once at start)
# ============================================================
print("[INIT] Loading models...")

skill_pipe = load_skill_extractor("jjzha/jobbert_skill_extraction")
embedder = load_embedder("BAAI/bge-base-en-v1.5")


# Load ESCO skills ontology
print("[INIT] Loading ontology skills...")
ontology_skills = load_ontology_skills("data/esco_skills.txt")
ontology_vecs = embed_texts(embedder, ontology_skills)
print(f"[INIT] Loaded {len(ontology_skills)} ontology skills from ESCO")

print("[INIT] Models + ontology loaded successfully!")

# ============================================================
# HELPERS
# ============================================================
def extract_required_years(text: str) -> int:
    """Extract minimum years of experience from JD text."""
    match = re.search(r"(\d+)\s+years?", text.lower())
    return int(match.group(1)) if match else 0


def cosine_sim(vec1, vec2) -> float:
    """Cosine similarity between two vectors."""
    v1 = np.array(vec1, dtype=float)
    v2 = np.array(vec2, dtype=float)
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))


def skills_coverage(required: list, cand_skills: list) -> float:
    """How many required JD skills are covered by candidate."""
    if not required:
        return 1.0
    cand_lower = [s.lower() for s in cand_skills]
    matched = sum(1 for s in required if s.lower() in cand_lower)
    return matched / len(required)


def experience_score(min_years: int, cand_years: int) -> float:
    """Scale candidate experience against requirement."""
    if min_years <= 0:
        return 1.0 if cand_years > 0 else 0.0
    return min(1.0, cand_years / float(min_years))


def pretty_vec(vec, max_len=10):
    arr = np.array(vec, dtype=float).tolist()
    preview = ", ".join(f"{x:.4f}" for x in arr[:max_len])
    if len(arr) > max_len:
        preview += ", ..."
    return f"[{preview}] (len={len(arr)})"

# ============================================================
# TEST DATA
# ============================================================
JOB_DESCRIPTION = """
We are looking for a Software Engineer with experience in Python, Django, and REST APIs.
The candidate should be able to work with databases, write clean code, and collaborate with teams.
Experience with cloud platforms (AWS/GCP) is a plus.
"""

RESUMES = [
    {
        "name": "Alice Johnson",
        "text": """
        Experienced Software Engineer with 4 years in Python and Django development.
        Built REST APIs, worked with PostgreSQL and MySQL databases, and deployed apps to AWS.
        Skilled in team collaboration and agile methodologies.
        """
    },
    {
        "name": "Bob Smith",
        "text": """
        Full-stack developer with JavaScript, React, and Node.js expertise.
        Basic knowledge of Python scripting and some experience with REST APIs.
        Familiar with SQL databases but not much cloud exposure.
        """
    },
    {
        "name": "Charlie Brown",
        "text": """
        Marketing specialist with 5 years of experience in digital campaigns, SEO, and analytics.
        Strong communication and project management skills but no programming background.
        """
    },
    {
        "name": "Diana Prince",
        "text": """
        Certified yoga instructor with 6 years of experience in fitness training, nutrition coaching,
        and wellness program design. Passionate about healthy living.
        """
    },
    {
        "name": "Ethan Lee",
        "text": """
        Data analyst with 3 years of experience using Python for data cleaning and visualization.
        Worked with SQL databases and created dashboards. Limited web development exposure.
        """
    },
]

# ============================================================
# MAIN SCREENING
# ============================================================
def run_screening():
    print("\n[DEBUG] Starting screening flow")
    print("[DEBUG] Job Description:\n", JOB_DESCRIPTION.strip())

    # ---- JD embedding ----
    print("\n[DEBUG] Embedding job description...")
    jd_vec = embed_texts(embedder, [JOB_DESCRIPTION])[0]
    print("[DEBUG] JD embedding vector:", pretty_vec(jd_vec))

    # ---- JD Skills + Years ----
    jd_skills_raw = extract_skills(skill_pipe, JOB_DESCRIPTION)
    jd_skills = normalize_skills_with_ontology(jd_skills_raw, embedder, ontology_skills, ontology_vecs)
    min_years = extract_required_years(JOB_DESCRIPTION)
    print(f"[DEBUG] Extracted raw JD skills: {jd_skills_raw}")
    print(f"[DEBUG] Normalized JD skills (ontology): {jd_skills}")
    print(f"[DEBUG] Extracted min years of exp: {min_years}")

    for cand in RESUMES:
        print("\n" + "="*60)
        print(f"[DEBUG] Processing candidate: {cand['name']}")

        candidate_text = cand["text"].strip()
        print("[DEBUG] Candidate text preview:", candidate_text[:200], "...")

        # Embedding
        cand_vec = embed_texts(embedder, [candidate_text])[0]
        print("[DEBUG] Candidate embedding vector:", pretty_vec(cand_vec))

        # Candidate skills
        cand_skills_raw = extract_skills(skill_pipe, candidate_text)
        cand_skills = normalize_skills_with_ontology(cand_skills_raw, embedder, ontology_skills, ontology_vecs)
        print(f"[DEBUG] Extracted raw skills: {cand_skills_raw}")
        print(f"[DEBUG] Normalized skills (ontology): {cand_skills}")

        # Similarity
        sim = cosine_sim(jd_vec, cand_vec)
        print(f"[DEBUG] Similarity score: {sim:.4f}")

        # Skills coverage
        skills_cov = skills_coverage(jd_skills, cand_skills)
        print(f"[DEBUG] Skills coverage: {skills_cov:.4f}")

        # Experience score (still placeholder since resumes not parsed)
        exp_score = experience_score(min_years, 0)
        print(f"[DEBUG] Experience score: {exp_score:.4f}")

        # Final score
        final = (W_SIM * sim) + (W_SKILLS * skills_cov) + (W_EXP * exp_score)
        final = max(0.0, min(1.0, final))
        print(f"[DEBUG] Final weighted score: {final:.4f}")

        breakdown = {
            "semantic_similarity": round(sim, 4),
            "skills_coverage": round(skills_cov, 4),
            "experience_score": round(exp_score, 4),
            "final_score": round(final, 4),
        }
        print("[DEBUG] Breakdown dict:", breakdown)

        # Decision
        status = "shortlisted" if final >= SHORTLIST_THRESHOLD else "reviewed"
        print(f"[DEBUG] Final decision → {cand['name']} = {status.upper()}")

    print("\n[DEBUG] Screening completed!")

# ============================================================
if __name__ == "__main__":
    run_screening()
