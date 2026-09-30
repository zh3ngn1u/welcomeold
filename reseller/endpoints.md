# Reseller / B2B / Balance / Job Endpoint Reference

Source: `analysis/js/` (34 chunks, all 32 originally downloaded + 2 more from
`/admin/spoofer-history`). Re-scanned 2026-09-30. No re-download of the target was needed
beyond the two extra route documents listed above.

---

## ⚠️ Read this first — two corrections to the premise

### 1. There is no "reseller" API. The program is branded **B2B Mesh** / **B2B API**.

A case-insensitive search of **all 34 chunks, both stylesheets and all 14 route HTML documents**
for `reseller`, `resell`, `dropship`, `wholesale`, `distributor`, `affiliate`, `payout`:

| Term | Hits in JS/CSS | Where it does appear |
|---|---|---|
| `reseller` / `resell` | **0** | — |
| `dropship` / `distributor` / `affiliate` / `payout` | **0** | — |
| `wholesale` | **1** | one marketing string: `"30% Off Wholesale Bulk Rate"` — a feature bullet on the Enterprise credit pack in `0o45.cg_g4a77.js` |

No route, no field, no enum value, no API path uses any reseller synonym. The reseller-style
program is the **B2B Mesh**: its tenants are labelled **"Seller"** in the admin UI
(`"Daftar Seller & API Key"`, `"Seller Aktif"`, `"Developer yang terdaftar di B2B Mesh"`), and its
resellers buy **asset credits**, get an **API key prefixed `bmk_spoof_`**, and consume credits per
download. That is the reseller surface, and it is what is documented below.

### 2. **No authenticated account was used at any point in this analysis.**

The brief refers to "the authenticated account used during analysis". To be explicit: **none was.**
All 44 live requests were unauthenticated `curl` with no token, no cookie, no session jar and no
replay. Consequently:

* Every authenticated endpoint below is documented **from the call sites in the bundles** and is
  marked `UNTESTED` in the live column.
* **No field is marked "observed" unless it was actually seen in a captured response.**
* Response schemas given below are *exactly the fields the frontend reads*, not full schemas.

---

## Response-field notation used below

| Marker | Meaning |
|---|---|
| `[seen]` | Value observed live in a file in `analysis/api/responses/` |
| `[read]` | Field name appears in a response handler in the bundle. **Shape inferred from usage — not observed.** |
| `[derived]` | Value computed client-side from `[read]` fields |

---

# GROUP 1 — B2B MESH SELLER PORTAL  (base `https://backend.blokmarket.store`)

All five are called through `apiFetch` → **`Authorization: Bearer <bmk_token>` + `credentials:"include"`**.
Live status: **all 401** (`responses/31`–`34`).

### Endpoint
`GET /api/b2b/portal/status`

### Purpose
Single call that bootstraps the whole seller page: returns the seller's tenant record, the
account-lock flag, and (on some responses) the **raw API key**.

### Authentication
Bearer + cookies. **Backend-only:** role must be an active B2B tenant.

### Request Structure
No body, no query params.

### Response Structure
| Field | Type | Mark |
|---|---|---|
| `success` | bool | `[read]` |
| `tenant` | object | `[read]` |
| `tenant.credits_balance` | number | `[read]` |
| `tenant.webhook_url` | string | `[read]` |
| `tenant.webhook_secret` | string | `[read]` — UI shows `slice(0,8) + "••••"` |
| `tenant.api_key_prefix` | string | `[read]` |
| `tenant.tier` | string (`"none"` = no plan) | `[read]` |
| `isLocked` | bool | `[read]` |
| `rawKey` | string | `[read]` — **the full secret** |
| `message` | string | `[read]` |

