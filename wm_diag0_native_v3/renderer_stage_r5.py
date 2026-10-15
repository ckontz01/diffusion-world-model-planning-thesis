"""Stage authenticated libraries and test only an artificial 4x4 GL context."""
import hashlib,json,os,subprocess,time,zlib
from pathlib import Path
from .common import DOC,RUN,identity,write_new
from .renderer_bundle_r4 import archive
from wm_diag0_preflight_v1.common import SIF,VENV
from wm_diag0_preflight_v1.transport import ssh

def main():
    row=json.loads((DOC/'RENDERER-R4-PREPARED-001.json').read_text())
    paths={name:DOC/'delivery/renderer-r4/libraries'/name for name in row['members']}
    aliases=dict(row['aliases']); extra=DOC/'delivery/renderer-r5-supplement';extra.mkdir(exist_ok=False)
    # These two Ubuntu packages also place runtime libraries under /lib rather
    # than /usr/lib. Inspect their already authenticated archive data; no GET.
    for package in ('libtinfo6','zlib1g'):
        receipt=row['packages'][package]; p=DOC/'delivery/renderer-r4'/receipt['filename'].replace('/','_')
        if identity(p)!=receipt['identity']: raise ValueError('existing signed supplier')
        with archive(p) as tar:
            for info in tar.getmembers():
                n=info.name.removeprefix('./');prefix='lib/x86_64-linux-gnu/'
                if not n.startswith(prefix) or '/' in n[len(prefix):] or '.so' not in n:continue
                name=Path(n).name
                if info.issym():
                    if info.linkname!=Path(info.linkname).name:raise ValueError('relative alias')
                    aliases[name]=info.linkname;continue
                if not info.isfile() or info.size>2_000_000:raise ValueError('small supplementary ELF')
                raw=tar.extractfile(info).read(2_000_001)
                if len(raw)!=info.size or not raw.startswith(b'\x7fELF'):raise ValueError('ELF supplier')
                with (extra/name).open('xb') as f:f.write(raw)
                paths[name]=extra/name
    aliases['libOSMesa.so']='libOSMesa.so.8.0.0'
    members={name:identity(p) for name,p in sorted(paths.items())}
    for name,x in row['members'].items():
        if members[name]!=x:raise ValueError('R4 library identity')
    body={'members':members,'aliases':aliases,'parent_receipt':identity(DOC/'RENDERER-R4-PREPARED-001.json'),
          'regular_library_bytes':sum(x['bytes'] for x in members.values()),'sif_unchanged':True,'old_environment_unchanged':True}
    write_new(DOC/'RENDERER-R5-MANIFEST.json',body)
    payload=json.dumps(body).encode()+b'\n'+zlib.compress(b''.join(paths[n].read_bytes() for n in sorted(members)),1)
    if len(payload)>65_000_000 or body['regular_library_bytes']>200_000_000:raise ValueError('finite stage transfer')
    write_new(DOC/'RENDERER-R5-STAGE-001.started.json',{'payload_bytes':len(payload),'manifest':identity(DOC/'RENDERER-R5-MANIFEST.json')})
    code='RUN='+repr(RUN)+'\n'+'''
import hashlib,json,os,pathlib,sys,zlib
root=pathlib.Path(RUN); libs=root/'renderer-r5';libs.mkdir(exist_ok=False)
header=sys.stdin.buffer.readline(100000);m=json.loads(header);raw=zlib.decompress(sys.stdin.buffer.read(65000001));offset=0
if len(raw)!=m['regular_library_bytes'] or len(raw)>200000000:raise ValueError('finite library bytes')
for name,x in sorted(m['members'].items()):
 if '/' in name or chr(92) in name or not name.startswith('lib') or x['bytes']>160000000:raise ValueError('library allowlist')
 b=raw[offset:offset+x['bytes']];offset+=len(b)
 if len(b)!=x['bytes'] or hashlib.sha256(b).hexdigest()!=x['sha256']:raise ValueError('library member identity')
 p=libs/name
 with p.open('xb') as f:f.write(b)
 p.chmod(0o444)
for name,target in m['aliases'].items():
 if any('/' in v or chr(92) in v or not v.startswith('lib') for v in (name,target)):raise ValueError('library alias')
 seen=set();t=target
 while t in m['aliases']:
  if t in seen:raise ValueError('alias cycle')
  seen.add(t);t=m['aliases'][t]
 if t not in m['members']:raise ValueError('alias target outside closure')
 (libs/name).symlink_to(target)
with (root/'controls/RENDERER-R5-MANIFEST.json').open('xb') as f:f.write(header.rstrip(b'\n'))
libs.chmod(0o555)
print(json.dumps({'status':'AUTHENTICATED_READONLY_LIBRARY_LAYER_STAGED','regular_bytes':len(raw),'members':len(m['members']),'aliases':len(m['aliases']),'copied_model_bytes':0}))
'''
    result=ssh(code,payload=payload,timeout=120);write_new(DOC/'RENDERER-R5-STAGE-001.json',result)
    toy='''import ctypes,hashlib,json
from OpenGL import GL,osmesa
ctx=osmesa.OSMesaCreateContextExt(GL.GL_RGBA,24,8,0,None)
if not ctx:raise RuntimeError('OSMesa context unavailable')
buf=(ctypes.c_ubyte*(4*4*4))()
try:
 if not osmesa.OSMesaMakeCurrent(ctx,buf,GL.GL_UNSIGNED_BYTE,4,4):raise RuntimeError('software context failed')
 GL.glClearColor(.2,.4,.6,1.);GL.glClear(GL.GL_COLOR_BUFFER_BIT);GL.glFinish()
 renderer=GL.glGetString(GL.GL_RENDERER).decode()
 if not any(n in renderer.lower() for n in ('llvmpipe','softpipe')):raise RuntimeError('software renderer required')
 if bytes(buf)!=bytes([51,102,153,255])*16:raise RuntimeError('artificial pixel equality')
 print(json.dumps({'status':'ARTIFICIAL_SOFTWARE_RENDER_PASSED','renderer':renderer,'pixels_sha256':hashlib.sha256(bytes(buf)).hexdigest(),'pixels':16,'models':0,'simulators':0,'gpu_requests':0}))
finally:osmesa.OSMesaDestroyContext(ctx)'''
    code='RUN='+repr(RUN)+'\nSIF='+repr(SIF)+'\nVENV='+repr(VENV)+'\nTOY='+repr(toy)+'\n'+'''
import json,os,pathlib,subprocess
root=pathlib.Path(RUN);temp=root/'renderer-test-tmp';temp.mkdir(exist_ok=False)
env=dict(os.environ)
for k,v in {'LD_LIBRARY_PATH':'/renderer:/opt/conda/lib:/.singularity.d/libs','PYTHONPATH':'','PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','MUJOCO_GL':'osmesa','PYOPENGL_PLATFORM':'osmesa','LIBGL_ALWAYS_SOFTWARE':'1','GALLIUM_DRIVER':'llvmpipe','LP_NUM_THREADS':'4','OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4','CUDA_VISIBLE_DEVICES':'','HOME':'/tmp'}.items():env['APPTAINERENV_'+k]=v
p=subprocess.run(['apptainer','exec','--containall','--cleanenv','--no-home','--bind',str(root/'renderer-r5')+':/renderer:ro','--bind',str(temp)+':/tmp:rw','--bind',VENV+':'+VENV+':ro',SIF,VENV+'/bin/python','-B','-c',TOY],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=35)
r={'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'runtime_or_host_modified':False}
with (root/'controls/RENDERER-R5-TEST.json').open('x') as f:json.dump(r,f,sort_keys=True)
print(json.dumps(r))
'''
    result=ssh(code);write_new(DOC/'RENDERER-R5-TEST-001.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
