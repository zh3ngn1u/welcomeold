# API Client Specification — Blokmarket spoofer / B2B

Derived **exclusively** from the downloaded frontend bundles in `analysis/js/` and from the
service's own public OpenAPI spec in `analysis/api/spoofer-engine-openapi.json`.
Nothing here is invented. Where the frontend does not reveal something, it says so.

**No account was authenticated during this analysis.** All 44 live probes were unauthenticated
`curl`. Fields marked `[read]` were read from a response handler in the bundle; fields marked
`[seen]` actually appear in a captured response in `analysis/api/responses/`. Nothing is marked
both unless it was truly observed.

---

# API Configuration

## Base URLs — there is no single base. Three origins.

| # | Base | Role | Same-origin? | Auth |
|---|---|---|---|---|
| 1 | `https://backend.blokmarket.store` | Dashboard app API (coins, jobs, B2B portal, admin) | **No** — cross-origin from `customer.blokmarket.store` | `Authorization: Bearer <bmk_token>` |
| 2 | `https://spoofer.blokmarket.store` | Spoofer engine (the actual work) | **No** | **none at the HTTP layer** |
| 3 | `https://audio.blokmarket.store` | Media file host | **No** | none observed |

## Exact literals from source

```js
// module 4989 — backend host
let t = "https://backend.blokmarket.store".replace(/\/+$/,"") || "http://localhost:3001";
function o(e){ let o = e.startsWith("/") ? e : `/${e}`; return `${t}/api${o}` }

// bulk-spoofer chunk — engine host
et = "https://spoofer.blokmarket.store/",
ea = et.endsWith("/") ? et.slice(0,-1) : et          // -> "https://spoofer.blokmarket.store"

// media host (module 4989)
download: (e,t) => `https://audio.blokmarket.store/api/download/${e}/${t}`
```

**Path prefixes**

| Origin | Prefix | Builder |
|---|---|---|
| backend | `/api` + path | `buildApiUrl()` |
| engine | **none** — paths are literal, e.g. `/api/download/batch/async` | template strings |

**Protocol** — HTTPS everywhere. The `http://localhost:3001` string is a build-time fallback that
ships in production; never use it.

**Env var name** — `NEXT_PUBLIC_HOST_API` appears in `0k1tyysfi6yay.js` (in a `try { new URL(…) }`
validation, whose result is discarded). The value was **inlined at build time**; the variable is
not read at runtime. Do not expect it to be available.

## Engine service identity (from its published spec `[seen]`)

```
openapi : 3.1.0
title   : "Roblox Asset Downloader Core Service"
version : 1.0.0
desc    : "Python-based high performance asynchronous backend to scan and download
           Roblox audios, animations, and emotes."
docs    : GET /docs, GET /redoc, GET /openapi.json   — all 200 [seen]
```

---

# Authentication

| Property | Value |
|---|---|
| **Token source** | OAuth popup → `postMessage` to the parent window |
| **Token name** | `bmk_token` (localStorage key; header is `Authorization`) |
| **Where frontend reads it** | `localStorage.getItem("bmk_token")` |
| **Where frontend sends it** | `i.set("Authorization", \`Bearer ${a}\`)` in `apiFetch` |
| **Required header** | `Authorization: Bearer <bmk_token>` |
| **Credentials mode** | `credentials: "include"` on every `apiFetch` call |
| **Mandatory?** | Yes for all `/api/**` on the backend. No for the engine. |
| **CSRF header** | **None.** No `X-CSRF-Token` or equivalent exists in any bundle. |
| **sessionStorage** | Not used anywhere. |
| **Refresh** | `POST /api/auth/refresh` on `401` → **404 `[seen]`**. Path is dead; no silent renewal. |

**Second credential — B2B seller key**

| Property | Value |
|---|---|
| Token name | seller API key, prefix **`bmk_spoof_`** |
| Read from | `GET /api/b2b/portal/status` → `rawKey` `[read]`; cached in `localStorage.bmk_b2b_raw_key` |
| Sent to | the B2B Mesh gateway, whose host is **NOT CONFIRMED FROM FRONTEND** |
| Companion | `tenant.webhook_secret` `[read]`, displayed masked to 8 chars |

**Third credential — Roblox**

