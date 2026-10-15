"""Independent selection/endpoint arithmetic within allocation; no model forward."""
import json,sys
from pathlib import Path
from .common import identity,write_new,SETTINGS,check_usage,canonical

def main():
    root=Path(sys.argv[1]);expected=sys.argv[2];setting=int(sys.argv[3]);cp=root/'source/TECHNICAL-CONTRACT.json';c=json.loads(cp.read_text())
    if identity(cp)['sha256']!=expected or setting not in (1,2,3):raise ValueError('exact setting contract')
    task=root/'tasks'/('technical-'+str(setting));w=json.loads((task/'controls/WORKER-SUCCESS.json').read_text())
    if w['phase']!='RC1_technical' or w['setting']!=setting:raise ValueError('worker setting')
    check_usage(setting,w['actual_usage'])
    name,backbone=SETTINGS[setting]
    from .suppliers import head
    directory,s=head(c,setting)
    from wm_diag0_native_v3.store import authenticate
    authenticate(task/'output',w['output_seal'],60000000)
    selected=json.loads((task/'output/SELECTION.json').read_text())
    plan=json.loads((root/'source/ROOT-PLAN.json').read_text());row=next(r for r in plan['roots'] if r['task']==name and r['root_index']==0)
    if selected['root']!=row or selected['backbone']!=backbone or not selected['technical'] or selected.get('RC1_retained_bank_continuation')!=(setting==1):raise ValueError('fixed root000/own backbone and reuse-only PushT')
    if backbone=='dinowm_noprop' and canonical(selected['route'])!=canonical(c['rc1_technical']['head_suppliers'][str(setting)]['route']):raise ValueError('amended active head route')
    source=Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json'
    if identity(source)!=c['source_acceptance']:raise ValueError('source acceptance')
    sources=json.loads(source.read_text());key=name+'-000'
    from .accept import accept
    result=accept(task/'output',w['output_seal'],task/'controls/SELECTION-EXTERNAL.json',Path(c['source_runs'][name])/'tasks'/key/'output',sources['source_seals'][key],directory,s,c,gpu=True)
    result={k:v for k,v in result.items() if k not in ('choices','outcomes','reasons','initial_success')}
    result.update(phase='RC1_technical',setting=setting,actual_usage=w['actual_usage'],readout_output_seal=s,contract_sha256=expected,scientific_values_emitted=False)
    write_new(task/'controls/ACCEPTED.json',result)
    print(json.dumps({'status':'RC1_NATIVE_SETTING_INDEPENDENTLY_ACCEPTED','setting':setting,'output_seal':w['output_seal']}))

if __name__=='__main__':main()
