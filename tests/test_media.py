"""Real FFmpeg negative cases: validate streams and content, not just file existence."""
import subprocess
import pytest
from renderer.settings import load,ROOT
from renderer.validation import validate_video

@pytest.fixture
def cfg():
    c=load(ROOT/'config/default.json'); c.update(width=720,height=1280,target_seconds=15);return c

def encode(path,cfg,audio=True):
    cmd=[cfg['ffmpeg'],'-v','error','-y','-f','lavfi','-i','color=c=black:s=720x1280:r=30:d=15']
    if audio: cmd+=['-f','lavfi','-i','sine=frequency=440:duration=15','-c:a','aac']
    cmd+=['-c:v','libx264','-preset','ultrafast','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(path)]
    subprocess.run(cmd,check=True,capture_output=True)

def test_black_video_rejected(tmp_path,cfg):
    p=tmp_path/'black.mp4';encode(p,cfg)
    with pytest.raises(ValueError,match='black frames'):validate_video(p,cfg,15)

def test_missing_audio_rejected(tmp_path,cfg):
    p=tmp_path/'silent.mp4';encode(p,cfg,False)
    with pytest.raises(ValueError,match='audio stream'):validate_video(p,cfg,15)

def test_corrupt_mp4_rejected(tmp_path,cfg):
    p=tmp_path/'corrupt.mp4';p.write_bytes(b'bad mp4'*3000)
    with pytest.raises(subprocess.CalledProcessError): validate_video(p,cfg,15)
