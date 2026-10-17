"""Exact new CPU job status, compact new-package readback; no old archive copy."""
import hashlib,json,os,shlex,subprocess,sys,time,zipfile
from pathlib import Path
from .common import DOC,REMOTE,identity,write_new
from .transport import call

STATUS=r'''
import hashlib,json,subprocess,sys
from pathlib import Path
d=json.load(sys.stdin);root=Path(d['root']);dispatch=json.loads((root/'controls/DISPATCH.json').read_text())
if dispatch['job_id']!=d['job_id'] or dispatch['freeze']!=d['freeze']:raise ValueError('actual exact new CPU dispatch')
raw=subprocess.check_output(['sacct','-X','-n','-P','-j',d['job_id'],'--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=8)
rows=[x.split('|') for x in raw.splitlines() if x]
if len(rows)!=1 or len(rows[0])!=7 or rows[0][:2]!=[d['job_id'],d['job_id']]:raise ValueError('one exact new CPU scheduler row')
state=rows[0][2];result={'status':'EXACT_NEW_SAVED_DATA_CPU_STATUS','scheduler_raw':raw,'job_id':d['job_id'],'state':state,'freeze':d['freeze']}
if state=='COMPLETED':
 if rows[0][3]!='0:0' or rows[0][5]!='4' or not 0<int(rows[0][4])<=1800:raise ValueError('actual saved-data CPU success/resources')
 p=root/'READY.json';b=p.read_bytes();ready=json.loads(b)
 if ready['status']!='ONE_SAVED_DATA_PASS_COMPLETE_CLOSED_PACKAGE_VERIFIED' or ready['freeze']!=d['freeze'] or ready['job_id']!=d['job_id']:raise ValueError('complete frozen one-pass output')
 result.update(ready=ready,ready_identity={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
if state not in ('RUNNING','PENDING'):
 p=root/'slurm.log'
 if p.exists():
  if p.is_symlink() or p.stat().st_size>64000:raise ValueError('bounded closed Slurm technical log')
  result['closed_slurm_log']=p.read_text()
 for name in ('controls/CPU-FAILED.json','analysis/SAVED-DATA-STOP.json'):
  p=root/name
  if p.exists():
   if p.stat().st_size>20000:raise ValueError('bounded exact saved-data issue')
   result[name]=json.loads(p.read_text())
print(json.dumps(result))
'''

def status(label):
    staged=json.loads((DOC/'STAGE001.json').read_text())
    return call(label,STATUS,{'root':REMOTE,'job_id':staged['job_id'],'freeze':staged['freeze']},seconds=25)

def collect(label):
    value=json.loads((DOC/(label+'.json')).read_text())
    if value['state']!='COMPLETED':raise ValueError('actual complete one-pass result required, no partial result collection')
    ready=value['ready'];want=ready['package']
    if want['bytes']>50000000 or ready['package_path']!=REMOTE+'/SAVED-DATA-PACKAGE.zip':raise ValueError('small new saved-only package, not completed study archive')
    from wm_diag0_rc1_final_v1.native_transfer_v1 import stream_once
    path=DOC/'SAVED-DATA-PACKAGE.zip';partial=DOC/'SAVED-DATA-PACKAGE.partial';stderr=DOC/'package-transport.stderr'
    with stderr.open('xb') as log:
        def factory():return subprocess.Popen(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout','70s','ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ConnectionAttempts=1','prometheus','cat -- '+shlex.quote(ready['package_path'])],stdout=subprocess.PIPE,stderr=log)
        streamed=stream_once(factory,partial,want,time.monotonic()+75)
    target=DOC/'collected';target.mkdir(exist_ok=False)
    with zipfile.ZipFile(partial) as z:
        names=z.namelist();expected=ready['member_map']
        if len(names)!=len(expected) or set(names)!=set(expected):raise ValueError('exact new compact package membership')
        for name in names:
            if name.startswith('/') or '..' in name.split('/') or '\\' in name or not name.startswith(('output/','controls/')):raise ValueError('new relative compact evidence names only')
            info=z.getinfo(name);w=expected[name]
            if info.file_size!=w['bytes'] or info.file_size>35000000:raise ValueError('compact member byte cap')
            raw=z.read(name)
            if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=w:raise ValueError('new compact every-member independent readback')
            write_new(target/name,raw,limit=35000000)
    if identity(partial)!=want:raise ValueError('whole compact package independent native readback')
    partial.rename(path)
    if identity(target/'output/MEMBERS.json')!=ready['output_seal']:raise ValueError('closed new output seal')
    output_members=json.loads((target/'output/MEMBERS.json').read_text())
    if any(identity(target/'output'/name)!=w for name,w in output_members.items()):raise ValueError('independent collected closed-output member authentication')
    if set(output_members)!={n[len('output/'):] for n in expected if n.startswith('output/') and n!='output/MEMBERS.json'}:raise ValueError('complete closed output membership')
    write_new(DOC/'COLLECTED.json',{'status':'ONE_COMPLETE_SAVED_DATA_PASS_NEW_PACKAGE_WHOLE_EVERY_MEMBER_VERIFIED','source_status':identity(DOC/(label+'.json')),'package':identity(path),'output_seal':ready['output_seal'],'verified_members':len(ready['member_map']),'stream':streamed,'old_study_archive_read_or_copied':False})
    write_new(DOC/'CLOSED-SLURM-LOG.txt',value.get('closed_slurm_log','').encode())
    print(json.dumps({'status':'COLLECTED_COMPLETE_SAVED_DATA_DISCOVERY_RESULTS','members':len(ready['member_map'])}))

def main():
    mode,label=sys.argv[1:3]
    if mode=='status':
        value=status(label);print(json.dumps({'job_id':value['job_id'],'state':value['state'],'complete_ready':'ready' in value}))
    elif mode=='collect':collect(label)
    else:raise ValueError('fixed status/collect modes')

if __name__=='__main__':main()
