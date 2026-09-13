"""Fail-closed prerequisites; no prospective reference/model payload access."""
import json
import sys
from pathlib import Path
from diffusion_bottleneck import require,require_sha

def check(src,audit):
    backup=json.loads((src/'docs/bottleneck/receipts/ARCHIVE-BACKUP-VERIFIED.json').read_text())
    require(backup['all_passed'] is True and backup['source_matched_shards']==450,'Incomplete off-cluster backup')
    require(backup['archive_sha256']=='d02d918017b9f9903b2b4a4bf6522e64776c6580f604ee5782f5d5beaec65e0b','Wrong backup archive')
    require(backup['canonical_receipt_sha256']=='0c406ca98e051d0f5aa9d8d701f5bc6bc299d67b38906bb2c6bbc39e6d5362ee','Wrong canonical receipt')
    entries={}
    for line in (audit/'sha256.txt').read_text().splitlines():
        digest,name=line.split(maxsplit=1);p=Path(name)
        require(p.parent==audit and p.name not in entries,'Unexpected audit seal path')
        require_sha(p,digest);entries[p.name]=digest
    require({'EXECUTION.json','traces.json','paired.json','paired-independent.json','canonical.json'}<=set(entries),'Incomplete audit')
    execution=json.loads((audit/'EXECUTION.json').read_text())
    require(execution['all_passed'] is True and all(x['returncode']==0 for x in execution['stages']),'Audit failed')
    trace=json.loads((audit/'traces.json').read_text())
    require(trace['raw_trajectories_read']==57600 and trace['verified_shards']==450,'Incomplete reduction')
    require(trace['technical_invalid_records']==0 and trace['independent_scalar_predicate_checked'] is True,'Reduction invalid')
    require(trace['reference_requests_and_planner_seeds_checked'] is True,'Missing identity checks')
    require(trace['historical_decision_unchanged']=='stop_futility_strong_adverse_signal','Historical change')
    require(trace['unevaluated_reference_payloads_read']==0 and trace['model_runs']==0,'Forbidden read or execution')
    print(json.dumps({'prerequisites_passed':True,'trace_sha256':entries['traces.json'],
                      'backup_archive_sha256':backup['archive_sha256']}),flush=True)

if __name__=='__main__':check(*(Path(x) for x in sys.argv[1:]))
