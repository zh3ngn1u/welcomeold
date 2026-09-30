# curl reference — every confirmed Bulk Spoofer call

Companion to `./javascript.js` and `./python.py`. Every request below maps to a call site in
`analysis/js/0nh-y8e1a0l~a.js` or a path in `analysis/api/spoofer-engine-openapi.json`.

## Setup

```bash
export BACKEND="https://backend.blokmarket.store"
export ENGINE="https://spoofer.blokmarket.store"

# Required for backend calls. No value is printed anywhere in this repo — get your own.
export BMK_TOKEN="<your bmk_token>"

# Optional. A live Roblox .ROBLOSECURITY session, sent ONLY on paid runs.
export ROBLOX_COOKIE="<optional .ROBLOSECURITY>"

# Roblox OAuth access token, only needed for the upload stage.
export ROBLOX_TOKEN="<roblox_access_token>"
```

| Origin | Auth |
|---|---|
| `$BACKEND` | `Authorization: Bearer $BMK_TOKEN` + `credentials: include` |
| `$ENGINE` | **none** — no bearer, no cookies. Only `X-Roblox-Cookie` on paid runs. |

> `--cookie-jar` is included on backend calls because upstream always sets
> `credentials: "include"`. The engine calls deliberately do **not** send cookies.

---

## 1. Session

```bash
# GET /api/auth/me  — seeds user, plan, coin balance, Roblox link state
curl -sS -X GET "$BACKEND/api/auth/me" \
  -H "Authorization: Bearer $BMK_TOKEN" -b cookies.txt -c cookies.txt | jq .
# 401 body is the odd one out: {"success":false,"message":"No token"}

# GET /api/auth/spoofer-state  — coins + history
curl -sS -X GET "$BACKEND/api/auth/spoofer-state" \
  -H "Authorization: Bearer $BMK_TOKEN" -b cookies.txt -c cookies.txt | jq .
```

## 2. Free spoof — the shortest confirmed path

No coins, no audit row, never sends `X-Roblox-Cookie`.

```bash
curl -sS -X POST "$ENGINE/api/download/batch/async" \
  -H "Content-Type: application/json" \
  -d '{"assets":[{"id":1846853302,"custom_name":"Asset #1846853302"}],"is_free":true}' | jq .
# -> {"task_id":"…"}
```

## 3. Paid spoof

```bash
# POST /api/auth/spoofer-check-cost — NOT in the apiEndpoints map; undeclared surface.
# The cost is SERVER-AUTHORITATIVE; there is no client-side tier table.
curl -sS -X POST "$BACKEND/api/auth/spoofer-check-cost" \
  -H "Authorization: Bearer $BMK_TOKEN" -H "Content-Type: application/json" \
  -b cookies.txt -c cookies.txt \
  -d '{"asset_ids":["1846853302","1846853303"]}' | jq .
# -> {"success":true,"cost":…,"has_ugc":…}

# POST /api/auth/spoofer-deduct — SPENDS REAL BALANCE, at submit time. No refund exists.
curl -sS -X POST "$BACKEND/api/auth/spoofer-deduct" \
  -H "Authorization: Bearer $BMK_TOKEN" -H "Content-Type: application/json" \
  -b cookies.txt -c cookies.txt \
  -d '{"asset_count":2,"asset_ids":["1846853302","1846853303"]}' | jq .

# POST /api/spoofer-jobs — audit row. PAID RUNS ONLY; free runs write nothing.
curl -sS -X POST "$BACKEND/api/spoofer-jobs" \
  -H "Authorization: Bearer $BMK_TOKEN" -H "Content-Type: application/json" \
  -b cookies.txt -c cookies.txt \
  -d '{"job_id":"<task_id>","status":"pending","total_assets":2,
       "success_count":0,"failed_count":0,"asset_breakdown":{}}' | jq .

# POST engine — note X-Roblox-Cookie is attached ONLY because is_free is false
curl -sS -X POST "$ENGINE/api/download/batch/async" \
  -H "Content-Type: application/json" \
  -H "X-Roblox-Cookie: $ROBLOX_COOKIE" \
  -d '{"assets":[{"id":1846853302,"custom_name":"Asset #1846853302"}],"is_free":false}' | jq .
```

## 4. Poll — every 1500 ms

```bash
# GET /api/task/:taskId/status — no auth at all
curl -sS -X GET "$ENGINE/api/task/$TASK_ID/status" | jq .
# -> { status, queue_position, total_queue, assets[…], zip_download_url }
# 404 -> {"detail":"Task not found."}
```

