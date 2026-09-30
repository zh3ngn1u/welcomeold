# Endpoint Inventory

All entries below are **RETRIEVED SOURCE**: strings extracted verbatim from the public
client bundles. Base URLs are hardcoded string literals in the client.

- Primary API client module: Turbopack module `4989`, in
  `js/0vs148roxm~ft.js` (duplicate copy in `js/11wojmndz1p1s.js`)
- Host literal: `let t="https://backend.blokmarket.store".replace(/\/+$/,"")||"http://localhost:3001"`
- URL builder: ``function o(e){let o=e.startsWith("/")?e:`/${e}`;return `${t}/api${o}`}``
- Referenced env name (not populated at runtime — literal inlined): `NEXT_PUBLIC_HOST_API`

**Method note:** the client never pairs methods with paths in the endpoint map. Methods below
are taken from each *call site* in the consuming components. Paths with no observed call site
are marked `(method not observed client-side)`.

---

## Origin 1 — `https://backend.blokmarket.store` (authenticated app API)

### Auth
| Method | Path | Observed payload / notes |
|---|---|---|
| GET/POST | `/api/auth/login` | method not observed client-side (endpoint declared) |
| POST | `/api/auth/register` | method not observed client-side (endpoint declared) |
| GET | `/api/auth/me` | called on mount; response `{success, data}` |
| POST | `/api/auth/logout` | declared |
| POST | `/api/auth/refresh` | called on `401`; `credentials:"include"` |
| GET | `/api/auth/google/login` | popup OAuth entry |
| GET | `/api/auth/roblox/login` | popup OAuth entry |
| POST | `/api/auth/roblox/unlink` | `{from:"spoofer"}` \| `{from:"bmk_upload"}` |
| POST | `/api/auth/roblox/refresh` | declared |
| GET | `/api/auth/roblox/groups` | declared |
| POST | `/api/auth/roblox/save-api-key` | `{apiKey, creatorId, creatorType, from?}` |
| GET/POST | `/api/auth/spoofer-state` | GET on mount; POST `{task_id}` after job |
| POST | `/api/auth/spoofer-deduct` | `{asset_count, asset_ids[]}` |
| POST | `/api/auth/spoofer-check-cost` | `{asset_ids[]}` → `{success, cost, has_ugc}` — **not in endpoint map; built via `buildApiUrl()` in the spoofer page only** |

### Spoofer jobs
| Method | Path |
|---|---|
| POST | `/api/spoofer-jobs` |
| GET | `/api/spoofer-jobs` |
| GET | `/api/spoofer-jobs/:id` |
| PATCH | `/api/spoofer-jobs/:id` → `{status, total_assets, success_count, failed_count, ...}` |
| GET | `/api/spoofer-jobs/admin/all` |

### Donation
`/api/donation/history`, `/api/donation/donatur-leaderboard`, `/api/donation/bypass-logs`

### Experience
`/api/experience`, `/api/experience/my-list`, `/api/experience/:id`,
`/api/experience/activated/:id`

### Product
`/api/product`, `/api/product/:id`, `/api/product/category`, `/api/product/global-assets`

### Audio
`/api/audio/preview`, `/convert`, `/status/:id`, `/upload-convert`, `/upload-roblox`,
`/history`, `/history/:id`, `/approved-count`, `/approved-daily-stats`,
`/roblox-maps`, `/roblox-maps/:id`, `/publish-to-game`

### Payment (PayPal)
Invoice + order/capture triples for four flows:
`create-audio-invoice` / `paypal/create-audio-order` / `paypal/capture-audio-order`,
`create-upload-invoice` / `paypal/create-upload-order` / `paypal/capture-upload-order`,
`create-coin-invoice` / `paypal/create-coin-order` / `paypal/capture-coin-order`,
`create-b2b-invoice` / `paypal/create-b2b-order` / `paypal/capture-b2b-order`

Plus `/api/payment/check/:id`, `/api/payment/my-history?t=<ts>&type=<type>`

