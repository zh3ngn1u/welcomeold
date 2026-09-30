"""
Blokmarket spoofer / B2B API client.

Built ONLY from fields confirmed in the downloaded frontend bundles and from the
engine's published OpenAPI spec (analysis/api/spoofer-engine-openapi.json).
Provenance for every field: analysis/my-api-client-spec.md

SECURITY: run server-side. BMK_TOKEN, ROBLOX_COOKIE and ROBLOX_TOKEN are all
high-value credentials. The engine's design puts the Roblox bearer in a QUERY
PARAMETER, so it lands in access logs / history / Referer.

No source maps were published, so upstream function names are minified and are
not reproduced here.

Requires: pip install requests
"""
from __future__ import annotations

import os
import re
import time
from typing import Any, Callable, Iterable, Optional

import requests

BACKEND = "https://backend.blokmarket.store"
ENGINE = "https://spoofer.blokmarket.store"
API_PREFIX = "/api"

# setInterval(n, 1500) in the upstream frontend
POLL_INTERVAL_S = 1.5

# Upstream hard caps. NOT confirmed as server-enforced.
MAX_IDS_PER_BATCH = 500
MAX_EXPERIENCE_IMAGE_BYTES = 1_048_576
MAX_AUDIO_SECONDS = 420


# ───────────────────────── errors ─────────────────────────

class APIError(Exception):
    """Backend style: {"success": false, "message": "..."}"""

    def __init__(self, message: str, status: int, body: Any = None):
        super().__init__(message)
        self.status, self.body = status, body


class EngineError(APIError):
    """FastAPI style: {"detail": "..."} or {"detail": [{loc,msg,type,input}]}"""


def _engine_message(body: Any, fallback: str) -> str:
    detail = (body or {}).get("detail")
    if isinstance(detail, str) and detail:
        return detail
    if isinstance(detail, list) and detail:
        return "; ".join(
            f"{'.'.join(str(p) for p in e.get('loc', []))}: {e.get('msg')}"
            for e in detail
        )
    return fallback


def _backend_message(body: Any, fallback: str) -> str:
    if isinstance(body, dict) and body.get("message"):
        return body["message"]
    return fallback


# ───────────────────────── primitives ─────────────────────────

def api_fetch(method: str, path: str, *, json_body=None, params=None,
              token: Optional[str] = None, timeout: int = 20) -> requests.Response:
    """Replicates upstream `apiFetch` (Turbopack module 4989, 0vs148roxm~ft.js).

    Sets Authorization: Bearer <bmk_token> and credentials:"include", and on 401
    clears the token and calls POST /api/auth/refresh once before retrying.
    NOTE: /api/auth/refresh currently returns 404, so the refresh never succeeds.
    """
    bearer = token or os.environ.get("BMK_TOKEN")
    headers = {"Accept": "application/json"}
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"

    try:
        res = requests.request(method, f"{BACKEND}{API_PREFIX}{path}", headers=headers,
                               params=params, json=json_body, timeout=timeout)
    except requests.RequestException as exc:
        # upstream never throws; it returns a synthetic ok:false response
        raise APIError(f"Connection failed to: {path}", 0, {"cause": str(exc)}) from exc

    if res.status_code == 401:
        try:
            refreshed = requests.post(f"{BACKEND}{API_PREFIX}/auth/refresh", timeout=timeout)
        except requests.RequestException:
            refreshed = None
        if refreshed is None or not refreshed.ok:
            code = refreshed.status_code if refreshed is not None else 0
            raise APIError(
                "401 Unauthorized and token refresh failed "
                f"(POST {API_PREFIX}/auth/refresh -> {code}); upstream redirects to /login",
                401,
            )
        res = requests.request(method, f"{BACKEND}{API_PREFIX}{path}", headers=headers,
                               params=params, json=json_body, timeout=timeout)
    return res


def api_json(method: str, path: str, **kw) -> Any:
    res = api_fetch(method, path, **kw)
    try:
        body = res.json()
    except ValueError:
        body = None
    if not res.ok:
        raise APIError(_backend_message(body, f"HTTP {res.status_code}"), res.status_code, body)
    return body


