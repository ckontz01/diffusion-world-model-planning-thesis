"""New approved closure budget, immutable legacy receipts and exclusive writes."""
import hashlib,json,math,os,stat
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
DOC=ROOT/'docs/world-model-diagnostic-rc1-completion-budget-v1-20261016'
CAPS={'implementation':2700,'cluster_validation':600,'binding_staging':1200,
      'publication':600,'monitoring':7200,'native_SSD':7200,'technical_fault':1200,'handoff':900}
OLD_DIRS=('docs/world-model-diagnostic-rc1-v1-20261016',
          'docs/world-model-diagnostic-rc1-prep-routing-v1-20261016',
          'docs/world-model-diagnostic-rc1-ops-reserve-v1-20261016',
          'docs/world-model-diagnostic-a2-native-v3-20261015')

def raw_json(obj):return (json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf8')

def identity(path):
    p=Path(path);s=p.lstat()
    if not stat.S_ISREG(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('ordinary nonredirected file required')
    h=hashlib.sha256();size=0
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b);size+=len(b)
    return {'bytes':size,'sha256':h.hexdigest()}

def write_new(path,obj,limit=1048576):
    p=Path(path);b=raw_json(obj)
    if len(b)>limit:raise ValueError('pre-write compact metadata bound')
    for q in (p.parent,)+tuple(p.parents):
        if q.exists() and getattr(q.lstat(),'st_file_attributes',0)&0x400:raise ValueError('no metadata destination redirect')
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:
        if f.write(b)!=len(b):raise IOError('short metadata write')
        f.flush();os.fsync(f.fileno())

def utc_seconds(text):return datetime.strptime(text,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()

def authority():
    a=json.loads((DOC/'AUTHORITY.json').read_text());v=json.loads((DOC/'ACTIVATION.json').read_text())
    if a['future_component_seconds']!=CAPS or sum(CAPS.values())!=21600 or (a['new_charge_seconds'],a['total_preparation_cap_seconds'])!=(21300,35700):raise ValueError('exact human-approved finite revision')
    if (v['cumulative_nonrefundable_charge_seconds'],v['previous_nonrefundable_charge_seconds'],v['new_nonrefundable_charge_seconds'])!=(35700,14400,21300):raise ValueError('no repeated funding charge')
    if identity(DOC/'BASELINE.json')!=v['historical_baseline']:raise ValueError('immutable historical baseline')
    return a,v

def legacy_unchanged(v):
    expected=json.loads((DOC/'BASELINE.json').read_text())['members']
    found={str(p.relative_to(ROOT)).replace('\\','/') for d in OLD_DIRS for p in (ROOT/d).glob('LOCAL-*.json')}
    if found!=set(expected):raise ValueError('historical runner/receipt set changed; reconcile, no reset')
    for n,x in expected.items():
        if identity(ROOT/n)!=x:raise ValueError('historical receipt changed: '+n)

def charges():
    rows=[]
    for p in sorted(DOC.glob('LOCAL-*.json')):
        if p.name.endswith('.started.json'):continue
        z=json.loads(p.read_text());n=z.get('charged_seconds',z.get('elapsed_seconds'))
        if z.get('component') not in CAPS or type(n) not in (int,float) or not math.isfinite(n) or n<0:raise ValueError('exact finite charge receipt')
        rows.append(z)
    for p in DOC.glob('LOCAL-*.started.json'):
        end=DOC/p.name.replace('.started.json','.json')
        if not end.exists():raise RuntimeError('ambiguous started operation; authenticate before further work: '+p.name)
    return rows

def charge(row):return row.get('charged_seconds',row['elapsed_seconds'])

def check_reservation(component,seconds,now,a,v,rows,monitor_count):
    if component not in CAPS or type(seconds) is not int or not 5<=seconds<=7200:raise ValueError('explicit finite component reservation')
    if sum(charge(x) for x in rows)+seconds>21600 or sum(charge(x) for x in rows if x['component']==component)+seconds>CAPS[component]:raise ValueError('full future component/total reservation exhausted; no transfer/refund')
    if now+seconds>utc_seconds(v['stop_utc']):raise ValueError('approved120-hour horizon cannot be extended')
    if component=='monitoring' and (seconds>30 or monitor_count>=240):raise ValueError('240checks/30seconds inclusive maximum')

def reserve(component,seconds,now):
    a,v=authority();legacy_unchanged(v);rows=charges()
    started_monitor=[p for p in DOC.glob('LOCAL-*.started.json') if json.loads(p.read_text()).get('component')=='monitoring']
    check_reservation(component,seconds,now,a,v,rows,len(started_monitor))
    return a,v,rows

def owned_bytes():
    total=0
    for root in (DOC,ROOT/'wm_diag0_rc1_completion_v1'):
        for p in root.rglob('*'):
            s=p.lstat()
            if getattr(s,'st_file_attributes',0)&0x400 or stat.S_ISLNK(s.st_mode):raise ValueError('no new auxiliary redirect')
            if stat.S_ISREG(s.st_mode):total+=s.st_size
            elif not stat.S_ISDIR(s.st_mode):raise ValueError('ordinary auxiliary files only')
    # Local allocation20MB. The other44MB is reserved for bounded remote,
    # portable inventory/sidecar and small-SSD logical copies, not assumed free.
    if total>20000000:raise ValueError('local auxiliary allocation exhausted')
    return total
