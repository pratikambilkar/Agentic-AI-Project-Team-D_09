# Placement Readiness & Career Intelligence Portal

A production-oriented starter for a student placement/career intelligence platform.

## Stack
- Frontend: React + TypeScript + Vite + Tailwind CSS + Recharts
- Backend: FastAPI + SQLAlchemy + JWT
- Database: PostgreSQL
- Cache/queue-ready: Redis
- ML: scikit-learn rule/feature-based career-fit engine (replaceable by trained models)
- LLM: provider abstraction with OpenAI-compatible HTTP support and secure server-side API keys

## Quick start with Docker
1. Install Docker Desktop.
2. Copy `.env.example` to `.env` and update secrets if needed.
3. Run `docker compose up --build`.
4. Open http://localhost:5173.
5. API docs: http://localhost:8000/docs

## Local development
### Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## LLM keys
The app supports a user-level LLM configuration from Settings. Keys are accepted by the backend only and encrypted at rest using `SECRET_KEY`. Do not put user keys in frontend code.

The included `.env` intentionally contains empty LLM keys. Add your own key through the UI or environment variables for development.


## AI agents (matches the project brief)

| Agent | What it does | Code |
|---|---|---|
| **Resume Agent** | Upload PDF/DOCX/TXT, extract contact, education, skills, projects, experience; ATS-style score (100 pts) with concrete fixes; optionally merges findings into your profile without overwriting your entries | `backend/app/agents/resume_agent.py` |
| **Skill Gap Agent** | Compares skills evidence (profile + resume + projects + coding) with role requirements; prioritised gap report, effort estimates, closest alternative roles | `skill_gap_agent.py`, role data in `catalog.py` |
| **Coding Analytics Agent** | Fetches public stats from LeetCode, Codeforces and GitHub (or manual entry); coding score, difficulty mix, strengths/gaps, recommendations | `coding_agent.py` |
| **Job Matching Agent** | Ranks companies/roles using skill coverage, TF-IDF profile similarity, DSA fit and CGPA; matches pasted job descriptions | `job_agent.py`, data in `app/data/companies.json` |
| **Interview Agent** | Mock interview (HR, technical, project, behavioural) from your role/skills/projects; LLM evaluation if a key is configured, otherwise keyword + STAR-structure scoring | `interview_agent.py` |

### Expected outputs
- **Placement readiness score** (`GET /api/readiness`): transparent weighted blend (profile 8, academics 10, skills 24, portfolio 10, resume 13, coding 20, interview 15). Areas not yet assessed count as zero and are flagged, so the score cannot look better than the evidence.
- **Skill-gap report** (`GET /api/skills/gap?target_role=`)
- **Company / role matches** (`GET /api/companies/matches`, `GET /api/jobs/live`, `POST /api/job/match`)
- **Learning roadmap** (`POST /api/roadmap/generate`): week-by-week plan from gaps in every agent, shown on the Learning Roadmap page.

### New API endpoints
`POST /resume/parse` (multipart) · `POST /resume/analyze-text` · `GET /resume/latest` · `GET /skills/gap` · `GET /roles` · `POST /coding/sync` · `POST /coding/manual` · `GET /coding/analytics` · `DELETE /coding/{platform}` · `GET /companies/matches` · `POST /job/match` · `POST /interview/start` · `POST /interview/{id}/answer` · `POST /interview/{id}/finish` · `GET /interview/sessions` · `GET /interview/{id}` · `GET /readiness` · `POST /roadmap/generate`

### Notes and limits
- **Embeddings:** similarity uses TF-IDF (offline, no key). `agents/similarity.py` is the single place to swap in neural embeddings.
- **Company catalog is illustrative.** Cut-offs and hiring processes are approximations; edit `app/data/companies.json` for your campus drives.
- **Coding platforms:** the backend calls LeetCode (unofficial GraphQL), Codeforces and GitHub public APIs. LeetCode's endpoint is unofficial and may change or rate-limit; manual entry is the fallback.
- **LLM providers:** OpenAI, Gemini and Anthropic (Settings page). Without a key the Interview Agent uses its offline question bank and heuristic scoring; heuristics reward keyword coverage and cannot verify correctness.
- **Database:** new tables (`resume_analyses`, `coding_stats`, `interview_sessions`, `readiness_snapshots`) are created automatically on startup. No existing table was changed, so no migration is needed.

### Tests
```bash
cd backend && python -m unittest discover -s tests -v
```

## Demo account
The backend exposes registration. Create your own account from the UI.

## Agentic AI additions (Agentic AI Lab)

The updated build adds a sidebar page named **Agentic AI Lab** (`/agentic-lab`) and authenticated API endpoints:

