# Request Flows — seller lifecycle, credit lifecycle, job lifecycle

All flows are reconstructed from the downloaded bundles. Every literal below is verbatim from a
call site. `—>` marks a value the client never sees (backend-only).

---

# FLOW A — B2B Mesh seller onboarding & consumption

```
Seller (dashboard tab /tools/b2b-api)
  │
  │  page mount
  ▼
GET /api/b2b/portal/status                         Bearer + credentials:"include"
  │
  ├── success && tenant ──> store tenant
  │      ├── lock        = isLocked ?? (tenant.credits_balance ?? 0) <= 0
  │      ├── webhook URL = tenant.webhook_url || ""
  │      ├── tab access  = !lock && credits_balance > 0 && tenant.tier !== "none"
  │      └── rawKey ? localStorage["bmk_b2b_raw_key"] = rawKey
  │                   : reuse stored key, accepted only if
  │                     startsWith("bmk_spoof_") && startsWith(tenant.api_key_prefix)
  │
  ├── tenant.tier === "none" or credits_balance <= 0 ──> force tab "topup"
  │                                                    (persist to bmk_b2b_active_tab)
  └── !success ──> toast "Gagal memuat status B2B API"
                   catch ──> toast "Gagal terhubung ke gateway B2B: " + err

  ┌─────────────────────────────── tab "usage" (only if access allowed) ─┐
  │ GET /api/b2b/portal/logs?page=1&limit=50        ──> success.logs[]  │
  │ GET /api/b2b/portal/analytics?days={1|7|30}                            │
  │        ──> { daily_metrics: r.daily_metrics || [],                   │
  │              summary: r.summary || {total_calls:0,total_errors:0,     │
  │                          error_rate:"0%",avg_latency:"0 ms"} }       │
  └───────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────── tab "billing" / "topup" ──────────────┐
  │ plan tables are NOT fetched — they are hardcoded arrays in the bundle  │
  │ (see "Frontend-visible pricing" below)                                 │
  └───────────────────────────────────────────────────────────────────────┘

Seller clicks "Rotate key"
  │ confirm("Peringatan: Kunci API lama akan langsung berhenti berfungsi…")
  │ guarded client-side: if locked ──> toast "Kunci API terkunci. Lak…
  ▼
POST /api/b2b/portal/key/rotate          no body, no explicit headers
  │
  ├── success && rawKey ──> display + localStorage["bmk_b2b_raw_key"] = rawKey
  │                        update tenant ──> toast "API Key baru berhasil dibuat!"
  └── else ──> toast message || "Gagal me-rotate API Key."

Seller edits the webhook field
  ▼
PUT /api/b2b/portal/webhook
{ "webhookUrl": "<input value>" }          Content-Type: application/json
  ├── success ──> update tenant ──> toast "Konfigurasi Webhook berhasil disimpan!"
  └── else ──> toast message || "Gagal menyimpan webhook."

  ── meanwhile, out of band ──>
  seller calls the B2B Mesh gateway directly with bmk_spoof_… :
      POST /download      ──> debits credits ──> (402 when empty, 429 when rate-limited)
      GET  /account/me    ──> balance / status
  ──> gateway logs each call; webhook callback fires on events
  ──> operator sees them in admin /admin/b2b/logs        (filter: download|account|webhook)

  ──> backend-only: the gateway host, credit-debit arithmetic, rate limiter,
      webhook delivery/signing/retry, key hashing. None retrievable.
```

**Tab state machine** `[read]` — `topup` (default) / `billing` / `usage`, resolved in order:
`?tab=` query param → `#hash` → `localStorage.bmk_b2b_active_tab` → `"topup"`.
Writing the tab back calls `history.replaceState` so the URL stays shareable.

### Frontend-visible pricing (hardcoded in `0o45.cg_g4a77.js`, never fetched)

