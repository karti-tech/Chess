import json
import os
import random
import urllib.request


def write(game,cfg,evaluations):
    rng = random.Random(int(game['hash'][:8],16) + cfg['seed'])
    hooks = ['THE KING FORGOT HIS SECURITY.', 'ONE BOARD. ZERO CHILL.', 'THIS POSITION HAS TRUST ISSUES.']
    capture = ['Material left the group chat.', 'That piece just clocked out.', 'Free delivery. No returns.']
    check = ['The king would like a refund.', 'Royal customer service is closed.', 'Your Majesty, please relocate.']
    quiet = ['Small move. Big main-character energy.', 'The plot is loading...', 'Another square. Another problem.', 'Act casual. It is still chess.']
    captions = []; seen=set()
    for j,i in enumerate(range(game['start'],game['end'])):
        e=game['events'][i]
        if e['mate']: line='CHECKMATE. The king has left the chat.'
        elif e['promotion']: line='Pawn got the executive promotion.'
        elif e['check']: line=rng.choice(check)
        elif e['capture']: line=rng.choice(capture)
        else: line=quiet[j % len(quiet)]
        if evaluations:
            loss = (evaluations[j]-evaluations[j+1]) * (1 if game['positions'][i].turn else -1)
            if loss >= 200 and abs(evaluations[j]) < 10000:
                line='Engine flags a costly move. Ouch.'
        if line in seen:
            piece=game['positions'][i].piece_at(game['moves'][i].from_square)
            import chess
            who=chess.piece_name(piece.piece_type).capitalize()
            square=chess.square_name(game['moves'][i].to_square)
            line=f'{who} to {square}. '+ ('Royal alarm activated.' if e['check'] else 'New square, new attitude.' if not e['capture'] else 'One less piece at the party.')
        seen.add(line)
        captions.append(line)
    final = game['positions'][game['end']]
    payoff = 'CHECKMATE' if final.is_checkmate() else 'EXCERPT COMPLETE'
    white=game['headers'].get('White','Unknown'); black=game['headers'].get('Black','Unknown')
    title=f"{rng.choice(['The king needs a bodyguard','Chess has no customer support','Royal panic on the board'])} | {game['sans'][game['end']-1]} #Shorts"
    description=(f"{white} vs {black}. Legal {'game' if game['start']==0 and game['end']==len(game['moves']) else 'excerpt'} "
                 f"from {game['source_file']}, plies {game['start']+1}-{game['end']}.\n"
                 f"Recorded result: {game['headers'].get('Result','*')}. Event: {game['headers'].get('Event','?')}.\n"
                 "Original animated editing, captions and locally synthesized soundtrack. Jokes are commentary, not engine evaluations.\n#Chess #Shorts")
    result={'hook':rng.choice(hooks),'captions':captions,'payoff':payoff,'title':title[:100],
            'description':description,'tags':['chess','shorts','chess humor'],'category_id':'20','writer':'local'}
    if cfg['ai_provider']=='openai':
        key=os.environ.get('CHESS_AI_API_KEY')
        if not key: raise ValueError('CHESS_AI_API_KEY is missing; use local mode or configure it securely')
        # Only write a non-factual hook/title; chess facts and move captions stay rule-driven.
        payload={'model':cfg['ai_model'],'response_format':{'type':'json_object'},'messages':[
            {'role':'system','content':'Write original playful chess comedy. Return JSON with hook and title only. No claims about players, blunders, results or history. Hook <=65 characters, title <=90. No URLs.'},
            {'role':'user','content':json.dumps({'san':game['sans'][game['start']:game['end']], 'theme':result['hook']})}]}
        req=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(payload).encode(),
                                  headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=45) as response: data=json.load(response)
        draft=json.loads(data['choices'][0]['message']['content'])
        result['ai_draft']={k:str(draft.get(k,''))[:90] for k in ('hook','title')}
        result['writer']='local with optional AI draft for human review'
    return result
