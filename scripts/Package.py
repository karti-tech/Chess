"""Build a source ZIP using Git's non-ignored files. No env, DB, credentials or venv."""
import subprocess
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if (ROOT/'.git').exists():
    paths=subprocess.check_output(['git','-C',str(ROOT),'ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
else:
    folders=['renderer','config','scripts','tests','workflows','docs','examples','games','assets']
    paths=[str(p.relative_to(ROOT)) for f in folders for p in (ROOT/f).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [p.name for p in ROOT.iterdir() if p.is_file() and (p.suffix in ('.md','.txt') or p.name in ('LICENSE','.gitignore','.env.example'))]
    paths=[p for p in paths if p not in ('config/local.json','config/client_secret.json')]
output=ROOT.parent/'ChessShortsFactory.zip'
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
    for name in sorted(set(paths)):
        if not name: continue
        p=ROOT/name
        if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(ROOT.resolve()): z.write(p,'ChessShortsFactory/'+name)
print(output)
