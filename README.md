# OptiStratixAI

**Human-in-the-Loop Multi-Agentic RAG for Smarter Digital Marketing**

OptiStratixAI scrapes and analyses competitor landing pages and social media,
identifies strategic gaps and market opportunities, and, with a human
validating every major step, turns that analysis into evidence-based,
ready-to-execute marketing strategy documents and content assets.

A Final Year Project at the Department of Artificial Intelligence, Dawood
University of Engineering & Technology.

---

## What it does

A run moves through nine stages. Two of them are yours:

| # | Stage | Who |
|---|-------|-----|
| 1 | User Input: brand details and competitor links | You |
| 2 | **Scout Agent**: collects web, social, review, forum and news data | Agent |
| 3 | Preprocessing & Storage: clean, chunk, embed, vectorise into ChromaDB | System |
| 4 | **Insight Agent**: gap and opportunity analysis | Agent |
| 5 | **Human Review: Gap Refinement** | **You** |
| 6 | **Strategist + Critic**: draft, then adversarially validate | Agents |
| 7 | **Human Review: Final Approval** | **You** |
| 8 | Strategy Document: full document with an implementation plan | System |
| 9 | Scalability & Automation: follow-on content assets | Agent |

Stages 5 and 7 are mandatory. No agent can advance past them. The API refuses,
not just the UI. That is the product's trust story, and it is enforced in
`backend/app/services/pipeline_service.py`.

---

## Quick start

Nothing needs configuring to see it run. With no `.env` files at all, both
halves start in **demo mode** and serve a seeded sample project ("Verdant
Roast") end to end: no scraping, no database, no LLM spend.

**Windows, one step:** right-click `start-dev.ps1` → *Run with PowerShell*. It
installs whatever is missing on first run, then opens the backend and frontend
in their own windows.

Or by hand:

```bash
# --- backend ---------------------------------------------------------------
cd backend
python -m venv .venv
.venv/Scripts/activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium   # only needed for e-commerce scraping
uvicorn app.main:app --reload   # http://127.0.0.1:8000  (docs at /docs)

# --- frontend --------------------------------------------------------------
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

Then open <http://localhost:5173>, sign in with any email and password (demo
mode accepts anything), and open the **Verdant Roast** project. It is parked at
the first human checkpoint, which is the interesting state.

Full setup, including connecting a real Supabase project, is in
[`docs/README.md`](docs/README.md).

---

## Repository layout

```
OptiStratixAI/
├── frontend/          React 18 + Vite + TypeScript + Tailwind
│   └── src/
│       ├── app/           routing and route guards
│       ├── pages/         one folder per area (marketing, auth, app)
│       ├── components/    ui, layout, pipeline, charts, marketing, shared
│       ├── features/      ← integration slot for teammates' repos
│       ├── lib/           api client, supabase, query client, mock data
│       ├── hooks/  stores/  styles/  types/
├── backend/           FastAPI + Supabase + ChromaDB
│   └── app/
│       ├── core/          config, security, errors, supabase clients
│       ├── api/v1/        routers, one per pipeline area
│       │   └── agents/    Scout / Insight / Strategist / Critic
│       ├── scrapers/      one folder per platform, behind a shared contract
│       │   └── daraz/     requests + BS4, Playwright fallback
│       ├── models/  services/  db/  vectorstore/
└── docs/              architecture, database, security, status, prompts
```

---

## Documentation

| Document | What it covers |
|---|---|
| [docs/README.md](docs/README.md) | Setup, environment variables, running locally |
| [docs/architecture.md](docs/architecture.md) | System design, the pipeline as built, the feature-integration pattern |
| [docs/database.md](docs/database.md) | Postgres schema, RLS policies, ChromaDB collections |
| [docs/security.md](docs/security.md) | Auth model, secrets handling, known gaps |
| [docs/error-handling.md](docs/error-handling.md) | Error conventions across both halves |
| [docs/project-status.md](docs/project-status.md) | What is built, what is stubbed, what is pending |
| [docs/project-summary.md](docs/project-summary.md) | Executive summary for a non-technical reader |
| [docs/prompts/](docs/prompts/) | Dated log of build sessions |
| [docs/LICENSE.md](docs/LICENSE.md) | MIT |

---

## Current state

The full nine-stage pipeline runs end to end. Everything around the agents is
real: the state machine, the checkpoint enforcement, the evidence trail, the
persistence layer, the auth model and the document generation.

The agents themselves are split:

- **Website and social comparisons** still run the four **mock** agents, which
  return hand-written, realistic data instead of calling an LLM. Swapping in a
  live agent is a one-line change in
  `backend/app/api/v1/agents/registry.py`.
- **E-commerce product comparisons scrape and display.** Creating one
  scrapes both Daraz listings for real (price, specs, reviews, seller details
  and product images), embeds their text, and opens a comparison page with
  eight parameter groups, side-by-side metrics and retrieved passages. No agent
  runs on this path for now, and the pipeline cannot be started on these
  projects. Website and social comparisons are listed as coming soon.
  `backend/app/scrapers/` is built to take more platforms.

See [docs/project-status.md](docs/project-status.md) for the honest inventory.

---

## Team

- Hadia (23-AI-01)
- Syed Huzaifa Nazim (23-AI-23)
- Muhammad Waqas Ali (23-AI-59)
- Muhammad Umar Khan (23-AI-71)

**Supervisor:** Ms. Noor Ul Huda Soomro, Lecturer, Department of Artificial
Intelligence

Dawood University of Engineering & Technology
Faculty of Information & Computing Sciences

---

Released under the [MIT License](docs/LICENSE.md).
