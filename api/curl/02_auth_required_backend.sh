#!/usr/bin/env bash
# 02_auth_required_backend.sh — every endpoint declared in the client apiEndpoints map
#
# ALL of these returned 401 {"success":false,"message":"Unauthorized"} (or
# {"success":false,"message":"No token"} for /auth/me) when called WITHOUT a token.
# NONE were executed with a token: no credentials were provided for this environment and
# none were guessed. Every block below is therefore UNTESTED-BY-AUTH.
#
# HOW THE FRONTEND SUPPLIES AUTH (verbatim from the bundle):
#   1. OAuth popup postMessage handler -> localStorage["bmk_token"] = <jwt>
#   2. apiFetch sends Authorization: Bearer <bmk_token>  +  credentials: "include"
#   3. On 401: POST /api/auth/refresh once, retry; on failure hard-redirect to /login.
#      (NOTE: /api/auth/refresh currently answers 404 — see 04_diagnostics.sh)
#
# export BMK_TOKEN="<paste your own bmk_token here>"
set -u
BASE="https://backend.blokmarket.store"
BMK_TOKEN="${BMK_TOKEN:-}"
[ -n "$BMK_TOKEN" ] || echo "!! set BMK_TOKEN first (this script never fabricates a token)"
AUTH=(-H "Authorization: Bearer $BMK_TOKEN" -H "Content-Type: application/json" --cookie-jar /tmp/bmk.jar)

#------------------------------------------------------------------------
# ADMIN
#------------------------------------------------------------------------
# --- admin.activateExperience | METHOD-NOT-OBSERVED /admin/experience/activated/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/experience/activated/:<param>"

# --- admin.addExperience | METHOD-NOT-OBSERVED /admin/users/:<param>/experiences | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/users/:<param>/experiences"

# --- admin.assets | METHOD-NOT-OBSERVED /admin/assets | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/assets"

# --- admin.b2bAdjustCredits | METHOD-NOT-OBSERVED /admin/b2b/tenants/:<param>/credits | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/b2b/tenants/:<param>/credits"

# --- admin.b2bToggleStatus | METHOD-NOT-OBSERVED /admin/b2b/tenants/:<param>/toggle-status | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/b2b/tenants/:<param>/toggle-status"

# --- admin.changeRole | METHOD-NOT-OBSERVED /admin/users/change-role/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/users/change-role/:<param>"

# --- admin.createProduct | METHOD-NOT-OBSERVED /admin/product | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/product"

# --- admin.createProductCategory | METHOD-NOT-OBSERVED /admin/product/category | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/product/category"

# --- admin.deleteAsset | METHOD-NOT-OBSERVED /admin/assets/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/assets/:<param>"

# --- admin.deleteExperience | METHOD-NOT-OBSERVED /admin/experience/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/experience/:<param>"

# --- admin.deleteProduct | METHOD-NOT-OBSERVED /admin/product/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/product/:<param>"

# --- admin.deleteProductCategory | METHOD-NOT-OBSERVED /admin/product/category/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/product/category/:<param>"

# --- admin.deleteUser | DELETE /admin/users/:<param> | call site: 04-8vca-nl7ws.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/users/:<param>"

# --- admin.experienceDetail | METHOD-NOT-OBSERVED /admin/experience/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/experience/:<param>"

# --- admin.experienceList | METHOD-NOT-OBSERVED /admin/experiences | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/experiences"

# --- admin.limitExperience | METHOD-NOT-OBSERVED /admin/users/limit-experience/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/users/limit-experience/:<param>"

# --- admin.paymentHistory | METHOD-NOT-OBSERVED /admin/payment-history | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/payment-history"

# --- admin.updateExperience | METHOD-NOT-OBSERVED /admin/experience/update/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/experience/update/:<param>"

# --- admin.updateProduct | METHOD-NOT-OBSERVED /admin/product/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/product/:<param>"

# --- admin.userDetail | METHOD-NOT-OBSERVED /admin/users/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/users/:<param>"

