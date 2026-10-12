"""Official resumable uploads. Never automatically retry an uncertain upload."""
import json
import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from .validation import validate_video

SCOPES=['https://www.googleapis.com/auth/youtube.upload']

def token_path(cfg): return Path(cfg['data_dir'])/'youtube_token.json'

def client(cfg):
    path=token_path(cfg)
    if not path.is_file(): raise ValueError('Run scripts/youtube_auth.py first on your own PC')
    credentials=Credentials.from_authorized_user_file(str(path),SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request()); save_token(path,credentials.to_json())
    if not credentials.valid: raise ValueError('YouTube credentials invalid; reauthorize locally')
    return build('youtube','v3',credentials=credentials,cache_discovery=False)

def save_token(path,text):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp'); temp.write_text(text,encoding='utf-8'); os.chmod(temp,0o600); temp.replace(path)

def publish(id,cfg,store,approved=False):
    job=store.get(id)
    if not job or job['status']!='succeeded': raise ValueError('Only successful render jobs can upload')
    if job['video_id']: return {'video_id':job['video_id'],'url':job['upload_url'],'already_uploaded':True}
    if job['dry_run']: raise ValueError('Dry-run jobs cannot publish')
    if not approved: raise ValueError('Explicit review approval is required')
    privacy=cfg['upload_privacy']
    if privacy not in ('private','unlisted','public'): raise ValueError('Invalid privacy')
    if privacy=='public' and (not cfg['allow_public'] or not cfg['private_test_video_id']):
        raise ValueError('Public requires allow_public=true and a confirmed private/unlisted test video ID')
    if privacy=='public':
        confirmed=[j for j in store.history(10000) if j['video_id']==cfg['private_test_video_id'] and j['upload_state'] in ('private','unlisted')]
        if not confirmed: raise ValueError('Configured test ID was not a confirmed private/unlisted upload in this database')
    result=job['result']; metadata=json.loads(Path(result['metadata']).read_text(encoding='utf-8'))
    validate_video(result['video'],metadata['config'],metadata['config']['target_seconds'])
    youtube=client(cfg)  # Authentication failure before claim is safe to retry.
    if not store.claim_upload(id): raise ValueError('Upload in progress or outcome uncertain. Inspect YouTube Studio before any manual recovery.')
    try:
        request=youtube.videos().insert(part='snippet,status',body={
            'snippet':{'title':result['title'][:100],'description':result['description'],'tags':result['tags'],'categoryId':result['category_id']},
            'status':{'privacyStatus':privacy,'selfDeclaredMadeForKids':False}},
            media_body=MediaFileUpload(result['video'],chunksize=8*1024*1024,resumable=True))
        response=None
        while response is None:
            _,response=request.next_chunk(num_retries=3)  # Resumable chunk retries, no blind videos.insert retry.
        if not response.get('id'): raise RuntimeError('YouTube returned no video ID')
        video_id=response['id']; url='https://www.youtube.com/watch?v='+video_id
        store.update(id,upload_state=privacy,video_id=video_id,upload_url=url)
        return {'video_id':video_id,'url':url,'privacy':privacy}
    except Exception:
        store.update(id,upload_state='uncertain')
        raise RuntimeError('Upload outcome uncertain. Check YouTube Studio; automatic re-upload is blocked.') from None