| Type | Transport | Destination |
|---|---|---|
| `roblox_access_token` | JSON body field | engine `/api/upload/batch` |
| `.ROBLOSECURITY` cookie | header `X-Roblox-Cookie` | engine `/api/download/batch/async` (only when `is_free` is false) |
| `.ROBLOSECURITY` cookie | query `?x-roblox-cookie=` | engine routes per spec `[seen]` |
| OAuth bearer | query `?authorization=` | engine `/api/download/{id}`, `/api/download/batch`, `/api/download/batch/async`, `/api/scan/place/{id}` `[seen in spec]` |
| `roblox_api_key` | JSON body field | `BatchDownloadRequest`, `UploadBatchRequest` `[seen in spec]` |

**Pre-auth gate** — Cloudflare Turnstile. Both OAuth buttons are inert without `turnstileToken`;
it is forwarded as `cf_token`. Site key/secret: **NOT CONFIRMED FROM FRONTEND** (widget is
server-rendered).

---

# Endpoints

## A. Spoofer engine — `https://spoofer.blokmarket.store` (no auth header, no cookies)

### 1. `POST /api/download/batch/async` — create the job

**Headers**
```
Content-Type: application/json
X-Roblox-Cookie: <.ROBLOSECURITY>     # OPTIONAL, only when is_free === false
```
No `Authorization`. No `credentials` mode. Raw `fetch`.

**Request body** — *exactly* what the dashboard sends, verbatim:
```json
{ "assets": [ { "id": 123456789, "custom_name": "optional-name" } ],
  "is_free": false }
```

**Full server schema** (`BatchDownloadRequest` from the spec `[seen]`) — the dashboard uses only
2 of the 6 fields:
| Field | Type | Required | Spec description |
|---|---|---|---|
| `assets` | `AssetBatchItem[]` \| null | no | "Optional list of structured Asset IDs with custom names" |
| `asset_ids` | `integer[]` \| null | no | "Optional flat list of Roblox Asset IDs" |
| `is_free` | `boolean` \| null | no, default `false` | "Is this a free spoof request?" |
| `roblox_api_key` | `string` \| null | no | "Roblox Open Cloud API Key for auto upload" |
| `creator_id` | `string` \| null | no | "Roblox User or Group Creator ID to upload under" |
| `creator_type` | `string` \| null | no | "Creator Type (User or Group)" |

`AssetBatchItem` = `{ id: integer (required), custom_name: string \| null }` `[seen]`.

**Response** — `200` with `{ task_id }` `[read]`.
Spec leaves the success body untyped; the field name `task_id` comes from the frontend:
`let{task_id:l} = await n.json()`.

**Errors observed** `[seen]`
* `400 {"detail":"Either 'asset_ids' or 'assets' must be provided."}` — when both are absent **or empty**
* `422` Pydantic array — when `assets` is not a list

```json
{"detail":"Either 'asset_ids' or 'assets' must be provided."}
```

**Frontend error handling** — on `!res.ok` it reads `s.detail` and uses it as the toast text,
falling back to `"Spoofer engine returned an unexpected error. Please try again."`, and appends a
timestamped `{timestamp, type:"error", text:"Error: "+detail}` line to the log.

---

### 2. `GET /api/task/{task_id}/status` — poll

**Query / path** — `task_id` (path). No headers, no body, no auth.

**Response** — `200`; fields the frontend reads `[read]`:
`status`, `queue_position`, `total_queue`, `assets[]` where each asset has
`id`, `status`, `real_name`, `custom_name`, `asset_type`, `file_name`, `file_size`,
`uploaded_asset_id`, `error`.

**Errors observed** `[seen]` — `404 {"detail":"Task not found."}` for an unknown id.
The frontend treats `404` as "task gone": clears the interval and drops the stored task.

---

### 3. `POST /api/upload/batch` — push results into a Roblox experience

**Headers** `Content-Type: application/json`. No `Authorization`, no `credentials`.

**Request body** — dashboard sends `[read]`:
```json
{ "files": [ { "…one asset…" } ],
  "roblox_access_token": "<roblox oauth token>",
  "creator_id": "<roblox user or group id>",
  "creator_type": "User" }
```
`creator_type` is computed as `roblox_id ? "Group" : "User"` `[read]`.
**One asset per request**, strictly serial — the frontend loops `for(;t<a.length && !e;)`.

