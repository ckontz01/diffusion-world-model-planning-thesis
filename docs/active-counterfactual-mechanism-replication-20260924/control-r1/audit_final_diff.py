"""Final mechanical adapter diff, distinct from initial preparation snapshot."""
import r1 as r
import difflib

if __name__=='__main__':
    text=''
    for old,new in [('worker.py','worker_r1.py'),('dispatch.py','campaign_r1.py'),('acceptance.py','acceptance_r1.py'),('preserve.py','preserve_r1.py')]:
        text+=''.join(difflib.unified_diff((r.science_root/old).read_text().splitlines(True),(r.ROOT/new).read_text().splitlines(True),fromfile='runtime-v2/'+old,tofile='control-r1/'+new))
    with (r.ROOT/'FINAL-SOURCE-DIFF.patch').open('xb') as f:f.write(text.encode())
    print(r.sha(r.ROOT/'FINAL-SOURCE-DIFF.patch'))
