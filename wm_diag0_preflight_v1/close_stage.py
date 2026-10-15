"""Compact public acceptance; raw site epilog stays in local/SSD evidence only."""
import json
import os
from pathlib import Path
from wm_diag0_preflight_v1.common import ROOT,DOC,identity,write_new
from wm_diag0_preflight_v1.preserve import volume

def main():
    raw_path=DOC/'stage-recovery-r1/OBSERVATION-001.json'
    r=json.loads(raw_path.read_text()); reviewed=r['parent_review']
    if not reviewed['accepted'] or r['job_id']!='316960': raise ValueError('exact accepted CPU task')
    output={n:{'bytes':v['bytes'],'sha256':v['sha256']} for n,v in r['output'].items()}
    model_counts={}
    for n,v in r['output'].items():
        if n.startswith('dino-'):
            model_counts[n]={'required_masks':len(v['data']['required_masks']),
                             'tensor_counts':{k:len(s['tensors']) for k,s in v['data']['objects'].items()}}
        elif n in ('encoder.json','lewm-pusht.json','lewm-reacher.json'):
            model_counts[n]={'tensors':len(v['data']['tensors']),'modules':len(v['data']['modules'])}
    local_rows=[json.loads(p.read_text()) for p in DOC.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    result={'study':'WM-DIAG0-A2','status':'CPU_PREFLIGHT_INDEPENDENTLY_ACCEPTED_NOT_CAMPAIGN_LAUNCH',
            'job_id':'316960','scheduler':r['sacct']['stdout'].strip(),'stage':reviewed,
            'source_commit':'04969e38ab070dd5e88f53d23fd60063956d208f',
            'transport_recovery_source_commit':'bc24a6a60598c220b544bcf0147db03f89b7cd80',
            'contract':identity(DOC/'stage-recovery-r1/CONTRACT.json'),
            'output_members':output,'module_metadata_counts':model_counts,'runtime':r['output']['runtime.json']['data'],
            'supervisor':r['controls']['ALLOCATION-RESULT.json']['data'],
            'log_identities':{n:{k:v[k] for k in ('bytes','sha256')} for n,v in r['logs'].items()},
            'raw_observation_identity':identity(raw_path),
            'privacy':'Unrelated site-account epilog is retained in raw local/SSD evidence but omitted from publication.',
            'local_measured_script_seconds_before_close':sum(x['elapsed_seconds'] for x in local_rows),
            'full_preparation_charge_seconds':1680,'cumulative_preparation_seconds':12104.10301460012,
            'remaining_preparation_seconds':2295.89698539988,
            'all_failure_inclusive_live_reservation':12536395242,'live_cap':13000000000,
            'archive_cap':14000000000,'inclusive_cap':44000000000,
            'research_forwards':0,'simulators_instantiated':0,'source_roots_generated':0,'fit_operations':0,'gpu_allocations':0,
            'native_source_comparison':identity(DOC/'NATIVE-SOURCE-COMPARISON-001.json'),
            'next_stage':'Implement and authenticate fixed native collection/replay, assets/rendering and model/selection/evaluation adapters; then fixed120 source attempts, four readouts, included first-four diagnostic parity tranche, remaining grid and full acceptance/preservation. No VM/admin approval required.'}
    write_new(DOC/'ACCEPTED-001.json',result)
    v=volume(); dest=Path('D:/THESIS-BACKUPS/world-model-diagnostic-a2-preflight-v1-20261015/accepted-stage')
    dest.mkdir(exist_ok=False); rows={}
    selected=[DOC/'ACCEPTED-001.json',DOC/'NATIVE-SOURCE-COMPARISON-001.json',DOC/'LOCAL-SOURCECOMPARE001.json',
              ROOT/'wm_diag0_preflight_v1/source_compare.py',ROOT/'wm_diag0_preflight_v1/close_stage.py']
    for p in selected:
        target=dest/p.name
        with target.open('xb') as f: f.write(p.read_bytes()); f.flush(); os.fsync(f.fileno())
        if identity(p)!=identity(target): raise ValueError('new member backup identity')
        rows[p.relative_to(ROOT).as_posix()]=identity(p)
    receipt={'status':'WHOLE_AND_EVERY_NEW_MEMBER_VERIFIED','members':rows,'volume':v,'old_archives_rebuilt':0,'weights_copied':0}
    write_new(DOC/'ACCEPTED-SSD-001.json',receipt); write_new(dest/'ACCEPTED-SSD-001.json',receipt)
    if identity(DOC/'ACCEPTED-SSD-001.json')!=identity(dest/'ACCEPTED-SSD-001.json'): raise ValueError('receipt identity')
    print(json.dumps({'status':result['status'],'job_id':result['job_id'],'cpu_seconds':17,'model_metadata_counts':model_counts,'next':result['next_stage']},indent=2))

if __name__=='__main__': main()
