"""Publish only already-sealed results after the completed nativeSSD verification gate."""
import hashlib,json,tarfile,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
SSD=Path('D:/THESIS-BACKUPS/active-counterfactual-verification-pilot-v1/run-c2c6fcbe8c41fed2')
EXPECTED='bd0f53b85c3de36376bc68a084d4fbc7cb5b0958943534a890d0ee9b2d70342b'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(n,data):
    raw=data if isinstance(data,bytes) else (json.dumps(data,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    with (HERE/n).open('xb') as f:f.write(raw)
req=read(SSD/'REQUEST.json');gate=read(SSD/'BACKUP-VERIFIED.json')
assert gate['status']=='VERIFIED' and gate['archive']==req['sha256']==EXPECTED
assert gate['bytes']==req['bytes']==(SSD/'final.tar').stat().st_size==814663680
assert gate['members']==len(req['members'])==3308 and not (SSD/'final.tar.partial').exists()
assert req['campaign_accounting']['successful_unique_tasks']==339 and req['campaign_accounting']['campaign_allocations']==340
with tarfile.open(SSD/'final.tar','r:') as tar:
    def raw(n):
        b=tar.extractfile(n).read();assert {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}==req['members'][n];return b
    def get(n):return json.loads(raw(n))
    report=raw('run/analysis/REPORT.json');write('REPORT.json',report)
    write('CAMPAIGN-ACCOUNTING.json',req['campaign_accounting'])
    write('MODEL-FREEZE.json',raw('run/MODEL-FREEZE.json'))
    write('ANALYSIS-TECHNICAL.json',raw('run/analysis/TECHNICAL.json'))
    write('FINAL-SCHEDULER.json',raw('r5_control/FINAL-SCHEDULER.json'))
    write('R5-COMPLETE.json',raw('r5_control/COMPUTE-COMPLETE.json'))
    fits={}
    for n in req['members']:
        if n.startswith(('run/fit-joint/','run/fit-ordinary/')) and n.endswith('.json'):
            fits[n]=get(n)
    write('FIT-RECORDS.json',fits)
write('BACKUP-VERIFIED.json',(SSD/'BACKUP-VERIFIED.json').read_bytes())
write('PRESERVATION.json',{'read_gate_unix':time.time(),'ssd':str(SSD),'archive_sha256':EXPECTED,'bytes':req['bytes'],'members':len(req['members']),
    'request_sha256':hashlib.sha256((SSD/'REQUEST.json').read_bytes()).hexdigest(),'backup_receipt_sha256':hashlib.sha256((SSD/'BACKUP-VERIFIED.json').read_bytes()).hexdigest(),
    'archive_wall_seconds':req['archive_wall_seconds'],'archive_cpu_seconds':req['archive_cpu_seconds'],'transfer_wall_seconds':gate['wall_seconds'],
    'root_labels':req['root_labels'],'scientific_aggregate_first_opened_after_verified_backup':True,'historical_archives_transferred':0,
    'source_manifest':req['package_sha256'],'worker_approval':req['approval_sha256'],'r5_manifest':req['r5_manifest'],'r6_manifest':req['r6_manifest']})
r=json.loads(report)
print(json.dumps({'status':r['status'],'success_mean':r['success_mean'],'primary_comparisons':r['primary_comparisons'],
    'source_ids':r['source_ids'],'fit_records':list(fits),'report_bytes':len(report)},indent=2))