**One-off credit packs** (`xc`):
| id | name | credits | IDR | USD | rateDisplay |
|---|---|---|---|---|---|
| `pack_500` | Core Pack | 500 | 50,000 | $3.60 | Rp 100 ($0.007) / asset credit |
| `pack_1500` | Growth Pack | 1,500 | 135,000 | $9.20 | Rp 90 ($0.006) · *"Save 10%"* |
| `pack_5000` | Pro Pack | 5,000 | 400,000 | $26.50 | Rp 80 ($0.005) · *"Save 20%"* |
| `pack_15000` | Enterprise Pack | 15,000 | 1,050,000 | $69.00 | Rp 70 ($0.004) · *"Save 30%"*, *"30% Off Wholesale Bulk Rate"*, *"Real-Time Webhook Callback Events"*, *"Dedicated Priority Worker Pool"* |

**Monthly plans** (`xs`):
| id | name | credits/mo | IDR | USD | rate limit | concurrency |
|---|---|---|---|---|---|---|
| `starter` | Starter Plan | 2,000 | 149,000 | $10.20 | 60 req/min | 3 |
| `business` | Professional Plan | 7,500 | 499,000 | $35.50 | 180 req/min | 10 |
| `enterprise` | Business Plan | 25,000 | 1,299,000 (was 1,499,000) | $86.00 | 600 req/min | 30 |

Plan feature bullets worth quoting, because they state the resale product plainly `[read]`:
*"All Assets ID"*, *"Multi-Asset Batch Spoofer"*, *"Advanced Roblox Moderation Bypass"*,
*"Optimized for High-Traffic Bots & Apps"*, *"Discord Bot & REST API Integration"*.

> These numbers are **client-side only**. Whether the server charges the same is backend-only
> and unverified. The top-up endpoints (`POST /api/b2b/portal/topup`, `GET /api/b2b/portal/pricing`)
> exist in the map but are **never called**, so the purchase path itself is not in these bundles.

---

# FLOW B — Coin (balance) lifecycle

```
Page mount
  ▼
GET /api/auth/spoofer-state                ──> { success, data }
  └── if typeof data.coins === "number"  -> coin badge (/coins60.png + count)
      if Array.isArray(data.history)     -> history array
      else on success                    -> set userAtom (full /auth/me refresh on the spoofer page)

User submits IDs
  ▼
POST /api/auth/spoofer-check-cost         { asset_ids: [...] }
  └── success ──> cost = t.cost, hasUgc = t.has_ugc ──> cost modal
      has_ugc selects the per-asset price tier
  └── role admin|owner ──> SKIP the pre-check, fire-and-forget the deduct
  └── else ──> toast t.message || "Failed to calculate coin cost."

User confirms ("Free Spoof" when is_free, otherwise pay)
  ▼
POST /api/auth/spoofer-deduct              { asset_count, asset_ids }
  └── newCoins ──> update displayed balance

  ── top-up path (alternative to coins) ──>
  method selector: "qris" | "paypal"
    qris   : POST /api/payment/create-coin-invoice { coins, paymentMethod:"qris" }
             ──> qrString ──> https://api.qrserver.com/v1/create-qr-code/?data=<enc>&size=600x600
                 ──> .blob() ──> download "BLOKMARKET-QRIS-{totalTransfer}.png"
    paypal : POST /api/payment/paypal/create-coin-order { coins }
             ──> PayPal SDK onApprove ──> POST /api/payment/paypal/capture-coin-order
                                          { paypalOrderId, orderId, coins }
  ──> backend-only: QRIS settlement, PayPal capture, actual credit issuance

Job reaches a terminal state (or non-free submit)
  ▼
POST /api/auth/spoofer-state               { task_id }
  └── server recomputes the balance ──> client redraws the badge
  └── on failure ──> toast "Failed to connect to the server to deduct coins."
      (mislabelled: this call reads, it does not deduct)
```

