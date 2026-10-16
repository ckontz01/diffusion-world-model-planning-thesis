"""Installed older Slurm: strictly bind the one unallocated cancelled group.

The failed V1 source/started/error are retained. This does not alter the old
published observer or invent allocated job rows. Original scheduler rows are
saved losslessly; the exact57 zero-time/unassigned tasks are coverage only.
"""
import json,sys
from . import inspect as v1
from .common import *
from .transport import call

BEFORE="""if len(rows)!=124 or {x[0] for x in rows}!={'317180_'+str(i) for i in range(124)}:raise ValueError('complete124 expanded terminal records')"""
AFTER="""original_rows=[list(x) for x in rows]
if len(rows)==68 and {x[0] for x in rows}=={'317180_'+str(i) for i in range(67)}|{'317180_[67-123%1]'}:
 group=next(x for x in rows if x[0]=='317180_[67-123%1]')
 if group[1]!='317180' or group[2].split()[0]!='CANCELLED' or group[3:]!=['0:0','0','4','None assigned']:raise ValueError('only exact zero-allocation cancelled57 placeholder')
 rows=[x for x in rows if x is not group]+[['317180_'+str(i)]+group[1:] for i in range(67,124)]
if len(rows)!=124 or {x[0] for x in rows}!={'317180_'+str(i) for i in range(124)}:raise ValueError('complete124 terminal logical coverage, no missing/duplicate row')"""

def program():
    from wm_diag0_rc1_grid_v1.scheduler import HISTORY
    code=v1.CODE
    if code.count("'--array',")!=1 or code.count(BEFORE)!=1:raise ValueError('exact diagnosed V1 preimage')
    code=code.replace("'--array',",'').replace(BEFORE,AFTER)
    code=code.replace("'scheduler':rows","'scheduler_raw_rows':original_rows,'normalized_zero_allocation_cancelled_indices':list(range(67,124))")
    code=code.replace("'old_PID':s['PID'] if False else 258808","'old_PID':258808")
    return 'OLD='+repr(OLD)+'\nGRID_HASH='+repr(GRID_HASH)+'\nHISTORY='+repr(HISTORY)+'\n'+code

def main():
    if not Path('D:/WSL/Thesis-Ubuntu/ext4.vhdx').is_file():raise RuntimeError('existing configured WSL path unavailable')
    if json.loads((DOC/'AUTHORITY-001.json').read_text())['direct_human_instruction']!=HUMAN:raise ValueError('latest human authorization')
    z=call('BINDING002',program(),seconds=160)
    print(json.dumps({'status':z['status'],'storage':z['storage'],'accepted_members_hashed':z['accepted_members_hashed']}))

if __name__=='__main__':main()
