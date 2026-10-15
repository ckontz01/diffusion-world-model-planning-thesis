"""Allocated source-stage entry point; scientific model stages use later gate."""
import json,sys
from pathlib import Path
from .common import identity,write_new

def main():
    contract=Path(sys.argv[1]); index=int(sys.argv[2]); task=Path(sys.argv[3]); c=json.loads(contract.read_text())
    if not c['source_generation_authorized'] or c['gpu_stage_authorized']: raise ValueError('source-only finite stage')
    from .world import NativeWorld
    from .runtime import verify_imports
    # Import the exact reviewed constructors and both renderer stacks before
    # opening the first root. No reset, model, or physical step is done here.
    from stable_worldmodel.envs.pusht.env import PushT
    from stable_worldmodel.envs.dmcontrol.reacher import ReacherDMControlWrapper
    checked=verify_imports(c,contract.parent)
    write_new(task/'controls/IMPORTED-RUNTIME-BEFORE.json',checked)
    from .source import collect
    plan=json.loads((contract.parent/'ROOT-PLAN.json').read_text())
    if identity(contract.parent/'ROOT-PLAN.json')['sha256']!=c['root_plan_sha256']: raise ValueError('root plan identity')
    good=collect(plan['roots'][index],task/'output')
    checked=verify_imports(c,contract.parent)
    write_new(task/'controls/IMPORTED-RUNTIME-AFTER.json',checked)
    return 0 if good else 1

if __name__=='__main__': sys.exit(main())
