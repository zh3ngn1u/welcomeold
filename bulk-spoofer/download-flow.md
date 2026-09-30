# Download Mechanism

**One function does every download.** There is no signed-URL logic, no `Content-Disposition`
parsing, and no server-side download token anywhere in the page.

## The function (verbatim, `../js/0nh-y8e1a0l~a.js`)

```js
sZ = async (e, s) => {                                  // (url, filename)
  try {
    let t = await fetch(e);
    if (!t.ok) throw Error("Network response was not ok");
    let a = await t.blob();
    let i = window.URL.createObjectURL(a);
    let r = document.createElement("a");
    r.href = i; r.download = s;
    document.body.appendChild(r);
    r.click();
    document.body.removeChild(r);
    window.URL.revokeObjectURL(i);
  } catch (t) {
    console.error("Force download failed, falling back to open in tab:", t);
    let s = document.createElement("a");
    s.href = e; s.target = "_blank"; s.click();
  }
}
```

## Mechanism, step by step
| Step | Operation |
|---|---|
| 1 | `fetch(url)` — plain GET, **no** `Authorization`, **no** credentials mode |
| 2 | `!res.ok` → `throw Error("Network response was not ok")` → fallback branch |
| 3 | `res.blob()` — the whole file is buffered into memory |
| 4 | `URL.createObjectURL(blob)` |
| 5 | a detached `<a download="filename">` is appended, clicked, then removed |
| 6 | `revokeObjectURL` — the object URL is released immediately |
| 7 | on any throw: an `<a target="_blank">` is synthesised and clicked → **opens in a new tab** |

## Filename builder (per asset)
```js
s0 = (e, s = "") => {
  let t = e.file_name ? "." + e.file_name.split(".").pop() : s;   // extension
  let a = e.metadata?.name || e.custom_name;                        // basename
  a = a.replace(/[\\/:*?"<>|]/g, "_").trim();                       // sanitise
  return `${a}${t}`;
}
```
Precedence: `metadata.name` → `custom_name` → `""`, always sanitised, extension taken from
`file_name` when present.

## Where the URLs come from
| Output | Source field | Persisted to |
|---|---|---|
| Batch ZIP | `zip_download_url` in the task-status response | `localStorage.bmk_spoofer_active_zip` + `bmk_spoofer_active_zip_count` |
| Individual asset | per-asset URL, consumed at render time and passed to `sZ` | row state, and `bmk_spoofer_downloads` for upload status |
| QRIS QR | `https://api.qrserver.com/v1/create-qr-code/?data=<encodeURIComponent(qrString)>&size=600x600&bgcolor=ffffff&color=000000&margin=2` | not persisted; downloaded as `BLOKMARKET-QRIS-{totalTransfer||"Payment"}.png` |

## Blob vs ArrayBuffer
`blob()` ×2 — once in `sZ`, once for the QRIS PNG. `arrayBuffer()` appears **0** times in this
chunk. `URL.createObjectURL` ×2, `revokeObjectURL` ×2.

## Where the ZIP is actually built
**On the server.** The page contains **zero** references to `JSZip`, `generateAsync`, `.file(` or
`folder(`. The engine's own spec states it *"generat[es] a ZIP package if successful downloads > 1"*
(`POST /api/download/batch` → `BatchDownloadResponse.zip_download_url`), and the async variant
reuses the same machinery. The engine also exposes `GET /api/files/download/{filename}` and
`GET /api/files/zips/{filename}`, described as *"Secure endpoint to serve downloaded asset files
while preventing path traversal attacks"* — but this page obtains its URLs from the task-status
payload rather than by constructing them.

## Consequence worth knowing
`res.blob()` loads the **entire** file into browser memory before saving. A large ZIP from a
500-asset batch is fully buffered. If you re-implement, prefer streaming to a file handle, or
at least surface the size so the user is not surprised. The engine spec does not promise a size
limit on `zip_download_url`.

## What is NOT present
* No `signedUrl` / `X-Amz-Signature` / `Content-Disposition` handling.
* No `Range` requests, no resumable download, no progress bar for the transfer.
* No `navigator.share` / Web Share API, no File System Access API.
* No `sendBeacon` (0 hits).