# --- admin.users | GET,POST /admin/users | call site: 04-8vca-nl7ws.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/admin/users"

#------------------------------------------------------------------------
# AUDIO
#------------------------------------------------------------------------
# --- audio.approvedCount | GET /audio/approved-count | call site: 0yht7~1hzhuyh.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/audio/approved-count"

# --- audio.approvedDailyStats | GET /audio/approved-daily-stats | call site: 0yht7~1hzhuyh.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/audio/approved-daily-stats"

# --- audio.connectRobloxMap | POST /audio/roblox-maps | call site: 0dxjv5~eww.do.js
# request body verbatim from call site:
#   {universe_id:t,api_key:s,map_name:o.trim()||void 0}
curl -X POST -sS ""${AUTH[@]}"" -d '{universe_id:t,api_key:s,map_name:o.trim()||void 0}' "$BASE/audio/roblox-maps"

# --- audio.convert | POST /audio/convert | call site: 068smn5x07xhr.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/audio/convert"

# --- audio.deleteHistory | DELETE /audio/history/:<param> | call site: 0dxjv5~eww.do.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/audio/history/:<param>"

# --- audio.deleteRobloxMap | DELETE /audio/roblox-maps/:<param> | call site: 0dxjv5~eww.do.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/audio/roblox-maps/:<param>"

# --- audio.getRobloxMaps | GET /audio/roblox-maps | call site: 0dxjv5~eww.do.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/audio/roblox-maps"

# --- audio.history | METHOD-NOT-OBSERVED /audio/history | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/audio/history"

# --- audio.preview | METHOD-NOT-OBSERVED /audio/preview | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/audio/preview"

# --- audio.publishToGame | POST /audio/publish-to-game | call site: 0dxjv5~eww.do.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/audio/publish-to-game"

# --- audio.renameRobloxMap | PATCH /audio/roblox-maps/:<param> | call site: 0dxjv5~eww.do.js
# request body verbatim from call site:
#   {name:z.trim()}
curl -X PATCH -sS ""${AUTH[@]}"" -d '{name:z.trim()}' "$BASE/audio/roblox-maps/:<param>"

# --- audio.saveHistory | POST /audio/history | call site: 068smn5x07xhr.js
# request body verbatim from call site:
#   {filename:h,asset_id:String(s),status:n}
curl -X POST -sS ""${AUTH[@]}"" -d '{filename:h,asset_id:String(s),status:n}' "$BASE/audio/history"

# --- audio.status | GET /audio/status/:<param> | call site: 068smn5x07xhr.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/audio/status/:<param>"

# --- audio.updateHistory | PATCH /audio/history/:<param> | call site: 068smn5x07xhr.js
# request body verbatim from call site:
#   {asset_id:String(s),status:n,filename:h}
curl -X PATCH -sS ""${AUTH[@]}"" -d '{asset_id:String(s),status:n,filename:h}' "$BASE/audio/history/:<param>"

# --- audio.uploadConvert | POST /audio/upload-convert | call site: 068smn5x07xhr.js
# multipart/form-data (see endpoints.md for confirmed field names)
# curl -X POST -sS ""${AUTH[@]}"" -F "field=value" "$BASE/audio/upload-convert"

# --- audio.uploadRoblox | POST /audio/upload-roblox | call site: 068smn5x07xhr.js
# request body verbatim from call site:
#   {job_id:String(t),filename:String(e),access_token:a,user_id:ai||String(ew?.roblox_id||""),is_group:ew?.roblox_refresh_token==="roblox_api_key"?ew?.roblox_display_name==="Group":!!ai&&ai!==String(ew?.roblox_id),display_name:x}
curl -X POST -sS ""${AUTH[@]}"" -d '{job_id:String(t),filename:String(e),access_token:a,user_id:ai||String(ew?.roblox_id||""),is_group:ew?.roblox_refresh_token==="roblox_api_key"?ew?.roblox_display_name==="Group":!!ai&&ai!==String(ew?.roblox_id),display_name:x}' "$BASE/audio/upload-roblox"

