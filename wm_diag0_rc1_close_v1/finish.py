"""Terminal CPU authentication, direct native SSD preservation and gated results."""
import base64,hashlib,json,os,shlex,subprocess,sys,threading,time
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from .transport_v2 import call
from wm_diag0_rc1_final_v2 import native_transfer_v3 as receiver
from wm_diag0_rc1_final_v2.archive_v2 import canonical
from wm_diag0_rc1_final_v1 import postarchive_v1 as sidecar

TERMINAL=r'''
import base64,hashlib,json,os,subprocess,sys,time
from pathlib import Path
data=json.load(sys.stdin);cp=Path(data['contract_path']);expected=data['contract'];c=json.loads(cp.read_text());f=c['rc1_final'];ops=Path(f['operational_root']);task=Path(f['run'])/'tasks/analysis-0'
sys.path.insert(0,str(cp.parent))
from wm_diag0_rc1_final_v2.evidence_auth_v1 import bound_json,bound_bytes
from wm_diag0_rc1_final_v2.archive_v2 import canonical
from wm_diag0_rc1_close_v1.closed_identity_v2 import identity
from wm_diag0_rc1_close_v1.analysis_closure_v2 import authenticate_closed
from wm_diag0_rc1_final_v1 import postarchive_v1 as sidecar
end=time.monotonic()+45
bound_bytes(cp,expected,1000000,end)
dispatch=json.loads((ops/'submission/DISPATCH.json').read_text());job=dispatch['job_id']
if dispatch['contract']!=expected or dispatch['staged_members']!=c['staged_members']:raise ValueError('actual frozen dispatch')
raw=subprocess.check_output(['sacct','-X','-n','-P','-j',job,'--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=10)
rows=[line.split('|') for line in raw.splitlines() if line]
if len(rows)!=1 or len(rows[0])!=7 or rows[0][:4]!=[job,job,'COMPLETED','0:0'] or rows[0][5]!='4' or not rows[0][4].isdigit() or not 0<int(rows[0][4])<=3600:raise ValueError('actual exact terminal CPU success/accounting')
closed_path=ops/'cpu/controls/ANALYSIS-CLOSED.json';closed=bound_json(closed_path,identity(closed_path,8000,end),8000,end)
authenticate_closed(c,expected,task,closed,end)
supervisor=bound_json(ops/'cpu/controls/SUPERVISOR-CLOSED.json',identity(ops/'cpu/controls/SUPERVISOR-CLOSED.json',100000,end),100000,end)
if supervisor['job_id']!=job or supervisor['closed_analysis_identity']!=identity(closed_path,8000,end):raise ValueError('closed actual supervisor chain')
readback=bound_json(ops/'archive/ARCHIVE-READBACK.json',identity(ops/'archive/ARCHIVE-READBACK.json',64000,end),64000,end)
if supervisor['archive_readback']['whole']!=readback['whole'] or readback['binding']['final_contract_sha256']!=expected['sha256']:raise ValueError('same archive independently read back after complete analysis')
archive=Path(f['archive_path'])
if archive.lstat().st_size!=readback['whole']['bytes']:raise ValueError('archive changed after closed readback')
portable=ops/'archive/portable-inventory.json'
bound_bytes(portable,readback['portable_inventory'],20000000,end)
terminal={'status':'ACTUAL_FINAL_CPU_TERMINAL_COMPLETE_ANALYSIS_AND_ARCHIVE_AUTHENTICATED','scheduler_raw':raw,'job_id':job,'contract':expected,
 'CPU_seconds':int(rows[0][4]),'CPU_history':1436,'protected_conversion_seconds_untouched':1800,
 'analysis_output_seal':closed['analysis_output_seal'],'archive_whole':readback['whole'],'archive_manifest':readback['manifest'],
 'portable_inventory':readback['portable_inventory'],'scientific_payloads_read':False}
control_root=ops/'postarchive/controls';terminal_path=control_root/'TERMINAL-CPU.json'
with terminal_path.open('xb') as out:out.write(canonical(terminal))
names=['submission/PREFLIGHT.json','submission/SBATCH-REQUEST.json','submission/SBATCH-RESPONSE.json','submission/DISPATCH.json','submission/RELEASE.json',
 'cpu/controls/ENTRY-VERIFIED.json','cpu/controls/PHASE-analysis.json','cpu/controls/PHASE-independent_acceptance.json','cpu/controls/PHASE-archive.json',
 'cpu/controls/ANALYSIS-CLOSED.json','cpu/controls/CPU-PHASES-COMPLETE.json','cpu/controls/SUPERVISOR-CLOSED.json',
 'cpu/supervisor.log','cpu/archive.log','archive/ARCHIVE-READBACK.json']
expected_controls={'TERMINAL-CPU.json':identity(terminal_path,100000,end)}
for name in names:
 source=ops/name;want=identity(source,300000,end);content=bound_bytes(source,want,300000,end,retain=True)
 target=control_root/name;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as out:out.write(content)
 expected_controls[name]=want
binding={'final_contract_sha256':expected['sha256'],'archive_whole':readback['whole'],'archive_manifest':readback['manifest'],'analysis_output_seal':closed['analysis_output_seal']}
raw_sidecar=sidecar.build(control_root,expected_controls,binding,'TERMINAL_CPU',None,end)
if len(raw_sidecar)>1000000:raise ValueError('full terminal control sidecar finite cap')
sid=sidecar.write_exclusive(ops/'sidecars/TERMINAL-CPU.json',raw_sidecar,end,control_root)
sidecar.verify(raw_sidecar,expected_controls,binding,'TERMINAL_CPU',None,sid,end)
members=bound_json(task/'output/MEMBERS.json',closed['analysis_output_seal'],20000000,end)
print(json.dumps({'status':terminal['status'],'job_id':job,'CPU_seconds':int(rows[0][4]),'contract':expected,
 'archive':str(archive),'whole':readback['whole'],'manifest':readback['manifest'],'portable_path':str(portable),'portable':readback['portable_inventory'],
 'archive_binding':readback['binding'],'sidecar_path':str(ops/'sidecars/TERMINAL-CPU.json'),'sidecar':sid,'control_map':expected_controls,'sidecar_binding':binding,
 'analysis_output_members':members,'analysis_output_seal':closed['analysis_output_seal'],'task':str(task),'ops':str(ops),'scientific_values_read':False},separators=(',',':')))
'''

