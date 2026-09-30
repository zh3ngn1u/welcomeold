# Feature Inventory — `/tools/bulk-spoofer`

Every row was **confirmed by reading the implementation** in `../js/0nh-y8e1a0l~a.js`
(124,311 B, the route's page chunk) plus `../js/0k1tyysfi6yay.js` (Roblox OAuth) and
`../js/0vs148roxm~ft.js` (API client, module `4989`). Rows marked **REFUTED** were probed and
found absent — they are listed so you don't build them.

Function names are the **minified** identifiers. No source maps were published, so the original
names are unrecoverable.

---

## A. Input & parsing

| # | Feature | Confirmed | Implementation |
|---|---|---|---|
| A1 | **Asset ID input** | ✅ | textarea state `eg`; page copy: *"Input assets LUA table or raw IDs queue to start bypass spoofer."* |
| A2 | **Multi-asset / bulk input** | ✅ | one textarea takes N IDs; max **500** per run |
| A3 | **LUA table parsing** | ✅ | `sQ` pass 1: `/\{([^{}]+)\}/g` per brace block |
| A4 | **Bare ID list parsing** | ✅ | `sQ` pass 2: `text.split("\n")` line-by-line fallback |
| A5 | **ID pattern is 9–18 digits** | ✅ | `/\d{9,18}/` — *not* `\d+`. Shorter numbers are silently ignored. |
| A6 | **Name extraction** (multi-strategy) | ✅ | `Name="x"` / `name='x'` → `"x",123` → first clean quoted string |
| A7 | **Default name** | ✅ | `` `Asset #${id}` `` when nothing parses |
| A8 | **Deduplication** | ✅ | `Set` of ids across both passes; first occurrence wins |
| A9 | **Clipboard auto-paste** | ✅ | `eL.length>10 && !eK && !eH` → `setTimeout(…, 800)` → `ab(eL)`; manual paste also errors with *"Gagal membaca clipboard. Mohon tempel secara manual."* |
| A10 | **Filename sanitiser** | ✅ | `(e)=>e.replace(/[\\/:*?"<>|]/g,"_").trim()` |

**REFUTED:** URL input (no URL field or URL parsing anywhere), file-picker input
(`type:"file"` absent from this chunk).

## B. Validation & gating

| # | Feature | Confirmed | Implementation |
|---|---|---|---|
| B1 | Empty-input guard | ✅ | `"Invalid input format! Please enter a LUA table or list of IDs."` |
| B2 | 500-ID cap | ✅ | `"Maximum of 500 IDs in a single bulk process!"` |
| B3 | Login gate | ✅ | whole UI gates on `userAtom` from `GET /api/auth/me` |
| B4 | Roblox-link gate | ✅ | `ep = !!(roblox_id && roblox_access_token)`; blocks the run |
| B5 | Turnstile gate | ✅ | `turnstileToken:"bypass_local"` required before Roblox OAuth |
| B6 | Cost pre-check | ✅ | `POST /api/auth/spoofer-check-cost {asset_ids}` → `cost`, `has_ugc` |
| B7 | Admin/owner cost bypass | ✅ | `if(role==="admin" \|\| role==="owner")` skips the pre-check, fires the deduct and ignores its failure |
| B8 | Tutorial/log gate (copy only) | ✅ | UI text: *"Execution Logs before spoofing to avoid issues such as cookie failure or upload errors."* — **no code enforces it** |
| B9 | Logout warning (copy only) | ✅ | *"Jangan pernah melakukan logout dari akun Roblox di browser selama proses spoofing"* — no code enforcement |

**REFUTED:** client-side Roblox-permission checks, asset-type validation, existence checks.

## C. Job submission

| # | Feature | Confirmed | Implementation |
|---|---|---|---|
| C1 | **Start / submit** | ✅ | `s2` → validate → `s5(assets)` |
| C2 | Free-spoof mode | ✅ | `is_free` boolean; button label flips to `"Free Spoof"` |
| C3 | Coin-paid mode | ✅ | `s4` → `POST /api/auth/spoofer-deduct {asset_count, asset_ids}` |
| C4 | **Job creation on the engine** | ✅ | `POST https://spoofer.blokmarket.store/api/download/batch/async` → `{task_id}` |
| C5 | **Audit-job record** | ✅ | non-free only: `POST /api/spoofer-jobs {job_id,status:"pending",…}` |
| C6 | Resume-after-reload | ✅ | `localStorage.bmk_spoofer_active_task = {task_id, parsedAssets, isSingle, batchId, startedAt}` |
| C7 | Optional `.ROBLOSECURITY` header | ✅ | password input → `localStorage.bmk_spoofer_user_cookie`; sent as `X-Roblox-Cookie` **only when `!is_free`** |
| C8 | **Single-asset "Free Spoof" panel** | ✅ | a *second, separate* form: `Asset ID (example: 124503154363488)` (digits stripped via `replace(/\D/g,"")`) + `Custom name (optional)` (default `` `Asset_${id}` ``). `s8` → `s5([{id, custom_name}], !0)` — **hardcoded `is_free:true`**, so it can never spend coins or send `X-Roblox-Cookie`. Guard: empty/`NaN` → `"Please enter a valid Asset ID."`. Reuses the same poll loop and shows `Waiting Queue (n/total)` |

## D. Progress, queue, status

| # | Feature | Confirmed | Implementation |
|---|---|---|---|
| D1 | **Polling** | ✅ | `setInterval(n, 1500)` in `s1`; single global ref `sS.current` |
| D2 | **Queue position** | ✅ | `queue_position` + `total_queue` → *"Waiting Queue (n/total)"* / *"Queue #n of t"* |
| D3 | Per-asset progress rows | ✅ | `{id, custom_name, status, progress, batchId}`; `status:"loading"`, `progress:20` initially |
| D4 | Live execution log | ✅ | `bmk_spoofer_logs`; timestamp `HH:MM:SS.mmm` + `{timestamp,type,text}` |
| D5 | Type-filtered per-asset log | ✅ | `"[Audio] "` prefix from `asset_type` |
| D6 | Refocus re-check | ✅ | `document.visibilitychange` + `focus` → one status read, queue only |
| D7 | Progress counters | ✅ | `{total, success, failed}` accumulated in `ev` |
| D8 | Stale-task recovery | ✅ | HTTP **404** → `clearInterval`, drop `bmk_spoofer_active_task` |
| D9 | Asset-type breakdown | ✅ | `asset_breakdown[type] = {success, failed}` for the PATCH |

**REFUTED:** user-initiated **cancel** (all `cancel`/`Batal`/`Abort` hits are PayPal `onCancel`,
payment `EXPIRED/CANCELED`, a *modal close button*, and the upload loop aborting on an expired
Roblox session — none is a user cancel of a running job), **abort/AbortController**,
per-asset retry of the spoof job, WebSocket/SSE, progress percentage from the server
(the `progress:20` value is a hardcoded client constant).

## E. Results

| # | Feature | Confirmed | Implementation |
|---|---|---|---|
| E1 | Per-asset result table | ✅ | status / file_name / file_size / asset_type / uploaded_asset_id / error |
| E2 | **"New Spoofed ID"** column | ✅ | renders `uploaded_asset_id`; label *"New Spoofed ID"* |
| E3 | ZIP result | ✅ | `zip_download_url` from the status response → stored in `bmk_spoofer_active_zip` + `_count` |
| E4 | Success toast | ✅ | *"Assets successfully spoofed!"* / *"Successfully downloaded N files! ZIP is ready."* |
| E5 | Place/Game rejection | ✅ | `asset_type === "Place"` → *"Bypass feature for Place/Game is currently unavailable."* |
| E6 | Generic failure | ✅ | *"Asset might be private or ID is invalid."* |
| E7 | "Failed Spoof" filter | ✅ | `.filter(e=>"failed"===e.status)` count badge |
| E8 | Comparison modal | ✅ | `window.dispatchEvent(new CustomEvent("open-spoofer-comparison"))`; loads `/bandingkan.png` |
| E9 | Per-asset force download | ✅ | `s0(asset)` → `{name}{ext}` from `metadata.name \|\| custom_name` + extension of `file_name` |
| E10 | History deep-link | ✅ | `/tools/history?tab=spoofer` |
| E11 | Clear logs / reset | ✅ | `eq([])` + `localStorage.removeItem("bmk_spoofer_logs")` |
| E12 | Result persistence | ✅ | `localStorage.bmk_spoofer_downloads` |

**ZIP generation is SERVER-SIDE.** `JSZip`, `generateAsync`, `.file(`, `folder(` → **0 hits** in
this chunk. The engine's spec states it *"generat[es] a ZIP package if successful downloads > 1"*.
An earlier note of mine calling this "JSZip packaging" was wrong and is corrected in
`../architecture.md` and `../findings.md`.

## F. Download

| # | Feature | Confirmed | Implementation |
|---|---|---|---|
| F1 | **Blob download** | ✅ | `sZ(url, name)`: `fetch(url)` → `res.blob()` → `URL.createObjectURL` → temp `<a download>` → click → `revokeObjectURL` |
| F2 | **Fallback** | ✅ | on failure: `a.href=url; a.target="_blank"; a.click()` — opens in a tab |
| F3 | Per-asset file download | ✅ | same `sZ` with the `s0()` filename |
| F4 | ZIP download | ✅ | same `sZ` with `zip_download_url` |
| F5 | QRIS PNG download | ✅ | `api.qrserver.com` → `.blob()` → `BLOKMARKET-QRIS-{totalTransfer}.png` |

## G. Roblox upload (optional second stage)

| # | Feature | Confirmed | Implementation |
|---|---|---|---|
| G1 | Target creator picker | ✅ | radio `is_group`; `creator_type = roblox_id ? "Group" : "User"` |
| G2 | **Batch upload to Roblox** | ✅ | `POST engine /api/upload/batch`, **one asset per request, strictly serial** |
| G3 | Per-asset upload status | ✅ | `upload_status`, `upload_error`; success ⇒ `uploaded_asset_id` set |
| G4 | **Silent token refresh + retry** | ✅ | on `401`/`403`/"invalid token": `POST /api/auth/roblox/refresh {from:"spoofer"}` → `robloxAccessToken` → update `userAtom` → **retry that one asset**; log *"Session refreshed successfully. Retrying asset upload..."* |
| G5 | Dead-token abort | ✅ | refresh failure ⇒ *"Upload aborted."*, remaining assets marked `upload_status:"failed"`, `upload_error:"Aborted"` |
| G6 | Completion summary | ✅ | *"Upload process completed. Success: N, Failed: M"* |
| G7 | Job-record sync | ✅ | `sX` → `PATCH /api/spoofer-jobs/:id {status, files, logs.slice(-500)}` |

## H. Coins & payment

| # | Feature | Confirmed | Implementation |
|---|---|---|---|
| H1 | Coin balance display | ✅ | `GET /api/auth/spoofer-state` → `data.coins` + `bmk_accent_secondary_v3` colour |
| H2 | Balance reconcile after job | ✅ | `POST /api/auth/spoofer-state {task_id}` |
| H3 | Coin top-up — QRIS | ✅ | `POST /api/payment/create-coin-invoice {coins, paymentMethod:"qris"}` |
| H4 | Coin top-up — PayPal | ✅ | `paypal/create-coin-order {coins}` → `onApprove` → `paypal/capture-coin-order {paypalOrderId, orderId, coins}` |
| H5 | **QRIS payment polling** | ✅ | `setInterval(…, 3000)` → `GET /api/payment/check/:trxId`; only when method is `qris` **and** `trxId` **and** `qrString` |
| H6 | **Auto-start after payment** | ✅ | on `status==="SUCCESS"` and *not* a coin top-up: *"Payment verified! Processing Bulk Spoofer..."* → re-parses the textarea → `s5(assets)` |
| H7 | Payment terminal states | ✅ | `SUCCESS` → cash sound `/audio/cashsound.mp3`, close, update coins, re-sync; `EXPIRED`/`CANCELED` → `clearInterval` + *"Payment expired or canceled"* |
| H8 | Spoof cost is **server-authoritative** | ✅ | no client-side tier table exists. `POST /api/auth/spoofer-check-cost {asset_ids}` → `cost`, stored in state and rendered verbatim as `"🪙 {cost} Coins"`. The only client-side number is the `useState(15)` default that exists *before* the response lands. `has_ugc` appends *"(UGC Asset Detected)"*. Balance gate: `coins >= cost` → `"Start Spoof"`; else `"Insufficient Coins (-{cost-coins})"` and the button opens the top-up modal |
| H9 | Coin **top-up** tiers (the hardcoded ones) | ✅ | `60 → Rp 50.000` · `150 → Rp 100.000 (popular)` · `350 → Rp 200.000`, with `/coins60.png`, `/coins150.png`, `/coins350.png` imagery. Confirm id `60 === coins ? 5e4 : 150 === coins ? 1e5 : 2e5` |

## I. Account / Roblox linking

| # | Feature | Confirmed | Implementation |
|---|---|---|---|
| I1 | Roblox OAuth popup | ✅ | `GET /api/auth/roblox/login?cf_token&token&from=spoofer&t`; `postMessage` → `localStorage.bmk_token` |
| I2 | Open Cloud key modal | ✅ | `POST /api/auth/roblox/save-api-key {apiKey, creatorId, creatorType, from:"spoofer"}` |
| I3 | Unlink Roblox | ✅ | `POST /api/auth/roblox/unlink {from:"spoofer"}` then `?refresh=<ts>` reload |
| I4 | Group picker | ✅ | `GET /api/auth/roblox/groups` |
| I5 | Tutorial video | ✅ | `window.open("https://youtu.be/Ermk2raFzLo","_blank")` |
| I6 | Help image | ✅ | `https://i.ibb.co.com/xtby0WnJ/secur.png` |

## J. Refuted / not present

| Feature | Status | Evidence |
|---|---|---|
| User cancel of a running job | **ABSENT** | no API, no handler; all `cancel` hits are PayPal/modal/session-abort |
| Retry a failed spoof job | **ABSENT** | the only `retry` is the Roblox *token* refresh in the upload stage |
| Private-asset / placeId mode | **ABSENT from the frontend** | body is literally `{assets, is_free}`; no `place_id`/`universeId`/`private` sent |
| Client-side ZIP building | **ABSENT** | 0 hits for `JSZip`/`generateAsync`/`.file(`/`folder(` |
| WebSocket / SSE / EventSource | **ABSENT** | 0 hits in all 34 chunks |
| `sendBeacon` | **ABSENT** | 0 hits |
| `sessionStorage` | **ABSENT** | 0 hits |
| Cookie reads for auth | **ABSENT** | 0 `document.cookie` in this chunk |
| Server-driven progress % | **ABSENT** | `progress:20` is a hardcoded literal |
| `Axios` / `XMLHttpRequest` in app code | **ABSENT** | `XMLHttpRequest` appears only in the core-js polyfill chunk |
