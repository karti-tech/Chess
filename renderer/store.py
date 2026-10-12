import json
import sqlite3
from datetime import datetime,timezone


def now(): return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self,path):
        self.path=str(path)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, request_key TEXT UNIQUE, status TEXT, game_hash TEXT, request TEXT, result TEXT, error TEXT, created TEXT, updated TEXT, upload_state TEXT, video_id TEXT, upload_url TEXT, dry_run INTEGER)')
    def connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row; return db
    def create(self,id,key,request):
        with self.connect() as db:
            db.execute('INSERT INTO jobs(id,request_key,status,request,created,updated,dry_run) VALUES(?,?,?,?,?,?,?)',
                       (id,key,'queued',json.dumps(request),now(),now(),int(request.get('dry_run',False))))
        return self.get(id)
    def by_key(self,key):
        with self.connect() as db: row=db.execute('SELECT id FROM jobs WHERE request_key=?',(key,)).fetchone()
        return self.get(row['id']) if row else None
    def get(self,id):
        with self.connect() as db: row=db.execute('SELECT * FROM jobs WHERE id=?',(id,)).fetchone()
        if not row: return None
        out=dict(row)
        for k in ('request','result'): out[k]=json.loads(out[k]) if out[k] else None
        return out
    def update(self,id,**values):
        allowed={'status','game_hash','result','error','upload_state','video_id','upload_url'}
        if set(values)-allowed: raise ValueError('Invalid database update')
        values={k:json.dumps(v) if k=='result' else v for k,v in values.items()}; values['updated']=now()
        with self.connect() as db:
            db.execute('UPDATE jobs SET '+','.join(k+'=?' for k in values)+' WHERE id=?',[*values.values(),id])
    def used(self):
        with self.connect() as db:
            return {r[0] for r in db.execute("SELECT game_hash FROM jobs WHERE dry_run=0 AND status IN ('running','succeeded') AND game_hash IS NOT NULL")}
    def recover(self):
        with self.connect() as db:
            db.execute("UPDATE jobs SET status='failed', error='Service restarted during rendering; submit a new request key', updated=? WHERE status IN ('queued','running')",(now(),))
    def history(self,limit=50):
        with self.connect() as db: ids=[r[0] for r in db.execute('SELECT id FROM jobs ORDER BY created DESC LIMIT ?',(limit,))]
        return [self.get(id) for id in ids]
    def claim_upload(self,id):
        with self.connect() as db:
            cur=db.execute("UPDATE jobs SET upload_state='uploading',updated=? WHERE id=? AND (upload_state IS NULL OR upload_state='not_started')",(now(),id))
        return cur.rowcount==1
