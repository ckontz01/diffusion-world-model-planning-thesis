"""Standard-library-only model-freeze boundary; no numerical/runtime imports."""
from pathlib import Path
import breadth_precision_contract as p
import candidate_value_contract as ct

CONFIGS=tuple(condition+'_'+objective for condition in ('A','B','C') for objective in ('bce','relative'))
METRICS_SHA='d54f2826a82af210d4148486f4a465e247f63ac7a8b8df54aa57cac839d166c5'


def check_frozen(run,source_sha):
    directory=Path(run)/'fit-0';r=ct.verify_seal(directory)
    p.require(r['models_frozen'] is True and r['new_source_sha256']==source_sha,'Frozen full model stage')
    freeze=ct.json_read(directory/'PRE-EVALUATION-FREEZE.json')
    p.require(freeze['fitted_models']==18 and freeze['configs']==list(CONFIGS) and not freeze['evaluation_outcomes_opened'], 'Pre-evaluation barrier')
    for name,digest in freeze['members'].items():p.require(p.sha(ct.child(directory,name))==digest,'Frozen member')
    return freeze
