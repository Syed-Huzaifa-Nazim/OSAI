# Setup and running locally

Last updated: 2026-09-06

---

## Prerequisites

| Tool | Version | Checked with |
|---|---|---|
| Node.js | 20+ | built and tested on 22.19.0 |
| npm | 10+ | 11.13.0 |
| Python | 3.11+ | 3.13.5 |

A Supabase project and an OpenAI key are **optional**, without them the app
runs in demo mode against a seeded sample project.

---

## The short version

```bash
# --- backend ---------------------------------------------------------------
cd backend
python -m venv .venv
.venv/Scripts/activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# → http://127.0.0.1:8000   ·   interactive docs at /docs

# --- frontend (a second terminal) ------------------------------------------
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

Open <http://localhost:5173>, click **Get started**, and sign in with any email
and password: demo mode accepts anything. Open the **Verdant Roast** project;
it is parked at the first human checkpoint, which is the state worth seeing.

`GET http://127.0.0.1:8000/api/v1/health` reports exactly what is wired up:

```json
{
  "status": "ok",
  "demoMode": true,
  "supabaseConfigured": false,
  "openaiConfigured": false,
  "vectorstoreAvailable": true
}
```

---

## Environment variables

Both halves ship an `.env.example`. Copy, do not rename. The examples are
committed and the real files are gitignored.

```bash
cp backend/.env.example  backend/.env
cp frontend/.env.example frontend/.env.local
```

### `backend/.env`

| Variable | Required | Purpose |
|---|---|---|
| `SUPABASE_URL` | for real data | Project URL (Settings → API) |
| `SUPABASE_ANON_KEY` | for real data | Public key; RLS protects the data |
| `SUPABASE_SERVICE_ROLE_KEY` | for real data | **Secret.** Bypasses RLS; background worker only |
| `SUPABASE_JWT_SECRET` | for real data | **Secret.** Verifies incoming tokens |
| `OPENAI_API_KEY` | for live agents | **Secret.** Unused while agents are mocks |
| `OPENAI_MODEL` | no | Default `gpt-4o` |
| `OPENAI_EMBEDDING_MODEL` | no | Default `text-embedding-3-small` |
| `CHROMA_PERSIST_DIR` | no | Default `./.chroma` |
| `APIFY_API_TOKEN` | for Instagram | **Secret.** Instagram scraping runs on Apify's hosted actor; without it that platform reports itself unavailable |
| `APIFY_INSTAGRAM_ACTOR_ID` | no | Default `apify/instagram-scraper` |
| `INSTAGRAM_POSTS_LIMIT` / `INSTAGRAM_COMMENTS_LIMIT` | no | Default 12 posts per profile, 20 comments per post. Every collected post can be opened on the results screen, so the post budget bounds the scrape |
| `INSTAGRAM_COMMENT_POSTS_LIMIT` | no | Default 0, meaning every collected post has its comments read. A positive value caps it at that many posts, busiest first; every post keeps its counts either way |
| `WEBSITE_MAX_PAGES` / `WEBSITE_MAX_DEPTH` | no | Default 12 and 2. How far a crawl goes from the submitted link |
| `WEBSITE_REQUEST_DELAY_SECONDS` | no | Default 1.5. Pause between page fetches |
| `WEBSITE_RESPECT_ROBOTS_TXT` | no | Default `true`. Leave it on |
| `DEMO_MODE` | no | `true` serves the seed; forced on when Supabase is absent |
| `CORS_ORIGINS` | no | Comma-separated; must include the frontend origin |
| `LOG_LEVEL` | no | Default `INFO` |

### `frontend/.env.local`

| Variable | Required | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | no | Default `/api/v1`, proxied by Vite in dev |
| `VITE_API_PROXY_TARGET` | no | Default `http://127.0.0.1:8000` |
| `VITE_SUPABASE_URL` | for real auth | Same value as the backend |
| `VITE_SUPABASE_ANON_KEY` | for real auth | Anon key **only**: never the service role |
| `VITE_DEMO_MODE` | no | Auto-enables when Supabase is absent |
| `VITE_MARKETING_NAV` | no | `top` or `vertical`; both are built |
| `VITE_PIPELINE_POLL_MS` | no | Default `2000` |

> Everything prefixed `VITE_` is **compiled into the browser bundle**. Only ever
> put public values there. See [security.md](security.md).

---

## Connecting a real Supabase project

1. Create a project at [supabase.com](https://supabase.com).

2. Apply the schema:

   ```bash
   supabase db execute --file backend/app/db/schema.sql
   ```

   or paste it into the SQL editor. It is idempotent, so re-running is safe.

3. Copy the four values from **Settings → API** into `backend/.env`, and the URL
   plus anon key into `frontend/.env.local`.

4. Set `DEMO_MODE=false` and `VITE_DEMO_MODE=false`.

5. Restart both processes. `/api/v1/health` should now report
   `"supabaseConfigured": true`.

6. **Verify RLS is on.** In the Supabase dashboard, Table Editor → each table →
   the RLS badge should read *enabled*. If a table shows "unrestricted", the
   schema did not apply cleanly: stop and fix it before adding data.

Email confirmation is on by default in Supabase. For local development, turn it
off under **Authentication → Providers → Email**, or you will have to confirm
every test account.

---

## Everyday commands

### Frontend

```bash
npm run dev         # dev server with HMR
npm run build       # typecheck + production build
npm run preview     # serve the built bundle
npm run typecheck   # tsc --noEmit
npm run test        # vitest, once
npm run test:watch  # vitest, watching
```

### Backend

```bash
uvicorn app.main:app --reload           # dev server
uvicorn app.main:app --host 0.0.0.0     # reachable from the network
pytest                                  # the suite
pytest -k checkpoint -v                 # the HITL tests
```

The whole backend suite runs against the in-memory repository, so it needs no
database, no network and no keys.

---

## Demo mode

Demo mode exists so the nine-stage pipeline can be walked end to end in a
defence with no scraping and no LLM spend.

It is on when `DEMO_MODE=true` **or** whenever Supabase is unconfigured, on both
halves independently.

What changes:

| | Demo | Real |
|---|---|---|
| Auth | Local session, any credentials | Supabase Auth |
| Data | Seeded "Verdant Roast" project | Postgres |
| Pipeline | Timer-driven simulation | Background runner |
| Agents | Mocks | Mocks *(live agents not yet implemented)* |
| Cost | Zero | LLM + scraping |

The pipeline simulation is a real state machine. It parks at stages 5 and 7
exactly as the server does, so the stepper animates against genuine transitions.

Anything drawn from seeded data carries a **Demo data** badge.

---

## Troubleshooting

**Frontend loads but every request 404s.** The backend is not running, or
`VITE_API_PROXY_TARGET` points somewhere else. Check
<http://127.0.0.1:8000/api/v1/health>.

**CORS errors in the console.** Add the frontend origin to `CORS_ORIGINS` in
`backend/.env` and restart uvicorn.

**"Your session has expired" immediately after logging in.** `SUPABASE_JWT_SECRET`
does not match the project the frontend authenticated against. Both halves must
point at the same Supabase project.

**`chromadb` fails to install.** It is optional. The API starts without it and
reports `"vectorstoreAvailable": false`; stage 3 counts chunks but does not
persist vectors, and says so in the stage warning.

**PDF or DOCX export returns 503.** `reportlab` or `python-docx` is missing.
`pip install -r requirements.txt`. Markdown export works regardless, and works
client-side even in demo mode.

**Tests hang on Windows.** Run them from the venv's interpreter directly:
`.venv/Scripts/python.exe -m pytest`.
