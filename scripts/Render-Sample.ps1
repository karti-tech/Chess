$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& '.venv\Scripts\python.exe' -m renderer.cli render --dry-run
if ($LASTEXITCODE) { throw 'Sample failed' }