### UI Flow
Page mount → `eU()` → `apiFetch(b2b.status())` → on `success && tenant`:
store tenant; set lock via `isLocked ?? (credits_balance ?? 0) <= 0`;
seed webhook input with `tenant.webhook_url`;
if `rawKey` present → save to `localStorage.bmk_b2b_raw_key` **and** display it;
else fall back to `localStorage.bmk_b2b_raw_key`, accepted only if it `startsWith("bmk_spoof_")`
and matches `tenant.api_key_prefix`; on failure → toast `"Gagal memuat status B2B API"`.

> **Note (frontend-visible, backend-only enforcement):** the key is delivered to the browser in
> full and persisted in plaintext `localStorage`. Server-side re-issue policy is not observable.

---

### Endpoint
`GET /api/b2b/portal/logs?page={p}&limit={l}`

### Purpose
The seller's own outbound API request log.

### Authentication
Bearer + cookies.

### Request Structure
Query: `page`, `limit`. The page hardcodes **`logs(1, 50)`** → `?page=1&limit=50`.

### Response Structure
`success` `[read]` · `logs[]` `[read]` · `message` `[read]`.
Log columns rendered (from the admin table, same shape):
`endpoint`, `method`, `status_code`, `response_time`, `ip`, `user_agent`, `created_at` `[read]`.

### UI Flow
"usage" tab becomes active → `eF()` → `logs(1,50)` → `logs[]` → table rows.
Errors are swallowed: `console.warn("Failed to fetch logs")`.

---

### Endpoint
`GET /api/b2b/portal/analytics?days={1|7|30}`

### Purpose
Usage analytics for the seller.

### Authentication
Bearer + cookies.

### Request Structure
Query `days`, derived from the range selector: `"24h"→1`, `"7d"→7`, `"30d"→30`.
**GET** — the call site passes no options object, so `fetch` defaults to GET.

### Response Structure
`success` `[read]` · `daily_metrics[]` `[read]` (defaults `[]`) ·
`summary` `[read]`, defaulted in code to
`{total_calls:0, total_errors:0, error_rate:"0%", avg_latency:"0 ms"}`
→ so those four summary keys are `[read]`.

### UI Flow
"usage" tab → `e$()` → `analytics(days)` → set `{daily_metrics, summary}` → metric cards.

---

### Endpoint
`POST /api/b2b/portal/key/rotate`

### Purpose
Issue a new seller API key and invalidate the old one.

### Authentication
Bearer + cookies. Guarded client-side: refused if already locked
(`"Kunci API terkunci. Lakukan pembelian kredit terlebih dahulu."`) and behind a `confirm()`:
`"Peringatan: Kunci API lama akan langsung berhenti berfungsi. Yakin ingin memperbarui?"`

### Request Structure
`{method:"POST"}` — **no body, no headers set by the caller**.

### Response Structure
`success` `[read]` · `rawKey` `[read]` (new key) · `tenant` `[read]` · `message` `[read]`.

### UI Flow
"Rotate / Perbarui Kunci" button → `confirm()` → `eK()` → on `success && rawKey`:
display key, write `bmk_b2b_raw_key`, update tenant, toast
`"API Key baru berhasil dibuat!"`. **UNTESTED** (state-changing, would invalidate a live key).

---

### Endpoint
`PUT /api/b2b/portal/webhook`

### Purpose
Set/clear the seller's outbound webhook callback URL.

### Authentication
Bearer + cookies.

### Request Structure
`Content-Type: application/json`
```json
{ "webhookUrl": "<absolute https URL from the input>" }
```
Origin: the `type:"url"` input, placeholder
`https://api.domain-anda.com/webhooks/bmk-spoof` (a **placeholder string only** — it is not a
live host, and no real webhook host is disclosed anywhere in the bundles).

### Response Structure
`success` `[read]` · `tenant` `[read]` · `message` `[read]`.

### UI Flow
"Webhook Callback URL (Opsional)" input → Save button → `eW()` → on success toast
`"Konfigurasi Webhook berhasil disimpan!"`. Field is labelled optional.

---

