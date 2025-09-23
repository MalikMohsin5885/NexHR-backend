# skill_extractor.py
import re
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional

# -------------------------
# Device helper
# -------------------------
def _get_pipeline_device():
    # pipeline expects device index or -1
    return 0 if torch.cuda.is_available() else -1

# -------------------------
# Load token-classification (skill extraction) pipeline
# -------------------------
def load_skill_extractor(model_name: str = "jjzha/jobbert_skill_extraction", device: Optional[int] = None):
    """
    Loads a HuggingFace token-classification pipeline for skill extraction.
    - model_name: HF model id (default: JobBERT skill extraction).
    - device: 0 for GPU, -1 for CPU; if None auto-detects.
    Returns: transformers.pipeline object
    """
    device = _get_pipeline_device() if device is None else device
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    model = AutoModelForTokenClassification.from_pretrained(model_name)
    # aggregation_strategy='simple' (newer transformers). If your transformers version is older,
    # pipeline may accept grouped_entities=True instead.
    try:
        nlp_pipe = pipeline(
            task="ner",
            model=model,
            tokenizer=tokenizer,
            device=0 if device == 0 else -1,
            aggregation_strategy="simple",  # groups token spans into entities
        )
    except TypeError:
        # fallback for older transformers versions
        nlp_pipe = pipeline(
            task="ner",
            model=model,
            tokenizer=tokenizer,
            device=0 if device == 0 else -1,
            grouped_entities=True,
        )
    return nlp_pipe

# -------------------------
# Extract spans (skills) from text
# -------------------------
def extract_skills_transformer(pipe, text: str, min_score: float = 0.35) -> List[str]:
    """
    Use the token-classification pipeline to extract skill spans.
    Returns a deduplicated, cleaned list of skill phrases (strings).
    """
    if not text or not text.strip():
        return []

    # the pipeline returns grouped entity spans if aggregation_strategy set
    raw = pipe(text)
    skills = []
    for ent in raw:
        score = ent.get("score", ent.get("confidence", 0.0))
        if score < min_score:
            continue
        # new pipeline returns keys: 'entity_group' and 'word' (or 'entity_group'/'score'/'start'/'end')
        word = ent.get("word") or ent.get("entity") or ent.get("wordpiece", "")
        if not word:
            continue
        # clean noisy tokens, punctuation, leading #'s etc
        w = re.sub(r"^[#\s]+|[^\w\-\+\.\/\s]+$", "", word).strip()
        if w:
            skills.append(w)

    # deduplicate while preserving order (case-insensitive)
    seen = set()
    out = []
    for s in skills:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out

# -------------------------
# Normalize / map extracted skills to canonical terms
# -------------------------
def normalize_skills(skills: List[str], mapping: Optional[Dict[str,str]] = None) -> List[str]:
    """
    Lowercases, strips punctuation and maps using provided mapping (synonyms -> canonical).
    mapping example: {'rest apis':'rest', 'rest api':'rest', 'aws':'aws'}
    """
    mapping = mapping or {}
    normalized = []
    for s in skills:
        k = s.lower().strip()
        k = re.sub(r"[^\w\-\+\.\/]+", " ", k).strip()  # remove special chars
        k = " ".join(k.split())  # normalize whitespace
        k = mapping.get(k, k)
        normalized.append(k)
    # dedupe keeping order
    seen = set(); out=[]
    for s in normalized:
        if s not in seen:
            seen.add(s); out.append(s)
    return out

# -------------------------
# Embeddings loader / helper (sentence-transformers)
# -------------------------
def load_sentence_embedder(model_name: str = "BAAI/bge-base-en-v1.5", device: Optional[str] = None):
    """
    Returns a sentence-transformers SentenceTransformer instance.
    device: 'cpu' / 'cuda' or None (auto)
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(model_name, device=device)
    return model

def embed_texts(embedder, texts: List[str], batch_size: int = 8, normalize: bool = False) -> List[List[float]]:
    """
    Embed a list of texts and return list of vectors (python lists).
    """
    if isinstance(texts, str):
        texts = [texts]
    vecs = embedder.encode(texts, batch_size=batch_size, show_progress_bar=False, normalize_embeddings=normalize)
    # convert numpy arrays to python lists if necessary
    return [v.tolist() for v in vecs]