def engine_fetch(method: str, path: str, *, json_body=None, params=None,
                 roblox_cookie: Optional[str] = None, oauth_bearer: Optional[str] = None,
                 timeout: int = 30) -> Any:
    """Engine calls use RAW fetch upstream: no Authorization header, no cookies.

    Roblox credentials ride per request: cookie via X-Roblox-Cookie header,
    OAuth bearer via the ?authorization= query parameter.
    """
    headers: dict[str, str] = {}
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    cookie = roblox_cookie or os.environ.get("ROBLOX_COOKIE")
    if cookie:
        headers["X-Roblox-Cookie"] = cookie

    q = dict(params or {})
    bearer = oauth_bearer or os.environ.get("ROBLOX_TOKEN")
    if bearer:
        q["authorization"] = bearer

    try:
        res = requests.request(method, f"{ENGINE}{path}", headers=headers,
                               params=q, json=json_body, timeout=timeout)
    except requests.RequestException as exc:
        raise APIError(f"Connection failed to: {path}", 0, {"cause": str(exc)}) from exc

    try:
        body = res.json()
    except ValueError:
        body = None
    if not res.ok:
        raise EngineError(_engine_message(body, f"HTTP {res.status_code}"),
                          res.status_code, body)
    return body


# ═════════════════════ SPOOFER ENGINE ═════════════════════

def create_spoof_job(assets: Iterable[Any], *, is_free: bool = False,
                     roblox_cookie: Optional[str] = None,
                     oauth_bearer: Optional[str] = None) -> dict:
    """POST /api/download/batch/async -> {"task_id": "..."}

    Body is exactly what the dashboard sends: {"assets":[{id,custom_name}], "is_free":bool}
    Live 400: {"detail":"Either 'asset_ids' or 'assets' must be provided."}

    X-Roblox-Cookie is attached only when is_free is False, matching upstream.
    """
    normalised = [
        {"id": a, "custom_name": None} if isinstance(a, int)
        else {"id": a["id"], "custom_name": a.get("custom_name")}
        for a in assets
    ]
    body = engine_fetch("POST", "/api/download/batch/async",
                        json_body={"assets": normalised, "is_free": bool(is_free)},
                        roblox_cookie=None if is_free else roblox_cookie,
                        oauth_bearer=oauth_bearer)
    if not isinstance(body, dict) or "task_id" not in body:
        raise EngineError(f"expected task_id, got: {body!r}", 200, body)
    return body


def get_job_status(task_id: str) -> dict:
    """GET /api/task/{task_id}/status — no auth header, no cookies.
    Live 404: {"detail":"Task not found."}

    Confirmed fields: status, queue_position, total_queue,
      assets[].{id,status,real_name,custom_name,asset_type,
                file_name,file_size,uploaded_asset_id,error},
      zip_download_url
    """
    return engine_fetch("GET", f"/api/task/{task_id}/status")


def get_result(task_id: str) -> dict:
    """THERE IS NO /result ENDPOINT — the status response IS the result.
    Confirmed by the engine's own OpenAPI spec, which lists no such route.

    This only reshapes the status payload; it makes no extra call beyond get_job_status.
    """
    s = get_job_status(task_id)
    assets = s.get("assets") or []
    return {
        "task_id": task_id,
        "state": s.get("status"),
        "queue_position": s.get("queue_position"),
        "total_queue": s.get("total_queue") or 0,
        "done": bool(assets) and all(a.get("status") != "processing" for a in assets),
        "succeeded": [a for a in assets if a.get("status") == "success"],
        "failed": [a for a in assets if a.get("status") == "failed"],
        "zip_url": s.get("zip_download_url"),
    }


