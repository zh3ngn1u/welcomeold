# Architecture for your own frontend against this API

The vendor's own design already keeps the secrets server-side. Follow it — and go further, because
their client has some sharp edges this document fixes.

```
┌──────────────────┐   HTTPS/JSON    ┌──────────────────┐   Bearer + cookies   ┌────────────────────────┐
│  Your frontend   │ ──────────────▶ │  Your backend    │ ───────────────────▶ │ backend.blokmarket.   │
│  (browser)       │  same-origin   │  (holds secrets) │                      │ store  (dashboard API) │
│                  │   /api/*       │                  │                      ├────────────────────────┤
│  NO credentials  │ ◀────────────── │  own auth, own   │  no auth header      │ spoofer.blokmarket.   │
│  ever            │   SSE or poll  │  rate limiting   │  Roblox creds        │ store  (spoof engine)  │
└──────────────────┘                └──────────────────┘                      └────────────────────────┘
                                                                                    │
                                                                    Roblox Open Cloud / CDN
```

Three rules, in priority order:

1. **Your browser must never hold `BMK_TOKEN`, `ROBLOX_COOKIE` or `ROBLOX_TOKEN`.**
2. **Your backend is the only thing that talks to the vendor.**
3. **Your backend is the only place that enforces business rules** (batch size, cost, quotas) —
   because the vendor's client-side caps are advisory.

---

## What must happen server-side, and why

| Call | Where | Reason |
|---|---|---|
| `POST engine /api/download/batch/async` | **Backend** | Carries `X-Roblox-Cookie` — a live Roblox session. A browser cannot hold it safely. |
| `POST engine /api/upload/batch` | **Backend** | Carries `roblox_access_token`. Irrevocable write into a real Roblox experience. |
| `POST /api/auth/spoofer-deduct` | **Backend** | Spends money. Must be atomic with job creation. |
| `POST /api/spoofer-jobs` / `PATCH /api/spoofer-jobs/:id` | **Backend** | Audit trail. Trust the server's copy. |
| `GET /api/auth/spoofer-check-cost` | **Backend** | Price must come from the server, never from client arithmetic. |
| `GET /api/auth/me`, `/auth/spoofer-state` | **Backend** | `BMK_TOKEN`. Forward only the fields your UI needs. |
| B2B portal + `key/rotate` | **Backend, admin-only** | `rotate` returns the **full** `rawKey` and invalidates the old one. |
| `GET /api/upload/*` | **Backend** | Quota and job state. |
| `GET engine /api/proxy/roblox-thumbnail` | Either | Public, no credential, CORS-open. Proxy it anyway to cut browser→vendor traffic. |
| `GET /api/product`, `/product/category`, `/upload/health`, `/audio/approved-count`, `/audio/approved-daily-stats` | Either | Public. Cache on your backend; these barely change. |
| `GET engine /openapi.json` | Backend | Cache at build time. |

### The one thing you can let the browser do directly
Thumbnails. `GET /api/proxy/roblox-thumbnail` is public and the engine echoes any `Origin`, so a
plain `<img src>` works. Everything else needs a proxy.

---

## Credentials: how to stop users exposing them

| Risk | Mitigation |
|---|---|
| Token in browser JS / bundle | Never send it. Proxy everything. |
| Token readable by an XSS on *your* origin | Keep the token in your backend's process memory or a secrets manager — **not** `localStorage`. The vendor stores three high-value secrets in plaintext `localStorage`; don't copy that. |
| Vendor's Roblox bearer travels as a **query parameter** | It lands in access logs, browser history and `Referer`. Prefer the `X-Roblox-Cookie` header. Never build such a URL in client-side code, and strip `Referer` on your own routes. |
| Users uploading **their own** Roblox cookie | **Don't accept it at all.** Have each user create an Open Cloud API key and store it encrypted per-account, or run the upload server-side with a key you manage. If you must accept a cookie, never echo it back in any response body. |
| `rawKey` from `POST /b2b/portal/key/rotate` | Return it **once**, to an admin-only route, and never log it. The vendor re-delivers it on every `GET /b2b/portal/status` — don't replicate that. |
| A user calling the engine directly with your key | Keys are `bmk_spoof_`-prefixed and credit-metered. Assume leak is possible: rotate, and monitor `GET /api/b2b/portal/logs` for unexpected `POST /download` volume. |

