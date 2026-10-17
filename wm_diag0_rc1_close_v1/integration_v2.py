"""NEW Linux V2 snapshot and regression, preserving first failure and fixtures."""
import ast,base64,hashlib,json
from .integration import CODE,source_members
from .common import DOC,write_new
from .transport_v2 import call
def main():
    code=CODE.replace("review-source-001","review-source-002").replace("final-runtime-001","final-runtime-002")
    before='from wm_diag0_rc1_close_v1 import driver,workflow,archive_operation as archive,analysis_closure as closure'
    after='from wm_diag0_rc1_close_v1 import driver_v2 as driver,workflow_v2 as workflow,archive_operation_v2 as archive,analysis_closure_v2 as closure'
    if code.count(before)!=1:raise ValueError('exact failed integration import')
    code=code.replace(before,after);ast.parse(code,feature_version=(3,6))
    members=source_members();ids={n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in members.items()}
    result=call('LINUXFINAL002',code,{'members':{n:base64.b64encode(b).decode() for n,b in members.items()},'identities':ids},seconds=150)
    print(json.dumps({'status':result['status'],'actual_analysis':False,'new_research_allocations':0}))
if __name__=='__main__':main()
