import hashlib
import io
import logging
from pathlib import Path
import chess
import chess.pgn
import chess.engine

log = logging.getLogger(__name__)

def scan(directory, min_plies=6):
    for path in sorted(p for p in Path(directory).rglob('*') if p.is_file() and p.suffix.lower()=='.pgn'):
        try: raw = path.read_bytes()
        except OSError:
            log.warning('Skipping unreadable PGN %s',path.name)
            continue
        try: text = raw.decode('utf-8-sig')
        except UnicodeDecodeError: text = raw.decode('cp1252', errors='replace')
        stream = io.StringIO(text)
        index = 0
        while True:
            try: game = chess.pgn.read_game(stream)
            except (ValueError, UnicodeError) as exc:
                log.warning('Skipping malformed PGN %s: %s', path.name, exc)
                break
            if game is None: break
            index += 1
            if game.errors:
                log.warning('Skipping game %s #%s: PGN parse errors', path.name, index)
                continue
            board = game.board()
            moves = list(game.mainline_moves())
            if type(board) is not chess.Board or board.chess960:
                log.warning('Skipping unsupported variant in %s #%s',path.name,index)
                continue
            if not board.is_valid() or len(moves) < min_plies: continue
            positions, sans, events = [board.copy()], [], []
            for move in moves:
                if move not in board.legal_moves: break
                sans.append(board.san(move))
                capture = board.is_capture(move)
                board.push(move)
                positions.append(board.copy())
                events.append({'capture':capture,'check':board.is_check(),'mate':board.is_checkmate(),
                               'promotion': bool(move.promotion)})
            else:
                identity = positions[0].fen() + '|' + ' '.join(m.uci() for m in moves)
                yield {'hash':hashlib.sha256(identity.encode()).hexdigest(), 'headers':dict(game.headers),
                       'source_file':path.name,'source_index':index,'moves':moves,'positions':positions,
                       'sans':sans,'events':events}


def select(directory, used, cfg):
    candidates = [g for g in scan(directory,cfg['min_plies']) if g['hash'] not in used]
    if not candidates: raise ValueError('No unused legal games. Add more PGNs or use dry-run to preview a used game.')
    def score(g):
        return sum(e['capture'] + 2*e['check'] + 10*e['mate'] + 3*e['promotion'] for e in g['events'])
    game = max(candidates,key=score)
    n = min(len(game['moves']),cfg['max_excerpt_plies'])
    ends = range(n,len(game['moves'])+1)
    end = max(ends, key=lambda j: sum(e['capture']+2*e['check']+10*e['mate']+3*e['promotion'] for e in game['events'][j-n:j]))
    game['start'],game['end'] = end-n,end
    return game


def evaluate(game,cfg):
    if not cfg['engine_path']: return []
    engine_path = Path(cfg['engine_path']).expanduser()
    if not engine_path.is_file(): raise ValueError('Stockfish executable does not exist: configure engine_path')
    evaluations = []
    with chess.engine.SimpleEngine.popen_uci(str(engine_path), timeout=20) as engine:
        options = {k:v for k,v in {'Threads':cfg['engine_threads'],'Hash':64}.items() if k in engine.options}
        engine.configure(options)
        for i in range(game['start'], game['end']+1):
            board = game['positions'][i]
            info = engine.analyse(board,chess.engine.Limit(time=cfg['engine_seconds']))
            evaluations.append(info['score'].white().score(mate_score=100000))
    return evaluations