---

## CORS

Observed, 2026-09-30:

| | `backend` | `engine` |
|---|---|---|
| `access-control-allow-origin` (foreign origin) | **absent** | **echoes the caller's Origin** |
| `access-control-allow-credentials` | `true` | `true` |
| `access-control-max-age` | — | `600` |
| Allowed headers | `Content-Type, Authorization, x-api-key, x-experience-id, Cookie` | `content-type, x-roblox-cookie` |

Consequences for you:

* Your **backend** is unaffected by CORS — it is not a browser. `credentials:"include"` matters
  only for the browser→vendor hop, which you should not make.
* If you proxy the engine, add **your own** strict allowlist. Do not forward
  `Access-Control-Allow-Origin: *` or reflect arbitrary origins; the engine's echo behaviour is
  not a pattern to copy.
* Because the engine reflects origins with credentials allowed, a hostile page that can satisfy
  the preflight can read engine responses. If you expose any engine call directly, restrict it to
  the thumbnail proxy.
* The refresh cookie rides on every `apiFetch` upstream (`credentials:"include"`). Keep your
  equivalent in an `HttpOnly; Secure; SameSite=Lax` cookie, and CSRF-protect the routes that
  mutate state.

---

## Polling

Upstream behaviour, reproduced exactly:

* Interval **1500 ms**, hardcoded, via `setInterval`.
* One active task at a time, guarded by a single interval ref.
* Re-check on `document.visibilitychange` and window `focus`.
* Stops when no asset is `processing`, or on `404`.
* **No retry, no backoff, no timeout, no cancellation.**

What to do differently:

1. **Server owns the poll.** Your backend polls the engine and holds task state in your DB. The
   browser never polls the vendor, so closing a tab does not lose a job and you stop being billed
   for orphaned polling.
2. **Push results to the browser** via SSE. Fall back to browser polling *your* backend at
   2–3 s, never 1.5 s against the vendor.
3. **Add exponential backoff with jitter** on `5xx`/network errors, cap it, and stop after N
   attempts. Upstream has none, so a vendor hiccup silently kills a batch for the user.
4. **Add a hard deadline** (e.g. 30 min) and a max queue wait. Without one, a job that never
   terminates loops forever.
5. **Adopt backpressure.** Upstream accepts 500 IDs per request with no rate control. Enforce
   your own per-account concurrency and queue, because the vendor advertises 60/180/600 req-min
   limits and will return `402` (out of credits) or `429` (rate limited).
6. **Reconcile on start-up.** Upstream resumes from `localStorage`, which is lost if the user
   clears it. Persist `task_id` server-side and re-attach on login.

---

## Error handling

Two incompatible error shapes — normalise them at your boundary so the rest of your app sees one
type.

| Origin | Shape | Example |
|---|---|---|
| Engine (FastAPI) | `{"detail": "string"}` **or** `{"detail": [{loc,msg,type,input}]}` | `{"detail":"Task not found."}` |
| Backend (Express-style) | `{"success":false,"message":"string"}` | `{"success":false,"message":"No token"}` |

Required mappings:

