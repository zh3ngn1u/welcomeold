# Complete Workflows

Five distinct workflows are implemented. All are reconstructed from the call sites in
`../js/0nh-y8e1a0l~a.js`.

---

## WORKFLOW 1 — Free spoof (single or bulk, no coins)

```
INPUT      textarea (eg) — LUA table or bare IDs, auto-pasted from clipboard
   │       (clipboard auto-read fires 800 ms after >10 chars land in the field)
   ▼
VALIDATE   sQ(raw)  →  [{id, custom_name}]      /\d{9,18}/, dedupe, default "Asset #<id>"
   │       0 items  → toast "Invalid input format! …"
   │       >500     → toast "Maximum of 500 IDs in a single bulk process!"
   ▼
PRE-CHECK  POST /api/auth/spoofer-check-cost  {asset_ids}
   │       → cost, has_ugc  → cost modal ("Free Spoof" button when is_free)
   ▼
SUBMIT     POST engine /api/download/batch/async
   │       headers: Content-Type: application/json
   │               (NO X-Roblox-Cookie when is_free === true)
   │       body:    {assets:[…], is_free:true}
   │       ← {task_id}
   │       persist localStorage.bmk_spoofer_active_task
   ▼
JOB        (no /api/spoofer-jobs row — audit is only written for paid runs)
   ▼
QUEUE      setInterval(1500) → GET engine /api/task/{id}/status
   │       queue_position ≠ null → "Waiting Queue (n/total)"
   │       assets[].status: processing → success | failed
   │       per-asset change → timestamped line into bmk_spoofer_logs
   │       404 → clearInterval, drop the stored task
   ▼
TERMINAL   asset_type === "Place" → "Bypass feature for Place/Game is currently unavailable."
   │       zip_download_url       → bmk_spoofer_active_zip, "ZIP is ready"
   │       neither                → "Asset might be private or ID is invalid."
   ▼
RESULT     per-asset rows: status, file_name, file_size, asset_type,
   │       "New Spoofed ID" = uploaded_asset_id
   ▼
DOWNLOAD   sZ(zip_download_url, name) → blob → object URL → <a download>
           fallback: window.open in a tab
   ▼
BALANCE    POST /api/auth/spoofer-state {task_id}   (still reconciled, even when free)
```

## WORKFLOW 2 — Paid spoof (coins)

```
…same through PRE-CHECK…
   ▼
DEDUCT     s4 → POST /api/auth/spoofer-deduct {asset_count, asset_ids}
   │       → coins / newCoins → update the balance display
   ▼
AUDIT      POST /api/spoofer-jobs {job_id:"pending", total_assets, 0, 0, asset_breakdown:{}}
   ▼
SUBMIT     POST engine /api/download/batch/async
   │       X-Roblox-Cookie attached when a cookie was pasted
   ▼
POLL/TERMINAL as Workflow 1, PLUS on every asset-status change and at terminal:
   PATCH /api/spoofer-jobs/:id
     {status, success_count, failed_count,
      asset_breakdown:{Type:{success,failed}},
      files:[{id,custom_name,status,file_name,file_size,asset_type,
               uploaded_asset_id,upload_status,upload_error}],
      logs: logs.slice(-500)}
   ▼
BALANCE    POST /api/auth/spoofer-state {task_id}
```

## WORKFLOW 3 — Coin top-up, then auto-resume the job

This is the least obvious flow: **paying for coins restarts the batch automatically.**

