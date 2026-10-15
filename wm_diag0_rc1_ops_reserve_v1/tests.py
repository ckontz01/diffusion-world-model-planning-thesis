import json,sys
from decimal import Decimal
from .runner import DOC,command_check
from wm_diag0_rc1_v1.common import ROOT,write_new,identity

def main():
    a=json.loads((DOC/'ACTIVATION.json').read_text())
    if Decimal(str(a['previous_nonrefundable_charge']))+Decimal(str(a['new_nonrefundable_charge']))!=Decimal('14400'):raise AssertionError('exact original cap')
    command_check([sys.executable.replace('\\','/'),'-B','-m','wm_diag0_rc1_technical_v1.operations','observe','X'])
    for c in ([sys.executable,'-B','-m','wm_diag0_rc1_technical_v1.worker'],[sys.executable,'-B','-c','arbitrary'],['different.exe','-B','-m','wm_diag0_rc1_technical_v1.operations']):
        try:command_check(c)
        except ValueError:pass
        else:raise AssertionError('command allowlist')
    sources={}
    for p in (ROOT/'wm_diag0_rc1_ops_reserve_v1').glob('*.py'):compile(p.read_bytes(),str(p),'exec');sources[p.name]=identity(p)
    write_new(DOC/'TEST-001.json',{'status':'PASSED','source':sources,'scripted_command_executed':False,'new_research_calls':0,'checks':['exact funding sum','equivalent slash command accepted','research worker/arbitrary code/different executable rejected']})
    print(json.dumps({'status':'FINAL_RESERVE_ACCOUNTING_COMMAND_GUARDS_PASSED','research_calls':0}))

if __name__=='__main__':main()
