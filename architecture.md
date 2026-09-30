# Frontend Architecture

## Framework

| Item | Value | Evidence |
|---|---|---|
| Framework | **Next.js (App Router)**, React 19 | `x-nextjs-prerender: 1`, `vary: rsc, next-router-state-tree, …`, RSC flight payload (`self.__next_f.push`) |
| Bundler | **Turbopack** | `turbopack-0581j6ku1vu32.js`, `globalThis.TURBOPACK` array loader |
| Rendering | **Client-side SPA shell** | `<body>` ships empty; the only real content is a client segment root |
| Hosting | **Vercel** | `server: Vercel`, `x-vercel-cache: HIT`, `x-vercel-id: sin1::…` |
| CDN | Vercel Edge (`age: 248810`) | response `age` header, 2.9-day-old cached HTML |
| Language | Indonesian UI copy, English code identifiers | "Masuk", "Spoof Cost", `bypass_failed` |

`x-matched-path: /tools/bulk-spoofer` + `x-nextjs-prerender: 1` = the route is statically
prerendered at build time and served from cache. The page body is empty in the HTML, so all
real rendering is client-side after hydration.

## Deployment topology (4 origins)

```
customer.blokmarket.store    ← Next.js frontend (this analysis)
   │  fetch (no auth)             │  fetch + Bearer bmk_token
   ▼                               ▼
spoofer.blokmarket.store     backend.blokmarket.store
   │  (spoof engine)               │
   │                               ├──► audio.blokmarket.store  (file download host)
   │                               ├──► Roblox OAuth / Open Cloud
   │                               └──► PayPal, Cloudflare Turnstile, Google OAuth
```

## Chunk graph

Turbopack splits by route. The HTML for each route enumerates its own chunk set; there is no
`BUILD_ID` and no `_buildManifest.js` (both 404), so route→chunk mapping was derived by
diffing the 11 route HTML documents I fetched.

### Shared runtime / vendor (all routes)
| File | Size | Role |
|---|---|---|
| `turbopack-0581j6ku1vu32.js` | 11,052 | Turbopack module runtime; declares `otherChunks` + `runtimeModuleIds:[94553]` |
| `10~x95jhs6ns3.js` | 227,314 | **react-dom** + scheduler |
| `03~yq9q893hmn.js` | 112,594 | core-js / legacy polyfill bundle, loaded `noModule` |
| `0yb2wil16uz6h.js` | 5,587 | Next.js client bootstrap |
| `06kj~icw.pnsk.js` | 41,658 | react-server-dom / sonner toasts |
| `14d95v2q-d4b-.js` | 54,646 | Next router internals |
| `0pqt~8bl3ukh4.js` | 44,414 | Next navigation |
| `150e0tn55wgos.js` | 31,396 | Next navigation |
| `00nlt7x_9mi4z.js` | 136,649 | shared client vendor |

### Bulk-Spoofer route (`/tools/bulk-spoofer`, 16 chunks)
| File | Size | Role |
|---|---|---|
| **`0nh-y8e1a0l~a.js`** | **124,311** | **The bulk-spoofer page itself** — all spoofer UI, engine calls, polling, upload-to-Roblox flow, i18n strings, JSZip |
| `0a6h4o63da-vz.js` | 57,280 | **App shell** — sidebar/nav, holds every client route href |
| `0vs148roxm~ft.js` | 21,856 | **API client (`apiFetch`, `apiEndpoints`, `API_HOST`)**, Jotai persisted atoms, framer-motion helpers |
| `0k1tyysfi6yay.js` | 28,621 | **Roblox OAuth connect button** (popup + `postMessage`) |
| `0b1k3kf2xf2nj.js` | 21,639 | icon set (lucide-style inlined SVGs) |
| `0k1tyysfi6yay`→`09t2isllljna7.js` | 119,814 | framer-motion / layout primitives |
| `0vs148roxm~ft`→`0a6h4o63da-vz.js` | 57,280 | shell (dup route) |
| `0b1k3kf2xf2nj.js` … `03gck3l74sr~i.js` | 1,655–119,814 | remaining route chunks (per-asset thumbnail component, modals, comparison view) |

### Route-unique chunks discovered by cross-route diff
`/login` → `0jxi_hvhi.3ae.js` (Google OAuth button), `11wojmndz1p1s.js` (API client + Jotai + Google page),
`0a8pu3n7fv_vz.js` (Roblox-link modal — `robloxSaveApiKey`), `04-8vca-nl7ws.js` (register form, "Daftar")

## CSS
- `0un2imgmn0h_r.css` — 291,094 B — **Tailwind v4** design-token layer (129 CSS custom properties, `@property`-based `--color-*` in `oklab()`), 1 `@keyframes`
- `0sl2u3uj3fuv6.css` — 12,514 B — 5 `@font-face` blocks (Inter, Poppins, Plus Jakarta Sans, Outfit, Geist Mono), each with a `next/font` generated `* Fallback` metric-compatible face

## Fonts (10 × woff2, all 200 OK)
`1b99372b…`, `47fe1b7c…`, `4b766aa3…`, `797e433a…`, `829ba422…`, `83afe278…`, `8e6fa89a…`, `a218039a…`, `e2334d71…`, `fba5a26e…` — served from `/_next/static/media/`, preloaded with `crossorigin`.

## Static images
`/bmkico.png` (95,220 B, favicon+apple-touch), `/bandingkan.png` (1,672,320 B), `/coins60.png` (1,288,111 B),
`/coins150.png` (1,994,222 B), `/coins350.png` (2,403,354 B), plus external `secur.png` (i.ibb.co.com).
`/default-avatar.png` is referenced in code but **404s** — dead reference, confirmed.

## State management
**Jotai** with `atomWithStorage` persistence. Module `93725` in `0vs148roxm~ft.js`:
`userAtom` / `userLoadingAtom` (module `52285`), plus persisted UI atoms:
`accentColorAtom` → `bmk_accent_color_v3` (default `#beee11`),
`accent_secondary_v3` (default `#d4ff33`), `bmk_dark_mode` (`true`), `bmk_sidebar_collapsed`.

## Client routes (from nav config in `0a6h4o63da-vz.js`)
`/` · `/login` · `/profile` · `/tools/bulk-spoofer` · `/tools/audio-converter` ·
`/tools/bmk-upload` · `/tools/b2b-api` · `/tools/history?tab=spoofer` ·
`/donation/history` · `/roblox/experience` · `/roblox/license` · `/roblox/payment-history` ·
`/admin/users` · `/admin/experience` · `/admin/product` · `/admin/history` ·
`/admin/payment-history` · `/admin/spoofer-history`

## Client-side vs server-side split

**Client-side (retrieved source):** all UI, routing, form validation, input parsing (LUA table → ID list),
cost pre-check, queue progress rendering, log buffers, per-asset status tables, ZIP packaging (JSZip),
localStorage persistence/resume, Roblox OAuth popup orchestration, admin/B2B/referral dashboards.

**Server-side (NOT exposed):** the spoof/"bypass" transformation itself, asset fetching from Roblox,
re-upload to Roblox, coin balance authority, PayPal order capture, JWT signing/validation,
role enforcement, audit persistence, Cloudflare Turnstile verification.

## Source maps
**Not available.** No `sourceMappingURL` comment in any of the 32 chunks or 2 stylesheets, and
all 34 `.map` probes returned `404`. Original file names/paths cannot be recovered; module
boundaries are only observable as Turbopack numeric module IDs (e.g. `4989`, `52285`, `93725`).
