# Bulk Processing — limits, concurrency, queueing, progress

Everything on this page was read out of `../js/0nh-y8e1a0l~a.js`. Where the vendor does not
implement something, this document says so rather than filling the gap with a guess.

---

## 1. Limits

| Limit | Value | Enforced | Evidence |
|---|---|---|---|
| Max IDs per run | **500** | ✅ client-side, **before any request** | `if(e.length>500) return toast.error("Maximum of 500 IDs in a single bulk process!")` |
| Min ID length | **9 digits** | ✅ silently dropped | `/\d{9,18}/` — a 6- or 8-digit number is *not* an error, it just never appears in the parsed list |
| Max ID length | **18 digits** | ✅ silently dropped | same regex |
| ID field | textarea state `eg` | — | one field carries N IDs; there is no second batch slot |
| Concurrent runs | **1** | ✅ | `sS.current` is a single `useRef`; a new submit does `sS.current && (clearInterval(sS.current), sS.current=null)` |

**The 500 cap is a client-side `if`, not a server contract.** Nothing in the engine's OpenAPI
document states a maximum. If you re-implement, enforce it server-side too — a client-only cap is
one removed line away from being bypassed.

## 2. Request structure — array, never individual

IDs are **always sent as one array in one request**. There is no per-ID HTTP call and no
client-side chunking of the 500.

```js
// validation → pre-check
JSON.stringify({ asset_ids: e.map(e => e.id) })      // strings, id only

// submission
JSON.stringify({ assets: [{id, custom_name}, …], is_free: bool })
```

| Field | Type | Notes |
|---|---|---|
| `asset_ids[]` | `string[]` | pre-check and deduct only — ids, no names |
| `assets[]` | `{id, custom_name}[]` | the engine call; carries the parsed display name |
| `is_free` | `boolean` | **`true` omits the `X-Roblox-Cookie` header** |

Note the two calls use *different* payload shapes for the same data. `spoofer-check-cost` and
`spoofer-deduct` take a flat `asset_ids` array; the engine takes `assets[]` of objects.

## 3. Queue behaviour — the engine owns it, the browser only reads

There is **no client-side job queue**. The browser fires one `POST` and immediately starts
polling; all queueing happens server-side.

```
POST /api/download/batch/async   →  { task_id }
setInterval(poll, 1500)          →  GET /api/task/{id}/status
```

| Behaviour | Confirmed detail |
|---|---|
| Poll interval | **`1500 ms`**, fixed — `sS.current=setInterval(n,1500),n()` (fires immediately once, then every 1.5 s) |
| Poll transport | plain `fetch`, no auth header, no `credentials` |
| Backoff | **none** — constant rate, even when idle in a queue |
| Visibility re-check | `document.visibilitychange` + `window.focus` fire **one** immediate status read; they do not restart or reschedule the interval |
| Queue read | `queue_position` + `total_queue` → `"Waiting Queue (n/total)"` / `"Queue #n of t"` |
| Stale task | HTTP `404` → `clearInterval` **and** `localStorage.removeItem("bmk_spoofer_active_task")` — treated as gone, not retried |
| Network error mid-poll | `console.error("Error polling task status:",e)` and **the interval keeps running** |
| Terminal detection | the interval is cleared when the status read yields no `zip_download_url` and no `asset_type === "Place"` |

## 4. Progress calculation

**There is no percentage.** The only progress value in the entire feature is a hardcoded literal.

```js
let r = e.map(e => ({ id: e.id, custom_name: e.custom_name,
                      status: "loading", batchId: i, progress: 20 }));
```

`progress: 20` is a constant written once at submit time and never updated. Real progress is
communicated by three things instead:

| Signal | Source | Rendering |
|---|---|---|
| per-asset `status` | `assets[].status` from the poll — `processing` → `success` \| `failed` | row state machine |
| `{total, success, failed}` | accumulated in the poll reducer as each asset flips | counters + a "Failed Spoof" badge |
| text log | `localStorage.bmk_spoofer_logs` | `HH:MM:SS.mmm` + `{timestamp, type, text}`, `type` filtered by `[Audio] ` style prefix from `asset_type` |

## 5. Concurrency

| Stage | Concurrency | Notes |
|---|---|---|
| Asset parsing | 1 (synchronous) | `Set` dedupe across two passes, first occurrence wins |
| Job submission | 1 request for N assets | never N requests |
| Status polling | 1 request / 1500 ms | single interval, single task |
| **Roblox upload** | **1 request / asset, strictly serial** | see below |
| QRIS payment poll | 1 request / 3000 ms | `setInterval(async()=>{…},3e3)`, cleared on `SUCCESS`/`EXPIRED`/`CANCELED` |