### Endpoint — **DECLARED, NO CALL SITE**
`GET /api/b2b/portal/pricing` · `POST /api/b2b/portal/topup`

Both exist in the `apiEndpoints` map but **neither is called from any downloaded chunk** — the
pricing table and the top-up form are driven by the **hardcoded plan arrays in the bundle** (§
Frontend-visible vs backend-only), not by these endpoints. `pricing` → `401` `[seen]`.
`topup` → live status not probed. Treat both as unconfirmed.

---

# GROUP 2 — ADMIN B2B MESH CONTROL  (operator-facing, same host)

All called via `apiFetch` → Bearer + cookies, plus **admin/owner role**.
Call site: `0mhu~2w72ast2.js` (the `/admin/spoofer-history` route chunk, 51,163 B).
Live status: **all 401** (`responses/35`–`37`).

### Endpoint
`GET /api/admin/b2b/overview?days={d}`

### Purpose
Operator KPI header for the B2B Mesh.

### Request Structure
Query `days`; the page passes a days state, defaulting to the `7d` range (same 1/7/30 selector).

### Response Structure
`success` `[read]` · `summary` `[read]`, and within it:
`total_credits` `[read]`, `active_tenants_count` `[read]`,
`total_calls` `[read]`, `total_errors` `[read]`, `error_rate` `[read]`, `avg_latency` `[read]`.
Rendered labels confirm intent: *"Kredit unduhan yang berhasil dikonsumsi"* (total_credits),
*"Seller Aktif"*, *"Error Rate & Latensi"*.

### UI Flow
Tab "B2B Seller API" mount → `ef()` → `b2bOverview(days)` → KPI cards.

---

### Endpoint
`GET /api/admin/b2b/tenants?page={p}&limit=15&search={q}`

### Request Structure
Query `page`, `limit` (hardcoded **15**), `search` (UI search box, omitted when blank).

### Response Structure
`success` `[read]` · `tenants[]` `[read]` · `totalPages` `[read]` · `total` `[read]`.
Tenant row fields: `id` `[read]`, `tenant_name` `[read]`, `email` `[read]`,
`role` `[read]`, `credits_balance` `[read]`, `is_active` `[read]`,
`api_key_prefix` `[read]`, `tier` `[read]`, `created_at` `[read]`, `experience_limit` `[read]`.
Column headers: *"Nama App Tenant"*, *"Email Pengguna"*, *"Role Sistem"*, *"Tier Paket"*,
*"API Key Prefix"*, *"Sisa Kredit"*, *"Kredit Terpakai"*, *"IP Pemanggil"*.

### UI Flow
Tab mount + page/search change → `eg()` → `b2bTenants(page,15,search)` → paginated table.

---

### Endpoint
`GET /api/admin/b2b/logs?page={p}&limit=20&endpoint={e}&status={s}&search={q}`

### Request Structure
Query `page`, `limit` (hardcoded **20**), `endpoint`, `status`, `search`.

**Filter enums are hardcoded in the bundle:**
* `endpoint`: `""` (*Semua Endpoint*), `"download"` (**POST /download**), `"account"`
  (**GET /account/me**), `"webhook"` (**Webhook Callback**)
* `status`: `""`, `"2xx"`, `"4xx"`, `"5xx"`, `"401"`, `"402"`, `"429"`

> These four enum labels are the **only** evidence of the seller-facing B2B Mesh REST contract:
> `POST /download`, `GET /account/me`, plus webhook callbacks, with `402 Payment Required`
> (out of credits) and `429 Rate / Limit` as real conditions. That API is **not** on
> `backend.blokmarket.store` (404 `[seen]`, `responses/41`) and **not** in the engine's public
> OpenAPI spec `[seen]`. Its host is not disclosed in any collected resource. The admin table can
> display those rows only because the gateway logs the path server-side.

