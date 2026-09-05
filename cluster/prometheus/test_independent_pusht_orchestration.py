"""Mocked scheduler regression checks; these tests submit no jobs."""
import json
import pytest
import submit_independent_pusht as ctl
from prepare_independent_pusht_study import prepare,tasks_for

def test_registry_full_coverage():
    for lo,hi in ((0,1600),(1600,3200),(3200,6000)):
        rows=tasks_for(lo,hi)
        assert len(rows)<1000
        keys=[(r['arm'],r['seed'],i) for r in rows for i in range(r['begin'],r['end'])]
        assert len(keys)==len(set(keys))==18*(hi-lo)

def make_study(tmp_path):
    source=tmp_path/'source';source.mkdir()
    for n in ('SOURCE-MANIFEST.sha256','INDEPENDENT-PUSHT-PROTOCOL.md'):(source/n).write_text('test-only')
    root=tmp_path/'study';prepare(root,source);return root

def test_dry_run(tmp_path,monkeypatch):
    root=make_study(tmp_path)
    monkeypatch.setattr(ctl,'submit',lambda args:pytest.fail('unexpected submission'))
    ctl.main(root,0,'123',dry=True)
    assert not (root/'SUBMISSION-0.json').exists()

def test_dependencies_and_duplicate_guard(tmp_path,monkeypatch):
    root=make_study(tmp_path);calls=[]
    def submit(args):calls.append(args);return str(100+len(calls))
    monkeypatch.setattr(ctl,'submit',submit)
    ctl.main(root,0,'77')
    assert '--dependency=afterok:77' in calls[0]
    assert '--dependency=afterok:101' in calls[1]
    assert '--dependency=afterok:102' in calls[2]
    with pytest.raises(RuntimeError,match='already submitted'):ctl.main(root,0)

def test_partial_submission_is_journaled(tmp_path,monkeypatch):
    root=make_study(tmp_path);count=[]
    def submit(args):
        count.append(1)
        if len(count)==1:return '555'
        raise RuntimeError('mock service unavailable')
    monkeypatch.setattr(ctl,'submit',submit)
    with pytest.raises(RuntimeError):ctl.main(root,0)
    d=json.loads((root/'SUBMISSION-0.json').read_text())
    assert d['array_job']=='555' and d['phase']=='array_submitted'

def test_verified_terminal_stops(tmp_path,monkeypatch):
    root=make_study(tmp_path);a=root/'analysis-0';a.mkdir()
    (a/'SUMMARY.json').write_text(json.dumps({'stop':True,'decision':'stop_all_three_established','n':1600}))
    (a/'INDEPENDENT-VERIFICATION.json').write_text(json.dumps({'all_passed':True,'summary_sha256':ctl.sha(a/'SUMMARY.json')}))
    monkeypatch.setattr(ctl,'submit',lambda args:pytest.fail('unexpected submission'))
    ctl.main(root,1)
    assert json.loads((root/'TERMINAL.json').read_text())['complete']
