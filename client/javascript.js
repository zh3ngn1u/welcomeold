/**
 * Blokmarket spoofer / B2B API client.
 *
 * Built ONLY from fields confirmed in the downloaded frontend bundles and from the
 * engine's published OpenAPI spec (analysis/api/spoofer-engine-openapi.json).
 * Nothing here is invented. See analysis/my-api-client-spec.md for provenance of every field.
 *
 * ── SECURITY ─────────────────────────────────────────────────────────────────────
 * Run this SERVER-SIDE. It carries credentials that must never reach a browser:
 *   • BMK_TOKEN        dashboard bearer  (Authorization: Bearer …)
 *   • ROBLOX_COOKIE    a live .ROBLOSECURITY session
 *   • ROBLOX_TOKEN     a Roblox OAuth access token
 * The engine's own design sends the Roblox bearer as a QUERY PARAMETER, so it ends up
 * in access logs, history and Referer. Never build such a URL in client-side code.
 * ─────────────────────────────────────────────────────────────────────────────────
 *
 * No source maps were published, so upstream function names are minified. Where the
 * original name is unrecoverable this file says so rather than inventing one.
 *
 * Requires Node 18+ (global fetch). No dependencies.
 */

'use strict';

const BACKEND = 'https://backend.blokmarket.store';
const ENGINE  = 'https://spoofer.blokmarket.store';

// Engine path prefix is NONE — these literals are used as-is. Backend paths get "/api".
const API_PREFIX = '/api';

// Polling interval hardcoded in the upstream frontend: setInterval(n, 1500)
const POLL_INTERVAL_MS = 1500;

/* ─────────────────────────── error shapes ─────────────────────────── */

// The upstream apiFetch wrapper never throws on a network failure; it returns a
// synthetic response so the UI can render an error toast. We reproduce that.
class ConnectionFailed extends Error {
  constructor(url, cause) {
    super(`Connection failed to: ${url}`);
    this.name = 'ConnectionFailed';
    this.url = url;
    this.cause = cause;
    this.status = 0;
  }
}

// Engine (FastAPI) errors: { detail: string } or { detail: [{loc,msg,type,input}] }
// Backend (Express-style) errors: { success:false, message:string }
function engineErrorText(body, fallback) {
  const d = body && body.detail;
  if (typeof d === 'string' && d) return d;
  if (Array.isArray(d) && d.length) {
    return d.map((e) => `${(e.loc || []).join('.')}: ${e.msg}`).join('; ');
  }
  return fallback;
}

function backendErrorText(body, fallback) {
  if (body && body.message) return body.message;
  return fallback;
}

/* ─────────────────────────── primitives ─────────────────────────── */

/**
 * Replicates upstream `apiFetch` — Turbopack module 4989, analysis/js/0vs148roxm~ft.js:
 *   headers.Authorization = `Bearer ${localStorage.bmk_token}`
 *   credentials: "include"
 *   on 401 -> clear token, POST /api/auth/refresh once, retry once
 *
 * NOTE: /api/auth/refresh currently returns 404 ("Endpoint not found"), so the
 * upstream refresh path never succeeds. We surface that instead of hard-redirecting.
 */
async function apiFetch(method, path, { body, query, token } = {}) {
  const bearer = token || process.env.BMK_TOKEN;
  const url = new URL(`${BACKEND}${API_PREFIX}${path}`);
  for (const [k, v] of Object.entries(query || {})) url.searchParams.set(k, String(v));

  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (bearer) headers.Authorization = `Bearer ${bearer}`;

  const init = { method, headers };
  if (body !== undefined) init.body = JSON.stringify(body);

  let res;
  try {
    res = await fetch(url, init);
  } catch (cause) {
    throw new ConnectionFailed(url.toString(), cause);
  }

  if (res.status === 401) {
    const refreshed = await fetch(`${BACKEND}${API_PREFIX}/auth/refresh`, {
      method: 'POST',
    }).catch(() => ({ ok: false }));
    if (!refreshed.ok) {
      const err = new Error(
        '401 Unauthorized and token refresh failed ' +
        `(POST ${API_PREFIX}/auth/refresh -> ${refreshed.status}). ` +
        'Upstream redirects to /login here.'
      );
      err.status = 401;
      throw err;
    }
    res = await fetch(url, init);
  }
  return res;
}

