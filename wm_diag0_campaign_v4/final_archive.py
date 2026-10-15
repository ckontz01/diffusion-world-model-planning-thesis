"""Create one bounded study tar only after complete independent acceptance."""
import hashlib,json,os,tarfile,time
from pathlib import Path

def ident(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return {'bytes':p.stat().st_size,'sha256':h.hexdigest()}

def create(root,c,deadline):
    root=Path(root);analysis=root/'tasks/analysis-0';accepted=json.loads((analysis/'controls/ACCEPTED.json').read_text())
    if not accepted['accepted'] or accepted['diagnostic_parents']!=128 or accepted['source_roots']!=120:raise ValueError('complete independent acceptance before archive')
    if ident(analysis/'output/MEMBERS.json')!=accepted['output_seal']:raise ValueError('analysis output seal')
    dest=root/'preservation';dest.mkdir(exist_ok=False);archive=dest/'final-study.tar'
    base=root.parent;files={};seen={};members={};total=0
    for label in ('preflight-v1','preflight-v1-stage-r1','native-v3','native-v3-import-r1','native-v3-source-r3','campaign-v4'):
        directory=base/label
        for p in sorted(directory.rglob('*')):
            if dest==p or dest in p.parents or p.is_dir():continue
            files['study/'+label+'/'+str(p.relative_to(directory)).replace('\\','/')]=p
    manifest=json.loads((root/'controls/RUNTIME-MANIFEST.json').read_text())['members']
    for rel,x in manifest.items():
        p=Path(c['venv'])/rel
        if p.is_symlink() or ident(p)!=x:raise ValueError('authenticated preserved runtime member')
        files['runtime/venv/'+rel]=p
    files['runtime/pytorch-runtime.sif']=Path(c['sif'])
    for task,x in c['lewm'].items():files['models/lewm-'+task+'.ckpt']=Path(x['path'])
    if sum(p.stat().st_size for p in files.values() if not p.is_symlink())>18000000000:raise ValueError('inclusive preservation input bound before deduplication')
    with archive.open('xb') as stream:
        with tarfile.open(fileobj=stream,mode='w',format=tarfile.PAX_FORMAT,dereference=False) as tar:
            for name,p in sorted(files.items()):
                if time.monotonic()>deadline:raise TimeoutError('finite analysis/preservation allocation')
                st=p.lstat();key=(st.st_dev,st.st_ino)
                if p.is_symlink():
                    target=os.readlink(str(p))
                    if '/renderer-r6/' not in name or c['renderer']['aliases'].get(p.name)!=target:raise ValueError('unexpected preservation symlink')
                    members[name]={'type':'symlink','target':target};tar.add(str(p),arcname=name,recursive=False)
                elif key in seen:
                    info=tar.gettarinfo(str(p),arcname=name);info.type=tarfile.LNKTYPE;info.size=0;info.linkname=seen[key]
                    tar.addfile(info);members[name]={'type':'hardlink','target':seen[key]}
                else:
                    x=ident(p);seen[key]=name;total+=x['bytes']
                    if total>13900000000:raise ValueError('14GB final archive reserve with metadata margin')
                    members[name]={'type':'file',**x};tar.add(str(p),arcname=name,recursive=False)
                if stream.tell()>14000000000:raise ValueError('14GB archive ceiling')
            raw=json.dumps({'contract_sha256':ident(root/'source/CONTRACT.json')['sha256'],'analysis_output_seal':accepted['output_seal'],'members':members},sort_keys=True).encode()
            if len(raw)>20000000:raise ValueError('archive manifest bound')
            import io
            info=tarfile.TarInfo('ARCHIVE-MEMBERS.json');info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
        stream.flush();os.fsync(stream.fileno())
    if archive.stat().st_size>14000000000:raise ValueError('14GB archive ceiling')
    row={'status':'FINAL_ARCHIVE_CREATED_PENDING_NATIVE_WINDOWS_SSD','archive':str(archive),'whole':ident(archive),'members':len(members)+1,
         'analysis_output_seal':accepted['output_seal'],'contract_sha256':ident(root/'source/CONTRACT.json')['sha256'],'scientific_results_published':False}
    with (dest/'ARCHIVE-CREATED.json').open('x') as f:json.dump(row,f,sort_keys=True)
    return row