**Cost display tiers** `[derived]`, hardcoded in the admin chunk:
`0` (admin/owner, or ≤1 asset) · `15` (≤100) · `30` (≤300) · `50` (>300) — otherwise the
server-provided `history[].cost` for a matching `task_id`.

---

# FLOW C — Spoofer job lifecycle (job / task / status)

```
UI: paste LUA table or raw ID list
  ▼
parse ──> [{ id, custom_name }]           0 items -> toast "Invalid input format!…"
                                          >500   -> toast "Maximum of 500 IDs in a single bulk process!"
                                          custom_name sanitiser: /[\\/:*?"<>|]/g -> "_"
  ▼
POST /api/auth/spoofer-check-cost  ──> cost, has_ugc
  ▼
(optional) POST /api/auth/spoofer-deduct
  ▼
if NOT single/free:
    POST /api/spoofer-jobs   { job_id, status:"pending", total_assets, success_count:0,
                               failed_count:0, asset_breakdown:{} }      <-- audit row
  ▼
POST engine /api/download/batch/async
     headers: { "Content-Type":"application/json" }
              + "X-Roblox-Cookie": <user .ROBLOSECURITY>   only when !is_free and a cookie was pasted
     body:    { assets:[{id,custom_name}], is_free }
     NO Authorization header, NO credentials
  │
  ├── !res.ok ──> engine `detail` becomes the toast
  │                "Spoofer engine returned an unexpected error. Please try again."  (default)
  │                timestamped error line pushed to bmk_spoofer_logs
  └── { task_id }
        └─> localStorage["bmk_spoofer_active_task"] = { task_id, parsedAssets, isSingle,
                                                          batchId, startedAt }   <-- resume point

POLL  setInterval(1500 ms)   [+ on visibilitychange / window focus]
  ▼
GET engine /api/task/{task_id}/status          no auth header
  │
  ├── 404 ──> clear interval, drop bmk_spoofer_active_task, stop
  ├── queue_position != null ──> "Waiting Queue (n / total_queue)"
  └── assets[] changed ──> per-asset log line, e.g. "[Audio] processing …",
                            bmk_spoofer_logs.append({timestamp, type, text})
      status transition ──> PATCH /api/spoofer-jobs/:id
                            { status, success_count, failed_count,
                              asset_breakdown:{Type:{success,failed}},
                              files:[…], logs: logs.slice(-500) }

TERMINAL
  ├── first asset asset_type === "Place"
  │      ──> "Failed: ID Detected as Place/Game. Bypass feature for Place/Game is
  │           currently unavailable."
  ├── zip_download_url ──> bmk_spoofer_active_zip + _count, "ZIP is ready", force-download
  ├── else ──> "Failed: Assets cannot be processed. Asset might be private or ID is invalid."
  └─> events bypass_completed / bypass_failed ──> activity log
  └─> POST /api/auth/spoofer-state { task_id }   (reconcile coins)

OPTIONAL: upload the results into the seller's own Roblox experience
  ▼
POST engine /api/upload/batch        (one HTTP request per asset, strictly serial)
     { files:[<one>], roblox_access_token, creator_id, creator_type }   creator_type = id ? "Group" : "User"
  ├── 401 / 403, or error containing "401" / "invalid token" ──> token dead, stop the loop
  ├── results[0].success ──> record uploaded_asset_id  (UI: "New Spoofed ID")
  └── else ──> upload_error recorded against the asset
  └─> bmk_spoofer_downloads updated per asset

ADMIN VIEW  /admin/spoofer-history
  ├─ tab "Web Spoofer Jobs":  GET /api/spoofer-jobs/admin/all?page&limit=10
  │                            [&status][&assetType][&search]
  │     row: status badge, per-type breakdown, uploaded count, failed-upload count,
  │          computed completion/partial state, cost, user email, role, coin balance
  └─ row expand ──> GET /api/spoofer-jobs/:id ──> data.logs[]  (lazy, per-row spinner)
```

