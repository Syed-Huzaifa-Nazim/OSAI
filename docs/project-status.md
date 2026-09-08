# Project status

Last updated: 2026-09-07

Living log. **Most recent entry on top.** The point of this file is that it
distinguishes what is real from what is stubbed. If you read nothing else,
read [§ What is mocked](#what-is-mocked).

---

## 2026-09-07: top nav redesign and dash removal (session 4)

Gave the horizontal navigation the same treatment the rail got, and removed
every em and en dash from the project. Full account in
[prompts/2026-09-07-nav-and-copy.md](prompts/2026-09-07-nav-and-copy.md).

**Top navbar.** Full width and transparent at rest, contracting into a floating
glass pill once you scroll past 24px. A honey pill slides between links on the
same shared layout id as the rail's marker, and a reading-position hairline runs
across the top. The mobile menu is now a full-screen numbered index matching the
rail's typography, with body scroll locked while it is open.

**Dashes.** 324 occurrences removed across code, comments, docs and copy. Each
was sorted into a label separator (colon), an independent clause (full stop) or
a tight aside (commas, or parentheses where the aside had its own commas),
because a comma splice reads worse than the dash it replaces. The rendered pages
now contain zero dash characters in either navigation variant.

The repo-wide rewrite broke seven places where its tidy-up regexes matched
across newlines, including a comment that ran into a spread operator and a
README table row whose parenthesis closed on the row below. All were found and
repaired; the type checker caught five within seconds. The author's original
brief was excluded from the sweep.

---

## 2026-09-07: Vertical nav redesign (session 3)

Reworked the marketing site's vertical navigation variant to be bolder and more
editorial: a numbered index in display type, a single honey marker that slides
between entries on a shared layout id, a rotated wordmark in the space the index
leaves over, a pull-quote above the CTA, and a warm bloom behind the header.
Rail widened 240px -> 288px, with the width exported so the shell reserves
exactly that much rather than repeating the number.

Two real bugs surfaced while verifying it in a browser, neither of them caused
by the redesign:

| Bug | Detail |
|---|---|
| **The mobile drawer never left the DOM.** | Tapping a nav link ran the exit animation but the node stayed at `translateX(-100%)` with 11 focusable links still in the tab order, invisible to sighted users, fully present to a keyboard or screen reader. AnimatePresence's removal is an internal state update, and it was being lost inside the router navigation the same tap started. Closing with the X button always worked, which is what made it hard to spot. Both the marketing rail and the app sidebar were affected. Fixed by driving `animate` off the open state and unmounting in `onAnimationComplete`, so removal cannot be swallowed. |
| **`Badge` dropped refs.** | Radix's `asChild` triggers clone their child and hand it a ref to anchor against; `Badge` was a plain function component, so `DemoBadge`'s tooltip had no anchor and React logged a warning on every app page. Now a `forwardRef`. |

Five regression tests added in
`src/components/layout/__tests__/mobile-drawer.test.tsx`. Two of them fail
against the old implementation and pass against the new one, checked by
reverting, after the previous session produced tests that passed either way.

Frontend tests: 80 -> 85.

---

## 2026-09-06: Reported defects (session 2)

Three defects reported after the first build. See
[prompts/2026-09-06-fixes.md](prompts/2026-09-06-fixes.md) for the full account.

| Report | Status |
|---|---|
| Site scrolls itself back up | **Fixed.** `PipelineStepper` used `scrollIntoView`, which scrolls the *document*, not the strip. The landing-page teaser advances a stage every couple of seconds, so the page was dragged back to a fixed offset on every tick. Confirmed by measurement before and after. |
| Other pages show a blank screen | **Not reproduced.** Every route was checked in a real Chromium against both the dev server and the production build, under normal conditions, reduced motion, and 400 ms of artificial latency per module. All render; no console errors. Awaiting the browser console output from the reporting machine. |
| Remove the FYP badge from the home page | **Done.** Removed from the landing hero; still stated on `/about` and in the footer. |

Two test-harness gaps were found in the process, jsdom implements neither
`IntersectionObserver` nor `Element.scrollTo`, so scroll-revealed sections were
rendering empty and the stepper's scroll crashed. Both are stubbed now, and
17 new tests cover route rendering and navigation.

Frontend tests: 63 -> 80.

---

## 2026-09-06: Initial full build

Built the complete product: public marketing site, authenticated application,
FastAPI backend, database schema, agent scaffolding, tests and documentation.

### Verified

| Check | Result |
|---|---|
| `tsc --noEmit` (strict, `noUncheckedIndexedAccess`, `noUnusedLocals`) | **passes, 0 errors** |
| `vite build` | **passes, no size warnings**, route-level code splitting, largest chunk 122 kB gzipped |
| `vitest run` | **63 passed / 63** across 10 files |
| `pytest` | **34 passed / 34** across 7 files |
| Full nine-stage run over HTTP | **passes**. See below |

### Scale

| | Files | Lines |
|---|---|---|
| Frontend (`.ts`, `.tsx`, `.css`) | 138 | ~14,314 |
| Backend (`.py`) | 57 | ~5,224 |
| SQL schema | 1 | 383 |
| Docs | 10 | ~1,888 |
| Pages | 25 |, |
| Routes | 29 |, |

### End-to-end run, over real HTTP

A complete nine-stage run was driven against a live `uvicorn` process, not the
test client, creating a fresh project and walking it to completion:

```
[1] Project created      -> 201  stage=1
[2] Scout started        -> 200
[3] Preprocess           -> complete
[4] Insight              -> complete: 7 gaps identified
>>> PARKED at stage 5.  blockedOn=5  stage6=idle
    7 gaps, all cited: True
[5] Premature review     -> 409 conflict
    "7 gap(s) still need a decision. Every gap has to be kept or dropped
     before this checkpoint can close."
[5] Gap review           -> 200  kept=4
[6] Strategist+Critic    -> 3 initiatives, 4 interventions (1 major)
    CRITIC REJECTED: Launch a paid retargeting programme across social
      reason: assumes a paid media budget, and nothing in the intake...
>>> PARKED at stage 7.  blockedOn=7  stage8=idle
[7] Revision, no notes   -> 409 conflict
[7] Approve              -> 200
[8] Document             -> ready to export (288 words, 6 sections)
[9] Automation           -> 5 content assets suggested
    run cost: $1.923 over 189,660 tokens
    audit trail: [(5, 'approved'), (7, 'approved')]
>>> FINAL: status=complete  stage=9
```

Both gates held, both refusals fired with actionable messages, the Critic
removed the unfunded initiative, and the audit trail recorded both decisions.

PDF, DOCX and Markdown rendering were each verified to produce valid output,
including a title containing `&` and `<>`, which crashes reportlab unescaped,
and which real brand names contain.

### Decisions taken this session

Four were put to the project owner before any code was written:

| Question | Decision | Consequence |
|---|---|---|
| Marketing nav: top bar or left rail? | **Both** | Both are built, switchable at runtime via `NavVariantSwitcher` and `VITE_MARKETING_NAV` |
| Zustand or Context? | **Zustand** | Selector subscriptions; a pipeline tick re-renders one card, not the tree |
| SQLAlchemy or Supabase client? | **Supabase client** | Every query carries the caller's JWT, so RLS is the single enforcement point |
| Optional scope | **All four** | Light/dark toggle, demo mode, Stage 9 as a real feature, and test scaffolding |

---

## What is built

### Frontend, complete

- **Public site (7 routes)**, landing with a live self-driving pipeline teaser,
  how-it-works (all nine stages, scroll-revealed), features, about (team,
  supervisor, objectives), pricing *(placeholder, flagged in-page)*, contact
  (working form), 404.
- **Auth (4 routes)**: login, signup, forgot-password, reset-password. Real
  full pages, not dialogs. zod validation, per-field server errors, loading
  states, password visibility toggle, live strength meter,
  redirect-after-login to the intended destination.
- **App (14 routes)**: dashboard, projects list, new-project intake, and one
  page per pipeline stage, plus four settings pages.
- **The animated stepper**: nine stage cards with five visually distinct
  states, self-drawing connectors, a travelling highlight while a stage runs,
  and a breathing butter-cream wash on a stage blocked on a human. Horizontal on
  desktop with auto-scroll-to-active; vertical below `lg`.
- **Design system**: five brand tokens as CSS variables; light and dark are the
  same tokens with roles swapped. No hex value in any component.
- **Charts**: six Recharts wrappers on a palette validated for lightness band,
  chroma floor, CVD separation, normal-vision floor and contrast, per mode.
  Every chart offers a table view of the same numbers.
- **Loading, empty and error states** on every data surface, designed rather
  than default. Empty states distinguish "nothing yet" from "nothing matches".
- **Accessibility**: semantic landmarks, `aria-label` on every icon-only
  button, `role="meter"` on the confidence display, visible focus rings,
  `prefers-reduced-motion` respected in both CSS and Framer Motion.

### Backend: complete

- **30 endpoints** (plus `/health`) mapped onto the pipeline stages.
- **Pipeline runner** that drives automated stages and **stops** at 5 and 7.
- **Two storage backends** behind one interface: in-memory (demo, tests) and
  Supabase (real).
- **Full Postgres schema**: 12 tables, RLS on all of them.
- **Agent scaffolding**: one interface, five implementations, swappable in a
  single line.
- **Document generation**: Markdown, PDF (reportlab), DOCX (python-docx).
- **One error envelope**, request-id tracing, per-stage token and cost tracking.

### Docs: complete

All nine mandatory files, each dated, plus this session's prompt log.

---

## What is mocked

**This is the honest inventory.** Everything around the agents is real; the
agents themselves are not.

| Component | State | What is genuinely real |
|---|---|---|
| **Scout Agent** (stage 2) | 🔴 Mock | Nothing: returns hand-written source templates bound to the project's real competitor rows. No network request is made. |
| **Preprocessing** (stage 3) | 🟡 Partly real | Chunking is real (sliding window, sentence-boundary preference, clamped overlap) and writes to Chroma. Embeddings use Chroma's default model, not OpenAI. |
| **Insight Agent** (stage 4) | 🔴 Mock | Gap templates are hand-written, but **evidence is bound to the project's real source rows**, so every citation in the UI resolves. |
| **Strategist** (stage 6a) | 🟡 Partly real | Templates are hand-written, but **selection is driven by the categories of the gaps the human actually accepted**, dropping everything except pricing yields a pricing strategy. |
| **Critic** (stage 6b) | 🟢 Real logic | Rule-based, not a second model, but the four checks genuinely run and genuinely modify the draft. Every intervention keeps `before` and `after`. |
| **Document** (stage 8) | 🟢 Real | Assembled from what the run actually produced. Real counts, real gap titles, real review records. |
| **Automation** (stage 9) | 🟡 Partly real | Asset templates are hand-written; mapping to initiatives is real. |
| **Vector search** | 🟡 Available | Chroma is wired and queryable; the mock Insight Agent does not use it. |
| **Contact email** | 🔴 Not sent | Submissions are stored. No transactional provider. The UI says so. |
| **Billing** | 🔴 Placeholder | No provider, no card collection. Both pages say so. |

### The Critic deserves a note

It is the only thing backing the claim "reduces hallucinated and misleading
insights", so it was built to behave like the real thing **in the way that
matters**: every intervention produces an inspectable record with the original
text and the replacement side by side. A live Critic must preserve that
contract. `backend/tests/test_critic_agent.py` asserts it.

The four checks it applies:

1. Rejects paid work when no budget was declared at intake.
2. Trims a plan past a sustainable action count.
3. Hedges outcome claims that assert results with no supporting source.
4. Adds a measurement step where an initiative has no way to be judged.

---

## Placeholder content: needs your review

Flagged in-product as well as here.

| Where | What | Why it needs you |
|---|---|---|
| `/pricing` | Three tiers, prices, limits | The deck has no commercial model. Tier names, prices and per-run limits were invented to give the page a plausible shape. An in-page banner tells visitors so. |
| `/app/settings/billing` | Plan display | Mirrors the above. |
| Demo dataset | "Verdant Roast" + three competitors | Fictional, using the reserved `.example` TLD. Not real businesses. |
| Feature registry | Three example integration rows | Placeholder names for teammates' real modules. |

---

## Pending

### Blocked on you

- [ ] Review and replace the pricing tiers, or confirm the page should be cut.
- [ ] Hand over the teammates' feature repos to integrate (§ 7 of
      `architecture.md` describes the seam; nothing was integrated in this
      session, per the brief).
