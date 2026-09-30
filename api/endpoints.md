# Endpoint Reference — customer.blokmarket.store

Analysis date **2026-09-30**. All request/response pairs in `responses/` are byte-exact captures.
**No token, cookie, key or secret was fabricated.** No authentication control was bypassed.

---

## 0. Request mechanisms actually present in the bundles

| Mechanism | Present? | Evidence |
|---|---|---|
| `fetch` | **Yes — the only one** | 19 raw `fetch(` sites; 88 `apiFetch)(…apiEndpoints.…` sites |
| `XMLHttpRequest` | Only inside the core-js legacy polyfill chunk `03~yq9q893hmn.js` — not app code | 1 hit |
| Axios | No | 0 hits |
| GraphQL | No | 0 hits |
| WebSocket / EventSource (SSE) | **No** | 0 hits, no `wss://` in any chunk |
| `navigator.sendBeacon` | No | 0 hits |
| Next.js RSC navigation + Server Actions | Yes, framework-internal only | `00nlt7x_9mi4z.js` — no app Server Action IDs present in any route HTML |
| `FormData` multipart | Yes — 3 endpoints | `audio.uploadConvert`, `experience.create`, `upload.batch` |

There is **no long-lived connection** to either backend. The only polling in the app is a
`setInterval(…, 1500)` against the engine's task-status endpoint.

### The single request implementation (verbatim, `0vs148roxm~ft.js` / `11wojmndz1p1s.js`)

```js
let t = "https://backend.blokmarket.store".replace(/\/+$/,"") || "http://localhost:3001";
function o(e){ let o = e.startsWith("/") ? e : `/${e}`; return `${t}/api${o}` }

async function n(e, t = {}) {
  let o, a = localStorage.getItem("bmk_token"),
      i = new Headers(t.headers || {});
  a && i.set("Authorization", `Bearer ${a}`);
  let l = () => fetch(e, { ...t, headers: i, credentials: "include" });
  try { o = await l() }
  catch (t) { return { ok:false, status:0, json: async()=>({success:false,message:"Connection failed"}) } }
  if (401 === o.status && localStorage.removeItem("bmk_token"), "/login" !== window.location.pathname)
    try {
      (await fetch(r.auth.refresh(), { method:"POST", credentials:"include" })).ok
        ? o = await l()
        : window.location.href = "/login"
    } catch (e) { window.location.href = "/login" }
  return o
}
// exports: API_HOST, apiEndpoints, apiFetch, buildApiUrl
```

**Static vs dynamic values**

| Value | Kind | Source |
|---|---|---|
| `https://backend.blokmarket.store` | **static**, string literal | baked in at build time |
| `http://localhost:3001` | **static** dev fallback, shipped to production | `\|\|` fallback |
| `https://spoofer.blokmarket.store` | **static**, string literal | `0nh-y8e1a0l~a.js` |
| `https://audio.blokmarket.store` | **static**, template literal | `0vs148roxm~ft.js` |
| `Authorization: Bearer …` | **dynamic** | `localStorage.bmk_token`, set post-OAuth |
| `?t=${Date.now()}` cache-buster | **dynamic** | appended on logout, OAuth entry, payment history |
| `:id` path segments | **dynamic** | task_id, job id, history id from responses/state |
| `cf_token` | **dynamic** | Cloudflare Turnstile token rendered server-side |
| `body.assets[].id` / `custom_name` | **dynamic** | user-typed LUA table / ID list |
| `?month=`, `?page=`, `?limit=`, `?days=`, `?search=`, `?status=`, `?endpoint=` | **dynamic** | UI state |
| PayPal `client-id` | **static** literal | `BAAE2aLMSjM7xZd0hscKvOCGclROj47Dcgx5OVRxz25I4FXB9o2CCw4NEHYV1oTRGP5RNMRbmjA7bnPWiM` |
| `X-Roblox-Cookie` | **dynamic**, user-supplied | `localStorage.bmk_spoofer_user_cookie` |

---

## 1. Two backends, two error conventions

