"""New forecast-driven real Linux preservation/controller regression."""
import ast,base64,hashlib,json
from .integration import CODE,source_members
from .transport_v2 import call
def main():
    code=CODE.replace('review-source-001','review-source-003').replace('final-runtime-001','final-runtime-003')
    before='from wm_diag0_rc1_close_v1 import driver,workflow,archive_operation as archive,analysis_closure as closure'
    after='from wm_diag0_rc1_close_v1 import driver_v3 as driver,workflow_v3 as workflow,archive_operation_v3 as archive,analysis_closure_v2 as closure'
    if code.count(before)!=1:raise ValueError('exact integration preimage')
    code=code.replace(before,after)
    code=code.replace("print(json.dumps(z,separators=(',',':')))","from wm_diag0_rc1_close_v1.preservation_budget_v2 import prove,PORTABLE_LIMIT\nif PORTABLE_LIMIT!=20000000:raise AssertionError('actual forecast cap')\nz['actual_forecast_portable_cap']=PORTABLE_LIMIT\nprint(json.dumps(z,separators=(',',':')))")
    ast.parse(code,feature_version=(3,6));members=source_members();ids={n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in members.items()}
    z=call('LINUXFINAL003',code,{'members':{n:base64.b64encode(b).decode() for n,b in members.items()},'identities':ids},seconds=150)
    print(json.dumps({'status':z['status'],'forecast_cap_tested':z['actual_forecast_portable_cap'],'real_analysis':False}))
if __name__=='__main__':main()
