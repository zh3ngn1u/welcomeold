# Authentication — every mechanism actually observed

**No account was authenticated during this analysis.** All 44 live requests were unauthenticated
`curl`. Everything below is read from the bundles plus the `401`/`404` bodies actually captured.

---

## 1. Dashboard session — `bmk_token` (Bearer)

### Storage and lifecycle
| Step | Mechanism | Source |
|---|---|---|
| Create | Google or Roblox OAuth **popup**; parent listens for `window.postMessage` | `0jxi_hvhi.3ae.js`, `0k1tyysfi6yay.js` |
| Capture | `e.data.token && localStorage.setItem("bmk_token", e.data.token)` | verbatim |
| Use | `i.set("Authorization", \`Bearer ${a}\`)` in `apiFetch` | `0vs148roxm~ft.js` |
| Reject | `401` → `localStorage.removeItem("bmk_token")` | verbatim |
| Clear | Logout button: `localStorage.removeItem("bmk_token")` then `POST /api/auth/logout?t=<ts>` with `credentials:"include"`, then `location.href="/login"` | `0a6h4o63da-vz.js` |

**Token shape / algorithm: not observable.** The client only ever handles it as an opaque string.
No JWT header/payload parsing, no `exp` check, no refresh-token rotation exists client-side.

### The refresh path is broken as shipped
```js
if(401===o.status && localStorage.removeItem("bmk_token"), "/login"!==window.location.pathname)
  try { (await fetch(r.auth.refresh(), {method:"POST", credentials:"include"})).ok
          ? o=await l() : window.location.href="/login" }
  catch(e){ window.location.href="/login" }
```
`POST /api/auth/refresh` → **`404 {"success":false,"message":"Endpoint not found"}`** `[seen]`
(`../api/responses/02`, `12`). `.ok` is false → hard redirect to `/login`.
**No token is ever silently renewed**, and the stored token is already deleted by then. Impact is
availability, not security.

### Send shape (verbatim)
```js
let i = new Headers(t.headers || {});
a && i.set("Authorization", `Bearer ${a}`);
fetch(e, { ...t, headers:i, credentials:"include" })
```
`credentials:"include"` is always set, so the refresh cookie rides along on every call.

---

## 2. Cloudflare Turnstile — pre-auth gate

Both OAuth buttons are inert until a Turnstile token exists:

```js
if(!g) return void f("Please complete the security verification first.");
if(j) return;
window.open(`${apiEndpoints.auth.robloxLogin()}?cf_token=${g}&token=${a}&from=${k}&t=${Date.now()}`,
             "robloxLogin", "width=500,height=650,…")
```
* Variable name `turnstileToken`; the bulk-spoofer page passes the literal `"bypass_local"`.
* The token is forwarded to the backend as `cf_token`.
* Popup-blocked handling: `"Popup blocked! Please allow popups for this site."`
* **Site key and secret: not retrievable.** The widget is rendered server-side; no site key
  literal appears in any bundle.

---

## 3. Roblox account linkage

The bulk spoofer requires a linked Roblox identity before it will run:

```js
ec?.spoofer_state?.roblox
ep = !!(ex?.roblox_id && ex?.roblox_access_token)
```

Stored under `userAtom.spoofer_state.roblox` `[read]`:
`roblox_id`, `roblox_access_token`, `roblox_username`, `roblox_display_name`, `roblox_api_key`.

| Action | Endpoint | Body |
|---|---|---|
| Link (OAuth) | `GET /api/auth/roblox/login` popup | `?cf_token=&token=&from=` |
| Save Open Cloud key | `POST /api/auth/roblox/save-api-key` | `{apiKey, creatorId, creatorType, from?}` |
| Unlink | `POST /api/auth/roblox/unlink` | `{from:"spoofer"\|"bmk_upload"\|"audio"}` |
| Refresh | `POST /api/auth/roblox/refresh` | `{from:"spoofer"}` |

