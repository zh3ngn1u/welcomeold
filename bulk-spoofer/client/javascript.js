/**
 * Bulk Spoofer reference client — CONFIRMED functionality only.
 *
 * Every function here maps to a call site in analysis/js/0nh-y8e1a0l~a.js or to a path
 * published in analysis/api/spoofer-engine-openapi.json. No endpoint is invented.
 * Where the vendor's behaviour is a bug, this client does the sane thing and says so.
 *
 * ── SECURITY ─────────────────────────────────────────────────────────────────────
 * Run this SERVER-SIDE. It carries credentials that must never reach a browser:
 *   • BMK_TOKEN     dashboard bearer  (Authorization: Bearer …)
 *   • ROBLOX_COOKIE a live .ROBLOSECURITY session
 *   • ROBLOX_TOKEN  a Roblox OAuth access token
 * The upstream page keeps all three in localStorage in plaintext. Do not copy that —
 * see ../my-web-architecture.md.
 * ─────────────────────────────────────────────────────────────────────────────────
 *
 * No source maps were published, so the original function names are minified and
 * unrecoverable. Names below are ours; the upstream minified id is quoted in comments.
 *
 * Requires Node 18+ (global fetch, Blob, ReadableStream). No dependencies.
 */

'use strict';

const BACKEND = 'https://backend.blokmarket.store';
const ENGINE  = 'https://spoofer.blokmarket.store';

/* ── Confirmed limits, lifted verbatim from the bundle ────────────────────────── */

const MAX_IDS_PER_RUN = 500;      // if (e.length > 500) → toast "Maximum of 500 IDs…"
const ID_PATTERN      = /\d{9,18}/;  // 9–18 digits; anything shorter is SILENTLY DROPPED
const POLL_INTERVAL_MS   = 1500;  // setInterval(n, 1500)
const PAYMENT_POLL_MS    = 3000;  // setInterval(async () => {…}, 3e3)
const CLIPBOARD_AUTOPASTE_MS = 800; // setTimeout(…, 800)
const LOG_TAIL_LIMIT     = 500;   // logs.slice(-500) before every PATCH
const UPLOAD_REFRESH_TRIGGERS = [401, 403];

/* ─────────────────────────── error helpers ─────────────────────────── */

/** Engine (FastAPI) `detail` is a string OR an array of Pydantic objects. Handle both. */
function engineErrorText(body, fallback = 'Engine error') {
  const d = body && body.detail;
  if (typeof d === 'string' && d) return d;
  if (Array.isArray(d) && d.length) {
    return d.map((e) => `${(e.loc || []).join('.') || 'body'}: ${e.msg || e.type}`).join('; ');
  }
  return fallback;
}

/** Backend (Express-style) is { success:false, message }. Some routes put the payload at top level. */
function backendErrorText(body, fallback = 'Backend error') {
  if (body && body.message) return body.message;
  return fallback;
}

class ApiError extends Error {
  constructor(message, { status = 0, body = null, url = '' } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
    this.url = url;
  }
}

/* ─────────────────────────── transport ─────────────────────────── */

/**
 * Backend call — mirrors upstream `apiFetch` (analysis/js/0vs148roxm~ft.js, module 4989).
 *
 * Differences from upstream, both deliberate bug fixes:
 *   1. Upstream returns a SYNTHETIC {ok:false,status:0} on a network error instead of
 *      throwing, so every try/catch around it is dead code. We throw ApiError.
 *   2. Upstream builds the Authorization header once, then on 401 deletes the token from
 *      localStorage and "retries" the request with the SAME dead header. It cannot succeed.
 *      We rebuild the header after refreshing.
 *
 * Note: upstream's refresh endpoint (`POST /api/auth/refresh`) returns 404 in production,
 * so in practice every expiry is a hard logout. See ../error-handling.md defect #2.
 */
