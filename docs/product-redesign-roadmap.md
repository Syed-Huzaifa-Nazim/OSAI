# OptiStratixAI Product Redesign Roadmap

## Objective

Reframe OptiStratixAI from a technically impressive multi-agent demo into a clear competitor-intelligence product:

> Show the evidence behind a competitor gap, let the marketer decide whether it matters, and turn approved gaps into an actionable strategy.

The redesign must preserve the FYP differentiators: evidence-linked reasoning, critic validation, and human approval.

## Target information architecture

### Public website

- Home
- How it works
- Features
- Pricing / project status
- About
- Contact

Technical terms such as RAG, vector store, and agent orchestration stay on How it works or a technical appendix.

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

The existing internal stages remain available inside the relevant sections, but they should not all appear as top-level navigation items.

## Proposed user flow

1. Create analysis: brand, competitors, goal, audience, channels.
2. Collect evidence: show source coverage and collection status.
3. Compare: show competitor benchmarks and meaningful differences.
4. Review findings: accept, reject, edit, or prioritise evidence-backed gaps.
5. Generate strategy: convert approved gaps into initiatives.
6. Critic review: show unsupported claims, weak logic, and revisions.
7. Approve strategy: human checkpoint with version history.
8. Export deliverables: strategy document and content/action assets.

## Phases

### Phase 0: Product foundation and measurement

Goal: freeze the product language and prevent more UI complexity from being added.

Tasks:

- Create a shared vocabulary: evidence, finding, gap, initiative, approval, deliverable.
- Replace technical labels in user-facing surfaces.
- Define the primary user persona: SME marketer or marketing strategist.
- Define one seeded demo project and one complete happy path.
- Add a route/page inventory and mark each page as keep, merge, rename, or remove.
- Define baseline usability checks: first-action clarity, navigation count, review completion, export completion.

Exit criteria:

- One approved information architecture.
- One end-to-end demo story.
- No ambiguous duplicate concepts such as Insights vs Review gaps without explanation.

### Phase 1: Navigation and shell simplification

Goal: make the workspace understandable in ten seconds.

Tasks:

- Change project navigation to Overview, Evidence, Findings, Strategy, Deliverables.
- Move Pipeline into Overview as a progress component.
- Merge Insights and Review gaps into Findings.
- Merge Strategy and Final approval into Strategy with visible draft/review/approved states.
- Move Document and Automation under Deliverables.
- Add a clear project header with project name, competitor count, status, last updated, and primary next action.
- Add an always-visible “Continue review” or “Create analysis” action.

Exit criteria:

- A new user can identify the next action without opening the sidebar.
- No project screen requires understanding the nine-stage architecture before use.

### Phase 2: Dashboard and onboarding redesign

Goal: make the first meaningful action obvious.

Tasks:

- Replace generic dashboard metrics with active work, pending reviews, recent findings, and recent deliverables.
- Redesign new analysis as a short guided setup.
- Use progressive disclosure for advanced options.
- Show estimated scope: sources, competitors, and expected analysis steps.
- Add a seeded demo entry point for FYP evaluation.
- Add meaningful empty states for no projects, no evidence, no findings, and no deliverables.

Exit criteria:

- User can start an analysis in under two minutes.
- Dashboard always provides a clear next action.

### Phase 3: Evidence-first comparison experience

Goal: make trust visible and make the product different from generic AI tools.

Tasks:

- Create an Evidence workspace with Website, Social, Product/content, and Reviews/forums filters.
- Show source URL, collection date, source type, excerpt, media preview, and relevance.
- Add evidence drawer from every finding.
- Add competitor comparison summary with side-by-side strengths, gaps, and examples.
- Add source coverage and data freshness indicators.
- Replace decorative-only visuals with screenshots, excerpts, charts, and source-linked examples.

Exit criteria:

- Every generated finding can be traced to at least one visible source.
- Users can compare competitors without reading raw scraped output.

### Phase 4: Findings and human review workflow

Goal: turn AI output into a confident human decision.

Tasks:

