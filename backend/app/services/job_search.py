"""Live job discovery from public job feeds.

Free public sources: Remotive, Jobicy, Arbeitnow, Himalayas, Remote OK and JobsForce India.
Only real source records are returned. Most sources are remote-focused; their
location labels are preserved and India eligibility must be checked on source.
"""
from __future__ import annotations
import html
import re
from typing import Any
import httpx

TIMEOUT = httpx.Timeout(25.0, connect=10.0)
HEADERS = {"User-Agent": "CareerPilot student project job discovery/1.0", "Accept": "application/json"}

# Domain vocabulary is deliberately title-oriented so broad descriptions do not
# make unrelated jobs appear in every search.
ROLE_PROFILES: dict[str, dict[str, Any]] = {
    "software": {"aliases": ["software developer", "software engineer", "software development", "application developer", "full stack developer", "full-stack developer", "web developer"], "terms": ["software", "full stack", "full-stack", "application developer", "web developer"], "industry": "engineering", "tag": "software"},
    "backend": {"aliases": ["backend developer", "back-end developer", "backend engineer", "server-side engineer", "api developer"], "terms": ["backend", "back-end", "server-side", "api developer"], "industry": "engineering", "tag": "backend"},
    "frontend": {"aliases": ["frontend developer", "front-end developer", "frontend engineer", "react developer", "ui engineer", "web interface developer"], "terms": ["frontend", "front-end", "react", "angular", "vue", "ui engineer"], "industry": "engineering", "tag": "frontend"},
    "ai_ml": {"aliases": ["ai engineer", "machine learning engineer", "ml engineer", "artificial intelligence engineer", "deep learning engineer", "nlp engineer", "computer vision engineer", "mlops engineer"], "terms": ["artificial intelligence", "machine learning", "ml engineer", "deep learning", "nlp engineer", "computer vision", "mlops"], "industry": "data-science", "tag": "machine learning"},
    "data_analyst": {"aliases": ["data analyst", "business intelligence analyst", "bi analyst", "product analyst", "analytics analyst"], "terms": ["data analyst", "business intelligence", "bi analyst", "product analyst", "analytics analyst"], "industry": "data-science", "tag": "data analyst"},
    "data_scientist": {"aliases": ["data scientist", "research scientist", "applied scientist"], "terms": ["data scientist", "applied scientist", "research scientist"], "industry": "data-science", "tag": "data scientist"},
    "python": {"aliases": ["python developer", "python engineer", "django developer", "flask developer", "fastapi developer"], "terms": ["python", "django", "flask", "fastapi"], "industry": "engineering", "tag": "python"},
    "java": {"aliases": ["java developer", "java engineer", "spring boot developer", "jvm engineer"], "terms": ["java", "spring boot", "jvm"], "industry": "engineering", "tag": "java"},
    "devops": {"aliases": ["devops engineer", "site reliability engineer", "sre", "platform engineer", "cloud infrastructure engineer"], "terms": ["devops", "site reliability", "sre", "platform engineer", "cloud infrastructure"], "industry": "admin", "tag": "devops"},
    "cloud": {"aliases": ["cloud engineer", "cloud architect", "aws engineer", "azure engineer", "gcp engineer"], "terms": ["cloud engineer", "cloud architect", "aws", "azure", "gcp"], "industry": "admin", "tag": "cloud"},
    "cybersecurity": {"aliases": ["cybersecurity analyst", "security engineer", "soc analyst", "penetration tester", "information security analyst"], "terms": ["cybersecurity", "security engineer", "soc analyst", "penetration tester", "information security"], "industry": "cybersecurity", "tag": "cybersecurity"},
    "qa": {"aliases": ["qa engineer", "quality assurance engineer", "software tester", "test automation engineer", "sdet"], "terms": ["qa engineer", "quality assurance", "software tester", "test automation", "sdet"], "industry": "qa-testing", "tag": "qa"},
    "mobile": {"aliases": ["mobile developer", "android developer", "ios developer", "flutter developer", "react native developer"], "terms": ["mobile developer", "android developer", "ios developer", "flutter", "react native"], "industry": "engineering", "tag": "mobile developer"},
    "ui_ux": {"aliases": ["ui designer", "ux designer", "product designer", "ux researcher"], "terms": ["ui designer", "ux designer", "product designer", "ux researcher"], "industry": "web-app-design", "tag": "ux designer"},
}