| | `backend.blokmarket.store` | `spoofer.blokmarket.store` |
|---|---|---|
| Stack | Node/Express-style | **FastAPI / Pydantic (Python)** |
| Success envelope | `{"success":true, …}` | bare object, **no envelope** |
| Error envelope | `{"success":false,"message":"…"}` | `{"detail": …}` (string or FastAPI array) |
| Auth | `Authorization: Bearer` + cookies | **none at the HTTP layer**; Roblox creds per request |
| Docs | none published | **OpenAPI 3.1 at `/openapi.json` — public** |

The engine's published spec (`spoofer-engine-openapi.json`, saved verbatim) is titled
**"Roblox Asset Downloader Core Service"**, described as
*"Python-based high performance asynchronous backend to scan and download Roblox audios, animations, and emotes."*

---

# ORIGIN A — `https://backend.blokmarket.store`

## A1. `GET /api/product/category`

**Authentication** — none required. Reachable with no token.

**Request** — no headers beyond `Accept`, no body, no query params.

**Example**
```bash
curl -sS -H 'Accept: application/json' 'https://backend.blokmarket.store/api/product/category'
```

**Response** — `200 application/json` (observed, `responses/05-product-category.txt`)
```json
{"success":true,"data":[{"id":"a4ba377b-d658-49ee-b66c-a88ed0c339c1","name":"Free",
 "description":"Kategori untuk produk yang tersedia secara gratis.",
 "created_at":"2026-04-23T14:47:30.007572+00:00","slug":"free"}]}
```

**Frontend flow** — product catalogue page mount → `apiFetch(apiEndpoints.product.categoryList())`
→ `res.json().data` → category filter chips.

---

## A2. `GET /api/product`

**Authentication** — none required.

**Request** — `GET /api/product`, no params, no body.

**Example**
```bash
curl -sS -H 'Accept: application/json' 'https://backend.blokmarket.store/api/product'
```

**Response** — `200` (observed, `responses/06-product-list.txt`)
```json
{"success":true,"data":[{"id":"0519e1b6-3056-4702-afa6-7f72ee9fdf8a",
 "category_id":"5d98584b-f01e-4167-9b35-5995dd6c83e6","name":"Music Player","price":400000,
 "thumbnail":"/public/uploads/products/prod-1783858499769-887318825.png",
 "images":[],"created_at":"2026-07-12T12:15:00.169449+00:00","is_active":true,
 "slug":"music-player-9796","thumbnail_url":null}]}
```

**Frontend flow** — shop page mount → `apiEndpoints.product.list()` → grid of product cards with
`price` rendered against the coin balance.

---

## A3. `GET /api/upload/health`

**Authentication** — none required.

**Response** — `200` (observed, `responses/07-upload-health.txt`)
```json
{"success":true,"data":{"status":"healthy","service":"bmk-upload","active_jobs":0}}
```

**Frontend flow** — upload tool health indicator / service banner.

---

## A4. `GET /api/audio/approved-count`

**Authentication** — none required. Returns a bare `count`, **not** wrapped in `data`.

**Response** — `200` (observed, `responses/22-audio-approved-count.txt`)
```json
{"success":true,"count":32958}
```

**Frontend flow** — `audio.approvedCount()` → public "N approved" counter.

---

## A5. `GET /api/audio/approved-daily-stats`

**Authentication** — none required.

**Response** — `200` (observed, `responses/23-audio-approved-daily-stats.txt`)
```json
{"success":true,"data":[{"date":"2026-09-26","day":"Sat","count":197},
 {"date":"2026-09-30","day":"Wed","count":254}]}
```

**Frontend flow** — `audio.approvedDailyStats()` → 7-day sparkline. Consumed field: `data[].date`, `data[].day`, `data[].count`.

---

## A6. `GET /api/auth/me` — the auth gate

**Authentication** — requires `Authorization: Bearer <bmk_token>`. **Browser session not required**
(a plain bearer token suffices, per the client code); `credentials:"include"` is also sent.

**Request** — no body, no params.

**Example (no token — observed)**
```bash
curl -sS -i 'https://backend.blokmarket.store/api/auth/me'
```

