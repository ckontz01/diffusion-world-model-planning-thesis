"""Small review reduction of sealed R2 analysis; no simulator imports."""
import json
from pathlib import Path
import sys
from analyze_gdp_cem_e19_r1 import read,sha

def main(source,out):
    x=read(source)
    result={k:v for k,v in x.items() if k!='singles'}
    result['full_summary_path']=str(source); result['full_summary_sha256']=sha(source)
    result['reducer_sha256']=sha(Path(__file__))
    result['singles']=[]
    for s in x['singles']:
        row={k:v for k,v in s.items() if k not in ('after_reset','before_physics','after_physics')}
        row['received_seed']=s['after_reset']['received_seed']; row['effective_seed']=s['after_reset']['effective_seed']
        row['actual_env_seed']=s['after_reset']['rng']['env_seed']
        row['boundary_body_state']={name:s[name]['physical']['bodies'] for name in ('after_reset','before_physics','after_physics')}
        row['shape_bounds']={name:s[name]['shapes'] for name in ('after_reset','before_physics','after_physics')}
        result['singles'].append(row)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f: json.dump(result,f,indent=2,sort_keys=True); f.write('\n')
    with (out.parent/'sha256.txt').open('x') as f:f.write(sha(out)+'  '+out.name+'\n')
    print(sha(out),out.stat().st_size)
if __name__=='__main__': main(Path(sys.argv[1]),Path(sys.argv[2]))
