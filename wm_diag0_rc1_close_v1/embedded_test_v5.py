"""Native fixture adapter: POSIX resource import is exercised on Linux, not NT."""
from pathlib import Path
def main():
    original=Path(__file__).with_name('embedded_test_v4.py');text=original.read_text()
    before="    with target.open('xb') as f:f.write(text.encode())"
    after="    if target.read_text()!=text:raise ValueError('unchanged already-derived production V4')"
    if text.count(before)!=1:raise ValueError('exact failed native fixture preimage')
    text=text.replace(before,after)
    before="    scope={};exec(compile(prefix,'<actual-reviewed-embedded-prefix>','exec'),scope)"
    after="    prefix=prefix.replace(',resource,',',') # Native fixture ONLY; POSIX allocation gates are not called\n    scope={};exec(compile(prefix,'<actual-reviewed-embedded-prefix>','exec'),scope)"
    if text.count(before)!=1:raise ValueError('exact fixture POSIX import')
    text=text.replace(before,after).replace('EMBEDDED-TEST-004.json','EMBEDDED-TEST-005.json')
    scope={'__name__':'new_native_fixture_adapter','__package__':'wm_diag0_rc1_close_v1','__file__':__file__}
    exec(compile(text,str(original)+'[native-resource-import-fixture-only]','exec'),scope);scope['main']()
if __name__=='__main__':main()
