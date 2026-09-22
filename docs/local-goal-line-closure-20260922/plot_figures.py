"""Plot fixed published summaries. No outcomes, inference or interval estimation.

Run from the documentation worktree with bundled Python + Pillow.
Only two allowlisted compact Git projections are read. SVG and PNG show
the same fixed marks. Figure B means = published time totals / counts.
"""
import hashlib
from decimal import Decimal, ROUND_HALF_UP
from html import escape
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
PINS = {
    'RB1': ('8a79e267cb0cb7b6243900cb3bc194e0eb069a85',
            'docs/local-goal-search-budget-20260919/FINAL-AGGREGATE-PROJECTION.json'),
    'RB2': ('0b6507fc7398eb0624d0755035db22e666de74d5',
            'docs/local-goal-source-replication-publication-20260920/completion-v6/FINAL-AGGREGATE-PROJECTION.json')}
BLUE, ORANGE, INK, GRAY = '#27628B', '#A74929', '#203144', '#657080'


def display_pp(value):
    # Display only: remove binary representation noise at exact half-decimals.
    # Point/interval positions and exported data stay unrounded and unchanged.
    return f"{Decimal(str(round(value, 12))).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP):+f}"


def read_pinned(key):
    commit, path = PINS[key]
    data = subprocess.check_output(['git','show',f'{commit}:{path}'], cwd=REPO)
    return json.loads(data), dict(commit=commit, path=path,
                                 sha256=hashlib.sha256(data).hexdigest())


class Canvas:
    def __init__(self, width, height):
        self.w, self.h = width, height
        self.im = Image.new('RGB', (width, height), 'white')
        self.d = ImageDraw.Draw(self.im)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                    '<rect width="100%" height="100%" fill="white"/>']
    def text(self, x, y, text, size=22, color=INK, bold=False, anchor='start'):
        font = ImageFont.truetype('C:/Windows/Fonts/'+('arialbd.ttf' if bold else 'arial.ttf'), size)
        self.d.text((x,y),text,font=font,fill=color,anchor={'start':'ls','middle':'ms','end':'rs'}[anchor])
        self.svg.append(f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}" text-anchor="{anchor}">{escape(text)}</text>')
    def line(self,x1,y1,x2,y2,color=GRAY,width=2):
        self.d.line((x1,y1,x2,y2),fill=color,width=width)
        self.svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>')
    def dot(self,x,y,color=BLUE,square=False):
        coords=(x-7,y-7,x+7,y+7)
        if square:
            self.d.rectangle(coords,fill=color)
            self.svg.append(f'<rect x="{x-7}" y="{y-7}" width="14" height="14" fill="{color}"/>')
        else:
            self.d.ellipse(coords,fill=color)
            self.svg.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{color}"/>')
    def save(self,name):
        self.im.save(ROOT/(name+'.png'))
        (ROOT/(name+'.svg')).write_text('\n'.join(self.svg+['</svg>'])+'\n',encoding='utf-8')