> **The dashboard `bmk_token` is passed as a URL query parameter** into the OAuth popup
> (`?token=${a}`). Query strings land in browser history, `Referer` headers and the OAuth
> provider's access logs. Frontend-observable; not exploited or tested.

---

## 4. B2B Mesh seller key — `bmk_spoof_…`

A **second, independent** credential — not a `bmk_token`.

| Property | Value | Source |
|---|---|---|
| Prefix | `bmk_spoof_` | `e.startsWith("bmk_spoof_")` `[read]` |
| Displayed form | `tenant.api_key_prefix` | `[read]` |
| Full value | `rawKey` from `GET /api/b2b/portal/status` / `POST /api/b2b/portal/key/rotate` | `[read]` |
| Client storage | `localStorage.bmk_b2b_raw_key` — **plaintext** | `[read]` |
| Re-adoption check | must start with `bmk_spoof_` **and** match `api_key_prefix` | `[read]` |
| Companion secret | `tenant.webhook_secret`, shown as `slice(0,8) + "••••"` | `[read]` |

Reconciliation logic, verbatim:
```js
if(t.rawKey){ s(t.rawKey); localStorage.setItem("bmk_b2b_raw_key", t.rawKey) }
else {
  let e = localStorage.getItem("bmk_b2b_raw_key"),
      r = (t.tenant.api_key_prefix||"").replace(/\.+$/,"");
  e && e.startsWith("bmk_spoof_") && (!r || e.startsWith(r)) && s(e)
}
```

### Seller lock condition (frontend-visible)
```js
f(t.isLocked ?? (t.tenant.credits_balance ?? 0) <= 0)              // isLocked display
let e = !(t.isLocked ?? (t.tenant.credits_balance ?? 0) <= 0)
        && (t.tenant.credits_balance ?? 0) > 0
        && "none" !== t.tenant.tier;                                // tab access
ep = !!(!h && !u && o && (o.credits_balance ?? 0) > 0 && "none" !== o.tier)
```
So a seller needs **all three**: not locked, `credits_balance > 0`, and `tier !== "none"`.
Rotation is additionally blocked client-side with
`"Kunci API terkunci. Lakukan pembelian kredit terlebih dahulu."`
**Server-side enforcement is backend-only and was not verified.**

### The seller API's own auth scheme: not retrievable
The admin log filter reveals the B2B Mesh REST surface — `POST /download`, `GET /account/me`,
webhook callbacks, with `402 Payment Required` and `429 Rate / Limit` as real statuses `[read]`.
That API is **not** on `backend.blokmarket.store` (404 `[seen]`) and **not** in the engine's public
OpenAPI spec `[seen]`. Its host and auth header format appear **nowhere** in any collected
resource. I have not guessed them.

---

## 5. Spoofer engine — no auth at the HTTP layer

All four engine calls use **raw `fetch`**, so they carry **no** `Authorization` and **no**
`credentials`. Roblox credentials travel per-request instead:

| Credential | Transport | Where |
|---|---|---|
| Roblox OAuth bearer | query `?authorization=<token>` | `authorization` is a declared query param on `/api/download/{id}`, `/api/download/batch`, `/api/download/batch/async`, `/api/scan/place/{id}` `[seen in spec]` |
| `.ROBLOSECURITY` cookie | header `X-Roblox-Cookie` | `/api/download/batch/async` `[read]` |
| `.ROBLOSECURITY` cookie | query `?x-roblox-cookie=` | same routes `[seen in spec]` |
| Open Cloud key | JSON body `roblox_api_key` | `BatchDownloadRequest` `[seen in spec]` |

The `.ROBLOSECURITY` value comes from a **password-type input** persisted in plaintext to
`localStorage.bmk_spoofer_user_cookie` `[read]`:
```js
localStorage.setItem("bmk_spoofer_user_cookie", e.target.value)
```
UI text states: *"Your cookie is only used for the bypass request to Roblox"* — the code sends it
to `spoofer.blokmarket.store`, a **different origin** from the dashboard.

