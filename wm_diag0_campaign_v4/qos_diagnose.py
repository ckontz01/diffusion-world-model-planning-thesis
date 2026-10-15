"""Read-only current-user scheduler route metadata; no permission changes."""
import json
from .common import DOC,write_new
from wm_diag0_native_v3.transport import ssh

def main():
    r=ssh('''import json,os,pwd,subprocess
user=pwd.getpwuid(os.getuid()).pw_name
def run(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=15)
 return {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
print(json.dumps({'user':user,'partition':run(['scontrol','show','partition','a6000']),
 'own_associations':run(['sacctmgr','-n','-P','show','assoc','where','user='+user,'format=User,Account,Partition,QOS,DefaultQOS']),
 'configured_submission_environment':{k:os.environ.get(k) for k in ('SBATCH_QOS','SBATCH_ACCOUNT','SBATCH_PARTITION')},'changes_made':0}))
''')
    write_new(DOC/'campaign/QOS-DIAGNOSIS-001.json',r);print(json.dumps(r,indent=2))

if __name__=='__main__':main()
