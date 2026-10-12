$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path '.venv\Scripts\python.exe')) { & "$PSScriptRoot\Setup.ps1" }
& '.venv\Scripts\python.exe' -c "from renderer.settings import load; import uvicorn; c=load(); uvicorn.run('renderer.service:app',host=c['host'],port=c['port'],workers=1,access_log=False)"
if ($LASTEXITCODE) { throw 'Service failed' }
