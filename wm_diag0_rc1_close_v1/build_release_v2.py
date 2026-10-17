"""Separate metadata-forecast final contract and staging release, no old edit."""
from pathlib import Path
from .common import ROOT,DOC,write_new
from .build import derive
def main():
    p='wm_diag0_rc1_close_v1/'
    extra="\nfor fixture in (DOC/'artificial-native-finish-001').rglob('*'):\n    if fixture.is_file():EVIDENCE['native-fixture/'+fixture.relative_to(DOC/'artificial-native-finish-001').as_posix()]=fixture\nEVIDENCE['NATIVE-FINISH-TEST.json']=DOC/'ARTIFICIAL-NATIVE-FINISH-001.json'\nEVIDENCE['PORTABLE-FORECAST.json']=DOC/'FORECAST001.json'\n"
    freeze=derive(p+'freeze.py',p+'freeze_v2.py',[
        ("DOC/'PREPARATION-COPIES-001.json'","DOC/'PREPARATION-COPIES-002.json'"),
        ("DOC/'PREPARATION-MEASUREMENT-001.json'","DOC/'PREPARATION-MEASUREMENT-002.json'"),
        ("'LINUX-INTEGRATION-002.json':DOC/'LINUXFINAL002.json'","'LINUX-INTEGRATION-003.json':DOC/'LINUXFINAL003.json'"),
        ('\ndef additions():',extra+'\ndef additions():'),
        ("tested=json.loads((DOC/'LINUXFINAL002.json').read_text())","tested=json.loads((DOC/'LINUXFINAL003.json').read_text())"),
        ("critical=('driver_v2.py','entry_v2.py','workflow_v2.py','archive_operation_v2.py','analysis_closure_v2.py','closed_identity_v2.py',","critical=('driver_v3.py','entry_v2.py','workflow_v3.py','archive_operation_v3.py','analysis_closure_v2.py','closed_identity_v2.py',"),
        ("'archive_pipeline.py','preservation_budget.py')","'archive_pipeline_v2.py','preservation_budget_v2.py','preparation_binding_v2.py','finish.py')"),
        ("'Linux_integration':identity(DOC/'LINUXFINAL002.json')","'Linux_integration':identity(DOC/'LINUXFINAL003.json')"),
        ("write_new(DOC/'FINAL-CONTRACT.json',c)","write_new(DOC/'FINAL-CONTRACT-002.json',c)"),
        ("'contract':identity(DOC/'FINAL-CONTRACT.json')","'contract':identity(DOC/'FINAL-CONTRACT-002.json')"),
        ("'actual_Linux_test':identity(DOC/'LINUXFINAL002.json')","'actual_Linux_test':identity(DOC/'LINUXFINAL003.json')"),
        ("write_new(DOC/'REVIEW-001.json',review)","write_new(DOC/'REVIEW-002.json',review)")])
    stage=derive(p+'stage_v2.py',p+'stage_v3.py',[
        ('from .publication_v2 import reviewed_additions','from .publication_delta_v4 import reviewed_additions'),
        ("DOC/'SSD-VERIFIED-001.json'","DOC/'SSD-VERIFIED-002.json'"),
        ("DOC/'FINAL-CONTRACT.json'","DOC/'FINAL-CONTRACT-002.json'"),
        ("DOC/'REVIEW-001.json'","DOC/'REVIEW-002.json'"),
        ("'wm_diag0_rc1_close_v1/stage_v2.py'","'wm_diag0_rc1_close_v1/stage_v3.py'"),
        ("('review-source-001','review-source-002','tests')","('review-source-001','review-source-002','review-source-003','tests')"),
        ('wm_diag0_rc1_close_v1.driver_v2','wm_diag0_rc1_close_v1.driver_v3'),
        ("call('STAGE001',CODE","call('STAGE002',CODE")])
    write_new(DOC/'FINAL-RELEASE-DERIVATION-002.json',{'status':'NEW_FORECAST_CORRECT_FINAL_CONTRACT_AND_STAGE_ADAPTER_DERIVED','freeze':freeze,'stage':stage,'scientific_source_or_estimator_changed':False})
    print('Final release adapters derived')
if __name__=='__main__':main()
