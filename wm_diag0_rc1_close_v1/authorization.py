import json
from pathlib import Path
from wm_diag0_rc1_grid_v1.common import identity
from wm_diag0_rc1_final_v1.usage import HISTORICAL_DINO,HISTORICAL_LEWM
def authorization(c,expected,contract,taskdir):
    final=c.get('rc1_final',{})
    if identity(contract)['sha256']!=expected or final.get('analysis_authorized') is not True or c['gpu_stages_authorized'] or Path(taskdir)!=Path(final.get('run',''))/'tasks/analysis-0':raise PermissionError('new frozen final CPU-only contract required')
    grid=Path(c['run'])/'source/GRID-CONTRACT.json'
    if identity(grid)!=final['grid_contract'] or c['run']!=final['grid_run']:raise ValueError('actual grid science/supplier contract retained')
    receipt=Path(final['historical_usage_receipt']['path'])
    if identity(receipt)!=final['historical_usage_receipt']['identity']:raise ValueError('historical invocation/source provenance not bound')
    h=json.loads(receipt.read_text())
    if h['DINO_baseline']!=HISTORICAL_DINO or h['LeWM_baseline']!=HISTORICAL_LEWM or h.get('independently_authenticated') is not True:raise ValueError('no invented historical instrumentation')
    return final
