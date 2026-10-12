from pathlib import Path
import json
import wave
import chess
import numpy as np
import pytest
from renderer.settings import ROOT,load,paths,validate
from renderer.games import scan,select,evaluate
from renderer.audio import synth,RATE
from renderer.visuals import Scene
from renderer.writing import write
from renderer.store import Store
from renderer.validation import validate_video

@pytest.fixture
def cfg(tmp_path):
    c=load(ROOT/'config/default.json'); c.update(width=720,height=1280,target_seconds=15)
    for k in ('output_dir','data_dir','logs_dir'): c[k]=str(tmp_path/k)
    return paths(c)

def test_pgn_legality_and_mate(cfg):
    g=select(ROOT/'games',set(),cfg)
    assert len(g['moves'])==7 and g['positions'][-1].is_checkmate()
    for board,move,after in zip(g['positions'],g['moves'],g['positions'][1:]):
        assert move in board.legal_moves
        b=board.copy(); b.push(move); assert b.fen()==after.fen()
    assert g['headers']['Source'].startswith('Original')
    with pytest.raises(ValueError,match='unused'): select(ROOT/'games',{g['hash']},cfg)

def test_multi_game_variations_and_encoding(tmp_path):
    game='[White "André"]\n[Result "*"]\n\n1. e4 (1. d4 d5) e5 2. Nf3 Nc6 *\n\n'
    (tmp_path/'multi.pgn').write_bytes((game+game).encode('cp1252'))
    games=list(scan(tmp_path,4))
    assert len(games)==2 and games[0]['headers']['White']=='André'
    assert [m.uci() for m in games[0]['moves']]==['e2e4','e7e5','g1f3','b8c6']
    assert games[0]['hash']==games[1]['hash']

def test_malformed_skipped(tmp_path):
    (tmp_path/'bad.pgn').write_text('[Result "*"]\n\n1. e4 e5 2. Bh6 *')
    assert not list(scan(tmp_path,1))

def test_audio_duration_mixing_and_clipping(cfg,tmp_path):
    p=tmp_path/'a.wav'
    stats=synth(15,[(3,{'capture':True,'check':True,'mate':False})],cfg,p)
    with wave.open(str(p)) as f:
        assert f.getnframes()==15*RATE and f.getnchannels()==2
        a=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2')
    assert 0<stats['rms']<.5 and np.max(np.abs(a.astype(int)))<32767
    assert a[0]==0
    cfg.update(music_volume=0,sfx_volume=0)
    with pytest.raises(ValueError,match='silent'): synth(15,[],cfg,p)

def test_duration_and_configuration(cfg):
    assert validate(cfg)
    for updates in ({'target_seconds':14},{'width':720,'height':1920},{'style':'unknown'},{'engine_seconds':2}):
        with pytest.raises(ValueError): validate({**cfg,**updates})

def test_engine_path(cfg):
    g=select(ROOT/'games',set(),cfg)
    assert evaluate(g,cfg)==[]
    with pytest.raises(ValueError,match='executable'): evaluate(g,{**cfg,'engine_path':'missing-stockfish.exe'})

@pytest.mark.parametrize('fen,uci',[
    ('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1','e1g1'),
    ('r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1','e8c8'),
    ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1','e5d6'),
    ('4k3/P7/8/8/8/8/8/4K3 w - - 0 1','a7a8q')])
def test_special_move_animation_matches_result(cfg,fen,uci,monkeypatch):
    # Solid colored proxy pieces expose wrong square occupancy at animation completion.
    from PIL import Image
    import renderer.visuals as v
    colors={k:(k*30,40,210,255) for k in range(1,7)}
    monkeypatch.setattr(v,'piece',lambda kind,color,size:Image.new('RGBA',(size,size),colors[kind]))
    b=chess.Board(fen); m=chess.Move.from_uci(uci); assert m in b.legal_moves
    after=b.copy(); after.push(m)
    scene=Scene(cfg,{},{}); frame=scene.board(b,m,1)
    for square,p in after.piece_map().items():
        x,y=scene.point(square)
        assert frame.getpixel((int(x+scene.tile/2),int(y+scene.tile/2)))==colors[p.piece_type]
    # Vacated squares may have highlights but must not retain a piece.
    for square in set(b.piece_map())-set(after.piece_map()):
        x,y=scene.point(square)
        assert frame.getpixel((int(x+scene.tile/2),int(y+scene.tile/2))) not in colors.values()

def test_smooth_animation_and_safe_dimensions(cfg):
    g=select(ROOT/'games',set(),cfg); scene=Scene(cfg,g,write(g,cfg,[]))
    a,b,c=[scene.frame(t,15) for t in (2.05,2.2,2.4)]
    assert a.size==(720,1280) and a.tobytes()!=b.tobytes()!=c.tobytes()
    assert scene.point(chess.A1)[0]<scene.point(chess.H1)[0]
    scene2=Scene({**cfg,'orientation':'black'},g,write(g,cfg,[]))
    assert scene2.point(chess.A1)[0]>scene2.point(chess.H1)[0]

def test_store_idempotency_and_recovery(tmp_path):
    import sqlite3
    s=Store(tmp_path/'jobs.db'); s.create('a','key',{'dry_run':False})
    with pytest.raises(sqlite3.IntegrityError): s.create('b','key',{})
    s.update('a',status='running',game_hash='game')
    assert s.used()=={'game'}
    s.recover(); assert s.get('a')['status']=='failed' and not s.used()
    s.update('a',status='succeeded'); assert s.used()=={'game'}
    assert s.claim_upload('a') and not s.claim_upload('a')


def test_invalid_video_rejected(cfg,tmp_path):
    p=tmp_path/'bad.mp4'; p.write_bytes(b'not a video')
    with pytest.raises(ValueError): validate_video(p,cfg,15)