- Build finding cards with title, impact, evidence, competitor example, confidence, and recommended action.
- Add accept, reject, edit, reprioritise, and comment actions.
- Add “Why am I seeing this?” explanations.
- Group findings by business area rather than by agent or pipeline stage.
- Add review queue counts and clear pending states.
- Preserve an audit trail for human decisions.

Exit criteria:

- A reviewer can process findings in a focused queue.
- Rejected findings cannot silently reappear in the final strategy.

### Phase 5: Strategy and critic experience

Goal: show how approved findings become realistic initiatives.

Tasks:

- Generate initiatives only from approved findings.
- Show the source findings beside every initiative.
- Add priority, effort, expected outcome, channel, owner, and timeline fields.
- Present Critic feedback inline with before/after revisions.
- Add draft, needs revision, and approved states.
- Add version history and approval notes.

Exit criteria:

- A reviewer can explain why every strategy item exists.
- Critic output is actionable instead of being another opaque score.

### Phase 6: Competitor benchmark layer

Goal: adopt the strongest proven patterns from market leaders without copying their product scope.

Benchmark patterns to implement:

- Semrush: snapshot overview, keyword/content gaps, channel-level competitor views, and actionable opportunity framing.
- Similarweb: comparison set, traffic/engagement-style benchmarks, historical change, and market context.
- Sprout Social: competitor profile reports, popular content, hashtag/topic comparisons, and shareable summaries.
- Brandwatch: market conversation themes, audience interests, trends, and visual signal exploration.

OptiStratixAI-specific implementation:

- Keep the benchmark focused on messaging, content, offers, positioning, and strategic gaps.
- Do not attempt to rebuild a full SEO, traffic intelligence, or social publishing suite.
- Convert each benchmark into a decision: what changed, why it matters, and what the user can approve.
- Label estimated or scraped metrics clearly so they are not mistaken for first-party analytics.

Exit criteria:

- Comparison screens show context, not isolated metrics.
- Each benchmark metric has a clear relation to a finding or strategy decision.

### Phase 7: Visual system and responsive polish

Goal: make the product feel credible, calm, and evidence-led.

Tasks:

- Reduce repeated glass cards and decorative containers.
- Use one dominant visual hierarchy per screen.
- Reserve emerald/jade for primary actions and positive signals.
- Reserve amber for warnings and human checkpoints.
- Use neutral surfaces for evidence and long-form content.
- Add realistic product screenshots to marketing pages.
- Audit image alt text, fallbacks, loading states, and broken asset URLs.
- Test mobile sidebar, comparison tables, evidence drawers, and review actions.

Exit criteria:

- No critical content depends on animation.
- Mobile users can review a finding and reach its evidence.
- Visuals explain the workflow instead of only decorating it.

### Phase 8: Validation and FYP demo readiness

Goal: produce a reliable, defensible final experience.

Tasks:

- Run typecheck, unit tests, and production build.
- Add route-level smoke tests for the new hierarchy.
- Add accessibility checks for keyboard navigation, contrast, labels, and focus states.
- Test loading, error, empty, partial-data, and failed-scrape states.
- Verify that demo data supports the complete flow.
- Prepare a five-minute defense walkthrough: problem, evidence, finding, human decision, critic, strategy, deliverable.

Exit criteria:

- Complete demo works without unexplained dead ends.
- Every major claim in the presentation can be shown in the product.
- UI communicates the FYP contribution without requiring a technical lecture first.

## Implementation order

1. Phase 0 and Phase 1 together
2. Phase 2
3. Phase 3 and Phase 4
4. Phase 5
5. Phase 6
6. Phase 7
7. Phase 8

## First implementation sprint

The first code sprint should be limited to the shell and terminology so later work has a stable foundation:

- Add the new project navigation model.
- Add a project header with primary next action.
- Route existing pages through the new grouped sections.
- Rename user-facing technical labels.
- Add an Overview page that contains the existing pipeline as a progress component.
- Add tests for route reachability and active navigation state.

Do not add more charts, agents, or decorative cards until this hierarchy is working.