UPLOAD=r'''
import base64,hashlib,json,os,sys
from pathlib import Path
data=json.load(sys.stdin);path=Path(data['ops'])/'sidecars/SSD-TRANSFER.json';raw=base64.b64decode(data['raw'])
if len(raw)>1000000 or {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=data['identity']:raise ValueError('bounded native sidecar identity')
if path.parent!=Path('/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015-rc1-preservation-v2/sidecars'):raise ValueError('exact disjoint final sidecar path')
with path.open('xb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
after=path.read_bytes()
if after!=raw:raise ValueError('remote independent sidecar readback')
print(json.dumps({'status':'SECOND_SIDECAR_REMOTE_WHOLE_BYTES_VERIFIED','identity':data['identity']}))
'''

def selected_publication():
    path=DOC/'SSD-VERIFIED-002.json'
    if not path.exists():path=DOC/'SSD-VERIFIED-001.json'
    return json.loads(path.read_text())

def terminal():
    pub=selected_publication();path=DOC/('FINAL-CONTRACT-002.json' if (DOC/'FINAL-CONTRACT-002.json').exists() else 'FINAL-CONTRACT.json')
    c=json.loads(path.read_text())
    if identity(path)!=pub['contract']:raise ValueError('frozen final source contract')
    return call('TERMINALCPU001',TERMINAL,{'contract_path':c['rc1_final']['run']+'/source/FINAL-CONTRACT.json','contract':pub['contract']},seconds=65)