- [ ] Decide whether the marketing site keeps the top navbar or the left rail. Both are live behind the switcher.
- [ ] Confirm the Supabase project to point at, and apply `schema.sql`.

### Next engineering steps, in the order I would take them

1. **Live Scout Agent.** The highest-value swap, everything downstream already
   consumes real source rows. **Must include SSRF protection** before it fetches
   a user-supplied URL (see `security.md`, gap 3).
2. **Live Insight Agent.** Retrieval already works; the missing piece is the
   prompt and the check that rejects a claim whose quote cannot be matched back
   to a retrieved chunk.
3. **OpenAI embeddings** in stage 3, replacing Chroma's default.
4. **Live Strategist and Critic.** The Critic's output contract is already
   fixed and tested, which de-risks this.
5. **Supabase Realtime** on `pipeline_states`, replacing polling.
6. **Celery or Edge Functions** once a run can outlive a web worker.
7. **Rate limiting** on auth and the contact form.

### Smaller items

- [ ] Transactional email for the contact form.
- [ ] Email-change flow (password change works; email change is not wired).
- [ ] Numbered migrations, before the schema changes again with real data in it.
- [ ] Dependency scanning in CI.
- [ ] Component tests for the stepper itself (currently covered indirectly).
- [ ] `chromadb` is not installed in the verification venv, so
      `vectorstoreAvailable` reports `false` and stage 3 counts chunks without
      persisting vectors. This is the documented graceful degradation, not a
      failure, but a full install should be verified before the defence.

