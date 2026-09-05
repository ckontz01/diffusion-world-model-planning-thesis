import json,sys,numpy as np
from pathlib import Path
from independent_pusht_collect import collect
root=Path(sys.argv[1]); collect(root,'pilot-20260906-v1',24,500)
p=json.loads((root/'COLLECTION.json').read_text())
q={str(h):{'displacement_quantiles':np.quantile([r['block_displacement'][str(h)] for r in p['records']],[0,.25,.5,.75,1]).tolist(),'already_solved':sum(r['initially_solved'][str(h)] for r in p['records'])} for h in (75,150)}
(root/'PILOT-QUALITY.json').write_text(json.dumps(q,indent=2))
print(json.dumps(q,indent=2))