**Response** — `401 application/json; charset=utf-8` (observed, `responses/01-auth-me-no-token.txt`)
```json
{"success":false,"message":"No token"}
```
> Note the message is `"No token"`, **not** the generic `"Unauthorized"` used by every other route.

**Frontend flow** — every page mount → `apiFetch(auth.me())` → `res.json().data` assigned to the
Jotai `userAtom`; the app shell gates all UI on it. A `401` triggers the refresh-retry path.

---

## A7. `POST /api/auth/refresh` — **documented client call that does not exist**

**Authentication** — would require a refresh cookie in the browser jar. Not tested with any session.

**Response** — `404` (observed both `GET` and `POST`, `responses/02`, `responses/12`)
```json
{"success":false,"message":"Endpoint not found"}
```

**Why this matters** — `apiFetch` calls this exact path on every `401`, as the sole token-renewal
mechanism. It resolves `404`, `ok` is false, so the wrapper sets `window.location.href = "/login"`.
**The silent-refresh path is dead as shipped**: every expired token is a hard logout, with no
localStorage token ever being renewed. This is a client-observable defect, not a bypass — it makes
sessions shorter, not weaker.

---

## A8. `POST /api/auth/spoofer-check-cost`

**Authentication** — required. `POST /api/auth/spoofer-deduct` — required.

> **Declared nowhere in the app's own `apiEndpoints` map.** The page builds it ad hoc:
> `apiFetch(buildApiUrl("/auth/spoofer-check-cost"), …)`. Undeclared surface.

**Request** — `application/json`
```json
{ "asset_ids": ["<robloxAssetId>", "…"] }
```
Origin: the parsed user ID list (`e.map(e => e.id)`), before the cost modal opens.

**Response** — consumed fields: `success`, `cost`, `has_ugc`, `message`. Shape is
**inferred from the handler only**; no authenticated response was observed. Without a token:
`401 {"success":false,"message":"Unauthorized"}` (observed, `responses/20`).

**Frontend flow** — user pastes IDs → parse → admin/owner bypasses the pre-check → else
`check-cost` → `{cost, has_ugc}` → cost modal (`has_ugc` picks the per-asset price tier) →
"Free Spoof" / pay-with-coins button.

---

## A9. `POST /api/spoofer-jobs` and `PATCH /api/spoofer-jobs/:id`

**Authentication** — required.

**Request** — `application/json`
```json
{ "job_id":"<taskId>", "status":"pending", "total_assets":<n>,
  "success_count":0, "failed_count":0,
  "asset_breakdown":{ "<AssetType>": {"success":0,"failed":0} } }
```
```json
{ "status":"<completed|failed>", "success_count":<n>, "failed_count":<n>,
  "asset_breakdown":{…}, "files":[…], "logs":[…last 500…] }
```
`files[]` item: `{id, custom_name, status, file_name, file_size, asset_type, uploaded_asset_id, upload_status, upload_error}`.

**Frontend flow** — a non-free run records a `pending` job on submit; each poll tick that changes an
asset status, or the terminal state, `PATCH`es the job. Backs `/tools/history?tab=spoofer`
and `/admin/spoofer-history`.

---

## A10. `POST /api/auth/roblox/save-api-key`

**Authentication** — required. `Content-Type: application/json`
```json
{ "apiKey":"<roblox open cloud key>", "creatorId":"<user|group id>",
  "creatorType":"User|Group", "from":"spoofer"|"bmk_upload" }
```
`from` is omitted for the audio tool (`from:"audio"===e ? void 0 : e`).
Origin: the "Connect Roblox" modal inputs `P` / `B` / `O` in `0a8pu3n7fv_vz.js`.
Response consumed: `success`, `message`. On success the page calls `location.reload()`.

---

# ORIGIN B — `https://spoofer.blokmarket.store` (the "engine")

Contract below is copied from the service's **own published OpenAPI 3.1 spec**
(`spoofer-engine-openapi.json`). Not inferred from names.

