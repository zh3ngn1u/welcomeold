# Request Schemas — exact, as constructed by the frontend

Every body below is copied verbatim from the call site. Minified variable names are kept so the
literal matches the bundle. `?` = `NOT CONFIRMED`.

---

## Backend — `https://backend.blokmarket.store`

All carry `Authorization: Bearer <bmk_token>` and `credentials: "include"` via `apiFetch`.
JSON bodies add `Content-Type: application/json`.

### 1. `GET /api/auth/me`
No body, no params, no custom headers. Gate for the entire page.

### 2. `GET /api/auth/spoofer-state`
No body. On mount and after a successful QRIS top-up.

### 3. `POST /api/auth/spoofer-state`
```json
{ "task_id": "<engine task_id>" }
```
Sent once a job reaches a terminal state, to reconcile the coin balance.

### 4. `POST /api/auth/spoofer-check-cost`
```json
{ "asset_ids": [ 1846853302, 1846853303 ] }
```
Built as `asset_ids: e.map(e => e.id)`. **Not in the `apiEndpoints` map** — the page uses
`buildApiUrl("/auth/spoofer-check-cost")`.
Response fields consumed: `success`, `cost`, `has_ugc`, `message`.

### 5. `POST /api/auth/spoofer-deduct`
```json
{ "asset_count": 2, "asset_ids": [ 1846853302, 1846853303 ] }
```
Built as `{ asset_count: e5.length, asset_ids: e5.map(e => e.id) }`.
Response fields consumed: `success`, `coins` / `newCoins`, `message`.

### 6. `POST /api/spoofer-jobs`
```json
{
  "job_id": "<task_id>",
  "status": "pending",
  "total_assets": 2,
  "success_count": 0,
  "failed_count": 0,
  "asset_breakdown": { "Audio": { "success": 0, "failed": 0 } }
}
```
`asset_breakdown` is built from `assets[].asset_type` (or `"Unknown"`), incrementing
`success`/`failed` by `assets[].status === "success"`.
Written **only for non-free runs**. Response consumed: `success`, `data`.

### 7. `PATCH /api/spoofer-jobs/:id`
```json
{
  "status": "completed",
  "success_count": 2,
  "failed_count": 0,
  "asset_breakdown": { "Audio": { "success": 2, "failed": 0 } },
  "files": [
    { "id": 1846853302, "custom_name": "Asset #1846853302", "status": "success",
      "file_name": null, "file_size": 0, "asset_type": "Unknown",
      "uploaded_asset_id": null, "upload_status": "not_started", "upload_error": null }
  ],
  "logs": [ /* …slice(-500) */ ]
}
```
Two call sites: `sY` (status change / terminal) and `sX` (upload-status change).

### 8–11. Roblox account
| Endpoint | Body |
|---|---|
| `POST /api/auth/roblox/save-api-key` | `{ "apiKey": "<trimmed>", "creatorId": "<trimmed>", "creatorType": "User"\|"Group", "from": "spoofer" }` |
| `POST /api/auth/roblox/unlink` | `{ "from": "spoofer" }` |
| `POST /api/auth/roblox/refresh` | `{ "from": "spoofer" }` → response field `robloxAccessToken` |
| `GET /api/auth/roblox/login` | query `?cf_token=<turnstile>&token=<bmk_token>&from=spoofer&t=<ms>` — popup, `width=500,height=650` |

### 12–15. Coins
```json
{ "coins": 60, "paymentMethod": "qris" }                                  // create-coin-invoice
{ "coins": 60 }                                                          // paypal/create-coin-order
{ "paypalOrderId": "<e.orderID>", "orderId": "<trxId|orderID>", "coins": 60 }  // capture-coin-order
```
`coins` defaults to `60` (`eT.coins || 60`).
`create-coin-invoice` response fields consumed: `qrString`, `trxId`, `totalTransfer`,
`isCoinTopUp`, `coins`.

### 16. `GET /api/payment/check/:id`
No body, no params. Response: `success`, `status` (`SUCCESS` | `EXPIRED` | `CANCELED`), `coins`.

## Engine — `https://spoofer.blokmarket.store`

**No `Authorization` header. No `credentials` mode.** Raw `fetch`.

### 17. `POST /api/download/batch/async`
```http
Content-Type: application/json
X-Roblox-Cookie: <user .ROBLOSECURITY>     ← only when is_free === false AND a cookie was pasted
```
```json
{ "assets": [ { "id": 1846853302, "custom_name": "Asset #1846853302" } ], "is_free": false }
```
Constructed literally as `JSON.stringify({assets:e, is_free:s})`. Nothing else is sent.

Full server schema (`BatchDownloadRequest`, `../api/spoofer-engine-openapi.json`):

| Field | Type | Req | Default | Spec description |
|---|---|---|---|---|
| `assets` | `AssetBatchItem[]\|null` | no | — | "Optional list of structured Asset IDs with custom names" |
| `asset_ids` | `integer[]\|null` | no | — | "Optional flat list of Roblox Asset IDs" |
| `is_free` | `boolean\|null` | no | `false` | "Is this a free spoof request?" |
| `roblox_api_key` | `string\|null` | no | — | "Roblox Open Cloud API Key for auto upload" |
| `creator_id` | `string\|null` | no | — | "Roblox User or Group Creator ID to upload under" |
| `creator_type` | `string\|null` | no | — | "Creator Type (User or Group)" |

`AssetBatchItem` = `{ id: integer (required), custom_name: string\|null }`.

> Only 2 of 6 fields are used by the dashboard. `asset_ids` is an undocumented alternative,
> proven by the live `400` message.

### 18. `GET /api/task/{task_id}/status`
No headers, no body. The `task_id` comes from the create response.

### 19. `POST /api/upload/batch`
```json
{
  "files": [ { "file_name": "…", "display_name": "…" } ],
  "roblox_access_token": "<userAtom.spoofer_state.roblox.roblox_access_token>",
  "creator_id": "<roblox_id>",
  "creator_type": "User"
}
```
Constructed as `JSON.stringify({files:[e], roblox_access_token:s, creator_id:i, creator_type:r})`
— note `files` is an array holding exactly **one** asset per request.

Server schema `UploadBatchRequest`:

| Field | Type | Req | Description |
|---|---|---|---|
| `files` | `UploadBatchItem[]` | **yes** | list of files |
| `creator_id` | `string` | **yes** | Roblox User or Group Creator ID |
| `creator_type` | `string` | **yes** | "User" or "Group" |
| `roblox_api_key` | `string\|null` | no | Roblox Open Cloud API Key |
| `roblox_access_token` | `string\|null` | no | Roblox OAuth Access Token |
| `custom_description` | `string\|null` | no | "Custom white-label description" |

`UploadBatchItem` = `{ file_name: string (req), display_name: string (req), asset_type: string|null }`

### 20. `GET /api/proxy/roblox-thumbnail`
```
?assetIds=<id>&size=150x150&format=Png&isCircular=false     ← list
?assetIds=<id>&size=420x420&format=Png&isCircular=false     ← detail modal
```

## Multipart
**None.** The Bulk Spoofer sends no `FormData`; it is JSON + one optional cookie header only.
(`FormData` appears in this app only for `/api/upload/batch`, `/api/audio/upload-convert` and
`/api/experience` — different tools.)

## Dynamically constructed URLs (no template literals missed)
`${ea}/api/proxy/roblox-thumbnail`, `${ea}/api/task/${e}/status`,
`${ea}/api/download/batch/async`, `${ea}/api/upload/batch`, plus `buildApiUrl()` and
`apiEndpoints` for the backend. Four engine call sites total; all four are captured above.