| Status | Meaning | Your behaviour |
|---|---|---|
| `401` (engine upload) | Roblox token rejected | Mark the stored credential dead, stop the loop, prompt the user to re-link. Upstream aborts the whole batch — isolate the failure to one asset instead. |
| `402` | Out of B2B credits | Stop, notify, top-up. Only seen as an admin log-filter label, not live. |
| `429` | Rate limited | Back off. Honour `Retry-After` if present. |
| `400 / 422` (engine) | Validation | Surface the `detail` — it is specific and user-actionable. |
| `404` on task status | Task gone or expired | Mark the task terminal-unknown; do not retry. |
| `401` (backend) | `bmk_token` expired | **Do not attempt the vendor's refresh — `/api/auth/refresh` is `404`.** Re-authenticate your user. |
| network error | vendor unreachable | Retry with backoff; surface a queued state, not a failure. |

---

## Rate limits

**Not observable.** Across 44 requests no `429`, `Retry-After` or `X-RateLimit-*` header appeared,
and no burst was generated — so real limits may exist and simply were not triggered. The only
evidence is the plan tables (60/180/600 req-min) and the admin log filter's `429 Rate / Limit`
option, both client-side marketing/UI strings.

So: treat limits as **unknown and non-zero**. Implement your own quotas per account, keep a
request budget, and prefer the batch endpoints (1 call for up to 500 assets) over per-asset
calls. The engine's `/api/upload/batch` takes an array but the dashboard sends **one asset per
request in a serial loop** — batching them yourself is strictly better and may change your
billing.

---

## Suggested backend shape

```
POST /api/spoof/quote            -> { cost, has_ugc }     (server: check-cost)
POST /api/spoof/jobs             -> { jobId }             (server: deduct + batch/async + record)
GET  /api/spoof/jobs/:id         -> job row + live engine status
GET  /api/spoof/jobs/:id/stream  -> SSE progress
POST /api/spoof/jobs/:id/upload  -> server: engine /api/upload/batch (batched, not serial)
GET  /api/spoof/jobs             -> your own history table
```

Job table columns worth persisting: `job_id`, `engine_task_id`, `user_id`, `asset_ids`,
`status`, `total_assets`, `success_count`, `failed_count`, `asset_breakdown`, `zip_url`,
`cost`, `created_at`, `updated_at`, `error`.

### Server-side rules to enforce (the vendor's client enforces none reliably)

| Rule | Upstream value | Note |
|---|---|---|
| Max IDs per batch | 500 | client-side only — enforce it yourself |
| Filename sanitiser | `/[\\/:*?"<>|]/g → "_"` | trivial to bypass from outside the UI |
| Experience image | `< 1,048,576` B | client-side only |
| Audio duration | `420` s | client-side only |
| Cost tiers | `0/15/30/50` by asset count | **display only**; the server's price is authoritative |

Do not compute what a user owes from those numbers. Call `/auth/spoofer-check-cost`, and treat
`/auth/spoofer-deduct` as the only source of truth.

---

## Before you build

Three things are **NOT CONFIRMED FROM FRONTEND** and will need the vendor:

1. **`bmk_token` issuance.** You need a real account and a way to obtain a token. The vendor's
   email/password login has **no client call site in the downloaded bundles**, and the documented
   OAuth routes return HTML meant for a popup. If you are not a B2B tenant, a browser-only flow
   may not be feasible — which is itself a reason to proxy server-side.
2. **The B2B Mesh gateway.** The seller-facing `POST /download` / `GET /account/me` API is on a
   host that appears **nowhere** in the bundles or the public spec, and 404s on both known
   origins. Ask the vendor for it.
3. **Actual pricing and limits.** Every price table and rate limit in the bundle is client-side
   marketing. Get the real numbers in writing.

And one thing worth deciding deliberately: the engine's own spec describes scanning Roblox
experiences for asset IDs and re-uploading them under a new creator ID, including a `place_id`
parameter documented as *"Optional custom Place ID to spoof for private assets"*. That conflicts
with Roblox's Terms of Service, and re-uploading third-party audio without the rightsholder's
permission implicates copyright. This is a property of the service you are integrating, and it
is a decision to make knowingly — not a technical obstacle.