**Authentication** — *none at the HTTP layer.* The frontend uses raw `fetch` here, so **no
`Authorization` header and no `credentials` mode** are sent. Roblox credentials ride per request:
`?authorization=<OAuth bearer>` **or** header `X-Roblox-Cookie: <.ROBLOSECURITY>`, plus
`?x-roblox-cookie=` as a query alternative on some routes.

**CORS** (observed, `responses/16`) — the engine **echoes the caller's `Origin`** with
`access-control-allow-credentials: true` and `max-age: 600`:
```
access-control-allow-origin: https://customer.blokmarket.store
access-control-allow-headers: content-type,x-roblox-cookie
```
The backend, by contrast, returns `access-control-allow-credentials: true` but
**no `access-control-allow-origin`** for a foreign origin (`responses/17`) — so a browser on
another site cannot read backend responses, but a non-browser client can.

---

## B1. `POST /api/download/batch/async` — the core operation

**Request** — `application/json`, body `BatchDownloadRequest` (from the spec):

| Field | Type | Required | Default | Spec description |
|---|---|---|---|---|
| `asset_ids` | `integer[] \| null` | no | — | "Optional flat list of Roblox Asset IDs" |
| `assets` | `AssetBatchItem[] \| null` | no | — | "Optional list of structured Asset IDs with custom names" |
| `roblox_api_key` | `string \| null` | no | — | "Roblox Open Cloud API Key for auto upload" |
| `creator_id` | `string \| null` | no | — | "Roblox User or Group Creator ID to upload under" |
| `creator_type` | `string \| null` | no | — | "Creator Type (User or Group)" |
| `is_free` | `boolean \| null` | no | `false` | "Is this a free spoof request?" |

`AssetBatchItem` = `{ id: integer (required), custom_name: string \| null }`.

**Exactly what the UI sends** — only `assets` and `is_free`:
```json
{ "assets": [ {"id": 123456789, "custom_name": "my-audio"} ], "is_free": false }
```
Headers: `Content-Type: application/json`, and `X-Roblox-Cookie: <.ROBLOSECURITY>` **only** when
`is_free` is false and the user pasted a cookie.

**Response** — `200`, `{"task_id": "<uuid>"}`. The spec leaves this as an untyped schema.

**Tested** — validation-only. `{"assets":[],"is_free":false}` → **`400`**:
```json
{"detail":"Either 'asset_ids' or 'assets' must be provided."}
```
(`responses/18`). `{"assets":"not-a-list"}` → `422` (`responses/30`). `{"asset_ids":[]}` → `400` (`responses/29`).

> **Discovered by testing, not by reading names:** the server accepts a flat `asset_ids` array as an
> alternative to `assets`. The frontend never sends it. Because both are optional in the schema and
> the emptiness check is a manual `detail` string rather than Pydantic, this endpoint is the least
> strictly-validated surface in the engine.

**Not tested** — a payload with real asset IDs was deliberately **not** sent, because that would run
the service's actual download/bypass function. Status for successful execution: **UNTESTED**.

**Frontend flow** — `sY` (start run) builds `r = {Content-Type:"application/json"}`, adds
`X-Roblox-Cookie` when applicable, POSTs, takes `task_id`, stores
`bmk_spoofer_active_task = {task_id, parsedAssets, isSingle, batchId, startedAt}`, then enters
`s1()` polling. Non-`!res.ok` reads `s.detail` into the toast.

---

## B2. `GET /api/task/{task_id}/status`

**Authentication** — none.

**Query** — `task_id` (path, required).

**Response** — `200`; fields consumed by the client: `status`, `queue_position`, `total_queue`,
`assets[]` where each asset has `id`, `status`, `real_name`, `custom_name`, `asset_type`,
`file_name`, `file_size`, `uploaded_asset_id`, `error`. Spec types this response as untyped.

**Tested** — bogus id → **`404 {"detail":"Task not found."}`** (`responses/14`).

**Frontend flow** — `setInterval(n, 1500)`. Queue fields render `Waiting Queue (n/total)`.
Per-asset status transitions push timestamped lines into `bmk_spoofer_logs`.
`404` → clear interval, drop `bmk_spoofer_active_task`. Also re-checked on `visibilitychange`
and window `focus`.

