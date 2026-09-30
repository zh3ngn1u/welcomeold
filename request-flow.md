# Request Flow — `/tools/bulk-spoofer`

All logic below is **RETRIEVED SOURCE** from `js/0nh-y8e1a0l~a.js` unless marked DERIVED.
Minified identifiers are preserved where useful; the original variable names are not recoverable
(no source maps).

## What the tool does, per its own UI copy

Input is a **LUA table or a raw list of Roblox asset IDs**. Each ID is submitted to a
third service which returns a file plus a **"New Spoofed ID"** (`uploaded_asset_id`), which can
then be **uploaded into the user's own Roblox experience** using their `roblox_access_token`.

Client-side copy confirming intent (verbatim):
- `"Input assets LUA table or raw IDs queue to start bypass spoofer."`
- `"Engine spoofer kami telah memproses validasi bypass id spoof sangat baik"` (id spoof bypass)
- `"Aset tersebut terbukti mustahil untuk di spoof"` (asset is impossible to spoof)
- `"New Spoofed ID"` / `uploaded_asset_id`
- `"Jangan pernah melakukan logout dari akun Roblox di browser selama proses spoofing"`
- Tutorial gate: `"Execution Logs" before spoofing to avoid issues such as cookie failure or upload errors.`

---

## Step 0 — Auth gate

On mount the page issues `GET /api/auth/me` via `apiFetch`. Signed-in state additionally
requires a linked Roblox account:

```js
ec?.spoofer_state?.roblox
ep = !!(ex?.roblox_id && ex?.roblox_access_token)
```

If absent, the page renders the Roblox connect button and blocks the run. The connect button
(`0k1tyysfi6yay.js`) requires a Cloudflare Turnstile token first:

```js
if(!g) return void f("Please complete the security verification first.");
window.open(`${apiEndpoints.auth.robloxLogin()}?cf_token=${g}&token=${a}&from=spoofer&t=${Date.now()}`,
             "robloxLogin", "width=500,height=650,...")
```

Success arrives via `window.postMessage` from the popup; `e.data.token` is written to
`localStorage.bmk_token`.

## Step 1 — Parse + client-side validation

Input is parsed by a function that accepts a LUA table or a bare ID list, producing
`{id, custom_name}` objects. Two hard client-side limits:

```js
if(0===e.length) return toast.error("Invalid input format! ...");
if(e.length>500) return toast.error("Maximum of 500 IDs in a single bulk process!");
```

Sanitisation of `custom_name` for filenames:
```js
a = a.replace(/[\\/:*?"<>|]/g,"_").trim()
```

## Step 2 — Cost pre-check

```js
POST /api/auth/spoofer-check-cost        // via buildApiUrl(), NOT in the endpoint map
{ asset_ids: string[] }
→ { success, cost, has_ugc }
```

`has_ugc` drives the per-asset cost tier shown in the modal. Role bypass for staff:

```js
if(ec?.role==="admin" || ec?.role==="owner"){ /* deduct, but ignore failure */ }
```

## Step 3 — Deduct coins

```js
POST /api/auth/spoofer-deduct
{ asset_count: n, asset_ids: string[] }
```

Coins are also purchasable: `POST /api/payment/create-coin-invoice` +
`/api/payment/paypal/create-coin-order` + `/api/payment/paypal/capture-coin-order`.

## Step 4 — Submit to the spoofing engine

```js
let n = await fetch(`${ea}/api/download/batch/async`, {
  method:"POST",
  headers:r,                                   // {"Content-Type":"application/json"}
  body: JSON.stringify({ assets:e, is_free:s })
});
let { task_id } = await n.json();
```

- `ea` = `https://spoofer.blokmarket.store` (trailing slash stripped)
- **No** `Authorization` header — raw `fetch`, not `apiFetch`
- Optional header `X-Roblox-Cookie: <user .ROBLOSECURITY value>` is added when
  `!is_free` and a cookie was pasted; it is read from `localStorage.bmk_spoofer_user_cookie`
- `is_free` = single-asset mode flag (`s`/`isSingle`)
- On `!res.ok` the engine's `detail` field becomes the toast message
- Task persisted to `localStorage.bmk_spoofer_active_task` for resume-after-reload

Non-free runs immediately record a job: `POST /api/spoofer-jobs`.

## Step 5 — Poll task status (1.5 s interval)