#------------------------------------------------------------------------
# AUTH
#------------------------------------------------------------------------
# --- auth.googleLogin | METHOD-NOT-OBSERVED /auth/google/login | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/auth/google/login"

# --- auth.login | METHOD-NOT-OBSERVED /auth/login | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/auth/login"

# --- auth.logout | METHOD-NOT-OBSERVED /auth/logout | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/auth/logout"

# --- auth.me | GET,POST /auth/me | call site: 068smn5x07xhr.js, 0a6h4o63da-vz.js, 0dxjv5~eww.do.js, 0nh-y8e1a0l~a.js, 0yomchjmrny8f.js, 11wojmndz1p1s.js
# request body verbatim from call site:
#   {plan_type:te.plan_type}
curl -X GET -sS ""${AUTH[@]}"" -d '{plan_type:te.plan_type}' "$BASE/auth/me"

# --- auth.refresh | METHOD-NOT-OBSERVED /auth/refresh | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/auth/refresh"

# --- auth.register | METHOD-NOT-OBSERVED /auth/register | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/auth/register"

# --- auth.robloxGroups | GET,POST /auth/roblox/groups | call site: 068smn5x07xhr.js, 0yomchjmrny8f.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/auth/roblox/groups"

# --- auth.robloxLogin | METHOD-NOT-OBSERVED /auth/roblox/login | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/auth/roblox/login"

# --- auth.robloxRefresh | POST /auth/roblox/refresh | call site: 068smn5x07xhr.js, 0nh-y8e1a0l~a.js
# request body verbatim from call site:
#   {from:"spoofer"}
curl -X POST -sS ""${AUTH[@]}"" -d '{from:"spoofer"}' "$BASE/auth/roblox/refresh"

# --- auth.robloxSaveApiKey | POST /auth/roblox/save-api-key | call site: 0a8pu3n7fv_vz.js
# request body verbatim from call site:
#   {apiKey:P.trim(),creatorId:B.trim(),creatorType:O,from:"audio"===e?void 0:e}
curl -X POST -sS ""${AUTH[@]}"" -d '{apiKey:P.trim(),creatorId:B.trim(),creatorType:O,from:"audio"===e?void 0:e}' "$BASE/auth/roblox/save-api-key"

# --- auth.robloxUnlink | POST /auth/roblox/unlink | call site: 068smn5x07xhr.js, 0a8pu3n7fv_vz.js, 0yomchjmrny8f.js
# request body verbatim from call site:
#   {from:"audio"}
curl -X POST -sS ""${AUTH[@]}"" -d '{from:"audio"}' "$BASE/auth/roblox/unlink"

# --- auth.spooferDeduct | POST /auth/spoofer-deduct | call site: 0nh-y8e1a0l~a.js
# request body verbatim from call site:
#   {asset_count:e.length,asset_ids:e.map(e=>e.id)}
curl -X POST -sS ""${AUTH[@]}"" -d '{asset_count:e.length,asset_ids:e.map(e=>e.id)}' "$BASE/auth/spoofer-deduct"

# --- auth.spooferState | GET,POST /auth/spoofer-state | call site: 0nh-y8e1a0l~a.js
# request body verbatim from call site:
#   {coins:e}
curl -X GET -sS ""${AUTH[@]}"" -d '{coins:e}' "$BASE/auth/spoofer-state"

#------------------------------------------------------------------------
# B2B
#------------------------------------------------------------------------
# --- b2b.analytics | POST /b2b/portal/analytics?days=:<param> | call site: 0o45.cg_g4a77.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/b2b/portal/analytics?days=:<param>"

# --- b2b.logs | GET /b2b/portal/logs?page=:<param>&limit=:<param> | call site: 0o45.cg_g4a77.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/b2b/portal/logs?page=:<param>&limit=:<param>"

# --- b2b.pricing | METHOD-NOT-OBSERVED /b2b/portal/pricing | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/b2b/portal/pricing"

