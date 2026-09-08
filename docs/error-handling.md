# Error handling

Last updated: 2026-09-06

One contract, both halves. The rule underneath all of it: **a user should never
see a raw exception, and a developer should always be able to find one.**

---

## 1. The wire format

Every failure (validation, auth, not-found, unhandled), leaves the API in the
same shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Some of the values you submitted are not valid.",
    "fields": { "brandDescription": "String should have at least 40 characters" },
    "requestId": "9c1f2b7e-4a2d-4f77-9e01-2b3a4c5d6e7f"
  }
}
```

| Field | Always | Purpose |
|---|---|---|
| `code` | yes | Machine-readable; drives client branching |
| `message` | yes | Safe to show a user verbatim |
| `fields` | validation only | Keyed by field name, so a form attaches each to its input |
| `requestId` | yes | Echoed in `X-Request-ID`; quotable in a bug report |

### Codes

| Code | HTTP | Meaning |
|---|---|---|
| `validation_error` | 422 | Field-level; `fields` is populated |
| `unauthorized` | 401 | No token, or not valid |
| `token_expired` | 401 | Valid but expired: re-login, do not retry |
| `auth_misconfigured` | 401 | **Server** problem: JWT secret missing |
| `forbidden` | 403 | Authenticated but not permitted |
| `not_found` | 404 | Missing, or not yours, deliberately indistinguishable |
| `conflict` | 409 | Valid request, wrong state (see below) |
| `service_unavailable` | 503 | A dependency is missing |
| `internal_error` | 500 | Unhandled; detail is logged, never returned |

**`conflict` carries real product meaning here.** It is what the API returns
when the pipeline refuses to advance: submitting a gap review with untriaged
gaps, or requesting a revision with no notes. These are not client bugs. They
are the checkpoints doing their job, and the message says exactly what is
missing.

---

## 2. Backend

### Raising

```python
from app.core.errors import ConflictError, NotFoundError

raise NotFoundError("That project does not exist, or you do not have access to it.")
raise ConflictError(
    f"{len(pending)} gap(s) still need a decision. Every gap has to be kept or "
    "dropped before this checkpoint can close."
)
```

Handlers in `core/errors.py` convert these, Pydantic validation failures,
Starlette HTTP errors and anything unhandled into the envelope.

### Message rules

1. **Say what to do, not what broke.** "Every gap has to be kept or dropped
   before this checkpoint can close" beats "invalid state".
2. **Never leak internals.** The 500 handler logs `exception()` with the request
   id and returns a fixed sentence.
3. **Do not confirm what a stranger should not learn.** A project that exists
   but belongs to someone else returns the same 404 as one that never existed.
4. **Distinguish a deployment gap from a client error.** A missing `reportlab`
   is a 503 saying `pip install -r requirements.txt`, not a 500.

### Logging

`RequestContextMiddleware` tags every request, echoes `X-Request-ID`, and logs
method, path, status and duration:

```
2026-09-06 13:44:28 INFO  optistratix.request POST /api/v1/projects/abc/gaps/review -> 409 (1.3ms) request_id=d7929855-...
```

Background tasks catch and log everything. A crashed background run must not be
silent:

```python
try:
    asyncio.run(pipeline_service.run_from(project_id, user_id, stage))
except Exception:
    logger.exception("Background pipeline run failed for %s", project_id)
```

A stage that fails is marked `error` with the message attached, and the run
stops. It never leaves the pipeline claiming to be running.

---

## 3. Frontend

### `ApiError`

`lib/api-client.ts` parses the envelope into a typed error:

```ts
error.status        // number  (0 = network failure, no response at all)
error.code          // string
error.fields        // Record<string, string>
error.requestId     // string | undefined
error.isAuthError   // 401 | 403
error.isRetryable   // 5xx, 408, 429
```

`isRetryable` drives the query client's retry policy, so a 422 is never retried
(it will not succeed) and a 500 is retried twice.

### Which surface an error uses

| Situation | Surface |
|---|---|
| Field-level validation | Inline under the input, via `FormField` |
| Whole-form failure (bad credentials) | `role="alert"` banner above the form |
| Mutation failure (save, delete, generate) | `toast.error` with the message as description |
| Query failure on a page's main content | Full `ErrorState` with a retry button |
| Render crash | `ErrorBoundary`. Contains the panel, keeps the shell alive |

### Three states, everywhere

Every surface that fetches data renders all three, designed rather than default:

```tsx
{isError ? (
  <ErrorState message={errorMessage(error)} onRetry={() => void refetch()} />
) : isLoading ? (
  <LoadingState rows={4} />
) : items.length === 0 ? (
  <EmptyState title="..." description="..." action={...} />
) : (
  <Content />
)}
```

**Empty states distinguish "nothing yet" from "nothing matches".** On the
insights page, no gaps because the agent has not run says something different
from no gaps because the filters exclude them, and only one of them offers
"clear filters".

The insights empty state also handles a third case honestly: the Insight Agent
ran and found nothing it could support with evidence. That is a real result, and
the copy says so rather than implying a failure.

### Optimistic updates

Gap triage at HITL #1 is optimistic: the reviewer clicks through a list at
speed, and a round trip per click would make the checkpoint feel like a chore,
which is the wrong incentive for the feature the product's credibility rests on.

`onError` rolls the cache back and raises a toast, so a silent failure is not
possible:

```ts
onError: (error, _variables, context) => {
  if (context?.previous) client.setQueryData(key, context.previous)
  toast.error('Could not save that change', { description: errorMessage(error) })
}
```

### Network failures

A `fetch` that never gets a response becomes `ApiError` with `status: 0` and the
message *"Could not reach the OptiStratixAI API. Check your connection."*, not
a `TypeError: Failed to fetch`.

---

## 4. What is not handled yet

| Gap | Consequence |
|---|---|
| No error reporting sink | `ErrorBoundary` logs to `console.error`; nothing aggregates them. Sentry is the obvious fit |
| No global 401 interceptor | Each caller handles auth errors; a central "expired → redirect to login" would be cleaner |
| No retry-after handling on 429 | Retried on the default backoff, ignoring the header |
| Toasts are not deduplicated | A burst of failures stacks |
