from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[2]
ROOT=REPO/'docs/active-counterfactual-verification-20260923/preservation-r6';sys.path.insert(0,str(ROOT))
import archive6 as a
old=HERE.parent/'finalization-r5'
base=a.read(old/'ARCHIVE-FAULT-RECONCILIATION.json');assert base['returncode']==0
b=a.json.loads(base['stdout']);assert b['archive_directory_exists'] is False
a.write(ROOT/'BASELINE.json',b)
# Preserve the exact failed invocation stdout/stderr in the new frozen package.
a.write(ROOT/'R5-ARCHIVE-FAILURE.json',a.read(old/'ARCHIVE.json'))
contract={'schema':'ACV0-archive-only-r6-contract','baseline_sha256':a.sha(ROOT/'BASELINE.json'),
    'r5_source':b['r5_binding']['control_source'],'r5_control':b['r5_binding']['control'],
    'r5_rel':'docs/active-counterfactual-verification-20260923/finalization-r5','r5_manifest':b['r5_manifest'],
    'r5_approval_sha256':b['r5_approval_sha256'],'completion_sha256':b['completion_sha256'],
    'research_root':b['r5_binding']['research_root'],'authority_commit':'ace242ee5ea14af284401ad857fc3a49b30e1b58',
    'authority':'Direct user standing technical-recovery instruction; not new signature',
    'new_jobs':0,'reanalysis':0,'new_archive_invocations':1,'previous_failed_precreation_archive_invocations':1,
    'transfer_attempts':1,'automatic_retry':False,'source_control_models_analysis_cap':500000000,
    'live_cap':2000000000,'inclusive_cap':8000000000,'unchanged_science_and_caps':True}
a.write(ROOT/'CONTRACT.json',contract)
print('Exclusive R6 inputs prepared; science unchanged')
