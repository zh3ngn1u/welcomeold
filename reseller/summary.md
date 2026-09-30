# Reseller / B2B Summary

## Two premise corrections

1. **No reseller API exists under that name.** `reseller`, `resell`, `dropship`, `distributor`,
   `affiliate`, `payout` = **0 hits** across all 34 chunks, 2 stylesheets, 14 route HTMLs.
   `wholesale` = **1 hit**, a single marketing bullet (`"30% Off Wholesale Bulk Rate"`).
   The reseller program is branded **B2B Mesh**; its tenants are called **Sellers** in the UI
   (`"Daftar Seller & API Key"`, `"Seller Aktif"`, `"Developer yang terdaftar di B2B Mesh"`).

2. **No authenticated account was used at any point.** All 44 live requests were unauthenticated
   `curl` — no token, cookie, session jar or replay. So no field is marked observed unless it
   appears in a captured response, and every authenticated endpoint is `UNTESTED` live.

## The reseller product, in the vendor's own words

Sellers buy **asset credits** and get an API key prefixed **`bmk_spoof_`**, consumed per download.
From the hardcoded plan tables in `0o45.cg_g4a77.js`:

* Packs: 500 cr / Rp 50,000 · 1,500 / Rp 135,000 · 5,000 / Rp 400,000 · 15,000 / Rp 1,050,000
* Monthly: Starter 2,000 cr, 60 req/min, 3 concurrent · Professional 7,500, 180 req/min, 10 ·
  Business 25,000, 600 req/min, 30
* Features sold: *"All Assets ID"*, *"Multi-Asset Batch Spoofer"*, *"Advanced Roblox Moderation
  Bypass"*, *"Real-Time Webhook Callback"*, *"Optimized for High-Traffic Bots & Apps"*,
  *"Discord Bot & REST API Integration"*

The seller-facing REST contract is visible only as log-filter labels: **`POST /download`**,
**`GET /account/me`**, and **webhook callbacks**, with `402 Payment Required` (out of credits) and
`429 Rate / Limit` as real statuses. That API is **not** on `backend.blokmarket.store` (404) and
**not** in the engine's published OpenAPI spec. **Its host is not disclosed in any collected
resource** — and I have not guessed it.

## Coins vs credits

Two distinct currencies, both client-visible, both authoritative only server-side:

| | Coins | B2B credits |
|---|---|---|
| Where | `userAtom.spoofer_state.coins` | `tenant.credits_balance` |
| Earned by | paying (PayPal / QRIS) | buying packs or monthly plans |
| Spent on | spoofer batches | gateway `POST /download` |
| Cost table | hardcoded `0 / 15 / 30 / 50` by `total_assets` | per-credit rate in the plan tables |
| API | `/auth/spoofer-state`, `/auth/spoofer-check-cost`, `/auth/spoofer-deduct` | `/b2b/portal/status`, `/admin/b2b/tenants/:id/credits` |

## Final table