**Server schema** `UploadBatchRequest` `[seen]`:
| Field | Type | Required |
|---|---|---|
| `files` | `UploadBatchItem[]` | **yes** |
| `creator_id` | `string` | **yes** |
| `creator_type` | `string` | **yes** |
| `roblox_api_key` | `string` \| null | no |
| `roblox_access_token` | `string` \| null | no |
| `custom_description` | `string` \| null | no |

`UploadBatchItem` = `{ file_name: string (required), display_name: string (required), asset_type: string|null }` `[seen]`.

**Response** — `UploadBatchResponse` `[seen]`: `{ total, success_count, failed_count, results[] }`
where `AssetUploadResult` = `{ file_name, success, asset_id|null, error|null }` `[seen]`.
The frontend reads `results[0]` and treats `401`/`403` or an `error` containing `"401"` /
`"invalid token"` as a dead token `[read]`.

**Error observed** `[seen]` — `{}` →
```json
{"detail":[{"type":"missing","loc":["body","files"],"msg":"Field required","input":{}},
           {"type":"missing","loc":["body","creator_id"],"msg":"Field required","input":{}},
           {"type":"missing","loc":["body","creator_type"],"msg":"Field required","input":{}}]}
```

---

### 4. `GET /api/proxy/roblox-thumbnail` — thumbnail CORS proxy

**Query** `[seen in spec]`: `assetIds` (required), `size` (default `"150x150"`), `format`
(default `"Png"`), `isCircular` (default `false`). The dashboard uses `150x150` in the asset list
and `420x420` in the detail modal.

**Response** `[seen]`:
```json
{"data":[{"targetId":1846853302,"state":"Blocked",
  "imageUrl":"https://tr.rbxcdn.com/…/150/150/UnapprovedImage/Png/noFilter",
  "version":"TN3.5"}]}
```

---

### 5. Engine endpoints NOT called by the dashboard — documented from the spec only

| Method | Path | Purpose | Status |
|---|---|---|---|
| GET | `/api/scan/place/{place_id}?page=1&limit=30` | Scan a Place for Audio/Animation/Emote references | UNTESTED |
| GET | `/api/download/{asset_id}?custom_name&place_id&authorization&x-roblox-cookie` | Single download; returns `DownloadResult` incl. `uploaded_asset_id` | UNTESTED |
| POST | `/api/download/batch` | Synchronous batch; returns `zip_download_url` when >1 success | UNTESTED |
| GET | `/api/asset/{asset_id}` | Asset metadata (cached) | UNTESTED |
| GET | `/api/files/download/{filename}?inline` | Serve a downloaded file | UNTESTED |
| GET | `/api/files/zips/{filename}` | Serve a batch ZIP | UNTESTED |
| GET | `/api/proxy/roblox-thumbnail-3d?assetId` | 3D thumbnail | UNTESTED |
| GET | `/api/proxy/roblox-user-avatar-3d?userId` | 3D avatar | UNTESTED |
| GET | `/api/proxy/roblox-3d-file?url` | rbxcdn.com proxy | UNTESTED |
| GET | `/api/proxy/roblox-toolbox` | Creator Store search | UNTESTED |
| GET | `/api/proxy/roblox-catalog` | Emotes/Animations catalog | UNTESTED |

---

## B. Dashboard backend — `https://backend.blokmarket.store`

All take `Authorization: Bearer <bmk_token>` + `credentials: "include"`.
Error envelope: `{"success":false,"message":"…"}` — **not** `detail`.

### 1. `GET /api/auth/me` — session
No body. Response `[read]`: `success`, `data` → `id`, `name`, `email`, `role`,
`experience_limit`, `plan_type`, `spoofer_state{roblox{roblox_id, roblox_access_token,
roblox_username, roblox_display_name, roblox_api_key}, coins, history[]}`,
`audio_plan`, `audio_plan_expires`.
Observed unauthenticated `[seen]`: `401 {"success":false,"message":"No token"}`.

### 2. `GET|POST /api/auth/spoofer-state` — coin balance
`GET` no body on mount. `POST {"task_id": "<id>"}` to reconcile after a job.
Response `[read]`: `success`, `data.coins` (number), `data.history[]` with `task_id`, `cost`.

