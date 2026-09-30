# cURL reference

Every command below uses only fields confirmed in the downloaded bundles or the engine's public
OpenAPI spec. **No real token, cookie or key appears anywhere.** Substitute your own credentials
into the exported variables.

```bash
export BACKEND="https://backend.blokmarket.store"
export ENGINE="https://spoofer.blokmarket.store"
export YOUR_AUTH_TOKEN="<paste your own bmk_token>"        # dashboard bearer
export YOUR_ROBLOX_COOKIE="<your .ROBLOSECURITY value>"    # engine header, server-side only
export YOUR_ROBLOX_TOKEN="<your Roblox OAuth access token>" # engine ?authorization=, server-side only
```

---

## 0. Public — no credentials (verified live 2026-09-30)

```bash
curl -sS "$BACKEND/api/upload/health"
curl -sS "$BACKEND/api/product"
curl -sS "$BACKEND/api/product/category"
curl -sS "$BACKEND/api/audio/approved-count"
curl -sS "$BACKEND/api/audio/approved-daily-stats"
curl -sS "$ENGINE/openapi.json" | head -c 400
```

Observed: `{"success":true,"count":32959}`, `{"success":true,"data":{"status":"healthy","service":"bmk-upload","active_jobs":0}}`, etc.
Note `count` on `/audio/approved-count` is **top-level**, not under `data`.

## 1. Auth gate — shows the exact 401 contract

```bash
curl -sS -i "$BACKEND/api/auth/me"
# HTTP/2 401 -> {"success":false,"message":"No token"}

curl -sS -i -X POST -H 'Content-Type: application/json' -d '{}' "$BACKEND/api/auth/refresh"
# HTTP/2 404 -> {"success":false,"message":"Endpoint not found"}
#   ^ the client's only token-renewal path is dead; every expiry is a hard logout
```

---

## 2. Spoofer engine — create a job

Body is verbatim what the dashboard sends. No `Authorization`, no cookies.

```bash
curl -sS -X POST \
  -H 'Content-Type: application/json' \
  -d '{"assets":[{"id":1846853302,"custom_name":null}],"is_free":true}' \
  "$ENGINE/api/download/batch/async"
# 200 -> {"task_id":"<uuid>"}
```

With a Roblox session attached (only meaningful when `is_free` is false):

```bash
curl -sS -X POST \
  -H 'Content-Type: application/json' \
  -H "X-Roblox-Cookie: $YOUR_ROBLOX_COOKIE" \
  -d '{"assets":[{"id":1846853302,"custom_name":null}],"is_free":false}' \
  "$ENGINE/api/download/batch/async"
```

Validation contracts (safe — they cannot perform any work):

```bash
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"assets":[],"is_free":false}' "$ENGINE/api/download/batch/async"
# 400 -> {"detail":"Either 'asset_ids' or 'assets' must be provided."}
#        NOTE: the server also accepts a flat "asset_ids": [int] array. The UI never sends it.

curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"assets":"not-a-list"}' "$ENGINE/api/download/batch/async"
# 422 -> FastAPI validation array
```

## 3. Spoofer engine — poll status

```bash
curl -sS "$ENGINE/api/task/<TASK_ID>/status"
curl -sS "$ENGINE/api/task/00000000-0000-0000-0000-000000000000/status"
# 404 -> {"detail":"Task not found."}
```

Upstream polls this every **1500 ms** and stops when no asset is `processing`.

## 4. Spoofer engine — thumbnail proxy (public)

```bash
curl -sS "$ENGINE/api/proxy/roblox-thumbnail?assetIds=1846853302&size=150x150&format=Png&isCircular=false"
# 200 -> {"data":[{"targetId":1846853302,"state":"Blocked","imageUrl":"https://tr.rbxcdn.com/…"}]}
```

## 5. Spoofer engine — upload to Roblox (one asset per request)

```bash
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{}' "$ENGINE/api/upload/batch"
# 422 -> required: files, creator_id, creator_type   (roblox_access_token is optional)

curl -sS -X POST -H 'Content-Type: application/json' \
  -d "{\"files\":[{\"file_name\":\"a.mp3\",\"display_name\":\"a\"}],
       \"roblox_access_token\":\"$YOUR_ROBLOX_TOKEN\",
       \"creator_id\":\"12345\",\"creator_type\":\"User\"}" \
  "$ENGINE/api/upload/batch"
# 200 -> {"total":1,"success_count":1,"failed_count":0,
#         "results":[{"file_name":"a.mp3","success":true,"asset_id":"…","error":null}]}
```

---

## 6. Dashboard backend — authenticated

```bash
AUTH=(-H "Authorization: Bearer $YOUR_AUTH_TOKEN" -H 'Content-Type: application/json')
```

```bash
curl -sS "${AUTH[@]}" "$BACKEND/api/auth/me"
curl -sS "${AUTH[@]}" "$BACKEND/api/auth/spoofer-state"

curl -sS -X POST "${AUTH[@]}" \
  -d '{"task_id":"<TASK_ID>"}' "$BACKEND/api/auth/spoofer-state"

curl -sS -X POST "${AUTH[@]}" \
  -d '{"asset_ids":[1846853302]}' "$BACKEND/api/auth/spoofer-check-cost"
# -> {"success":true,"cost":…,"has_ugc":…}
#    NOT in the upstream apiEndpoints map — built via buildApiUrl().

curl -sS -X POST "${AUTH[@]}" \
  -d '{"asset_count":1,"asset_ids":[1846853302]}' "$BACKEND/api/auth/spoofer-deduct"
```

