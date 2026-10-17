"""Strict failure-inclusive GPU reconciliation, independent of scientific values."""
OLD_ALLOCATED={
 '317163_0':('317167','COMPLETED','0:0',27), '317163_1':('317168','COMPLETED','0:0',20),
 '317163_2':('317169','COMPLETED','0:0',27), '317163_3':('317163','COMPLETED','0:0',20),
 '317164_0':('317170','COMPLETED','0:0',65), '317164_1':('317171','FAILED','125:0',77),
 '317172':('317172','COMPLETED','0:0',13), '317173':('317173','COMPLETED','0:0',19),
 '317174':('317174','COMPLETED','0:0',19), '317175_1':('317176','COMPLETED','0:0',22),
 '317175_3':('317175','COMPLETED','0:0',22)}
OLD_UNALLOCATED={'317166','317164_[2-3%1]','317165_[0-123%1]'}


def reconcile(raw,grid_dispatch,technical_raw_ids,grid_raw_ids):
    """One consolidated scheduler readback; exact raw IDs bound from STARTEDs.

    The cancelled, never-allocated historical placeholders remain represented,
    but consume zero allocations. No live/pending/ambiguous row is discounted.
    """
    if not grid_dispatch.isdigit() or set(technical_raw_ids)!={1,2,3} or set(grid_raw_ids)!=set(range(124)):raise ValueError('exact actual dispatch/raw-ID bindings')
    expected=dict(OLD_ALLOCATED)
    for i in (1,2,3):expected['317177_'+str(i)]=(technical_raw_ids[i],'COMPLETED','0:0',None)
    for i in range(124):expected[grid_dispatch+'_'+str(i)]=(grid_raw_ids[i],'COMPLETED','0:0',None)
    found={};charge=0;allocated=0;raw_seen=set()
    for line in raw.splitlines():
        if not line.strip():continue
        row=line.split('|')
        if len(row)!=7:raise ValueError('exact scheduler columns')
        logical,actual,state,exitcode,seconds,cpus,node=row
        if logical in found or not actual.isdigit() or cpus!='4' or not seconds.isdigit():raise ValueError('duplicate/invalid scheduler identity')
        found[logical]=row;elapsed=int(seconds)
        if logical in OLD_UNALLOCATED:
            if not state.startswith('CANCELLED') or elapsed!=0 or node!='None assigned':raise ValueError('historical unallocated placeholder changed')
            continue
        if logical not in expected:raise ValueError('unexpected allocation must be reconciled, never omitted')
        eraw,estate,eexit,etime=expected[logical]
        if actual!=eraw or state!=estate or exitcode!=eexit or node not in ('gpu09','gpu09.cluster') or actual in raw_seen:raise ValueError('terminal exact allocated attempt')
        if not 0<elapsed<=3600 or (etime is not None and elapsed!=etime):raise ValueError('actual elapsed charge and unchanged history')
        raw_seen.add(actual);charge+=elapsed;allocated+=1
    if set(found)!=set(expected)|OLD_UNALLOCATED or allocated!=138 or charge>468000:raise ValueError('all138 attempts/failures/full cumulative cap')
    return {'status':'ALL138_ALLOCATED_GPU_ATTEMPTS_RECONCILED_INCLUDING_FAILURES','GPU_charged_seconds':charge,
        'allocated_attempts':allocated,'historical_unallocated_cancelled_placeholders':sorted(OLD_UNALLOCATED),
        'CPU_charged_before_analysis':1436,'analysis_reserved_seconds':3600,'unused_conversion_reserved_seconds':1800,
        'CPU_full_future_seconds':6836,'GPU_cap':468000,'CPU_cap':13800,'all_scheduler_rows':found}