> **Query-parameter transport for a bearer token** means such tokens appear in access logs,
> browser history, and `Referer`. Frontend-observable; not exercised.

The engine also holds a Roblox session of its own — its spec describes
`/api/proxy/roblox-thumbnail-3d` and `/api/proxy/roblox-user-avatar-3d` as
*"using backend ROBLOSECURITY cookie to bypass CORS"* `[seen in spec]`.

---

## 6. Referral cookie

```js
(function(e){ if("u"<typeof document) return "";
  let t = `; ${document.cookie}`.split(`; ${e}=`);
  return 2===t.length && t.pop()?.split(";").shift() || "" })("bmk_ref")
```
Read from the `bmk_ref` cookie and forwarded as `&ref=` to `GET /api/auth/google/login`.
Set server-side; the setter is not in any client bundle.

---

## 7. Public (no authentication) — confirmed live

| Endpoint | Observed |
|---|---|
| `GET /api/product` | `200` `[seen]` |
| `GET /api/product/category` | `200` `[seen]` |
| `GET /api/upload/health` | `200 {"success":true,"data":{"status":"healthy","service":"bmk-upload","active_jobs":0}}` `[seen]` |
| `GET /api/audio/approved-count` | `200 {"success":true,"count":32958}` `[seen]` |
| `GET /api/audio/approved-daily-stats` | `200` `[seen]` |
| `GET engine /api/proxy/roblox-thumbnail` | `200` `[seen]` |
| `GET engine /openapi.json`, `/docs`, `/redoc` | `200` `[seen]` |

**Everything else returned `401 {"success":false,"message":"Unauthorized"}`**, except
`/api/auth/me` which returns **`{"success":false,"message":"No token"}`**.

---

## 8. CORS

| | `backend` | `engine` |
|---|---|---|
| ACAO, foreign origin | **absent** | **echoes the caller's Origin** |
| `access-control-allow-credentials` | `true` | `true` |
| `access-control-max-age` | — | `600` |
| Allowed headers | `Content-Type,Authorization,x-api-key,x-experience-id,Cookie` | `content-type,x-roblox-cookie` |

Backend responses are unreadable cross-origin from a third-party page; **engine** responses are
readable by any origin that satisfies the preflight. Both observed `[seen]`.

---

## 9. Complete `bmk_*` client storage inventory

Re-scanned across all 34 chunks (this supersedes the earlier 11-key list, which covered only
17 chunks):

| Key | Holds | Sensitivity |
|---|---|---|
| `bmk_token` | dashboard JWT/bearer | **high** |
| `bmk_b2b_raw_key` | full seller API key `bmk_spoof_…` | **high** |
| `bmk_spoofer_user_cookie` | Roblox `.ROBLOSECURITY` | **high — live session** |
| `bmk_ref` | referral code (also a cookie) | low |
| `bmk_spoofer_active_task` | `{task_id, parsedAssets, isSingle, batchId, startedAt}` | low |
| `bmk_spoofer_active_zip` / `_count` | `zip_download_url`, asset count | low |
| `bmk_spoofer_downloads` | per-asset status array | low |
| `bmk_spoofer_logs` | timestamped log lines | low |
| `bmk_audio_job` / `bmk_audio_history_id` / `bmk_audio_upload_success` | audio tool resume state | low |
| `bmk_upload` | upload tool state | low |
| `bmk_b2b_active_tab` | `topup`/`billing`/`usage` | low |
| `bmk_accent_color_v3` / `_secondary_v3` | UI accent (defaults `#beee11`, `#d4ff33`) | none |
| `bmk_dark_mode` / `bmk_sidebar_collapsed` | UI prefs | none |
| `bmk_welcome_modal_dismissed` | UI flag | none |
| `bmk_spoof_` | prefix match, not a key | — |

**All three high-sensitivity secrets sit in plaintext `localStorage` on the same origin.**
No XSS was sought or found; this is stated as an exposure-surface fact only.