- `GET /api/agentic/status` — lists the agents, registered tools, RAG method, memory design, and MCP endpoint.
- `POST /api/agentic/run` — runs a transparent workflow: read the signed-in student's profile → run Skill Gap analysis → retrieve relevant career guidance → return a combined recommendation and execution trace.
- `POST /api/agentic/rag/query` — retrieves relevant passages from the bundled career knowledge base using TF-IDF and returns the retrieved source titles. This is a local, deterministic RAG retrieval demo; the response synthesis does not require an external LLM.
- `POST /api/agentic/tools/call` — invokes one of the allow-listed application tools.
- `GET/POST/DELETE /api/agentic/memory` — views, stores, or clears Short-Term Memory (STM) and Task Memory (TM). **These memories are in-process and reset when the backend restarts.** They are isolated by logged-in user ID.
- `POST /api/mcp` — a lightweight MCP-style JSON-RPC HTTP tool endpoint supporting `initialize`, `ping`, `tools/list`, and `tools/call`. Send the normal bearer token from login in the `Authorization` header. Tools are allow-listed and read-only.

### MCP test request

Send a POST request to `http://localhost:8000/api/mcp` with `Content-Type: application/json`, `Authorization: Bearer <access_token>`, and this body:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
```

To call a tool:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_career_knowledge","arguments":{"query":"backend developer skills"}}}
```

### Scope and honest limitations

- The existing Resume, Skill Gap, Coding Analytics, Job Matching, and Interview agent modules remain in place. The Agentic AI Lab exposes a new orchestrated workflow and trace so the sequence can be demonstrated.
- RAG uses a small bundled knowledge set and TF-IDF retrieval, not a hosted vector database. Expand `CAREER_DOCS` in `backend/app/api/agentic.py` to add curated materials.
- MCP support is a lightweight HTTP JSON-RPC tool endpoint in this app, not a connector to an external MCP server. It exposes only the listed safe, read-only tools.
- STM/TM is implemented as in-memory demo state; use a database-backed store for durable memory in production.
- LLM calls still require a valid provider and API key in AI / LLM Settings. RAG and the demo agent workflow work without an LLM key.

### Run and test

From the project root:

```bash
docker compose up --build
```

Open `http://localhost:5173`, sign in, and select **Agentic AI Lab**. FastAPI docs are at `http://localhost:8000/docs`.

Run backend unit tests inside the backend environment with:

```bash
python -m unittest discover -s tests -v
```


### Live job vacancies: remote, hybrid and work from office

The Job Matching Agent includes a live vacancy search with filters for **All**, **Remote / Work from home**, **Hybrid**, and **On-site / Work from office**. Search by role and location (default: India). Listings are matched against the signed-in student's skills and resume, then ranked with optional AI analysis or a local rule-based fallback.

**Free public sources used by the backend**
- Remotive — remote vacancies.
- Jobicy — remote vacancies; APAC is a regional filter, not a guarantee of India eligibility.
- Himalayas — remote vacancies; preserve source attribution and the original application link.
- Remote OK — remote vacancies; credit the source and link to the original listing.
- Arbeitnow — public job-board feed; work mode may be unspecified.
- JobsForce India — queried separately for India remote, hybrid and on-site vacancies.

The remote-focused feeds are included for remote searches and for **All**. When a user selects Hybrid or On-site, CareerPilot returns only records explicitly marked with that arrangement by JobsForce India; it does not guess a work arrangement from an unclear listing. A location such as Bengaluru can be entered to narrow the India-specific search.

No vacancy API key is required. Gemini/OpenAI keys are optional and are used only for enhanced match explanations, not for retrieving vacancies. Without an AI key, live listings and local skill-overlap matching still work. Configure `GEMINI_API_KEY` or `OPENAI_API_KEY` in `.env` only if you want AI explanations. Never commit real keys.

**Important limitations:** public feeds can be unavailable, rate-limited, delayed or incomplete. This is not a comprehensive index of every Indian employer's career page, and no API can guarantee that every role/city/work-mode combination has results. The app never fabricates sample vacancies. Always verify the employer, eligibility, work arrangement, vacancy status and application instructions on the original listing before applying. Agency-sourced listings are labelled as confidential client roles when the API identifies them as agency listings.

### Windows / VS Code quick start

1. Extract this ZIP and open the `placement_portal` folder in VS Code.
2. Copy `.env.example` to `.env` if `.env` does not exist. Set a private `SECRET_KEY` and database password before using beyond a local demo. AI keys are optional.
3. In the VS Code terminal, run `docker compose up --build`. If containers were already running after a code update, run `docker compose down` and then `docker compose up --build`.
4. Open the frontend at `http://localhost:5173`; backend API docs are at `http://localhost:8000/docs`.
5. Register/sign in, open **Job Matching Agent → Live job vacancies**, enter a role and location, choose the work arrangement, and select **Find live jobs**.

### Verification

Backend unit tests:

```bash
cd backend
python -m unittest discover -s tests -v
```

Python syntax compilation:

```bash
python -m compileall -q backend/app backend/tests
```

Live API availability depends on network access and each provider's current service status; passing local tests does not guarantee that external feeds are reachable at runtime.
