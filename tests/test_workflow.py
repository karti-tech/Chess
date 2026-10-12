import json
from pathlib import Path
from renderer.settings import ROOT

def test_workflow_has_bounded_polling_and_no_upload():
    w=json.loads((ROOT/'workflows/Chess-Shorts-Factory.json').read_text())
    nodes={n['name']:n for n in w['nodes']}
    assert not w['active'] and nodes['Daily Schedule']['disabled']
    assert '45*60*1000' in nodes['Check Status And Deadline']['parameters']['jsCode']
    assert 'dry_run:true' in nodes['Configuration']['parameters']['jsCode']
    assert all('/publish' not in str(n) for n in w['nodes'])
    assert not any('credentials' in n for n in w['nodes'])
    assert w['connections']['Finished?']['main'][1][0]['node']=='Wait 15 Seconds'
    p=json.loads((ROOT/'workflows/Chess-Shorts-Publish-Reviewed.json').read_text())
    publish=next(n for n in p['nodes'] if n['type'].endswith('httpRequest'))
    assert not publish.get('retryOnFail')