async function apiJSON(method, path, opts = {}) {
  const res = await apiFetch(method, path, opts);
  let body = null;
  try { body = await res.json(); } catch { /* non-JSON body */ }
  if (!res.ok) {
    const err = new Error(backendErrorText(body, `HTTP ${res.status}`));
    err.status = res.status;
    err.body = body;
    throw err;
  }
  return body;
}

/**
 * Engine calls use RAW fetch upstream: no Authorization header, no credentials mode.
 * Roblox credentials ride per request — cookie via header, OAuth bearer via query.
 */
async function engineFetch(method, path, { body, query, robloxCookie, oauthBearer } = {}) {
  const url = new URL(`${ENGINE}${path}`);
  for (const [k, v] of Object.entries(query || {})) url.searchParams.set(k, String(v));
  if (oauthBearer) url.searchParams.set('authorization', oauthBearer);

  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const cookie = robloxCookie || process.env.ROBLOX_COOKIE;
  if (cookie) headers['X-Roblox-Cookie'] = cookie;

  const init = { method, headers };
  if (body !== undefined) init.body = JSON.stringify(body);

  let res;
  try {
    res = await fetch(url, init);
  } catch (cause) {
    throw new ConnectionFailed(url.toString(), cause);
  }
  const text = await res.text();
  let parsed = null;
  try { parsed = text ? JSON.parse(text) : null; } catch { /* keep raw */ }
  if (!res.ok) {
    const err = new Error(engineErrorText(parsed, `HTTP ${res.status}`));
    err.status = res.status;
    err.body = parsed;
    throw err;
  }
  return { status: res.status, body: parsed, raw: text };
}

/* ═══════════════════════════ SPOOFER ENGINE ═══════════════════════════ */

/**
 * createSpoofJob(assets) -> { task_id }
 *
 * POST /api/download/batch/async
 * Body sent by the upstream dashboard, verbatim:
 *     { assets: [{ id, custom_name }], is_free: <bool> }
 * 400 response seen live: { detail: "Either 'asset_ids' or 'assets' must be provided." }
 *
 * @param {number[]|{id:number, custom_name?:string}[]} assets
 * @param {{isFree?:boolean, robloxCookie?:string, oauthBearer?:string}} [opts]
 *        isFree        — upstream sends this as `is_free`. When false and a cookie is
 *                        supplied, the X-Roblox-Cookie header is attached.
 *        robloxCookie  — .ROBLOSECURITY value. SERVER-SIDE ONLY.
 *        oauthBearer   — Roblox OAuth token, sent as ?authorization=. SERVER-SIDE ONLY.
 */
async function createSpoofJob(assets, opts = {}) {
  const normalised = assets.map((a) =>
    typeof a === 'number' ? { id: a } : { id: a.id, custom_name: a.custom_name ?? null }
  );
  const { body } = await engineFetch('POST', '/api/download/batch/async', {
    body: { assets: normalised, is_free: Boolean(opts.isFree) },
    robloxCookie: opts.isFree ? undefined : opts.robloxCookie,
    oauthBearer: opts.oauthBearer,
  });
  if (!body || !body.task_id) {
    throw new Error('Expected { task_id } from /api/download/batch/async, got: ' + JSON.stringify(body));
  }
  return body; // { task_id }
}

/**
 * getJobStatus(taskId) -> status object
 *
 * GET /api/task/{task_id}/status   — no auth header, no cookies.
 * Live: 404 -> { detail: "Task not found." }
 *
 * Fields confirmed in the upstream response handler:
 *   status, queue_position, total_queue,
 *   assets[]: { id, status, real_name, custom_name, asset_type,
 *               file_name, file_size, uploaded_asset_id, error }
 *   zip_download_url  (present when more than one asset succeeded)
 */
async function getJobStatus(taskId) {
  const { body } = await engineFetch('GET', `/api/task/${encodeURIComponent(taskId)}/status`);
  return body;
}

/**
 * getResult(taskId)
 *
 * THERE IS NO /result ENDPOINT. The task-status response IS the result — this helper
 * only reshapes it. Confirmed by the engine's own OpenAPI spec, which lists no such
 * route, and by the dashboard, which reads everything from the status payload.
 *
 * Returns { taskId, state, queuePosition, totalQueue, assets, zipUrl, done, failed }
 * where `done` means every asset has left the `processing` state.
 */