def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()

def _plain_text(value: Any) -> str:
    return _clean(re.sub(r"<[^>]+>", " ", html.unescape(str(value or ""))))

def _role_profile(role: str) -> dict[str, Any]:
    q = _clean(role).lower()
    q_compact = re.sub(r"[^a-z0-9]+", " ", q).strip()
    if ("ai" in q_compact.split() and "ml" in q_compact.split()) or "machine learning" in q:
        return ROLE_PROFILES["ai_ml"]
    # Longest matching aliases first, to avoid mapping a specialist role to generic software.
    matches = []
    for key, profile in ROLE_PROFILES.items():
        for alias in profile["aliases"]:
            if alias in q or q in alias:
                matches.append((len(alias), profile))
    if matches:
        return max(matches, key=lambda x: x[0])[1]
    # Unknown role: require its meaningful title terms, not generic words.
    stop = {"engineer", "developer", "specialist", "senior", "junior", "intern", "the", "and", "of"}
    terms = [x for x in re.findall(r"[a-z0-9+#.]+", q) if len(x) > 1 and x not in stop]
    return {"aliases": [q], "terms": terms or [q], "industry": "engineering", "tag": q}

def _role_matches(title: str, role: str, description: str = "", industries: list[str] | None = None) -> bool:
    profile = _role_profile(role)
    title_norm = _clean(title).lower()
    title_norm = re.sub(r"[^a-z0-9+#. ]+", " ", title_norm)
    # Title match is mandatory for the mapped specialist profiles. Description is
    # intentionally not enough by itself, as it caused unrelated repeated results.
    aliases = [re.sub(r"[^a-z0-9+#. ]+", " ", x.lower()) for x in profile["aliases"]]
    if any(re.search(r"\b" + re.escape(a) + r"\b", title_norm) for a in aliases if a):
        return True
    terms = profile["terms"]
    # Match a distinctive domain keyword in the title; never use generic
    # "engineer" or "developer" by themselves to avoid cross-domain leakage.
    return any(t in title_norm for t in terms)

def _location_matches(job_location: str, requested: str) -> bool:
    requested = _clean(requested).lower()
    actual = _clean(job_location).lower()
    if not requested or requested in {"any", "anywhere", "remote", "worldwide", "global"}:
        return True
    global_terms = ("worldwide", "anywhere", "global", "all countries")
    if any(x in actual for x in global_terms):
        return True
    if requested in actual:
        return True
    # Jobicy only exposes APAC as a regional filter; this is not a promise that
    # each APAC listing is eligible in India, so preserve its source location.
    if requested in {"india", "india remote"} and (actual == "apac" or "asia-pacific" in actual):
        return True
    return False

def _normalise_remotive(row: dict) -> dict:
    return {"id": f"remotive-{row.get('id', '')}", "title": _clean(row.get("title")),
        "company": _clean(row.get("company_name")) or "Company not listed",
        "location": _clean(row.get("candidate_required_location")) or "Remote",
        "description": _plain_text(row.get("description")), "url": row.get("url") or "",
        "salary": _clean(row.get("salary")) or None, "job_type": _clean(row.get("job_type")) or "Not specified",
        "source": "Remotive", "posted_at": row.get("publication_date"), "remote": True, "work_mode": "remote"}

