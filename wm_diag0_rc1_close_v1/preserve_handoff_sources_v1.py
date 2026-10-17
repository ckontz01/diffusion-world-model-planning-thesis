"""Recover exact tested helper preimage and clarify validation scope in new V2."""
import ast,hashlib,json
from .common import ROOT,DOC,identity,write_new

def main():
    proof=json.loads((DOC/'ARTIFICIAL-RESULTS-HANDOFF-001.json').read_text())
    current=(ROOT/'wm_diag0_rc1_close_v1/publish_results_v1.py').read_bytes()
    text=current.decode('utf8')
    text=text.replace('selected=[];ignored=[];native_test_evidence={}','selected=[];ignored=[]')
    start=text.index('        test_prefix=');end=text.index('        test=subprocess.run',start)
    text=text[:start]+text[end:]
    text=text.replace("        limit=38000000 if p==DOC/'RESULTS.json' else 2000000\n        if p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400 or p.stat().st_size>limit:","        if p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400 or p.stat().st_size>2000000:")
    start=text.index('    test_archive=');end=text.index("    result={'status'",start)
    text=text[:start]+text[end:]
    text=text.replace("        'postarchive_native_test_SSD_archive':str(test_archive),'postarchive_native_test_whole':identity(test_archive),'postarchive_native_test_members':len(native_test_evidence),\n",'')
    raw=text.encode('utf8');want=proof['publisher_source']
    if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=want:raise ValueError('exact historical tested publisher source preimage, not inferred bytes')
    history=DOC/'source-history';history.mkdir(exist_ok=False)
    with (history/'publish_results_tested_preimage.py').open('xb') as out:out.write(raw)
    original=ROOT/'wm_diag0_rc1_close_v1/report_v1.py'
    if identity(original)!=proof['report_source']:raise ValueError('tested report source unchanged')
    with (history/'report_v1_tested.py').open('xb') as out:out.write(original.read_bytes())
    old=original.read_text(encoding='utf8')
    needle="        'Intervals: descriptive 95% percentile parent-paired bootstrap, 10,000 resamples, seed 20261004. No multiplicity-controlled or causal decomposition claim. No cross-backbone significance test is made.',"
    if old.count(needle)!=1:raise ValueError('exact reporting-only clarification location')
    new=old.replace(needle,needle+"\n        'Validation scope: a separate process reauthenticated original inputs and reconstructed every fixed field using the same prespecified estimator. This is software/result validation, not an external scientific replication or peer review.',")
    ast.parse(new,feature_version=(3,6));path=ROOT/'wm_diag0_rc1_close_v1/report_v2.py'
    with path.open('xb') as out:out.write(new.encode('utf8'))
    write_new(DOC/'HANDOFF-SOURCE-PREIMAGE-001.json',{'status':'EXACT_TESTED_HELPER_PREIMAGE_PRESERVED_NEW_REPORT_V2_SCOPE_CLARIFICATION_ONLY',
        'tested_publisher':identity(history/'publish_results_tested_preimage.py'),'tested_report':identity(history/'report_v1_tested.py'),
        'current_publisher':identity(ROOT/'wm_diag0_rc1_close_v1/publish_results_v1.py'),'new_report':identity(path),'scientific_inputs_estimator_or_values_changed':False})
    print('Exact tested helper source preimages preserved; new report V2 clarifies validation scope only')

if __name__=='__main__':main()
