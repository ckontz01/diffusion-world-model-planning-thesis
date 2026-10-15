"""Finite UTF-8/package-reader repair; R3 downloads and failure stay intact."""
import hashlib,io,json,lzma,os,subprocess,tarfile,time,urllib.request
from pathlib import Path
from .common import DOC,identity,write_new
from .renderer_bundle_r3 import BASE,NAMES,paragraphs,ar_data

DEST=DOC/'delivery/renderer-r4'
OLD=DOC/'delivery/renderer-r3'
OLD_ID=json.loads((DOC/'RENDERER-R3-FAILURE-001.json').read_text())['retained_members']

def get(relative,maximum):
    name=relative.replace('/','_')
    if relative.startswith('/') or '..' in relative.split('/'): raise ValueError('official relative URL')
    prior=OLD/name
    if name in OLD_ID:
        if identity(prior)!=OLD_ID[name]: raise ValueError('authenticated R3 supplier changed')
        return prior,OLD_ID[name]
    p=DEST/name; partial=p.with_name(p.name+'.partial'); n=0; h=hashlib.sha256()
    with urllib.request.urlopen(BASE+relative,timeout=25) as response,partial.open('xb') as f:
        if not response.geturl().startswith(BASE): raise ValueError('official origin')
        while True:
            raw=response.read(1048576)
            if not raw: break
            n+=len(raw)
            if n>maximum or retained()+len(raw)>250_000_000: raise ValueError('transfer/retained bound')
            f.write(raw);h.update(raw)
        f.flush();os.fsync(f.fileno())
    if p.exists(): raise FileExistsError('exclusive download')
    partial.rename(p)
    return p,{'bytes':n,'sha256':h.hexdigest()}

def retained():
    return sum(p.stat().st_size for base in (OLD,DEST) for p in base.rglob('*') if p.is_file())

def archive(path):
    name,raw=ar_data(path)
    if name.endswith('.zst'):
        wsl='/mnt/'+path.drive[0].lower()+path.as_posix()[2:]
        p=subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout','30s','dpkg-deb','--fsys-tarfile',wsl],capture_output=True,timeout=35)
        if p.returncode or len(p.stdout)>220_000_000: raise ValueError('bounded existing dpkg data decompressor')
        return tarfile.open(fileobj=io.BytesIO(p.stdout),mode='r:')
    return tarfile.open(fileobj=io.BytesIO(raw),mode='r:*')

def main():
    DEST.mkdir(parents=True,exist_ok=False); began=time.monotonic(); signatures={};indexes={};chosen={};receipts={}
    try:
        for pocket in ('jammy-updates','jammy'):
            release,rid=get('dists/'+pocket+'/InRelease',1_000_000)
            wsl='/mnt/'+release.drive[0].lower()+release.as_posix()[2:]
            p=subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','timeout','15s','gpgv','--keyring','/usr/share/keyrings/ubuntu-archive-keyring.gpg',wsl],capture_output=True,text=True,timeout=20)
            signatures[pocket]={'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'release':rid}
            if p.returncode: raise ValueError('signed release')
            entries={};active=False
            for line in release.read_text(encoding='utf8').splitlines():
                if line=='SHA256:':active=True;continue
                if active:
                    if not line.startswith(' '):break
                    sha,size,name=line.split();entries[name]={'bytes':int(size),'sha256':sha}
            for component in ('main','universe'):
                name=component+'/binary-amd64/Packages.xz';p,pid=get('dists/'+pocket+'/'+name,40_000_000)
                if pid!=entries[name]: raise ValueError('signed index identity')
                with lzma.open(p,'rt',encoding='utf8') as f: text=f.read(240_000_001)
                if len(text)>240_000_000:raise ValueError('index expansion')
                indexes[pocket+'/'+name]=pid
                for row in paragraphs(text):chosen.setdefault(row['Package'],row)
                if set(chosen)==set(NAMES):break
            if set(chosen)==set(NAMES):break
        if set(chosen)!=set(NAMES):raise ValueError('finite package allowlist')
        write_new(DOC/'RENDERER-R4-SELECTED-001.json',{'packages':{k:{x:r[x] for x in ('Version','Filename','Size','SHA256','Depends')} for k,r in chosen.items()},'signatures':signatures,'indexes':indexes})
        libs=DEST/'libraries';libs.mkdir();members={};aliases={}
        for name in NAMES:
            row=chosen[name];p,pid=get(row['Filename'],80_000_000)
            if pid!={'bytes':int(row['Size']),'sha256':row['SHA256']}:raise ValueError('signed package identity')
            with archive(p) as tar:
                infos=tar.getmembers()
                if len(infos)>3000:raise ValueError('package membership bound')
                for info in infos:
                    n=info.name.removeprefix('./');prefix='usr/lib/x86_64-linux-gnu/'
                    if not n.startswith(prefix) or '/' in n[len(prefix):] or '.so' not in n:continue
                    target=libs/Path(n).name
                    if info.issym():
                        if info.linkname!=Path(info.linkname).name:raise ValueError('relative library alias')
                        aliases[target.name]=info.linkname;continue
                    if not info.isfile() or info.size>160_000_000:raise ValueError('numeric ELF data member')
                    raw=tar.extractfile(info).read(160_000_001)
                    if len(raw)!=info.size or not raw.startswith(b'\x7fELF'):raise ValueError('ELF format/size')
                    if retained()+len(raw)>250_000_000:raise ValueError('all-failure-inclusive retained bound')
                    with target.open('xb') as f:f.write(raw)
                    members[target.name]=identity(target)
            receipts[name]={'version':row['Version'],'filename':row['Filename'],'identity':pid,'depends':row.get('Depends'),'download_url':BASE+row['Filename']}
        result={'status':'SIGNED_LIBRARY_BYTES_READY_NOT_INSTALLED','members':members,'aliases':aliases,'packages':receipts,'signatures':signatures,'indexes':indexes,
                'reused_R3_suppliers':OLD_ID,'library_bytes':sum(x['bytes'] for x in members.values()),'retained_bytes':retained(),
                'elapsed_seconds':time.monotonic()-began,'old_environment_modified':False,'models_loaded':0,'simulators':0}
        write_new(DOC/'RENDERER-R4-PREPARED-001.json',result);print(json.dumps(result,indent=2))
    except BaseException as exc:
        write_new(DOC/'RENDERER-R4-FAILURE-001.json',{'error_type':type(exc).__name__,'error':str(exc)[:1500],'packages':receipts,'elapsed_seconds':time.monotonic()-began,
                  'retained_members':{str(p.relative_to(DOC/'delivery')):identity(p) for b in (OLD,DEST) for p in b.rglob('*') if p.is_file()}})
        raise

if __name__=='__main__':main()