def poll_task(task_id: str, *, on_update: Optional[Callable[[dict], None]] = None,
              interval_s: float = POLL_INTERVAL_S, max_seconds: Optional[float] = None) -> dict:
    """Reproduces upstream: setInterval(fn, 1500), single guard, no retry, no backoff.

    Stops when every asset leaves `processing`, or on 404, or at max_seconds if given.
    """
    deadline = None if max_seconds is None else time.monotonic() + max_seconds
    last: Optional[str] = None
    while True:
        s = get_job_status(task_id)                 # 404 propagates as EngineError
        serialised = repr(sorted(s.items())) if isinstance(s, dict) else repr(s)
        if serialised != last:
            last = serialised
            if on_update:
                on_update(s)
        assets = s.get("assets") or []
        if assets and all(a.get("status") != "processing" for a in assets):
            return {
                "task_id": task_id,
                "state": s.get("status"),
                "queue_position": s.get("queue_position"),
                "total_queue": s.get("total_queue") or 0,
                "done": True,
                "succeeded": [a for a in assets if a.get("status") == "success"],
                "failed": [a for a in assets if a.get("status") == "failed"],
                "zip_url": s.get("zip_download_url"),
            }
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError(f"poll_task exceeded {max_seconds}s for task {task_id}")
        time.sleep(interval_s)


def upload_to_roblox(asset: dict, *, access_token: Optional[str] = None,
                     creator_id: str = "", creator_type: Optional[str] = None) -> dict:
    """POST /api/upload/batch — ONE asset per request; the dashboard loops serially.

    Live 422 with {} confirmed required fields: files, creator_id, creator_type.
    roblox_access_token is optional server-side.
    creator_type = "Group" if creator_id else "User" (upstream derivation).
    """
    return engine_fetch("POST", "/api/upload/batch", json_body={
        "files": [asset],
        "roblox_access_token": access_token or os.environ.get("ROBLOX_TOKEN"),
        "creator_id": str(creator_id),
        "creator_type": creator_type or ("Group" if creator_id else "User"),
    })


def get_thumbnail(asset_id: int, *, size: str = "150x150",
                  fmt: str = "Png", is_circular: bool = False) -> Optional[str]:
    """GET /api/proxy/roblox-thumbnail -> { data:[{targetId,state,imageUrl,version}] }"""
    body = engine_fetch("GET", "/api/proxy/roblox-thumbnail", params={
        "assetIds": asset_id, "size": size, "format": fmt, "isCircular": str(is_circular),
    })
    data = (body or {}).get("data") or []
    return data[0].get("imageUrl") if data else None


# ═════════════════════ DASHBOARD BACKEND ═════════════════════

def get_auth_me(**kw) -> Any:
    """GET /api/auth/me. 401 -> {"success":false,"message":"No token"}"""
    return api_json("GET", "/auth/me", **kw).get("data")


def get_coin_state(**kw) -> Any:
    """GET /api/auth/spoofer-state -> data with coins + history"""
    return api_json("GET", "/auth/spoofer-state", **kw).get("data")


def reconcile_coin_state(task_id: str, **kw) -> Any:
    """POST /api/auth/spoofer-state {"task_id": ...}"""
    return api_json("POST", "/auth/spoofer-state", json_body={"task_id": task_id}, **kw).get("data")


def check_cost(asset_ids: Iterable[int], **kw) -> dict:
    """POST /api/auth/spoofer-check-cost {"asset_ids":[...]} -> {success,cost,has_ugc,message}
    NOT in the upstream apiEndpoints map — built via buildApiUrl() in the UI."""
    return api_json("POST", "/auth/spoofer-check-cost",
                    json_body={"asset_ids": list(asset_ids)}, **kw)


def deduct_coins(asset_ids: Iterable[int], **kw) -> dict:
    """POST /api/auth/spoofer-deduct {"asset_count":n,"asset_ids":[...]} — spends real balance."""
    ids = list(asset_ids)
    return api_json("POST", "/auth/spoofer-deduct",
                    json_body={"asset_count": len(ids), "asset_ids": ids}, **kw)


def create_job_record(job: dict, **kw) -> dict:
    """POST /api/spoofer-jobs"""
    return api_json("POST", "/spoofer-jobs", json_body=job, **kw)


def patch_job(job_id: str, patch: dict, **kw) -> dict:
    """PATCH /api/spoofer-jobs/{id} — upstream truncates `logs` to the last 500."""
    return api_json("PATCH", f"/spoofer-jobs/{job_id}", json_body=patch, **kw)


