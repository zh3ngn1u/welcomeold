# Endpoint Inventory — every endpoint the Bulk Spoofer tool touches

**Every** endpoint used by `/tools/bulk-spoofer`, not just the spoofer engine. 18 call sites
across three origins: 18 `apiFetch` sites + 8 raw `fetch` sites in `../js/0nh-y8e1a0l~a.js`.

Legend — `✅ seen` = response captured in `../api/responses/`; `📦 declared` = in the
`apiEndpoints` map or engine spec, no live response observed; `🔒 spec` = published OpenAPI only.

---

## Origin 1 — `https://backend.blokmarket.store` (Bearer `bmk_token`)

| # | METHOD | Path | Handler | Request | Response (fields used) | Status |
|---|---|---|---|---|---|---|
| 1 | GET | `/api/auth/me` | page mount + post-Turnstile | — | `success`,`data` → `id,name,email,role,experience_limit,plan_type,spoofer_state{roblox{…},coins,history[]},audio_plan,audio_plan_expires` | ✅ seen `401 {"success":false,"message":"No token"}` |
| 2 | GET | `/api/auth/spoofer-state` | mount, post-payment | — | `success`,`data.coins`,`data.history[]` | ✅ seen `401` |
| 3 | POST | `/api/auth/spoofer-state` | job terminal | `{"task_id":"<id>"}` | `success`,`data` | 📦 declared |
| 4 | POST | `/api/auth/spoofer-check-cost` | `s2` pre-check | `{"asset_ids":["…"]}` | `success`,`cost`,`has_ugc`,`message` | ✅ seen `401` |
| 5 | POST | `/api/auth/spoofer-deduct` | `s4` | `{"asset_count":n,"asset_ids":[…]}` | `success`,`coins`/`newCoins`,`message` | 📦 declared — **not called, spends real balance** |
| 6 | POST | `/api/spoofer-jobs` | non-free submit | `{"job_id","status":"pending","total_assets","success_count":0,"failed_count":0,"asset_breakdown"}` | `success`,`data` | 📦 declared |
| 7 | PATCH | `/api/spoofer-jobs/:id` | `sY` / `sX` on each change + terminal | `{"status","success_count","failed_count","asset_breakdown","files":[…],"logs":[…]}` (`logs` truncated to last 500) | `success`,`message` | 📦 declared |
| 8 | GET | `/api/auth/roblox/groups` | group picker | — | `success`,`data[]` | 📦 declared |
| 9 | POST | `/api/auth/roblox/save-api-key` | link modal | `{"apiKey","creatorId","creatorType","from":"spoofer"}` | `success`,`message` | 📦 declared — account-mutating |
| 10 | POST | `/api/auth/roblox/unlink` | unlink | `{"from":"spoofer"}` | `success`,`message` | 📦 declared — account-mutating |
| 11 | POST | `/api/auth/roblox/refresh` | **silent token refresh** (upload `401`) | `{"from":"spoofer"}` | `success`,`robloxAccessToken` | 📦 declared |
| 12 | GET | `/api/auth/roblox/login` | OAuth popup entry | query `cf_token`,`token`,`from=spoofer`,`t` | popup HTML; result arrives via `postMessage` | 📦 declared |
| 13 | POST | `/api/payment/create-coin-invoice` | QRIS top-up | `{"coins":n,"paymentMethod":"qris"}` | `success`,`qrString`,`trxId`,`totalTransfer`,`isCoinTopUp`,`coins` | 📦 declared — financial |
| 14 | POST | `/api/payment/paypal/create-coin-order` | PayPal top-up | `{"coins":n}` | `success`, PayPal order | 📦 declared — financial |
| 15 | POST | `/api/payment/paypal/capture-coin-order` | PayPal `onApprove` | `{"paypalOrderId","orderId","coins"}` | `success`,`coins` | 📦 declared — financial |
| 16 | GET | `/api/payment/check/:id` | **QRIS poll, 3 s** | query none | `success`,`status` ∈ `SUCCESS`\|`EXPIRED`\|`CANCELED`,`coins` | 📦 declared |
| 17 | GET | `/api/auth/logout` *(app shell)* | logout | `?t=<ts>`, `credentials:"include"` | — | 📦 declared |
| 18 | GET | `/api/auth/refresh` | `apiFetch` 401-retry wrapper | — | `{"success":false,"message":"Endpoint not found"}` | ✅ seen **`404`** |

> #4 is **not present in the app's `apiEndpoints` map** — the page builds it with
> `buildApiUrl("/auth/spoofer-check-cost")`. Undeclared surface.

## Origin 2 — `https://spoofer.blokmarket.store` (the engine — **no auth header, no cookies**)

