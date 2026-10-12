import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(path=None):
    cfg = json.loads((ROOT / 'config/default.json').read_text(encoding='utf-8'))
    local = Path(path or os.environ.get('CHESS_CONFIG', ROOT / 'config/local.json'))
    if local.exists():
        extra = json.loads(local.read_text(encoding='utf-8-sig'))
        if set(extra) - set(cfg):
            raise ValueError(f'Unknown configuration fields: {set(extra) - set(cfg)}')
        cfg.update(extra)
    return cfg

def paths(cfg):
    result = dict(cfg)
    for key in ('games_dir', 'output_dir', 'data_dir', 'logs_dir'):
        p = Path(cfg[key]).expanduser()
        result[key] = p if p.is_absolute() else ROOT / p
        result[key].mkdir(parents=True, exist_ok=True)
    return result

def validate(cfg):
    if (cfg['width'], cfg['height']) not in ((720,1280),(1080,1920)):
        raise ValueError('Choose 720x1280 or 1080x1920')
    if not 15 <= cfg['min_seconds'] <= cfg['target_seconds'] <= cfg['max_seconds'] <= 60:
        raise ValueError('Duration must be between 15 and 60 seconds')
    if cfg['fps'] not in (24,30,60):
        raise ValueError('FPS must be 24, 30 or 60')
    if cfg['style'] not in ('meme_chaos','cinematic','clean_chess'):
        raise ValueError('Unknown visual style')
    if cfg['orientation'] not in ('white','black'):
        raise ValueError('Orientation must be white or black')
    if cfg['encoder'] != 'libx264':
        raise ValueError('CPU libx264 is the verified encoder; NVENC needs separate validation')
    for k in ('music_volume','sfx_volume'):
        if not 0 <= cfg[k] <= 1: raise ValueError(f'{k} must be 0..1')
    if not 1 <= cfg['engine_threads'] <= 4 or not .01 <= cfg['engine_seconds'] <= .5:
        raise ValueError('Engine limits: 1..4 threads, 0.01..0.5 seconds per position')
    if not 1 <= cfg['max_excerpt_plies'] <= 30 or cfg['min_plies'] < 1:
        raise ValueError('Invalid game selection limits')
    if cfg['retention_days'] < 1: raise ValueError('Retention must be at least one day')
    if cfg['ai_provider'] not in ('local','openai'): raise ValueError('Unknown AI provider')
    return cfg
