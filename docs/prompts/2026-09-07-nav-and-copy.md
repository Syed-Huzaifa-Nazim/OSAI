# Build log, 2026-09-07: top nav redesign and dash removal

Last updated: 2026-09-07

---

## What was asked

1. Give the horizontal (top) navigation the same treatment the vertical rail
   got: bolder, more distinctive.
2. Remove the em dashes, which read as AI generated.

---

## 1. Top navbar

Rebuilt so the two navigation variants read as one brand rather than one
designed piece and one default.

**It changes shape as you scroll.** At the top of a page the bar is full width
and transparent, leaving the hero uninterrupted. Past 24px it contracts into a
floating glass pill (1152px wide, fully rounded, with a drop shadow), so the
chrome only takes up space once it has a reason to.

**A honey pill slides between the links.** Same shared layout id technique as
the rail's marker, so the active state moves rather than jumping.

**A reading-position hairline** sits across the very top, driven by scroll
progress through a spring.

**The mobile menu is a full-screen numbered index**, not a dropdown. It uses the
rail's typography, its `01`..`06` numbering and its pull-quote, so switching
variants does not feel like switching products. Body scroll is locked while it
is open, and it uses the self-managed mount from the previous session, so it
leaves the DOM cleanly after a navigation.

Verified in a browser: pill geometry, progress scaling, both themes, and the
mobile menu unmounting with zero stray focusable elements.

---

## 2. Em dashes

324 em and en dashes across the codebase, docs and copy. All gone; the rendered
pages now contain zero dash characters in either navigation variant.

Rather than swapping one character for another, the rewrite sorted each
occurrence into one of three cases, because a comma splice reads worse than the
dash it replaced:

| Case | Example | Becomes |
|---|---|---|
| Label separator | `Human Review - Gap Refinement` | colon |
| Independent clause | `not a fallback - it is a peer view` | full stop, capitalised |
| Tight aside | `the policy - announced today - is` | commas, or parentheses when the aside has its own commas |

The author's original brief in `Claude Prompts in md/` was excluded. It is an
input, not project text.

### What the automation got wrong, and how it was caught

The tidy-up regexes used `\s`, which matches newlines. That collapsed content
across line boundaries in seven places, including live code:

- `router.tsx`: a comment ran into the `...featureRoutes()` spread below it,
  which broke the build.
- `api-client.ts`, `use-insights.ts`, `demo-data.ts`, `marketing-sidenav.ts`:
  spread operators lost their separating comma (`{ ...gap, ...patch }` became
  `{ ...gap...patch }`).
- Three JSDoc blocks had their continuation `*` pulled onto the previous line.

The paired-aside rule had the same flaw, and paired a dash on one table row with
a dash on the next. In the README's stage table that produced an opening
parenthesis in row 3 and its closing partner in row 4.

Two of them were ranges rather than punctuation. The stage labels on the
landing page came out as `Stages 2: 3` and `Stages 8: 9`. Both are hyphenated
ranges now.

All of it was found by the type checker, a targeted scan for unbalanced
parentheses in prose, and a read-through of every change to visitor-facing copy.
The README stage table and team list were rewritten by hand.

**The lesson worth keeping:** a repo-wide regex rewrite needs line-anchored
patterns and a compile step behind it. The type checker caught five of the seven
collapses within seconds; the other two were in comments and needed the scan.

---

## Verification

| Check | Result |
|---|---|
| `tsc --noEmit` | 0 errors |
| `vitest run` | 85 / 85 passed |
| `pytest` | 34 / 34 passed |
| `vite build` | Succeeds, no size warnings |
| Browser, both nav variants, six pages | All render, zero dash characters in the output |
| Scroll stability on the landing page | Holds position |
| Console errors | None |
