import json
from .common import DOC,write_new
from wm_diag0_native_v3.transport import ssh

def main():
    result=ssh('''import json,subprocess
a=subprocess.run(['sinfo','-N','-h','-n','gpu09','-o','%N|%P|%G|%c|%m|%T'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
b=subprocess.run(['sbatch','--help'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
print(json.dumps({'gpu09':a.stdout,'sinfo_returncode':a.returncode,'stderr':a.stderr,'dependency_supported':'--dependency' in b.stdout,'invalid_dependency_cancellation_supported':'--kill-on-invalid-dep' in b.stdout,'slurm_help_returncode':b.returncode,'new_jobs':0}))
''')
    write_new(DOC/'SCHEDULER-CAPABILITY-001.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
