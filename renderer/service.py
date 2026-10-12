import hmac
import logging
import os
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Literal
from pathlib import Path
from fastapi import FastAPI,Header,HTTPException,Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field,ConfigDict
from dotenv import load_dotenv
from .settings import ROOT,load,paths,validate
from .store import Store
from .pipeline import run_job,preflight,cleanup
from .youtube import publish

load_dotenv(ROOT/'.env')
cfg=paths(validate(load()))
store=Store(cfg['data_dir']/'factory.sqlite3')
pool=ThreadPoolExecutor(max_workers=1)
lock=threading.Lock()
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')

@asynccontextmanager
async def lifespan(app):
    if not os.environ.get('CHESS_SERVICE_TOKEN') or len(os.environ['CHESS_SERVICE_TOKEN'])<24:
        raise RuntimeError('Set a random CHESS_SERVICE_TOKEN of at least 24 characters in .env')
    store.recover(); cleanup(cfg)
    yield
    pool.shutdown(wait=True)

app=FastAPI(title='Chess Shorts Factory',lifespan=lifespan,docs_url=None,redoc_url=None)

def auth(x_chess_token: str=Header(default='')):
    token=os.environ.get('CHESS_SERVICE_TOKEN','')
    if not token or not hmac.compare_digest(x_chess_token,token): raise HTTPException(401,'Invalid service token')

class RenderRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_key: str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_:-]+$')
    target_seconds: int|None=Field(default=None,ge=15,le=60)
    style: Literal['meme_chaos','cinematic','clean_chess']|None=None
    width: Literal[720,1080]|None=None
    height: Literal[1280,1920]|None=None
    dry_run: bool=False

class UploadRequest(BaseModel):
    approved: bool=False

@app.get('/health')
def health(): return {'status':'ok','service':'chess-shorts','version':'1.0.0'}

@app.get('/ready',dependencies=[Depends(auth)])
def ready():
    try: preflight(cfg)
    except Exception as exc: raise HTTPException(503,str(exc)) from None
    return {'ready':True,'resolution':[cfg['width'],cfg['height']]}

def worker(id):
    try: run_job(id,cfg,store)
    except Exception: pass  # Persisted by run_job; HTTP polling reports the failure.

@app.post('/jobs',status_code=202,dependencies=[Depends(auth)])
def create_job(body:RenderRequest):
    req=body.model_dump()
    candidate=dict(cfg); candidate.update({k:v for k,v in req.items() if k in ('target_seconds','style','width','height') and v is not None})
    try: validate(candidate)
    except ValueError as exc: raise HTTPException(422,str(exc)) from None
    with lock:
        prior=store.by_key(body.request_key)
        if prior:
            if prior['request']!=req: raise HTTPException(409,'Request key reused with different parameters')
            return {'id':prior['id'],'status':prior['status'],'reused':True}
        active=[j for j in store.history(1000) if j['status'] in ('queued','running')]
        if len(active)>=3: raise HTTPException(429,'Queue full; poll existing jobs before retrying')
        id=str(uuid.uuid4()); store.create(id,body.request_key,req); pool.submit(worker,id)
    return {'id':id,'status':'queued','reused':False}

@app.get('/jobs',dependencies=[Depends(auth)])
def history(): return {'jobs':store.history()}

@app.get('/jobs/{id}',dependencies=[Depends(auth)])
def status(id:str):
    job=store.get(id)
    if not job: raise HTTPException(404,'Unknown job')
    return job

@app.get('/jobs/{id}/video',dependencies=[Depends(auth)])
def download(id:str):
    job=store.get(id)
    if not job or job['status']!='succeeded': raise HTTPException(404,'No validated video')
    return FileResponse(job['result']['video'],media_type='video/mp4',filename=Path(job['result']['video']).name)

@app.post('/jobs/{id}/publish',dependencies=[Depends(auth)])
def upload(id:str,body:UploadRequest):
    try: return publish(id,cfg,store,body.approved)
    except ValueError as exc: raise HTTPException(409,str(exc)) from None
    except Exception: raise HTTPException(502,'Upload failed; check persisted upload state before retrying') from None
