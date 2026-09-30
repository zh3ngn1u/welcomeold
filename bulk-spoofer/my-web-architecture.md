# My Web Architecture — rebuilding this safely

The upstream app runs entirely in the browser: your `bmk_token` and a live Roblox
`.ROBLOSECURITY` cookie sit in `localStorage` in plaintext, and every privileged call goes
straight from the page to the vendor's backend. That is convenient and it is not something to
copy. This document shows the same functionality with the credentials where they belong.

---

## The target shape

```
┌──────────────┐   session cookie     ┌──────────────┐
│   Browser    │ ───────────────────► │              │
│              │   (HttpOnly,Secure,  │   My Backend │
│  your own UI │    SameSite=Lax)     │              │
└──────────────┘ ◄─────────────────── └──────┬───────┘
   fetch(…, {credentials:'include'})           │
                                    bearer / Roblox creds
                                             │  live only in process memory
                                             │  or a secrets manager
                                    ┌────────▼────────┐
                                    │   Upstream      │
                                    │ backend + engine│
                                    └────────┬────────┘
                                             │
                                    ┌────────▼────────┐
                                    │  Roblox          │
                                    │ (upload stage)   │
                                    └─────────────────┘
```

**The single rule:** the browser never holds `BMK_TOKEN`, `ROBLOX_COOKIE`, or `ROBLOX_TOKEN`.
It holds an opaque session cookie and nothing else.

---

## Request routing — what crosses which boundary

| Step | Browser → My Backend | My Backend → Upstream | Credential needed |
|---|---|---|---|
| Parse input | ✅ client-side | — | none |
| Enforce ≤500 | ✅ client-side **and** server-side | — | none |
| Show cost | ✅ | `POST /api/auth/spoofer-check-cost` | `BMK_TOKEN` |
| Check balance | ✅ | `GET /api/auth/spoofer-state` | `BMK_TOKEN` |
| Start job | ✅ | `POST /api/auth/spoofer-deduct` → `POST engine /api/download/batch/async` | `BMK_TOKEN`, `ROBLOX_COOKIE` |
| Poll status | ✅ via SSE or your own poll | `GET /api/task/:id/status` | none |
| Download | ✅ (URL relayed, or proxied) | — | ideally none |
| Upload to Roblox | ✅ trigger only | `POST /api/auth/roblox/refresh` → `POST engine /api/upload/batch` | `ROBLOX_TOKEN`, `BMK_TOKEN` |
| Pay | ✅ | QRIS / PayPal endpoints | `BMK_TOKEN` |

### Client-side is genuinely fine for

* **Parsing.** The 9–18 digit regex, LUA-table extraction, dedupe and filename sanitising are
  pure functions with no secrets. Verified byte-for-byte against upstream — see
  `client/javascript.js` §`parseAssets`.
* **The 500 cap** and the empty-input guard, as a UX nicety.
* **Rendering** queue position, counters and the execution log, if you poll your own backend.
* **Building the QRIS image** — but see the warning below.

### Must stay server-side

* `BMK_TOKEN` — a bearer that grants coin spending and account mutation.
* `ROBLOX_COOKIE` — a **live authenticated Roblox web session**. Full account takeover if leaked.
* `ROBLOX_TOKEN` — authorises writes into a real Roblox experience.
* **Coin deduction.** Never let the browser decide whether a charge succeeded.
* **The Roblox upload loop**, including the silent-refresh-and-retry logic.
* **Job ownership.** Which `task_id` belongs to which user.

---

## What upstream gets wrong, so you do not copy it

| Upstream | Consequence | Do instead |
|---|---|---|
| `localStorage.bmk_token` in plaintext | any XSS is a full account takeover | `HttpOnly; Secure; SameSite=Lax` session cookie your backend sets |
| `bmk_token` in the OAuth **query string** | leaks into history, `Referer`, provider logs | `POST` the token in a body, or use PKCE with the code only |
| `localStorage.bmk_spoofer_user_cookie` | the Roblox session sits in persistent storage | hold it server-side, encrypted at rest, never sent to the browser |
| No CSRF token | any `/api/**` call is forgeable from another origin | same-site cookie + CSRF token on mutations |
| `apiFetch` 401 retry replays the deleted token | renewal can never succeed | rebuild headers after refresh |
| `/api/auth/refresh` is 404 | every expiry is a logout | implement a real rotating refresh token |
| Cost display, then deduct client-side | client is the source of truth for money | deduct server-side, atomically, before you hand back a task |
| Coins spent at submit, no refund | user pays for a batch that fully failed | reserve → commit → refund on terminal failure |
| Poll with no ceiling | an interval fires every 1.5 s forever | backoff + max attempts + an explicit "lost" state |
| New job clears the old interval | starting job B orphans job A | allow concurrent jobs, keyed by `task_id` |

---

## Data flow — free spoof, end to end