### The upload loop is genuinely serial

The upload stage calls an engine endpoint that accepts an **array** (`files[]`) but the frontend
sends exactly **one** element per request and awaits each before starting the next:

```js
x = async (e, s) => await fetch(`${ENGINE}/api/upload/batch`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ files: [e], roblox_access_token: s, creator_id: i, creator_type: r })
})
```

with a hand-rolled indexed cursor and an abort flag:

```js
for (; t < a.length && !e; ) {
  let r = t++;
  if (r >= a.length || e) break;
  … await x(n, token) …          // one asset
}
```

So a 500-asset run that all succeed produces **500 sequential HTTP round-trips** to the engine.
This is almost certainly to dodge Roblox rate limiting rather than a deliberate design choice,
but it is what the code does — match it, or deliberately parallelise and accept the risk.

## 6. Partial failures

Partial failure is a **first-class, expected** outcome, not an error path.

| Aspect | Behaviour |
|---|---|
| Per-asset failure | `assets[].status === "failed"`, optional `assets[].error` string. Other assets keep going. |
| Success vs failure accounting | `success_count` / `failed_count` incremented independently |
| `asset_breakdown` | `{ "<AssetType>": { success: n, failed: m } }`, keyed by the `asset_type` the engine returned |
| Terminal job status | `completed` · `partial` · `bypass_completed` · `bypass_failed` · `failed` |
| ZIP | still produced when **more than one** asset succeeded — partial runs still yield a ZIP |
| UI | a "Failed Spoof" filter badge counts `status === "failed"` rows |
| No-success case | no `zip_download_url` and no `Place` type → `"Asset might be private or ID is invalid."` |
| Place assets | `asset_type === "Place"` → hard stop: `"Bypass feature for Place/Game is currently unavailable."` |
| Coins | spent at **submit** time, before any asset succeeds. A 500-ID batch where all 500 fail still cost the full amount. There is no refund call anywhere in the bundle. |

**Not implemented:** there is no retry of a failed *spoof*. No cancel. No resume of a partial run.
The only `retry` in the codebase re-sends an **upload** after a Roblox token refresh.

## 7. Retry behaviour

| Retry | Exists? | Trigger | Scope |
|---|---|---|---|
| Roblox **upload** | ✅ | `401` / `403`, or a body error containing `"401"` / `"invalid token"` / `"token"` | that single asset, once per refresh |
| Roblox **upload** abort | ✅ | the refresh itself fails | every remaining asset → `upload_status:"failed"`, `upload_error:"Aborted"` |
| Spoof **job** | ❌ | — | — |
| Poll after network error | ❌ (keeps polling, never re-submits) | — | — |

The refresh is **single-flight** — a memoised promise, so N parallel 401s trigger exactly one
refresh rather than a stampede:

```js
i || (i = (async () => { …refresh…; return o = e, i = null, e })());
try { const e = await i; return await m(e); }   // re-attempt the SAME asset with the new token
```

Once it resolves, `i` is reset to `null` so a later expiry can refresh again.

## 8. Resume after reload

```
localStorage.bmk_spoofer_active_task = { task_id, parsedAssets, isSingle, batchId, startedAt }
```

On mount the page reads that key and immediately re-enters the poll loop. This is the *only*
recovery mechanism — there is no server-side "my running jobs" list, no job index, no
reconciliation. Consequences:

* Clear storage, switch browser, or switch device → the job is **orphaned**; it keeps running on
  the engine but the page will never find it again.
* Because `sS.current` is a single slot, starting a second job **abandons the first**.
* The stored `parsedAssets` is the client's own parse, not the engine's — so a resumed run
  re-renders from the client's memory, not from server truth.

## 9. What the engine declares but the queue never uses

For completeness, from the engine OpenAPI spec — **not** reachable from this page:

| Endpoint | Relevance to bulk |
|---|---|
| `POST /api/download/batch` | the **synchronous** sibling. Returns `zip_download_url` when >1 success. The page only ever calls the `async` variant. |
| `GET /api/scan/place/{place_id}` | scans a Place for Audio/Animation/Emote references, `page=1`/`limit=30`. The frontend has no caller — this is how a *Place*-based private-asset workflow would be driven. |
| `GET /api/download/{asset_id}` | single-asset path. **This is the only endpoint carrying `place_id`**, documented as *"Optional custom Place ID to spoof for private assets"*. |

> **Private assets are not a mode of this tool.** The submitted body is literally
> `{assets, is_free}` — no `place_id`, `universeId`, `is_private`, `type` or `mode` is ever sent.
> Use the vendor's documented single-asset API for that; do not bolt it onto this page.
