from pathlib import Path
import json
import pytest
from renderer.store import Store
from renderer import youtube
from renderer.settings import load,ROOT

@pytest.fixture
def upload(tmp_path,monkeypatch):
    cfg=load(ROOT/'config/default.json')
    p=tmp_path/'metadata.json'; p.write_text(json.dumps({'config':cfg}))
    s=Store(tmp_path/'db'); s.create('a','a',{'dry_run':False}); s.update('a',status='succeeded',result={
        'video':'unused.mp4','metadata':str(p),'title':'Test','description':'Test','tags':['chess'],'category_id':'20'})
    monkeypatch.setattr(youtube,'validate_video',lambda *args: {'valid':True})
    monkeypatch.setattr(youtube,'MediaFileUpload',lambda *args,**kwargs: object())
    return cfg,s

class FakeUpload:
    def __init__(self,fail=False): self.fail=fail; self.calls=0
    def videos(self): return self
    def insert(self,**kwargs): self.calls+=1; return self
    def next_chunk(self,**kwargs):
        if self.fail: raise OSError('network lost')
        return None,{'id':'verified-id'}

def test_confirmed_upload_is_idempotent(upload,monkeypatch):
    cfg,s=upload; fake=FakeUpload(); monkeypatch.setattr(youtube,'client',lambda c:fake)
    with pytest.raises(ValueError,match='approval'): youtube.publish('a',cfg,s,False)
    result=youtube.publish('a',cfg,s,True)
    assert result['video_id']=='verified-id' and s.get('a')['upload_state']=='private'
    assert youtube.publish('a',cfg,s,True)['already_uploaded'] and fake.calls==1

def test_uncertain_upload_never_reinserts(upload,monkeypatch):
    cfg,s=upload; fake=FakeUpload(True); monkeypatch.setattr(youtube,'client',lambda c:fake)
    with pytest.raises(RuntimeError,match='uncertain'): youtube.publish('a',cfg,s,True)
    assert s.get('a')['upload_state']=='uncertain'
    with pytest.raises(ValueError,match='uncertain'): youtube.publish('a',cfg,s,True)
    assert fake.calls==1

def test_public_gate_and_dryrun(upload):
    cfg,s=upload
    with pytest.raises(ValueError,match='Public'): youtube.publish('a',{**cfg,'upload_privacy':'public'},s,True)
    s.create('dry','dry',{'dry_run':True}); s.update('dry',status='succeeded')
    with pytest.raises(ValueError,match='Dry-run'): youtube.publish('dry',cfg,s,True)
