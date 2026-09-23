"""ACV0 completion: small stdlib control plane. Imports do not access research."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
REPO = BASE.parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE))
CONTROLS = ('vanilla', 'static', 'passive', 'active', 'no_update', 'ordinary', 'bayesian', 'early-replan')
RESEARCH = '/lustreFS/data/superworld/ckontzias/thesis'
RUN_PARENT = RESEARCH + '/experiments/active-counterfactual-verification-pilot-v1'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def write(path, value):
    """Exclusive creation; never silently replace evidence."""
    with Path(path).open('xb') as f:
        f.write(canonical(value) + b'\n')
        f.flush()
        os.fsync(f.fileno())


def roles():
    return read(BASE / 'DATA-ROLES-PROPOSED.json')['proposed_roles']


def grid():
    jobs = read(BASE / 'PILOT-PROPOSED.json')['grid']
    for j in jobs:
        if j['stage'] == 'fitting':
            j.pop('epochs')
            j['updates'] = 192
        j['byte_cap'] = 10_000_000 if j['stage'] == 'collection' else 2_000_000 if j['stage'] == 'evaluation' else 100_000_000
        if j['key'] == 'collect-fit-490':
            j['seconds'] = 1740  # R1: same physical task, one shortened replacement.
    require(len(jobs) == 339 and len({j['key'] for j in jobs}) == 339, 'Grid identity')
    return jobs


def seal(directory, identity):
    p = Path(directory)
    files = {str(f.relative_to(p)).replace('\\', '/'): {'sha256': sha(f), 'bytes': f.stat().st_size}
             for f in sorted(p.rglob('*')) if f.is_file() and f.name != 'SEAL.json'}
    write(p / 'SEAL.json', {'identity': identity, 'files': files})


def verify_seal(directory, expected=None):
    p = Path(directory)
    s = read(p / 'SEAL.json')
    if expected is not None:
        require(s['identity'] == expected, 'Seal identity')
    actual = {str(f.relative_to(p)).replace('\\', '/') for f in p.rglob('*') if f.is_file() and f.name != 'SEAL.json'}
    require(actual == set(s['files']), 'Seal member set')
    for name, info in s['files'].items():
        f = p / name
        require(f.resolve().is_relative_to(p.resolve()) and not f.is_symlink(), 'Seal path')
        require(f.stat().st_size == info['bytes'] and sha(f) == info['sha256'], 'Seal member: ' + name)
    return s


class Authorization:
    """Explicit contract capability. False template rejected BEFORE input reads.

    This is an execution interlock, not a cryptographic signature or a substitute
    for a user's explicit instruction. No command in this package creates an
    enabled approval. The immutable package must be reviewed first.
    """
    def __init__(self, approval, run):
        a = read(approval)
        fields = {'schema', 'authorized', 'instruction', 'package_sha256', 'grid_sha256',
                  'roles_sha256', 'inputs_sha256', 'run', 'no_retry', 'research_caps', 'recovery'}
        require(set(a) == fields and a['schema'] == 'ACV0-recovery-r1', 'Approval schema')
        if a['authorized'] is not True:
            raise PermissionError('Research execution disabled; explicit execution instruction here required')
        require(isinstance(a['instruction'], str) and a['instruction'].startswith('EXECUTE ACV0 ') and len(a['instruction']) > 40,
                'Missing recorded explicit execution instruction')
        require(a['run'] == str(run) and Path(run).parent.as_posix() == RUN_PARENT, 'Exclusive run namespace')
        require(Path(run).name == 'run-' + a['package_sha256'][:16], 'Run/package identity')
        require(a['no_retry'] is True and a['research_caps'] == caps(), 'Frozen caps/no retry')
        require(a['package_sha256'] == sha(ROOT / 'SOURCE-MANIFEST.json'), 'Package manifest identity')
        require(a['grid_sha256'] == digest(grid()), 'Grid identity')
        require(a['roles_sha256'] == sha(BASE / 'DATA-ROLES-PROPOSED.json'), 'Roles identity')
        require(a['inputs_sha256'] == sha(ROOT / 'INPUT-BINDINGS.json'), 'Inputs identity')
        from recovery import approval_binding
        require(a['recovery'] == approval_binding(a['package_sha256']), 'Recovery authorization binding')
        require(hashlib.sha256(a['instruction'].encode('utf8')).hexdigest() == a['recovery']['instruction_sha256'], 'Exact recovery instruction')
        for name, h in read(ROOT / 'SOURCE-MANIFEST.json')['files'].items():
            require(sha(REPO / name) == h, 'Source closure: ' + name)
        self.approval = a
        self.run = Path(run)
        self.approval_sha = sha(approval)
        self.inputs = read(ROOT / 'INPUT-BINDINGS.json')

    def runtime(self):
        """Source and runtime authentication only; no research checkpoints here."""
        if getattr(self,'runtime_verified',False):return
        for p, h in self.inputs['runtime_files'].items():
            require(sha(p) == h, 'Runtime source/dependency identity: ' + p)
        require(sha(self.inputs['container']['path']) == self.inputs['container']['sha256'], 'Container identity')
        self.runtime_verified=True

    def checkpoint(self):
        p = self.inputs['lewm']
        require(sha(p) == self.inputs['lewm_sha256'], 'Le-WM checkpoint identity')
        return p

    def reference(self, index, role):
        require(index in roles()[role], 'Forbidden reference role')
        r = self.inputs['references'][str(index)]
        require(sha(r['file']) == r['sha256'], 'Reference identity')
        return r


def caps():
    return {'gpu_seconds': 220800, 'cpu_job_seconds': 21600, 'gpu_concurrency': 1,
            'new_live_bytes': 2_000_000_000, 'live_archive_partial_bytes': 8_000_000_000,
            'source_models_control_analysis_bytes': 500_000_000, 'ssd_free_bytes': 40_000_000_000}


def work_seconds(spec):
    return spec['seconds'] - (120 if spec['stage'] == 'collection' else 60)


def supervisor_seconds(spec):
    return spec['seconds'] - 10