**Single-active-task invariant** — one global `setInterval` ref (`sS.current`) guards one task;
a new submit clears the previous interval. Resume is driven purely by `localStorage`, so a
half-finished batch survives a reload and is re-hydrated with its `parsedAssets`.

**Status vocabulary** `[read]`: `not_started`, `processing`, `success`, `failed`, `pending`,
`completed`, `partial`, `bypass_completed`, `bypass_failed`, plus `upload_status` values.
**Asset types** `[read]`: `Audio`, `Animation`, `Decal`, …

---

# FLOW D — Operator (admin) B2B control

```
/admin/spoofer-history ──> tab "B2B Seller API"
  │
  ├─ GET /api/admin/b2b/overview?days            -> summary{total_credits, active_tenants_count,
  │                                                 total_calls, total_errors, error_rate, avg_latency}
  ├─ GET /api/admin/b2b/tenants?page&limit=15&search
  │      -> tenants[{id, tenant_name, email, role, credits_balance, is_active,
  │                  api_key_prefix, tier, created_at, experience_limit}], total, totalPages
  ├─ GET /api/admin/b2b/logs?page&limit=20&endpoint&status&search
  │      -> logs[{endpoint, method, status_code, response_time, ip, user_agent, created_at}]
  │
  ├─ "Sesuaikan Saldo Kredit"  ──> POST /api/admin/b2b/tenants/:id/credits
  │        { amount, action:"add"|"deduct"|"set" }
  │        client guard: parseInt(amount); NaN or <0 -> "Masukkan jumlah kredit yang valid!"
  │        success -> toast message, refresh tenants + overview
  │
  └─ suspend/reactivate  ──> confirm("Yakin ingin <bekukan (suspend)|aktifkan kembali>
                               API Key untuk <tenant_name>?")
             ──> POST /api/admin/b2b/tenants/:id/toggle-status      (no body)
             target state derived from tenant.is_active
```
**Range selector** `[read]`: `24 Jam` → `days=1`, `7 Hari` → `7`, `30 Hari` → `30`.
**Endpoint filter** `[read]`: `""`, `download` (POST /download), `account` (GET /account/me),
`webhook` (Webhook Callback).
**Status filter** `[read]`: `""`, `2xx`, `4xx`, `5xx`, `401`, `402`, `429`.

---

# FLOW E — Upload job lifecycle (`/tools/bmk-upload`)

```
GET  /api/upload/quota            ──> { remaining, is_admin }   (POST with {})
     guard: !is_admin && (remaining <= 0 || batch.length > remaining)
            ──> "Batas kuota upload Anda telah habis. Silakan upgrade ke Pro!"
POST /api/upload/batch            multipart/form-data
     creator_id, is_group("true"/"false"), target_name, files[] (repeated)
     access_token = "session_auto_resolved"     <-- server substitutes the caller's own token
     ──> { success, message } ──> "Upload dimulai, santai sejenak…"  (server-side job)
GET  /api/upload/jobs?page&limit  ──> job list
GET  /api/upload/jobs/:id         ──> per-job status
POST /api/upload/jobs/:id/retry   { item_index } ──> retry one failed item
```
---

# Cross-flow note on what the frontend never sees

| Concern | Frontend knows | Backend-only |
|---|---|---|
| Coin price | display tiers `0/15/30/50` | the real price, and whether `has_ugc` changes it |
| Credit price | hardcoded IDR/USD tables | what `/b2b/portal/topup` actually charges |
| Seller lock | `isLocked ?? credits_balance<=0`, `tier!=="none"` | whether the gateway enforces the same |
| Rate limits | plan marketing text `60/180/600 req-min` | the real limiter and its headers |
| Webhook | a URL field, a masked secret, a log filter | delivery, payload, HMAC scheme, retries |
| Job cost | advisory schedule | authoritative debit |
| Bypass | input IDs, status strings, output ZIP | the transformation itself |
