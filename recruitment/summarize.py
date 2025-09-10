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
    print("[Gemini] API key present:", bool(api_key))
    print("[Gemini] API key value (first 6 chars):", api_key[:6] if api_key else "None")

    if not api_key or genai is None:
        print("[Gemini] Not configured → returning fallback summary")
        return (
            "Summary unavailable (Gemini not configured).\n"
            f"Breakdown: {breakdown}"
        )

    try:
        genai.configure(api_key=api_key)
        print("[Gemini] Configured client successfully")

        prompt = (
            f"{_SYS_PROMPT}\n\n"
            f"JD:\n{jd_text}\n\n"
            f"Candidate Profile:\n{candidate_text}\n\n"
            f"Score Breakdown (0..1): {breakdown}\n\n"
            f"Write the summary now."
        )
        print("[Gemini] Sending prompt...")
        print("[Gemini] Prompt (first 300 chars):", prompt[:300])

        model = genai.GenerativeModel("gemini-2.5-flash")
        resp = model.generate_content(prompt)

        print("[Gemini] Response received:", resp)
        print("[Gemini] Response text:", getattr(resp, "text", None))

        return (resp.text or "").strip()
    except Exception as e:
        print("[Gemini] ERROR:", e)
        return f"Summary generation error: {e}\nBreakdown: {breakdown}"
