import os
import json
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Isolate service's DB and paths from user's real history.
TMP=Path(tempfile.mkdtemp(prefix='chess-tests-'))
CONFIG=TMP/'config.json'
CONFIG.write_text(json.dumps({k:str(TMP/k) for k in ('output_dir','data_dir','logs_dir')}))
os.environ['CHESS_CONFIG']=str(CONFIG)
os.environ['CHESS_SERVICE_TOKEN']='test-only-token-not-for-production-123456789'
from renderer import service
HEADERS={'X-Chess-Token':os.environ['CHESS_SERVICE_TOKEN']}

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(service.pool,'submit',lambda *args:None)
    with TestClient(service.app) as c: yield c

def test_auth_health_and_queue(client):
    assert client.get('/health').status_code==200
    assert client.post('/jobs',json={'request_key':'forbidden'}).status_code==401
    assert client.get('/ready',headers=HEADERS).status_code==200
    req={'request_key':'one','dry_run':True,'width':720,'height':1280,'target_seconds':15}
    first=client.post('/jobs',json=req,headers=HEADERS)
    assert first.status_code==202
    id=first.json()['id']
    again=client.post('/jobs',json=req,headers=HEADERS).json()
    assert again['id']==id and again['reused']
    assert client.get('/jobs/'+id,headers=HEADERS).json()['request']['dry_run']
    assert client.post('/jobs',json={**req,'target_seconds':30},headers=HEADERS).status_code==409
    assert client.post('/jobs',json={'request_key':'bad','width':720,'height':1920},headers=HEADERS).status_code==422
    assert client.get('/jobs/unknown',headers=HEADERS).status_code==404
    assert client.post('/jobs/'+id+'/publish',headers=HEADERS,json={'approved':False}).status_code==409
