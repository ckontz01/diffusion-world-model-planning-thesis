"""Authenticate existing WSL software-rendering closure before any transfer."""
import json,subprocess
from .common import DOC,write_new
from wm_diag0_preflight_v1.common import SIF,VENV
from wm_diag0_preflight_v1.transport import ssh

def main():
    script='''import hashlib,json,os,re,subprocess
root='/usr/lib/x86_64-linux-gnu/libOSMesa.so.8.0.0'
text=subprocess.check_output(['ldd',root],universal_newlines=True)
paths=[root]
for line in text.splitlines():
 m=re.search(r'=> (/[^ ]+)',line)
 if m: paths.append(os.path.realpath(m.group(1)))
skip=('libc.so.','libm.so.','libdl.so.','librt.so.','libpthread.so.','ld-linux')
rows={}
for p in sorted(set(paths)):
 if os.path.basename(p).startswith(skip): continue
 data=open(p,'rb').read()
 versions=subprocess.check_output(['readelf','--version-info',p],universal_newlines=True)
 required=sorted(set(re.findall(r'Name: (GLIBC_[0-9.]+)',versions)))
 rows[os.path.basename(p)]={'path':p,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'glibc_versions':required}
print(json.dumps({'os_release':open('/etc/os-release').read(),'ldd':text,'members':rows,'total_bytes':sum(r['bytes'] for r in rows.values()),'new_downloads':0}))'''
    p=subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout','35s','python3','-B','-c',script],capture_output=True,text=True,timeout=40)
    if p.returncode: raise RuntimeError(p.stderr)
    row=json.loads(p.stdout)
    write_new(DOC/'RENDER-WSL-MANIFEST-001.json',row)
    script2="import json,platform; print(json.dumps({'os_release':open('/etc/os-release').read(),'libc':platform.libc_ver()}))"
    code='SIF='+repr(SIF)+'\nVENV='+repr(VENV)+'\nSCRIPT='+repr(script2)+'\n'+'''
import subprocess,json
p=subprocess.run(['apptainer','exec','--containall','--cleanenv','--no-home','--bind',VENV+':'+VENV+':ro',SIF,VENV+'/bin/python','-B','-c',SCRIPT],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=25)
print(json.dumps({'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}))
'''
    remote=ssh(code);write_new(DOC/'RENDER-CONTAINER-ABI-001.json',remote)
    print(json.dumps({'wsl':row,'container':remote},indent=2))

if __name__=='__main__': main()
