"""Freeze reviewed preparation only; never enables or submits research."""
import common as c


def build_inputs():
    old=c.read(c.BASE/'RUNTIME-PINS.json');r=c.read(c.BASE/'DATA-ROLES-PROPOSED.json')
    previous=c.read(c.REPO/'docs/local-goal-source-replication-20260920/INPUTS.json')
    refs={}
    for key,value in r['records'].items():
        v=dict(value)
        v['file']=str(c.Path(previous['references']['74']['file']).parent / v['file']).replace('\\','/')
        refs[key]=v
    inspected=c.read(c.ROOT/'INSPECTED-SOURCES.json')
    files=dict(old['runtime_files'])
    for s in inspected:files[s['path']]=s['sha256']
    root=c.RESEARCH+'/snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0/official-sage/stable_worldmodel/wm/lewm/'
    return {'lewm':old['lewm'],'lewm_sha256':previous['files'][old['lewm']], 'container':old['container'],
            'runtime':old['runtime'],'runtime_files':files,'model_sources':{'lewm':root+'lewm.py','module':root+'module.py'},
            'references':refs,'roles_sha256':c.sha(c.BASE/'DATA-ROLES-PROPOSED.json'),
            'registry_path':r['registry_path'],'registry_sha256':r['registry_sha256'],
            'research_payload_reads_in_preparation':0,'model_shape':{'D':192,'x':996,'a':212,'r':192},
            'decoder':old['decoder'],'precision':'NumPy float64 CEM/cost; BF16 Le-WM; delivered native float32',
            'trained_binding':'New joint/ordinary/frozen Bayesian approximation; seal after final192 before final32'}


def freeze():
    c.write(c.ROOT/'INPUT-BINDINGS.json',build_inputs())
    c.write(c.ROOT/'GRID.json',c.grid())
    files={}
    accepted=['model.py','tree.py','policy.py','runtime_adapter.py','bayes.py','mock.py',
              'DATA-ROLES-PROPOSED.json','PILOT-PROPOSED.json','RUNTIME-PINS.json',
              'PILOT-PROTOCOL.md','TRAINING-AND-DECISION.md']
    paths=[c.BASE/n for n in accepted]+[c.REPO/'cluster/prometheus/pusht_fresh_initialization.py']
    paths += [p for p in c.ROOT.iterdir() if p.is_file() and p.name not in ('SOURCE-MANIFEST.json','APPROVAL-TEMPLATE.json','DELIVERY.json','ATTEMPTS.jsonl')]
    for p in paths:files[p.relative_to(c.REPO).as_posix()]=c.sha(p)
    c.write(c.ROOT/'SOURCE-MANIFEST.json',{'reviewed_base':'1c66038901fe39640add38aa796a816c06ccd1ae','files':files})
    h=c.sha(c.ROOT/'SOURCE-MANIFEST.json')
    c.write(c.ROOT/'APPROVAL-TEMPLATE.json',{'schema':'ACV0-execution-v1','authorized':False,'instruction':'',
            'package_sha256':h,'grid_sha256':c.digest(c.grid()),'roles_sha256':c.sha(c.BASE/'DATA-ROLES-PROPOSED.json'),
            'inputs_sha256':c.sha(c.ROOT/'INPUT-BINDINGS.json'),'run':c.RUN_PARENT+'/run-'+h[:16],
            'no_retry':True,'research_caps':c.caps()})
    print('DISABLED frozen package',h)


if __name__=='__main__':freeze()