---

## Deviations from the spec

Flagged rather than absorbed silently.

1. **`api/v1/agents/` holds service modules, not routes.** Agents are invoked
   by the pipeline service, not over HTTP; a router there would create an
   endpoint that should not exist.
2. **Two endpoints added**, `GET .../reviews` (the HITL audit trail) and
   `GET .../cost` (the run-cost readout). Both are user-visible features.
3. **Two tables added**. `pipeline_states` (run state has to persist across a
   background run) and `content_suggestions` (stage 9 was built as a real
   feature).
4. **`email-validator`** added to `requirements.txt`; Pydantic's `EmailStr`
   requires it.
5. **`tailwindcss-animate`** added to the frontend; it supplies the enter/exit
   keyframes the Radix primitives expect.

---

## Bugs found and fixed during verification

Recorded because each one was invisible to the type checker and to the unit
tests as first written.

| Bug | How it showed up | Fix |
|---|---|---|
| **`MemoryRepository` writes were invisible across instances.** Rebinding a class-level store through `self` (`self._gaps = [...]`) creates an *instance* attribute that shadows the shared one, so the background worker's writes never reached the repository serving the next request. | The end-to-end run reported "7 gaps identified" while `GET /gaps` returned an empty list. | Rebind through the class. `tests/test_repository.py` now covers the worker-writes-then-request-reads path that exposed it. |
| **Chunking degraded to roughly one chunk per character** when the overlap approached the window size. | A pathological-input test ran to ~4,900 chunks on 5,000 characters. | Clamp overlap to at most half the window. |
| **The Critic's mandatory measurement step pushed a plan back over the action cap** it had just been trimmed to. | The trim test saw 7 actions after a cap of 6. | The last optional step now gives way, so measurement is never the thing dropped. |
| **The demo project was not actually parked at checkpoint 1.** Its pipeline state was created empty on first read, so stage 5 was `idle` rather than `awaiting_human`. | Submitting a gap review on the demo project returned 409. | Seeded a real parked state: stages 1, 4 complete, stage 5 awaiting a human. |
| **FastAPI rejected `status_code=204` with a `-> None` annotation.** | The app would not import. | `response_class=Response` and an explicit `Response` return. |

---

## Environment

Built and verified on Windows 11, Node 22.19.0, npm 11.13.0, Python 3.13.5.
