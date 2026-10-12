"""Original scalable piece silhouettes; no external images or Unicode chess glyphs."""
from functools import lru_cache
from pathlib import Path
import math
import chess
from PIL import Image,ImageDraw,ImageFont,ImageFilter

PALETTES={
 'meme_chaos':('#0C1022','#18203B','#EAEDDE','#405967','#A6FF59','#FBD05D'),
 'cinematic':('#0D131B','#182532','#E7DAC1','#647579','#FFC56D','#FFD793'),
 'clean_chess':('#0C1921','#17303C','#DCEAE5','#43796E','#66DFCC','#FFE08B')}

@lru_cache(maxsize=64)
def font(size,path=''):
    candidates=[path, 'C:/Windows/Fonts/arialbd.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
    for p in candidates:
        if p and Path(p).is_file(): return ImageFont.truetype(p,size)
    return ImageFont.load_default(size=size)

@lru_cache(maxsize=24)
def piece(kind,color,size):
    s=256
    im=Image.new('RGBA',(s,s)); d=ImageDraw.Draw(im)
    fill='#FAF3DD' if color else '#243348'; edge='#26354C' if color else '#E6CFA9'
    def poly(points): d.polygon(points,fill=fill); d.line(points+[points[0]],fill=edge,width=7,joint='curve')
    def ellipse(box): d.ellipse(box,fill=fill,outline=edge,width=7)
    # Distinct classic piece shapes, drawn at 256px then downsampled.
    poly([(52,217),(63,197),(192,197),(204,217)])
    if kind==chess.PAWN:
        ellipse((89,37,167,114)); poly([(105,110),(151,110),(166,177),(183,194),(73,194),(90,177)])
    elif kind==chess.ROOK:
        poly([(69,55),(91,55),(91,80),(114,80),(114,55),(141,55),(141,80),(164,80),(164,55),(186,55),(179,113),(159,126),(166,194),(89,194),(97,126),(77,113)])
    elif kind==chess.KNIGHT:
        poly([(77,192),(88,153),(118,125),(72,131),(51,114),(80,74),(107,57),(107,31),(136,49),(166,62),(188,99),(190,192)])
        d.ellipse((112,77,123,88),fill=edge); d.line((64,116,93,116),fill=edge,width=6)
    elif kind==chess.BISHOP:
        poly([(82,194),(99,159),(107,114),(85,88),(94,60),(128,30),(160,61),(170,89),(147,114),(155,160),(176,194)])
        d.line((139,51,115,94),fill=edge,width=9)
    elif kind==chess.QUEEN:
        poly([(84,194),(98,145),(64,77),(104,107),(127,54),(151,107),(193,77),(159,145),(172,194)])
        for x,y in [(64,69),(127,47),(193,69)]: ellipse((x-12,y-12,x+12,y+12))
    else:
        poly([(86,194),(99,141),(91,105),(101,88),(155,88),(166,105),(156,141),(171,194)])
        d.rectangle((118,28,138,86),fill=fill,outline=edge,width=5)
        d.rectangle((101,44,155,64),fill=fill,outline=edge,width=5)
    d.line((87,178,170,178),fill=edge,width=5)
    # Offset outline is deliberate; avoids unreadable all-black pieces.
    return im.resize((size,size),Image.Resampling.LANCZOS)


def wrap(draw,text,f,maxwidth):
    lines=[]; line=''
    for word in text.split():
        candidate=(line+' '+word).strip()
        if draw.textlength(candidate,font=f)>maxwidth and line: lines.append(line); line=word
        else: line=candidate
    if line: lines.append(line)
    return lines


def center(draw,text,y,width,size,color,path='',maxwidth=None,maxlines=3):
    maxwidth=maxwidth or width*.82
    f=font(max(12,size),path); lines=wrap(draw,text,f,maxwidth)
    while size>12:
        f=font(size,path); lines=wrap(draw,text,f,maxwidth)
        if len(lines)<=maxlines and all(draw.textlength(x,font=f)<=maxwidth for x in lines): break
        size-=2
    for line in lines[:maxlines]:
        draw.text((width/2,y),line,font=f,fill=color,anchor='mt')
        y+=size*1.25
    return y


class Scene:
    def __init__(self,cfg,game,script):
        self.cfg,self.game,self.script=cfg,game,script
        self.w,self.h=cfg['width'],cfg['height']; self.scale=self.w/1080
        self.bg,self.panel,self.light,self.dark,self.accent,self.gold=PALETTES[cfg['style']]
        self.size=int(self.w*.82); self.cell=self.size/8; self.x=(self.w-self.size)//2; self.y=int(self.h*.285)
        self.tile=int(self.cell*.94)
        self.board_background=Image.new('RGBA',(self.size,self.size))
        d=ImageDraw.Draw(self.board_background)
        for rank in range(8):
            for file in range(8):
                c=self.light if (rank+file)%2==0 else self.dark
                d.rectangle((round(file*self.cell),round(rank*self.cell),round((file+1)*self.cell),round((rank+1)*self.cell)),fill=c)
    def point(self,square):
        f,r=chess.square_file(square),chess.square_rank(square)
        if self.cfg['orientation']=='white': r=7-r
        else: f=7-f
        return (f*self.cell+(self.cell-self.tile)/2,r*self.cell+(self.cell-self.tile)/2)
    def board(self,position,move=None,progress=1,event=None):
        im=self.board_background.copy(); d=ImageDraw.Draw(im,'RGBA')
        if move:
            for square in (move.from_square,move.to_square):
                x,y=self.point(square); pad=(self.cell-self.tile)/2
                d.rectangle((x-pad,y-pad,x-pad+self.cell,y-pad+self.cell),fill=(180,255,95,95))
        movers={}
        if move:
            movers[move.from_square]=move.to_square
            if position.is_castling(move):
                rank=chess.square_rank(move.from_square)
                kingside=chess.square_file(move.to_square)>chess.square_file(move.from_square)
                movers[chess.square(7 if kingside else 0,rank)]=chess.square(5 if kingside else 3,rank)
        captured=move.to_square if move else None
        if move and position.is_en_passant(move): captured=move.to_square+(-8 if position.turn else 8)
        for square,p in position.piece_map().items():
            if square in movers: continue
            if move and square==captured and progress>.6: continue
            im.alpha_composite(piece(p.piece_type,p.color,self.tile),(int(self.point(square)[0]),int(self.point(square)[1])))
        for square,dest in movers.items():
            p=position.piece_at(square)
            if p is None: continue
            x,y=self.point(square); tx,ty=self.point(dest)
            kind=move.promotion if square==move.from_square and move.promotion and progress>.94 else p.piece_type
            im.alpha_composite(piece(kind,p.color,self.tile),(round(x+(tx-x)*progress),round(y+(ty-y)*progress)))
        if event and event['capture'] and .55<progress<1:
            x,y=self.point(move.to_square); rad=self.cell*(.25+progress*.45)
            d.ellipse((x+self.tile/2-rad,y+self.tile/2-rad,x+self.tile/2+rad,y+self.tile/2+rad),outline=(255,210,90,180),width=5)
        return im
    def frame(self,t,duration):
        w,h=self.w,self.h; im=Image.new('RGB',(w,h),self.bg); d=ImageDraw.Draw(im)
        s=self.scale; start,end=self.game['start'],self.game['end']; n=end-start
        hook_seconds=2; ending_seconds=2; segment=(duration-hook_seconds-ending_seconds)/n
        phase=(t-hook_seconds)/segment
        local=max(0,min(n-1,int(phase))); idx=start+local
        intro=t<hook_seconds; outro=t>=duration-ending_seconds
        move=None; event=None; progress=1
        if intro: board=self.game['positions'][start]; caption='The setup. Watch the next move.'; label='THE SETUP'
        elif outro:
            board=self.game['positions'][end]; caption=self.script['payoff']; label='THE PAYOFF'
        else:
            board=self.game['positions'][idx]; move=self.game['moves'][idx]; event=self.game['events'][idx]
            fraction=phase-local
            linear=min(1,max(0,fraction/.65)); progress=linear*linear*(3-2*linear)
            caption=self.script['captions'][local]; label=f"MOVE {board.fullmove_number}{' • WHITE' if board.turn else ' • BLACK'}  {self.game['sans'][idx]}"
        # Rounded cards, stable safe margins, animated accent progress.
        d.rounded_rectangle((w*.08,h*.055,w*.92,h*.09),radius=int(18*s),fill=self.panel)
        center(d,self.cfg['brand'],h*.063,w,int(24*s),self.accent,self.cfg['font_path'],maxlines=1)
        center(d,self.script['hook'],h*.125,w,int(56*s),'#F5F7FF',self.cfg['font_path'],maxlines=2)
        center(d,self.game['headers'].get('White','Unknown')+' vs '+self.game['headers'].get('Black','Unknown'),h*.235,w,int(20*s),'#9BA9BF',self.cfg['font_path'],maxlines=1)
        center(d,label,h*.265,w,int(27*s),self.gold,self.cfg['font_path'],maxlines=1)
        d.rounded_rectangle((self.x-14*s,self.y-14*s,self.x+self.size+14*s,self.y+self.size+14*s),radius=int(20*s),fill=self.panel)
        boardim=self.board(board,move,progress,event)
        zoom=1
        if self.cfg['style']!='clean_chess': zoom+=.012*math.sin(math.pi*min(1,max(0,(t/duration))))
        boardim=boardim.resize((round(self.size*zoom),round(self.size*zoom)),Image.Resampling.BICUBIC)
        offset=(boardim.width-self.size)//2
        shake=round(3*s*math.sin(t*60)*(1-progress)) if event and event['capture'] and self.cfg['style']=='meme_chaos' else 0
        im.paste(boardim,(self.x-offset+shake,self.y-offset),boardim)
        d=ImageDraw.Draw(im)
        for k in range(8):
            file='abcdefgh'[k if self.cfg['orientation']=='white' else 7-k]
            rank=str(8-k if self.cfg['orientation']=='white' else k+1)
            d.text((self.x+(k+.5)*self.cell,self.y+self.size+12*s),file,font=font(int(18*s),self.cfg['font_path']),fill='#95A4BD',anchor='mt')
            d.text((self.x-22*s,self.y+(k+.5)*self.cell),rank,font=font(int(18*s),self.cfg['font_path']),fill='#95A4BD',anchor='mm')
        capy=h*.79
        d.rounded_rectangle((w*.07,capy-20*s,w*.93,h*.89),radius=int(22*s),fill=self.panel)
        center(d,caption,capy,w,int(44*s),'#FFFFFF',self.cfg['font_path'],maxlines=3)
        footer='COMEDY COMMENTARY • LEGAL MOVES' if not outro else 'MORE CHESS. LESS ROYAL CONFIDENCE.'
        center(d,footer,h*.925,w,int(18*s),'#9BA9BF',self.cfg['font_path'],maxlines=1)
        d.rectangle((w*.08,h*.91,w*.92,h*.914),fill=self.panel)
        d.rectangle((w*.08,h*.91,w*.08+w*.84*min(1,t/duration),h*.914),fill=self.accent)
        return im
