"""Presentation-only escape for four table labels; no science recomputation."""
import json
from .common import DOC,identity,write_new

def main():
    path=DOC/'RESULTS.md';receipt=json.loads((DOC/'REPORT-RECEIPT.json').read_text())
    if identity(path)!=receipt['report']:raise ValueError('exact original frozen formatter output required')
    raw=path.read_bytes();updated=raw
    for key in (b'pusht|dinowm_noprop',b'pusht|lewm',b'reacher|dinowm_noprop',b'reacher|lewm'):
        old=b'| '+key+b' |';new=b'| '+key.replace(b'|',b' / ')+b' |'
        if updated.count(old)!=1:raise ValueError('only four exact presentation labels')
        updated=updated.replace(old,new)
    write_new(DOC/'reports-original/RESULTS-001.md',raw)
    # Fixed formatting-only mechanical rewrite, after lossless preimage retention.
    path.write_bytes(updated)
    final=dict(receipt,report=identity(path),status='COMPLETE_FOUR_SETTING_ALL128_PARENT_REPORT_PRESENTATION_ONLY_FIXED',
        original_report=identity(DOC/'reports-original/RESULTS-001.md'),original_report_receipt=identity(DOC/'REPORT-RECEIPT.json'),
        change='Four table row labels use slash instead of unescaped pipe; no number, formula, outcome or scientific source changes; no scientific rerun.')
    write_new(DOC/'REPORT-FORMAT-RECEIPT.json',final)
    print(json.dumps({'status':final['status'],'report':final['report']}))

if __name__=='__main__':main()
