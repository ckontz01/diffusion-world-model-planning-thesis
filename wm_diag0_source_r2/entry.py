"""Only Reacher0 replacement and59 untouched roots, same manifest and bytes."""
import json,sys
from pathlib import Path
from wm_diag0_native_v3.common import identity,write_new

def main():
    contract=Path(sys.argv[1]);index=int(sys.argv[2]);task=Path(sys.argv[3]);c=json.loads(contract.read_text())
    if not c['source_generation_authorized'] or c['gpu_stage_authorized'] or not 60<=index<120:raise ValueError('exact finite source recovery scope')
    from stable_worldmodel.envs.pusht.env import PushT
    from stable_worldmodel.envs.dmcontrol.reacher import ReacherDMControlWrapper
    from wm_diag0_native_v3.runtime import verify_imports
    write_new(task/'controls/IMPORTED-RUNTIME-BEFORE.json',verify_imports(c,contract.parent))
    from wm_diag0_source_r2.writer import collect
    plan=json.loads((contract.parent/'ROOT-PLAN.json').read_text())
    if identity(contract.parent/'ROOT-PLAN.json')['sha256']!=c['root_plan_sha256']:raise ValueError('unchanged manifest')
    good=collect(plan['roots'][index],task/'output')
    if good and index==60:
        compared={}
        for name,row in c['source_recovery']['failed_partial'].items():
            original=Path(c['source_recovery']['partial_supplier'])/name
            if identity(original)!=row or identity(task/'output'/name)!=row:raise ValueError('same-seed technical replacement must match every preserved original array bit')
            compared[name]=row
        write_new(task/'controls/ORIGINAL-PARTIAL-BYTE-IDENTITY.json',{'all_four_original_arrays_bit_identical':True,'members':compared,'changed_science':False})
    write_new(task/'controls/IMPORTED-RUNTIME-AFTER.json',verify_imports(c,contract.parent))
    return 0 if good else 1

if __name__=='__main__':sys.exit(main())