### Response Structure
`success` `[read]` · `logs[]` `[read]` · `totalPages` `[read]` · `total` `[read]`.
Row fields as Group 1 `logs`.

---

### Endpoint
`POST /api/admin/b2b/tenants/:id/credits`

### Purpose
Manually add, deduct, or set a seller's credit balance.

### Request Structure
`Content-Type: application/json`
```json
{ "amount": 500, "action": "add" }
```
* `amount` — parsed from the input, `parseInt`, rejected client-side if `NaN` or `< 0`
  (`"Masukkan jumlah kredit yang valid!"`).
* `action` — **enum confirmed in the bundle**:
  `"add"` (*Tambah (+)…*), `"deduct"` (*Kurang (-)…*), `"set"` (*Set Nilai (=)…*). Default `"add"`.

### Response Structure
`success` `[read]` · `message` `[read]` (shown as the success toast).

### UI Flow
Row action *"Sesuaikan Saldo Kredit"* → modal → amount input + action select → `eN()` →
`b2bAdjustCredits(tenant.id)` → toast `message` → refresh `b2bTenants` + `b2bOverview`.
**UNTESTED** — state-changing financial operation.

---

### Endpoint
`POST /api/admin/b2b/tenants/:id/toggle-status`

### Purpose
Suspend / reactivate a seller (freeze or restore their API key).

### Request Structure
`{method:"POST"}` — **no body**.

### Response Structure
`success` `[read]` · `message` `[read]`.

### UI Flow
Row action → `confirm("Yakin ingin <bekukan (suspend) / aktifkan kembali> API Key untuk <tenant_name>?")`
→ `ev()` → `b2bToggleStatus(tenant.id)` → toast `message` → refresh tenant list.
Target state derived client-side from `tenant.is_active` `[derived]`.
**UNTESTED** — state-changing.

---

# GROUP 3 — REFERRAL / COMMISSION  ⚠️ DECLARED BUT NOT DEPLOYED

Eight paths exist in the `apiEndpoints` map:

```
/api/referral/join              /api/referral/admin/overview
/api/referral/info              /api/referral/admin/withdrawals[?status=]
/api/referral/commissions       /api/referral/admin/withdrawals/:id
/api/referral/withdraw
/api/referral/withdrawals
```

**Evidence they are dead in this deployment:**
* **Zero** `apiFetch` call sites across all 34 chunks.
* Routes `/referral`, `/tools/referral`, `/affiliate` all return the Next.js 404 page
  (10,833 B, byte-identical to other 404s) `[seen]`.
* `GET /api/referral/info` → **404** `[seen]` (`responses/39`)
* `GET /api/referral/commissions` → **404** `[seen]` (`responses/40`)

So the commission/withdrawal subsystem — the closest thing to classic reseller payouts in the
codebase — is **wired into the client API map but has neither a route nor a live backend
endpoint**. No request structure, response schema, or UI flow is documented, because none exists
to observe. Purpose is **unknown** and must not be guessed.

---

# GROUP 4 — COIN / BALANCE

Coins are the spend currency for the spoofer tool. Balance lives in
`userAtom.spoofer_state.coins` `[read]`.

### Endpoint
`GET|POST /api/auth/spoofer-state`

### Purpose
Read coin balance + history; reconcile it after a job.

### Authentication
Bearer + cookies.

### Request Structure
* `GET` on page mount, no body.
* `POST` `{ "task_id": "<engine task id>" }` after a job reaches a terminal state.

### Response Structure
`success` `[read]` · `data.coins` (number, gated on `typeof === "number"`) `[read]` ·
`data.history[]` `[read]`, entries carry `task_id` `[read]` and `cost` `[read]`
(consumed in the admin view via `accounts.spoofer_state.history.find(t => t.task_id === job.job_id)`).

### UI Flow
Mount → `GET` → set coin display (`/coins60.png` icon + `🪙` in the cost modal).
After job completion → `POST {task_id}` → recompute displayed balance.
Errors → toast `"Failed to connect to the server to deduct coins."` (misleading label on a read).