### Upload
`/api/upload/batch`, `/api/upload/quota`,
`/api/upload/jobs?page&limit`, `/api/upload/jobs/:id`, `/api/upload/jobs/:id/retry`

### B2B portal
`/api/b2b/portal/status`, `/key/rotate`, `/webhook`, `/logs?page&limit`, `/pricing`,
`/topup`, `/analytics?days`

### Referral
`/api/referral/join`, `/info`, `/commissions`, `/withdraw`, `/withdrawals`,
`/admin/overview`, `/admin/withdrawals`, `/admin/withdrawals/:id`

### Activity
`/api/activity/logs?month=<YYYY-MM>`

### Admin
`/api/admin/users`, `/users/:id`, `/users/change-role/:id`, `/users/limit-experience/:id`,
`/users/:id/experiences`, `/experiences`, `/experience/:id`, `/experience/activated/:id`,
`/experience/update/:id`, `/product`, `/product/:id`, `/product/category`,
`/product/category/:id`, `/payment-history`, `/assets`, `/assets/:id`,
`/b2b/overview?days`, `/b2b/tenants?page&limit&search`, `/b2b/logs?page&limit&endpoint&status&search`,
`/b2b/tenants/:id/credits`, `/b2b/tenants/:id/toggle-status`

---

## Origin 2 — `https://spoofer.blokmarket.store` (spoofing engine — NO auth header sent)

Base literal in `js/0nh-y8e1a0l~a.js`:
`et="https://spoofer.blokmarket.store/", ea=et.endsWith("/")?et.slice(0,-1):et`

| Method | Path | Headers | Body | Observed response fields |
|---|---|---|---|---|
| POST | `/api/download/batch/async` | `Content-Type: application/json`, optional `X-Roblox-Cookie` | `{assets:[…], is_free:bool}` | `{task_id}`; errors surface `detail` |
| GET | `/api/task/:taskId/status` | none | — | `status`, `queue_position`, `total_queue`, `assets[]` |
| POST | `/api/upload/batch` | `Content-Type: application/json` | `{files:[…], roblox_access_token, creator_id, creator_type}` | `{results:[{success, error}]}` |
| GET | `/api/proxy/roblox-thumbnail` | none | — | `data[0].imageUrl` (queried `?assetIds&size=150x150&format=Png&isCircular=false`) |

> These calls use raw `fetch`, **not** the `apiFetch` wrapper — so they carry **no**
> `Authorization` header and **no** refresh-on-401 logic. Authorization is server-side only.

---

## Origin 3 — `https://audio.blokmarket.store`
`GET /api/download/:id/:fileName` — built as a template string, not via `buildApiUrl`.

## Origin 4 — third-party (loaded client-side)
- `https://www.paypal.com/sdk/js?client-id=BAAE2aLMSjM7xZd0hscKvOCGclROj47Dcgx5OVRxz25I4FXB9o2CCw4NEHYV1oTRGP5RNMRbmjA7bnPWiM&curre…` (truncated in bundle)
- `https://api.qrserver.com/v1/create-qr-code/?data=<qr payload>`
- `https://i.ibb.co.com/xtby0WnJ/secur.png`
- `https://www.blokmarket.store/bgbmk.webp`
- `https://discord.com/invite/PwsAuaR9Ur`, `https://youtu.be/Ermk2raFzLo`
- `https://vercel.live/_next-live/feedback/feedback.js` (Vercel toolbar)

---

## NOT RETRIEVED (server-side, never exposed to the browser)
- All backend implementation for `backend.blokmarket.store` and `spoofer.blokmarket.store`
- Roblox Open Cloud / web API credentials used to fetch and re-upload assets
- Cloudflare Turnstile site/secret key pair (only a client-side token variable `turnstileToken` is present; the widget is rendered server-side)
- Database schema, PayPal client **secret**, Google OAuth client secret
- The "bypass" algorithm itself — the client only sees `status` strings, never the transformation