```
TRIGGER    "Buy coins" → s3(method)
   │       state sn = "qris" | "paypal"
   ▼
QRIS       POST /api/payment/create-coin-invoice {coins, paymentMethod:"qris"}
   │       → qrString, trxId, totalTransfer, isCoinTopUp
   │       QR rendered client-side from api.qrserver.com; "Save QRIS" downloads a PNG
   ▼
POLL       setInterval(3000) → GET /api/payment/check/:trxId
   │       (only fires when method==="qris" && trxId && qrString)
   │
   ├─ status === "SUCCESS"
   │    ├─ new Audio("/audio/cashsound.mp3").play()
   │    ├─ if isCoinTopUp:
   │    │     toast "Top Up successful! An additional N Coins have been added."
   │    │     set coins (t.coins if numeric, else += invoice coins)
   │    │     GET /api/auth/spoofer-state  → re-sync coins + history
   │    └─ else:  ← the auto-resume branch
   │          toast "Payment verified! Processing Bulk Spoofer…"
   │          sQ(textarea)  →  s5(assets)        ← Workflow 1/2 continues automatically
   │
   └─ status in ["EXPIRED","CANCELED"] → clearInterval, toast "Payment expired or canceled"
   ▼
PAYPAL     POST /api/payment/paypal/create-coin-order {coins}
   │       PayPal SDK onApprove →
   │       POST /api/payment/paypal/capture-coin-order {paypalOrderId, orderId, coins}
   │       (onCancel / onError / "closed"|"destroyed" are handled)
```

## WORKFLOW 4 — Upload results into your own Roblox experience

```
ENTRY      after a completed batch, choose a target: User or Group
   │       creator_type = roblox_id ? "Group" : "User"
   ▼
LOOP       for each successful asset, ONE request, strictly serial:
   │         POST engine /api/upload/batch
   │           {files:[<one asset>], roblox_access_token,
   │            creator_id, creator_type}
   │         ← {results:[{success, asset_id, error}]}
   │
   ├─ ok   → uploaded_asset_id recorded; row shows "New Spoofed ID"
   │
   ├─ 401 / 403, or error containing "401" / "invalid token"
   │      └─ SILENT REFRESH + RETRY  ← the retry feature
   │           POST /api/auth/roblox/refresh {from:"spoofer"}
   │           ← robloxAccessToken
   │           update userAtom.spoofer_state.roblox.roblox_access_token
   │           log "Session refreshed successfully. Retrying asset upload…"
   │           re-attempt the SAME asset
   │
   │      └─ refresh failed → log "Session token expired and silent refresh failed.
   │                          Aborting remaining uploads."
   │                         toast "Roblox session expired and failed to renew.
   │                               Upload aborted."
   │                         all remaining assets ← upload_status:"failed",
   │                                              upload_error:"Aborted"
   ▼
SUMMARY    "Upload process completed. Success: N, Failed: M"
   │       success → "Successfully published N assets to Roblox Creator Dashboard"
   ▼
PERSIST    sX → PATCH /api/spoofer-jobs/:id with the updated files[] + logs
           localStorage.bmk_spoofer_downloads updated per asset
```

## WORKFLOW 5 — Result download (per asset and ZIP)

```
PER-ASSET  s0(asset) = basename(metadata.name || custom_name).replace(/[\\/:*?"<>|]/g,"_").trim()
                     + (file_name ? "." + extname(file_name) : fallback)
   │       sZ(url, filename)
   ▼
BLOB       fetch(url)  →  !ok ⇒ throw  →  res.blob()
   │       URL.createObjectURL(blob) → temp <a download=name> → .click() → revokeObjectURL
   ▼
FALLBACK   on any throw: console.error("Force download failed, falling back to open in tab")
           a.href = url; a.target = "_blank"; a.click()

ZIP        identical path, url = zip_download_url, name from bmk_spoofer_active_zip
```

**There is no signed URL, no `Content-Disposition` handling in JS, and no server-side download
token in the code.** The `zip_download_url` is fetched with a plain `fetch` and turned into a
blob. The engine exposes `GET /api/files/download/{filename}` and `GET /api/files/zips/{filename}`
in its spec, but this page obtains its URLs from the task-status response instead.

---

## Cross-cutting: resume-after-reload

```
page load → localStorage.bmk_spoofer_active_task
          → { task_id, parsedAssets, isSingle, batchId, startedAt }
          → sv(task_id), sN(isSingle), s1(task_id, parsedAssets, isSingle, batchId)
          → polling resumes immediately
```
Only **one** task can be active: `sS.current` is a single interval ref, and a new submission
clears the previous one. There is no server-side list of "my running jobs", so if the user
clears storage or opens a different device, the resume is lost and the job becomes orphaned.
