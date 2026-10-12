$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
Get-Command ffmpeg, ffprobe -ErrorAction Stop | Select-Object Name,Source
& '.venv\Scripts\python.exe' -m renderer.cli doctor
if ($LASTEXITCODE) { throw 'Dependency or PGN check failed' }
& '.venv\Scripts\python.exe' -m pytest -q
if ($LASTEXITCODE) { throw 'Tests failed' }