---

## B3. `POST /api/upload/batch` — re-upload to Roblox

**Authentication** — none at the HTTP layer. Roblox creds are in the **body**.

**Request** — `application/json`, body `UploadBatchRequest`:

| Field | Type | Required | Spec description |
|---|---|---|---|
| `files` | `UploadBatchItem[]` | **yes** | List of files to upload |
| `creator_id` | `string` | **yes** | Roblox User or Group Creator ID |
| `creator_type` | `string` | **yes** | Creator Type (User or Group) |
| `roblox_api_key` | `string \| null` | no | Roblox Open Cloud API Key |
| `roblox_access_token` | `string \| null` | **no** | Roblox OAuth Access Token |
| `custom_description` | `string \| null` | no | "Custom white-label description for Roblox asset" |

`UploadBatchItem` = `{ file_name: string (required), display_name: string (required), asset_type: string|null }`.

What the UI sends (from `0nh-y8e1a0l~a.js`) — one asset per request, serially:
```json
{ "files":[<one asset>], "roblox_access_token":"<user oauth token>",
  "creator_id":"<roblox_id>", "creator_type":"User|Group" }
```
`creator_type` is computed as `ex.roblox_id ? "Group" : "User"`.
The token comes from `userAtom.spoofer_state.roblox.roblox_access_token`.

**Response** — `UploadBatchResponse`: `{total, success_count, failed_count, results[]}` where
`AssetUploadResult` = `{file_name, success, asset_id|null, error|null}`. Client reads
`results[0]`, treats `401`/`403` or an error containing `401` / `"invalid token"` as a dead token.

**Tested** — empty body → **`422`**, confirming exactly which fields are required:
```json
{"detail":[{"type":"missing","loc":["body","files"],"msg":"Field required","input":{}},
           {"type":"missing","loc":["body","creator_id"],"msg":"Field required","input":{}},
           {"type":"missing","loc":["body","creator_type"],"msg":"Field required","input":{}}]}
```
(`responses/19`). Note `roblox_access_token` is **absent** from the required list.

**Not tested** — uploading requires a real Roblox OAuth token, which was not available. **UNTESTED.**

---

## B4. `GET /api/proxy/roblox-thumbnail`

**Query** — `assetIds` (required), `size` (default `150x150`), `format` (default `Png`), `isCircular` (default `false`).

**Response** — `200` (observed, `responses/13`)
```json
{"data":[{"targetId":1846853302,"state":"Blocked",
 "imageUrl":"https://tr.rbxcdn.com/…/150/150/UnapprovedImage/Png/noFilter","version":"TN3.5"}]}
```

**Frontend flow** — memoised per asset id; `size` is `150x150` in the list and `420x420` in the
detail modal. Result is put straight into `<img referrerPolicy="no-referrer">`.

---

## B5–B16. Remaining engine endpoints — documented from the published spec, **UNTESTED**

| Method | Path | Spec summary | Notable spec detail |
|---|---|---|---|
| GET | `/` | Serve Index | *"Serves the main frontend index.html if compiled, otherwise returns healthy status."* → observed `403` (`responses/15`) |
| GET | `/api/scan/place/{place_id}` | Scan Place | *"Scans a Place ID for asset references (Audio, Animations, Emotes)… Accepts either `Authorization: Bearer {oauth_token}` or `x-roblox-cookie`"*; `page=1`, `limit=30`; → `PlaceScanResponse{place_id,place_name,total_found,pagination,assets}` |
| GET | `/api/download/{asset_id}` | Download Asset | query `custom_name`, **`place_id` — "Optional custom Place ID to spoof for private assets"**, `authorization`, `x-roblox-cookie`; → `DownloadResult` incl. `uploaded_asset_id` |
| POST | `/api/download/batch` | Download Batch | *"generating a ZIP package if successful downloads > 1"*; → `BatchDownloadResponse{total,success_count,failed_count,results,zip_download_url}` |
| GET | `/api/asset/{asset_id}` | Get Asset Info | *"Retrieves and caches Roblox asset metadata"*; → `AssetInfo` |
| GET | `/api/files/download/{filename}` | Serve Downloaded File | *"while preventing path traversal attacks"*; `inline` |
| GET | `/api/files/zips/{filename}` | Serve Zip Archive | |
| GET | `/api/proxy/roblox-thumbnail-3d` | 3D Thumbnail | *"using backend ROBLOSECURITY cookie to bypass CORS"* — **the engine holds a Roblox session of its own** |
| GET | `/api/proxy/roblox-user-avatar-3d` | Avatar 3D | same, uses backend cookie |
| GET | `/api/proxy/roblox-3d-file` | 3D File | *"Proxies requests to the Roblox CDN (rbxcdn.com)"* |
| GET | `/api/proxy/roblox-toolbox` | Proxy Toolbox | Creator Store search |
| GET | `/api/proxy/roblox-catalog` | Proxy Catalog | *"Avatar Emotes/Animations"* |