def _normalise_jobicy(row: dict) -> dict:
    salary = None
    if row.get("salaryMin") or row.get("salaryMax"):
        salary = f"{row.get('salaryMin', '')}-{row.get('salaryMax', '')} {row.get('salaryCurrency', '')} {row.get('salaryPeriod', '')}".strip(" -")
    return {"id": f"jobicy-{row.get('id', '')}", "title": _clean(row.get("jobTitle")),
        "company": _clean(row.get("companyName")) or "Company not listed", "location": _clean(row.get("jobGeo")) or "Remote",
        "description": _plain_text(row.get("jobDescription") or row.get("jobExcerpt")), "url": row.get("url") or "",
        "salary": salary, "job_type": _clean(", ".join(row.get("jobType", [])) if isinstance(row.get("jobType"), list) else row.get("jobType")) or "Not specified",
        "source": "Jobicy", "posted_at": row.get("pubDate"), "remote": True, "work_mode": "remote"}

def _normalise_arbeitnow(row: dict) -> dict:
    remote = bool(row.get("remote"))
    return {"id": f"arbeitnow-{row.get('slug') or row.get('url') or ''}", "title": _clean(row.get("title")),
        "company": _clean(row.get("company_name")) or "Company not listed", "location": _clean(row.get("location")) or ("Remote" if remote else "Location not listed"),
        "description": _plain_text(row.get("description")), "url": row.get("url") or "", "salary": None,
        "job_type": _clean(", ".join(row.get("job_types", [])) if isinstance(row.get("job_types"), list) else "Not specified"),
        "source": "Arbeitnow", "posted_at": row.get("created_at"), "remote": remote, "work_mode": "remote" if remote else "Not specified"}

async def _get_remotive(client: httpx.AsyncClient, role: str, limit: int) -> list[dict]:
    r = await client.get("https://remotive.com/api/remote-jobs", params={"search": role, "limit": limit})
    r.raise_for_status(); payload = r.json()
    return [_normalise_remotive(x) for x in payload.get("jobs", []) if isinstance(x, dict)]

async def _get_jobicy(client: httpx.AsyncClient, role: str, location: str, limit: int) -> list[dict]:
    p = _role_profile(role)
    params = {"count": min(100, max(limit * 3, 30)), "tag": p["tag"]}
    if p.get("industry"):
        params["industry"] = p["industry"]
    # India is not a distinct Jobicy geo slug; APAC is the closest supported region.
    loc = _clean(location).lower()
    if loc in {"india", "india remote", "asia", "apac"}:
        params["geo"] = "apac"
    elif loc in {"usa", "united states", "us"}:
        params["geo"] = "usa"
    elif loc in {"europe", "uk", "canada", "australia"}:
        params["geo"] = "europe" if loc == "europe" else loc
    r = await client.get("https://jobicy.com/api/jobs", params=params)
    if r.status_code == 429:
        raise httpx.HTTPStatusError("Jobicy rate limit (429); retry later", request=r.request, response=r)
    r.raise_for_status(); payload = r.json()
    rows = payload.get("jobs", []) if isinstance(payload, dict) else []
    return [_normalise_jobicy(x) for x in rows if isinstance(x, dict)]

async def _get_arbeitnow(client: httpx.AsyncClient, role: str, location: str, limit: int) -> list[dict]:
    r = await client.get("https://www.arbeitnow.com/api/job-board-api", params={"page": 1})
    r.raise_for_status(); payload = r.json()
    rows = payload.get("data", []) if isinstance(payload, dict) else []
    return [_normalise_arbeitnow(x) for x in rows if isinstance(x, dict)]



def _normalise_himalayas(row: dict) -> dict:
    restrictions = row.get("locationRestrictions") or []
    location = ", ".join(("India" if str(x).upper() == "IN" else str(x)) for x in restrictions) if restrictions else "Worldwide / Remote"
    salary = None
    if row.get("minSalary") or row.get("maxSalary"):
        salary = f'{row.get("minSalary") or ""}-{row.get("maxSalary") or ""} {row.get("currency") or ""} / {row.get("salaryPeriod") or "annual"}'.strip(" -/")
    return {"id": f'himalayas-{row.get("guid") or row.get("id") or row.get("applicationLink")}',
        "title": _clean(row.get("title")), "company": _clean(row.get("companyName")) or "Company not listed",
        "location": location, "description": _plain_text(row.get("description") or row.get("excerpt")),
        "url": row.get("applicationLink") or "", "salary": salary,
        "job_type": _clean(row.get("employmentType")) or "Not specified",
        "source": "Himalayas", "posted_at": row.get("pubDate"), "remote": True, "work_mode": "remote"}

