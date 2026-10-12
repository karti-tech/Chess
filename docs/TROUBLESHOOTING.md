# Troubleshooting

- **Python not found**: run `py -3.12 --version`. Install Python 3.12 with the Windows launcher. Setup creates an isolated `.venv`, so system Pillow/python-chess installations do not matter.
- **FFmpeg not found**: `Get-Command ffmpeg, ffprobe`. Put both executables on PATH, then open a fresh PowerShell. Use a trusted build with H.264 libx264/AAC support. Verification/TLS is never disabled.
- **PowerShell script policy**: the README uses process-specific `-ExecutionPolicy Bypass`; it does not permanently change machine policy. Inspect scripts before running downloaded software.
- **401**: renderer expects `X-Chess-Token`, not Bearer auth. Header credential value is the token only, without quotes or the variable name. Setup writes a random token to `.env`; read it privately. Restart service after token changes. Do not post it in support chat.
- **Docker ECONNREFUSED**: launch the service first, bind 0.0.0.0, check firewall/private network and port. Run Test-N8nConnection.ps1. This tests health without transmitting a credential. Docker Desktop normally provides host.docker.internal; Linux Docker may require `--add-host=host.docker.internal:host-gateway`.
- **Renderer failed/no unused game**: inspect `logs/<jobid>.log`, `output/<jobid>/ffmpeg.log` and job status. Add PGNs; dry-run allows previews without marking games used. A malformed game with parser errors is skipped, not repaired silently.
- **Invalid JSON/BOM**: settings accept UTF-8/BOM from PowerShell. Use forward slashes in Windows JSON paths, or double every backslash.
- **Wrong dimensions**: change width AND height together; supported pairs are 720/1280 and 1080/1920.
- **Slow render**: use 720 mode, keep one service worker, close heavy apps. CPU rendering is expected. A 45-minute poll timeout stops waiting, not an already-running render. Check existing status before resubmitting.
- **Queue full**: wait and poll. A request-key replay returns the original job. A different body with the same key returns 409.
- **No sound**: default procedural music needs no assets. Both volumes at zero fails validation; user audio requires a file and source/license entry. Check Windows media-player volume too.
- **OAuth access_denied**: add your account as an OAuth test user, confirm Desktop client, enable YouTube API and select the right channel account. A ChatGPT subscription is unrelated to API access. Do not use browser-login automation.
- **Upload uncertain/uploading after restart**: inspect YouTube Studio. Do not retry inserts or reset/delete database rows until you establish what happened. Normal repeat calls for a confirmed upload return its ID. There is no unsafe automatic recovery command.
- **Upload is private despite public request**: check Google API project verification/audit restrictions and YouTube Studio. API confirmation of an ID is not proof of finished processing or monetization approval.
- **Schedule doesn't run**: enable Schedule node, set timezone, publish/activate workflow in your n8n UI. Error Trigger only applies to automatic executions; manual failures are shown directly.
- **n8n version**: `docker exec n8n n8n --version` checks the actual container; `n8n --version` can refer to a different host installation.

## Authenticated API from PowerShell

Do not copy tokens into workflow JSON. Locally:

```powershell
$token = ((Get-Content .env | Where-Object { $_ -match '^CHESS_SERVICE_TOKEN=' }) -split '=',2)[1]
$headers = @{'X-Chess-Token'=$token}
$job = Invoke-RestMethod http://localhost:8765/jobs -Method Post -Headers $headers -ContentType application/json -Body '{"request_key":"local-test-001","dry_run":true,"target_seconds":15,"width":720,"height":1280}'
Invoke-RestMethod "http://localhost:8765/jobs/$($job.id)" -Headers $headers
```

Repeat the last command until succeeded/failed. `/ready` checks local prerequisites. `GET /jobs` lists recent history, `GET /jobs/{id}/video` returns only a succeeded video, and `POST /jobs/{id}/publish` needs `{"approved":true}` plus local OAuth and a non-dry successful job.