### 3. `POST /api/auth/spoofer-check-cost` — price a batch
```json
{ "asset_ids": ["123456789"] }
```
Response `[read]`: `success`, `cost`, `has_ugc`, `message`.
> **Not in the `apiEndpoints` map** — built with `buildApiUrl("/auth/spoofer-check-cost")`.
> Observed unauthenticated `[seen]`: `401`.

### 4. `POST /api/auth/spoofer-deduct` — spend coins
```json
{ "asset_count": 25, "asset_ids": ["…"] }
```
Response `[read]`: `success`, `coins`/`newCoins`, `message`. UNTESTED (spends real balance).

### 5. `POST /api/spoofer-jobs` / `GET /api/spoofer-jobs` / `GET|PATCH /api/spoofer-jobs/:id`
```json
{ "job_id": "<taskId>", "status": "pending", "total_assets": 25,
  "success_count": 0, "failed_count": 0, "asset_breakdown": { "Audio": {"success":0,"failed":0} } }
```
```json
{ "status": "completed", "success_count": 24, "failed_count": 1,
  "asset_breakdown": {…}, "files": [ … ], "logs": [ … last 500 … ] }
```
`files[]` item `[read]`: `{id, custom_name, status, file_name, file_size, asset_type,
uploaded_asset_id, upload_status, upload_error}`.

### 6. B2B Mesh seller portal
| Method | Path | Request | Response `[read]` |
|---|---|---|---|
| GET | `/api/b2b/portal/status` | — | `success`, `tenant{credits_balance, webhook_url, webhook_secret, api_key_prefix, tier, is_active, tenant_name, email, created_at}`, `isLocked`, **`rawKey`** |
| GET | `/api/b2b/portal/logs?page&limit` | query | `success`, `logs[]` |
| GET | `/api/b2b/portal/analytics?days` | query `days` ∈ {1,7,30} | `success`, `daily_metrics[]`, `summary{total_calls,total_errors,error_rate,avg_latency}` |
| POST | `/api/b2b/portal/key/rotate` | **no body** | `success`, `rawKey`, `tenant`, `message` |
| PUT | `/api/b2b/portal/webhook` | `{"webhookUrl":"<url>"}` | `success`, `tenant`, `message` |
| GET | `/api/b2b/portal/pricing` | — | **declared, never called** |
| POST | `/api/b2b/portal/topup` | — | **declared, never called** |

### 7. Public (no auth) — confirmed live `[seen]`
| Method | Path | Observed response |
|---|---|---|
| GET | `/api/product` | `{"success":true,"data":[…]}` |
| GET | `/api/product/category` | `{"success":true,"data":[…]}` |
| GET | `/api/upload/health` | `{"success":true,"data":{"status":"healthy","service":"bmk-upload","active_jobs":0}}` |
| GET | `/api/audio/approved-count` | `{"success":true,"count":32958}` |
| GET | `/api/audio/approved-daily-stats` | `{"success":true,"data":[{"date":"2026-09-30","day":"Wed","count":254}]}` |
| GET | `engine /openapi.json` | full spec |

### 8. Confirmed `401` (`{"success":false,"message":"Unauthorized"}`) `[seen]`
`/api/donation/donatur-leaderboard`, `/api/donation/bypass-logs`, `/api/activity/logs`,
`/api/admin/users`, `/api/spoofer-jobs`, `/api/experience/my-list`,
`/api/payment/check/:id`, `/api/product/global-assets`, `/api/b2b/portal/pricing`,
`/api/b2b/portal/status`, `/api/b2b/portal/logs`, `/api/b2b/portal/analytics`,
`/api/admin/b2b/overview`, `/api/admin/b2b/tenants`, `/api/admin/b2b/logs`,
`/api/spoofer-jobs/admin/all`

### 9. Confirmed `404` `[seen]`
`/api/auth/refresh` (GET **and** POST), `/api/referral/info`, `/api/referral/commissions`,
`/api/account/me`

---

# Request Schemas (quick reference)