async function getResult(taskId) {
  const s = await getJobStatus(taskId);
  const assets = Array.isArray(s.assets) ? s.assets : [];
  const done = assets.length > 0 && assets.every((a) => a.status !== 'processing');
  return {
    taskId,
    state: s.status,
    queuePosition: s.queue_position ?? null,
    totalQueue: s.total_queue ?? 0,
    done,
    succeeded: assets.filter((a) => a.status === 'success'),
    failed: assets.filter((a) => a.status === 'failed'),
    zipUrl: s.zip_download_url ?? null,
  };
}

/**
 * pollTask(taskId, { onUpdate, onComplete, onFailed, intervalMs, signal })
 *
 * Reproduces the upstream loop: setInterval(fn, 1500) with a single guard ref, plus
 * re-checks on document visibilitychange / window focus. Upstream has no retry,
 * no backoff and no timeout — neither does this.
 *
 * Stops when: signal aborts, a 404 is raised, or every asset is no longer `processing`.
 */
function pollTask(taskId, opts = {}) {
  const {
    onUpdate, onComplete, onFailed,
    intervalMs = POLL_INTERVAL_MS,
    signal,
  } = opts;

  return new Promise((resolve, reject) => {
    let last = null;
    const stop = (fn, arg) => { clearInterval(timer); fn(arg); };

    const tick = async () => {
      try {
        const s = await getJobStatus(taskId);
        if (last === null || JSON.stringify(s) !== last) {
          last = JSON.stringify(s);
          if (onUpdate) onUpdate(s);
        }
        const assets = Array.isArray(s.assets) ? s.assets : [];
        if (assets.length && assets.every((a) => a.status !== 'processing')) {
          const result = {
            taskId,
            state: s.status,
            queuePosition: s.queue_position ?? null,
            totalQueue: s.total_queue ?? 0,
            done: true,
            succeeded: assets.filter((a) => a.status === 'success'),
            failed: assets.filter((a) => a.status === 'failed'),
            zipUrl: s.zip_download_url ?? null,
          };
          stop(resolve, result);
        }
      } catch (err) {
        // 404 => the task is gone upstream. Upstream clears the interval and stops.
        stop(reject, err);
      }
    };

    const timer = setInterval(tick, intervalMs);
    if (signal) signal.addEventListener('abort', () => stop(reject, new Error('aborted')));

    const onFocus = () => tick();
    if (typeof document !== 'undefined' && document.addEventListener) {
      document.addEventListener('visibilitychange', onFocus);
      globalThis.addEventListener?.('focus', onFocus);
    }
    tick();
  });
}

/**
 * uploadToRoblox(asset, { accessToken, creatorId, creatorType })
 *
 * POST /api/upload/batch — one asset PER REQUEST; the dashboard loops serially.
 * Live 422 with {} confirmed required: files, creator_id, creator_type.
 * `roblox_access_token` is optional server-side. creator_type = creatorId ? 'Group' : 'User'.
 */
async function uploadToRoblox(asset, { accessToken, creatorId, creatorType } = {}) {
  const token = accessToken || process.env.ROBLOX_TOKEN;
  return engineFetch('POST', '/api/upload/batch', {
    body: {
      files: [asset],
      roblox_access_token: token,
      creator_id: String(creatorId),
      creator_type: creatorType || (creatorId ? 'Group' : 'User'),
    },
  });
}

/**
 * getThumbnail(assetId, { size, format, isCircular })
 * GET /api/proxy/roblox-thumbnail?assetIds=…&size=…&format=…&isCircular=…
 * Live 200: { data:[{ targetId, state, imageUrl, version }] }
 */
async function getThumbnail(assetId, { size = '150x150', format = 'Png', isCircular = false } = {}) {
  const { body } = await engineFetch('GET', '/api/proxy/roblox-thumbnail', {
    query: { assetIds: assetId, size, format, isCircular: String(isCircular) },
  });
  return body?.data?.[0]?.imageUrl ?? null;
}

/* ═══════════════════════════ DASHBOARD BACKEND ═══════════════════════════ */

/** GET /api/auth/me -> user object. 401 -> { success:false, message:"No token" } */
const getAuthMe = (opts) => apiJSON('GET', '/auth/me', opts).then((b) => b.data);

/** GET|POST /api/auth/spoofer-state — coin balance + history. POST { task_id }. */
const getCoinState = (opts) => apiJSON('GET', '/auth/spoofer-state', opts).then((b) => b.data);
const reconcileCoinState = (taskId, opts) =>
  apiJSON('POST', '/auth/spoofer-state', { ...opts, body: { task_id: taskId } }).then((b) => b.data);

