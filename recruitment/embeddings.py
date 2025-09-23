# apps/recruit/utils/embeddings.py
import numpy as np
from typing import List, Optional
from sentence_transformers import SentenceTransformer

# Use bge-base-en-v1.5 (dim=768) to match your VectorField
_MODEL_NAME = "BAAI/bge-base-en-v1.5"
_model: Optional[SentenceTransformer] = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print("[Embeddings] Loading model:", _MODEL_NAME)
        _model = SentenceTransformer(_MODEL_NAME)
    return _model

def embed_text(text: str) -> List[float]:
    text = (text or "").strip()
    if not text:
        return [0.0] * 768  # safe zero vector
    model = get_model()
    vec = model.encode([text], normalize_embeddings=False)[0]
    return vec.tolist()

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None: 
        return 0.0
    if a.ndim > 1: a = a.ravel()
    if b.ndim > 1: b = b.ravel()
    na = np.linalg.norm(a); nb = np.linalg.norm(b)
    if na == 0 or nb == 0: return 0.0
    return float(np.dot(a, b) / (na * nb))

def build_candidate_profile_text(app) -> str:
    # Compose a single text block (resume_text + cover + form fields + skills + experiences + education)
    parts = []
    if app.resume_text: parts.append(f"Resume:\n{app.resume_text}")
    if app.cover_letter: parts.append(f"Cover Letter:\n{app.cover_letter}")
    # Skills
    skill_names = list(app.skills.values_list("name", flat=True))
    if skill_names: parts.append("Skills: " + ", ".join(skill_names))
    # Experiences
    exps = app.experiences.all()
    if exps:
        exp_lines = [f"{e.previous_job_titles} at {e.company_name} ({e.years_of_experience} years)" for e in exps]
        parts.append("Experience:\n" + "\n".join(exp_lines))
    # Education
    edus = app.educations.all()
    if edus:
        edu_lines = [f"{e.degree_detail} - {e.institution_name} ({e.education_level})" for e in edus]
        parts.append("Education:\n" + "\n".join(edu_lines))
    return "\n\n".join(parts).strip()