def _normalise_remoteok(row: dict) -> dict:
    tags = row.get("tags") or []
    desc = " ".join([str(row.get("description") or ""), " ".join(str(x) for x in tags)])
    return {"id": f'remoteok-{row.get("id") or row.get("slug") or row.get("url")}',
        "title": _clean(row.get("position") or row.get("title")),
        "company": _clean(row.get("company")) or "Company not listed",
        "location": _clean(row.get("location")) or "Remote",
        "description": _plain_text(desc), "url": row.get("url") or "",
        "salary": _clean(row.get("salary")) or None, "job_type": "Not specified",
        "source": "Remote OK", "posted_at": row.get("date"), "remote": True, "work_mode": "remote"}

async def _get_himalayas(client: httpx.AsyncClient, role: str, location: str, limit: int) -> list[dict]:
    params = {"q": role, "sort": "recent", "page": 1}
    loc = _clean(location).lower()
    if loc in {"india", "india remote"}:
        params["country"] = "IN"
    r = await client.get("https://himalayas.app/jobs/api/search", params=params)
    r.raise_for_status()
    payload = r.json()
    rows = payload.get("jobs", []) if isinstance(payload, dict) else []
    return [_normalise_himalayas(x) for x in rows[:limit] if isinstance(x, dict)]

async def _get_remoteok(client: httpx.AsyncClient, role: str, limit: int) -> list[dict]:
    # Remote OK returns an array whose first item may be API metadata.
    tags = ",".join(re.findall(r"[a-z0-9+#.-]+", role.lower())[:4])
    r = await client.get("https://remoteok.com/api", params={"tag": tags})
    r.raise_for_status()
    payload = r.json()
    rows = payload if isinstance(payload, list) else []
    return [_normalise_remoteok(x) for x in rows if isinstance(x, dict) and (x.get("position") or x.get("title"))][:limit]


def _normalise_jobsforce(row: dict) -> dict:
    loc = row.get("location") or {}
    hiring = row.get("hiring") or {}
    salary = row.get("salary") or {}
    company = hiring.get("display") or hiring.get("name") or "Employer not listed"
    # JobsForce explicitly marks agency listings; do not attribute confidential
    # client vacancies to the recruiting agency as though it were the employer.
    if hiring.get("type") == "agency":
        company = "Confidential client (via JobsForce India)"
    sal = salary.get("label") if isinstance(salary, dict) else None
    city = _clean(loc.get("city"))
    state = _clean(loc.get("state"))
    country = _clean(loc.get("country")) or "India"
    location = ", ".join(x for x in (city, state, country) if x) or country
    mode = _clean(row.get("work_mode")).lower()
    return {"id": f'jobsforce-{row.get("id") or row.get("url")}',
        "title": _clean(row.get("title")), "company": company, "location": location,
        "description": _plain_text(row.get("summary") or ""),
        "url": row.get("url") or row.get("apply_url") or "",
        "apply_url": row.get("apply_url") or row.get("url") or "",
        "salary": _clean(sal) or None, "job_type": _clean(row.get("job_type")) or "Not specified",
        "source": "JobsForce India", "posted_at": row.get("posted_date"),
        "remote": mode == "remote", "work_mode": mode or "Not specified",
        "hiring_type": hiring.get("type") or "employer"}