/**
 * POST /api/auth/spoofer-check-cost  { asset_ids: number[] }
 * -> { success, cost, has_ugc, message }
 * NOT present in the upstream apiEndpoints map — built via buildApiUrl() in the UI.
 */
const checkCost = (assetIds, opts) =>
  apiJSON('POST', '/auth/spoofer-check-cost', { ...opts, body: { asset_ids: assetIds } });

/** POST /api/auth/spoofer-deduct { asset_count, asset_ids } — spends real balance. */
const deductCoins = (assetIds, opts) =>
  apiJSON('POST', '/auth/spoofer-deduct', {
    ...opts,
    body: { asset_count: assetIds.length, asset_ids: assetIds },
  });

/** POST /api/spoofer-jobs — audit record. */
const createJobRecord = (job, opts) => apiJSON('POST', '/spoofer-jobs', { ...opts, body: job });
/** PATCH /api/spoofer-jobs/{id} — progress; `logs` is truncated to the last 500. */
const patchJob = (id, patch, opts) =>
  apiJSON('PATCH', `/spoofer-jobs/${id}`, { ...opts, body: patch });
/** GET /api/spoofer-jobs/{id} -> { success, data:{ logs:[] } } */
const getJobRecord = (id, opts) => apiJSON('GET', `/spoofer-jobs/${id}`, opts).then((b) => b.data);

/* ── B2B Mesh seller portal (all Bearer) ── */
const getB2BStatus   = (o) => apiJSON('GET', '/b2b/portal/status', o);
const getB2BLogs     = (o) => apiJSON('GET', '/b2b/portal/logs', { query: { page: 1, limit: 50 }, ...o });
const getB2BAnalytics= (days = 7, o) => apiJSON('GET', '/b2b/portal/analytics', { query: { days }, ...o });
/** POST — NO BODY. Returns { success, rawKey, tenant, message }. Invalidates the old key. */
const rotateB2BKey   = (o) => apiJSON('POST', '/b2b/portal/key/rotate', o);
/** PUT { webhookUrl } */
const setB2BWebhook  = (webhookUrl, o) =>
  apiJSON('PUT', '/b2b/portal/webhook', { ...o, body: { webhookUrl } });

/* ── Public, verified reachable with no auth ── */
const getProductCatalog   = () => apiJSON('GET', '/product');
const getProductCategories= () => apiJSON('GET', '/product/category');
const getUploadHealth     = () => apiJSON('GET', '/upload/health');
/** NOTE: `count` is top-level, not under `data`. */
const getApprovedCount    = () => apiJSON('GET', '/audio/approved-count');
const getApprovedDaily    = () => apiJSON('GET', '/audio/approved-daily-stats');

/* ─────────────────────────── client-side validation ─────────────────────────── */

/** Upstream hard caps. NOT confirmed as server-enforced — enforce server-side too. */
const MAX_IDS_PER_BATCH = 500;
const MAX_EXPERIENCE_IMAGE_BYTES = 1048576;
const MAX_AUDIO_SECONDS = 420;

