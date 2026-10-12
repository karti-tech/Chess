import wave
from pathlib import Path
import subprocess
import numpy as np

RATE=48000

def synth(duration, events, cfg, target):
    count=round(duration*RATE)
    t=np.arange(count)/RATE
    music=np.zeros(count,dtype=np.float64)
    rng=np.random.default_rng(cfg['seed'])
    # Original four-chord arpeggio and kick/snare rhythm, composed algorithmically.
    chords=[[220,261.626,329.628],[174.614,220,261.626],[130.813,164.814,195.998],[195.998,246.942,293.665]]
    beat=.5
    for k,start in enumerate(np.arange(0,duration,beat)):
        lo=int(start*RATE); n=min(int(beat*RATE),count-lo); x=np.arange(n)/RATE
        note=chords[(k//8)%4][k%3]
        env=(1-np.exp(-x*70))*np.exp(-x*5)
        tone=(np.sin(2*np.pi*note*x)+.25*np.sin(2*np.pi*note*2*x))*env
        kick=np.sin(2*np.pi*(48*x+5*(1-np.exp(-x*25))))*np.exp(-x*25)
        snare=rng.normal(0,.15,n)*np.exp(-x*30) if k%2 else 0
        music[lo:lo+n] += .22*tone+.18*kick+snare
    if cfg['music_file']:
        if not cfg['music_license']: raise ValueError('User music requires music_license/source declaration')
        music=read_external(cfg['music_file'],duration,cfg)
    effects=np.zeros(count,dtype=np.float64); duck=np.ones(count)
    for start,e in events:
        lo=int(start*RATE); n=min(int(.42*RATE),count-lo)
        if n<=0: continue
        x=np.arange(n)/RATE
        freq=135 if e['capture'] else 800
        tone=np.sin(2*np.pi*(freq*x + 90*x*x))*np.exp(-x*(10 if e['capture'] else 32))
        if e['check']: tone += .4*np.sin(2*np.pi*440*x)*np.exp(-x*6)
        if e['mate']: tone += .5*np.sin(2*np.pi*660*x)*np.exp(-x*4)
        effects[lo:lo+n] += tone*.4
        duck[lo:lo+n] *= .55+.45*x/.42
    voice=np.zeros(count)
    if cfg['tts_file']:
        if not cfg['tts_license']: raise ValueError('Narration requires a source/license declaration')
        voice=read_external(cfg['tts_file'],duration,cfg)
        # Duck music around supplied speech; no paid TTS dependency.
        block=RATE//10
        for lo in range(0,count,block):
            if np.max(np.abs(voice[lo:lo+block]))>.015: duck[lo:lo+block] *= .25
    mix=music*cfg['music_volume']*duck+effects*cfg['sfx_volume']+voice*.65
    fade=np.minimum(1,np.minimum(t/.5,(duration-t)/.8))
    mix=np.tanh(mix*1.6)*np.maximum(0,fade)
    peak=np.max(np.abs(mix))
    if peak<1e-6: raise ValueError('Audio is silent: raise music or sfx volume')
    mix *= min(1,.90/peak)
    stereo=np.stack([mix,mix],axis=1)
    with wave.open(str(target),'wb') as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(RATE)
        f.writeframes((stereo*32767).astype('<i2').tobytes())
    return {'peak':float(np.max(np.abs(mix))),'rms':float(np.sqrt(np.mean(mix**2))),'samples':count}

def read_external(path,duration,cfg):
    p=Path(path)
    if not p.is_file(): raise ValueError('Configured audio file does not exist')
    result=subprocess.run([cfg['ffmpeg'],'-v','error','-i',str(p),'-t',str(duration),'-f','f32le','-ac','1','-ar',str(RATE),'pipe:1'],capture_output=True,check=True)
    a=np.frombuffer(result.stdout,dtype='<f4').astype(np.float64)
    return np.pad(a,(0,max(0,round(duration*RATE)-len(a))))[:round(duration*RATE)]