> **This is the "spoof" mechanism, stated by the service itself.** `/api/download/{asset_id}`
> takes a `place_id` whose own spec description is *"Optional custom Place ID to spoof for private
> assets"*. `/api/scan/place/{place_id}` enumerates every Audio/Animation/Emote ID inside a game.
> Combined with `/api/upload/batch` (Roblox Open Cloud), the service scrapes assets out of Roblox
> experiences and re-publishes them under the requester's own creator ID. The dashboard UI labels
> the output "New Spoofed ID"; the engine calls the same value `uploaded_asset_id`.
>
> These four were **not executed** — doing so is the service's actual purpose.

---

# ORIGIN C — `https://audio.blokmarket.store`

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/download/:id/:fileName` | none observed | Template literal in `audio.download(e,t)`; not covered by `apiFetch`, so no bearer is attached. **UNTESTED** — no valid id available. |

---

# ORIGIN D — third-party

| Origin | Used for | Request |
|---|---|---|
| `www.paypal.com/sdk/js` | PayPal Buttons SDK | `?client-id=BAAE2aLMSjM7xZd0hscKvOCGclROj47Dcgx5OVRxz25I4FXB9o2CCw4NEHYV1oTRGP5RNMRbmjA7bnPWiM&curre…` (truncated in bundle) |
| `api.qrserver.com` | QRIS QR PNG | `GET /v1/create-qr-code/?data=<urlencoded>&size=600x600&bgcolor=ffffff&color=000000&margin=2`, result read via `.blob()` |
| `i.ibb.co.com` | one help image | `GET /xtby0WnJ/secur.png` (observed `200`) |

---

## What could NOT be tested, and why

| Endpoint group | Why not |
|---|---|
| All `Authorization`-protected backend routes (95 of 101 declared) | **No credentials were supplied and none were guessed.** Each was called once **without** a token; all returned `401`. Confirming the 401 envelope is not a bypass. |
| `/api/auth/refresh` with a session | Needs a real refresh cookie from a live login. Confirmed `404` unauthenticated only. |
| `/api/payment/*` (12 routes) | **Not called at all.** Creating invoices and PayPal orders is financial, state-changing. |
| `/api/auth/spoofer-deduct` | Spends a real coin balance. Not called. |
| `/api/auth/roblox/save-api-key`, `/api/auth/roblox/unlink` | Mutates the linked account. Not called. |
| `POST /api/upload/batch` (successful) | Requires a real Roblox OAuth token. Validation path only. |
| `POST /api/download/batch/async` (successful) | Would run the download/bypass. Validation path only. |
| Engine `/api/scan/place/*`, `/api/download/{id}`, `/api/download/batch`, `/api/asset/{id}` | These *are* the asset-extraction function. Deliberately not executed. |
| `DELETE` / `PATCH` mutating routes | Not called. |
| `audio.blokmarket.store/api/download/…` | Needs a valid job id. Not called. |

## Rate limiting
None observed. No `Retry-After`, no `X-RateLimit-*`, no 429 across 31 requests.
CORS `access-control-max-age: 600` on the engine only affects preflight caching.
The UI shows no client-side rate limiting; whether the server throttles is **unknown** — not
determinable without issuing many requests, which was not done.
