# Findings — customer.blokmarket.store/tools/bulk-spoofer

Analysis date: 2026-09-30 · Method: unauthenticated HTTP GET of public resources only.
No authentication, no credential use, no state-changing call, no exploitation was performed.

---

## Framework
**Next.js App Router (React 19) bundled with Turbopack**, statically prerendered
(`x-nextjs-prerender: 1`) and served from Vercel's edge cache. Tailwind CSS v4 with
`next/font` self-hosted woff2. Client state: **Jotai** with `atomWithStorage` persistence.
Animation: framer-motion. Toasts: sonner. ZIP packaging: JSZip.

The route ships an **empty `<body>`** — a pure client-rendered SPA shell. All analysis below
comes from the 32 JS chunks, 2 stylesheets and 16 media files it loads.

## Entry points
- Primary target: `https://customer.blokmarket.store/tools/bulk-spoofer` → **HTTP 200**, no redirect, no `Set-Cookie`
- 10 additional public routes fetched to complete the route→chunk map (all 200)
- Static runtime base: `/_next/static/chunks/`, fonts/media under `/_next/static/media/`

## Complete resource inventory — 50 files, all HTTP 200
| Class | Count | Bytes | Notes |
|---|---|---|---|
| JS chunks | 32 | 2,291 KB | 16 on `/tools/bulk-spoofer`, 16 more from sibling routes |
| CSS | 2 | 303 KB | `0un2imgmn0h_r.css` (Tailwind tokens) + `0sl2u3uj3fuv6.css` (fonts) |
| woff2 fonts | 10 | 195 KB | Inter, Poppins, Plus Jakarta Sans, Outfit, Geist Mono |
| PNG images | 6 | ~7.5 MB | `bmkico`, `bandingkan`, `coins60/150/350`, external `secur.png` |
| HTML documents | 11 | — | target + 10 sibling routes |

**404s recorded (negative findings):** `/_next/static/BUILD_ID`, `/_buildManifest.js`,
`/manifest.json`, `/robots.txt`, `/sitemap.xml`, `/api/health` on the frontend origin,
`/default-avatar.png` (referenced in code but dead), and all 34 `.map` probes.

## API inventory
**92 distinct API paths** across 4 origins (86 backend templates from the endpoint map, +1 undeclared `spoofer-check-cost`, 4 spoofer-engine, 1 audio download) — full table in `endpoints.md`.
- `backend.blokmarket.store/api/**` — 87 paths, all behind `Bearer bmk_token`
- `spoofer.blokmarket.store/api/**` — 4 paths, **no auth header**
- `audio.blokmarket.store/api/download/:id/:file` — 1 path
- third-party: PayPal SDK, `api.qrserver.com` (QR generation), i.ibb.co.com

Notable: `/api/auth/spoofer-check-cost` is called via `buildApiUrl()` but is **absent from the
app's own `apiEndpoints` map** — an undocumented/unregistered endpoint.

## Authentication mechanism
1. **Primary**: Google OAuth via popup → `postMessage` → JWT stored at `localStorage.bmk_token`
2. **Secondary**: Roblox OAuth via popup (`/api/auth/roblox/login?cf_token=…&token=…&from=…`)
   → stores `spoofer_state.roblox.{roblox_id, roblox_access_token, roblox_username, roblox_display_name, roblox_api_key}`
3. **Transport**: `Authorization: Bearer <bmk_token>` on every `apiFetch` call, plus
   `credentials: "include"`; transparent `POST /api/auth/refresh` on any `401`
4. **Gate before OAuth**: Cloudflare Turnstile token required client-side
   (`turnstileToken`, literal `"bypass_local"` on this page) — the widget itself is server-rendered
5. Referral code carried in a `bmk_ref` **cookie**, read and forwarded as `&ref=` to Google login

