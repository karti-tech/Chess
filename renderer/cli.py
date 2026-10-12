import argparse
import json
import uuid
import logging
from .settings import load,paths,validate
from .pipeline import run_job,preflight,cleanup
from .store import Store

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=['render','doctor','cleanup']); parser.add_argument('--config'); parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args(); cfg=paths(validate(load(args.config))); logging.basicConfig(level=logging.INFO)
    if args.command=='doctor':
        preflight(cfg)
        from .games import scan
        games=list(scan(cfg['games_dir'],cfg['min_plies']))
        if not games: raise ValueError('No usable legal games found')
        print(json.dumps({'ready':True,'usable_games':len(games),'resolution':[cfg['width'],cfg['height']]},indent=2)); return
    if args.command=='cleanup': cleanup(cfg); return
    store=Store(cfg['data_dir']/'factory.sqlite3'); id=str(uuid.uuid4())
    store.create(id,'cli-'+id,{'dry_run':args.dry_run})
    print(json.dumps(run_job(id,cfg,store),indent=2))

if __name__=='__main__': main()
