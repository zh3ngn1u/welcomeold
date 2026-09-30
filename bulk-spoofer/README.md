# Bulk Spoofer — functional reverse-engineering

Everything here was derived from the **downloaded production bundles** under `../js/` and
`../raw/`, the **published OpenAPI spec** at `../api/spoofer-engine-openapi.json`, and
**live unauthenticated responses** captured under `../api/responses/`.

No source maps were published, so original function names are unrecoverable. Names like
`sQ`, `s5`, `s1` are the **minified** identifiers from the bundle. Where something could not
be confirmed it says **NOT CONFIRMED** — it is never guessed.

**No credentials were obtained or used.** No account was authenticated. No successful paid
run was executed. Every `[read]` claim is read out of the implementation; every `[seen]` claim
is backed by a file in `../api/responses/`.

---

## Target

`https://customer.blokmarket.store/tools/bulk-spoofer` — page chunk
`../js/0nh-y8e1a0l~a.js` (124,311 B). The page calls **three origins**: the dashboard
backend, a separate spoofer engine, and third parties (PayPal SDK, QR image service).

---

## Read in this order

| File | What it answers |
|---|---|
| **`features.md`** | every feature, with `REFUTED` rows so you don't build what isn't there |
| **`workflow.md`** | the five implemented workflows, start to finish |
| **`bulk-flow.md`** | limits, concurrency, queueing, progress, retry — §8 of the spec |
| **`endpoints.md`** | all 29 endpoints across 3 origins, incl. the ones never called |
| **`requests.md`** | exact request bodies, copied verbatim from the call sites |
| **`responses.md`** | both response envelopes, and every observed status code |
| **`authentication.md`** | 4 credential families; what is browser-side vs server-side |
| **`download-flow.md`** | how a file actually reaches the disk |
| **`error-handling.md`** | every error branch, plus 12 defects not to copy |
| **`my-web-architecture.md`** | how to rebuild this without leaking your users' credentials |
| `client/` | a working reference client in JS + Python + curl |

---

## The shortest useful summary

```
INPUT      textarea — LUA table or bare IDs
   │       parser: /\d{9,18}/, dedupe, name extraction, default "Asset #<id>"
   ▼
VALIDATE   0 items → "Invalid input format!"
           >500     → "Maximum of 500 IDs in a single bulk process!"
   ▼
COST       POST /api/auth/spoofer-check-cost  {asset_ids}   → cost, has_ugc
           │                                     (server-authoritative)
           ├─ free  → is_free:true
           └─ paid  → POST /api/auth/spoofer-deduct  ← money moves HERE
   ▼
SUBMIT     POST https://spoofer.blokmarket.store/api/download/batch/async
           {assets:[{id,custom_name}], is_free}     ← { task_id }
   ▼
POLL       every 1500 ms → GET /api/task/:id/status
           queue_position / total_queue → "Waiting Queue (n/total)"
           per-asset: processing → success | failed
   ▼
TERMINAL   zip_download_url → "ZIP is ready"
           asset_type==="Place" → "Bypass feature for Place/Game is currently unavailable."
           neither             → "Asset might be private or ID is invalid."
   ▼
DOWNLOAD   fetch(url) → blob → object URL → <a download>
           ZIP is built SERVER-SIDE by the engine
   ▼
UPLOAD     optional, to the user's own Roblox experience:
           POST engine /api/upload/batch — ONE asset per request, strictly serial
```

---

## Two origins, two incompatible envelopes

This is the number one thing to get right.

| | Backend | Engine |
|---|---|---|
| Host | `backend.blokmarket.store` | `spoofer.blokmarket.store` |
| Stack | Express-style | FastAPI 3.1 |
| Auth | `Authorization: Bearer <bmk_token>` | **none** |
| Success | `{"success":true, …}` | **bare object, no envelope** |
| Failure | `{"success":false,"message":"…"}` | `{"detail":"…"}` |
| Errors | `401` · `404` | `400` · `403` · `404` · `422` |

And the trap: **`detail` is sometimes a string and sometimes an array** of Pydantic objects.
And some backend routes put their payload at the **top level** rather than under `data`
(`/api/audio/approved-count` returns `{"success":true,"count":32959}`).

---

## Things that will waste your time if you assume otherwise

* **The cost is server-side.** There is no client-side tier table. The hardcoded numbers
  `60 / 150 / 350` are the **top-up** coin packages (Rp 50.000 / 100.000 / 200.000), not the
  per-run cost. *(An earlier draft of `features.md` claimed a `0/15/30/50` spoof-cost tier
  table. It does not exist — corrected in place.)*
* **IDs must be 9–18 digits.** `\d{9,18}`, not `\d+`. A 6-digit number is **silently dropped** —
  no error, the batch just shrinks.
* **ZIP is server-side.** `JSZip` / `generateAsync` / `.file(` / `folder(` → **0 hits** in the
  page chunk.
* **There is no cancel and no retry of a failed job.** The only `retry` in the codebase
  re-sends a *Roblox upload* after a token refresh.
* **The upload is serial.** One asset per request → 500 assets is 500 sequential round-trips.
* **There is no percentage.** `progress: 20` is a literal written once at submit.
* **Only one job at a time.** A single `useRef` interval; a new submission abandons the old.
* **Free runs write no audit row.** `POST /api/spoofer-jobs` is paid-runs-only, so free usage
  is invisible server-side.
* **Private assets are not a mode of this tool.** The body is literally `{assets, is_free}`.
  No `place_id` / `universeId` / `is_private` is ever sent.

---

## Using the reference client

```bash
cd client

export BMK_TOKEN="…"        # dashboard bearer      (server-side only)
export ROBLOX_COOKIE="…"     # .ROBLOSECURITY        (optional, paid runs only)
export ROBLOX_TOKEN="…"      # Roblox OAuth token    (upload stage only)

node -e '
const c = require("./javascript.js");
c.runFreeSpoof("1846853302\n1846853303", { onUpdate: (s) => console.log(s.status) })
 .then(r => console.log(r.outcome));
'
```

```python
import python as c
r = c.run_free_spoof("1846853302\n1846853303")
print(r["outcome"])
```

The parser in both clients was verified to produce **byte-identical output to the upstream
implementation** across 12 input shapes — LUA tables, quoted-pair form, bracketed keys,
`asset_id =` assignments, `rbxassetid://` URLs, sub-9-digit noise, and duplicates.

See `client/curl.md` for every request as a copy-pasteable command.

---

## Confidence legend

| Mark | Meaning |
|---|---|
| ✅ seen | response captured live in `../api/responses/` |
| 📦 declared | present in the `apiEndpoints` map or the engine's OpenAPI spec; no live response |
| 🔒 spec | published in the OpenAPI spec only |
| NOT CONFIRMED | searched for and **not** found — stated as absent, not guessed |
| REFUTED | probed for, looked plausible, and **is not there** |

---

## Boundaries respected

* No authentication, rate limit, or access control was bypassed.
* No credentials, cookies, or tokens were obtained or printed.
* No successful paid or authenticated run was executed.
* Roblox permissions were not circumvented — the upload stage is documented as the vendor's
  own documented API, used with the user's own token against their own experience.