## Important frontend modules
| Turbopack ID | File | Contents |
|---|---|---|
| `4989` | `0vs148roxm~ft.js`, `11wojmndz1p1s.js` | `API_HOST`, `apiEndpoints`, `apiFetch`, `buildApiUrl` |
| `52285` | — | `userAtom`, `userLoadingAtom` |
| `93725` | `0vs148roxm~ft.js` | persisted Jotai atoms (accent/dark-mode/sidebar) |
| `64888` | `0k1tyysfi6yay.js` | Roblox OAuth connect button |
| `388` | `0jxi_hvhi.3ae.js` | Google OAuth connect button |
| `30972` | `0a8pu3n7fv_vz.js` | Roblox link/unlink + save-API-key modal |
| page default | `0nh-y8e1a0l~a.js` | the entire bulk-spoofer tool |

## Bulk-spoofer workflow
`parse LUA table/ID list (max 500)` → `POST /auth/spoofer-check-cost {asset_ids}`
→ `POST /auth/spoofer-deduct {asset_count, asset_ids}` →
`POST spoofer:/api/download/batch/async {assets, is_free}` (optional `X-Roblox-Cookie`) →
returns `task_id` → poll `GET spoofer:/api/task/:id/status` @1.5 s →
`PATCH /spoofer-jobs/:id` + `POST /auth/spoofer-state` →
optional serial `POST spoofer:/api/upload/batch {files, roblox_access_token, creator_id, creator_type}`.
Full detail and sequence diagram in `request-flow.md`.

The tool is an **asset-ID spoofing / "bypass" service**: it accepts arbitrary Roblox asset IDs
and yields a "New Spoofed ID" (`uploaded_asset_id`) plus a downloadable file, which it can then
push into a user's own Roblox experience via that user's access token. Its own UI markets
"bypass id spoof" and claims 100 % parity with a Discord "Sound Downloader" bot. The
transformation itself is entirely server-side at `spoofer.blokmarket.store` and was **not**
retrievable. Re-uploading assets under fresh IDs to defeat duplicate/ownership detection is
contrary to Roblox's Terms of Service, and where the source asset is third-party audio it
implies copyright infringement. That is a property of the target, not of this analysis.

## Dependencies (identified from bundle contents)
react / react-dom + scheduler · next (router, navigation, font, image) · jotai ·
framer-motion · sonner · lucide-react (icons inlined) · jszip · core-js (legacy polyfill) ·
Tailwind CSS v4. Third-party runtime: PayPal JS SDK, Cloudflare Turnstile, `api.qrserver.com`,
i.ibb.co.com, Google OAuth, Roblox OAuth/Open Cloud, Vercel toolbar.

## Exposed configuration
| Value | Where | Note |
|---|---|---|
| `https://backend.blokmarket.store` | `0vs148roxm~ft.js` | hardcoded API host |
| `https://spoofer.blokmarket.store` | `0nh-y8e1a0l~a.js` | hardcoded engine host |
| `https://audio.blokmarket.store` | `0vs148roxm~ft.js` | hardcoded media host |
| `http://localhost:3001` | `0vs148roxm~ft.js` | **dev fallback** for the API host, shipped to production |
| `NEXT_PUBLIC_HOST_API` | `0k1tyysfi6yay.js` | name only; value was inlined at build |
| PayPal **client** id `BAAE2aLMSjM7xZd0hscKvOCGclROj47Dcgx5OVRxz25I4FXB9o2CCw4NEHYV1oTRGP5RNMRbmjA7bnPWiM` | `0nh-y8e1a0l~a.js` | public by design |
| Google OAuth ref cookie `bmk_ref` | `0jxi_hvhi.3ae.js` | |
| Discord invite `PwsAuaR9Ur` | bundle | |
| Accent defaults `#beee11` / `#d4ff33` | `0vs148roxm~ft.js` | user-editable via localStorage |
| Full 92-path API surface + all client route names | bundles | complete route inventory |
| `localStorage` keys: `bmk_token`, `bmk_spoofer_user_cookie`, `bmk_spoofer_active_task`, `bmk_spoofer_active_zip`, `bmk_spoofer_active_zip_count`, `bmk_spoofer_downloads`, `bmk_spoofer_logs`, `bmk_accent_color_v3`, `bmk_accent_secondary_v3`, `bmk_dark_mode`, `bmk_sidebar_collapsed` | bundles | |

