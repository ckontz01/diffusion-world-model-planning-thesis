"""Standard-library-only copy of the v1 metadata/hash model-freeze gate.

This does not deserialize models, inspect scientific fit quality, fit anything,
or need NumPy. Its output is byte-identical to fitting.model_freeze.
"""
import common as c


def model_freeze(run, package_sha):
    entries = {}
    for key in ('fit-joint','fit-ordinary'):
        seal = c.verify_seal(run/key)
        c.require(c.read(run/key/'FIT.json')['updates']==192, 'Fit update contract')
        c.require(set(c.read(run/key/'PREPROCESSING.json')['fit_ids']) == set(map(str,c.roles()['fit'])), 'Preprocessing source seal')
        entries[key] = {'seal':c.sha(run/key/'SEAL.json'),'files':seal['files']}
    c.write(run/'MODEL-FREEZE.json',{'package':package_sha, 'models':entries,'selection':'final192 only; before any final source'})
