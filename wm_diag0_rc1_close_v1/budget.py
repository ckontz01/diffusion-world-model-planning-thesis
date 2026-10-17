"""Human-authorized shared engineering allocation; immutable old receipts stay."""
import json,time
from wm_diag0_rc1_completion_v1.common import ROOT,DOC,raw_json,write_new,identity,owned_bytes,charge,charges,authority,legacy_unchanged,utc_seconds
AUTH=ROOT/'docs/world-model-diagnostic-rc1-final-close-v1-20261017/AUTHORITY-002.json'
# These are per-operation-category ceilings on the SAME shared21600 envelope,
# NOT additive grants. Actual history is never moved, refunded or rewritten.
CAPS={k:21600 for k in ('implementation','cluster_validation','binding_staging','publication','monitoring','native_SSD','technical_fault','handoff')}

def reserve(component,seconds,now):
    a,v=authority();legacy_unchanged(v);rows=charges();grant=json.loads(AUTH.read_text())
    if grant.get('supersedes_agent_designed_engineering_component_partitions_and_auxiliary_subcaps_as_approval_barriers') is not True:raise PermissionError('direct human finalization authority required')
    if component not in CAPS or type(seconds) is not int or not 5<=seconds<=7200:raise ValueError('finite owned operation')
    if sum(charge(z) for z in rows)+seconds>21600 or now+seconds>utc_seconds(v['stop_utc']):raise ValueError('shared outer engineering envelope/horizon')
    if component=='monitoring' and (seconds>30 or sum(z['component']=='monitoring' for z in rows)>=240):raise ValueError('bounded monitor only')
    return a,v,rows
