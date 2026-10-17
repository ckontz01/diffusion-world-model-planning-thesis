"""Correct generator's two explicit measurement-name references, no old edit."""
from pathlib import Path
def main():
    original=Path(__file__).with_name('build_manifest_v3.py');text=original.read_text()
    before="        (\"PREPARATION-MEASUREMENT-001.json\",\"PREPARATION-MEASUREMENT-002.json\"),"
    after="        (\"write_new(doc/'PREPARATION-MEASUREMENT-001.json',audit)\",\"write_new(doc/'PREPARATION-MEASUREMENT-002.json',audit)\"),\n        (\"commitment=identity(doc/'PREPARATION-MEASUREMENT-001.json')\",\"commitment=identity(doc/'PREPARATION-MEASUREMENT-002.json')\"),"
    if text.count(before)!=1:raise ValueError('exact source-generator preimage')
    text=text.replace(before,after)
    scope={'__name__':'corrected_explicit_source_generator','__package__':'wm_diag0_rc1_close_v1','__file__':__file__}
    exec(compile(text,str(original)+'[two-explicit-references]','exec'),scope);scope['main']()
if __name__=='__main__':main()