def get_job_record(job_id: str, **kw) -> Any:
    """GET /api/spoofer-jobs/{id} -> data with logs[]"""
    return api_json("GET", f"/spoofer-jobs/{job_id}", **kw).get("data")


# ── B2B Mesh seller portal (all Bearer) ──
def get_b2b_status(**kw)     -> dict: return api_json("GET", "/b2b/portal/status", **kw)
def get_b2b_logs(**kw)       -> dict: return api_json("GET", "/b2b/portal/logs",
                                                       params={"page": 1, "limit": 50}, **kw)
def get_b2b_analytics(days: int = 7, **kw) -> dict:
    return api_json("GET", "/b2b/portal/analytics", params={"days": days}, **kw)
def rotate_b2b_key(**kw)    -> dict: return api_json("POST", "/b2b/portal/key/rotate", **kw)  # no body
def set_b2b_webhook(webhook_url: str, **kw) -> dict:
    return api_json("PUT", "/b2b/portal/webhook", json_body={"webhookUrl": webhook_url}, **kw)


# ── Public, verified reachable without auth ──
def get_product_catalog()   -> Any: return api_json("GET", "/product")
def get_product_categories()-> Any: return api_json("GET", "/product/category")
def get_upload_health()     -> Any: return api_json("GET", "/upload/health")
def get_approved_count()    -> Any: return api_json("GET", "/audio/approved-count")   # `count` top-level
def get_approved_daily()    -> Any: return api_json("GET", "/audio/approved-daily-stats")


# ───────────────── client-side validation (upstream parity) ─────────────────

def sanitise_file_name(name: str) -> str:
    """Upstream: replace(/[\\/:*?"<>|]/g, "_").trim()"""
    for ch in '\\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip()


# Quote classes are built from chr() so the literals stay readable and safe to embed.
_DQ, _SQ = chr(34), chr(39)
_Q = f"[{re.escape(_DQ + _SQ)}]"          # a char class matching either quote char
Q_NAME_ASSIGN = rf"(?:{_Q}?Name{_Q}?|{_Q}?name{_Q}?)\s*[=:]\s*{_Q}([^{_DQ}{_SQ}]+){_Q}"
Q_NAME_FIRST  = rf"^\s*{_Q}([^{_DQ}{_SQ}]+){_Q}\s*,\s*\d+"
Q_ANY_QUOTED  = rf"{_Q}([^{_DQ}{_SQ}]+){_Q}"
Q_TABLE_PAIR  = rf"\{{\s*{_Q}([^{_DQ}{_SQ}]+){_Q}\s*,\s*\d+\s*\}}"
Q_INDEX_ASSIGN= rf"\[\s*{_Q}([^{_DQ}{_SQ}]+){_Q}\s*\]\s*[=:]"
Q_KEY_ASSIGN  = r"^([a-zA-Z_][a-zA-Z0-9_\s-]*)\s*[=:]"
ID_RE = r"\d{9,18}"


