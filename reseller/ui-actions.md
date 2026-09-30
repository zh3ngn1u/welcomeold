# UI Actions → API Calls

Every row is a control that exists in the downloaded UI and the API call it triggers.
`[read]` = read from the bundle. No row was executed with credentials.

---

## B2B Mesh seller page — `/tools/b2b-api` (`0o45.cg_g4a77.js`)

| Control | Handler (minified) | Call | Notes |
|---|---|---|---|
| Page mount | `eU` | `GET /api/b2b/portal/status` | seeds tenant, lock, webhook URL, API key |
| Tab switch `topup`/`billing`/`usage` | inline `useEffect` | **no call** | `history.replaceState`, persists `bmk_b2b_active_tab` |
| "usage" tab activate | `useEffect([ef,ep])` | — | blocked → forced back to `topup` |
| Range `24 Jam`/`7 Hari`/`30 Hari` | `useEffect([em])` | — | re-labels to hours/days, then `e$` |
| Usage view | `e$` | `GET /api/b2b/portal/analytics?days={1\|7\|30}` | 24h→1, 7d→7, 30d→30 |
| Log list | `eF` | `GET /api/b2b/portal/logs?page=1&limit=50` | hardcoded page 1, limit 50 |
| Metric sub-tab `calls` | `eh/ey` state | — | no call |
| "Rotate / Perbarui Kunci" | `eK` | `POST /api/b2b/portal/key/rotate` | `confirm()` first; blocked if locked |
| Webhook URL input | `onChange` | — | local state only |
| "Simpan Webhook" | `eW` | `PUT /api/b2b/portal/webhook` | `{webhookUrl}` |
| Plan / pack card | `onClick` | — | sets `{itemId,itemType,title,credits,amountIdr,usdAmount}` into the checkout state, then redirects to `/login` if signed out |
| QRIS / PayPal checkout tab | layout `layoutId:"spooferCheckoutTab"` | via `eq` | `paymentMethod: "qris" \| "paypal"` |
| Copy API key | `onClick` | — | `navigator.clipboard`, 800 ms "copied" state |
| "Unduh Dokumentasi" | anchor | — | external link; **target not present as a literal in the bundle** |

---

## Admin B2B control — `/admin/spoofer-history` tab "B2B Seller API" (`0mhu~2w72ast2.js`)

| Control | Handler | Call | Notes |
|---|---|---|---|
| Tab mount | `ef` / `eg` / `ej` (3 × `useEffect`) | `GET /api/admin/b2b/overview?days` · `GET /api/admin/b2b/tenants?page&limit=15&search` · `GET /api/admin/b2b/logs?page&limit=20&endpoint&status&search` | all three fire on mount |
| Days `24 Jam`/`7 Hari`/`30 Hari` | `e` state | re-calls `b2bOverview(days)` | |
| Seller search box | `v` state | re-calls `b2bTenants` | omitted from query when blank |
| Endpoint filter dropdown | `R` array | re-calls `b2bLogs` | `""`,`download`,`account`,`webhook` |
| Status filter dropdown | `U` array | re-calls `b2bLogs` | `""`,`2xx`,`4xx`,`5xx`,`401`,`402`,`429` |
| "Semua Status HTTP" etc. | `<option>` | — | |
| Pagination `‹ 1 2 3 … ›` | `en` window function | re-calls with new page | window of ±2, collapses to 5 around the ends |
| "Sesuaikan Saldo Kredit" | opens modal → `eN` | `POST /api/admin/b2b/tenants/:id/credits` | `{amount, action}`; `action` ∈ `add`\|`deduct`\|`set` |
| Amount input | `ed` state | — | `parseInt`; `NaN`/`<0` blocked |
| Action select | `ex` state | — | default `"add"` |
| "Bekukan"/"Aktifkan" API Key | `ev` | `POST /api/admin/b2b/tenants/:id/toggle-status` | `confirm()`; no body |
| "Batal" | modal close | — | |

---

## Admin spoofer audit — tab "Web Spoofer Jobs" (same chunk)

