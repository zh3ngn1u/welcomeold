#!/usr/bin/env bash
# 03_spoofer_engine.sh — https://spoofer.blokmarket.store
#
# CONTRACT SOURCE: the service publishes its own OpenAPI 3.1 spec at /openapi.json
#   (saved verbatim as ../spoofer-engine-openapi.json). Every path, query param and
#   body field below is copied from that spec, NOT inferred from names.
#   info.title = "Roblox Asset Downloader Core Service"
#   info.description = "Python-based high performance asynchronous backend to scan and
#                      download Roblox audios, animations, and emotes."
#   Stack: FastAPI (Pydantic) — errors use the {"detail": ...} shape, not {"success":...}
#
# WHAT WAS AND WAS NOT EXECUTED:
#   * /api/proxy/roblox-thumbnail, /api/task/{id}/status -> executed, read-only
#   * /api/download/batch/async, /api/upload/batch -> executed ONLY with an empty /
#     missing payload, so validation ran but no asset was downloaded, bypassed or
#     uploaded. Successful execution of these two is deliberately NOT attempted here.
#   * every other endpoint below -> UNTESTED (documented from the published spec only)
#
# These engine calls are made by the frontend with NO Authorization header and NO
# credentials mode. Roblox auth is passed instead as a query param `authorization`
# (OAuth bearer) or header `x-roblox-cookie` (.ROBLOSECURITY), per the spec.
set -u
ENGINE="https://spoofer.blokmarket.store"

#------------------------------------------------------------------------
# GET /  --  Serve Index
# Serves the main frontend index.html if compiled, otherwise returns healthy status.
# STATUS: 403 (responses/15)
# --- example (not executed unless marked TESTED above) ---
curl -sS "$ENGINE/"

#------------------------------------------------------------------------
# GET /api/proxy/roblox-thumbnail  --  Proxy Roblox Thumbnail
# Proxies requests to the Roblox Thumbnails API to bypass CORS limitations on the client side.
# STATUS: TESTED live 200 (responses/13)
# query params (from spec): assetIds, size, format, isCircular
# --- example (not executed unless marked TESTED above) ---
curl -sS "$ENGINE/api/proxy/roblox-thumbnail?assetIds=<assetId>"

#------------------------------------------------------------------------
# GET /api/proxy/roblox-thumbnail-3d  --  Proxy Roblox Thumbnail 3D
# Proxies requests to the Roblox 3D Thumbnail API using backend ROBLOSECURITY cookie to bypass CORS.
# STATUS: UNTESTED (documented from published OpenAPI spec only)
# query params (from spec): assetId
# --- example (not executed unless marked TESTED above) ---
curl -sS "$ENGINE/api/proxy/roblox-thumbnail-3d?assetId=<assetId>"

#------------------------------------------------------------------------
# GET /api/proxy/roblox-user-avatar-3d  --  Proxy Roblox User Avatar 3D
# Proxies requests to the Roblox User Avatar 3D API using backend ROBLOSECURITY cookie to bypass CORS.
# STATUS: UNTESTED (documented from published OpenAPI spec only)
# query params (from spec): userId
# --- example (not executed unless marked TESTED above) ---
curl -sS "$ENGINE/api/proxy/roblox-user-avatar-3d?userId=<assetId>"

#------------------------------------------------------------------------
# GET /api/proxy/roblox-3d-file  --  Proxy Roblox 3D File
# Proxies requests to the Roblox CDN (rbxcdn.com) to bypass CORS.
# STATUS: UNTESTED (documented from published OpenAPI spec only)
# query params (from spec): url
# --- example (not executed unless marked TESTED above) ---
curl -sS "$ENGINE/api/proxy/roblox-3d-file?url=<assetId>"

#------------------------------------------------------------------------
# GET /api/proxy/roblox-toolbox  --  Proxy Roblox Toolbox
# Proxies search requests to the Roblox Toolbox Service API (Creator Store).
# STATUS: UNTESTED (documented from published OpenAPI spec only)
# --- example (not executed unless marked TESTED above) ---
curl -sS "$ENGINE/api/proxy/roblox-toolbox"

