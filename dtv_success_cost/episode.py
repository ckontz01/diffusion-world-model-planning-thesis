"""Matched closed loop and independent native endpoint/action reconstruction.

No simulator or model imports in this module. Real and artificial adapters use
the same loop. Audit and serialization are outside the operational intervals.
"""
import math
import time

def success(task, evidence):
    current=evidence['current']; target=evidence['target']
    if not all(math.isfinite(float(x)) for x in current+target): raise ValueError('nonfinite endpoint')
    if task=='pusht':
        delta=abs(current[4]-target[4]);delta=min(delta,2*math.pi-delta)
        return sum((a-b)**2 for a,b in zip(current[:4],target[:4]))**.5<20 and delta<math.pi/9
    if task=='reacher':return len(current)==len(target)==2 and all(abs(a-b)<.05 for a,b in zip(current,target))
    if task=='cube':return len(current)==len(target)==3 and sum((a-b)**2 for a,b in zip(current,target))**.5<=.04
    raise ValueError('unknown task')

def run_episode(adapter, config, check=lambda:None, clock=time.perf_counter, journal=lambda r:None):
    rows=[]; plans=[]; times=[]; audit=0.; op=0.; planning=0.; cpu=time.process_time(); start=clock()
    adapter.sync(); t=clock();adapter.reset();adapter.sync();reset_seconds=clock()-t
    t=clock();initial=adapter.evidence();audit+=clock()-t
    initial_success=success(adapter.task,initial)
    if adapter.native_success()!=initial_success:raise RuntimeError('initial native endpoint disagreement')
    t=clock();journal(dict(event='initial',endpoint=initial,initial_success=initial_success));audit+=clock()-t
    outcome=initial_success; reason='initial_success' if outcome else 'action_budget'
    for step in range(50 if not outcome else 0):
        check();decision=step%25==0
        adapter.sync();t=clock();action, plan=adapter.action();adapter.sync();latency=clock()-t
        planning+=latency;op+=latency
        if decision!=(plan is not None):raise RuntimeError('planning cadence changed')
        t=clock();converted=adapter.plan_list(plan) if plan is not None and hasattr(adapter,'plan_list') else plan
        delivered=adapter.action_list(action)
        journal(dict(event='action_intent',step=step,action=delivered,plan=converted));audit+=clock()-t
        adapter.sync();t=clock();terminated,truncated=adapter.step(action);adapter.sync();environment=clock()-t;op+=environment
        t=clock();evidence=adapter.evidence();native=adapter.native_success();found=success(adapter.task,evidence)
        if native!=found:raise RuntimeError('native success and independent endpoint differ')
        if plan is not None:
            plans.append(dict(step=step,**converted))
        rows.append(dict(step=step,action=delivered,endpoint=evidence,terminated=bool(terminated),truncated=bool(truncated),success=found))
        times.append(dict(step=step,planning_decision=decision,observation_to_action_seconds=latency,environment_seconds=environment))
        journal(dict(event='transition',row=rows[-1],timing=times[-1]))
        audit+=clock()-t
        if found or terminated or truncated:
            outcome=found;reason='native_success' if found else ('terminated' if terminated else 'truncated');break
    whole=clock()-start
    return dict(config=config,task=adapter.task,initial=initial,initial_success=initial_success,success=outcome,termination=reason,
                actions=rows,plans=plans,timings=times,planning_seconds=planning,reset_seconds=reset_seconds,
                episode_operational_seconds=reset_seconds+op,episode_elapsed_including_audit_seconds=whole,audit_seconds=audit,
                process_cpu_seconds=time.process_time()-cpu,decoder=adapter.decoder(),resources=adapter.resources())

def verify_episode(e):
    task=e['task']; initial=success(task,e['initial'])
    if initial!=e['initial_success']:raise RuntimeError('initial endpoint altered')
    rows=e['actions'];plans=e['plans'];times=e['timings'];config=e['config'];rounds=int(config[-2:])
    if rounds not in (28,30) or config[:-2] not in ('dtv','acid','forward','plain'):raise RuntimeError('configuration identity')
    if len(rows)>50 or len(rows)!=len(times) or [r['step'] for r in rows]!=list(range(len(rows))):raise RuntimeError('physical budget/trace changed')
    expected_steps=[i for i in range(len(rows)) if i%25==0]
    if [p['step'] for p in plans]!=expected_steps:raise RuntimeError('planning cadence')
    if initial and rows:raise RuntimeError('post-initial-terminal work')
    for p in plans:
        if p['populations']!=rounds or p['candidates']!=rounds*300 or p['return_rule']!='final_elite_mean':raise RuntimeError('solver counts/return changed')
        if len(p['normalized_actions'])!=25:raise RuntimeError('five groups of five actions required')
        mean=e['decoder']['mean'];scale=e['decoder']['scale']
        if len(mean)!=len(scale) or any(not math.isfinite(float(v)) for v in mean+scale):raise RuntimeError('decoder identity/precision invalid')
        for i,a in enumerate(p['normalized_actions']):
            if len(a)!=len(mean) or any(not math.isfinite(float(v)) for v in a):raise RuntimeError('action support/precision invalid')
            physical=p['step']+i
            if physical>=len(rows):break
            if e['decoder'].get('precision')=='float32_inplace_multiply_then_add':
                import struct
                f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
                expected=[f32(f32(float(v*s))+m) for v,m,s in zip(a,mean,scale)]
            else:expected=[float(v*s+m) for v,m,s in zip(a,mean,scale)]
            actual=rows[physical]['action']
            if any(not math.isfinite(float(v)) for v in actual):raise RuntimeError('nonfinite delivered action')
            if len(actual)!=len(expected) or any(abs(v-w)>1e-6*max(1,abs(v),abs(w)) for v,w in zip(expected,actual)):raise RuntimeError('delivered action differs from decoded plan')
    for i,r in enumerate(rows):
        found=success(task,r['endpoint'])
        if found!=r['success'] or r['endpoint']['target']!=e['initial']['target']:raise RuntimeError('endpoint/goal changed')
        if i+1<len(rows) and (found or r['terminated'] or r['truncated']):raise RuntimeError('post-terminal physics/planning')
    final=initial if not rows else rows[-1]['success']
    if bool(final)!=e['success']:raise RuntimeError('trace-to-success disagreement')
    reason='initial_success' if initial else 'action_budget'
    if rows and (final or rows[-1]['terminated'] or rows[-1]['truncated']):
        reason='native_success' if final else ('terminated' if rows[-1]['terminated'] else 'truncated')
    if e['termination']!=reason or (not initial and len(rows)<50 and reason=='action_budget'):raise RuntimeError('premature stopping')
    for i,t in enumerate(times):
        if t['step']!=i or t['planning_decision']!=(i%25==0):raise RuntimeError('timing trace identity')
        if any(not math.isfinite(t[k]) or t[k]<0 for k in ('observation_to_action_seconds','environment_seconds')):raise RuntimeError('timing invalid')
    total=sum(t['observation_to_action_seconds'] for t in times)
    if abs(total-e['planning_seconds'])>1e-8:raise RuntimeError('complete planning boundary')
    if abs(e['episode_operational_seconds']-e['reset_seconds']-total-sum(t['environment_seconds'] for t in times))>1e-8:raise RuntimeError('episode boundary')
    return dict(actions=len(rows),decisions=len(plans),endpoint_checks=len(rows)+1,populations=sum(p['populations'] for p in plans))
