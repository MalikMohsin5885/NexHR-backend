# apps/recruit/utils/summarize.py
import os
from django.conf import settings

try:
    import google.generativeai as genai
except Exception:
    genai = None

_SYS_PROMPT = """You are an assistant that writes concise HR screening summaries.
Given the Job Description (JD), a candidate profile, and a score breakdown,
write 4-7 bullet points: top strengths, skill matches, gaps, experience fit,
and any risks. Avoid fluff and keep it factual.
"""

def summarize_candidate(jd_text: str, candidate_text: str, breakdown: dict) -> str:
    api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    if not api_key or genai is None:
        # Fallback plain string if Gemini not configured
        return (
            "Summary unavailable (Gemini not configured).\n"
            f"Breakdown: {breakdown}"
        )
    genai.configure(api_key=api_key)
    prompt = (
        f"{_SYS_PROMPT}\n\n"
        f"JD:\n{jd_text}\n\n"
        f"Candidate Profile:\n{candidate_text}\n\n"
        f"Score Breakdown (0..1): {breakdown}\n\n"
        f"Write the summary now."
    )
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")  # fast & cheap for summaries
        resp = model.generate_content(prompt)
        return (resp.text or "").strip()
    except Exception as e:
        return f"Summary generation error: {e}\nBreakdown: {breakdown}"
