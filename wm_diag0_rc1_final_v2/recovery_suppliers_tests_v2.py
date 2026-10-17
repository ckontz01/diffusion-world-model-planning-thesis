"""Separate native fixture-path correction; original failed V1 retained.

The mapping library returned the correct Path. V1 compared Windows backslashes
to Linux literals. Normalize ONLY fixture rendering; no production code change.
"""
from pathlib import Path

def main():
    original=Path(__file__).with_name('recovery_suppliers_tests_v1.py')
    raw=original.read_text()
    before='locations.append(str(location))'
    if raw.count(before)!=1:raise ValueError('exact diagnosed fixture preimage')
    raw=raw.replace(before,'locations.append(location.as_posix())')
    raw=raw.replace("ARTIFICIAL-RECOVERY-SUPPLIERS-001.json","ARTIFICIAL-RECOVERY-SUPPLIERS-002.json")
    raw=raw.replace("[Path(__file__),Path(__file__).with_name('recovery_suppliers_v1.py')]","[Path(__file__),Path(__file__).with_name('recovery_suppliers_tests_v1.py'),Path(__file__).with_name('recovery_suppliers_v1.py')]")
    scope={'__name__':'corrected_native_fixture_not_old_suite','__package__':'wm_diag0_rc1_final_v2','__file__':__file__}
    exec(compile(raw,str(original)+'[fixture-path-normalization-only]','exec'),scope);scope['main']()

if __name__=='__main__':main()
