param([string]$Text='The king would like a refund.')
$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
Add-Type -AssemblyName System.Speech
New-Item -ItemType Directory -Force 'assets\sfx' | Out-Null
$synth=New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SetOutputToWaveFile((Join-Path (Get-Location) 'assets\sfx\narration.wav'))
$synth.Speak($Text)
$synth.Dispose()
Write-Host 'Generated optional local Windows speech. In config/local.json set tts_file to its absolute path and tts_license to Original text, Windows system speech; review voice terms.'
