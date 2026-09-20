"""Future approved detached controller launcher. Disabled templates cannot run."""
import argparse,os,subprocess,time
from pathlib import Path
import lgprb2_contract as c

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--approval',type=Path,required=True);a=p.parse_args()
    approval,_=c.authorize(a.source,a.approval)
    run=c.ROOT/'experiments'/c.NAME/('run-'+approval['source_sha256'][:16]);control=c.control_path(run)
    c.require(not run.parent.exists() and not control.exists(),'Prior launch/claim: no automatic restart')
    c.verify_models(a.source);control.mkdir(parents=True,exist_ok=False)
    c.write(control/'EXECUTION-APPROVAL.json',approval)
    command=['/usr/bin/python3.9','-B',str(a.source/'cluster/prometheus/lgprb2_dispatch.py'),
        '--source',str(a.source),'--approval',str(control/'EXECUTION-APPROVAL.json'),'--run',str(run)]
    c.write(control/'LAUNCH-INTENT.json',dict(command=command,unix=time.time(),exclusive=True))
    with (control/'controller.out').open('xb') as out,(control/'controller.err').open('xb') as err:
        proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
    stat=Path('/proc',str(proc.pid),'stat')
    c.require(stat.exists(),'Controller exited during launch; preserve control, do not relaunch')
    c.write(control/'CONTROLLER-PROCESS.json',dict(pid=proc.pid,start_ticks=stat.read_text().rsplit(')',1)[1].split()[19],unix=time.time(),command=command))
    print(str(control))

if __name__=='__main__':main()