def parse_asset_ids(raw: str) -> list[dict]:
    """Parse a LUA table or bare ID list.

    ID rule confirmed from the upstream parser: \\d{9,18}  (9-18 digits, NOT 3+).
    Name resolution order, as upstream:
      pass 1  brace blocks  { ... }:  Name="x"  |  "x",123  |  first clean quoted string
      pass 2  per line:               { "x", 1 }  |  ["x"]=  |  key=value (not id/assetid/asset_id)
                                    |  first clean quoted string
    Default name is "Asset #<id>". Ids are de-duplicated.
    Upstream guards:
      0 items -> "Invalid input format! Please enter a LUA table or list of IDs."
      >500    -> "Maximum of 500 IDs in a single bulk process!"
    """
    text = (raw or "").strip()
    if not text:
        raise ValueError("Invalid input format! Please enter a LUA table or list of IDs.")

    out: list[dict] = []
    seen: set[int] = set()

    def clean(value: str | None) -> str | None:
        if not value:
            return None
        v = value.strip()
        if not v or "rbxassetid" in v or v.isdigit():
            return None
        if v.lower() in {"id", "assetid", "asset_id"}:
            return None
        return v

    def push(asset_id: int, name: str | None) -> None:
        if asset_id not in seen:
            out.append({"id": asset_id, "custom_name": name or f"Asset #{asset_id}"})
            seen.add(asset_id)

    # pass 1 - brace blocks
    for inner in re.findall(r"\{([^{}]+)\}", text):
        id_m = re.search(r"\d{9,18}", inner)
        if not id_m:
            continue
        asset_id = int(id_m.group(0))
        name = None
        for pattern, flags in (
            (Q_NAME_ASSIGN, re.IGNORECASE),
            (Q_NAME_FIRST, 0),
            (Q_ANY_QUOTED, 0),
        ):
            m = re.search(pattern, inner, flags)
            if m and clean(m.group(1)):
                name = clean(m.group(1))
                break
        push(asset_id, name)

    # pass 2 - per-line fallback
    for line in text.split("\n"):
        t = line.strip()
        if not t:
            continue
        id_m = re.search(r"\d{9,18}", t)
        if not id_m:
            continue
        asset_id = int(id_m.group(0))
        if asset_id in seen:
            continue
        name = None
        for pattern in (Q_TABLE_PAIR, Q_INDEX_ASSIGN, Q_KEY_ASSIGN, Q_ANY_QUOTED):
            m = re.search(pattern, t)
            if m and clean(m.group(1)):
                name = clean(m.group(1))
                break
        push(asset_id, name)

    if not out:
        raise ValueError("Invalid input format! Please enter a LUA table or list of IDs.")
    if len(out) > MAX_IDS_PER_BATCH:
        raise ValueError("Maximum of 500 IDs in a single bulk process!")
    return out


# ───────────────────────── end-to-end ─────────────────────────

def run_batch(raw_input: str, *, roblox_cookie=None, is_free: bool = False,
              on_update: Optional[Callable[[dict], None]] = None,
              token: Optional[str] = None) -> dict:
    """Full upstream flow, server-side. See analysis/reseller/request-flow.md."""
    assets = parse_asset_ids(raw_input)
    ids = [a["id"] for a in assets]

    quote = check_cost(ids, token=token)
    if not quote.get("success"):
        raise APIError(quote.get("message") or "Failed to calculate coin cost.", 200, quote)

    if not is_free:
        deduct_coins(ids, token=token)

    task = create_spoof_job(assets, is_free=is_free, roblox_cookie=roblox_cookie)
    task_id = task["task_id"]

    if not is_free:
        try:
            create_job_record({"job_id": task_id, "status": "pending",
                               "total_assets": len(assets), "success_count": 0,
                               "failed_count": 0, "asset_breakdown": {}}, token=token)
        except APIError:
            pass

    result = poll_task(task_id, on_update=on_update)

    try:
        reconcile_coin_state(task_id, token=token)
    except APIError:
        pass
    if not is_free:
        try:
            patch_job(task_id, {
                "status": "partial" if result["failed"] else "completed",
                "success_count": len(result["succeeded"]),
                "failed_count": len(result["failed"]),
                "asset_breakdown": {},
                "files": [{
                    "id": a.get("id"), "custom_name": a.get("custom_name"), "status": "success",
                    "file_name": a.get("file_name"), "file_size": a.get("file_size") or 0,
                    "asset_type": a.get("asset_type") or "Unknown",
                    "uploaded_asset_id": a.get("uploaded_asset_id"),
                    "upload_status": "not_started", "upload_error": None,
                } for a in result["succeeded"]],
                "logs": [],
            }, token=token)
        except APIError:
            pass
    return result


if __name__ == "__main__":
    # No credentials are hardcoded anywhere. Export them first.
    print("health          :", get_upload_health())
    print("approved count  :", get_approved_count())
    print("catalog count   :", len(get_product_catalog()["data"]))
    # Authenticated examples — uncomment with BMK_TOKEN set:
    # print("me              :", get_auth_me())
    # print("coins           :", get_coin_state())
    # print("cost for 2 ids  :", check_cost([1846853302, 1846853302]))
    # print("b2b status      :", get_b2b_status())
