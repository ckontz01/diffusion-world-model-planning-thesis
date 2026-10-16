"""New publisher syntax/ordinary temporary ZIP guard tests; no git/D:/network."""
import ast,json,tempfile,zipfile
from pathlib import Path
from .common import ROOT,DOC,identity,write_new
from .publication import verify
from wm_diag0_preflight_v1.preserve import digest


def main():
    for p in Path(__file__).parent.glob('*.py'):
        text=p.read_text();ast.parse(text,feature_version=(3,6))
        if any(line.rstrip()!=line for line in text.splitlines()):raise ValueError('reject trailing whitespace before publication')
    with tempfile.TemporaryDirectory(prefix='wmrc1-monitor-source-') as tmp:
        path=Path(tmp)/'source.zip';payload={'fixture.py':b'new inert source\n'}
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as z:
            for n,b in payload.items():z.writestr(n,b)
        verify(path,{n:digest(b) for n,b in payload.items()})
        try:verify(path,{'wrong.py':digest(b'')})
        except ValueError:pass
        else:raise AssertionError('exact member guard')
        try:verify(path,{'fixture.py':digest(b'changed')})
        except ValueError:pass
        else:raise AssertionError('every member guard')
    result={'status':'ARTIFICIAL_MONITOR_PUBLICATION_SOURCE_GUARDS_PASSED',
            'sources':{p.name:identity(p) for p in Path(__file__).parent.glob('*.py')},
            'checks':['all new sources AST3.6','no trailing whitespace','actual ordinary-temp uncompressed ZIP member readback','wrong member/hash rejection'],
            'external_processes_launched':0,'cluster_or_designated_SSD_accessed':False,'research_calls':0}
    write_new(DOC/'ARTIFICIAL-002.json',result);print(json.dumps({'status':result['status'],'research_calls':0}))


if __name__=='__main__':main()