# --- b2b.rotateKey | POST /b2b/portal/key/rotate | call site: 0o45.cg_g4a77.js
# request body verbatim from call site:
#   {webhookUrl:x}
curl -X POST -sS ""${AUTH[@]}"" -d '{webhookUrl:x}' "$BASE/b2b/portal/key/rotate"

# --- b2b.status | GET /b2b/portal/status | call site: 0o45.cg_g4a77.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/b2b/portal/status"

# --- b2b.topup | METHOD-NOT-OBSERVED /b2b/portal/topup | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/b2b/portal/topup"

# --- b2b.updateWebhook | PUT /b2b/portal/webhook | call site: 0o45.cg_g4a77.js
# request body verbatim from call site:
#   {webhookUrl:x}
curl -X PUT -sS ""${AUTH[@]}"" -d '{webhookUrl:x}' "$BASE/b2b/portal/webhook"

#------------------------------------------------------------------------
# DONATION
#------------------------------------------------------------------------
# --- donation.bypassLogs | METHOD-NOT-OBSERVED /donation/bypass-logs | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/donation/bypass-logs"

# --- donation.donaturLeaderboard | METHOD-NOT-OBSERVED /donation/donatur-leaderboard | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/donation/donatur-leaderboard"

# --- donation.history | METHOD-NOT-OBSERVED /donation/history | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/donation/history"

#------------------------------------------------------------------------
# EXPERIENCE
#------------------------------------------------------------------------
# --- experience.activate | METHOD-NOT-OBSERVED /experience/activated/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/experience/activated/:<param>"

# --- experience.create | POST /experience | call site: 0f8dbzohbyw1o.js
# multipart/form-data (see endpoints.md for confirmed field names)
# curl -X POST -sS ""${AUTH[@]}"" -F "field=value" "$BASE/experience"

# --- experience.delete | METHOD-NOT-OBSERVED /experience/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/experience/:<param>"

# --- experience.detail | METHOD-NOT-OBSERVED /experience/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/experience/:<param>"

# --- experience.myList | GET /experience/my-list | call site: 0f8dbzohbyw1o.js, 0yht7~1hzhuyh.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/experience/my-list"

#------------------------------------------------------------------------
# PAYMENT
#------------------------------------------------------------------------
# --- payment.capturePayPalAudioOrder | POST /payment/paypal/capture-audio-order | call site: 068smn5x07xhr.js
# request body verbatim from call site:
#   {paypalOrderId:e.orderID,orderId:tl.current||te.trxId||e.orderID,plan_type:te.plan_type}
curl -X POST -sS ""${AUTH[@]}"" -d '{paypalOrderId:e.orderID,orderId:tl.current||te.trxId||e.orderID,plan_type:te.plan_type}' "$BASE/payment/paypal/capture-audio-order"

# --- payment.capturePayPalB2BOrder | POST /payment/paypal/capture-b2b-order | call site: 0o45.cg_g4a77.js
# request body verbatim from call site:
#   {paypalOrderId:e.orderID,orderId:eB.current||eN.trxId||e.orderID,item_id:eN.itemId,item_type:eN.itemType}
curl -X POST -sS ""${AUTH[@]}"" -d '{paypalOrderId:e.orderID,orderId:eB.current||eN.trxId||e.orderID,item_id:eN.itemId,item_type:eN.itemType}' "$BASE/payment/paypal/capture-b2b-order"

# --- payment.capturePayPalCoinOrder | POST /payment/paypal/capture-coin-order | call site: 0nh-y8e1a0l~a.js
# request body verbatim from call site:
#   {paypalOrderId:e.orderID,orderId:sx.current||eT.trxId||e.orderID,coins:eT.coins||60}
curl -X POST -sS ""${AUTH[@]}"" -d '{paypalOrderId:e.orderID,orderId:sx.current||eT.trxId||e.orderID,coins:eT.coins||60}' "$BASE/payment/paypal/capture-coin-order"

