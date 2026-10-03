# One finite proposed grid, not execution authority

wm_diag0.resource_plan prints checked arithmetic. Four settings,32 diagnostic parents/task,16 candidates/source/backbone and two evaluation draws. No substitution, hidden fit work, automatic retries or cap expansion. Authentication may show this grid incompatible; then return the exact blocker.

| Work | Maximum |
|---|---:|
| Source/backbone banks and fresh bank-helper worlds |128 |
| Independent oracle-prefix worlds (25-action prefix) |2,048 |
| Evaluation candidate-tail worlds (50 total actions) |4,096 |
| Total fresh worlds, including helpers |6,272 |
| Readout fit/validation frames |1,024 /384 |
| Historical replay per fresh world |≤200 controller actions |
| Total physical controller steps, replay included |1,510,400 |
| Native CEM sequences: bank + at most one tail replan |38,016,000 |
| Retained-bank reforecast sequences |2,048 |
| Predicted macro transitions at horizon5 |190,090,240 |
| Batched population/bank cost calls |126,848 |
| Batched predictor calls, five per cost call |634,240 |
| Context/goal encoder calls, ≤two per cost call |253,696 |

Counts are **conditional on the authenticated native 300-population/30-iteration/horizon5/grouping5 interface**. They are not proof that the released DINO implementation fits. The encoder call cap allows up to3 context frames +1 goal frame per cost call:507,392 image frames; readout history adds≤4,224; oracle realized history≤30,720, totaling≤542,336 encoded image frames. Verify native rescore/tail internals; additional native calls must fit these bounds or the proposal blocks. Simulator internal substeps/action repeat are additional to controller counts: exact per-task factors must be bound before launch, not omitted or called equal across tasks.

## Jobs and hard envelopes

Propose serial one exact NVIDIA RTX6000 Ada on gpu09/gpu09.cluster,4CPU/8GiB per GPU allocation.128 parent/backbone jobs×3,600s (3,540 work+60 preservation) and4 readout feature/fit/validation jobs×1,800s (1,740+60). Aggregate **468,000 GPU allocation seconds (130 hours)**, including all failed attempts. CPU preflight1,200s and analysis3,600s each4CPU/8GiB; aggregate4,800 CPU-stage allocation-wall seconds. Successful logical tasks134 (132GPU+2CPU). No separate sampler/pilot/training job is implicitly granted.

The included technical tranche is the first diagnostic parent in each of four settings (four already-counted GPU jobs), after all four counted readout jobs. It checks action/encoder/replay/selection/endpoint identities, not efficacy, and is never repeated to select favorable tasks. Any failure is preserved/charged; reconcile every live/terminal/ambiguous allocation and accepted seal before a smallest versioned technical repair. No successful/live/ambiguous work is resubmitted. A genuine replacement needs a finite full-future reservation within unchanged cumulative caps; no implicit replacement allowance is assumed.

Save real action arrays, endpoint-state traces and observation hashes, not full replay RGB videos. Full patch features are retained at declared score positions. Per parent worker70MB +1MB log; readout worker500MB +1MB log; CPU preflight1MB/analysis50MB +1MB log each. Source closures20MB total, controls300MB, reused weights≤2GB, live≤12GB, archive≤14GB, inclusive≤42GB across cluster/local/SSD and failures. Maximum DINO layout256×384 float32 is a planning bound; any larger native layout blocks rather than pooling. Preserve all failed/partial/evidence records.

## Throughput assumptions and uncertainty

Historical Le-WM saved-input/native first-decision timing is only a planning lead (~3s per30-population CEM decision), not measured closed-loop WM-DIAG0 timing. One source job has at most33 CEM decisions (bank+32 tails):~99s Le-WM planning under that lead. Physical workload per job≤11,800 controller actions; hypothetical .005/.02/.05s each adds59/236/590s. Add30–120s setup/encoding/preservation overhead. DINO planning could be8–32× slower:792–3,168s before physics/overhead. The slow32×+590+120=3,878s scenario **exceeds3,540s work** and would fail this finite envelope. These are labelled scenarios, not a throughput guarantee or authority to extend time. No research timing pilot is authorized now.

## Preparation and preservation

Local scripted tests: cumulative14,400s,4CPU,8GiB,1GB new outputs, each future test fully reserved600s. All attempts, including failures, retained in test-receipts/. Native existing Python/NumPy only. No research models, data forwards, fitting, physics, GPU/Slurm or monitor.

Only the new study's small preparation package is archived once to D:/THESIS-BACKUPS/world-model-diagnostic-20261004 on THESIS_SSD volume0a2f1ba9-0000-0000-0000-100000000000, native Windows only,≥40GB free, whole SHA256 and every member checked against immutable Git contents. Existing historical packages are not recreated. Future study preservation remains subject to its complete independent acceptance and explicit execution contract; preparation backup is not a scientific acceptance gate.