def binary_command(path,seconds):
    if not path.startswith('/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015') or '..' in path.split('/') or '\n' in path or '\x00' in path:raise ValueError('fixed bound final artifact path')
    return ['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout',str(seconds)+'s','ssh','-o','BatchMode=yes','-o','ConnectTimeout=12','-o','ConnectionAttempts=1','prometheus','cat -- '+shlex.quote(path)]

def stream_file(remote,partial,want,end,stderr_path):
    stop=threading.Event();thread=None;process=None
    with Path(stderr_path).open('xb') as error_log:
        def factory():
            nonlocal thread,process
            process=subprocess.Popen(binary_command(remote,max(1,int(end-time.monotonic()))),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            def drain():
                count=0
                while not stop.is_set():
                    raw=process.stderr.read(1024)
                    if not raw:return
                    if count+len(raw)>100000:
                        process.kill();return
                    error_log.write(raw);error_log.flush();count+=len(raw)
            thread=threading.Thread(target=drain,daemon=True);thread.start();return process
        try:return receiver.stream_once(factory,partial,want,end)
        finally:
            stop.set()
            if thread is not None:thread.join(timeout=1)

def transfer():
    began=time.monotonic();end=began+7180;stream_end=began+5380;verify_end=began+6880
    terminal=json.loads((DOC/'TERMINALCPU001.json').read_text());pub=selected_publication()
    if terminal['status']!='ACTUAL_FINAL_CPU_TERMINAL_COMPLETE_ANALYSIS_AND_ARCHIVE_AUTHENTICATED' or terminal['contract']!=pub['contract']:raise ValueError('actual complete CPU/analysis/archive chain')
    destination,volume=receiver.destination()
    if destination.exists():raise FileExistsError('never duplicate final SSD destination or partial')
    destination.mkdir(parents=True,exist_ok=False)
    for p in (destination,)+tuple(destination.parents):
        if p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400:raise ValueError('ordinary designated native SSD ancestors')
    portable_path=destination/'portable-inventory.json';portable_partial=destination/'portable-inventory.partial'
    stream_file(terminal['portable_path'],portable_partial,terminal['portable'],stream_end,destination/'portable-transport.stderr')
    portable_partial.rename(portable_path)
    portable=json.loads(portable_path.read_bytes())
    side_path=destination/'TERMINAL-CPU.json';side_partial=destination/'TERMINAL-CPU.partial'
    stream_file(terminal['sidecar_path'],side_partial,terminal['sidecar'],stream_end,destination/'sidecar-transport.stderr');side_partial.rename(side_path)
    first=sidecar.verify(side_path.read_bytes(),terminal['control_map'],terminal['sidecar_binding'],'TERMINAL_CPU',None,terminal['sidecar'],stream_end)
    partial=destination/'final-study.tar.partial';target=destination/'final-study.tar'
    streamed=stream_file(terminal['archive'],partial,terminal['whole'],stream_end,destination/'archive-transport.stderr')
    verified=receiver.verify_and_promote(partial,target,portable,terminal['archive_binding'],terminal['whole'],terminal['manifest'],terminal['portable'],verify_end)
    if verified['status']!='WHOLE_AND_EVERY_MEMBER_INDEPENDENTLY_VERIFIED':raise ValueError('actual native archive readback')
    control=destination/'native-controls';control.mkdir()
    write_new(control/'NATIVE-READBACK.json',{'readback':verified,'stream':streamed,'volume_before':volume,'first_sidecar':first,'terminal_CPU':terminal['job_id']})
    expected={'NATIVE-READBACK.json':identity(control/'NATIVE-READBACK.json')}
    raw=sidecar.build(control,expected,terminal['sidecar_binding'],'SSD_TRANSFER',terminal['sidecar'],end)
    if len(raw)>1000000:raise ValueError('native postarchive sidecar cap')
    sid=sidecar.write_exclusive(destination/'SSD-TRANSFER.json',raw,end,control)
    sidecar.verify((destination/'SSD-TRANSFER.json').read_bytes(),expected,terminal['sidecar_binding'],'SSD_TRANSFER',terminal['sidecar'],sid,end)
    remote=call('POSTARCHIVEUPLOAD001',UPLOAD,{'ops':terminal['ops'],'raw':base64.b64encode(raw).decode(),'identity':sid},seconds=60)
    if remote['identity']!=sid:raise ValueError('exact two-copy sidecar readback')
    _,after=receiver.destination()
    result={'status':'COMPLETE_STUDY_INDEPENDENT_ACCEPTANCE_AND_FINAL_DESIGNATED_SSD_WHOLE_EVERY_MEMBER_GATE_PASSED',
        'source':identity(__file__),'contract':terminal['contract'],'source_commit':pub['source_commit'],
        'archive':str(target),'whole':terminal['whole'],'manifest':terminal['manifest'],'portable':terminal['portable'],
        'native_readback':verified,'terminal_CPU_job':terminal['job_id'],'terminal_CPU_seconds':terminal['CPU_seconds'],
        'first_sidecar':terminal['sidecar'],'second_sidecar':sid,'second_sidecar_remote_readback':remote,
        'designated_SSD_volume':after,'no_third_full_archive_copy':True,'scientific_values_read_before_gate':False,
        'parents':128,'ordinary_grid_runs':124,'source_roots':120,'retained_fits':6,'active_heads':4,'all_attempts':139}
    write_new(destination/'FINAL-SSD-VERIFIED.json',result);write_new(DOC/'FINAL-SSD-VERIFIED.json',result)
    if identity(destination/'FINAL-SSD-VERIFIED.json')!=identity(DOC/'FINAL-SSD-VERIFIED.json'):raise ValueError('host/SSD final gate receipt')
    print(json.dumps({k:v for k,v in result.items() if k not in ('native_readback','designated_SSD_volume')}))

def results():
    gate=json.loads((DOC/'FINAL-SSD-VERIFIED.json').read_text());terminal=json.loads((DOC/'TERMINALCPU001.json').read_text())
    ssd=Path(gate['archive']).parent
    if identity(DOC/'FINAL-SSD-VERIFIED.json')!=identity(ssd/'FINAL-SSD-VERIFIED.json') or gate['whole']!=terminal['whole']:raise PermissionError('actual matching final gate before scientific access')
    for name in ('RESULTS.json','ACCEPTANCE.json'):
        target=DOC/name;partial=DOC/(name+'.partial')
        stream_file(terminal['task']+'/output/'+name,partial,terminal['analysis_output_members'][name],time.monotonic()+120,DOC/(name+'.transport.stderr'))
        if identity(partial)!=terminal['analysis_output_members'][name]:raise ValueError('exact independently validated results byte identity')
        partial.rename(target)
    write_new(DOC/'RESULTS-RELEASED.json',{'status':'COMPLETE_VALIDATED_RESULTS_FETCHED_AFTER_FINAL_SSD_GATE','final_gate':identity(DOC/'FINAL-SSD-VERIFIED.json'),
        'RESULTS':identity(DOC/'RESULTS.json'),'ACCEPTANCE':identity(DOC/'ACCEPTANCE.json'),'payload_before_gate':False})
    print(json.dumps({'status':'COMPLETE_VALIDATED_RESULTS_RELEASED_FOR_REPORT_AND_GITHUB'}))

def main():
    mode=sys.argv[1]
    if mode=='terminal':print(json.dumps(terminal()))
    elif mode=='transfer':transfer()
    elif mode=='results':results()
    else:raise ValueError('fixed terminal/transfer/results phases only')
if __name__=='__main__':main()
