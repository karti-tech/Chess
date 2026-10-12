$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path '.venv\Scripts\python.exe')) { py -3.12 -m venv .venv; if ($LASTEXITCODE) { throw 'Python 3.12 required' } }
& '.venv\Scripts\python.exe' -m pip install -r requirements.lock.txt
if ($LASTEXITCODE) { throw 'Dependency installation failed' }
if (-not (Test-Path '.env')) {
  & '.venv\Scripts\python.exe' -c "import secrets; from pathlib import Path; Path('.env').write_text('CHESS_SERVICE_TOKEN='+secrets.token_urlsafe(32)+'\nCHESS_AI_API_KEY=\n',encoding='utf-8')"
}
if (-not (Test-Path 'config\local.json')) {
  '{"host":"0.0.0.0","width":720,"height":1280}' | Set-Content -Encoding utf8 'config\local.json'
}
& '.venv\Scripts\python.exe' -m renderer.cli doctor
if ($LASTEXITCODE) { throw 'Doctor failed; see README troubleshooting' }
Write-Host 'Setup complete. Token is in .env; put it in an n8n Header Auth credential, not in workflow JSON.'