```js
fetch(`${ea}/api/task/${taskId}/status`)
→ { status, queue_position, total_queue, assets:[ … ] }
```

Per-asset fields consumed client-side: `id`, `status` (`processing`/`success`/`failed`),
`real_name`, `custom_name`, `asset_type`, `file_name`, `file_size`, `uploaded_asset_id`,
`error`.

- Queue position is also refreshed on `visibilitychange` / window `focus` for a stuck page
- HTTP `404` → task gone; clear interval, drop `bmk_spoofer_active_task`
- On terminal state → `PATCH /api/spoofer-jobs/:id` with
  `{status, total_assets, success_count, failed_count, …}` and per-asset rows
  `{id, custom_name, status, file_name, file_size, asset_type, uploaded_asset_id, …}`
- Then `POST /api/auth/spoofer-state {task_id}` to reconcile the coin balance
- Events `bypass_completed` / `bypass_failed` are written to the activity log

### Success handling
- If the first asset is `asset_type === "Place"` →
  `"Bypass feature for Place/Game is currently unavailable."`
- Otherwise if `zip_download_url` present → stored to `bmk_spoofer_active_zip` and offered as a ZIP
- UI label per asset: `"New Spoofed ID"` = `uploaded_asset_id`

## Step 6 — Optional upload into the user's Roblox experience

```js
POST https://spoofer.blokmarket.store/api/upload/batch
{
  files: [ <one asset> ],       // one HTTP request per asset, sequentially
  roblox_access_token: ex.roblox_access_token,
  creator_id: ex.roblox_id,
  creator_type: ex.roblox_id ? "Group" : "User"
}
→ { results: [ { success, error } ] }
```

Loop: `for(; t<a.length && !e; )` — strictly serial, aborts on first unrecoverable failure.
`401`/`403` or an error containing `401` / `"invalid token"` is treated as a dead token
and reported to the user. Per-asset result is written to
`bmk_spoofer_downloads` with `upload_status` / `upload_error`.

## Step 7 — Thumbnail rendering
`GET https://spoofer.blokmarket.store/api/proxy/roblox-thumbnail?assetIds=<id>&size=150x150&format=Png&isCircular=false`
→ `data[0].imageUrl`, memoised per asset id via `react.memo`.

---

## Full sequence diagram (DERIVED from retrieved call sites)

```
Browser                     backend.blokmarket.store        spoofer.blokmarket.store
  |                                |                                 |
  |-- GET  /api/auth/me ----------->|                                 |
  |                                |                                 |
  |  [submit] POST /auth/spoofer-check-cost {asset_ids} -------------->|
  |                        |       |                                 |
  |  [pay]  POST /auth/spoofer-deduct {asset_count, asset_ids} ------>|
  |                        |       |                                 |
  |-- POST /api/download/batch/async  {assets, is_free, X-Roblox-Cookie}|
  |------------------------------>|  (NO auth header)  ------------->|
  |<--------------- {task_id} ----------------------------------------|
  |                                |                                 |
  |-- GET  /api/task/:id/status  (every 1500ms, no auth header) ------>|
  |<-- {status, queue_position, total_queue, assets[]} ---------------|
  |                                |                                 |
  |-- PATCH /api/spoofer-jobs/:id ------------------------------------>|
  |-- POST /api/auth/spoofer-state {task_id} ------------------------>|
  |                                |                                 |
  |  [upload] POST /api/upload/batch {files, roblox_access_token, --- >|
  |            creator_id, creator_type}      (no auth header) -------|
  |<-- {results:[{success, error}]} ----------------------------------|
```

## Request headers actually sent (RETRIEVED)

| Header | Where | Value |
|---|---|---|
| `Authorization` | `apiFetch` only | `Bearer ${localStorage.bmk_token}` |
| `Content-Type` | JSON POSTs | `application/json` |
| `X-Roblox-Cookie` | engine submit only, `!is_free` | user-supplied `.ROBLOSECURITY` |
| *(none)* | all `spoofer.*` calls | plain `fetch`, no credentials mode |
| *(implicit)* | every `apiFetch` | `credentials: "include"` |

## Retry / concurrency behaviour
No retry logic, no backoff, no request cancellation. One global `setInterval` ref (`sS.current`)
guards a single active task; a new submission clears the previous interval. The page can hold
exactly one in-flight spoofer task, rehydrated from `localStorage` on load.