| Endpoint | Method | Auth | Purpose | Frontend File |
|---|---|---|---|---|
| `/api/b2b/portal/status` | GET | Bearer | Seller bootstrap: tenant, lock, `rawKey` | `0o45.cg_g4a77.js` |
| `/api/b2b/portal/logs?page&limit` | GET | Bearer | Seller's own API request log | `0o45.cg_g4a77.js` |
| `/api/b2b/portal/analytics?days` | GET | Bearer | Usage analytics | `0o45.cg_g4a77.js` |
| `/api/b2b/portal/key/rotate` | POST | Bearer | Re-issue seller API key | `0o45.cg_g4a77.js` |
| `/api/b2b/portal/webhook` | PUT | Bearer | Register callback URL | `0o45.cg_g4a77.js` |
| `/api/b2b/portal/pricing` | GET | Bearer | **declared, never called** | map only |
| `/api/b2b/portal/topup` | POST | Bearer | **declared, never called** | map only |
| `/api/admin/b2b/overview?days` | GET | Bearer + admin | Operator KPIs | `0mhu~2w72ast2.js` |
| `/api/admin/b2b/tenants?page&limit&search` | GET | Bearer + admin | Seller list | `0mhu~2w72ast2.js` |
| `/api/admin/b2b/logs?page&limit&endpoint&status&search` | GET | Bearer + admin | Gateway request log | `0mhu~2w72ast2.js` |
| `/api/admin/b2b/tenants/:id/credits` | POST | Bearer + admin | `{amount, action: add\|deduct\|set}` | `0mhu~2w72ast2.js` |
| `/api/admin/b2b/tenants/:id/toggle-status` | POST | Bearer + admin | Suspend / reactivate | `0mhu~2w72ast2.js` |
| `/api/referral/*` (8 paths) | mixed | Bearer | **404, no route, no call site** | map only |
| `/api/auth/spoofer-state` | GET / POST | Bearer | Coin balance + history; `{task_id}` | `0nh-y8e1a0l~a.js` |
| `/api/auth/spoofer-check-cost` | POST | Bearer | `{asset_ids[]}` → `cost`, `has_ugc` | `0nh-y8e1a0l~a.js` |
| `/api/auth/spoofer-deduct` | POST | Bearer | `{asset_count, asset_ids[]}` | `0nh-y8e1a0l~a.js` |
| `/api/payment/create-coin-invoice` | POST | Bearer | `{coins, paymentMethod:"qris"}` | `0nh-y8e1a0l~a.js` |
| `/api/payment/paypal/create-coin-order` | POST | Bearer | `{coins}` | `0nh-y8e1a0l~a.js` |
| `/api/payment/paypal/capture-coin-order` | POST | Bearer | `{paypalOrderId, orderId, coins}` | `0nh-y8e1a0l~a.js` |
| `/api/spoofer-jobs` | POST / GET | Bearer | Create / list user jobs | `0nh-y8e1a0l~a.js` |
| `/api/spoofer-jobs/:id` | GET / PATCH | Bearer | Detail / update progress | `0nh-y8e1a0l~a.js`, `0mhu~2w72ast2.js` |
| `/api/spoofer-jobs/admin/all` | GET | Bearer + admin | `?page&limit&status&assetType&search` | `0mhu~2w72ast2.js` |
| `/api/upload/quota` | POST | Bearer | `{}` → `remaining`, `is_admin` | `0yomchjmrny8f.js` |
| `/api/upload/batch` | POST | Bearer | multipart: `creator_id`,`is_group`,`target_name`,`files[]` | `0yomchjmrny8f.js` |
| `/api/upload/jobs`, `/jobs/:id`, `/jobs/:id/retry` | GET / POST | Bearer | Upload job tracking; retry `{item_index}` | `0yomchjmrny8f.js` |
| `/api/upload/health` | GET | **Public** | Service health | verified live 200 |
| `/api/auth/me` | GET | Bearer | Session/user; gates all UI | many |
| `/api/auth/refresh` | POST | cookie | **404 — route missing** | `0vs148roxm~ft.js` |
| `/api/auth/roblox/login` | GET | Turnstile + popup | Roblox OAuth | `0k1tyysfi6yay.js` |
| `/api/auth/google/login` | GET | Turnstile + popup | Google OAuth | `0jxi_hvhi.3ae.js` |
| `/api/auth/roblox/save-api-key` | POST | Bearer | `{apiKey,creatorId,creatorType,from}` | `0a8pu3n7fv_vz.js` |
| `/api/auth/roblox/unlink` | POST | Bearer | `{from}` | `0a8pu3n7fv_vz.js` |
| `/api/auth/logout` | POST | cookie | raw fetch + `?t=` cache-buster | `0a6h4o63da-vz.js` |
| `/api/experience/my-list`, `/api/experience` | GET / POST | Bearer | Profile license; multipart create | `0f8dbzohbyw1o.js` |
| `/api/activity/logs?month` | GET | Bearer | Audit timeline | `0_c4xg1tyr_uo.js` |
| `engine /api/download/batch/async` | POST | **none** (Roblox creds) | Core spoof/download | `0nh-y8e1a0l~a.js` |
| `engine /api/task/:id/status` | GET | **none** | Polled every 1500 ms | `0nh-y8e1a0l~a.js` |
| `engine /api/upload/batch` | POST | **none** | Re-upload to Roblox Open Cloud | `0nh-y8e1a0l~a.js` |
| `engine /api/proxy/roblox-thumbnail` | GET | **none** | Thumbnail CORS proxy | `0nh-y8e1a0l~a.js` |
| `engine /api/files/download/{filename}` | GET | **none** | Serve downloaded file | spec only |
| `engine /api/files/zips/{filename}` | GET | **none** | Serve batch ZIP | spec only |
| `engine /api/scan/place/{place_id}` | GET | Roblox creds | Enumerate a game's assets | spec only |
| `engine /api/download/{asset_id}` | GET | Roblox creds | Single download; **`place_id` = "Place ID to spoof for private assets"** | spec only |
| `engine /api/asset/{asset_id}` | GET | none/cookie | Asset metadata | spec only |
| `engine /openapi.json`, `/docs`, `/redoc` | GET | **Public** | Full API contract | verified live 200 |

