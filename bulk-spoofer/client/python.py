"""
Bulk Spoofer reference client - CONFIRMED functionality only.

Port of ./javascript.js. Every function maps to a call site in
analysis/js/0nh-y8e1a0l~a.js or to a path published in
analysis/api/spoofer-engine-openapi.json. No endpoint is invented.

SECURITY
    Run this SERVER-SIDE. It carries credentials that must never reach a browser:
      BMK_TOKEN     dashboard bearer  (Authorization: Bearer ...)
      ROBLOX_COOKIE a live .ROBLOSECURITY session
      ROBLOX_TOKEN  a Roblox OAuth access token
    The upstream page keeps all three in localStorage in plaintext. Do not copy that -
    see ../my-web-architecture.md.

No source maps were published, so the original function names are minified and
unrecoverable. Names below are ours; the upstream minified id is quoted in comments.

Requires Python 3.9+. Standard library only (urllib) unless `httpx` is installed -
`HTTP_CLIENT = "httpx"` at the top switches the transport.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

BACKEND = "https://backend.blokmarket.store"
ENGINE = "https://spoofer.blokmarket.store"

# HTTP_CLIENT = "httpx"   # uncomment and `pip install httpx` for streaming downloads

# --- Confirmed limits, lifted verbatim from the bundle --------------------------
MAX_IDS_PER_RUN = 500          # if (e.length > 500) -> toast "Maximum of 500 IDs..."
ID_PATTERN = re.compile(r"\d{9,18}")   # 9-18 digits; shorter is SILENTLY DROPPED
POLL_INTERVAL_MS = 1500        # setInterval(n, 1500)
PAYMENT_POLL_MS = 3000         # setInterval(async () => {...}, 3e3)
CLIPBOARD_AUTOPASTE_MS = 800    # setTimeout(..., 800)
LOG_TAIL_LIMIT = 500           # logs.slice(-500) before every PATCH
UPLOAD_REFRESH_TRIGGERS = (401, 403)

# Max response we will buffer into memory, mirroring res.blob() but bounded.
MAX_BUFFERED_DOWNLOAD = 256 * 1024 * 1024


# --- errors ---------------------------------------------------------------------


class ApiError(Exception):
    """Any non-2xx response or transport failure."""

    def __init__(self, message: str, *, status: int = 0, body: Any = None, url: str = ""):
        super().__init__(message)
        self.message = message
        self.status = status
        self.body = body
        self.url = url


def engine_error_text(body: Any, fallback: str = "Engine error") -> str:
    """FastAPI `detail` is a string OR an array of Pydantic objects. Handle both."""
    if not isinstance(body, dict):
        return fallback
    detail = body.get("detail")
    if isinstance(detail, str) and detail:
        return detail
    if isinstance(detail, list) and detail:
        parts = []
        for item in detail:
            if isinstance(item, dict):
                loc = ".".join(str(x) for x in (item.get("loc") or [])) or "body"
                parts.append(f"{loc}: {item.get('msg') or item.get('type')}")
            else:
                parts.append(str(item))
        return "; ".join(parts)
    return fallback


def backend_error_text(body: Any, fallback: str = "Backend error") -> str:
    """Backend is {success:false, message}. Some routes put the payload at top level."""
    if isinstance(body, dict) and body.get("message"):
        return str(body["message"])
    return fallback


# --- transport ------------------------------------------------------------------


def _request(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    json_body: Any = None,
    timeout: int = 60,
) -> Any:
    """Single transport shim. Returns the parsed JSON body, raises ApiError otherwise."""
    hdrs = dict(headers or {})
    data: Optional[bytes] = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")

    req = Request(url, data=data, headers=hdrs, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status
    except HTTPError as exc:                       # non-2xx
        raw = exc.read()
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except Exception:
            parsed = {"raw": raw[:500].decode("utf-8", "replace")}
        raise ApiError(
            _error_text_for(url, parsed, f"HTTP {exc.code}"),
            status=exc.code,
            body=parsed,
            url=url,
        ) from exc
    except URLError as exc:
        # Upstream calls this "Connection failed". Same meaning, but we surface it as a raise.
        raise ApiError(f"Connection failed to: {url}", status=0, url=url) from exc

    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {"raw": raw[:500].decode("utf-8", "replace")}


def _error_text_for(url: str, body: Any, fallback: str) -> str:
    if url.startswith(ENGINE):
        return engine_error_text(body, fallback)
    return backend_error_text(body, fallback)


def backend_fetch(
    method: str,
    path: str,
    *,
    json_body: Any = None,
    query: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
    timeout: int = 30,
) -> Any:
    """
    Backend call - mirrors upstream `apiFetch` (analysis/js/0vs148roxm~ft.js, module 4989).

    Differences from upstream, both deliberate bug fixes:
      1. Upstream returns a SYNTHETIC {ok:false,status:0} on a network error instead of
         raising, so every try/except around it is dead code. We raise ApiError.
      2. Upstream builds the Authorization header once, then on 401 deletes the token and
         "retries" with the SAME dead header. It cannot succeed. Here the header is simply
         not set when there is no token.

    Note: upstream's refresh endpoint (POST /api/auth/refresh) returns 404 in production,
    so in practice every expiry is a hard logout. See ../error-handling.md defect #2.
    """
    base = urljoin(BACKEND + "/", path.lstrip("/"))
    if not base.startswith(BACKEND):
        base = urljoin(BACKEND + "/", "api/" + path.lstrip("/"))
    if query:
        base += ("&" if "?" in base else "?") + urlencode(
            {k: v for k, v in query.items() if v is not None}
        )

    headers: Dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    return _request(base, method=method, headers=headers, json_body=json_body, timeout=timeout)


def engine_fetch(
    method: str,
    path: str,
    *,
    json_body: Any = None,
    roblox_cookie: Optional[str] = None,
    timeout: int = 60,
) -> Any:
    """
    Engine call - NO Authorization header, NO cookies. Upstream calls this origin with bare
    fetch and sends exactly one non-standard header, X-Roblox-Cookie, and only when
    is_free is false. See ../authentication.md sec 3.
    """
    url = urljoin(ENGINE + "/", path.lstrip("/"))
    headers: Dict[str, str] = {}
    if roblox_cookie:
        headers["X-Roblox-Cookie"] = roblox_cookie   # ONLY for paid runs
    return _request(url, method=method, headers=headers, json_body=json_body, timeout=timeout)


# --- input parsing --------------------------------------------------------------


def sanitise_file_name(name: str) -> str:
    """Upstream `s0`: (e) => e.replace(/[\\/:*?"<>|]/g, "_").trim()"""
    return re.sub(r'[\\/:*?"<>|]', "_", str(name)).strip()


def parse_assets(raw: str) -> List[Dict[str, Any]]:
    """
    Upstream `sQ`. Two passes over the raw textarea, deduped by id, first occurrence wins.

    Pass 1 - LUA table: every /\\{([^{}]+)\\}/ block.
    Pass 2 - bare lines: split("\\n"), one id per line.

    ID is the FIRST /\\d{9,18}/ in the chunk and is int()'d.
    If nothing matches, that line is skipped SILENTLY - it is not an error. Upstream has no
    per-line diagnostics; see ../error-handling.md defect #9 for why you should add them.
    """
    out: List[Dict[str, Any]] = []
    seen = set()

    # ---- Pass 1: { ... } blocks ---------------------------------------------
    for chunk in re.findall(r"\{([^{}]+)\}", raw):
        id_hit = ID_PATTERN.search(chunk)
        if not id_hit:
            continue

        asset_id = int(id_hit.group(0))
        name = f"Asset #{asset_id}"

        named = re.search(
            r"""(?:['"]?Name['"]?|['"]?name['"]?)\s*[=:]\s*["']([^"']+)["']""",
            chunk,
            re.IGNORECASE,
        )
        leading = re.search(r"""^\s*["']([^"']+)["']\s*,\s*\d+""", chunk)

        if named:
            name = named.group(1).strip()
        elif leading:
            name = leading.group(1).strip()
        else:
            for q in re.findall(r"""["']([^"']+)["']""", chunk):
                value = q.strip()
                if value and "rbxassetid" not in value and not re.fullmatch(r"\d+", value):
                    name = value
                    break

        if asset_id not in seen:
            out.append({"id": asset_id, "custom_name": name})
            seen.add(asset_id)

    # ---- Pass 2: one id per line -------------------------------------------
    for raw_line in raw.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        id_hit = ID_PATTERN.search(line)
        if not id_hit:
            continue                      # silently ignored

        asset_id = int(id_hit.group(0))
        if asset_id in seen:
            continue

        name = f"Asset #{asset_id}"
        brace = re.search(r"""\{\s*["']([^"']+)["']\s*,\s*\d+\s*\}""", line)
        indexed = re.search(r"""\[\s*["']([^"']+)["']\s*\]\s*[=:]""", line)
        ident = re.match(r"^([a-zA-Z_][a-zA-Z0-9_\s-]*)\s*[=:]", line)

        if brace:
            name = brace.group(1).strip()
        elif indexed:
            name = indexed.group(1).strip()
        elif ident and ident.group(1).strip().lower() not in ("id", "assetid", "asset_id"):
            name = ident.group(1).strip()
        else:
            quoted = re.search(r"""["']([^"']+)["']""", line)
            if quoted and "rbxassetid" not in quoted.group(1) and not re.fullmatch(
                r"\d+", quoted.group(1)
            ):
                name = quoted.group(1).strip()

        out.append({"id": asset_id, "custom_name": name})
        seen.add(asset_id)

    return out


def validate_assets(assets: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Upstream `s2` guard order - empty first, then the 500 cap. Both are pre-network."""
    if not assets:
        raise ApiError("Invalid input format! Please enter a LUA table or list of IDs.", status=400)
    if len(assets) > MAX_IDS_PER_RUN:
        raise ApiError(f"Maximum of {MAX_IDS_PER_RUN} IDs in a single bulk process!", status=400)
    return list(assets)


# --- backend: session & coins ----------------------------------------------------


def get_auth_me(*, token: Optional[str] = None) -> Any:
    """GET /api/auth/me - 401 body is the odd one out: {"success":false,"message":"No token"}."""
    return backend_fetch("GET", "/api/auth/me", token=token)


def get_coin_state(*, token: Optional[str] = None) -> Any:
    """GET /api/auth/spoofer-state -> { success, data:{ coins, history[] } }"""
    return backend_fetch("GET", "/api/auth/spoofer-state", token=token)


def reconcile_coin_state(task_id: str, *, token: Optional[str] = None) -> Any:
    """POST /api/auth/spoofer-state {task_id} - reconciling balance AFTER a job."""
    return backend_fetch("POST", "/api/auth/spoofer-state", token=token, json_body={"task_id": task_id})


def check_cost(asset_ids: Iterable[Any], *, token: Optional[str] = None) -> Any:
    """
    POST /api/auth/spoofer-check-cost {asset_ids:[...]}

    NOT present in the app's apiEndpoints map - upstream builds it with
    buildApiUrl("/auth/spoofer-check-cost"). An undeclared surface; documented in
    ../endpoints.md note under row #4.

    The cost is SERVER-AUTHORITATIVE. There is no client-side tier table.
    Returns { success, cost, has_ugc, message }.
    """
    ids = [str(a) for a in asset_ids]
    return backend_fetch("POST", "/api/auth/spoofer-check-cost", token=token, json_body={"asset_ids": ids})


def deduct_coins(assets: Sequence[Dict[str, Any]], *, token: Optional[str] = None) -> Any:
    """
    POST /api/auth/spoofer-deduct {asset_count, asset_ids:[...]} - upstream `s4`.
    Spends real balance. Returns { success, coins } or { success, newCoins }.

    WARNING: upstream charges at SUBMIT time, before any asset is known to succeed, and
    there is no refund endpoint anywhere in the bundle. See ../bulk-flow.md sec 6.
    """
    return backend_fetch(
        "POST",
        "/api/auth/spoofer-deduct",
        token=token,
        json_body={"asset_count": len(assets), "asset_ids": [str(a["id"]) for a in assets]},
    )


def refresh_roblox_token(*, token: Optional[str] = None) -> Any:
    """POST /api/auth/roblox/refresh {from:"spoofer"} -> { success, robloxAccessToken }."""
    return backend_fetch("POST", "/api/auth/roblox/refresh", token=token, json_body={"from": "spoofer"})


def get_roblox_groups(*, token: Optional[str] = None) -> Any:
    """GET /api/auth/roblox/groups -> { success, data:[...] } - the group picker."""
    return backend_fetch("GET", "/api/auth/roblox/groups", token=token)


# --- backend: audit job record (paid runs only) ---------------------------------


def create_job_record(job: Dict[str, Any], *, token: Optional[str] = None) -> Any:
    """
    POST /api/spoofer-jobs - upstream writes this ONLY for paid runs. A free run creates
    no audit row at all, so free usage is invisible server-side.
    """
    return backend_fetch("POST", "/api/spoofer-jobs", token=token, json_body=job)


def patch_job_record(
    job_id: str, patch: Dict[str, Any], *, token: Optional[str] = None
) -> Any:
    """
    PATCH /api/spoofer-jobs/:id - upstream `sX`/`sY`. Called on EVERY asset status change
    and again at terminal. Upstream slices logs to the last 500.

    Upstream swallows failures here (console.error only), so an audit row can silently
    diverge from reality. We let the error propagate; catch it yourself if best-effort.
    """
    body = dict(patch)
    if isinstance(body.get("logs"), list):
        body["logs"] = body["logs"][-LOG_TAIL_LIMIT:]
    return backend_fetch("PATCH", f"/api/spoofer-jobs/{job_id}", token=token, json_body=body)


# --- engine: the spoof job -------------------------------------------------------


def submit_spoof_job(
    assets: Sequence[Dict[str, Any]],
    *,
    is_free: bool = False,
    roblox_cookie: Optional[str] = None,
) -> Any:
    """
    POST /api/download/batch/async - upstream `s5`.

    Body is literally { assets:[{id,custom_name}], is_free:bool }. No place_id, no
    universeId, no is_private, no type, no mode - private assets are NOT a mode of this
    endpoint. See ../endpoints.md, final note.

    roblox_cookie is sent ONLY when is_free is False (upstream: !s && sg && sg.trim()).
    Returns { task_id }.
    """
    return engine_fetch(
        "POST",
        "/api/download/batch/async",
        roblox_cookie=None if is_free else roblox_cookie,
        json_body={
            "assets": [{"id": a["id"], "custom_name": a["custom_name"]} for a in assets],
            "is_free": bool(is_free),
        },
    )


def get_task_status(task_id: str) -> Any:
    """
    GET /api/task/:taskId/status - the poll target.
    Returns { status, queue_position, total_queue, assets[], zip_download_url }.

    A 404 here means "Task not found." Upstream treats it as terminal and deletes the task
    from localStorage; we surface it as an ApiError so you can decide (see
    ../error-handling.md defect #5).
    """
    return engine_fetch("GET", f"/api/task/{task_id}/status")


def is_task_settled(payload: Optional[Dict[str, Any]]) -> bool:
    """True when the status payload has produced everything the user can act on."""
    if not payload:
        return False
    if payload.get("zip_download_url"):
        return True
    return any(a.get("asset_type") == "Place" for a in (payload.get("assets") or []))


def poll_task(
    task_id: str,
    *,
    on_update: Optional[Callable[[Dict[str, Any], Optional[Dict[str, Any]]], None]] = None,
    timeout_ms: int = 30 * 60_000,
    interval_ms: int = POLL_INTERVAL_MS,
) -> Dict[str, Any]:
    """
    Poll a task every POLL_INTERVAL_MS until it settles or timeout_ms elapses.

    Deliberate differences from upstream, which has neither bound:
      * an overall timeout, so a permanently-200-but-never-settling endpoint cannot spin forever
      * backoff is intentionally NOT added - 1500 ms matches upstream. Add it if you want.
    """
    deadline = time.monotonic() + timeout_ms / 1000
    previous: Optional[Dict[str, Any]] = None

    while True:
        payload = get_task_status(task_id)
        if on_update:
            on_update(payload, previous)
        previous = payload

        if is_task_settled(payload):
            return payload
        if time.monotonic() >= deadline:
            raise ApiError("Timed out waiting for task to settle", status=0, body=payload)
        time.sleep(interval_ms / 1000)


# --- download --------------------------------------------------------------------


def build_file_name(asset: Dict[str, Any], *, fallback_ext: str = "") -> str:
    """
    Upstream `s0`:
      basename = metadata.name || custom_name
      ext      = "." + extname(file_name) when file_name is present, else fallback_ext
      then sanitised

    There is NO Content-Disposition parsing and NO signed-URL logic anywhere in the page.
    """
    base = (asset.get("metadata") or {}).get("name") or asset.get("custom_name") or ""
    file_name = asset.get("file_name")
    ext = ("." + str(file_name).split(".")[-1]) if file_name else fallback_ext
    return f"{sanitise_file_name(base)}{ext}"


def download_asset(url: str, filename: str, *, destination: Optional[str] = None) -> str:
    """
    Download a URL the way upstream `sZ` does - fetch -> bytes -> save.

    Prefer this over buffering a whole ZIP in memory: upstream's res.blob() holds the
    ENTIRE file in RAM, so a 500-asset ZIP is fully resident. See ../download-flow.md.
    """
    req = Request(url, method="GET")          # no Authorization, no credentials
    try:
        with urlopen(req, timeout=120) as resp:
            if resp.status >= 400:
                raise ApiError(f"Download failed: HTTP {resp.status}", status=resp.status, url=url)
            data = resp.read(MAX_BUFFERED_DOWNLOAD + 1)
    except HTTPError as exc:
        raise ApiError(f"Download failed: HTTP {exc.code}", status=exc.code, url=url) from exc
    except URLError as exc:
        raise ApiError(f"Connection failed to: {url}", url=url) from exc

    if len(data) > MAX_BUFFERED_DOWNLOAD:
        raise ApiError(
            f"Refusing to buffer >{MAX_BUFFERED_DOWNLOAD} bytes; stream to disk instead",
            url=url,
        )

    if destination:
        with open(destination, "wb") as fh:
            fh.write(data)
        return destination
    return filename


def describe_outcome(status: Dict[str, Any]) -> Dict[str, Any]:
    """Terminal-result summary, reproducing the upstream branching in workflow.md sec 1."""
    assets = status.get("assets") or []
    places = [a for a in assets if a.get("asset_type") == "Place"]
    success = [a for a in assets if a.get("status") == "success"]
    failed = [a for a in assets if a.get("status") == "failed"]

    if places:
        return {
            "kind": "place",
            "message": "Bypass feature for Place/Game is currently unavailable.",
        }
    if status.get("zip_download_url"):
        return {
            "kind": "zip",
            "message": f"Successfully downloaded {len(success)} files! ZIP is ready.",
            "zip_url": status["zip_download_url"],
        }
    if not success:
        return {"kind": "empty", "message": "Asset might be private or ID is invalid."}
    return {"kind": "done", "message": "Assets successfully spoofed!"}


# --- engine: upload results into a Roblox experience -----------------------------


def upload_one(
    asset: Dict[str, Any],
    *,
    roblox_access_token: Optional[str],
    creator_id: Any,
    creator_type: str,
) -> Any:
    """POST /api/upload/batch - ONE asset per request; upstream is strictly serial."""
    return engine_fetch(
        "POST",
        "/api/upload/batch",
        json_body={
            "files": [asset],
            "roblox_access_token": roblox_access_token,
            "creator_id": str(creator_id),
            "creator_type": creator_type,      # "User" | "Group"
        },
    )


def _needs_token_refresh(status: int, result: Optional[Dict[str, Any]]) -> bool:
    if status in UPLOAD_REFRESH_TRIGGERS:
        return True
    if not result:
        return False
    err = str(result.get("error") or "").lower()
    return "401" in err or "invalid token" in err or "token" in err


def upload_batch_to_roblox(
    assets: Sequence[Dict[str, Any]],
    *,
    roblox_access_token: Optional[str] = None,
    creator_id: Any,
    creator_type: str,
    token: Optional[str] = None,
    on_progress: Optional[Callable[[Dict[str, Any], Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Upload every successful asset, SERIALLY, with upstream's silent-refresh-and-retry.

    Upstream behaviour reproduced:
      * one request per asset, strictly sequential - 500 assets = 500 round-trips
      * on 401/403/"invalid token": refresh once, then retry THAT asset
      * if the refresh itself fails: abort everything remaining, mark them
        upload_status:"failed" / upload_error:"Aborted"

    Unlike upstream this never raises - it returns a summary, so a partial upload is a
    value, not an exception.
    """
    access_token = roblox_access_token
    success = 0
    failed = 0
    aborted = False
    refresh: Optional[Callable[[], Any]] = None

    for asset in assets:
        if aborted:
            asset["upload_status"] = "failed"
            asset["upload_error"] = "Aborted"
            failed += 1
            continue

        try:
            result = upload_one(
                asset,
                roblox_access_token=access_token,
                creator_id=creator_id,
                creator_type=creator_type,
            )
            asset["uploaded_asset_id"] = result.get("asset_id")
            asset["upload_status"] = "success" if result.get("success") else "failed"
            if result.get("success"):
                success += 1
            else:
                failed += 1
        except ApiError as exc:
            result = None
            if isinstance(exc.body, dict):
                results = exc.body.get("results") or []
                result = results[0] if results else None
            if not _needs_token_refresh(exc.status, result):
                asset["upload_status"] = "failed"
                asset["upload_error"] = f"HTTP Error: {exc.status}"
                failed += 1
                if on_progress:
                    on_progress(asset, {"success": success, "failed": failed})
                continue

            try:
                refreshed = refresh_roblox_token(token=token)
                access_token = refreshed.get("robloxAccessToken")
                result = upload_one(
                    asset,
                    roblox_access_token=access_token,
                    creator_id=creator_id,
                    creator_type=creator_type,
                )
                asset["uploaded_asset_id"] = result.get("asset_id")
                asset["upload_status"] = "success" if result.get("success") else "failed"
                if result.get("success"):
                    success += 1
                else:
                    failed += 1
            except ApiError:
                aborted = True
                asset["upload_status"] = "failed"
                asset["upload_error"] = "Aborted"
                failed += 1
                if on_progress:
                    on_progress(asset, {"success": success, "failed": failed, "aborted": True})
                break

        if on_progress:
            on_progress(asset, {"success": success, "failed": failed})

    return {
        "success": success,
        "failed": failed,
        "aborted": aborted,
        "roblox_access_token": access_token,
        "summary": f"Upload process completed. Success: {success}, Failed: {failed}",
    }


# --- thumbnails --------------------------------------------------------------------


def get_thumbnail(
    asset_ids: Any,
    *,
    size: str = "150x150",
    fmt: str = "Png",
    is_circular: bool = False,
) -> Any:
    """
    GET /api/proxy/roblox-thumbnail?assetIds=...&size=...&format=Png&isCircular=false
    Returns { data:[{ targetId, state, imageUrl, version }] }.

    `state` may be "Blocked" and the URL still resolves - do not gate the UI on state.
    Upstream fetches 150x150 for rows and 420x420 for the modal.
    """
    ids = asset_ids if isinstance(asset_ids, str) else ",".join(str(a) for a in asset_ids)
    return engine_fetch(
        "GET",
        "/api/proxy/roblox-thumbnail",
        query={
            "assetIds": ids,
            "size": size,
            "format": fmt,
            "isCircular": str(is_circular).lower(),
        },
    )


# --- coins & payment -----------------------------------------------------------------


def create_coin_invoice(*, coins: int, payment_method: str = "qris") -> Any:
    """
    POST /api/payment/create-coin-invoice {coins, paymentMethod:"qris"}
    -> { success, qrString, trxId, totalTransfer, isCoinTopUp, coins }

    The QR image is rendered CLIENT-SIDE by a third party:
      https://api.qrserver.com/v1/create-qr-code/?data=<encoded qrString>&size=600x600&...
    That means the payment string is sent to an external host. Do not do this in a
    production app without saying so to your users.
    """
    return backend_fetch(
        "POST",
        "/api/payment/create-coin-invoice",
        json_body={"coins": coins, "paymentMethod": payment_method},
    )


def check_payment(trx_id: str) -> Any:
    """GET /api/payment/check/:trxId -> { success, status: SUCCESS|EXPIRED|CANCELED, coins }"""
    return backend_fetch("GET", f"/api/payment/check/{trx_id}")


def poll_payment(
    trx_id: str,
    *,
    interval_ms: int = PAYMENT_POLL_MS,
    timeout_ms: int = 15 * 60_000,
    on_tick: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Poll a QRIS invoice every PAYMENT_POLL_MS until it is terminal."""
    deadline = time.monotonic() + timeout_ms / 1000
    while True:
        res = check_payment(trx_id)
        if on_tick:
            on_tick(res)
        if res.get("status") == "SUCCESS":
            return res
        if res.get("status") in ("EXPIRED", "CANCELED"):
            raise ApiError("Payment expired or canceled", status=res.get("status", 0), body=res)
        if time.monotonic() >= deadline:
            raise ApiError("Payment polling timed out", status=0, body=res)
        time.sleep(interval_ms / 1000)


def create_paypal_coin_order(*, coins: int) -> Any:
    """POST /api/payment/paypal/create-coin-order {coins}"""
    return backend_fetch("POST", "/api/payment/paypal/create-coin-order", json_body={"coins": coins})


def capture_paypal_coin_order(*, paypal_order_id: str, order_id: str, coins: int) -> Any:
    """POST /api/payment/paypal/capture-coin-order {paypalOrderId, orderId, coins}"""
    return backend_fetch(
        "POST",
        "/api/payment/paypal/capture-coin-order",
        json_body={"paypalOrderId": paypal_order_id, "orderId": order_id, "coins": coins},
    )


# --- end-to-end ---------------------------------------------------------------------


def run_free_spoof(
    raw_input: str,
    *,
    on_progress: Optional[Callable[[Dict[str, Any], Dict[str, Any]], None]] = None,
    timeout_ms: int = 30 * 60_000,
) -> Dict[str, Any]:
    """
    The whole confirmed free-spoof workflow: parse -> validate -> submit -> poll -> settle.
    This is the "Free Spoof" path - no coins, no audit row, never sends X-Roblox-Cookie.
    """
    assets = validate_assets(parse_assets(raw_input))
    submitted = submit_spoof_job(assets, is_free=True)
    task_id = submitted["task_id"]
    status = poll_task(task_id, on_update=on_progress, timeout_ms=timeout_ms)
    return {"task_id": task_id, "assets": assets, "status": status, "outcome": describe_outcome(status)}


def run_paid_spoof(
    raw_input: str,
    *,
    token: str,
    roblox_cookie: Optional[str] = None,
    on_progress: Optional[Callable[[Dict[str, Any], Dict[str, Any]], None]] = None,
    timeout_ms: int = 30 * 60_000,
) -> Dict[str, Any]:
    """
    The whole confirmed paid-spoof workflow.

    Order matters and is not negotiable, because it mirrors upstream:
      1. check cost        (server-authoritative)
      2. deduct coins      <- MONEY MOVES HERE, before any asset is attempted
      3. create audit row  (upstream skips both for admin/owner)
      4. submit + poll
      5. reconcile balance
      6. PATCH the audit row on every change and at terminal

    If you re-implement, add a refund path - upstream has none.
    """
    assets = validate_assets(parse_assets(raw_input))
    ids = [str(a["id"]) for a in assets]

    quote = check_cost(ids, token=token)
    if not quote.get("success"):
        raise ApiError(quote.get("message") or "Failed to calculate coin cost.", status=400, body=quote)

    state = get_coin_state(token=token)
    coins = ((state or {}).get("data") or {}).get("coins")
    if isinstance(coins, int) and coins < quote.get("cost", 0):
        raise ApiError(f"Insufficient Coins (-{quote['cost'] - coins})", status=402, body=quote)

    deduction = deduct_coins(assets, token=token)
    submitted = submit_spoof_job(assets, is_free=False, roblox_cookie=roblox_cookie)
    task_id = submitted["task_id"]

    create_job_record(
        {
            "job_id": task_id,
            "status": "pending",
            "total_assets": len(assets),
            "success_count": 0,
            "failed_count": 0,
            "asset_breakdown": {},
        },
        token=token,
    )

    logs: List[Dict[str, Any]] = []

    def _on_update(payload: Dict[str, Any], previous: Optional[Dict[str, Any]]) -> None:
        counts = {"success": 0, "failed": 0}
        for a in payload.get("assets") or []:
            counts["success" if a.get("status") == "success" else "failed"] += 1
        if on_progress:
            on_progress(payload, counts)
        if not previous:
            return
        prev_by_id = {a.get("id"): a for a in (previous.get("assets") or [])}
        for a in payload.get("assets") or []:
            before = prev_by_id.get(a.get("id"))
            if before and before.get("status") != a.get("status"):
                logs.append(
                    {
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
                        "type": "info",
                        "text": f"[{a.get('asset_type')}] {a.get('id')} -> {a.get('status')}",
                    }
                )

    status = poll_task(task_id, on_update=_on_update, timeout_ms=timeout_ms)
    reconcile_coin_state(task_id, token=token)

    counts = {"success": 0, "failed": 0}
    for a in status.get("assets") or []:
        counts["success" if a.get("status") == "success" else "failed"] += 1
    terminal = "partial" if status.get("zip_download_url") and counts["failed"] else (
        "completed" if status.get("zip_download_url") else "failed"
    )

    patch_job_record(
        task_id,
        {
            "status": terminal,
            "success_count": counts["success"],
            "failed_count": counts["failed"],
            "asset_breakdown": {},
            "files": status.get("assets") or [],
            "logs": logs,
        },
        token=token,
    )

    return {
        "task_id": task_id,
        "assets": assets,
        "status": status,
        "counts": counts,
        "outcome": describe_outcome(status),
        "deduction": deduction,
    }


__all__ = [
    "MAX_IDS_PER_RUN", "POLL_INTERVAL_MS", "PAYMENT_POLL_MS", "LOG_TAIL_LIMIT",
    "ApiError", "engine_error_text", "backend_error_text",
    "parse_assets", "validate_assets", "sanitise_file_name", "build_file_name",
    "get_auth_me", "get_coin_state", "reconcile_coin_state", "check_cost", "deduct_coins",
    "refresh_roblox_token", "get_roblox_groups",
    "create_job_record", "patch_job_record",
    "submit_spoof_job", "get_task_status", "poll_task", "is_task_settled", "describe_outcome",
    "download_asset",
    "upload_one", "upload_batch_to_roblox",
    "get_thumbnail",
    "create_coin_invoice", "check_payment", "poll_payment",
    "create_paypal_coin_order", "capture_paypal_coin_order",
    "run_free_spoof", "run_paid_spoof",
]
