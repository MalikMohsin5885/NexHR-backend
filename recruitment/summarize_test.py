import os
import json
import time
from django.conf import settings

try:
    import google.generativeai as genai
except Exception:
    genai = None

_SYS_PROMPT = """You are an assistant that writes concise HR screening summaries in JSON only.
Given the Job Description (JD), a candidate profile, and a score breakdown,
output a JSON object with the following keys:

{
  "strengths": [list of top strengths],
  "skill_matches": [list of skills the candidate matches],
  "gaps": [list of missing skills or gaps],
  "experience_fit": [short summary of experience fit],
  "risks": [list of potential risks],
  "score_alignment": "short statement summarizing score alignment"
}

Rules:
- Respond ONLY with valid JSON (no markdown, no extra text).
- Keep lists factual and concise (max 3–5 items each).
"""


def _call_gemini_with_retry(model, prompt, retries=3, base_delay=20):
    """
    Call Gemini API with retry logic for 429 quota errors.
    Exponential backoff: base_delay, 2*base_delay, 3*base_delay...
    """
    for attempt in range(1, retries + 1):
        try:
            resp = model.generate_content(prompt)
            return resp
        except Exception as e:
            err_str = str(e)
            if "429" in err_str and attempt < retries:
                wait_time = base_delay * attempt
                print(f"[Gemini] Quota exceeded. Retrying in {wait_time}s (attempt {attempt}/{retries})...")
                time.sleep(wait_time)
                continue
            raise  # re-raise other errors or last attempt failure


def summarize_candidate(jd_text: str, candidate_text: str, breakdown: dict, skills: list = None):
    """
    Generates a structured JSON summary of candidate vs JD using Gemini API.
    Now does skill-matching in a single batched request instead of one per skill.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    print("[Gemini] API key present:", bool(api_key))
    print("[Gemini] API key value (first 6 chars):", api_key[:6] if api_key else "None")

    if not api_key or genai is None:
        print("[Gemini] Not configured → returning fallback summary")
        return {
            "strengths": [],
            "skill_matches": [],
            "gaps": [],
            "experience_fit": "Summary unavailable (Gemini not configured).",
            "risks": [],
            "score_alignment": f"Breakdown: {breakdown}"
        }

    try:
        genai.configure(api_key=api_key)
        print("[Gemini] Configured client successfully")

        # Include skills in the prompt if provided
        skills_text = f"\n\nSkills to check against candidate: {skills}" if skills else ""

        prompt = (
            f"{_SYS_PROMPT}\n\n"
            f"JD:\n{jd_text}\n\n"
            f"Candidate Profile:\n{candidate_text}\n\n"
            f"Score Breakdown (0..1): {breakdown}\n"
            f"{skills_text}\n\n"
            f"Write the summary now."
        )

        print("[Gemini] Sending prompt...")
        print("[Gemini] Prompt (first 300 chars):", prompt[:300])

        model = genai.GenerativeModel("gemini-2.5-flash")
        resp = _call_gemini_with_retry(model, prompt)

        raw_text = (resp.text or "").strip()
        print("[Gemini] Response text:", raw_text[:300])

        # ✅ Try to parse JSON
        try:
            parsed = json.loads(raw_text)
            return parsed
        except Exception as e:
            print("[Gemini] JSON parse failed:", e)
            return {
                "strengths": [],
                "skill_matches": [],
                "gaps": [],
                "experience_fit": "Parsing failed, see raw_summary.",
                "risks": [],
                "score_alignment": f"Breakdown: {breakdown}",
                "raw_summary": raw_text
            }

    except Exception as e:
        print("[Gemini] ERROR:", e)
        return {
            "strengths": [],
            "skill_matches": [],
            "gaps": [],
            "experience_fit": "Summary generation error.",
            "risks": [],
            "score_alignment": f"Error: {e}, Breakdown: {breakdown}"
        }