```jsonc
// engine — create job
{ "assets": [{ "id": 123456789, "custom_name": null }], "is_free": false }

// engine — upload to Roblox (one asset per request)
{ "files": [{ "file_name": "…", "display_name": "…" }],
  "roblox_access_token": "…", "creator_id": "…", "creator_type": "User" }

// backend — price
{ "asset_ids": ["123456789"] }

// backend — deduct
{ "asset_count": 1, "asset_ids": ["123456789"] }

// backend — create job record
{ "job_id": "…", "status": "pending", "total_assets": 1,
  "success_count": 0, "failed_count": 0, "asset_breakdown": {} }

// backend — update job
{ "status": "completed", "success_count": 1, "failed_count": 0,
  "asset_breakdown": {}, "files": [], "logs": [] }

// backend — b2b webhook
{ "webhookUrl": "https://example.com/hook" }

// backend — b2b credits (admin)
{ "amount": 500, "action": "add" }        // action: "add" | "deduct" | "set"
```

**Multipart** (`FormData`) endpoints `[read]`:
```
POST /api/upload/batch        creator_id, is_group("true"|"false"), target_name,
                              files[] (repeated), access_token="session_auto_resolved"
POST /api/audio/upload-convert file, roblox_speed, amplify_db, modify="true",
                              format, max_duration="420"
POST /api/experience          name, experience_id, image   (client cap: < 1,048,576 B)
```

---

# Response Schemas

## Engine — task status (the "result"; there is no separate result endpoint)
```jsonc
{
  "status": "<terminal state>",            // see job states below
  "queue_position": 3,                     // null when not queued
  "total_queue": 17,
  "assets": [{
    "id": 123456789,
    "status": "success",                   // processing | success | failed
    "real_name": "Original Name",
    "custom_name": "display name",
    "asset_type": "Audio",
    "file_name": "…",
    "file_size": 123456,
    "uploaded_asset_id": "1122334455",     // the "New Spoofed ID"
    "error": null
  }],
  "zip_download_url": "https://…"         // present when >1 asset succeeded
}
```
> `zip_download_url` and `assets[].uploaded_asset_id` are the actual outputs. **The status
> response is the result** — no `/result` route exists `[seen in spec]`.

## Backend — envelope
```jsonc
{ "success": true,  "data": <payload> }              // read endpoints
{ "success": false, "message": "Unauthorized" }       // 401
{ "success": false, "message": "No token" }          // 401 on /auth/me
{ "success": false, "message": "Endpoint not found" }// 404
```
Coin-specific: `{"success":true,"count":32958}` — `count` sits at the **top level**, not under
`data`. Be careful.

---

# Error Handling

| Origin | Shape | Notes |
|---|---|---|
| Engine | `{"detail": "<string>"}` for app errors, `{"detail":[{loc,msg,type,input}]}` for Pydantic validation | FastAPI |
| Backend | `{"success":false,"message":"…"}` | distinct `"No token"` on `/auth/me` |

**Client behaviour to replicate** `[read]`:
1. Network failure → backend call returns a synthetic `{ok:false, status:0, json:()=>({success:false, message:"Connection failed"})}` — the wrapper never throws.
2. `401` → clear `bmk_token`, call `/api/auth/refresh` (currently `404` → hard redirect).
3. Engine `!res.ok` → prefer `detail`; fallback text *"Spoofer engine returned an unexpected error. Please try again."*
4. Engine `404` on task status → stop polling, clear the stored task.
5. Engine upload `401`/`403` or an `error` containing `"401"`/`"invalid token"` → token dead, abort the loop.
6. Backend `.success === false` → `message` goes straight into a toast.

**No retry, no backoff, no cancellation, no timeout anywhere in the client.**

---

# Async Jobs

```
create ──> task_id
            │
            └─> poll every 1500 ms   (setInterval)
                 GET /api/task/{task_id}/status
                 also re-checked on document visibilitychange + window focus
                 │
                 ├─ queue_position != null ──> show "Waiting Queue (n / total_queue)"
                 ├─ assets[].status changed ──> append a timestamped log line
                 ├─ 404 ──> stop polling, drop the stored task
                 │
                 └─ terminal ──> PATCH /api/spoofer-jobs/:id
                                POST  /api/auth/spoofer-state {task_id}   (reconcile coins)
```

**Polling interval** — `setInterval(n, 1500)`, i.e. **1500 ms**, hardcoded `[read]`.

