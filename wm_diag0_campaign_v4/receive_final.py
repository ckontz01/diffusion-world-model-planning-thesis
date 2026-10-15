"""Native Windows final SSD transfer, only after exact analysis allocation ends.

Never runs compute, extracts tar members, or opens scientific result values.
Failed transfer partials/receipts remain; no blind retry or overwrite.
"""
import hashlib,json,os,shlex,subprocess,time
from pathlib import Path
from .common import DOC,RUN,write_new
from .verify_archive import verify
from wm_diag0_preflight_v1.preserve import volume
from wm_diag0_native_v3.transport import ssh

def main():
    if os.name!='nt':raise RuntimeError('native Windows transfer only')
    v=volume();path=DOC/'campaign';write_new(path/'FINAL-TRANSFER-001.started.json',{'run':RUN,'volume':v,'no_compute_or_extraction':True})
    metadata=ssh('RUN='+repr(RUN)+'\n'+'''
import json,pathlib,subprocess
r=pathlib.Path(RUN);d=json.loads((r/'controls/DAG-DISPATCH.json').read_text());job=d['jobs']['analysis']
raw=subprocess.check_output(['sacct','-X','-n','-P','-j',job,'--format=JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS'],universal_newlines=True,timeout=15)
rows=[x.split('|') for x in raw.splitlines() if x.strip()]
if len(rows)!=1 or rows[0][0]!=job or rows[0][1]!='COMPLETED' or rows[0][2]!='0:0' or rows[0][4]!='4':raise RuntimeError('exact final CPU allocation must be successful terminal')
c=json.loads((r/'source/CONTRACT.json').read_text());result=json.loads((r/'tasks/analysis-0/controls/RESULT.json').read_text());accepted=json.loads((r/'tasks/analysis-0/controls/ACCEPTED.json').read_text());archive=json.loads((r/'preservation/ARCHIVE-CREATED.json').read_text())
if result['status']!='ACCEPTED' or archive['analysis_output_seal']!=accepted['output_seal'] or archive['contract_sha256']!=d['contract_sha256']:raise ValueError('complete acceptance/archive identity chain')
total=c['cpu_charged_before']+int(rows[0][3])
if total+1800>13800:raise ValueError('all-attempt CPU cap with unused conversion reserve')
print(json.dumps({'archive':archive,'analysis_result':result,'analysis_acceptance':accepted,'final_CPU_scheduler':raw,'CPU_total_charged':total,'conversion_seconds_consumed':0,'GPU_scheduler':json.loads((r/'tasks/analysis-0/controls/ALL-ALLOCATIONS-TERMINAL.json').read_text())}))
''')
    archive=metadata['archive']
    if archive['archive']!=RUN+'/preservation/final-study.tar' or archive['whole']['bytes']>14000000000:raise ValueError('exact final archive and bound')
    dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-final-20261015');dest.mkdir(exist_ok=True)
    target=dest/'final-study.tar';partial=dest/'final-study.tar.partial'
    if target.exists() or partial.exists():raise FileExistsError('preserve completed/failed transfer; diagnose, never overwrite')
    from wm_diag0.windows_limits import limits
    limits() # four CPU affinity and8GiB process-tree RAM cap; no environment change
    command=['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout','7200s','ssh','-o','BatchMode=yes','-o','ConnectTimeout=12','-o','ConnectionAttempts=1','prometheus','cat -- '+shlex.quote(archive['archive'])]
    began=time.monotonic();h=hashlib.sha256();count=0
    with (path/'FINAL-TRANSFER-001.stderr').open('xb') as err:
        p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=err)
        try:
            with partial.open('xb') as out:
                for b in iter(lambda:p.stdout.read(1048576),b''):
                    count+=len(b)
                    if count>archive['whole']['bytes'] or time.monotonic()-began>7200:raise RuntimeError('finite transfer byte/time bound')
                    out.write(b);h.update(b)
                out.flush();os.fsync(out.fileno())
            rc=p.wait(timeout=10)
            if rc or {'bytes':count,'sha256':h.hexdigest()}!=archive['whole']:raise ValueError('exact full transfer identity')
            proof=verify(partial,archive['whole'],archive['contract_sha256'])
            partial.rename(target)
        except BaseException:
            if p.poll() is None:p.kill();p.wait()
            write_new(path/'FINAL-TRANSFER-001.failed.json',{'bytes_retained':count,'partial':str(partial),'elapsed':time.monotonic()-began,'all_compute_left_unchanged':True})
            raise
    receipt={**proof,'archive':str(target),'volume':v,'terminal_metadata':metadata,'elapsed_seconds':time.monotonic()-began,'scientific_results_inspected':False}
    write_new(path/'FINAL-SSD-VERIFIED-001.json',receipt);write_new(dest/'FINAL-SSD-VERIFIED-001.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k!='terminal_metadata'}))

if __name__=='__main__':main()
