# OptiStratixAI — Product/UI Redesign Handover

**Last updated:** 17 November 2026  
**Purpose:** This document gives a new agent, supervisor, or collaborator enough context to understand the FYP, the UI problems discovered, the benchmark direction, the work already completed, and the next work to continue.

---

## 1. Product and FYP context

OptiStratixAI is an FYP competitor-intelligence and strategy-support product for non-technical marketers, SMEs, and marketing strategists.

Its intended end-to-end story is:

1. A user adds their brand and one or more competitors.
2. The system reads publicly available website, product-listing, or social-media material.
3. The user sees the evidence collected from both sides.
4. The system surfaces evidence-backed competitor opportunities/findings.
5. A human accepts, rejects, edits, or reprioritises the findings.
6. Approved findings become a strategy with initiatives and deliverables.

### FYP differentiators that must be preserved

- Evidence-linked reasoning: a finding should be traceable to visible source material.
- Human-in-the-loop checkpoints: the user makes the important decisions.
- Critic/review layer: generated strategy should be reviewable, not opaque.
- Competitor intelligence focused on content, positioning, offers, messaging, and public signals.

The product should **not** become a full Semrush, Similarweb, social publishing, or ad-spend platform. Its value is turning public competitor evidence into clear next decisions.

---

## 2. Original UX problems found

The initial UI was technically capable but hard for a new/non-technical user to understand.

| Problem | Why it was harmful |
| --- | --- |
| Nine-stage pipeline language was exposed directly in navigation and screens. | A user had to understand internal implementation before knowing what to do. |
| Labels such as *Scraped data*, *agents*, *embedding*, *parameters*, *crawler*, and *gap analysis* were prominent. | They sounded technical and did not explain user value. |
| Project navigation was fragmented: Pipeline, Insights, Review gaps, Final approval, Document, Automation, etc. | The hierarchy was unclear; related decisions were spread across many screens. |
| Dashboard had generic metrics and activity/status clutter. | It did not answer the user's first question: “What should I do next?” |
| New Analysis looked like a technical configuration form. | It made onboarding feel difficult and did not communicate the benefit. |
| Evidence page exposed raw data before explaining its value. | Users saw posts/pages but not a clear comparison or next action. |
| An early progress-journey connector produced confusing vertical lines and an awkward mobile-like layout. | It looked broken and made the journey difficult to scan. |
| Visuals were mostly cards and raw tables; there were no meaningful animated comparison graphs. | The product looked less credible than competitor-intelligence tools and did not feel domain-specific. |
| A project-list navigation regression could leave Projects blank after returning from Dashboard. | It damaged trust in basic product reliability. |

### User feedback that drove the redesign

- The interface must be easy for a non-technical user.
- Avoid complex technical terms in visible product copy.
- Make the product feel specific to competitor intelligence, not a generic AI dashboard.
- Use attractive, meaningful animated graphics; do not add decorative complexity.
- Keep moving through the redesign phases quickly while maintaining SQA.

---

## 3. Target information architecture

### Signed-in workspace

- Dashboard
- Projects
- Settings

### Project workspace

- Overview
- Evidence
- Findings
- Strategy
- Deliverables

The nine technical/internal stages remain available inside relevant pages, but they are no longer the primary navigation model.

### Intended user flow

```text
Create analysis
  → Read public evidence
  → See both sides visually
  → Find and review opportunities
  → Approve strategy
  → Export deliverables
```

---

## 4. Benchmark and reference analysis

### Product-market benchmarks

| Benchmark | Pattern worth adopting | OptiStratixAI adaptation |
| --- | --- | --- |
| Semrush | Snapshot overview, gaps, actionable opportunity framing. | Show a short evidence summary and convert differences into decisions. |
| Similarweb | Comparison set, historical context, clear benchmark charts. | Show only public-evidence comparisons; never claim unavailable traffic data. |
| Sprout Social | Competitor-profile reports, popular content, audience/content signals. | Compare public posts, media, reactions, comments, hashtags, and examples. |
| Brandwatch | Visual signal exploration and conversation themes. | Use evidence-backed themes/findings later; do not create unsupported social-listening claims. |

### Visual reference images supplied by the user

Two supplied dashboard references were analysed.

