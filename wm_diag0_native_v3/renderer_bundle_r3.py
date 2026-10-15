"""New read-only library layer. Never installs packages or replaces core libc."""
import base64
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import subprocess
import tarfile
import time
import urllib.request
from .common import DOC,identity,write_new

BASE='https://archive.ubuntu.com/ubuntu/'
DEST=DOC/'delivery/renderer-r3'
NAMES=('libosmesa6','libglapi-mesa','libllvm15','libdrm2','libffi8','libedit2','libtinfo6','libxml2','libicu70','libbsd0','libmd0','libzstd1','zlib1g')

def get(relative,maximum):
    if relative.startswith('/') or '..' in relative.split('/'): raise ValueError('official relative URL')
    p=DEST/relative.replace('/','_'); partial=p.with_name(p.name+'.partial')
    h=hashlib.sha256(); n=0
    with urllib.request.urlopen(BASE+relative,timeout=25) as r, partial.open('xb') as f:
        if not r.geturl().startswith(BASE): raise ValueError('unexpected download origin')
        while True:
            b=r.read(1048576)
            if not b: break
            n+=len(b)
            if n>maximum or sum(x.stat().st_size for x in DEST.rglob('*') if x.is_file())+len(b)>250_000_000: raise ValueError('finite transfer/storage bound')
            f.write(b);h.update(b)
        f.flush();os.fsync(f.fileno())
    # Exclusive target checked before recoverable rename; no evidence overwritten.
    if p.exists(): raise FileExistsError('preserve prior download')
    partial.rename(p)
    return p,{'bytes':n,'sha256':h.hexdigest()}

def paragraphs(text):
    for block in text.split('\n\n'):
        row={}
        for line in block.splitlines():
            if line and not line[0].isspace() and ': ' in line:
                k,v=line.split(': ',1);row[k]=v
        if row.get('Package') in NAMES and row.get('Architecture')=='amd64': yield row

def ar_data(path):
    with path.open('rb') as f:
        if f.read(8)!=b'!<arch>\n': raise ValueError('Debian ar magic')
        while True:
            h=f.read(60)
            if not h: break
            if len(h)!=60 or h[-2:]!=b'`\n': raise ValueError('ar header')
            name=h[:16].decode().strip().rstrip('/'); n=int(h[48:58])
            if n>90_000_000: raise ValueError('ar member size')
            raw=f.read(n)
            if len(raw)!=n: raise ValueError('ar truncation')
            if n%2: f.read(1)
            if name.startswith('data.tar.'):
                return name,raw
    raise ValueError('one package data archive')

def main():
    DEST.mkdir(parents=True,exist_ok=False); started=time.monotonic()
    chosen={}; indexes={}; signatures={}; receipts={}
    try:
        for pocket in ('jammy-updates','jammy'):
            release,rid=get('dists/'+pocket+'/InRelease',1_000_000)
            wsl='/mnt/'+release.drive[0].lower()+release.as_posix()[2:]
            p=subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout','15s','gpgv','--keyring','/usr/share/keyrings/ubuntu-archive-keyring.gpg',wsl],capture_output=True,text=True,timeout=20)
            signatures[pocket]={'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'release':rid}
            if p.returncode: raise ValueError('official archive signature')
            text=release.read_text(); entries={}; active=False
            for line in text.splitlines():
                if line=='SHA256:': active=True;continue
                if active:
                    if not line.startswith(' '): break
                    sha,size,name=line.split();entries[name]={'bytes':int(size),'sha256':sha}
            for component in ('main','universe'):
                name=component+'/binary-amd64/Packages.xz'
                p,pid=get('dists/'+pocket+'/'+name,40_000_000)
                if pid!=entries[name]: raise ValueError('signed package index identity')
                with lzma.open(p,'rt') as f:
                    text=f.read(240_000_001)
                if len(text)>240_000_000: raise ValueError('index expansion bound')
                indexes[pocket+'/'+name]=pid
                for row in paragraphs(text): chosen.setdefault(row['Package'],row)
                if set(chosen)==set(NAMES): break
            if set(chosen)==set(NAMES): break
        if set(chosen)!=set(NAMES): raise ValueError('finite package allowlist unavailable')
        libs=DEST/'libraries';libs.mkdir()
        aliases={}; members={}
        for name in NAMES:
            row=chosen[name]
            p,pid=get(row['Filename'],80_000_000)
            if pid!={'bytes':int(row['Size']),'sha256':row['SHA256']}: raise ValueError('signed package bytes')
            archive,raw=ar_data(p)
            with tarfile.open(fileobj=io.BytesIO(raw),mode='r:*') as tar:
                infos=tar.getmembers()
                if len(infos)>3000: raise ValueError('package member bound')
                for info in infos:
                    n=info.name.removeprefix('./')
                    if not n.startswith('usr/lib/x86_64-linux-gnu/') or '/' in n[len('usr/lib/x86_64-linux-gnu/'):]: continue
                    if '.so' not in n: continue
                    target=libs/Path(n).name
                    if info.issym():
                        link=Path(info.linkname).name
                        if info.linkname!=link: raise ValueError('relative library link only')
                        aliases[target.name]=link;continue
                    if not info.isfile() or info.size>160_000_000: raise ValueError('ELF library member')
                    data=tar.extractfile(info).read(160_000_001)
                    if len(data)!=info.size or not data.startswith(b'\x7fELF'): raise ValueError('bounded ELF bytes')
                    if target.exists():
                        if target.read_bytes()!=data: raise ValueError('library basename collision')
                    else:
                        with target.open('xb') as f:f.write(data)
                    members[target.name]=identity(target)
            receipts[name]={'version':row['Version'],'filename':row['Filename'],'identity':pid,'depends':row.get('Depends'),'download_url':BASE+row['Filename']}
            if sum(x.stat().st_size for x in DEST.rglob('*') if x.is_file())>250_000_000: raise ValueError('retained preparation limit')
        result={'status':'OFFICIAL_SIGNED_LIBRARY_BYTES_PREPARED_NOT_INSTALLED','signatures':signatures,'indexes':indexes,
                'packages':receipts,'members':members,'aliases':aliases,'library_bytes':sum(x['bytes'] for x in members.values()),
                'retained_bytes':sum(x.stat().st_size for x in DEST.rglob('*') if x.is_file()),'old_environment_modified':False,
                'simulators_instantiated':0,'models_loaded':0,'elapsed_seconds':time.monotonic()-started}
        write_new(DOC/'RENDERER-R3-PREPARED-001.json',result); print(json.dumps(result,indent=2))
    except BaseException as exc:
        write_new(DOC/'RENDERER-R3-FAILURE-001.json',{'error':repr(exc),'signatures':signatures,'indexes':indexes,'packages':receipts,
                   'retained_members':{str(p.relative_to(DEST)):identity(p) for p in DEST.rglob('*') if p.is_file()},'elapsed_seconds':time.monotonic()-started})
        raise

if __name__=='__main__':main()
