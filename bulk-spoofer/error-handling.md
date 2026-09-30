# Error Handling — every branch, as implemented

The error surface of this page is small but sloppy in ways that matter. This document lists
**all** user-visible strings and all `console.error` sites, grouped by stage, then flags the
defects you should not copy.

---

## 0. The shared `apiFetch` wrapper — read this first

Every `backend.blokmarket.store` call goes through one function (`../js/0vs148roxm~ft.js`,
module `4989`). Its behaviour is not what most developers expect:

```js
async function apiFetch(url, opts = {}) {
  let res, tok = localStorage.getItem("bmk_token");
  let headers = new Headers(opts.headers || {});
  tok && headers.set("Authorization", `Bearer ${tok}`);
  const send = () => fetch(url, { ...opts, headers, credentials: "include" });

  try { res = await send(); }
  catch (e) {                                  // ← network failure
    console.error(`[API Fetch] Connection failed to: ${url}`, e);
    return { ok: false, status: 0, json: async () => ({ success: false, message: "Connection failed" }) };
  }

  if (res.status === 401 && (localStorage.removeItem("bmk_token"),
                             "/login" !== window.location.pathname))
    try {
      (await fetch(refresh(), { method: "POST", credentials: "include" })).ok
        ? res = await send()                   // ← retry, SAME headers
        : window.location.href = "/login";
    } catch (e) { window.location.href = "/login"; }

  return res;
}
```

Three consequences:

1. **It never rejects on a network error.** It returns a *synthetic* response
   `{ ok:false, status:0 }`. So `try/catch` around an `apiFetch` call is dead code for
   connection failures — you must branch on `res.ok`. This is why the page shows a friendly
   "Failed to connect to the server…" toast instead of a crash.
2. **The 401 retry replays a dead token.** `headers` is built **once** and `send()` closes over
   it. The token is deleted from `localStorage` *before* the retry, but the retry re-sends the
   old `Authorization` value. It cannot succeed.
3. **The refresh endpoint is 404.** Verified live, both `GET` and `POST`. So point 2 never even
   runs — the `else` branch fires and the user is hard-redirected to `/login`.

> Net effect: **every session expiry is a logout.** There is no silent renewal. That is an
> availability bug, not a security hole — but do not copy it into your own app.

## 1. Engine calls do not go through `apiFetch`

`spoofer.blokmarket.store` is called with bare `fetch` and **no** `try/catch` around the
response body in every case. Two different error envelopes therefore reach the UI raw:

| Origin | Success | Failure |
|---|---|---|
| backend (Express) | `{"success":true, …}` | `{"success":false,"message":"…"}` |
| engine (FastAPI) | bare object, **no envelope** | `{"detail":"string"}` **or** `{"detail":[{…}]}` |

`detail` is polymorphic — a string for application errors, an array of Pydantic error objects
for validation. Any client you write must handle both.

---

## 2. By stage

### 2.1 Input validation (client-side, pre-network)

| Condition | Message | Network call? |
|---|---|---|
| parser returned 0 items | `Invalid input format! Please enter a LUA table or list of IDs.` | **no** |
| parsed > 500 | `Maximum of 500 IDs in a single bulk process!` | **no** |
| single-asset field empty or `NaN` | `Please enter a valid Asset ID.` | **no** |
| clipboard read denied | `Gagal membaca clipboard. Mohon tempel secara manual.` | no |
| IDs shorter than 9 digits | **silent** — no error, the item just vanishes | no |

The last row is the dangerous one: a user pasting 6-8 digit numbers gets a silently empty batch.

### 2.2 Cost pre-check

| Failure | Message | Code |
|---|---|---|
| network / non-`success` body | `t.message` → fallback `Failed to calculate coin cost.` | `console.error("Check cost error:",e)` |
| transport throw | `Failed to connect to the server to calculate coins.` | `console.error("Check cost error:",e)` |
| balance < cost | `Insufficient Coins (-{cost - coins})` rendered in the modal; the confirm button is replaced by one that opens the top-up modal | — |

### 2.3 Coin deduction

| Failure | Message |
|---|---|
| transport / `!success` | `Failed to deduct coins.` (or `t.message`) |
| logged | `console.error("Spoofer deduct error:",e)` |

> **Admin/owner short-circuit.** `if (role === "admin" || role === "owner")` skips the pre-check
> entirely, calls the deduct endpoint with `.catch(() => null)` — **ignoring the failure** — and
> submits anyway. So an admin can start a paid run with zero coins and no confirmation dialog.

### 2.4 Job submission

| Failure | Message |
|---|---|
| transport throw | `Failed to process bulk spoof!` |
| `!res.ok` | `Failed to connect to spoofer server!` |
| body not JSON / unexpected | `Failed to process assets. Make sure the ID is valid and the asset is public.` |
| all assets failed | `All downloads failed to process.` |

The submit handler wipes four `localStorage` keys (`bmk_spoofer_logs`, `bmk_spoofer_downloads`,
`bmk_spoofer_active_zip`, `bmk_spoofer_active_zip_count`) **before** the network call, so a
failed submit still destroys the previous run's history.

### 2.5 Polling

| Failure | Behaviour |
|---|---|
| HTTP `404` | `clearInterval` + `removeItem("bmk_spoofer_active_task")` — job abandoned silently |
| other non-OK | `console.error("Polling error:",e)`; interval keeps running forever |
| transport throw | `console.error("Error polling task status:",e)`; interval keeps running forever |
| `asset_type === "Place"` | `Failed: Place/Game bypass is currently unavailable.` |