```
Browser                  My Backend                      Upstream
   │                          │                               │
   │ POST /api/spoof/jobs    │                               │
   │ { raw_input }           │                               │
   │────────────────────────►│ parse + validate (≤500)       │
   │                          │                               │
   │                          │ POST engine /download/…/async │
   │                          │──────────────────────────────►│
   │                          │            { task_id }        │
   │                          │◄──────────────────────────────│
   │  { task_id }             │                               │
   │◄────────────────────────│                               │
   │                          │                               │
   │ GET /api/spoof/jobs/:id │ GET engine /task/:id/status   │
   │────────────────────────►│──────────────────────────────►│
   │                          │◄──────────────────────────────│
   │ { queue_position,        │                               │
   │   assets[], zip? }       │                               │
   │◄────────────────────────│                               │
```

Poll your own backend on the **same 1500 ms** cadence if you want identical feel — the win is
that a leaked URL gives away nothing, because `task_id` is scoped to the session that created it.

### Prefer SSE over polling

Upstream polls because it must. If you own the backend, open one `EventSource` per active
task and push updates:

```js
// Browser
const es = new EventSource(`/api/spoof/jobs/${taskId}/events`, { withCredentials: true });
es.onmessage = (e) => {
  const s = JSON.parse(e.data);              // { queue_position, total_queue, assets[] }
  if (s.zip_download_url) { /* offer the download */ es.close(); }
};
```

Your backend holds the single upstream poll and fans out. One upstream request per 1.5 s
regardless of how many tabs are open.

---

## Download handling — the one thing to get right

Upstream does this (`../download-flow.md`):

```js
let r = await fetch(url);            // no auth, no credentials
let b = await r.blob();              // ENTIRE file buffered in browser memory
let u = URL.createObjectURL(b);
```

A 500-asset ZIP is fully resident in the tab. **Do not do this.** Two safe shapes:

**A — relay a short-lived URL.** Your backend stores the `zip_download_url` against the job,
returns an opaque id, and streams on download:

```js
// Browser — no upstream URL ever reaches the client
await fetch(`/api/spoof/jobs/${taskId}/download`, { credentials: 'include' });
```

Your backend then either redirects to the upstream URL or streams the body. Streaming is
better: it keeps the URL out of the browser entirely and lets you set `Content-Disposition`
yourself, which upstream's JS never does.

**B — stream to a file handle** if you must stay client-side:

```js
const res = await fetch(url);
const handle = await window.showSaveFilePicker({ suggestedName: 'assets.zip' });
await (await handle.createWritable()).write(await res.blob());   // still buffered!
```

Note that even the File System Access API does not help without chunked reads — use a
`ReadableStream` and write chunks if you go this route. Prefer option A.

---

## The Roblox upload stage

The dangerous one. Upstream runs it in the browser with a live Roblox token in component
state. Keep it server-side.

```js
// Browser — trigger only. No token, ever.
await fetch(`/api/spoof/jobs/${taskId}/upload`, {
  method: 'POST',
  credentials: 'include',
  body: JSON.stringify({ creator_id: 123456, creator_type: 'Group' }),
});
```

Your backend then reproduces the confirmed behaviour — **serial, one asset per request, with
single-flight silent refresh and retry**:

```
for asset of successfulAssets:            # strictly serial, upstream does the same
    r = engine POST /api/upload/batch {files:[asset], roblox_access_token, creator_id, creator_type}
    if r.status in (401,403) or "token" in r.error:
        token = refresh_once()           # single-flight: one refresh at a time
        r = retry(that same asset)
        if refresh failed:
            mark all remaining {upload_status:"failed", upload_error:"Aborted"}
            break
```

Store `ROBLOX_TOKEN` encrypted at rest. It authorises writes into a real experience — a leak
is a real-world write capability, not just data disclosure.

---

## Session design

```
login / OAuth callback
   └─► validate with upstream (or your own IdP)
        └─► issue YOUR session cookie
              HttpOnly · Secure · SameSite=Lax · Path=/ · Max-Age=…
                   │
                   ├─► server-side: BMK_TOKEN   → encrypted, rotating, per user
                   ├─► server-side: ROBLOX_TOKEN → encrypted at rest, per user
                   └─► browser: nothing but the opaque cookie
```

CSRF: because the cookie is sent automatically, every mutating route needs an
`Origin`/`Referer` check at minimum, and a double-submit CSRF token for defence in depth.
Upstream has neither — check the `Origin` header on your side.

---

## Things to disclose to your users

* The **QRIS QR is rendered by a third party**. Upstream sends the payment string to
  `api.qrserver.com`, which means that string leaves your infrastructure. Either render it
  yourself or say so plainly.
* The `.ROBLOSECURITY` cookie is **their live Roblox session**. UI copy should say so.
* Uploading publishes assets **into their own Roblox experience**, under their own token.
  One mis-click writes to a live account.

---

## What NOT to build

Confirmed **absent** upstream — do not invent them:

* WebSocket / SSE / EventSource (upstream polls; `EventSource` → 0 hits)
* User-initiated cancel of a running job
* Retry of a failed spoof job (the only `retry` is the Roblox *token* refresh)
* Client-side ZIP building (`JSZip` → 0 hits; ZIPs are built server-side by the engine)
* A private-asset / `place_id` mode — the submitted body is literally `{assets, is_free}`
* Server-driven progress percentage (`progress: 20` is a hardcoded literal)

Full list with evidence: `features.md` §J.
