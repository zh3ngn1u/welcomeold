#!/usr/bin/env bash
# 01_public_reads.sh — endpoints verified PUBLIC (no auth required)
# Every response body below was OBSERVED live on 2026-09-30. See ../responses/.
# Base: https://backend.blokmarket.store

BASE="https://backend.blokmarket.store"
CURL=(curl -sS -H "Accept: application/json")

echo "== GET /api/product/category  (200) =="
"${CURL[@]}" "$BASE/api/product/category"; echo; echo
echo "== GET /api/product  (200) =="
"${CURL[@]}" "$BASE/api/product"; echo; echo
echo "== GET /api/upload/health  (200) =="
"${CURL[@]}" "$BASE/api/upload/health"; echo; echo
echo "== GET /api/audio/approved-count  (200) =="
"${CURL[@]}" "$BASE/api/audio/approved-count"; echo; echo
echo "== GET /api/audio/approved-daily-stats  (200) =="
"${CURL[@]}" "$BASE/api/audio/approved-daily-stats"; echo;