**There is no poll backoff and no poll give-up.** A dead-but-200 endpoint means an interval
firing every 1.5 s indefinitely. Add a ceiling in your own implementation.

### 2.6 Result interpretation (not errors, but look like them)

| State | Message |
|---|---|
| ≥1 success | `Assets successfully spoofed!` |
| ZIP present | `Successfully downloaded N files! ZIP is ready.` |
| `Place` present | `Bypass feature for Place/Game is currently unavailable.` |
| nothing usable | `Asset might be private or ID is invalid.` |

### 2.7 Download

| Failure | Behaviour |
|---|---|
| `fetch` throws or `!res.ok` | `console.error("Force download failed, falling back to open in tab:",e)` then `<a target="_blank">` + click |
| QRIS PNG fetch | `Gagal mengunduh QRIS. Silakan simpan manual.` |

The fallback means a CORS-blocked or 500 ZIP silently becomes "opens a blank tab". There is no
user-visible error at all on that path.

### 2.8 Roblox upload — the only real retry logic

| Failure | Behaviour |
|---|---|
| `401` / `403`, or body error matching `401` / `invalid token` / `token` | **silent refresh** → retry that one asset |
| refresh succeeds | log `Session refreshed successfully. Retrying asset upload...` |
| refresh fails / throws | log `Session token expired and silent refresh failed. Aborting remaining uploads.` + toast `Roblox session expired and failed to renew. Upload aborted.`; every remaining asset → `upload_status:"failed"`, `upload_error:"Aborted"` |
| HTTP error | log `✗ Failed to upload "<name>" (HTTP Error: {status})`, increment failed counter, **continue** |
| no successful downloads to upload | `No successful downloads history to upload yet!` |
| Roblox not linked | `Please link your Roblox account first!` / `Upload Error: Roblox Account not linked.` |
| fatal | log `Fatal Error: Asset publication workflow failed. Please try again.` + toast `Connection error occurred while publishing assets!` |
| 0 successes | `Batch upload process failed.` |

The refresh is single-flight — one in-flight promise is memoised, so a burst of 401s causes one
refresh. It is reset to `null` after resolving so a later expiry can refresh again.

### 2.9 Payment

| Failure | Message |
|---|---|
| create-invoice transport | `Failed to connect to the payment server.` |
| create-invoice non-`success` | `An error occurred while processing payment` / `Payment system error` |
| capture non-`success` | `Payment system error` |
| PayPal SDK load | `Failed to load PayPal SDK` |
| QRIS PNG fetch | `Gagal mengunduh QRIS. Silakan simpan manual.` |
| `EXPIRED` / `CANCELED` | `Payment expired or canceled` |
| cash sound blocked by autoplay policy | `console.error("Audio play failed:",e)` — swallowed |

PayPal `onCancel` / `onError` / `"closed"` / `"destroyed"` are handled silently — **no message**.

### 2.10 Background / non-fatal (logged, never shown)

`Failed to load spoofer state:` · `Failed to re-sync spoofer state:` · `Failed to verify task on
backend:` · `Failed to save spoofer job to DB:` · `Failed to create initial spoofer job in DB:` ·
`Failed to update spoofer job upload status:` · `Failed to resume active spoofer task:` ·
`Failed to fetch groups:` · `Polling error:` · `Error polling task status:`

All of these are `console.error` only. **Audit rows can silently fail to persist** and the user
is never told.

---

## 3. Defects to avoid copying

| # | Defect | Fix in your version |
|---|---|---|
| 1 | `apiFetch` retry replays the deleted token | rebuild headers after refreshing |
| 2 | `/api/auth/refresh` is 404 — every expiry logs the user out | implement a real refresh/rotation |
| 3 | Network failure returns a fake `{ok:false}` instead of throwing | throw, and handle it once at the boundary |
| 4 | Poll has no backoff, no max attempts, no give-up | exponential backoff + ceiling + explicit "lost" state |
| 5 | A `404` on the very first poll after a fresh submit deletes the task and gives up | retry before declaring it gone |
| 6 | Submit wipes `localStorage` **before** the request succeeds | clear on success |
| 7 | Coins are spent at submit time; no refund path exists | refund on terminal failure, or reserve-then-commit |
| 8 | Admin/owner bypass swallows deduct failure (`.catch(() => null)`) | never ignore a money operation's error |
| 9 | Short IDs are silently dropped, producing a mysteriously empty batch | reject the batch with a per-line error report |
| 10 | Download failure degrades to opening a tab with no error shown | surface the HTTP status to the user |
| 11 | Engine `detail` is sometimes a string, sometimes an array | normalise both shapes |
| 12 | Background sync failures are console-only | tell the user, or retry with backoff |

---

## 4. Error-response catalogue (observed live)

Captured under `../api/responses/`.

| Status | Body | Origin |
|---|---|---|
| `400` | `{"detail":"Either 'asset_ids' or 'assets' must be provided."}` | engine |
| `401` | `{"success":false,"message":"No token"}` | backend — **only** `/api/auth/me` |
| `401` | `{"success":false,"message":"Unauthorized"}` | backend — 20+ other routes |
| `403` | — (root route guarded) | engine |
| `404` | `{"detail":"Task not found."}` | engine |
| `404` | `{"success":false,"message":"Endpoint not found"}` | backend — `/api/auth/refresh` |
| `422` | `{"detail":[{"type","loc","msg","input","ctx"}]}` | engine (Pydantic) |
| `500` | **NOT CONFIRMED** — never observed | both |

> `422` bodies echo the **submitted input** back in `detail[].input`. That can leak asset ids and
> custom names into logs. Worth knowing if you ever put a prompt-response pair in one of these
> fields.