---

### Endpoint
`POST /api/auth/spoofer-check-cost`

### Purpose
Price a batch before starting it.

### Request Structure
```json
{ "asset_ids": ["<id>", "…"] }
```
> **Not present in the `apiEndpoints` map** — built ad hoc via
> `buildApiUrl("/auth/spoofer-check-cost")`. Undeclared surface.

### Response Structure
`success` `[read]` · `cost` `[read]` · `has_ugc` `[read]` · `message` `[read]`.
Live unauthenticated: `401 {"success":false,"message":"Unauthorized"}` `[seen]` (`responses/20`).

---

### Endpoint
`POST /api/auth/spoofer-deduct`

### Request Structure
```json
{ "asset_count": 25, "asset_ids": ["<id>", "…"] }
```
Sent twice in some paths: once optimistically before the run, once on terminal state.

### Response Structure
`success` `[read]` · `coins` / `newCoins` `[read]` · `message` `[read]`.
**UNTESTED** — spends a real balance.

---

### Endpoint — coin purchase
`POST /api/payment/create-coin-invoice` `{ "coins": <n>, "paymentMethod": "qris" }`
→ `POST /api/payment/paypal/create-coin-order` `{ "coins": <n> }`
→ `POST /api/payment/paypal/capture-coin-order` `{ "paypalOrderId", "orderId", "coins" }` `[read]`.
`coins` defaults to `60` client-side (`eT.coins||60`), matching the 60-coin price tier.
`paymentMethod` is one of `"qris" | "paypal"` (a `layoutId` tab switcher exists in the bundle).
QR rendering: `qrString` → `api.qrserver.com` → `.blob()` → download as
`BLOKMARKET-QRIS-{totalTransfer}.png`.
**UNTESTED** — financial.

---

# GROUP 5 — JOB / TASK / STATUS

### Engine (live polling — the only real polling in the app)
`GET https://spoofer.blokmarket.store/api/task/{task_id}/status` — **no auth header, no cookies.**
Response `[read]`: `status`, `queue_position`, `total_queue`, `assets[]`
(`id`, `status`, `real_name`, `custom_name`, `asset_type`, `file_name`, `file_size`,
`uploaded_asset_id`, `error`).
Live: `404 {"detail":"Task not found."}` for a bogus id `[seen]` (`responses/14`).
Polled every **1500 ms**; also re-checked on `visibilitychange` and window `focus`.
Full detail in `../api/request-flow.md`.

### User spoofer jobs (`backend`)
| Endpoint | Method | Request | Response `[read]` |
|---|---|---|---|
| `/api/spoofer-jobs` | POST | `{job_id, status:"pending", total_assets, success_count:0, failed_count:0, asset_breakdown}` | `success`, `data` |
| `/api/spoofer-jobs` | GET | — | `success`, `data[]` |
| `/api/spoofer-jobs/:id` | GET | — | `success`, `data` |
| `/api/spoofer-jobs/:id` | PATCH | `{status, success_count, failed_count, asset_breakdown, files[], logs[≤500]}` | `success`, `message` |
| `/api/spoofer-jobs/:id` | GET (admin) | `{method:"GET", credentials:"include"}` | `success`, `data.logs[]`, `message` |

### Admin job audit
`GET /api/spoofer-jobs/admin/all?page={p}&limit=10[&status=][&assetType=][&search=]`
The page **builds the query string manually** with `URLSearchParams` and appends it to the
declared path. Enums hardcoded in the bundle:
* `status`: `all`, `completed`, `partial`, `bypass_completed`, `failed`
* `assetType`: `all`, `Audio`, `Animation`, `Decal`, …
Response `[read]`: `data[]`, `pagination.total_pages`, `message`.
Live: **401** `[seen]` (`responses/38`).

