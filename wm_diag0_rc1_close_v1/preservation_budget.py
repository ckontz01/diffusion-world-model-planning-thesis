"""Complete byte proof with current actual auxiliary/artif reservations."""
from wm_diag0_rc1_final_v2.preservation_budget_v1 import prove as original,PORTABLE_LIMIT,SIDECAR_LIMIT
def prove(planned,roots,contract,preparation):
    result=original(planned,roots,contract,preparation)
    extra=17000000 #80MB+5MB rather than old64MB+4MB; no copy discounts
    for key in ('full_future_live_bytes','full_future_archive_bytes','full_future_inclusive_bytes'):result[key]+=extra
    if result['full_future_live_bytes']>13500000000 or result['full_future_archive_bytes']>14000000000 or result['full_future_inclusive_bytes']>44000000000:raise ValueError('full current storage proof')
    result['all_new_auxiliary_logical_copy_reservation_bytes']=80000000
    result['final_artificial_whole_root_reservation_bytes']=5000000
    result['earlier_auxiliary_subreservations_are_historical_not_current_authority']=True
    return result
