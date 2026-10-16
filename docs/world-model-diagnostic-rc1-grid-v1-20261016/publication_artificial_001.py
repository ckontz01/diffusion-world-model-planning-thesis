"""Artificial publisher transaction tests, no Git/network/SSD or research call."""
import json,subprocess,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from wm_diag0_rc1_grid_v1 import publication as pub
from wm_diag0_rc1_grid_v1.common import ROOT,DOC,identity,write_new


def main():
    c=json.loads((DOC/'GRID-CONTRACT.json').read_text())
    for n,x in c['staged_members'].items():
        if n.startswith('wm_diag0_rc1_grid_v1/') and identity(ROOT/n)!=x:raise ValueError('frozen source changed after actual review/freeze')
    for mode in ('success','unrelated_staged','remote_mismatch'):
        with tempfile.TemporaryDirectory(prefix='wm-rc1-publish-artificial-') as tmp:
            d=Path(tmp);write_new(d/'GRID-CONTRACT.json',{'domain':'artificial'})
            (d/'INDEPENDENT-PREFREEZE-REVIEW-001.txt').write_text('artificial only')
            calls=[];diffs=0;sha='c'*40;file='wm_diag0_rc1_grid_v1/common.py'
            def git(*args):
                nonlocal diffs
                calls.append(args)
                if args==('diff','--cached','--name-only'):
                    diffs+=1
                    return b'unrelated-user-file' if mode=='unrelated_staged' else b'' if diffs==1 else file.encode()
                if args[0]=='ls-files':return file.encode() if args[-1]=='wm_diag0_rc1_grid_v1' else b''
                if args==('rev-parse','HEAD'):return sha.encode()
                if args[0]=='ls-remote':return (('d'*40 if mode=='remote_mismatch' else sha)+'\tref').encode()
                return b''
            runner=SimpleNamespace(returncode=0,stdout=json.dumps({'status':'artificial-SSD-verified'}),stderr='')
            with patch.object(pub,'DOC',d),patch.object(pub,'ROOT',d),patch.object(pub,'git',git),patch.object(pub.subprocess,'run',return_value=runner) as mock_run:
                failed=False
                try:pub.main()
                except (ValueError,RuntimeError):failed=True
                if failed!=(mode!='success'):raise AssertionError('publisher gate result')
                if mode=='unrelated_staged' and any(x[0] in ('add','commit','push') for x in calls):raise AssertionError('unrelated work changed')
                if mode=='remote_mismatch' and mock_run.called:raise AssertionError('SSD proceeded before full remote match')
                if mode=='success' and (not mock_run.called or not (d/'PUBLICATION-001.json').exists()):raise AssertionError('publication receipt missing')
    write_new(DOC/'PUBLICATION-ARTIFICIAL-001.json',{'status':'PASSED','frozen_contract':identity(DOC/'GRID-CONTRACT.json'),
        'publisher_source':identity(ROOT/'wm_diag0_rc1_grid_v1/publication.py'),'checks':['exact frozen new source identities','unrelated staged work rejected','remote full hash mismatch blocks preservation','publication/SSD receipt only after success'],
        'actual_git_network_SSD_model_or_simulator_calls':0})
    print(json.dumps({'status':'PUBLICATION_ARTIFICIAL_PASSED','research_calls':0}))


if __name__=='__main__':main()
