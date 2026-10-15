"""Allocated independent acceptance subprocess; prints technical metadata only."""
import json,sys
from pathlib import Path
from .common import identity,write_new,SETTINGS

def main():
    path=Path(sys.argv[1]);phase=sys.argv[2];index=int(sys.argv[3]);taskdir=Path(sys.argv[4]);c=json.loads(path.read_text())
    success=json.loads((taskdir/'controls/WORKER-SUCCESS.json').read_text())
    if success['phase']!=phase or success['index']!=index:raise ValueError('worker task identity')
    seal=success['output_seal']
    if phase=='readout':
        from .accept_readout import accept
        result=accept(taskdir/'output',seal,c,index)
    else:
        setting=index if phase=='technical' else index//31
        source_index=0 if phase=='technical' else 1+index%31
        task,backbone=SETTINGS[setting]
        key=task+'-'+str(source_index).zfill(3)
        sources=json.loads((Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json').read_text())
        readout=Path(c['run'])/'tasks'/('readout-'+str(setting))
        head=json.loads((readout/'controls/ACCEPTED.json').read_text())
        from .accept import accept
        result=accept(taskdir/'output',seal,taskdir/'controls/SELECTION-EXTERNAL.json',Path(c['source_run'])/'tasks'/key/'output',
                      sources['source_seals'][key],readout/'output',head['output_seal'],c,gpu=True)
        # No scientific choices or outcomes are emitted into public controls.
        result={k:v for k,v in result.items() if k not in ('choices','outcomes','reasons','initial_success')}
    result.update(output_seal=seal,phase=phase,index=index,accepted=True)
    write_new(taskdir/'controls/ACCEPTED.json',result)
    print(json.dumps({'status':'NATIVE_TASK_INDEPENDENTLY_ACCEPTED','phase':phase,'index':index,'output_seal':seal}))

if __name__=='__main__':main()
