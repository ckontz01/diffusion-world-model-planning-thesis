"""All original 139 allocated successes and failures; no scheduler/query entry."""
from wm_diag0_rc1_final_v2.recovery_suppliers_v1 import terminal_ledger
def reconcile(c,body):
    return terminal_ledger(c,body['scheduler'],body['old_grid_raw_ids'],body['recovery_grid_raw_ids'])
