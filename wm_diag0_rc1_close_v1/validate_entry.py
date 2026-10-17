"""Fixed independent second-pass entry; only technical proof leaves this child."""
import json,sys
from pathlib import Path
from .analysis_validate import validate_complete
from wm_diag0_rc1_grid_v1.common import write_new
def main():
    proof=validate_complete(sys.argv[1],sys.argv[2],sys.argv[3],float(sys.argv[4]))
    write_new(Path(sys.argv[3])/'controls/INDEPENDENT-ANALYSIS-VERIFIED.json',proof)
    print(json.dumps({'status':proof['status'],'parents':proof['parents'],'scientific_values_emitted':False}))
if __name__=='__main__':main()