Job row fields `[read]`: `id`, `job_id`, `status`, `total_assets`, `success_count`,
`failed_count`, `assets[]`/`files[]` (each with `uploaded_asset_id`, `upload_status`,
`file_name`, `file_size`, `custom_name`), `zip_url`, `accounts.email`, `accounts.role`,
`accounts.experience_limit`, `accounts.spoofer_state.coins`, `accounts.spoofer_state.history[]`.

**Client-side coin cost schedule** (found in the admin chunk — a real *frontend-visible* rule,
**[derived]** from `total_assets` and `accounts.role`, with no server call):
```js
role === "admin" || role === "owner"  -> 0
history entry matching job_id        -> t.cost        // server-provided
else total_assets <= 1               -> 0
else total_assets <= 100             -> 15
else total_assets <= 300             -> 30
else                                  -> 50
```
> These tiers exist only in the browser. Whatever the server charges is authoritative; the
> dashboard's own cost estimate is advisory. The same tiering drives the spoofer modal's
> `cost` display via `/auth/spoofer-check-cost`.

### Upload jobs
| Endpoint | Method | Request |
|---|---|---|
| `/api/upload/jobs?page&limit` | GET | query `page`, `limit` |
| `/api/upload/jobs/:id` | GET | — |
| `/api/upload/jobs/:id/retry` | POST | `{item_index}` `[read]` |
| `/api/upload/quota` | POST | `{}` — returns `remaining`, `is_admin` `[read]` |
| `/api/upload/health` | GET | **PUBLIC** — `{"success":true,"data":{"status":"healthy","service":"bmk-upload","active_jobs":0}}` `[seen]` |

---

# GROUP 6 — WEBHOOK

| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `/api/b2b/portal/webhook` | PUT | Bearer | Seller registers their callback URL. `{webhookUrl}` |
| `/api/b2b/portal/key/rotate` | POST | Bearer | Response carries `rawKey`; rotation is a webhook-relevant event |
| *(engine)* outbound callbacks | — | — | Logged as `"webhook"` in the admin endpoint filter `[read]`; **delivery is backend-only** — no delivery code, URL template, payload shape, signature scheme, or retry policy exists anywhere in the bundles |

`tenant.webhook_secret` is returned to the seller UI (masked to 8 chars) `[read]`, which implies
some signing scheme — but **the scheme itself is backend-only and was not retrieved.**

---

# GROUP 7 — DOWNLOAD / UPLOAD

### Spoofer engine (no auth header; Roblox creds per request)
| Method | Path | Body | Status |
|---|---|---|---|
| POST | `engine /api/download/batch/async` | `{assets:[{id,custom_name}], is_free}` | 400/422 validation-only `[seen]` |
| GET | `engine /api/task/:id/status` | — | 200 / 404 `[seen]` |
| POST | `engine /api/upload/batch` | `{files:[{file_name,display_name,asset_type}], roblox_access_token, creator_id, creator_type, custom_description}` | 422 validation-only `[seen]` |
| GET | `engine /api/files/download/{filename}` | query `inline` | UNTESTED |
| GET | `engine /api/files/zips/{filename}` | — | UNTESTED |

Authoritative schemas: `../api/spoofer-engine-openapi.json`.
Spec title: **"Roblox Asset Downloader Core Service"**; `BatchDownloadRequest.is_free` is
documented as *"Is this a free spoof request?"*.

### Backend (Bearer)
| Method | Path | Request type | Body `[read]` |
|---|---|---|---|
| POST | `/api/upload/batch` | **multipart** | `creator_id`, `is_group`("true"/"false"), `target_name`, repeated `files[]`. `access_token` is sent as the literal string `"session_auto_resolved"` — the server resolves the caller's own token |
| POST | `/api/audio/upload-convert` | **multipart** | `file`, `roblox_speed`, `amplify_db`, `modify`("true"), `format`, `max_duration`("420") |
| POST | `/api/audio/upload-roblox` | JSON | `{job_id, filename, access_token, user_id, is_group}` |
| POST | `/api/audio/convert` | JSON | — |
| GET | `/api/audio/status/:id` | — | polled by the audio tool |
| POST | `/api/audio/publish-to-game` | JSON | — |
| GET | `audio.blokmarket.store/api/download/:id/:fileName` | — | separate media host, no bearer attached |