/** Upstream filename sanitiser: replace(/[\\/:*?"<>|]/g, "_").trim() */
function sanitiseFileName(name) {
  return String(name).replace(/[\\/:*?"<>|]/g, '_').trim();
}

/**
 * Parse the upstream input format: a LUA table or a bare list of IDs.
 * Reproduces the two upstream guards:
 *   0 items -> "Invalid input format! Please enter a LUA table or list of IDs."
 *   >500    -> "Maximum of 500 IDs in a single bulk process!"
 */
function parseAssetIds(raw) {
  const text = String(raw).trim();
  if (!text) throw new Error('Invalid input format! Please enter a LUA table or list of IDs.');

  // ID rule confirmed from the upstream parser: /\d{9,18}/  (9-18 digits, not 3+)
  const ID_RE = /\d{9,18}/g;
  const out = [];
  const seen = new Set();
  const push = (id, name) => { if (!seen.has(id)) { out.push({ id, custom_name: name || `Asset #${id}` }); seen.add(id); } };

  // Pass 1: brace blocks  { ... }  — Luau table entries
  const blockRe = /\{([^{}]+)\}/g;
  let m;
  while ((m = blockRe.exec(text)) !== null) {
    const inner = m[1];
    const idM = inner.match(/\d{9,18}/);
    if (!idM) continue;
    const id = parseInt(idM[0], 10);
    const nameM =
      inner.match(/(?:['"]?Name['"]?|['"]?name['"]?)\s*[=:]\s*["']([^"']+)["']/i) ||
      inner.match(/^\s*["']([^"']+)["']\s*,\s*\d+/) ||
      inner.match(/["']([^"']+)["']/);
    let name = `Asset #${id}`;
    if (nameM) {
      const v = nameM[1].trim();
      if (v && !v.includes('rbxassetid') && !/^\d+$/.test(v)) name = v;
    }
    push(id, name);
  }

  // Pass 2: per-line fallback for bare ID lists
  for (const line of text.split('\n')) {
    const t = line.trim();
    if (!t) continue;
    const idM = t.match(/\d{9,18}/);
    if (!idM) continue;
    const id = parseInt(idM[0], 10);
    if (seen.has(id)) continue;
    const cands = [
      t.match(/\{\s*["']([^"']+)["']\s*,\s*\d+\s*\}/),
      t.match(/\[\s*["']([^"']+)["']\s*\]\s*[=:]/),
      t.match(/^([a-zA-Z_][a-zA-Z0-9_\s-]*)\s*[=:]/),
      t.match(/["']([^"']+)["']/),
    ];
    let name = `Asset #${id}`;
    for (const c of cands) {
      if (!c) continue;
      const v = c[1].trim();
      if (!v) continue;
      if (['id', 'assetid', 'asset_id'].includes(v.toLowerCase())) continue;
      if (v.includes('rbxassetid') || /^\d+$/.test(v)) continue;
      name = v;
      break;
    }
    push(id, name);
  }

  if (out.length === 0) throw new Error('Invalid input format! Please enter a LUA table or list of IDs.');
  if (out.length > MAX_IDS_PER_BATCH) throw new Error('Maximum of 500 IDs in a single bulk process!');
  return out;
}

/* ─────────────────────────── end-to-end ─────────────────────────── */

/**
 * Full upstream flow, server-side. Order and payloads match analysis/reseller/request-flow.md.
 */
async function runBatch(rawInput, { token, robloxCookie, isFree = false, onUpdate } = {}) {
  const assets = parseAssetIds(rawInput);
  const ids = assets.map((a) => a.id);

  // 1. price it
  const quote = await checkCost(ids, { token });
  if (!quote.success) throw new Error(quote.message || 'Failed to calculate coin cost.');

  // 2. optionally spend coins (skipped upstream for admin/owner roles)
  if (!isFree) await deductCoins(ids, { token });

  // 3. audit row (upstream only records non-free runs)
  const { task_id } = await createSpoofJob(assets, { isFree, robloxCookie });
  if (!isFree) {
    await createJobRecord({
      job_id: task_id, status: 'pending', total_assets: assets.length,
      success_count: 0, failed_count: 0, asset_breakdown: {},
    }, { token }).catch(() => {});
  }

  // 4. poll to completion
  const result = await pollTask(task_id, { onUpdate });

  // 5. reconcile coins + close the audit row
  await reconcileCoinState(task_id, { token }).catch(() => {});
  if (!isFree) {
    await patchJob(task_id, {
      status: result.failed.length ? 'partial' : 'completed',
      success_count: result.succeeded.length,
      failed_count: result.failed.length,
      asset_breakdown: {},
      files: result.succeeded.map((a) => ({
        id: a.id, custom_name: a.custom_name, status: 'success',
        file_name: a.file_name ?? null, file_size: a.file_size ?? 0,
        asset_type: a.asset_type ?? 'Unknown', uploaded_asset_id: a.uploaded_asset_id ?? null,
        upload_status: 'not_started', upload_error: null,
      })),
      logs: [],
    }, { token }).catch(() => {});
  }
  return result;
}

/* ─────────────────────────── exports ─────────────────────────── */
module.exports = {
  BACKEND, ENGINE, POLL_INTERVAL_MS, MAX_IDS_PER_BATCH,
  // engine
  createSpoofJob, getJobStatus, getResult, pollTask, uploadToRoblox, getThumbnail,
  // backend
  getAuthMe, getCoinState, reconcileCoinState, checkCost, deductCoins,
  createJobRecord, patchJob, getJobRecord,
  getB2BStatus, getB2BLogs, getB2BAnalytics, rotateB2BKey, setB2BWebhook,
  getProductCatalog, getProductCategories, getUploadHealth, getApprovedCount, getApprovedDaily,
  // helpers
  parseAssetIds, sanitiseFileName, runBatch,
  // errors
  ConnectionFailed,
};