#------------------------------------------------------------------------
# GET /api/proxy/roblox-catalog  --  Proxy Roblox Catalog
# Proxies search requests to the Roblox Catalog API (Avatar Emotes/Animations).
# STATUS: UNTESTED (documented from published OpenAPI spec only)
# --- example (not executed unless marked TESTED above) ---
curl -sS "$ENGINE/api/proxy/roblox-catalog"

#------------------------------------------------------------------------
# GET /api/asset/{asset_id}  --  Get Asset Info
# Retrieves and caches Roblox asset metadata.
# STATUS: UNTESTED (documented from published OpenAPI spec only)
# --- example (not executed unless marked TESTED above) ---
curl -sS "$ENGINE/api/asset/{asset_id}"

#------------------------------------------------------------------------
# GET /api/download/{asset_id}  --  Download Asset
# Fetches and downloads a single asset to local server storage.
# STATUS: UNTESTED (documented from published OpenAPI spec only)
# query params (from spec): custom_name, place_id
# --- example (not executed unless marked TESTED above) ---
curl -sS "$ENGINE/api/download/{asset_id}?custom_name=<assetId>"

#------------------------------------------------------------------------
# POST /api/download/batch  --  Download Batch
# Concurrently downloads multiple asset IDs, generating a ZIP package if successful downloads > 1.
# STATUS: UNTESTED (documented from published OpenAPI spec only)
# body schema: BatchDownloadRequest  (see spoofer-engine-openapi.json -> components.schemas)
# --- example (not executed unless marked TESTED above) ---
curl -sS -X POST -H "Content-Type: application/json" \
  -d '{}  # see schema: BatchDownloadRequest' \
  "$ENGINE/api/download/batch"

#------------------------------------------------------------------------
# POST /api/download/batch/async  --  Download Batch Async
# Asynchronously downloads multiple asset IDs in the background, returning a task_id immediately.
# STATUS: TESTED validation-only: 400 + 422 (responses/18,29,30)
# body schema: BatchDownloadRequest  (see spoofer-engine-openapi.json -> components.schemas)
# --- example (not executed unless marked TESTED above) ---
curl -sS -X POST -H "Content-Type: application/json" \
  -d '{}  # see schema: BatchDownloadRequest' \
  "$ENGINE/api/download/batch/async"

#------------------------------------------------------------------------
# GET /api/task/{task_id}/status  --  Get Task Status
# Retrieves the progress and results of a background download task.
# STATUS: TESTED 404 with bogus id (responses/14)
# --- example (not executed unless marked TESTED above) ---
curl -sS "$ENGINE/api/task/{task_id}/status"

#------------------------------------------------------------------------
# POST /api/upload/batch  --  Upload Batch
# Concurrently uploads multiple locally downloaded asset files to Roblox Open Cloud.
# STATUS: TESTED validation-only: 422 (responses/19)
# body schema: UploadBatchRequest  (see spoofer-engine-openapi.json -> components.schemas)
# --- example (not executed unless marked TESTED above) ---
curl -sS -X POST -H "Content-Type: application/json" \
  -d '{}  # see schema: UploadBatchRequest' \
  "$ENGINE/api/upload/batch"

#------------------------------------------------------------------------
# GET /api/scan/place/{place_id}  --  Scan Place
# Scans a Place ID for asset references (Audio, Animations, Emotes) with pagination support.
Accepts either Authorization: Bearer {oauth_token} or x-roblox-cookie: {ROBLOSECURITY}.
# STATUS: UNTESTED (documented from published OpenAPI spec only)
# query params (from spec): page, limit
# --- example (not executed unless marked TESTED above) ---
curl -sS "$ENGINE/api/scan/place/{place_id}?page=<assetId>"

#------------------------------------------------------------------------
# GET /api/files/download/{filename}  --  Serve Downloaded File
# Secure endpoint to serve downloaded asset files while preventing path traversal attacks.
# STATUS: UNTESTED (documented from published OpenAPI spec only)
# query params (from spec): inline
# --- example (not executed unless marked TESTED above) ---
curl -sS "$ENGINE/api/files/download/{filename}?inline=<assetId>"

#------------------------------------------------------------------------
# GET /api/files/zips/{filename}  --  Serve Zip Archive
# Secure endpoint to serve batch zip packages.
# STATUS: UNTESTED (documented from published OpenAPI spec only)
# --- example (not executed unless marked TESTED above) ---
curl -sS "$ENGINE/api/files/zips/{filename}"

