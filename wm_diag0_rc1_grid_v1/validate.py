"""Original independent parent acceptance, mixed active head suppliers."""
import json,sys
from pathlib import Path
from .common import identity,write_new,SETTINGS,setting,check_usage,gates,canonical

def main():
    root=Path(sys.argv[1]);expected=sys.argv[2];index=int(sys.argv[3]);s,ri=setting(index);task=root/'tasks'/('grid-'+str(index));cp=root/'source/GRID-CONTRACT.json';c=json.loads(cp.read_text())
    if identity(cp)['sha256']!=expected:raise ValueError('exact grid contract')
    gates(c);w=json.loads((task/'controls/WORKER-SUCCESS.json').read_text())
    if (w['phase'],w['index'],w['setting'],w['root_index'])!=('RC1_grid',index,s,ri):raise ValueError('worker exact grid/root binding')
    check_usage(index,w['actual_usage'])
    from wm_diag0_native_v3.store import authenticate
    authenticate(task/'output',w['output_seal'],60000000)
    selected=json.loads((task/'output/SELECTION.json').read_text());name,backbone=SETTINGS[s]
    row=next(r for r in json.loads((root/'source/ROOT-PLAN.json').read_text())['roots'] if r['task']==name and r['root_index']==ri)
    if selected['root']!=row or selected['backbone']!=backbone or selected['technical'] or selected.get('RC1_retained_bank_continuation'):raise ValueError('ordinary non-reused fixed grid parent')
    if backbone=='dinowm_noprop' and canonical(selected['route'])!=canonical(c['rc1_technical']['head_suppliers'][str(s)]['route']):raise ValueError('own amended DINO route')
    from wm_diag0_rc1_technical_v1.suppliers import head
    hd,hs=head(c,s);sa=Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json'
    if identity(sa)!=c['source_acceptance']:raise ValueError('accepted source authority')
    sources=json.loads(sa.read_text());key=name+'-'+str(ri).zfill(3)
    from wm_diag0_campaign_v4.accept import accept
    result=accept(task/'output',w['output_seal'],task/'controls/SELECTION-EXTERNAL.json',Path(c['source_runs'][name])/'tasks'/key/'output',sources['source_seals'][key],hd,hs,c,gpu=True)
    result={k:v for k,v in result.items() if k not in ('choices','outcomes','reasons','initial_success')}
    result.update(phase='RC1_grid',index=index,setting=s,root_index=ri,actual_usage=w['actual_usage'],readout_output_seal=hs,contract_sha256=expected,scientific_values_emitted=False)
    write_new(task/'controls/ACCEPTED.json',result);print(json.dumps({'status':'FIXED_RC1_PARENT_INDEPENDENTLY_ACCEPTED','index':index,'output_seal':w['output_seal']}))

if __name__=='__main__':main()
