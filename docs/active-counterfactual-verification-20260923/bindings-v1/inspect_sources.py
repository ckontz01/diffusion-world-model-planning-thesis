"""Read pinned CODE ONLY over configured SSH. No runtime import or data load."""
import common
import subprocess

sage = common.RESEARCH + '/snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0/official-sage'
old = common.read(common.BASE / 'RUNTIME-PINS.json')
paths = [sage + '/sage/runtime/lewm.py', sage + '/stable_worldmodel/wm/lewm/lewm.py',
         sage + '/stable_worldmodel/wm/lewm/module.py']
runtime = old['runtime'] + '/lib/python3.11/site-packages/stable_worldmodel/'
paths += [runtime + r for r in ('world.py', 'wrapper.py', 'policy.py', 'envs/pusht/env.py')]
script = 'import pathlib,hashlib,json\nresult=[]\n'
script += 'for name in ' + repr(paths) + ':\n b=pathlib.Path(name).read_bytes();result.append(dict(path=name,sha256=hashlib.sha256(b).hexdigest(),source=b.decode()))\nprint(json.dumps(result))\n'
r = subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15',
                    '-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','prometheus','python3.9','-'],
                   input=script, capture_output=True, text=True, timeout=120)
common.require(r.returncode == 0, r.stderr)
values = common.json.loads(r.stdout)
for entry in values:
    if entry['path'] in old['runtime_files']:
        common.require(entry['sha256'] == old['runtime_files'][entry['path']], 'Pinned source changed')
common.write(common.ROOT / 'INSPECTED-SOURCES.json', values)
print('Source-only receipt:', len(values), 'files; research payload opens = 0')