## Frontend-visible vs backend-only

**Frontend-visible (retrieved):** tab/lock state machine; hardcoded pack and plan tables; the
`0/15/30/50` coin schedule and admin/owner exemption; log and job filter enums; page sizes
(50/20/15/10); `bmk_spoof_` prefix and plaintext key persistence; masked `webhook_secret`; the
1500 ms poll and localStorage resume; the 500-ID / 1 MB / 420 s client caps; the filename sanitiser.

**Backend-only (not retrievable):** real credit and coin arithmetic; whether `has_ugc` changes
price; gateway host, its auth scheme and rate limiter; webhook delivery, payload, HMAC signing
(`webhook_secret` implies it, no code confirms it) and retries; API-key hashing and rotation
invalidation; whether any client-side cap is enforced; the spoof transformation itself; PayPal
and QRIS capture; JWT signing; RBAC; Turnstile verification.

## Notable defects found (frontend-observable, not exploited)

1. `POST /api/auth/refresh` → **404**, so `apiFetch`'s only token-renewal path is dead; every
   expiry is a hard logout. Availability issue, not a security hole.
2. `http://localhost:3001` ships in the production bundle as the API-host fallback.
3. `/api/auth/spoofer-check-cost` is used but **absent from the `apiEndpoints` map** — undeclared.
4. **Three high-value secrets in plaintext `localStorage`** on one origin: `bmk_token`,
   `bmk_b2b_raw_key` (full seller key), `bmk_spoofer_user_cookie` (live `.ROBLOSECURITY`).
   The third is also forwarded to a **different origin** (`spoofer.blokmarket.store`).
5. The dashboard `bmk_token` is passed **as a URL query parameter** into the OAuth popup.
6. The engine accepts a **bearer token as a query parameter** and **echoes any caller `Origin`**
   with `access-control-allow-credentials: true`.
7. `/api/download/batch/async` accepts an undocumented flat `asset_ids` array, validated by a
   hand-written check rather than Pydantic — the loosest surface in the engine.
8. `default-avatar.png` is referenced in code but 404s.

## ToS note (material to any integration decision)

The engine's own spec describes `/api/scan/place/{place_id}` as scanning a Roblox game for
Audio/Animation/Emote IDs, and `/api/download/{asset_id}` as taking a `place_id` to
*"spoof for private assets"*, with `/api/upload/batch` re-publishing through Roblox Open Cloud.
Extracting assets out of experiences and re-uploading them under a new creator ID conflicts with
Roblox's Terms of Service, and re-uploading third-party audio without the rightsholder's
permission implicates copyright. That is a property of the service being integrated, not of this
analysis — but it is a decision the integrator has to make knowingly.
