#!/usr/bin/env bash
# 04_diagnostics.sh — auth-gate + routing probes, all responses OBSERVED 2026-09-30
set -u
BACKEND="https://backend.blokmarket.store"
ENGINE="https://spoofer.blokmarket.store"

echo "== GET /api/auth/me  (no Authorization) -> 401 {"success":false,"message":"No token"} =="
curl -sS -i -H "Accept: application/json" "$BACKEND/api/auth/me" | head -1; echo
curl -sS -H "Accept: application/json" "$BACKEND/api/auth/me"; echo; echo
echo "== POST /api/auth/refresh  (no cookie) -> 404 Endpoint not found =="
# NOTE: apiFetch calls this on every 401. It resolves 404, so the retry always fails.
curl -sS -i -X POST -H "Content-Type: application/json" --data '{}' "$BACKEND/api/auth/refresh" | head -1; echo
curl -sS -X POST -H "Content-Type: application/json" --data '{}' "$BACKEND/api/auth/refresh"; echo; echo
echo "== GET /api/admin/users  (no auth) -> 401 Unauthorized =="
curl -sS -H "Accept: application/json" "$BACKEND/api/admin/users"; echo; echo
echo "== CORS: backend reflects no Access-Control-Allow-Origin for foreign origin =="
curl -sS -i -X OPTIONS -H "Origin: https://evil.example" -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: authorization" "$BACKEND/api/auth/me" \
  | grep -i "^HTTP\|access-control" ; echo
echo "== CORS: engine DOES echo the caller origin + credentials =="
curl -sS -i -X OPTIONS -H "Origin: https://customer.blokmarket.store" -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,x-roblox-cookie" \
  "$ENGINE/api/download/batch/async" | grep -i "^HTTP\|access-control"; echo
