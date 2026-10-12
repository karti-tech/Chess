param([Parameter(Mandatory=$true)][string]$JobId)
$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$line=Get-Content '.env' | Where-Object { $_ -match '^CHESS_SERVICE_TOKEN=' } | Select-Object -First 1
$token=$line.Substring('CHESS_SERVICE_TOKEN='.Length)
$headers=@{'X-Chess-Token'=$token}
$job=Invoke-RestMethod "http://localhost:8765/jobs/$JobId" -Headers $headers
if ($job.status -ne 'succeeded') { throw 'Job has not passed rendering validation' }
Start-Process $job.result.video
$answer=Read-Host 'After reviewing the video and its source rights, type APPROVE to upload (privacy comes from config)'
if ($answer -ne 'APPROVE') { Write-Host 'No upload requested'; exit }
Invoke-RestMethod "http://localhost:8765/jobs/$JobId/publish" -Method Post -Headers $headers -ContentType 'application/json' -Body '{"approved":true}' -TimeoutSec 1800
