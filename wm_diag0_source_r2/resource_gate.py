"""Fail closed against original physical-work maxima, including failed work."""
from .common import ROOT
import json


def reservation(reconciliation):
    limits=json.loads((ROOT/'docs/world-model-diagnostic-a2-20261004/RESOURCE-PLAN.json').read_text())['counts']
    failed=reconciliation['failed_physical_work']
    # No unused future episodes, ragged banks, early stops or favorable outcomes
    # may be assumed in order to fund a technical replacement.
    extra={'collector_steps_max':failed['controller_actions'],
           'source_frames_max':45 if failed['controller_actions']==44 else None,
           'world_resets_max':failed['world_resets'],
           'all_controller_steps_max':failed['controller_actions'],
           'reacher_dm_steps_max':failed['Reacher_dm_steps']}
    if any(v is None for v in extra.values()):raise ValueError('unknown failed source-frame reservation')
    return {k:{'existing_max':limits[k],'charged_failed_plus_full_future':limits[k]+v,'excess':v}
            for k,v in extra.items()}


def require_within_original_limits(reconciliation):
    rows=reservation(reconciliation)
    if any(x['charged_failed_plus_full_future']>x['existing_max'] for x in rows.values()):
        raise RuntimeError('R2 NOT AUTHORIZED WITHIN EXISTING LIMITS: failed physical work plus full future exceeds original maxima; no stage or submission')
    return rows