`upload.batch` is gated client-side: non-admin with `remaining <= 0` or a batch larger than
`remaining` is blocked client-side (`"Batas kuota upload Anda telah habis. Silakan upgrade ke Pro!"`).

---

# GROUP 8 — ACCOUNT / PROFILE

| Endpoint | Method | Request `[read]` | Response `[read]` |
|---|---|---|---|
| `/api/auth/me` | GET | — | `success`, `data` → `id`, `name`, `email`, `role`, `experience_limit`, `plan_type`, `spoofer_state{roblox{…}, coins, history[]}`, `audio_plan`, `audio_plan_expires` |
| `/api/auth/roblox/groups` | GET | — | `success`, `data[]` (group picker) |
| `/api/auth/roblox/save-api-key` | POST | `{apiKey, creatorId, creatorType, from?}` | `success`, `message` |
| `/api/auth/roblox/unlink` | POST | `{from:"spoofer"\|"bmk_upload"\|"audio"}` | `success`, `message` |
| `/api/auth/roblox/refresh` | POST | `{from:"spoofer"}` | `success`, `message` |
| `/api/experience/my-list` | GET | — | `success`, `data[]`, `count`, `limit` |
| `/api/experience` | POST | **multipart** `name`, `experience_id`, `image` (client-checked `< 1,048,576` B) | `success`, `data`, `message` |
| `/api/activity/logs?month=` | GET | query `month` (YYYY-MM) | `success`, `data[]` |

OAuth entry points (popups, not `apiFetch`): `/api/auth/google/login?prompt=select_account&cf_token=&ref=&t=`,
`/api/auth/roblox/login?cf_token=&token=&from=&t=`. `ref` is read from the **`bmk_ref` cookie**.
`/api/auth/logout` is a raw `fetch` POST with `credentials:"include"` and a `?t=` cache-buster,
preceded by `localStorage.removeItem("bmk_token")`.

---

# FRONTEND-VISIBLE vs BACKEND-ONLY

**Frontend-visible (reconstructed, retrieved):**
* B2B tab state machine and lock gating (`isLocked`, `credits_balance>0`, `tier!=="none"`)
* Hardcoded credit-pack and monthly-plan tables (credits, IDR/USD price, rate per credit, rate limits 60/180/600 req-min, concurrency 3/10/30, feature bullets)
* The `0 / 15 / 30 / 50` coin cost schedule and the admin/owner exemption
* Log and job filter enums, page sizes (50 seller logs, 20 admin logs, 15 tenants, 10 jobs)
* `bmk_spoof_` key prefix, `bmk_b2b_raw_key` persistence, masked `webhook_secret` display
* The 1500 ms poll interval, resume-from-localStorage, single-active-task invariant
* Filename sanitiser `/[\\/:*?"<>|]/g → "_"` and the 500-ID / 1 MB / 420 s client-side caps

**Backend-only (NOT exposed, not retrievable):**
* Whether the server enforces any of those caps, tiers, or the lock
* Actual credit debit arithmetic, and whether `has_ugc` changes the price
* Seller API key generation, storage, hashing, rotation invalidation
* The B2B Mesh gateway host, its `POST /download` / `GET /account/me` implementations, auth scheme, and rate limiter
* Webhook delivery, payload, signing (`webhook_secret` implies HMAC but no code confirms it), retries
* The spoof/"bypass" transformation, asset fetching, and re-upload
* PayPal/QRIS order capture, JWT signing, RBAC, audit persistence, Turnstile verification
