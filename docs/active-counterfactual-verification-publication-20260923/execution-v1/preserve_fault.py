"""Preserve the received direction and prelaunch fault; never enable or launch."""
import json
import operate as o

if __name__=='__main__':
    raw=o.ATTACHMENT.read_bytes()
    assert __import__('hashlib').sha256(raw).hexdigest()=='e6f0a90b53f902bf7b65cacb39ca330043aa6cd5a2cb857b881375c61f30fe1f'
    with (o.HERE/'RECEIVED-EXECUTION-INSTRUCTION.txt').open('xb') as f:f.write(raw)
    reconciliation=o.read(o.HERE/'PRELAUNCH-RECONCILIATION.json');assert reconciliation['returncode']==0
    remote=json.loads(reconciliation['stdout'])
    assert not any(remote['path_exists'].values()) and not remote['active_acv0b1_rows'] and not remote['accounted_acv0b1_rows']
    assert o.read(o.PACKAGE/'APPROVAL-TEMPLATE.json')['authorized'] is False
    assert not (o.HERE/'EXECUTION-APPROVAL.json').exists()
    for name,h in o.read(o.PACKAGE/'SOURCE-MANIFEST.json')['files'].items():assert o.sha(o.REPO/name)==h,name
    o.write(o.HERE/'FAULT.json',{
        'status':'PRELAUNCH_STOP_NO_RESEARCH_ALLOCATION',
        'authorization_provenance':'Explicit execution direction supplied here under standing user delegation, not a newly obtained direct user signature',
        'instruction_sha256':o.sha(o.HERE/'RECEIVED-EXECUTION-INSTRUCTION.txt'),
        'approved_implementation':'3b2db69e563af89b1ced2149b11c11a1999ba4df',
        'approved_receipt':'b27605ccf7e9097beb02e3d0d638d3e31a175121','source_manifest':o.MANIFEST_SHA,
        'fault':'New local launch-operation helper placed the entire input-binding JSON in a Windows command-line argument. Windows CreateProcess rejected its length (error206) before WSL/SSH started.',
        'attribution':'Operational helper introduced during this launch task, outside the approved scientific closure; not an experiment or cluster failure',
        'local_archive_members_authenticated':40,'remote_runtime_authentication_completed':False,
        'enabled_approval_created':False,'source_control_run_absent':True,'controller_started':False,
        'submitted_jobs':0,'live_jobs':0,'terminal_jobs':0,'ambiguous_submissions':0,
        'gpu_allocation_seconds':0,'cpu_job_allocation_seconds':0,'research_reference_reads':0,
        'research_checkpoint_loads':0,'simulator_episodes':0,'tranche_status':'NOT_STARTED',
        'scientific_source_unchanged':True,'false_template_preserved':True,'automatic_retry':False,
        'namespace_reconciliation':remote,
        'proposed_scoped_recovery':'Authorize a launch-transport-only correction sending bounded JSON/code through SSH stdin, then complete one authenticated staging and one campaign launch in the SAME absent exclusive paths. No source changes, test allocations, dependency changes, research retries or cap changes.'})
    print('Fault, exact instruction and zero-allocation reconciliation preserved; no approval enabled.')