#### Reference A: Aurora-style Competitor Intelligence dashboard

Useful patterns:

- A compact top row of competitor cards with small moving trend lines.
- A small number of clearly titled charts instead of one giant data dump.
- Donut chart for composition/mix.
- Side-by-side time/trend graph.
- Horizontal distribution/ranking bars.
- Strong visual hierarchy: cards first, then charts, then detailed evidence.

#### Reference B: Brand vs competitor dashboard

Useful patterns:

- Brand/competitor cards with animated sparklines.
- A donut showing the split between compared sides.
- Grouped/side-by-side bars for direct comparison.
- A larger central line chart for change or variation.
- Minimal labels; each visual answers one simple question.

### Important design decision

The visual language is inspired by these references, but the product must not copy their UI or invent unavailable metrics such as ad spend, visits, impressions, market share, or traffic growth.

All OptiStratixAI graphs must use collected evidence only. For example:

- Posts/pages read
- Visual/media items found
- Reactions/comments from public posts
- Links found on websites
- Words read from pages
- Current project status

---

## 5. Work completed before the current visual pass

### Navigation, routing, and shell

- Project navigation was simplified to **Overview, Evidence, Findings, Strategy, Deliverables**.
- Alias routes were added for `overview`, `findings`, and `deliverables` so the improved hierarchy can reuse existing functional pages during incremental redesign.
- The project landing redirect now opens Overview instead of exposing internal stages first.
- The app shell was adjusted to remove a route-level animation that could leave a blank content area.
- Project/header navigation was made clearer and more consistent.

### Project reliability fix

- Investigated and fixed the issue where projects could disappear after going from Dashboard back to Projects.
- Added/maintained route and project-index behaviour so a valid project returns to the correct workspace view.

### Dashboard and onboarding

- Added a prominent **Next action** area to Dashboard.
- Added a readable four-step journey instead of exposing internal agent/pipeline concepts.
- Simplified New Analysis copy:
  - “Start here” instead of implementation-stage labels.
  - Plain language explaining that the system reads both public links.
  - Better descriptions for comparison type, brand, objectives, competitors, and optional context.
  - “Extra context” replaced “Notes for the agents”.

### Evidence page

- Renamed user-facing “Scraped data” to **Evidence**.
- Added an Evidence coverage summary with counts for both sides.
- Added clear states for reading, empty evidence, failure, retry, and next action.
- Replaced technical copy such as crawler/headless browser/Apify/embedding with plain-language progress text.
- Added an obvious **Find opportunities** CTA after social evidence is ready.
- Renamed raw source area to **Source library**.
- Fixed the broken-looking journey connector/vertical lines and made the journey compact and horizontally readable.

---

## 6. Current visual dashboard work (latest implementation)

### Evidence visual intelligence panel

A new reusable component was added:

`frontend/src/components/shared/visual-intelligence.tsx`

It adds a compact visual comparison section to Evidence with the following pieces.

| Visual | Purpose | Data source |
| --- | --- | --- |
| Two side cards | Immediate “your side vs competitor side” understanding. | Posts/pages read and reaction/link totals. |
| Animated SVG sparklines | Adds motion and shows variation in collected items. | Public-post reactions by post, or website page-word counts by page. |
| Donut: Reading split | Shows how much material was collected from each side. | Number of posts/pages read. |
| Animated line chart | Compares activity across collected posts/pages. | Reactions per post for social; words read per page for websites. |
| Animated horizontal bar chart | Shows the direct evidence-count comparison. | Posts/pages, visuals, reactions/links. |

The animations use Framer Motion and Recharts. They animate into view and retain readable table alternatives through the existing chart-frame pattern.

### Dashboard visual intelligence panel

Dashboard now includes:

- A small workspace snapshot: all analyses, ready analyses, and analyses waiting for the user.
- A donut showing where analyses currently are.
- An animated bar chart showing what happens next: ready, needs you, and working.

This deliberately stays small. Dashboard should direct a user to their next action, not become an overwhelming reporting screen.

---

## 7. Key implementation files