# --- payment.capturePayPalUploadOrder | POST /payment/paypal/capture-upload-order | call site: 0yomchjmrny8f.js
# request body verbatim from call site:
#   {paypalOrderId:e.orderID,orderId:eM.current||e.orderID}
curl -X POST -sS ""${AUTH[@]}"" -d '{paypalOrderId:e.orderID,orderId:eM.current||e.orderID}' "$BASE/payment/paypal/capture-upload-order"

# --- payment.checkStatus | GET,POST /payment/check/:<param> | call site: 068smn5x07xhr.js, 0nh-y8e1a0l~a.js, 0o45.cg_g4a77.js, 0yomchjmrny8f.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/payment/check/:<param>"

# --- payment.createAudioInvoice | POST /payment/create-audio-invoice | call site: 068smn5x07xhr.js
# request body verbatim from call site:
#   {plan_type:e}
curl -X POST -sS ""${AUTH[@]}"" -d '{plan_type:e}' "$BASE/payment/create-audio-invoice"

# --- payment.createB2BInvoice | POST /payment/create-b2b-invoice | call site: 0o45.cg_g4a77.js
# request body verbatim from call site:
#   {item_id:eN.itemId,item_type:eN.itemType}
curl -X POST -sS ""${AUTH[@]}"" -d '{item_id:eN.itemId,item_type:eN.itemType}' "$BASE/payment/create-b2b-invoice"

# --- payment.createCoinInvoice | POST /payment/create-coin-invoice | call site: 0nh-y8e1a0l~a.js
# request body verbatim from call site:
#   {coins:e,paymentMethod:"qris"}
curl -X POST -sS ""${AUTH[@]}"" -d '{coins:e,paymentMethod:"qris"}' "$BASE/payment/create-coin-invoice"

# --- payment.createPayPalAudioOrder | POST /payment/paypal/create-audio-order | call site: 068smn5x07xhr.js
# request body verbatim from call site:
#   {plan_type:te.plan_type}
curl -X POST -sS ""${AUTH[@]}"" -d '{plan_type:te.plan_type}' "$BASE/payment/paypal/create-audio-order"

# --- payment.createPayPalB2BOrder | POST /payment/paypal/create-b2b-order | call site: 0o45.cg_g4a77.js
# request body verbatim from call site:
#   {item_id:eN.itemId,item_type:eN.itemType}
curl -X POST -sS ""${AUTH[@]}"" -d '{item_id:eN.itemId,item_type:eN.itemType}' "$BASE/payment/paypal/create-b2b-order"

# --- payment.createPayPalCoinOrder | POST /payment/paypal/create-coin-order | call site: 0nh-y8e1a0l~a.js
# request body verbatim from call site:
#   {coins:eT.coins||60}
curl -X POST -sS ""${AUTH[@]}"" -d '{coins:eT.coins||60}' "$BASE/payment/paypal/create-coin-order"

# --- payment.createPayPalUploadOrder | POST /payment/paypal/create-upload-order | call site: 0yomchjmrny8f.js
# request body verbatim from call site:
#   {}
curl -X POST -sS ""${AUTH[@]}"" -d '{}' "$BASE/payment/paypal/create-upload-order"

# --- payment.createUploadInvoice | POST /payment/create-upload-invoice | call site: 0yomchjmrny8f.js
# request body verbatim from call site:
#   {}
curl -X POST -sS ""${AUTH[@]}"" -d '{}' "$BASE/payment/create-upload-invoice"

#------------------------------------------------------------------------
# PRODUCT
#------------------------------------------------------------------------
# --- product.categoryList | METHOD-NOT-OBSERVED /product/category | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/product/category"

# --- product.detail | METHOD-NOT-OBSERVED /product/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/product/:<param>"

# --- product.globalAssets | METHOD-NOT-OBSERVED /product/global-assets | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/product/global-assets"

# --- product.list | METHOD-NOT-OBSERVED /product | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/product"

#------------------------------------------------------------------------
# REFERRAL
#------------------------------------------------------------------------
# --- referral.adminOverview | METHOD-NOT-OBSERVED /referral/admin/overview | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/referral/admin/overview"

