"""Run on Windows after creating your OWN Google desktop OAuth client."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from renderer.settings import load,paths,ROOT
from renderer.youtube import SCOPES,save_token,token_path
from google_auth_oauthlib.flow import InstalledAppFlow

if __name__=='__main__':
    client=ROOT/'config/client_secret.json'
    if not client.is_file(): raise SystemExit('Download Desktop OAuth client JSON to config/client_secret.json')
    cfg=paths(load())
    flow=InstalledAppFlow.from_client_secrets_file(str(client),SCOPES)
    credentials=flow.run_local_server(port=0,open_browser=True)
    save_token(token_path(cfg),credentials.to_json())
    print('OAuth token saved locally. Keep data/ private; no credentials printed.')
