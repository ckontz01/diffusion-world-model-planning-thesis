"""Bounded scheduler read: purged live queue IDs require exact terminal history."""
SOURCE=r'''
def exact_snapshot(ids,required_logical):
 a=subprocess.check_output(['sacct','-X','-n','-P','-j',ids,'--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
 rows=[x.split('|') for x in a.splitlines() if x.strip()]
 if any(len(x)!=7 for x in rows) or len({x[0] for x in rows})!=len(rows):raise ValueError('exact unique scheduler columns')
 p=subprocess.run(['squeue','-h','-j',ids,'-o','%i|%T|%M|%N|%R'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
 note={'returncode':p.returncode,'stderr':p.stderr,'invalid_live_queue_id_authenticated_by_complete_terminal_history':False}
 if p.returncode:
  terminal={'COMPLETED','FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL','PREEMPTED','BOOT_FAIL','DEADLINE','REVOKED'}
  if p.returncode!=1 or p.stdout.strip() or p.stderr.strip()!='slurm_load_jobs error: Invalid job id specified' or {x[0] for x in rows}!=set(required_logical) or any(x[2].split()[0] not in terminal for x in rows):
   raise RuntimeError('queue unavailable/ambiguous; not proof of terminal allocations: '+p.stderr)
  note['invalid_live_queue_id_authenticated_by_complete_terminal_history']=True
 return p.stdout,a,note
'''

HISTORY=r'''
HISTORY_EXPECTED={
 '317163_0':('317167','COMPLETED','0:0',27),'317163_1':('317168','COMPLETED','0:0',20),
 '317163_2':('317169','COMPLETED','0:0',27),'317163_3':('317163','COMPLETED','0:0',20),
 '317164_0':('317170','COMPLETED','0:0',65),'317164_1':('317171','FAILED','125:0',77),
 '317172':('317172','COMPLETED','0:0',13),'317173':('317173','COMPLETED','0:0',19),
 '317174':('317174','COMPLETED','0:0',19),'317175_1':('317176','COMPLETED','0:0',22),
 '317175_3':('317175','COMPLETED','0:0',22),
 '317177_1':('317178','COMPLETED','0:0',None),'317177_2':('317179','COMPLETED','0:0',None),'317177_3':('317177','COMPLETED','0:0',None)}
HISTORY_UNALLOCATED={'317166','317164_[2-3%1]','317165_[0-123%1]'}
def all_before_grid(raw):
 rows=[x.split('|') for x in raw.splitlines() if x.strip()];found={};charge=0;raw_seen=set();technical=[]
 for x in rows:
  if len(x)!=7:raise ValueError('historical exact columns')
  k,j,state,exitcode,seconds,cpus,node=x
  if k in found or not seconds.isdigit() or cpus!='4':raise ValueError('unique historical identity')
  found[k]=x;n=int(seconds)
  if k in HISTORY_UNALLOCATED:
   if not state.startswith('CANCELLED') or n!=0 or node!='None assigned':raise ValueError('old cancelled unallocated placeholder changed')
   continue
  if k not in HISTORY_EXPECTED:raise ValueError('unexpected old attempt, reconcile before action')
  ej,es,ee,en=HISTORY_EXPECTED[k]
  if j!=ej or state!=es or exitcode!=ee or node not in ('gpu09','gpu09.cluster') or j in raw_seen or not 0<n<=3600 or (en is not None and n!=en):raise ValueError('failure-inclusive old terminal history changed')
  raw_seen.add(j);charge+=n
  if k.startswith('317177_'):technical.append(x)
 if set(found)!=set(HISTORY_EXPECTED)|HISTORY_UNALLOCATED or len(raw_seen)!=14 or charge-sum(int(x[4]) for x in technical)!=331:raise ValueError('all14allocated attempts including failures and331historical seconds')
 if charge+124*3600>468000:raise ValueError('full remaining124future reservation')
 return technical,charge
'''