**Completion condition** — the frontend does not test a single `status` string for the batch; it
watches per-asset `assets[].status` and stops when the interval is cleared on a terminal state.
Terminal handling branches on:
* first asset `asset_type === "Place"` → *"Bypass feature for Place/Game is currently unavailable."*
* `zip_download_url` present → store it, show "ZIP is ready"
* neither → *"Assets cannot be processed. Asset might be private or ID is invalid."*

**Exact status values in use** `[read]`
| Context | Values |
|---|---|
| Engine per-asset | `processing`, `success`, `failed` |
| Engine batch | *(read only as "terminal" vs "still running"; literal not asserted client-side)* |
| Client-side placeholder | `loading` |
| Upload | `upload_status`: `not_started`, `failed`, plus a success case implied by `uploaded_asset_id` |
| Job record | `pending`, `completed`, `partial`, `bypass_completed`, `bypass_failed`, `failed` |
| Admin filter enum | `all`, `completed`, `partial`, `bypass_completed`, `failed` |
| Asset types | `Audio`, `Animation`, `Decal`, … |

**One-active-task invariant** — a single `setInterval` ref guards one task; a new submission
clears the previous one. State is persisted to `localStorage.bmk_spoofer_active_task` as
`{task_id, parsedAssets, isSingle, batchId, startedAt}` and re-hydrated on load `[read]`.

**Client-side limits** `[read]` — none of these are server-enforced as far as is observable:
* `0` assets → *"Invalid input format! Please enter a LUA table or list of IDs."*
* `> 500` → *"Maximum of 500 IDs in a single bulk process!"*
* `custom_name` sanitised with `/[\\/:*?"<>|]/g → "_"`

---

# Private Asset Flow

**The dashboard frontend has no way to request private-asset handling.** Verified by scanning the
bulk-spoofer chunk for `place_id`, `placeId`, `universe_id`, `universeId`, `is_private`,
`isPrivate`, `private_asset`, `"private"`, `"public"`, `mode`, `spoof_mode`, `target_type`:
the only hits are `asset_type` (a value **read** from responses, never sent) and the substring
`mode` inside unrelated UI copy. The request body is literally:

```js
JSON.stringify({ assets: e, is_free: s })
```

Nothing else. **So: `assetId` and `is_free` only — no `universeId`, no `placeId`, no
`private`/`public` flag, no `type` or `mode` field.**

The capability exists **server-side only**, per the engine's published spec `[seen]`:
* `GET /api/download/{asset_id}` declares query param `place_id` described as
  **"Optional custom Place ID to spoof for private assets"**
* `GET /api/scan/place/{place_id}` — "Scans a Place ID for asset references (Audio, Animations,
  Emotes)"; accepts `authorization` **or** `x-roblox-cookie`

Neither route is called by the dashboard UI, and I did not exercise them. Anything beyond
`{assets, is_free}` in a bulk request is **NOT CONFIRMED FROM FRONTEND** as a *working* flow —
the schema permits `asset_ids`, `roblox_api_key`, `creator_id` and `creator_type`, but no
frontend code path sends them to this endpoint.

No attempt was made to reach private assets, bypass Roblox auth, or test any credential.

---

# What is NOT confirmed

| Item | Status |
|---|---|
| `bmk_token` format, algorithm, lifetime | NOT CONFIRMED — handled as an opaque string client-side |
| Email/password login payload | **NOT CONFIRMED** — `/api/auth/login` and `/api/register` are declared but have **no `apiFetch` call site in any downloaded chunk** |
| B2B Mesh gateway host + auth header | NOT CONFIRMED — no literal anywhere; `/account/me` 404s on both known hosts |
| Webhook delivery URL, payload, signing, retries | NOT CONFIRMED — only a URL input, a masked secret, and a log filter |
| Real credit/coin arithmetic | NOT CONFIRMED — all price tables are client-side |
| Whether client caps (500 IDs, 1 MB, 420 s) are enforced server-side | NOT CONFIRMED |
| Cloudflare Turnstile site key | NOT CONFIRMED — server-rendered |
| Authenticated response shapes | **NOT CONFIRMED** — no account was authenticated; all `[read]`, none `[seen]` |
| Rate limits | No `429`/`Retry-After`/`X-RateLimit-*` observed in 44 requests; no burst generated |
