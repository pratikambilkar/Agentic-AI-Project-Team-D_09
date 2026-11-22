"""Use Gemini or OpenAI to explain matches for real retrieved listings only."""
from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import settings


def _skill_names(profile_skills: Any) -> list[str]:
    """Accept candidate_skills output (skill -> evidence dict) or a simple list."""
    if isinstance(profile_skills, dict):
        names = list(profile_skills.keys())
    elif isinstance(profile_skills, (list, tuple, set)):
        names = list(profile_skills)
    else:
        names = []
    return [str(name)[:100] for name in names if name][:80]


def _fallback(jobs: list[dict], matched_skills: list[str], missing_by_job: list[list[str]]) -> list[dict]:
    out = []
    for i, job in enumerate(jobs):
        out.append({
            "match_score": None,
            "matched_skills": matched_skills[:8],
            "missing_skills": (missing_by_job[i] if i < len(missing_by_job) else [])[:8],
            "why_recommended": [
                "This is a real listing retrieved from " + str(job.get("source", "the job source")) + ".",
                "Review the original description to confirm required skills and eligibility.",
            ],
            "ai_provider": "rule-based fallback",
        })
    return out


async def analyse_jobs(jobs: list[dict], profile_skills: Any, resume_text: str = "") -> list[dict]:
    """AI ranks only supplied listings; it must not create companies, vacancies, links or requirements."""
    if not jobs:
        return []
    skills = _skill_names(profile_skills)
    provider = "gemini" if settings.gemini_api_key else ("openai" if settings.openai_api_key else "")
    if not provider:
        return _fallback(jobs, skills, [[] for _ in jobs])

    compact_jobs = [
        {"index": i, "title": j.get("title"), "company": j.get("company"),
         "description": str(j.get("description", ""))[:3500], "location": j.get("location")}
        for i, j in enumerate(jobs[:20])
    ]
    prompt = (
        "You are a career matching analyst. Analyse ONLY the real job records supplied below. "
        "Never invent jobs, companies, URLs, qualifications or facts. Return valid JSON only: "
        '{"results":[{"index":0,"match_score":0,"matched_skills":[],"missing_skills":[],"why_recommended":[]}]} . '
        "Scores are profile similarity, not guaranteed eligibility. Be conservative and cite only evidence in the description.\n"
        f"Candidate skills: {json.dumps(skills)}\n"
        f"Resume excerpt: {str(resume_text or '')[:5000]}\n"
        f"Job records: {json.dumps(compact_jobs, ensure_ascii=False)}"
    )
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(35, connect=8)) as client:
            if provider == "gemini":
                model = settings.gemini_model or "gemini-2.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                response = await client.post(
                    url, params={"key": settings.gemini_api_key},
                    json={"contents": [{"parts": [{"text": prompt}]}],
                         "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}},
                )
                response.raise_for_status()
                body = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={"model": settings.openai_model or "gpt-4o-mini", "temperature": 0.1,
                          "response_format": {"type": "json_object"},
                          "messages": [{"role": "user", "content": prompt}]},
                )
                response.raise_for_status()
                body = response.json()["choices"][0]["message"]["content"]

        parsed = json.loads(body)
        by_index = {int(x.get("index", -1)): x for x in parsed.get("results", []) if isinstance(x, dict)}
        result = []
        for i in range(len(jobs)):
            x = by_index.get(i, {})
            try:
                score = max(0, min(100, int(x.get("match_score"))))
            except (TypeError, ValueError):
                score = None
            matched, missing, reasons = x.get("matched_skills", []), x.get("missing_skills", []), x.get("why_recommended", [])
            result.append({
                "match_score": score,
                "matched_skills": [str(v)[:80] for v in matched[:10]] if isinstance(matched, list) else [],
                "missing_skills": [str(v)[:80] for v in missing[:10]] if isinstance(missing, list) else [],
                "why_recommended": [str(v)[:240] for v in reasons[:4]] if isinstance(reasons, list) else [],
                "ai_provider": provider,
            })
        return result
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
        return _fallback(jobs, skills, [[] for _ in jobs])