# --- referral.adminUpdateWithdrawal | METHOD-NOT-OBSERVED /referral/admin/withdrawals/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/referral/admin/withdrawals/:<param>"

# --- referral.commissions | METHOD-NOT-OBSERVED /referral/commissions | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/referral/commissions"

# --- referral.info | METHOD-NOT-OBSERVED /referral/info | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/referral/info"

# --- referral.join | METHOD-NOT-OBSERVED /referral/join | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/referral/join"

# --- referral.withdraw | METHOD-NOT-OBSERVED /referral/withdraw | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/referral/withdraw"

# --- referral.withdrawals | METHOD-NOT-OBSERVED /referral/withdrawals | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/referral/withdrawals"

#------------------------------------------------------------------------
# SPOOFERJOBS
#------------------------------------------------------------------------
# --- spooferJobs.adminList | METHOD-NOT-OBSERVED /spoofer-jobs/admin/all | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/spoofer-jobs/admin/all"

# --- spooferJobs.create | POST /spoofer-jobs | call site: 0nh-y8e1a0l~a.js
# request body verbatim from call site:
#   {job_id:l,status:"pending",total_assets:e.length,success_count:0,failed_count:0,asset_breakdown:{},files:s,zip_url:null,logs:t}
curl -X POST -sS ""${AUTH[@]}"" -d '{job_id:l,status:"pending",total_assets:e.length,success_count:0,failed_count:0,asset_breakdown:{},files:s,zip_url:null,logs:t}' "$BASE/spoofer-jobs"

# --- spooferJobs.detail | GET /spoofer-jobs/:<param> | call site: 0dxjv5~eww.do.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/spoofer-jobs/:<param>"

# --- spooferJobs.list | METHOD-NOT-OBSERVED /spoofer-jobs | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/spoofer-jobs"

# --- spooferJobs.update | PATCH /spoofer-jobs/:<param> | call site: 0nh-y8e1a0l~a.js
# request body verbatim from call site:
#   {status:c,success_count:n,failed_count:l,asset_breakdown:o,files:r,logs:Array.isArray(i)?i.slice(-500):[]}
curl -X PATCH -sS ""${AUTH[@]}"" -d '{status:c,success_count:n,failed_count:l,asset_breakdown:o,files:r,logs:Array.isArray(i)?i.slice(-500):[]}' "$BASE/spoofer-jobs/:<param>"

#------------------------------------------------------------------------
# UPLOAD
#------------------------------------------------------------------------
# --- upload.batch | POST /upload/batch | call site: 0yomchjmrny8f.js
# request body verbatim from call site:
#   {item_index:e}
curl -X POST -sS ""${AUTH[@]}"" -d '{item_index:e}' "$BASE/upload/batch"

# --- upload.deleteJob | METHOD-NOT-OBSERVED /upload/jobs/:<param> | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/upload/jobs/:<param>"

# --- upload.health | METHOD-NOT-OBSERVED /upload/health | NO call site in downloaded chunks
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/upload/health"

# --- upload.jobStatus | GET /upload/jobs/:<param> | call site: 0yomchjmrny8f.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/upload/jobs/:<param>"

# --- upload.list | GET /upload/jobs?page=:<param>&limit=:<param> | call site: 0dxjv5~eww.do.js, 0yomchjmrny8f.js
# method not observed in the bundle — confirm before use
# curl -sS ""${AUTH[@]}"" "$BASE/upload/jobs?page=:<param>&limit=:<param>"

# --- upload.quota | POST /upload/quota | call site: 0yomchjmrny8f.js
# request body verbatim from call site:
#   {}
curl -X POST -sS ""${AUTH[@]}"" -d '{}' "$BASE/upload/quota"

# --- upload.retry | POST /upload/jobs/:<param>/retry | call site: 0yomchjmrny8f.js
# request body verbatim from call site:
#   {item_index:e}
curl -X POST -sS ""${AUTH[@]}"" -d '{item_index:e}' "$BASE/upload/jobs/:<param>/retry"