async function backendFetch(method, path, { body, query, token, timeoutMs = 30_000 } = {}) {
  const url = new URL(path.startsWith('/') ? path : `/api/${path}`, BACKEND);
  for (const [k, v] of Object.entries(query || {})) {
    if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
  }

  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  let res;
  try {
    res = await fetch(url, {
      method,
      headers,
      credentials: 'include',            // upstream always sets this
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (cause) {
    // Upstream calls this "Connection failed". Same meaning, but we surface it as a throw.
    throw new ApiError(`Connection failed to: ${url.href}`, { status: 0, url: url.href });
  }

  const text = await res.text();
  let parsed = null;
  if (text) { try { parsed = JSON.parse(text); } catch { parsed = { raw: text }; } }

  if (!res.ok) {
    throw new ApiError(backendErrorText(parsed, `HTTP ${res.status}`), {
      status: res.status, body: parsed, url: url.href,
    });
  }
  return parsed;
}

/**
 * Engine call — NO Authorization header, NO cookies. Upstream calls this origin with bare
 * fetch and sends exactly one non-standard header, X-Roblox-Cookie, and only when is_free
 * is false. See ../authentication.md §3.
 */
async function engineFetch(method, path, { body, robloxCookie, timeoutMs = 60_000 } = {}) {
  const url = new URL(path, ENGINE);
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (robloxCookie) headers['X-Roblox-Cookie'] = robloxCookie;  // ONLY for paid runs

  let res;
  try {
    res = await fetch(url, {
      method, headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (cause) {
    throw new ApiError(`Connection failed to: ${url.href}`, { status: 0, url: url.href });
  }

  const text = await res.text();
  let parsed = null;
  if (text) { try { parsed = JSON.parse(text); } catch { parsed = { raw: text }; } }

  if (!res.ok) {
    throw new ApiError(engineErrorText(parsed, `HTTP ${res.status}`), {
      status: res.status, body: parsed, url: url.href,
    });
  }
  return parsed;
}

/* ─────────────────────────── input parsing ─────────────────────────── */

/** Upstream `s0`: (e) => e.replace(/[\\\/:*?"<>|]/g, "_").trim() */
function sanitiseFileName(name) {
  return String(name).replace(/[\\/:*?"<>|]/g, '_').trim();
}

/**
 * Upstream `sQ`. Two passes over the raw textarea, deduped by id, first occurrence wins.
 *
 * Pass 1 — LUA table: every /\{([^{}]+)\}/ block.
 * Pass 2 — bare lines: split("\n"), one id per line.
 *
 * ID is the FIRST /\d{9,18}/ in the chunk and is parseInt'd to a Number.
 * If nothing matches, that line is skipped SILENTLY — it is not an error. Upstream has no
 * per-line diagnostics; see ../error-handling.md defect #9 for why you should add them.
 */
function parseAssets(raw) {
  const out = [];
  const seen = new Set();

  // ---- Pass 1: { ... } blocks -------------------------------------------------
  const blocks = /\{([^{}]+)\}/g;
  let m;
  while ((m = blocks.exec(raw)) !== null) {
    const chunk = m[1];
    const idHit = chunk.match(ID_PATTERN);
    if (!idHit) continue;

    const id = parseInt(idHit[0], 10);
    let name = `Asset #${id}`;

    // a) Name="x" / name='x' / Name : 'x'   (case-insensitive)
    const named = chunk.match(/(?:['"]?Name['"]?|['"]?name['"]?)\s*[=:]\s*["']([^"']+)["']/i);
    // b) "x", 123456
    const leading = chunk.match(/^\s*["']([^"']+)["']\s*,\s*\d+/);
    if (named)      name = named[1].trim();
    else if (leading) name = leading[1].trim();
    else {
      // c) first quoted string that is not an rbxassetid URL and not a bare number
      const quoted = chunk.match(/["']([^"']+)["']/g) || [];
      for (const q of quoted) {
        const v = q.slice(1, -1).trim();
        if (v && !v.includes('rbxassetid') && !/^\d+$/.test(v)) { name = v; break; }
      }
    }

    if (!seen.has(id)) { out.push({ id, custom_name: name }); seen.add(id); }
  }

  // ---- Pass 2: one id per line ----------------------------------------------
  for (const rawLine of raw.split('\n')) {
    const line = rawLine.trim();
    if (!line) continue;

    const idHit = line.match(ID_PATTERN);
    if (!idHit) continue;                       // silently ignored

    const id = parseInt(idHit[0], 10);
    if (seen.has(id)) continue;

    let name = `Asset #${id}`;
    // a) {"Name", 123456}
    const brace = line.match(/\{\s*["']([^"']+)["']\s*,\s*\d+\s*\}/);
    // b) ["Name"] = …  or  ["Name"]: …
    const indexed = line.match(/\[\s*["']([^"']+)["']\s*\]\s*[=:]/);
    // c) identifier = … , excluding the obvious id keys
    const ident = line.match(/^([a-zA-Z_][a-zA-Z0-9_\s-]*)\s*[=:]/);

    if (brace) name = brace[1].trim();
    else if (indexed) name = indexed[1].trim();
    else if (ident && !['id', 'assetid', 'asset_id'].includes(ident[1].trim().toLowerCase())) {
      name = ident[1].trim();
    } else {
      const quoted = line.match(/["']([^"']+)["']/);
      if (quoted && !quoted[1].includes('rbxassetid') && !/^\d+$/.test(quoted[1])) {
        name = quoted[1].trim();
      }
    }

    out.push({ id, custom_name: name });
    seen.add(id);
  }

  return out;
}

/** Upstream `s2` guard order — empty first, then the 500 cap. Both are pre-network. */
function validateAssets(assets) {
  if (!assets.length) {
    throw new ApiError('Invalid input format! Please enter a LUA table or list of IDs.', { status: 400 });
  }
  if (assets.length > MAX_IDS_PER_RUN) {
    throw new ApiError(`Maximum of ${MAX_IDS_PER_RUN} IDs in a single bulk process!`, { status: 400 });
  }
  return assets;
}

/* ─────────────────────── backend: session & coins ─────────────────────── */

/** GET /api/auth/me — 401 body is the odd one out: {"success":false,"message":"No token"}. */
function getAuthMe({ token } = {}) {
  return backendFetch('GET', '/api/auth/me', { token });
}

/** GET /api/auth/spoofer-state → { success, data:{ coins, history[] } } */
function getCoinState({ token } = {}) {
  return backendFetch('GET', '/api/auth/spoofer-state', { token });
}

/** POST /api/auth/spoofer-state {task_id} — reconciling balance AFTER a job (upstream `sz`). */
function reconcileCoinState(taskId, { token } = {}) {
  return backendFetch('POST', '/api/auth/spoofer-state', { token, body: { task_id: taskId } });
}

/**
 * POST /api/auth/spoofer-check-cost {asset_ids:[…]}
 *
 * NOT present in the app's apiEndpoints map — upstream builds it with
 * buildApiUrl("/auth/spoofer-check-cost"). An undeclared surface; documented in
 * ../endpoints.md note under row #4.
 *
 * The cost is SERVER-AUTHORITATIVE. There is no client-side tier table.
 * Returns { success, cost, has_ugc, message }.
 */
function checkCost(assetIds, { token } = {}) {
  return backendFetch('POST', '/api/auth/spoofer-check-cost', {
    token,
    body: { asset_ids: assetIds.map(String) },
  });
}

/**
 * POST /api/auth/spoofer-deduct {asset_count, asset_ids:[…]} — upstream `s4`.
 * Spends real balance. Returns { success, coins } or { success, newCoins }.
 *
 * WARNING: upstream charges at SUBMIT time, before any asset is known to succeed, and
 * there is no refund endpoint anywhere in the bundle. See ../bulk-flow.md §6.
 */
function deductCoins(assets, { token } = {}) {
  return backendFetch('POST', '/api/auth/spoofer-deduct', {
    token,
    body: { asset_count: assets.length, asset_ids: assets.map((a) => String(a.id)) },
  });
}

/** POST /api/auth/roblox/refresh {from:"spoofer"} → { success, robloxAccessToken }. */
function refreshRobloxToken({ token } = {}) {
  return backendFetch('POST', '/api/auth/roblox/refresh', {
    token, body: { from: 'spoofer' },
  });
}

/** GET /api/auth/roblox/groups → { success, data:[…] } — the group picker. */
function getRobloxGroups({ token } = {}) {
  return backendFetch('GET', '/api/auth/roblox/groups', { token });
}

/* ─────────────────── backend: audit job record (paid runs only) ─────────────────── */

/**
 * POST /api/spoofer-jobs — upstream writes this ONLY for paid runs. A free run creates
 * no audit row at all, so free usage is invisible server-side.
 */
function createJobRecord(job, { token } = {}) {
  return backendFetch('POST', '/api/spoofer-jobs', { token, body: job });
}

/**
 * PATCH /api/spoofer-jobs/:id — upstream `sX`/`sY`. Called on EVERY asset status change
 * and again at terminal. Upstream slices logs to the last 500 (LOG_TAIL_LIMIT).
 *
 * Upstream swallows failures here (`console.error` only), so an audit row can silently
 * diverge from reality. We let the error propagate; catch it yourself if best-effort.
 */
async function patchJobRecord(jobId, patch, { token } = {}) {
  const body = { ...patch };
  if (Array.isArray(body.logs)) body.logs = body.logs.slice(-LOG_TAIL_LIMIT);
  return backendFetch('PATCH', `/api/spoofer-jobs/${jobId}`, { token, body });
}

/* ─────────────────────────── engine: the spoof job ─────────────────────────── */

/**
 * POST /api/download/batch/async  — upstream `s5`.
 *
 * Body is literally { assets:[{id,custom_name}], is_free:bool }. No place_id, no
 * universeId, no is_private, no type, no mode — private assets are NOT a mode of this
 * endpoint. See ../endpoints.md, final note.
 *
 * robloxCookie is sent ONLY when isFree === false (upstream: !s && sg && sg.trim()).
 * Returns { task_id }.
 */
function submitSpoofJob(assets, { isFree = false, robloxCookie } = {}) {
  return engineFetch('POST', '/api/download/batch/async', {
    robloxCookie: isFree ? undefined : robloxCookie,
    body: { assets: assets.map((a) => ({ id: a.id, custom_name: a.custom_name })), is_free: !!isFree },
  });
}

/**
 * GET /api/task/:taskId/status — the poll target.
 * Returns { status, queue_position, total_queue, assets[], zip_download_url }.
 *
 * A 404 here means "Task not found." Upstream treats it as terminal and deletes the task
 * from localStorage; we surface it as an ApiError so you can decide (see
 * ../error-handling.md defect #5).
 */
function getTaskStatus(taskId) {
  return engineFetch('GET', `/api/task/${encodeURIComponent(taskId)}/status`);
}

/** True when the status payload has produced everything the user can act on. */
function isTaskSettled(payload) {
  return !!(payload && (payload.zip_download_url || (payload.assets || []).some((a) => a.asset_type === 'Place')));
}

/**
 * Poll a task every POLL_INTERVAL_MS until it settles or opts.timeoutMs elapses.
 *
 * Deliberate differences from upstream, which has neither bound:
 *   • an overall timeout, so a permanently-200-but-never-settling endpoint cannot spin forever
 *   • backoff is intentionally NOT added — 1500 ms matches upstream. Add it if you want.
 *
 * onUpdate(payload, previous) is called after every successful read, including repeats,
 * which is what drives a progress UI.
 */
async function pollTask(taskId, { onUpdate, signal, timeoutMs = 30 * 60_000, intervalMs = POLL_INTERVAL_MS } = {}) {
  const deadline = Date.now() + timeoutMs;
  let previous = null;

  for (;;) {
    if (signal && signal.aborted) throw new ApiError('Polling aborted', { status: 0 });

    const payload = await getTaskStatus(taskId);
    if (onUpdate) onUpdate(payload, previous);
    previous = payload;

    if (isTaskSettled(payload)) return payload;
    if (Date.now() >= deadline) {
      throw new ApiError('Timed out waiting for task to settle', { status: 0, body: payload });
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

/* ─────────────────────────── download ─────────────────────────── */

/**
 * Upstream `s0`:
 *   basename = metadata?.name || custom_name
 *   ext      = file_name ? "." + extname(file_name) : fallback
 *   then sanitised
 *
 * There is NO Content-Disposition parsing and NO signed-URL logic anywhere in the page.
 */
function buildFileName(asset, { fallbackExt = '' } = {}) {
  const base = (asset.metadata && asset.metadata.name) || asset.custom_name || '';
  const ext = asset.file_name ? `.${String(asset.file_name).split('.').pop()}` : fallbackExt;
  return `${sanitiseFileName(base)}${ext}`;
}

/**
 * Download a URL the way upstream `sZ` does — fetch → blob → object URL → <a download>.
 *
 * Prefer streamToFile() for anything large: upstream's res.blob() buffers the ENTIRE file
 * in memory, so a 500-asset ZIP is fully resident. See ../download-flow.md.
 *
 * In Node, pass a `sink` to write bytes to disk; in a browser omit it and the Blob is
 * returned for the caller to save.
 */
async function downloadAsset(url, filename, { sink } = {}) {
  const res = await fetch(url);                       // no Authorization, no credentials
  if (!res.ok) throw new ApiError(`Download failed: HTTP ${res.status}`, { status: res.status, url });

  if (sink) {
    const { writeFile } = require('node:fs/promises');
    const chunks = [];
    for await (const chunk of res.body) chunks.push(Buffer.from(chunk));
    await writeFile(sink, Buffer.concat(chunks));
    return sink;
  }
  return { filename, blob: await res.blob() };
}

/** Terminal-result summary, reproducing the upstream branching in workflow.md §1. */
function describeOutcome(status) {
  const assets = status.assets || [];
  const places = assets.filter((a) => a.asset_type === 'Place');
  const success = assets.filter((a) => a.status === 'success');
  const failed  = assets.filter((a) => a.status === 'failed');

  if (places.length) return { kind: 'place',   message: 'Bypass feature for Place/Game is currently unavailable.' };
  if (status.zip_download_url) return { kind: 'zip', message: `Successfully downloaded ${success.length} files! ZIP is ready.`, zipUrl: status.zip_download_url };
  if (!success.length) return { kind: 'empty', message: 'Asset might be private or ID is invalid.' };
  return { kind: 'done', message: 'Assets successfully spoofed!' };
}

/* ─────────────── engine: upload results into a Roblox experience ─────────────── */

/** POST /api/upload/batch — ONE asset per request; upstream is strictly serial. */
function uploadOne(asset, { robloxAccessToken, creatorId, creatorType } = {}) {
  return engineFetch('POST', '/api/upload/batch', {
    body: {
      files: [asset],
      roblox_access_token: robloxAccessToken,
      creator_id: String(creatorId),
      creator_type: creatorType,        // "User" | "Group"
    },
  });
}

function needsTokenRefresh(status, result) {
  if (status === 401 || status === 403) return true;
  const err = result && result.error;
  if (!err) return false;
  const e = String(err).toLowerCase();
  return e.includes('401') || e.includes('invalid token') || e.includes('token');
}

/**
 * Upload every successful asset, SERIALLY, with upstream's silent-refresh-and-retry.
 *
 * Upstream behaviour reproduced:
 *   • one request per asset, strictly sequential — 500 assets = 500 round-trips
 *   • on 401/403/"invalid token": refresh once, then retry THAT asset
 *   • the refresh is single-flight (memoised promise) so a burst triggers only one refresh
 *   • if the refresh itself fails: abort everything remaining, mark them
 *     upload_status:"failed" / upload_error:"Aborted"
 *
 * Unlike upstream this never throws — it returns a summary, so a partial upload is a
 * value, not an exception.
 */
async function uploadBatchToRoblox(assets, { robloxAccessToken, creatorId, creatorType, token, onProgress } = {}) {
  let accessToken = robloxAccessToken;
  let inFlightRefresh = null;
  let success = 0;
  let failed = 0;
  let aborted = false;

  for (const asset of assets) {
    if (aborted) {
      asset.upload_status = 'failed';
      asset.upload_error = 'Aborted';
      failed++;
      continue;
    }

    let result;
    try {
      result = await uploadOne(asset, { robloxAccessToken: accessToken, creatorId, creatorType });
      asset.uploaded_asset_id = result.asset_id;
      asset.upload_status = result.success ? 'success' : 'failed';
      if (result.success) success++; else failed++;
    } catch (err) {
      const body = err.body && err.body.results ? err.body.results[0] : null;
      if (!needsTokenRefresh(err.status, body)) {
        asset.upload_status = 'failed';
        asset.upload_error = `HTTP Error: ${err.status}`;
        failed++;
        if (onProgress) onProgress(asset, { success, failed });
        continue;
      }

      // single-flight: at most one refresh in the air at a time
      if (!inFlightRefresh) {
        inFlightRefresh = refreshRobloxToken({ token }).finally(() => { inFlightRefresh = null; });
      }
      try {
        const refreshed = await inFlightRefresh;
        accessToken = refreshed.robloxAccessToken;
        result = await uploadOne(asset, { robloxAccessToken: accessToken, creatorId, creatorType });
        asset.uploaded_asset_id = result.asset_id;
        asset.upload_status = result.success ? 'success' : 'failed';
        if (result.success) success++; else failed++;
      } catch (retryErr) {
        aborted = true;
        asset.upload_status = 'failed';
        asset.upload_error = 'Aborted';
        failed++;
        if (onProgress) onProgress(asset, { success, failed, aborted });
        break;
      }
    }
    if (onProgress) onProgress(asset, { success, failed });
  }

  return {
    success, failed, aborted, robloxAccessToken: accessToken,
    summary: `Upload process completed. Success: ${success}, Failed: ${failed}`,
  };
}

/* ─────────────────────────── thumbnails ─────────────────────────── */

/**
 * GET /api/proxy/roblox-thumbnail?assetIds=…&size=…&format=Png&isCircular=false
 * Returns { data:[{ targetId, state, imageUrl, version }] }.
 *
 * `state` may be "Blocked" and the URL still resolves — do not gate the UI on state.
 * assetIds is a comma-joined list; upstream fetches 150x150 for rows and 420x420 for
 * the modal.
 */
function getThumbnail(assetIds, { size = '150x150', format = 'Png', isCircular = false } = {}) {
  const ids = (Array.isArray(assetIds) ? assetIds : [assetIds]).join(',');
  return engineFetch('GET', '/api/proxy/roblox-thumbnail', {
    query: { assetIds: ids, size, format, isCircular: String(isCircular) },
  });
}

/* ─────────────────────────── coins & payment ─────────────────────────── */

/**
 * POST /api/payment/create-coin-invoice {coins, paymentMethod:"qris"}
 * → { success, qrString, trxId, totalTransfer, isCoinTopUp, coins }
 *
 * The QR image is rendered CLIENT-SIDE by a third party:
 *   https://api.qrserver.com/v1/create-qr-code/?data=<encodeURIComponent(qrString)>&size=600x600&…
 * That means the payment string is sent to an external host. Do not do this in a
 * production app without saying so to your users.
 */
function createCoinInvoice({ coins, paymentMethod = 'qris' }) {
  return backendFetch('POST', '/api/payment/create-coin-invoice', { body: { coins, paymentMethod } });
}

/** GET /api/payment/check/:trxId → { success, status: SUCCESS|EXPIRED|CANCELED, coins } */
function checkPayment(trxId) {
  return backendFetch('GET', `/api/payment/check/${encodeURIComponent(trxId)}`);
}

/** Poll a QRIS invoice every PAYMENT_POLL_MS until it is terminal. */
async function pollPayment(trxId, { intervalMs = PAYMENT_POLL_MS, timeoutMs = 15 * 60_000, onTick } = {}) {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const res = await checkPayment(trxId);
    if (onTick) onTick(res);
    if (res.status === 'SUCCESS') return res;
    if (res.status === 'EXPIRED' || res.status === 'CANCELED') {
      throw new ApiError('Payment expired or canceled', { status: res.status, body: res });
    }
    if (Date.now() >= deadline) {
      throw new ApiError('Payment polling timed out', { status: 0, body: res });
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

/** POST /api/payment/paypal/create-coin-order {coins} */
function createPayPalCoinOrder({ coins }) {
  return backendFetch('POST', '/api/payment/paypal/create-coin-order', { body: { coins } });
}

/** POST /api/payment/paypal/capture-coin-order {paypalOrderId, orderId, coins} */
function capturePayPalCoinOrder({ paypalOrderId, orderId, coins }) {
  return backendFetch('POST', '/api/payment/paypal/capture-coin-order', {
    body: { paypalOrderId, orderId, coins },
  });
}

/* ─────────────────────────── end-to-end ─────────────────────────── */

/**
 * The whole confirmed free-spoof workflow: parse → validate → submit → poll → settle.
 * This is the "Free Spoof" path — no coins, no audit row, never sends X-Roblox-Cookie.
 */
async function runFreeSpoof(rawInput, { onProgress, signal } = {}) {
  const assets = validateAssets(parseAssets(rawInput));
  const { task_id: taskId } = await submitSpoofJob(assets, { isFree: true });
  const status = await pollTask(taskId, { onUpdate: onProgress, signal });
  return { taskId, assets, status, outcome: describeOutcome(status) };
}

/**
 * The whole confirmed paid-spoof workflow.
 *
 * Order matters and is not negotiable, because it mirrors upstream:
 *   1. check cost        (server-authoritative)
 *   2. deduct coins      ← MONEY MOVES HERE, before any asset is attempted
 *   3. create audit row  (upstream wraps 2+3 in one function and skips both for admin/owner)
 *   4. submit + poll
 *   5. reconcile balance
 *   6. PATCH the audit row on every change and at terminal
 *
 * If you re-implement, add a refund path — upstream has none.
 */
async function runPaidSpoof(rawInput, { token, robloxCookie, onProgress, signal } = {}) {
  const assets = validateAssets(parseAssets(rawInput));
  const ids = assets.map((a) => String(a.id));

  const quote = await checkCost(ids, { token });
  if (!quote.success) throw new ApiError(quote.message || 'Failed to calculate coin cost.', { status: 400, body: quote });

  const state = await getCoinState({ token });
  const coins = state && state.data ? state.data.coins : 0;
  if (typeof coins === 'number' && coins < quote.cost) {
    throw new ApiError(`Insufficient Coins (-${quote.cost - coins})`, { status: 402, body: quote });
  }

  const deduction = await deductCoins(assets, { token });

  const { task_id: taskId } = await submitSpoofJob(assets, { isFree: false, robloxCookie });

  await createJobRecord({
    job_id: taskId,
    status: 'pending',
    total_assets: assets.length,
    success_count: 0,
    failed_count: 0,
    asset_breakdown: {},
  }, { token });

  const logs = [];
  const status = await pollTask(taskId, {
    signal,
    onUpdate: (payload, previous) => {
      const counts = { success: 0, failed: 0 };
      const breakdown = {};
      for (const a of payload.assets || []) {
        counts[a.status === 'success' ? 'success' : 'failed']++;
        const type = a.asset_type || 'Unknown';
        breakdown[type] = breakdown[type] || { success: 0, failed: 0 };
        breakdown[type][a.status === 'success' ? 'success' : 'failed']++;
      }
      if (onProgress) onProgress(payload, counts);

      if (!previous) return;
      for (const a of payload.assets || []) {
        const before = (previous.assets || []).find((x) => x.id === a.id);
        if (before && before.status !== a.status) {
          logs.push({ timestamp: new Date().toISOString(), type: 'info', text: `[${a.asset_type}] ${a.id} → ${a.status}` });
        }
      }
    },
  });

  await reconcileCoinState(taskId, { token });

  const counts = { success: 0, failed: 0 };
  for (const a of status.assets || []) counts[a.status === 'success' ? 'success' : 'failed']++;
  const terminal = status.zip_download_url ? (counts.failed ? 'partial' : 'completed') : 'failed';

  await patchJobRecord(taskId, {
    status: terminal,
    success_count: counts.success,
    failed_count: counts.failed,
    asset_breakdown: {},
    files: status.assets || [],
    logs,
  }, { token });

  return { taskId, assets, status, counts, outcome: describeOutcome(status), deduction };
}

module.exports = {
  // constants
  MAX_IDS_PER_RUN, ID_PATTERN, POLL_INTERVAL_MS, PAYMENT_POLL_MS, LOG_TAIL_LIMIT,
  // errors
  ApiError, engineErrorText, backendErrorText,
  // parsing
  parseAssets, validateAssets, sanitiseFileName, buildFileName,
  // backend session + coins
  getAuthMe, getCoinState, reconcileCoinState, checkCost, deductCoins,
  refreshRobloxToken, getRobloxGroups,
  // audit
  createJobRecord, patchJobRecord,
  // engine job
  submitSpoofJob, getTaskStatus, pollTask, isTaskSettled, describeOutcome,
  // download
  downloadAsset,
  // roblox upload
  uploadOne, uploadBatchToRoblox,
  // extras
  getThumbnail,
  // payment
  createCoinInvoice, checkPayment, pollPayment, createPayPalCoinOrder, capturePayPalCoinOrder,
  // end-to-end
  runFreeSpoof, runPaidSpoof,
};
