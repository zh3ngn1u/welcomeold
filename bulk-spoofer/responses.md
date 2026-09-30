# Response Schemas & Status Codes

Two different backends → two incompatible envelopes. Normalise them.

---

## Engine — FastAPI (3.1), `spoofer.blokmarket.store`

| Status | Body | When |
|---|---|---|
| `200` | bare object, **no envelope** | success |
| `400` | `{"detail":"Either 'asset_ids' or 'assets' must be provided."}` | ✅ seen — both keys absent or empty |
| `422` | `{"detail":[{"type","loc","msg","input","ctx"}]}` | ✅ seen — Pydantic validation / wrong type |
| `404` | `{"detail":"Task not found."}` | ✅ seen — unknown `task_id` |
| `403` | — | ✅ seen on `/` (root guarded) |

`detail` is **sometimes a string and sometimes an array**. Handle both.

### 200 shapes

**`POST /api/download/batch/async`**
```json
{ "task_id": "<uuid>" }
```
Spec types this as an untyped schema; `task_id` is the field the frontend destructures.

**`GET /api/task/{id}/status`**
```jsonc
{
  "status": "<terminal state>",
  "queue_position": 3,            // null when not queued
  "total_queue": 17,
  "assets": [{
    "id": 1846853302,
    "status": "processing",       // processing | success | failed
    "real_name": "…",
    "custom_name": "…",
    "asset_type": "Audio",        // "Place" triggers the unsupported branch
    "file_name": "…",
    "file_size": 123456,
    "uploaded_asset_id": "1122334455",
    "error": null
  }],
  "zip_download_url": "https://…" // present when more than one asset succeeded
}
```
Only these fields are read by the frontend — the server may send more.

**`POST /api/upload/batch`**
```json
{ "total": 1, "success_count": 1, "failed_count": 0,
  "results": [{ "file_name": "…", "success": true, "asset_id": "…", "error": null }] }
```
Client reads `results[0]` only. `AssetUploadResult` = `{file_name, success, asset_id|null, error|null}`.

**`GET /api/proxy/roblox-thumbnail`** ✅ seen
```json
{ "data": [{ "targetId": 1846853302, "state": "Blocked",
  "imageUrl": "https://tr.rbxcdn.com/…/150/150/UnapprovedImage/Png/noFilter",
  "version": "TN3.5" }] }
```
Client reads `data[0].imageUrl`. `state` may be `Blocked` and the URL still resolve.

---

## Backend — `backend.blokmarket.store` (Express-style)

| Status | Body | Notes |
|---|---|---|
| `200` | `{"success":true,"data":…}` or `{"success":true,…}` | some routes put the payload at the **top level** |
| `401` | `{"success":false,"message":"Unauthorized"}` | ✅ seen, 20+ routes |
| `401` | `{"success":false,"message":"No token"}` | ✅ seen, **only** `/api/auth/me` |
| `404` | `{"success":false,"message":"Endpoint not found"}` | ✅ seen, `/api/auth/refresh` |
| `500` | `{success:false, message:?}` | **?** — never observed |

> ⚠️ **Top-level vs `data`:** `/api/audio/approved-count` returns `{"success":true,"count":32959}`
> — `count` is **not** under `data`. Do not assume a uniform envelope.

### Fields consumed per route
| Route | Fields read |
|---|---|
| `/api/auth/me` | `success`, `data` → `id, name, email, role, experience_limit, plan_type, spoofer_state{roblox{roblox_id, roblox_access_token, roblox_username, roblox_display_name, roblox_api_key}, coins, history[]}, audio_plan, audio_plan_expires` |
| `/api/auth/spoofer-state` | `success`, `data.coins` (guarded by `typeof === "number"`), `data.history[]` (`Array.isArray`) |
| `/api/auth/spoofer-check-cost` | `success`, `cost`, `has_ugc`, `message` |
| `/api/auth/spoofer-deduct` | `success`, `coins`/`newCoins`, `message` |
| `/api/spoofer-jobs` | `success`, `data` |
| `/api/spoofer-jobs/:id` | `success`, `data`, `message` |
| `/api/auth/roblox/refresh` | `success`, `robloxAccessToken` |
| `/api/payment/create-coin-invoice` | `qrString`, `trxId`, `totalTransfer`, `isCoinTopUp`, `coins` |
| `/api/payment/check/:id` | `success`, `status`, `coins` |

**All of the above are `[read]` from the handlers, not `[seen]` in a live response** — no account
was authenticated during this analysis. The two envelopes and the `400/401/403/404/422` bodies
**are** `[seen]`.

---

## Job-status vocabulary

| Context | Values (from the bundle) |
|---|---|
| Engine per-asset | `processing`, `success`, `failed` |
| Client placeholder (pre-response) | `loading` |
| Upload | `upload_status`: `not_started`, `failed`; success inferred from `uploaded_asset_id` |
| Job record | `pending`, `completed`, `partial`, `bypass_completed`, `bypass_failed`, `failed` |
| Admin filter enum | `all`, `completed`, `partial`, `bypass_completed`, `failed` |
| Payment | `SUCCESS`, `EXPIRED`, `CANCELED` |
| Asset types | `Audio`, `Animation`, `Decal`, `Place` (unsupported), `Unknown` (fallback) |

## Known defect: the refresh path
`POST /api/auth/refresh` → **404** (both `GET` and `POST`, verified). `apiFetch` calls it as the
sole token-renewal mechanism and hard-redirects to `/login` when it fails. **No token is ever
silently renewed** — every expiry is a logout. Availability bug, not a security hole.
