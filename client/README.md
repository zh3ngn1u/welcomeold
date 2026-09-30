# Ready-to-implement client

A clean integration surface for the Blokmarket spoofer / B2B API — **not** a copy of the vendor's
UI. Every function maps to an endpoint that was actually observed in the downloaded bundles or in
the engine's published OpenAPI spec.

| File | What it is |
|---|---|
| `javascript.js` | Node 18+ client, zero dependencies. 32 exports. |
| `python.py` | Python client, needs `requests`. |
| `curl.md` | Every endpoint as a copy-pasteable command. |

## Provenance rules used

1. Every request field is either read from a call site in `../js/*.js` or from a component schema
   in `../api/spoofer-engine-openapi.json`.
2. No field was inferred from a name. Where the upstream code does not reveal something, the
   spec says `NOT CONFIRMED FROM FRONTEND` rather than guessing.
3. **No token, cookie or key is hardcoded anywhere.** All credentials come from env vars.
4. Client-side caps are reproduced (500 IDs, filename sanitiser) but are marked as
   *not confirmed* server-enforced — enforce them in your own backend too.
5. No `getResult` route was invented. The engine's status response **is** the result; the helper
   only reshapes it, and says so.

## Setup

```bash
# Python
pip install requests

# Credentials — supply your own, never commit them
export BMK_TOKEN="<your bmk_token>"
export ROBLOX_COOKIE="<your .ROBLOSECURITY value>"      # optional
export ROBLOX_TOKEN="<your Roblox OAuth access token>"  # optional
```

## Smoke test — runs with no credentials

```bash
python3 python.py
```

Expected, verified live 2026-09-30:

```
health          : {'success': True, 'data': {'status': 'healthy', 'service': 'bmk-upload', 'active_jobs': 0}}
approved count  : {'success': True, 'count': 32959}
categories      : ['Free', 'Script', 'Tool']
catalog count   : 5
approved daily  : {'date': '2026-09-30', 'day': 'Wed', 'count': 254}
```

## The core four

```js
const { createSpoofJob, getJobStatus, getResult, pollTask } = require('./javascript.js');

const { task_id } = await createSpoofJob([{ id: 1846853302 }], { isFree: true });
const status = await getJobStatus(task_id);        // { queue_position, total_queue, assets[] }
const result = await getResult(task_id);           // reshaped status; no separate endpoint exists
const done   = await pollTask(task_id, { onUpdate: s => console.log(s.queue_position) });
```

```python
from python import create_spoof_job, get_job_status, get_result, poll_task

task  = create_spoof_job([{"id": 1846853302}], is_free=True)
st    = get_job_status(task["task_id"])
res   = get_result(task["task_id"])
final = poll_task(task["task_id"], on_update=lambda s: print(s.get("queue_position")))
```

## End-to-end

```js
const { runBatch } = require('./javascript.js');
const r = await runBatch('{1846853302}, {1846853303}', { isFree: true });
console.log(r.succeeded.length, 'ok,', r.failed.length, 'failed, zip:', r.zipUrl);
```

Mirrors the upstream order exactly: `check-cost` → optional `deduct` → `batch/async` →
poll 1500 ms → `spoofer-state` reconcile → `PATCH spoofer-jobs/:id`.

## Error contracts (all reproduced and verified live)

| Call | Result |
|---|---|
| `get_task_status(<bogus>)` | `EngineError: 404 Task not found.` |
| `create_spoof_job([])` | `EngineError: 400 Either 'asset_ids' or 'assets' must be provided.` |
| `POST /api/upload/batch {}` | `EngineError: 422 body.files: Field required; body.creator_id: …; body.creator_type: …` |
| `get_auth_me()` no token | `APIError: 401 … token refresh failed (POST /api/auth/refresh -> 404)` |

The last one is a real upstream defect: `/api/auth/refresh` does not exist, so the client's only
renewal path is dead and every token expiry is a hard logout.

## What the client deliberately does NOT do

* It does not call `/api/scan/place/*`, `/api/download/{id}` or `/api/download/batch`. Those are
  the asset-extraction functions; they are documented in `../my-api-client-spec.md` but not
  exercised here.
* It does not touch payment or coin-purchase endpoints.
* It does not invent a private-asset parameter. The dashboard sends only `{assets, is_free}`; the
  `place_id` "spoof for private assets" capability exists **server-side only** and is not
  reachable from the bulk UI.
* It does not hardcode or guess the B2B Mesh gateway host, or the `bmk_token` format.

## Security notes for whoever wires this up

* Run the client **server-side**. It carries `BMK_TOKEN`, `ROBLOX_COOKIE` and `ROBLOX_TOKEN`.
* The engine takes the Roblox OAuth bearer as a **query parameter** — it will appear in access
  logs, history and `Referer`. Prefer the `X-Roblox-Cookie` header where possible.
* The engine **echoes any caller's `Origin`** with `access-control-allow-credentials: true`,
  while the dashboard backend does not. Do not add your own origin to that allowlist.
* Rate limits are advertised (60/180/600 req-min) but no limit header was ever observed. Add
  your own throttling and backoff; the upstream client has neither.

## ToS note

The engine's own spec describes scanning Roblox experiences for Audio/Animation/Emote IDs and
re-uploading them under a new creator ID. That conflicts with Roblox's Terms of Service, and
re-uploading third-party audio without the rightsholder's permission implicates copyright. It is
a property of the service, not of this client — but it is a decision to make knowingly.