**No secrets retrieved.** No `.env`, no private key, no client secret, no database URL,
no Roblox/Open Cloud key, no Cloudflare Turnstile secret.

## Source-map availability
**None.** Zero `sourceMappingURL` comments across 32 JS + 2 CSS files; all 34 `.map` URLs → 404.
Original filenames, directory structure and symbol names are unrecoverable. Only Turbopack
numeric module IDs survive, and variable names are minified single letters.

## Client-side vs server-side
**Client-side (retrieved):** routing, all UI, LUA/ID input parsing, the 500-ID cap, filename
sanitisation, cost pre-check display, queue/progress rendering, log buffers, per-asset status
tables, JSZip packaging, localStorage persistence and resume-after-reload, OAuth popup
orchestration, admin/B2B/referral/payment dashboards, role-gated nav.

**Server-side (not exposed):** the spoof/bypass algorithm, Roblox asset fetching, re-upload
to Roblox, coin-balance authority, PayPal order capture, JWT signing/validation, RBAC
enforcement, audit persistence, Turnstile verification, and the entire body of
`backend.blokmarket.store` and `spoofer.blokmarket.store`.

## What could and could not be retrieved

**Retrieved (verified present on disk in `analysis/`):** target HTML + 10 sibling route HTML;
response headers; all 32 JS chunks; 2 CSS files; 10 woff2 fonts; 6 images; and, extracted from
them, the complete API route map, the authenticated `apiFetch` wrapper, the OAuth flows, the
entire bulk-spoofer client implementation, the route map, and the state/localStorage schema.

**Not retrievable:**
- Source maps, `BUILD_ID`, `_buildManifest.js`, `robots.txt`, `sitemap.xml`
- Any backend source, database schema, or server config
- The spoofing algorithm (server-side only)
- Request/response *bodies* of any API call — no authenticated call was made, so payload
  shapes are read from client call sites, and **response** shapes are only partially inferable
  from consumed fields
- Cloudflare Turnstile site key (widget rendered server-side; only the client-side token
  variable is visible)
- PayPal client secret, Google OAuth secret, Roblox Open Cloud credentials
- `default-avatar.png` (404 — dead reference in the bundle)

## Security observations (client-observable only)
1. **JWT in a URL** — `robloxLogin()?…&token=${bmk_token}` puts the bearer token in the popup
   URL, where it can land in history, referrers, and the OAuth provider's logs.
2. **`http://localhost:3001` shipped in the production bundle** as the API host fallback.
3. **`/auth/spoofer-check-cost` missing from the client endpoint map** — undeclared surface.
4. **Spoofer-engine calls are unauthenticated at the client layer** (no `Authorization`, no
   `credentials`). Whatever gates them is server-side and unverified by this analysis.
5. **Roblox `.ROBLOSECURITY` cookie pasted into a page input** and persisted in plaintext to
   `localStorage` (`bmk_spoofer_user_cookie`), then forwarded to `spoofer.blokmarket.store`.
   Any XSS on the dashboard origin would therefore yield a live Roblox session token.
6. **Client-only input limits** (500-ID cap, name sanitisation) — trivially bypassed by calling
   the engine directly; enforcement must be server-side.
7. **Complete API surface disclosed in the bundle** — the 92-path map gives an attacker a
   ready-made endpoint inventory; authorisation is the only control.
8. `default-avatar.png` 404 and an oversized ~7.5 MB of coin PNGs suggest unoptimised assets.

None of these were exploited or verified beyond what the public response shows.
