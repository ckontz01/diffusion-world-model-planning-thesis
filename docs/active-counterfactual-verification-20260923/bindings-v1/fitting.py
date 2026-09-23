"""Explicit192 whole-source updates; same accepted architecture/loss/Adam."""
import common as c
import time
import numpy as np
from model import JointModel, OrdinaryModel, Preprocessing, Adam
from bayes import BayesianRegression


def assert_roles(data, expected, role):
    c.require(set(data['roles']) == {role}, 'Fitting/validation role boundary')
    c.require(set(map(str, data['source_ids'])) == set(map(str, expected)), 'Exact whole-source cohort')
    c.require(len(expected) == (64 if role=='fit' else 16), 'Fixed source count')
    c.require(data['x'].shape[1:] == (996,) and data['a'].shape[2:] == (212,) and data['r'].shape[1:] == (192,), 'D192 feature schema')


def train192(model, fit, validation, role_map=None, progress=None):
    rm = c.roles() if role_map is None else role_map
    assert_roles(fit, rm['fit'], 'fit'); assert_roles(validation, rm['validation'], 'validation')
    c.require(set(map(str,model.pre.fit_ids)) == set(map(str,rm['fit'])), 'Fit-only preprocessing')
    opt = Adam(model.params); trace = []; start = time.monotonic(); rng = np.random.default_rng(94013)
    sources = np.unique(fit['source_ids'])
    for update in range(1,193):
        order = rng.permutation(sources)
        keep = np.isin(fit['source_ids'], order[:64])
        c.require(keep.all(), 'Whole-source batch64 must contain entire fixed cohort')
        batch = {k:np.asarray(v)[keep] for k,v in fit.items()}
        loss, gradients, components = model.loss_and_grad(batch)
        opt.step(gradients)
        # Reporting only; no validation-driven branch changes or model selection.
        vloss, _, vcomponents = model.loss_and_grad(validation)
        trace.append({'update':update, 'fit_pre_update_loss':loss, 'fit_components':components,
                      'validation_post_update_loss':vloss, 'validation_components':vcomponents})
        if progress is not None: progress[:] = trace
    c.require(opt.t == 192, 'Exactly192 updates')
    final_fit = model.loss_and_grad(fit)[0]
    return {'updates':opt.t, 'whole_source_batch':64, 'seed':model.seed, 'parameters':model.parameter_count,
            'trace':trace, 'final_fit_loss':final_fit, 'final_validation_loss':trace[-1]['validation_post_update_loss'],
            'seconds':time.monotonic()-start, 'checkpoint_selection':'final update only', 'validation_selection':False}


def fit_job(kind, fit, validation, out, joint_dir=None, role_map=None):
    rm = c.roles() if role_map is None else role_map
    assert_roles(fit,rm['fit'],'fit'); assert_roles(validation,rm['validation'],'validation')
    if kind == 'joint':
        pre = Preprocessing.fit(fit)
        model = JointModel(996,212,192,seed=94011,preprocessing=pre)
    else:
        c.require(kind=='ordinary' and joint_dir is not None, 'Two frozen fit types')
        c.verify_seal(joint_dir)
        joint = JointModel.load(joint_dir/'joint.npz')
        model = OrdinaryModel(996,212,192,seed=94012,preprocessing=joint.pre)
    progress=[]
    try:result = train192(model,fit,validation,rm,progress)
    except BaseException:
        # Incomplete weights/history are evidence only, never a resumable fit.
        with (out/'PARTIAL-WEIGHTS.npz').open('xb') as f:np.savez(f,**{f'p{i}':v for i,v in enumerate(model.params)})
        c.write(out/'PARTIAL-FIT.json',{'completed_reporting_updates':len(progress),'trace':progress,
                                      'accepted_checkpoint':False,'resume_authorized':False})
        raise
    if kind == 'joint': model.save(out/'joint.npz')
    else:
        meta = {'kind':'ACV0-ordinary','preprocessing':'joint.npz','dims':model.net.dims,'seed':94012}
        with (out/'ordinary.npz').open('xb') as f:
            np.savez(f,metadata=np.array(c.json.dumps(meta)),**{f'p{i}':p for i,p in enumerate(model.params)})
        started = time.monotonic(); bayes = BayesianRegression(model).fit(fit)
        with (out/'bayesian.npz').open('xb') as f:
            np.savez(f,mean=bayes.mean,precision=bayes.precision,covariance=bayes.covariance)
        result.update(bayesian_seconds=time.monotonic()-started,bayesian_label='Bayesian last-layer approximation')
    c.write(out/'FIT.json',result)
    c.write(out/'PREPROCESSING.json',{'fit_ids':list(model.pre.fit_ids), 'provenance':'fit64 only; no validation/final fitting',
                                     'statistics_sha256':{k:__import__('bridge').array_hash(getattr(model.pre,k))
                                                        for k in ('xmean','xstd','amean','astd','rmean','rstd')}})
    return result


def model_freeze(run, package_sha):
    entries = {}
    for key in ('fit-joint','fit-ordinary'):
        seal = c.verify_seal(run/key)
        c.require(c.read(run/key/'FIT.json')['updates']==192, 'Fit update contract')
        c.require(set(c.read(run/key/'PREPROCESSING.json')['fit_ids']) == set(map(str,c.roles()['fit'])), 'Preprocessing source seal')
        entries[key] = {'seal':c.sha(run/key/'SEAL.json'),'files':seal['files']}
    c.write(run/'MODEL-FREEZE.json',{'package':package_sha, 'models':entries,'selection':'final192 only; before any final source'})


def load_models(run, *, require_freeze=True):
    if require_freeze:
        frozen = c.read(run/'MODEL-FREEZE.json')
        for key, v in frozen['models'].items():
            c.require(c.sha(run/key/'SEAL.json')==v['seal'], 'Model freeze identity')
    for key in ('fit-joint','fit-ordinary'): c.verify_seal(run/key)
    joint = JointModel.load(run/'fit-joint/joint.npz')
    ordinary = OrdinaryModel.load(run/'fit-ordinary/ordinary.npz',joint)
    bayes = BayesianRegression(ordinary)
    with np.load(run/'fit-ordinary/bayesian.npz',allow_pickle=False) as b:
        for k in ('mean','precision','covariance'):
            a=b[k]; c.require(np.isfinite(a).all(),'Bayesian finite checkpoint'); setattr(bayes,k,a.copy())
    c.require(bayes.mean.shape==(65,) and bayes.precision.shape==bayes.covariance.shape==(65,65),'Bayesian shape')
    return joint,ordinary,bayes