| Area | File(s) |
| --- | --- |
| Main redesign plan | `docs/product-redesign-roadmap.md` |
| This handover | `docs/optistratixai-agent-handover.md` |
| Visual dashboards and animation | `frontend/src/components/shared/visual-intelligence.tsx` |
| Four-step plain-language journey | `frontend/src/components/shared/analysis-journey.tsx` |
| Dashboard | `frontend/src/pages/app/dashboard.tsx` |
| New Analysis/onboarding | `frontend/src/pages/app/project-new.tsx` |
| Evidence workspace | `frontend/src/pages/app/project-sources.tsx` |
| Project routes | `frontend/src/app/router.tsx` |
| Project navigation model | `frontend/src/components/layout/nav-config.ts` |
| Project default route | `frontend/src/app/project-index-redirect.tsx` |
| Route helpers | `frontend/src/lib/project-routes.ts` |

---

## 8. Quality assurance completed

The following checks were run after the redesign changes:

| Check | Result |
| --- | --- |
| TypeScript typecheck | Passed |
| Targeted New Analysis tests | Passed |
| Targeted Evidence tests | Passed |
| Combined targeted test total | 16/16 passed |
| Production frontend build | Passed |

### Known test warning

Recharts emits width/height-zero warnings in the jsdom test environment because it has no real layout dimensions. Tests still pass and the production build succeeds. This is a test-environment warning, not a confirmed browser-runtime failure.

### Visual QA limitation

Local Chrome was opened on the Evidence page, but the computer-use preview refresh was stopped by the automation environment because it could not confidently verify the current browser URL. The new visual UI compiled successfully and is covered by the Evidence render tests, but it should still be visually inspected in the local browser after a manual refresh.

---

## 9. What is intentionally not done yet

- Findings/review screen has not yet been redesigned into a focused human decision queue.
- Strategy/Critic/Final approval experience has not yet been merged into a clean strategy-review flow.
- Deliverables/export experience still needs a user-facing redesign.
- Evidence filters, drawers, source excerpts, and per-finding evidence tracing need deeper work.
- Mobile/responsive visual QA needs a dedicated pass.
- The New Analysis form is clearer, but it is not yet a fully paginated wizard.
- More visual assets/illustrations can be added later, but only where they clarify a decision; they should not be decorative filler.

---

## 10. Recommended next phases

### Next: Findings and human review

Build a non-technical **Findings** screen where each card answers:

- What did we notice?
- Why does it matter?
- What evidence supports it?
- What should the user do next?
- Accept, reject, edit, or change priority.

### Then: Strategy and critic review

- Show initiatives produced only from accepted findings.
- Show the linked evidence/findings beside every initiative.
- Display critic feedback as before/after improvements, not as an unexplained score.
- Make approval status obvious: Draft, Needs changes, Ready to approve, Approved.

### Then: Deliverables and FYP demo polish

- Make documents/assets easy to preview and export.
- Create one seeded demo project with a complete story.
- Prepare a five-minute FYP demo:
  1. Add/choose a brand and competitor.
  2. Show evidence collection.
  3. Show visual comparison.
  4. Review an opportunity with evidence.
  5. Approve a strategy initiative.
  6. Open/export a deliverable.

---

## 11. Instructions for the next agent

1. Read this document and `docs/product-redesign-roadmap.md` first.
2. Preserve the simplified information architecture; do not reintroduce internal pipeline stages as primary navigation.
3. Preserve plain language for user-facing copy. Technical words may exist in code/comments or a technical appendix, not in primary user flows.
4. Do not fake analytics. Every visible metric/chart must be derived from available data and named honestly.
5. Prefer one clear action per screen over many equal-priority buttons.
6. Keep the FYP's evidence trail, human review, and critic validation visible—they are the actual product differentiators.
7. Run typecheck, relevant tests, and production build after each substantial UI phase.
8. Check loading, error, empty, partial-data, and mobile states whenever a screen is changed.

---

## 12. Suggested prompt for a new agent

> Read `docs/optistratixai-agent-handover.md` and `docs/product-redesign-roadmap.md` first. Continue the OptiStratixAI FYP redesign without undoing the simplified navigation or plain-language UI. The completed work includes Evidence and Dashboard visual-intelligence panels that use only real collected data. Next, redesign the Findings review experience for a non-technical user, preserving evidence links, human approval, and the critic workflow. Run TypeScript typecheck, relevant tests, and a production build before handing back changes.