def main():
    rb1, p1 = read_pinned('RB1')
    rb2, p2 = read_pinned('RB2')
    assert rb1['independent_sources'] == 32 and rb2['independent_sources'] == 512
    panels = []
    for label, n, data in [('LGP-RB1',32,rb1),('LGP-RB2',512,rb2)]:
        effects=[]
        for budget in (5,30):
            d = data['family_differences'][str(budget)] if n==32 else (data['primary'] if budget==5 else data['secondary']['delta30'])
            effects.append(dict(populations=budget,mean=d['mean'],
                                interval=d['descriptive_interval'] if n==32 else d['interval95']))
        panels.append(dict(cohort=label,sources=n,effects=effects))
    points=[]
    for c in rb2['configurations']:
        key=f"{c['family']}-{c['populations']}"
        a=rb2['absolute'][key]
        assert c['episodes']==3072
        assert abs(c['successes']/c['episodes']-a['mean']) < 1e-12
        points.append(dict(arm=key,episodes=c['episodes'],successes=c['successes'],
                           rate=a['mean'],interval=a['interval95'],
                           complete_episode_total_seconds=c['episode_timing_totals']['complete_episode_seconds'],
                           mean_complete_episode_seconds=c['episode_timing_totals']['complete_episode_seconds']/c['episodes']))
    inputs=dict(provenance={'RB1':p1,'RB2':p2},figure_a=panels,figure_b=points,
                arithmetic_only='Proportion to percentage/pp; complete episode total divided by count. No interval calculation.',
                timing='Includes instrumentation/evidence; excludes shared backend/model setup.')
    (ROOT/'FIGURE-DATA.json').write_text(json.dumps(inputs,indent=2)+'\n',encoding='utf-8')

    a=Canvas(1500,740)
    a.text(60,55,'A  |  Diffusion minus matched GMM',32,bold=True)
    a.text(60,92,'Fixed estimates and published 95% source-cluster intervals; cohorts remain separate',22,color=GRAY)
    for p,left in zip(panels,(80,810)):
        a.text(left,160,f"{p['cohort']}  /  {p['sources']} development sources",25,bold=True)
        xmin,xmax=-10,12
        x=lambda v:left+85+(v-xmin)/(xmax-xmin)*520
        yaxis=525
        a.line(x(xmin),yaxis,x(xmax),yaxis)
        for tick in (-10,-5,0,5,10):
            a.line(x(tick),yaxis,x(tick),yaxis+7)
            a.text(x(tick),yaxis+33,f'{tick:+d}' if tick else '0',19,anchor='middle')
        a.line(x(0),200,x(0),yaxis,'#B7BDC5',2)
        for e,y in zip(p['effects'],(280,430)):
            m=e['mean']*100; low,high=[v*100 for v in e['interval']]
            color=BLUE if e['populations']==5 else ORANGE
            a.text(left,y+7,str(e['populations']),23,bold=True)
            a.line(x(low),y,x(high),y,color,4)
            a.line(x(low),y-9,x(low),y+9,color,3)
            a.line(x(high),y-9,x(high),y+9,color,3)
            a.dot(x(m),y,color)
            a.text(left+85,y+53,f'{display_pp(m)}  [{display_pp(low)}, {display_pp(high)}] pp',21,color=color)
        a.text(left,206,'Populations',19,color=GRAY)
        a.text(left+345,598,'Diffusion − GMM (percentage points)',22,anchor='middle')
    a.text(60,661,'RB1: 30-population outcomes reused from LGP1; RB1 interval retained, not LGP1’s original interval.',20,color=GRAY)
    a.text(60,699,'No pooling, new resampling, subgroup selection or cross-cohort significance test.',20,color=GRAY)
    a.save('figure-a')

    b=Canvas(1500,880)
    b.text(65,57,'B  |  RB2 native success and measured episode time',32,bold=True)
    b.text(65,95,'512 source clusters; 3,072 episodes per arm; published success intervals only',22,color=GRAY)
    x=lambda t:160+t/14*1180
    y=lambda r:660-(r-10)/12*440
    for rate in (10,12,14,16,18,20,22):
        b.line(x(0),y(rate),x(14),y(rate),'#E2E6EA',1)
        b.text(135,y(rate)+7,f'{rate}%',20,anchor='end')
    for second in range(0,15,2):
        b.line(x(second),660,x(second),668)
        b.text(x(second),696,str(second),20,anchor='middle')
    b.line(160,220,160,660)
    b.line(160,660,1340,660)
    b.text(160,173,'Native success (%)',23,bold=True)
    for p in points:
        px=x(p['mean_complete_episode_seconds']); py=y(p['rate']*100)
        lo,hi=[y(v*100) for v in p['interval']]
        isg=p['arm'].startswith('gmm')
        col=BLUE if isg else ORANGE
        b.line(px,lo,px,hi,col,3)
        b.line(px-8,lo,px+8,lo,col,3);b.line(px-8,hi,px+8,hi,col,3)
        b.dot(px,py,col,square=not isg)
        dx=-28 if isg else 25
        dy=-17 if isg else 31
        name=p['arm'].replace('gmm-','GMM').replace('diffusion-','Diffusion')
        b.text(px+dx,py+dy,name,23,col,True,'end' if isg else 'start')
    b.text(750,750,'Mean complete-episode time (seconds; published total ÷ 3,072)',23,anchor='middle')
    b.text(65,802,'Timing includes initialization, planning, physical delivery, instrumentation/evidence and close.',21,color=GRAY)
    b.text(65,840,'Shared model setup excluded. No time intervals or statistical Pareto-dominance claim.',21,color=GRAY)
    b.save('figure-b')
    print(json.dumps(dict(points=[(p['arm'],p['mean_complete_episode_seconds']) for p in points],
                          intervals_copied_unchanged=True,formats=['SVG','PNG'])))


if __name__=='__main__':
    main()
