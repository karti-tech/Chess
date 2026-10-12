import json
import logging
import shutil
import subprocess
import time
from pathlib import Path
from .settings import validate,paths
from .games import select,evaluate
from .writing import write
from .audio import synth
from .visuals import Scene
from .validation import validate_video

log=logging.getLogger(__name__)

def preflight(cfg):
    validate(cfg)
    for tool in ('ffmpeg','ffprobe'):
        if not shutil.which(cfg[tool]): raise ValueError(f'{tool} not found on PATH')
    if cfg['engine_path'] and not Path(cfg['engine_path']).is_file(): raise ValueError('Stockfish executable does not exist: configure engine_path')
    output=Path(cfg['output_dir'])
    if shutil.disk_usage(output).free<cfg['min_free_gb']*1024**3: raise ValueError('Insufficient free disk space')
    if not any(p.is_file() and p.suffix.lower()=='.pgn' for p in Path(cfg['games_dir']).rglob('*')): raise ValueError('No .pgn files in games_dir')


def run_job(id,cfg,store):
    job=store.get(id); request=job['request']; cfg=dict(cfg)
    cfg.update({k:v for k,v in request.items() if k in ('target_seconds','style','width','height') and v is not None})
    cfg=paths(cfg); validate(cfg)
    work=cfg['output_dir']/id; work.mkdir(exist_ok=False)
    logfile=cfg['logs_dir']/f'{id}.log'
    handler=logging.FileHandler(logfile,encoding='utf-8'); handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logging.getLogger().addHandler(handler)
    try:
        store.update(id,status='running'); preflight(cfg)
        used=set() if request.get('dry_run') else store.used()
        game=select(cfg['games_dir'],used,cfg); store.update(id,game_hash=game['hash'])
        evaluations=evaluate(game,cfg); script=write(game,cfg,evaluations)
        metadata={'headers':game['headers'],'source_file':game['source_file'],'source_index':game['source_index'],
                  'game_hash':game['hash'],'start_ply':game['start'],'end_ply':game['end'],
                  'initial_fen':game['positions'][game['start']].fen(),
                  'moves':[m.uci() for m in game['moves'][game['start']:game['end']]],
                  'san':game['sans'][game['start']:game['end']],'evaluations_cp_white':evaluations,'script':script,
                  'rights_note':'Local PGN supplied by user; confirm source terms before publishing. Demo PGN is an original legal demonstration.',
                  'assets':{'pieces':'Original procedural silhouettes, project MIT license','music':cfg['music_license'] or 'Original locally synthesized composition, project MIT license',
                            'sfx':'Original synthesized sounds, project MIT license','font':'System font used locally; not bundled','narration':cfg['tts_license'] or 'None'},
                  'config':{k:str(v) if isinstance(v,Path) else v for k,v in cfg.items()}}
        (work/'metadata.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
        duration=cfg['target_seconds']; n=game['end']-game['start']; segment=(duration-4)/n
        events=[(2+j*segment+segment*.65,e) for j,e in enumerate(game['events'][game['start']:game['end']])]
        audio=synth(duration,events,cfg,work/'soundtrack.wav'); scene=Scene(cfg,game,script)
        # Render frames directly to FFmpeg: never a directory of millions of PNGs.
        out=work/f"{cfg['output_prefix']}_{id}.mp4"
        if not cfg['output_prefix'].replace('_','').replace('-','').isalnum(): raise ValueError('output_prefix may only contain letters, digits, _ or -')
        command=[cfg['ffmpeg'],'-y','-v','warning','-f','rawvideo','-pix_fmt','rgb24','-s',f"{cfg['width']}x{cfg['height']}",
                 '-r',str(cfg['fps']),'-i','pipe:0','-i',str(work/'soundtrack.wav'),'-c:v','libx264','-preset','veryfast','-crf','20',
                 '-threads','2','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-af','loudnorm=I=-16:TP=-1.5:LRA=11',
                 '-t',str(duration),'-movflags','+faststart',str(out)]
        log.info('Rendering %s: %sx%s, %ss, %s moves',id,cfg['width'],cfg['height'],duration,n)
        with (work/'ffmpeg.log').open('wb') as err:
            process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=err)
            try:
                for frame in range(round(duration*cfg['fps'])):
                    image=scene.frame(frame/cfg['fps'],duration)
                    process.stdin.write(image.tobytes())
                process.stdin.close()
                if process.wait(timeout=180)!=0: raise RuntimeError('FFmpeg failed; see job ffmpeg.log')
            except BaseException:
                process.kill(); process.wait(); raise
        validation=validate_video(out,cfg,duration)
        scene.frame(duration-1,duration).save(work/'thumbnail.jpg',quality=95)
        # Contact sheet lets a human inspect opening, motion, tactical moment and ending.
        from PIL import Image
        sheet=Image.new('RGB',(720,640))
        for j,t in enumerate([.5,2.5,duration*.55,duration-1]):
            shot=scene.frame(t,duration).resize((180,320)); sheet.paste(shot,(j*180,160))
        sheet.save(work/'contact_sheet.jpg',quality=92)
        result={'video':str(out),'thumbnail':str(work/'thumbnail.jpg'),'metadata':str(work/'metadata.json'),
                'validation':validation,'audio':audio,'title':script['title'],'description':script['description'],
                'tags':script['tags'],'category_id':script['category_id'],'review_required':True,'dry_run':request.get('dry_run',False)}
        (work/'validation.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
        store.update(id,status='succeeded',result=result)
        if not cfg['debug']: (work/'soundtrack.wav').unlink()
        log.info('Validated job %s',id)
        return result
    except Exception as exc:
        # Do not log request headers, API keys, credentials or raw provider responses.
        message=str(exc) if isinstance(exc,(ValueError,FileNotFoundError)) else f'{type(exc).__name__}: see local job/FFmpeg logs; no credentials logged'
        import traceback
        log.error('Job %s failed: %s',id,message)
        log.error('Failure locations:\n%s',''.join(traceback.format_tb(exc.__traceback__)))
        store.update(id,status='failed',error=message)
        raise
    finally:
        logging.getLogger().removeHandler(handler); handler.close()


def cleanup(cfg):
    """Remove only old temporary WAVs from factory UUID job directories. Keep videos and PGNs."""
    import uuid
    cutoff=time.time()-cfg['retention_days']*86400
    for folder in Path(cfg['output_dir']).iterdir():
        try: uuid.UUID(folder.name)
        except ValueError: continue
        candidate=folder/'soundtrack.wav'
        if candidate.is_file() and candidate.stat().st_mtime<cutoff: candidate.unlink()