### Job records
```bash
curl -sS -X POST "${AUTH[@]}" \
  -d '{"job_id":"<TASK_ID>","status":"pending","total_assets":1,
       "success_count":0,"failed_count":0,"asset_breakdown":{}}' \
  "$BACKEND/api/spoofer-jobs"

curl -sS "${AUTH[@]}" "$BACKEND/api/spoofer-jobs"
curl -sS "${AUTH[@]}" "$BACKEND/api/spoofer-jobs/<JOB_ID>"

curl -sS -X PATCH "${AUTH[@]}" \
  -d '{"status":"completed","success_count":1,"failed_count":0,
       "asset_breakdown":{},"files":[],"logs":[]}' \
  "$BACKEND/api/spoofer-jobs/<JOB_ID>"
```

### B2B Mesh seller portal
```bash
curl -sS "${AUTH[@]}" "$BACKEND/api/b2b/portal/status"          # -> { success, tenant, isLocked, rawKey }
curl -sS "${AUTH[@]}" "$BACKEND/api/b2b/portal/logs?page=1&limit=50"
curl -sS "${AUTH[@]}" "$BACKEND/api/b2b/portal/analytics?days=7"

curl -sS -X POST "${AUTH[@]}" "$BACKEND/api/b2b/portal/key/rotate"      # no body; invalidates the old key

curl -sS -X PUT "${AUTH[@]}" \
  -d '{"webhookUrl":"https://example.com/hook"}' \
  "$BACKEND/api/b2b/portal/webhook"
```

### Admin B2B control (requires admin/owner)
```bash
curl -sS "${AUTH[@]}" "$BACKEND/api/admin/b2b/overview?days=7"
curl -sS "${AUTH[@]}" "$BACKEND/api/admin/b2b/tenants?page=1&limit=15&search="
curl -sS "${AUTH[@]}" "$BACKEND/api/admin/b2b/logs?page=1&limit=20&endpoint=&status=&search="

curl -sS -X POST "${AUTH[@]}" \
  -d '{"amount":500,"action":"add"}' \
  "$BACKEND/api/admin/b2b/tenants/<TENANT_ID>/credits"
#   action: "add" | "deduct" | "set"

curl -sS -X POST "${AUTH[@]}" "$BACKEND/api/admin/b2b/tenants/<TENANT_ID>/toggle-status"
```

### Admin spoofer audit
```bash
curl -sS "${AUTH[@]}" "$BACKEND/api/spoofer-jobs/admin/all?page=1&limit=10&status=all&assetType=Audio&search="
#   status:     all | completed | partial | bypass_completed | failed
#   assetType:  all | Audio | Animation | Decal | …
```

### Multipart uploads
```bash
curl -sS -X POST "${AUTH[@]}" \
  -F "creator_id=12345" -F "is_group=false" -F "target_name=MyPlace" \
  -F "files=@a.mp3" \
  "$BACKEND/api/upload/batch"
# NOTE: the dashboard also sends access_token="session_auto_resolved" — a literal the
#       server substitutes with the caller's own token. Do not send a real one here.

curl -sS -X POST "${AUTH[@]}" \
  -F "file=@song.ogg" -F "roblox_speed=1" -F "amplify_db=0" \
  -F "modify=true" -F "format=mp3" -F "max_duration=420" \
  "$BACKEND/api/audio/upload-convert"
```

### Logout (raw fetch upstream, with a cache-buster)
```bash
curl -sS -X POST --cookie-jar /tmp/bmk.jar "$BACKEND/api/auth/logout?t=$(date +%s%3N)"
```

---

## 7. CORS probes

```bash
curl -sS -i -X OPTIONS -H 'Origin: https://evil.example' \
  -H 'Access-Control-Request-Method: GET' \
  -H 'Access-Control-Request-Headers: authorization' \
  "$BACKEND/api/auth/me" | grep -i '^HTTP\|access-control'
# -> 204, allow-credentials:true, NO allow-origin  (backend blocks foreign origins)

curl -sS -i -X OPTIONS -H 'Origin: https://customer.blokmarket.store' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type,x-roblox-cookie' \
  "$ENGINE/api/download/batch/async" | grep -i '^HTTP\|access-control'
# -> 200, allow-origin is ECHOED, max-age 600
```

---

## Errors — the two shapes

```bash
# Engine (FastAPI)
{"detail":"Task not found."}
{"detail":[{"type":"missing","loc":["body","files"],"msg":"Field required","input":{}}]}

# Backend (Express-style)
{"success":false,"message":"No token"}
{"success":false,"message":"Unauthorized"}
{"success":false,"message":"Endpoint not found"}
```

Handle both. Do not assume a `message` field exists on engine errors, and do not assume
`detail` is a string — it can be an array.

## Rate limits
**Not observable.** No `429`, `Retry-After` or `X-RateLimit-*` header appeared in any of the 44
requests made during analysis, and no burst was generated. The B2B plan tables advertise
60/180/600 req-min, and the admin log filter has a `429 Rate / Limit` option, so limits exist
server-side — but the headers, window and enforcement are **NOT CONFIRMED FROM FRONTEND**.