| Control | Handler | Call | Notes |
|---|---|---|---|
| Tab mount / page / filter change | `er` | `GET /api/spoofer-jobs/admin/all?page&limit=10[&status][&assetType][&search]` | query built with `URLSearchParams`, appended to the declared path |
| Status pills `all`/`completed`/`partial`/`bypass_completed`/`failed` | inline `onClick` | re-calls `er` | |
| Asset-type dropdown | dropdown array | re-calls `er` | `all`,`Audio`,`Animation`,`Decal`,… |
| Search box | `L` state | re-calls `er` (debounced via `H(1)`) | |
| Job row click / chevron | `ee` | lazy `GET /api/spoofer-jobs/:id` | per-row `loading` map; injects `data.logs[]` |
| ZIP download cell | anchor | engine/host ZIP URL from `zip_url` | label "Unduh ZIP" |
| Pagination | `Y`/`O` | re-calls `er` | |

---

## Bulk spoofer page — `/tools/bulk-spoofer` (`0nh-y8e1a0l~a.js`)

| Control | Handler | Call | Notes |
|---|---|---|---|
| ID textarea paste | `onChange` → `sQ(eg)` | — | 800 ms debounce; clipboard-read button exists |
| Submit / process | `s2` | parse → `POST /api/auth/spoofer-check-cost` | `0` → "Invalid input format!…"; `>500` → "Maximum of 500 IDs…" |
| "Free Spoof" button | `s5` (via `s2`) | `POST engine /api/download/batch/async` | `is_free=true` ⇒ **no** `X-Roblox-Cookie` |
| Pay-with-coins button | `s4` | `POST /api/auth/spoofer-deduct` | then `s5` |
| "Buy coins" / QRIS / PayPal | `s3` | `POST /api/payment/create-coin-invoice` → `paypal/create-coin-order` → `paypal/capture-coin-order` | `paymentMethod:"qris"` |
| `.ROBLOSECURITY` password input | `onChange` | — | plaintext → `localStorage.bmk_spoofer_user_cookie` |
| Roblox "Connect" | `0k1tyysfi6yay.js` popup | `GET /api/auth/roblox/login?cf_token&token&from=spoofer&t` | requires Turnstile first |
| Save Open Cloud key modal | `q` | `POST /api/auth/roblox/save-api-key` | `{apiKey, creatorId, creatorType, from:"spoofer"}` |
| Unlink Roblox | `$` | `POST /api/auth/roblox/unlink` | `{from:"spoofer"}` then `?refresh=<ts>` reload |
| "Compare Spoof" | `eF`/custom event | — | opens the comparison modal, loads `/bandingkan.png` |
| Upload-target radio (User/Group) | `eL` state | — | `creator_type = id ? "Group" : "User"` |
| "Start upload" | `x`/loop | `POST engine /api/upload/batch` | one request per asset, serial |
| Progress rows | `r[e.id]` map | — | per-asset status line into `bmk_spoofer_logs` |
| "Unduh ZIP" | `sZ` | `fetch(zip_download_url)` → `.blob()` | forced download via object URL |
| "Clear logs" | inline | — | `localStorage.removeItem("bmk_spoofer_logs")` |
| History icon | `window.location.href="/tools/history?tab=spoofer"` | — | |
| Resize / tab refocus | `visibilitychange`, `focus` | `GET engine /api/task/:id/status` | queue-position refresh only |

---

## App shell (`0a6h4o63da-vz.js`) & account

| Control | Call |
|---|---|
| Logout button | `localStorage.removeItem("bmk_token")` → `POST /api/auth/logout?t=<ts>` (`credentials:"include"`) → `/login` |
| Profile menu | `/profile` |
| Sidebar collapse | `localStorage` only, no call |
| Accent colour picker | `localStorage` only, no call |

## Login page (`0jxi_hvhi.3ae.js`, `0a8pu3n7fv_vz.js`, `04-8vca-nl7ws.js`)

| Control | Call |
|---|---|
| "Continue with Google" | popup `GET /api/auth/google/login?prompt=select_account&cf_token&ref&t` |
| "Connect Roblox" | popup `GET /api/auth/roblox/login?cf_token&token&from&t` |
| Roblox link modal | `POST /api/auth/roblox/save-api-key`, `POST /api/auth/roblox/unlink` |
| **Email/password form** | **NO `apiFetch` call site found in any downloaded chunk.** `/api/auth/login` and `/api/auth/register` are declared in the map, but the form either posts via a mechanism not present in the collected chunks or is rendered by a chunk not reached. **NOT CONFIRMED** — do not assume a payload shape. |

---

## Global on-mount call (every authenticated page)

| Trigger | Call |
|---|---|
| Any page mount | `GET /api/auth/me` → `userAtom`; the entire UI gates on it |
| Spoofer page, after Turnstile success | `GET /api/auth/me` then `setUser(s.data)` |
