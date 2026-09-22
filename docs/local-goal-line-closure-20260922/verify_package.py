"""Read-only checks of closure documents, fixed summaries and links. No science run."""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
from PIL import Image

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent.parent
BASE='dcf51819b1e0961388856e890b1e3c7f833257fe'


def pinned(commit,path):
    return subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=REPO)


def main():
    checks=[]
    def require(name, condition):
        if not condition: raise AssertionError(name)
        checks.append(name)
    discussion=(ROOT/'RESULTS-AND-DISCUSSION.md').read_text(encoding='utf-8')
    prose=re.sub(r'^\[[^\]]+\]:.*$', '', discussion, flags=re.M)
    words=len(prose.split())
    require('Discussion is 2000-3000 words (excluding reference definitions)',2000<=words<=3000)
    decision=(ROOT/'DECISION.md').read_text(encoding='utf-8')
    require('Decision compact one-page text ceiling (350 words)',len(decision.split())<=350)
    require('All five fixed RB2 contrast estimates included',all(v in discussion for v in ['−0.7487','−0.7813','+0.0326','−2.7669','−3.5482']))
    require('All four rate/count pairs present',all(v in discussion for v in ['464 / 3,072','441 / 3,072','550 / 3,072','526 / 3,072']))
    claims=list(csv.DictReader((ROOT/'CLAIMS-AND-EVIDENCE.csv').open(newline='',encoding='utf-8')))
    require('32 complete six-column claim records',len(claims)==32 and all(len(r)==6 and all(r.values()) for r in claims))
    require('All five claim categories present',set(r['category'] for r in claims)=={'reported result','arithmetic derivation','interpretation','limitation','prospective research decision'})
    url_re=r'https://github\.com/ckontz01/diffusion-world-model-planning-thesis/blob/([a-f0-9]{40})/([^\s\)\];]+)'
    texts=[discussion,decision,(ROOT/'README.md').read_text(encoding='utf-8')]
    texts.extend(r['immutable_supporting_files'] for r in claims)
    refs=set()
    for text in texts:
        refs.update((c,p.rstrip('"')) for c,p in re.findall(url_re,text))
    sources=[]
    for commit,path in sorted(refs):
        b=pinned(commit,path)
        sources.append(dict(commit=commit,path=path,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
    require('Every immutable evidence link resolves to its exact local Git blob',len(sources)>=11)
    # Check actual document links without fetching web pages or protected payloads.
    future={'MANIFEST.json','CHECKS.json','BACKUP-RECEIPT.json'}
    local_links=[]
    for path in ROOT.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if target.startswith('https:'): continue
            dest=(path.parent/target.split('#')[0])
            require('Local link '+path.name+' -> '+target,dest.exists() or target in future)
            local_links.append(target)
    data=json.loads((ROOT/'FIGURE-DATA.json').read_text())
    p1=data['provenance']['RB1'];p2=data['provenance']['RB2']
    rb1=json.loads(pinned(p1['commit'],p1['path']));rb2=json.loads(pinned(p2['commit'],p2['path']))
    for panel in data['figure_a']:
        require('Separate cohort '+panel['cohort'],panel['sources'] in (32,512))
        for row in panel['effects']:
            s=rb1['family_differences'][str(row['populations'])] if panel['sources']==32 else (rb2['primary'] if row['populations']==5 else rb2['secondary']['delta30'])
            interval=s['descriptive_interval'] if panel['sources']==32 else s['interval95']
            require(f"Unchanged Figure A estimate/interval {panel['cohort']} {row['populations']}",row['mean']==s['mean'] and row['interval']==interval)
    for p in data['figure_b']:
        c=next(c for c in rb2['configurations'] if f"{c['family']}-{c['populations']}"==p['arm'])
        a=rb2['absolute'][p['arm']]
        require('Unchanged Figure B interval '+p['arm'],p['interval']==a['interval95'] and p['rate']==a['mean'])
        require('Arithmetic only mean '+p['arm'],p['episodes']==c['episodes']==3072 and p['mean_complete_episode_seconds']==c['episode_timing_totals']['complete_episode_seconds']/3072)
        require('Rate-count agreement '+p['arm'],abs(p['successes']/3072-p['rate'])<1e-12)
    svg_ns={'s':'http://www.w3.org/2000/svg'}
    for name,size in [('figure-a',(1500,740)),('figure-b',(1500,880))]:
        tree=ET.parse(ROOT/(name+'.svg'))
        with Image.open(ROOT/(name+'.png')) as image:
            require(name+' PNG dimensions',image.size==size)
            image.verify()
        require(name+' SVG labels',len(tree.findall('.//s:text',svg_ns))>=15)
    root_readme=(REPO/'README.md').read_text(encoding='utf-8')
    old=pinned(BASE,'README.md').decode('utf-8')
    old_tail=old[old.index('implements the delegated reasoning'):]
    require('Root README historical chronology unchanged after new dated status',old_tail==root_readme[root_readme.index('implements the delegated reasoning'):])
    monitor=json.loads((ROOT/'MONITOR-FINAL-STATUS.json').read_text())
    require('Only identified RB2 monitor paused, not deleted',monitor['status_after']=='PAUSED' and monitor['id']=='monitor-lgp-rb1-every-two-hours' and not monitor['unrelated_tasks_modified'] and not monitor['deleted'])
    paths=subprocess.check_output(['git','diff','--name-only',BASE],cwd=REPO,text=True).splitlines()
    require('Tracked edits confined to README and closure package',all(p=='README.md' or p.startswith('docs/local-goal-line-closure-20260922/') for p in paths))
    total=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    require('Package below 250000000 bytes',total<250_000_000)
    result=dict(passed=True,check_count=len(checks),checks=checks,discussion_word_count=words,
                decision_word_count=len(decision.split()),package_bytes_at_check=total,
                immutable_sources=sources,local_links=local_links,
                visual_review='Both full scientific figures and Claims A1:C3 preview inspected; no clipped scientific labels or hidden points. Figure A decimal formatting aligned to published report.',
                source_limitations=['No new source blocker','Historical30 separate reset/episode times unavailable, not reconstructed','E11 retains original task-callable endpoint/interface','Fixed-seed and development-population limits retained'],
                link_scope='Local immutable Git blobs, not unauthenticated external URL availability',
                scope='Documentation, fixed-summary arithmetic and plotting only; no new inferential/scientific analysis')
    (ROOT/'CHECKS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k in ['passed','check_count','discussion_word_count','decision_word_count','package_bytes_at_check']}))


if __name__=='__main__': main()
