param([string]$Container='n8n')
$ErrorActionPreference='Stop'
docker exec $Container node -e "fetch('http://host.docker.internal:8765/health').then(async r=>{console.log(r.status,await r.text());if(!r.ok)process.exit(1)}).catch(e=>{console.error(e.message);process.exit(1)})"
if ($LASTEXITCODE) { throw 'Docker cannot reach host renderer. Check service binding and Windows Firewall.' }
