import json
import subprocess
import struct
from pathlib import Path


def validate_video(path,cfg,duration):
    p=Path(path)
    if not p.is_file() or p.stat().st_size<10000: raise ValueError('MP4 missing or too small')
    result=subprocess.run([cfg['ffprobe'],'-v','error','-show_streams','-show_format','-of','json',str(p)],capture_output=True,text=True,check=True)
    info=json.loads(result.stdout)
    videos=[s for s in info['streams'] if s['codec_type']=='video']; audios=[s for s in info['streams'] if s['codec_type']=='audio']
    if len(videos)!=1 or len(audios)!=1: raise ValueError('Exactly one video and one audio stream required')
    v,a=videos[0],audios[0]
    if (v['width'],v['height'])!=(cfg['width'],cfg['height']): raise ValueError('Wrong dimensions')
    if v['codec_name']!='h264' or v['pix_fmt']!='yuv420p' or a['codec_name']!='aac': raise ValueError('Wrong codecs/pixel format')
    num,den=map(int,v['avg_frame_rate'].split('/'))
    if abs(num/den-cfg['fps'])>.01: raise ValueError('Wrong frame rate')
    for value in (info['format']['duration'],v['duration'],a['duration']):
        if abs(float(value)-duration)>.15: raise ValueError('Wrong duration or A/V alignment')
    subprocess.run([cfg['ffmpeg'],'-v','error','-xerror','-i',str(p),'-f','null','-'],capture_output=True,check=True)
    if int(v.get('nb_frames',round(duration*cfg['fps'])))!=round(duration*cfg['fps']): raise ValueError('Wrong frame count')
    black=subprocess.run([cfg['ffmpeg'],'-v','info','-i',str(p),'-vf','blackdetect=d=0.12:pix_th=0.03:pic_th=0.99','-an','-f','null','-'],capture_output=True,text=True,check=True)
    if 'black_start:' in black.stderr: raise ValueError('Unintended black frames detected')
    # Verify the encoded audio is audible, not merely present.
    result=subprocess.run([cfg['ffmpeg'],'-v','error','-i',str(p),'-vn','-ac','1','-ar','8000','-f','f32le','pipe:1'],capture_output=True,check=True)
    import numpy as np
    samples=np.frombuffer(result.stdout,dtype='<f4')
    rms=float(np.sqrt(np.mean(samples**2)))
    if not .001<rms<.8: raise ValueError('Audio silent or excessively loud')
    # Top-level atom order proves fast-start moov precedes media.
    atoms=[]
    with p.open('rb') as f:
        while True:
            header=f.read(8)
            if len(header)<8: break
            size,kind=struct.unpack('>I4s',header); header_size=8
            if size==1: size=struct.unpack('>Q',f.read(8))[0]; header_size=16
            atoms.append(kind.decode('ascii',errors='replace'))
            if size==0: break
            if size<header_size: raise ValueError('Corrupt MP4 atom')
            f.seek(size-header_size,1)
    if 'moov' not in atoms or 'mdat' not in atoms or atoms.index('moov')>atoms.index('mdat'): raise ValueError('MP4 is not fast-start')
    return {'valid':True,'width':v['width'],'height':v['height'],'fps':num/den,'duration':float(info['format']['duration']),
            'video_codec':v['codec_name'],'audio_codec':a['codec_name'],'audio_rms':rms,'decode':'passed','faststart':True,'black_frames':'none'}