Loop it exactly as upstream does — fixed 1.5 s, no backoff, no ceiling:

```bash
while :; do
  s=$(curl -sS -X GET "$ENGINE/api/task/$TASK_ID/status")
  echo "$s" | jq -c '{status,queue_position,total_queue,zip:(.zip_download_url!=null)}'
  echo "$s" | jq -e '.zip_download_url != null or any(.assets[]?; .asset_type=="Place")' >/dev/null && break
  sleep 1.5
done
```

## 5. Terminal reconciliation

```bash
# POST /api/auth/spoofer-state — reconcile the balance after the job, free or paid
curl -sS -X POST "$BACKEND/api/auth/spoofer-state" \
  -H "Authorization: Bearer $BMK_TOKEN" -H "Content-Type: application/json" \
  -b cookies.txt -c cookies.txt -d "{\"task_id\":\"$TASK_ID\"}" | jq .

# PATCH /api/spoofer-jobs/:id — called on EVERY asset change and again at terminal.
# Upstream truncates logs to the last 500.
curl -sS -X PATCH "$BACKEND/api/spoofer-jobs/$TASK_ID" \
  -H "Authorization: Bearer $BMK_TOKEN" -H "Content-Type: application/json" \
  -b cookies.txt -c cookies.txt \
  -d '{"status":"completed","success_count":2,"failed_count":0,
       "asset_breakdown":{"Audio":{"success":2,"failed":0}},
       "files":[],"logs":[]}' | jq .
```

## 6. Download

```bash
# The ZIP URL comes from the status payload. Upstream fetches it with a PLAIN GET,
# buffers the whole body into a Blob, and saves it. There is no signed URL and no
# Content-Disposition handling anywhere in the page.
curl -sS -L -o out.zip "$ZIP_DOWNLOAD_URL"

# Per-asset: filename = sanitise(metadata.name || custom_name) + extname(file_name)
curl -sS -L -o "asset.rbx" "$ASSET_URL"
```

## 7. Upload results into your own Roblox experience

**One asset per request, strictly serial.** The endpoint accepts an array, but upstream
sends `files:[<one asset>]`. 500 successful assets = 500 sequential round-trips.

```bash
curl -sS -X POST "$ENGINE/api/upload/batch" \
  -H "Content-Type: application/json" \
  -d '{"files":[{ …one asset… }],
       "roblox_access_token":"'"$ROBLOX_TOKEN"'",
       "creator_id":"123456",
       "creator_type":"User"}' | jq .
# creator_type = "Group" | "User"  (upstream: creator_id !== user.roblox_id ? "Group" : "User")
# -> { total, success_count, failed_count, results:[{file_name,success,asset_id,error}] }
# Client reads results[0] only.
```

### The one retry that exists — silent Roblox token refresh

```bash
# On 401 / 403, or a body error containing "401" / "invalid token" / "token":
curl -sS -X POST "$BACKEND/api/auth/roblox/refresh" \
  -H "Authorization: Bearer $BMK_TOKEN" -H "Content-Type: application/json" \
  -b cookies.txt -c cookies.txt -d '{"from":"spoofer"}' | jq .
# -> {"success":true,"robloxAccessToken":"…"}   then RE-SEND THAT ONE ASSET
# If the refresh itself fails: every REMAINING asset -> upload_status:"failed",
# upload_error:"Aborted", and the run stops.
```

## 8. Roblox account linking

```bash
# GET /api/auth/roblox/groups — the group picker
curl -sS -X GET "$BACKEND/api/auth/roblox/groups" \
  -H "Authorization: Bearer $BMK_TOKEN" -b cookies.txt -c cookies.txt | jq .

# POST /api/auth/roblox/save-api-key — Open Cloud key (account-mutating)
curl -sS -X POST "$BACKEND/api/auth/roblox/save-api-key" \
  -H "Authorization: Bearer $BMK_TOKEN" -H "Content-Type: application/json" \
  -b cookies.txt -c cookies.txt \
  -d '{"apiKey":"…","creatorId":"123456","creatorType":"Group","from":"spoofer"}' | jq .

# POST /api/auth/roblox/unlink
curl -sS -X POST "$BACKEND/api/auth/roblox/unlink" \
  -H "Authorization: Bearer $BMK_TOKEN" -H "Content-Type: application/json" \
  -b cookies.txt -c cookies.txt -d '{"from":"spoofer"}' | jq .
```

The OAuth entry is a popup and puts your bearer **in a URL query parameter** — never do that:

