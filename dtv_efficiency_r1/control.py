"""Strict binding overlay; scientific/input fields are inherited byte-exact."""
import copy,json
from pathlib import Path
from dtv_efficiency.profile import sha

ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs/dtv-efficiency-correction-r1-20260930'
ORIGINAL_DOC=ROOT/'docs/dtv-efficiency-20260930'
WORK_SECONDS=720
PRESERVATION_SECONDS=60
WORKER_SECONDS=780
GRID_RESERVATION_SECONDS=7020
AGGREGATE_SECONDS=7200

def load_bindings(path=DOC/'BINDINGS.json'):
    overlay=json.loads(Path(path).read_text())
    base=ROOT/overlay['reviewed_bindings_path']
    if base.resolve()!=ORIGINAL_DOC/'BINDINGS.json' or sha(base)!=overlay['reviewed_bindings_sha256']:
        raise RuntimeError('reviewed scientific bindings changed')
    expected=dict(work_deadline_seconds=WORK_SECONDS,preservation_allowance_seconds=PRESERVATION_SECONDS,worker_wall_seconds=WORKER_SECONDS,grid_reservation_seconds=GRID_RESERVATION_SECONDS,gpu_allocation_seconds_cap=AGGREGATE_SECONDS)
    if overlay.get('control')!=expected or overlay.get('execute') is not False:
        raise RuntimeError('corrected finite contract differs')
    result=copy.deepcopy(json.loads(base.read_text()))
    for job in result['jobs']:job['wall_limit_seconds']=WORKER_SECONDS
    result.update(expected)
    result['execute']=False
    if len(result['jobs'])!=9 or sum(j['wall_limit_seconds'] for j in result['jobs'])!=GRID_RESERVATION_SECONDS:
        raise RuntimeError('nine-worker reservation mismatch')
    return result
