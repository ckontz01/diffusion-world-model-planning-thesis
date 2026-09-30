"""Create separate operational authority; never changes approved source."""
import hashlib,json,subprocess,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
SOURCE='/lustreFS/data/superworld/ckontzias/thesis/snapshots/dtv-efficiency-correction-r1-8d3ebff35241a01f'
CONTROL='/lustreFS/data/superworld/ckontzias/thesis/staging/dtv-efficiency-20260930-8d3ebff35241a01f'
RUN='/lustreFS/data/superworld/ckontzias/thesis/experiments/dtv-efficiency-20260930/run-8d3ebff35241a01f'
MANIFEST='8d3ebff35241a01f7bf55a111a03881143ac36d57f996b7a8cb5f2e7130e8a30'
BINDINGS='cc6ae51b954df12adbddde9aae1d32cc506947c77c4237beee6f8a8f40b3af68'
ARCHIVE='71de0ef3e20f5524ce49919cd277ef30c574af2407eb745ec2517dc8cda459fe'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,value):
    with (HERE/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2)

def main():
    instruction=HERE/'AUTHORIZATION-INSTRUCTION.txt'
    if sha(instruction)!='12db6f2489669a054b90a70698921e6e3c39b5e266addfa6dcd5f4b4a6f3ca18':raise RuntimeError('instruction changed')
    doc=ROOT/'docs/dtv-efficiency-correction-r1-20260930'
    if sha(doc/'PACKAGE-MANIFEST.json')!=MANIFEST or sha(doc/'BINDINGS.json')!=BINDINGS:raise RuntimeError('approved package/bindings changed')
    from dtv_efficiency.package import verify_archive
    exported=Path('D:/THESIS-BACKUPS/dtv-efficiency-20260930/correction-r1/package-8d3ebff35241a01f/package.tar')
    if exported.stat().st_size!=4413440 or sha(exported)!=ARCHIVE:raise RuntimeError('approved source export changed')
    if verify_archive(exported,json.loads((doc/'PACKAGE-MANIFEST.json').read_text())['files'])!=282:raise RuntimeError('approved export inventory')
    volume=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command','Get-Volume -DriveLetter D | Select-Object FileSystemLabel,UniqueId,SizeRemaining | ConvertTo-Json -Compress'],text=True))
    if volume['FileSystemLabel']!='THESIS_SSD' or volume['UniqueId'].lower()!='\\\\?\\Volume{0a2f1ba9-0000-0000-0000-100000000000}\\'.lower() or volume['SizeRemaining']<40000000000:raise RuntimeError('required SSD unavailable')
    delegation=dict(authority_basis='Explicit user-supplied execution direction under the standing delegation; not a newly obtained direct user signature',standing_delegation_date='2026-09-20',standing_delegation_quote='New experiments or expanded resources/access will still need your approval. if it tells you (gpt 6 pro) to start an experiment etc. I allow you to do it without my authoraztion. dont wait for me',source_of_this_direction='Attached complete execution instruction supplied by the user in this task',browser_origin_independently_reverified_this_turn=False,rights_and_frozen_limits_remain_binding=True)
    save('DELEGATION-PROVENANCE.json',delegation)
    authority=dict(study='DTV-EFF0',execution_authorized=True,authorization_basis=delegation['authority_basis'],instruction_sha256=sha(instruction),delegation_provenance_sha256=sha(HERE/'DELEGATION-PROVENANCE.json'),source_commit='bc44841c7bef6889e1e1b33548d9c9ab6acde48e',reviewed_receipt_commit='00774af81133fc9fd6fb1cb8c54f8a0a65e87beb',package_manifest_sha256=MANIFEST,bindings_sha256=BINDINGS,source_export_sha256=ARCHIVE,source=SOURCE,control=CONTROL,run=RUN,limits=dict(workers=9,per_worker_seconds=780,work_seconds=720,preservation_seconds=60,grid_gpu_reservation_seconds=7020,aggregate_gpu_seconds=7200,cpus=4,ram_bytes=8589934592,worker_bytes=4000000,worker_logs_bytes=2000000,source_bytes=4000000,other_control_report_bytes=2000000,live_bytes=60000000,archive_bytes=62000000,inclusive_bytes=250000000,cpu_final_local_wall_seconds=600,transfer_attempts=1),no_retry=True,no_monitor=True,no_fitting_or_physics=True,created_unix=time.time())
    save('AUTHORIZATION.json',authority)
    approval=dict(study='DTV-EFF0',version='control-correction-r1',execute=True,research_execution_authorized=True,preparation_only=False,bindings_sha256=BINDINGS,package_manifest_sha256=MANIFEST,authorization_record=CONTROL+'/AUTHORIZATION.json',authorization_record_sha256=sha(HERE/'AUTHORIZATION.json'))
    save('EXECUTION-APPROVAL.json',approval)
    identity=dict(instruction_sha256=sha(instruction),authority_sha256=sha(HERE/'AUTHORIZATION.json'),enabled_approval_sha256=sha(HERE/'EXECUTION-APPROVAL.json'),false_template_sha256=sha(doc/'EXECUTION-APPROVAL.json'),manifest_sha256=MANIFEST,bindings_sha256=BINDINGS,source_export_sha256=ARCHIVE,source_export_members=282,source_export_bytes=4413440,source=SOURCE,control=CONTROL,run=RUN,designated_ssd=volume,source_templates_unchanged=True)
    save('IDENTITIES.json',identity);print(json.dumps(identity,indent=2))
if __name__=='__main__':main()