| # | METHOD | Path | Handler | Request | Response | Status |
|---|---|---|---|---|---|---|
| 19 | POST | `/api/download/batch/async` | `s5` | headers `Content-Type: application/json` (+ `X-Roblox-Cookie` when `!is_free`); body `{"assets":[{id,custom_name}],"is_free":bool}` | `{"task_id"}` | ✅ seen `400 {"detail":"Either 'asset_ids' or 'assets' must be provided."}`, `422` Pydantic — **successful run deliberately NOT executed** |
| 20 | GET | `/api/task/:taskId/status` | poll `n` in `s1` (+ refocus) | — | `status`,`queue_position`,`total_queue`,`assets[]{id,status,real_name,custom_name,asset_type,file_name,file_size,uploaded_asset_id,error}`,`zip_download_url` | ✅ seen `404 {"detail":"Task not found."}`; `200` on the thumbnail route |
| 21 | POST | `/api/upload/batch` | upload loop `x` | `{"files":[<one asset>],"roblox_access_token","creator_id","creator_type"}` — **one asset per request** | `{total,success_count,failed_count,results[]{file_name,success,asset_id,error}}` | ✅ seen `422` required `files`,`creator_id`,`creator_type` — successful run NOT executed |
| 22 | GET | `/api/proxy/roblox-thumbnail` | `ei` list, `er` modal | `?assetIds&size=150x150\|420x420&format=Png&isCircular=false` | `data[0].imageUrl` | ✅ seen `200` |

## Origin 3 — third-party

| # | METHOD | URL | Purpose | Status |
|---|---|---|---|---|
| 23 | GET | `https://api.qrserver.com/v1/create-qr-code/?data=<enc>&size=600x600&bgcolor=ffffff&color=000000&margin=2` | QRIS QR PNG → `.blob()` → download | 📦 declared |
| 24 | GET | `https://www.paypal.com/sdk/js?client-id=BAAE2aLMSjM7xZd0hscKvOCGclROj47Dcgx5OVRxz25I4FXB9o2CCw4NEHYV1oTRGP5RNMRbmjA7bnPWiM&curre…` | PayPal Buttons SDK | 📦 declared |
| 25 | GET | `https://i.ibb.co.com/xtby0WnJ/secur.png` | help image | ✅ seen `200` |
| 26 | GET | `https://youtu.be/Ermk2raFzLo` | tutorial, `window.open` | 📦 declared |
| 27 | GET | `/bandingkan.png` (same origin) | comparison-modal image | ✅ seen `200` |
| 28 | GET | `/audio/cashsound.mp3` (same origin) | `new Audio(...)` on payment success | 📦 declared |
| 29 | GET | `/coins60.png`, `/coins150.png`, `/coins350.png` | coin-tier imagery | ✅ seen `200` |

---

## Engine endpoints that exist but the Bulk Spoofer NEVER calls

Documented for completeness — **not part of this tool's workflow**.

| METHOD | Path | Spec summary |
|---|---|---|
| GET | `/api/scan/place/{place_id}` | "Scans a Place ID for asset references (Audio, Animations, Emotes)"; `page=1`,`limit=30`; `PlaceScanResponse` |
| GET | `/api/download/{asset_id}` | `custom_name`, **`place_id` — "Optional custom Place ID to spoof for private assets"**, `authorization`, `x-roblox-cookie`; → `DownloadResult` |
| POST | `/api/download/batch` | synchronous batch, `zip_download_url` when >1 success |
| GET | `/api/asset/{asset_id}` | "Retrieves and caches Roblox asset metadata" |
| GET | `/api/files/download/{filename}` | "…while preventing path traversal attacks"; `inline` |
| GET | `/api/files/zips/{filename}` | serve batch ZIP |
| GET | `/api/proxy/roblox-thumbnail-3d`, `/api/proxy/roblox-user-avatar-3d` | *"using backend ROBLOSECURITY cookie to bypass CORS"* |
| GET | `/api/proxy/roblox-3d-file` | rbxcdn.com proxy |
| GET | `/api/proxy/roblox-toolbox`, `/api/proxy/roblox-catalog` | Creator Store / Catalog search |
| GET | `/openapi.json`, `/docs`, `/redoc` | the contract this is derived from |

**Private-asset workflow: NOT PART OF THIS TOOL.** The Bulk Spoofer's request body is literally
`JSON.stringify({assets:e, is_free:s})`. No `place_id`, `universeId`, `is_private`, `type` or
`mode` is ever sent. The private-asset capability belongs to `/api/download/{asset_id}` and
`/api/scan/place/{place_id}`, which this UI does not expose. If you want that workflow, you need
the vendor's documented single-asset API — **not** this page.