```bash
# GET /api/auth/roblox/login?cf_token=…&token=…&from=spoofer&t=…
#   ^^^^^^^ this is bmk_token, which now lives in browser history, Referer and provider logs
```

## 9. Payment

```bash
# POST /api/payment/create-coin-invoice — QRIS top-up
curl -sS -X POST "$BACKEND/api/payment/create-coin-invoice" \
  -H "Authorization: Bearer $BMK_TOKEN" -H "Content-Type: application/json" \
  -b cookies.txt -c cookies.txt -d '{"coins":150,"paymentMethod":"qris"}' | jq .
# -> { success, qrString, trxId, totalTransfer, isCoinTopUp, coins }

# Upstream renders the QR by handing qrString to an EXTERNAL host:
curl -sS -G "https://api.qrserver.com/v1/create-qr-code/" \
  --data-urlencode "data=$QR_STRING" \
  --data "size=600x600" --data "bgcolor=ffffff" \
  --data "color=000000" --data "margin=2" -o qr.png
# ^ the payment string leaves your infrastructure. Say so, or render it yourself.

# GET /api/payment/check/:trxId — polled every 3000 ms
curl -sS -X GET "$BACKEND/api/payment/check/$TRX_ID" | jq .
# -> { success, status: SUCCESS|EXPIRED|CANCELED, coins }

# PayPal
curl -sS -X POST "$BACKEND/api/payment/paypal/create-coin-order" \
  -H "Authorization: Bearer $BMK_TOKEN" -H "Content-Type: application/json" \
  -b cookies.txt -c cookies.txt -d '{"coins":150}' | jq .

curl -sS -X POST "$BACKEND/api/payment/paypal/capture-coin-order" \
  -H "Authorization: Bearer $BMK_TOKEN" -H "Content-Type: application/json" \
  -b cookies.txt -c cookies.txt \
  -d '{"paypalOrderId":"…","orderId":"…","coins":150}' | jq .
```

Confirmed hardcoded **top-up** tiers: `60 → Rp 50.000` · `150 → Rp 100.000` · `350 → Rp 200.000`.

> On `status == "SUCCESS"` **and** `isCoinTopUp` false, upstream auto-resumes the queued
> job without asking. See `../workflow.md` Workflow 3.

## 10. Thumbnails

```bash
# GET /api/proxy/roblox-thumbnail — 150x150 for rows, 420x420 for the modal
curl -sS -G "$ENGINE/api/proxy/roblox-thumbnail" \
  --data "assetIds=1846853302,1846853303" \
  --data "size=150x150" --data "format=Png" --data "isCircular=false" | jq .
# -> { data:[{ targetId, state, imageUrl, version }] }
# `state` may be "Blocked" while imageUrl still resolves.
```

## 11. End-to-end in one line

```bash
TASK_ID=$(curl -sS -X POST "$ENGINE/api/download/batch/async" \
  -H "Content-Type: application/json" \
  -d '{"assets":[{"id":1846853302,"custom_name":"Demo"}],"is_free":true}' \
  | jq -r .task_id)
until curl -sS "$ENGINE/api/task/$TASK_ID/status" | jq -e '.zip_download_url != null' >/dev/null; do sleep 1.5; done
curl -sS -L -o out.zip "$(curl -sS "$ENGINE/api/task/$TASK_ID/status" | jq -r .zip_download_url)"
```

---

## Not called by this tool

Published by the engine, but with **zero** frontend call sites. Do not wire these into a
Bulk Spoofer clone on the assumption they belong to it:

| Method | Path | Why it is listed |
|---|---|---|
| POST | `/api/download/batch` | the synchronous sibling; this page only calls `/async` |
| GET | `/api/download/{asset_id}` | single-asset; **the only endpoint carrying `place_id`** — *"Optional custom Place ID to spoof for private assets"* |
| GET | `/api/scan/place/{place_id}` | scans a Place for Audio/Animation/Emote refs, `page=1`/`limit=30` |
| GET | `/api/asset/{asset_id}` | metadata + cache |
| GET | `/api/files/download/{filename}` · `/api/files/zips/{filename}` | spec'd "to prevent path traversal"; this page gets URLs from the status payload instead |
| GET | `/api/proxy/roblox-thumbnail-3d` · `roblox-user-avatar-3d` · `roblox-3d-file` · `roblox-toolbox` · `roblox-catalog` | other proxy routes; the 3D ones use a *backend* `.ROBLOSECURITY` |
