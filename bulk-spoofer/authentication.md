# Authentication Map

Four credential families. **No real value is printed anywhere in this document, and none was
obtained** — no account was authenticated during this analysis.

---

## 1. Dashboard session — `bmk_token`

| Property | Value |
|---|---|
| Credential name | `bmk_token` (localStorage key) |
| Storage | `localStorage` — **plaintext** |
| Read at | `localStorage.getItem("bmk_token")`, inside `apiFetch` (module `4989`) |
| Sent via | `Authorization: Bearer <bmk_token>` |
| Also sent | `credentials: "include"` → any refresh cookie rides along |
| Required for | **all** `/api/**` on `backend.blokmarket.store` |
| CSRF header | **none** — no `X-CSRF-Token` or equivalent in any bundle |
| `sessionStorage` | **not used anywhere** (0 hits, all 34 chunks) |
| Browser or server | browser-side in the vendor app; **server-side in yours** |
| Format / algorithm / TTL | **NOT CONFIRMED** — handled as an opaque string client-side |

### Issuance
OAuth popup → `postMessage` to the parent → `localStorage.setItem("bmk_token", e.data.token)`.
Two providers, both Turnstile-gated:

```js
// Roblox  — 0k1tyysfi6yay.js
GET /api/auth/roblox/login?cf_token=<turnstile>&token=<bmk_token>&from=spoofer&t=<ms>
// Google  — 0jxi_hvhi.3ae.js
GET /api/auth/google/login?prompt=select_account&cf_token=<turnstile>&ref=<bmk_ref cookie>&t=<ms>
```
The popup result is inspected as `e.data === "oauth_success"` or `e.data?.type === "oauth_success"`
or `e.data?.status === "success"`, filtered by `e.data.from === "spoofer"`.

> **Email/password login: NOT CONFIRMED.** `/api/auth/login` and `/api/auth/register` are declared
> in the `apiEndpoints` map but have **zero** call sites in any downloaded chunk, and no email or
> password payload could be extracted. Do not assume a login body.

### Lifecycle
| Event | Action |
|---|---|
| `401` on any call | `localStorage.removeItem("bmk_token")` |
| `401` (not on `/login`) | `POST /api/auth/refresh` once, retry once |
| refresh fails or throws | `window.location.href = "/login"` |
| Logout button | `removeItem` → `POST /api/auth/logout?t=<ms>` (`credentials:"include"`) → `/login` |

> ⚠️ `/api/auth/refresh` answers **404** (verified, both methods). The renewal path is dead, so
> every token expiry becomes a hard logout.

## 2. Roblox session (second factor for the tool)

The tool refuses to run without a linked Roblox identity:
```js
ep = !!(ex?.roblox_id && ex?.roblox_access_token)
```

| Property | Value |
|---|---|
| Credential name | `roblox_access_token`, `roblox_api_key` |
| Storage | server-side, surfaced to the UI at `userAtom.spoofer_state.roblox.*` |
| Sent via | **request body** on `engine /api/upload/batch` (`roblox_access_token`) |
| Refreshed via | `POST /api/auth/roblox/refresh {from:"spoofer"}` → `robloxAccessToken` |
| Browser or server | **server-side in yours** — it authorises writes into a real Roblox experience |

## 3. Roblox `.ROBLOSECURITY` cookie (optional)

| Property | Value |
|---|---|
| Credential name | `.ROBLOSECURITY` |
| Source | a `type:"password"` textarea, user-pasted |
| Storage | `localStorage.bmk_spoofer_user_cookie` — **plaintext** |
| Sent via | header `X-Roblox-Cookie: <value>` |
| Sent to | `engine /api/download/batch/async`, **only when `is_free === false`** |
| Required | no — the field is labelled *"(optional, recommended)"* |
| Browser or server | **server-side in yours** — a live Roblox web session |

UI copy: *"Your cookie is only used for the bypass request to Roblox"* — the code sends it to
`spoofer.blokmarket.store`, a **different origin** from the dashboard.

## 4. Cloudflare Turnstile (pre-auth gate)

| Property | Value |
|---|---|
| Variable | `turnstileToken`; the spoofer page passes the literal `"bypass_local"` |
| Enforcement | client-side — both OAuth buttons are disabled while it is falsy |
| Forwarded as | `cf_token` on the OAuth entry URL |
| Site key / secret | **NOT CONFIRMED** — the widget is server-rendered; no key literal in any bundle |
| Verified by | the client only. Server-side verification is backend-only. |

## 5. Credentials that are NOT used here
* No API key header, no `x-api-key`, no `x-experience-id` — although the backend *allows* them in
  CORS. Not used by this tool.
* No cookie-based session for the engine — engine calls send no `credentials` mode.
* No `sessionStorage` usage at all.
* No B2B seller key (`bmk_spoof_…`) is used by this page. That belongs to `/tools/b2b-api`;
  see `../reseller/auth.md`.

## Server-side credentials (never in the bundle, never retrievable)
Roblox Open Cloud service keys used by the engine, PayPal/QRIS secrets, the Google OAuth client
secret, the Cloudflare Turnstile secret key, JWT signing keys, and the engine's own
`.ROBLOSECURITY` — the spec says its 3D-thumbnail routes use *"backend ROBLOSECURITY cookie"*.

## Exposure summary for a re-implementation
`localStorage` on the dashboard origin holds **three** high-value secrets in plaintext:
`bmk_token`, `bmk_spoofer_user_cookie`, and (on the B2B page) `bmk_b2b_raw_key`.
The OAuth entry also puts `bmk_token` in a **URL query parameter**, where it can reach history,
`Referer` and provider logs. Neither pattern is needed — see `my-web-architecture.md`.
