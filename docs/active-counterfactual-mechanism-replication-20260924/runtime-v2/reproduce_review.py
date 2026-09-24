"""Run the supplied immutable excerpt probes, not a production acceptance test."""
import common as c
import ast
import contextlib
import io
from pathlib import Path
import tempfile
from unittest.mock import patch

def main():
    supplied=c.ROOT/'review-input';manifest=c.read(supplied/'MANIFEST.json')
    for name,item in manifest.items():
        p=supplied/name;c.require(p.stat().st_size==item['bytes'] and c.sha(p)==item['sha256'],'Supplied probe identity')
    script=(supplied/'review_probes.py').read_text(encoding='utf8')
    with tempfile.TemporaryDirectory() as directory:
        ns={'__name__':'review_probe_not_main','__file__':str(Path(directory)/'review_probes.py')}
        exec(compile(script,str(supplied/'review_probes.py'),'exec'),ns)
        checked=[]
        for name,path,function in [('COMMAND_SOURCE',c.ROOT.parent/'runtime-v1/dispatch.py','command'),
                                   ('EVALUATION_SOURCE',c.ROOT.parent/'runtime-v1/worker.py','evaluation'),
                                   ('READER_SOURCE',c.OLD/'verify.py','load_verify')]:
            source=path.read_text(encoding='utf8');node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==function)
            c.require(ast.dump(ast.parse(ns[name]),include_attributes=False)==ast.dump(ast.Module(body=[node],type_ignores=[]),include_attributes=False),'Review excerpt diverged from pinned source')
            checked.append(dict(function=function,file=str(path.relative_to(c.REPO)),sha256=c.sha(path)))
        read_bytes=Path.read_bytes
        # The supplied Linux-only ELF assertion is a binary fixture on Windows.
        # The literal erroneous operand and function excerpts remain untouched.
        def local_bytes(path):return b'\x7fELF' if str(path).replace('\\','/')=='/bin/bash' else read_bytes(path)
        output=io.StringIO()
        with patch.object(Path,'read_bytes',local_bytes),contextlib.redirect_stdout(output):ns['main']()
        result=c.read(Path(directory)/'PROBE-RESULTS.json')
        result.update(exact_source_excerpts=checked,windows_adaptation='Only /bin/bash read_bytes returned an artificial ELF header; no host binary or Slurm was run.',
                      supplied_script_sha256=c.sha(supplied/'review_probes.py'),original_supplied_results_preserved=True)
        c.write(c.ROOT/'PROBE-REPRODUCTION.json',result)
        print(c.json.dumps(result,indent=2))
if __name__=='__main__':main()
