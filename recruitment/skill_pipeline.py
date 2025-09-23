# skill_pipeline.py
import os
import re
import numpy as np
import torch
from typing import List, Dict, Optional
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from sentence_transformers import SentenceTransformer, util

# -------------------------
# DEVICE
# -------------------------
def _get_device_index():
    return 0 if torch.cuda.is_available() else -1

def _get_device_str():
    return "cuda" if torch.cuda.is_available() else "cpu"

# -------------------------
# SKILL EXTRACTION PIPELINE
# -------------------------
def load_skill_extractor(model_name: str = "jjzha/jobbert_skill_extraction", device: Optional[int] = None):
    device = _get_device_index() if device is None else device
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    model = AutoModelForTokenClassification.from_pretrained(model_name)

    try:
        nlp_pipe = pipeline(
            task="ner",
            model=model,
            tokenizer=tokenizer,
            device=device,
            aggregation_strategy="simple",
        )
    except TypeError:
        nlp_pipe = pipeline(
            task="ner",
            model=model,
            tokenizer=tokenizer,
            device=device,
            grouped_entities=True,
        )
    return nlp_pipe

def extract_skills(pipe, text: str, min_score: float = 0.35) -> List[str]:
    """Extract raw skill phrases from text using transformer NER."""
    if not text or not text.strip():
        return []

    raw = pipe(text)
    skills = []
    for ent in raw:
        score = ent.get("score", ent.get("confidence", 0.0))
        if score < min_score:
            continue
        word = ent.get("word") or ent.get("entity") or ""
        if not word:
            continue
        w = re.sub(r"^[#\s]+|[^\w\-\+\.\/\s]+$", "", word).strip()
        if w:
            skills.append(w)

    # deduplicate
    seen = set(); out=[]
    for s in skills:
        k = s.lower()
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out

# -------------------------
# EMBEDDINGS
# -------------------------
def load_embedder(model_name: str = "BAAI/bge-base-en-v1.5"):
    return SentenceTransformer(model_name, device=_get_device_str())

def embed_texts(embedder, texts: List[str], normalize: bool = True) -> np.ndarray:
    if isinstance(texts, str):
        texts = [texts]
    vecs = embedder.encode(texts, convert_to_numpy=True, normalize_embeddings=normalize, show_progress_bar=False)
    return vecs

# -------------------------
# ONTOLOGY LOADING
# -------------------------
def load_ontology_skills(file_path: str = "data/esco_skills.txt") -> List[str]:
    """Load ontology skills list (e.g., ESCO). One skill per line."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Ontology skills file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        skills = [line.strip() for line in f if line.strip()]
    return skills

# def normalize_skills_with_ontology(raw_skills: List[str], embedder, ontology_skills: List[str], ontology_vecs: np.ndarray, threshold: float = 0.7) -> List[str]:
#     """Map extracted skills to closest ontology skills."""
#     if not raw_skills:
#         return []
#     raw_vecs = embed_texts(embedder, raw_skills)

#     normalized = []
#     for skill, s_emb in zip(raw_skills, raw_vecs):
#         sims = util.cos_sim(s_emb, ontology_vecs)[0]
#         best_idx = int(torch.argmax(sims))
#         best_score = float(sims[best_idx])
#         if best_score >= threshold:
#             normalized.append(ontology_skills[best_idx])
#         else:
#             normalized.append(skill)  # fallback
#     # dedupe
#     seen=set(); out=[]
#     for s in normalized:
#         if s not in seen:
#             seen.add(s); out.append(s)
#     return out


def normalize_skills_with_ontology(extracted, embedder, ontology_skills, ontology_vecs, top_k=3, threshold=0.6):
    normalized = []
    for skill in extracted:
        vec = embedder.encode([skill])[0]
        sims = np.dot(ontology_vecs, vec) / (np.linalg.norm(ontology_vecs, axis=1) * np.linalg.norm(vec))
        top_idx = np.argsort(-sims)[:top_k]
        for idx in top_idx:
            if sims[idx] >= threshold:
                normalized.append(ontology_skills[idx])
    return list(set(normalized))
