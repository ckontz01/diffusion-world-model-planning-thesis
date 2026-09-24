"""Same-source, same-selected-action prefix coupling; no efficacy interpretation.

Controller uses only bounded digests of authenticated saved fields. Independent
analysis compares the actual saved array bytes, keeping one source block in RAM.
No grouping by policy, seed, prefix index, outcome or unexecuted suffix is used.
"""
import common as c
import hashlib

FIELDS=('state','proprio','dynamics','latent','pixel_hash','flags','action')

def digest(fields):
    h=hashlib.sha256()
    for key in sorted(fields):
        a=fields[key];h.update(c.canonical([key,a.dtype.str,list(a.shape)]));h.update(a.tobytes(order='C'))
    return h.hexdigest()

def projection(a,m):
    import numpy as np
    c.require(m['kind']=='evaluation' and len(m['branches'])==1,'One saved evaluation episode')
    b=m['branches'][0];n=b['prefix_steps']
    c.require(type(n) is int and n==min(5,b['steps']) and 1<=n<=5,'Recorded actual prefix length')
    c.require(b['plans'][0]['start']==0,'Prefix begins at initial state')
    selected=a['b0/plan0'][:5]
    c.require(selected.shape==(5,2) and np.isfinite(selected).all(),'Complete selected prefix action identity')
    flags=a['b0/flags'][:n]
    c.require(flags.shape==(n,2) and not flags[:-1].any() and not flags[:,1].any(),'Prefix native flags')
    c.require(bool(flags[-1,0])==(b['steps']<=5),'Terminal prefix length/flags consistent')
    np.testing.assert_array_equal(a['b0/clock'][:n],np.arange(1,n+1))
    fields={'selected_actions':selected,'recorded_length':np.asarray(n,dtype=np.int64),
            'requested_initial':a['requested_initial'],'initial_image':a['initial_image']}
    for key in FIELDS:
        fields['initial_'+key]=a['b0/initial_'+key]
        fields[key]=a['b0/'+key][:n]
        c.require(len(fields[key])==n,'Missing recorded prefix steps')
    for key in ('clock','remaining','plan_index','plan_offset','prefix_images'):
        fields[key]=a['b0/'+key][:n]
        c.require(len(fields[key])==n,'Missing recorded prefix history')
    return selected,fields

def technical(a,m):
    selected,fields=projection(a,m)
    return dict(schema='ACVM1-prefix-coupling-v1',reference=m['reference'],
                action_sha256=digest({'selected_actions':selected}),
                prefix_steps=m['branches'][0]['prefix_steps'],history_sha256=digest(fields))

def check_technical(records):
    groups={};count=0
    for r in records:
        c.require(set(r)=={'schema','reference','action_sha256','prefix_steps','history_sha256'} and
                  r['schema']=='ACVM1-prefix-coupling-v1' and type(r['reference']) is int and
                  type(r['prefix_steps']) is int and 1<=r['prefix_steps']<=5,'Bounded prefix digest schema')
        for name in ('action_sha256','history_sha256'):
            c.require(type(r[name]) is str and len(r[name])==64 and all(x in '0123456789abcdef' for x in r[name]),'Prefix digest identity')
        key=(r['reference'],r['action_sha256']);value=(r['prefix_steps'],r['history_sha256'])
        if key in groups:c.require(groups[key]==value,'Cross-episode same-action prefix history mismatch')
        groups[key]=value;count+=1
    return dict(schema='ACVM1-prefix-coupling-v1',records=count,action_groups=len(groups),passed=True)

def check_actual(groups,a,m):
    """Independent array check: no trust in TECHNICAL.json or matching digests."""
    selected,fields=projection(a,m);key=(m['reference'],digest({'selected_actions':selected}))
    if key in groups:
        old=groups[key];c.require(set(fields)==set(old),'Prefix field coverage')
        for name,value in fields.items():
            other=old[name]
            c.require(value.dtype==other.dtype and value.shape==other.shape and
                      value.tobytes(order='C')==other.tobytes(order='C'),
                      'Cross-episode same-action prefix array mismatch: '+name)
    else:groups[key]={name:value.copy() for name,value in fields.items()}
    return len(groups)