async def _get_jobsforce(client: httpx.AsyncClient, role: str, location: str, limit: int,
                         work_mode: str | None = None) -> list[dict]:
    params: dict[str, Any] = {"q": role, "per_page": min(20, max(10, limit)), "page": 1}
    loc = _clean(location)
    # The endpoint accepts a city rather than a country-wide India filter.
    if loc.lower() not in {"", "india", "india remote", "any", "anywhere", "remote", "worldwide"}:
        params["city"] = loc
    if work_mode in {"remote", "hybrid", "onsite"}:
        params["work_mode"] = work_mode
    r = await client.get("https://jobsforceindia.com/api/public/v1/jobs", params=params)
    r.raise_for_status()
    payload = r.json()
    rows = payload.get("results", []) if isinstance(payload, dict) else []
    return [_normalise_jobsforce(x) for x in rows if isinstance(x, dict)]

def _work_mode_matches(job: dict, requested: str) -> bool:
    """Keep selected work-mode results strict; unknown modes are never guessed."""
    requested = _clean(requested).lower() or "all"
    if requested == "all":
        return True
    actual = _clean(job.get("work_mode")).lower()
    if requested == "remote":
        return bool(job.get("remote")) or actual == "remote"
    # Only the India-specific source currently provides explicit hybrid/on-site labels.
    return job.get("source") == "JobsForce India" and actual == requested


async def search_live_jobs(role: str, location: str = "India", limit: int = 30, work_mode: str = "all") -> tuple[list[dict], list[str]]:
    role = _clean(role)[:100]; location = _clean(location)[:100]
    work_mode = _clean(work_mode).lower()
    if work_mode not in {"all", "remote", "hybrid", "onsite"}: work_mode = "all"
    limit = max(1, min(int(limit), 50)); notes: list[str] = []; errors: list[str] = []
    if not role:
        return [], ["Enter a target job role to search live vacancies."]
    jobs: list[dict] = []
    providers = [
        ("Remotive", lambda c: _get_remotive(c, role, min(limit * 3, 100))),
        ("Jobicy", lambda c: _get_jobicy(c, role, location, limit)),
        ("Himalayas", lambda c: _get_himalayas(c, role, location, limit)),
        ("Remote OK", lambda c: _get_remoteok(c, role, limit)),
        ("Arbeitnow", lambda c: _get_arbeitnow(c, role, location, limit * 3)),
    ]
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
        for source, fetch in providers:
            try:
                raw = await fetch(client)
                filtered = [j for j in raw if j.get("url") and _role_matches(j["title"], role, j.get("description", ""))]
                # For worldwide remote feeds, do not falsely label them India-only.
                filtered = [j for j in filtered if _location_matches(j["location"], location)
                            or (location.lower() in {"india", "india remote"} and j.get("remote") and
                                j["source"] in {"Remotive", "Remote OK"})]
                jobs.extend(j for j in filtered if _work_mode_matches(j, work_mode))
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                errors.append(f"{source}: {type(exc).__name__}")
        # India-specific board: explicitly query each requested work arrangement.
        modes = ["remote", "hybrid", "onsite"] if work_mode == "all" else ([work_mode] if work_mode in {"remote", "hybrid", "onsite"} else [])
        if location:
            for mode in modes:
                try:
                    raw = await _get_jobsforce(client, role, location, limit, mode)
                    jobs.extend(j for j in raw if j.get("url") and _role_matches(j["title"], role, j.get("description", "")) and _work_mode_matches(j, work_mode))
                except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                    errors.append(f"JobsForce India ({mode}): {type(exc).__name__}")
    unique = {}
    for j in jobs:
        unique.setdefault((j["title"].lower(), j["company"].lower(), j["url"]), j)
    results = list(unique.values())
    if results:
        sources = sorted({j["source"] for j in results})
        notes.append("Job sources used: " + ", ".join(sources) + ".")
        notes.append("Work mode is shown per listing when the source provides it; JobsForce India is queried separately for remote, hybrid and on-site roles.")
        notes.append("Listings are from public job feeds. Verify work arrangement, India eligibility and vacancy status on the original listing before applying.")
    if errors:
        notes.append("Some free job sources were unavailable: " + "; ".join(errors))
    if not results:
        notes.append("No matching live vacancies were found for this role and location. Try a broader role title or Worldwide/Any location. No sample jobs are generated.")
    return results[:limit], notes
