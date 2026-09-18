# LGP1 staged resource proposal — NOT launch authorization

One recommended envelope, one A6000 at a time, no parallel GPU expansion.
Use the existing pinned runtime/container and approved site account/QoS; no
dependency installation or environment mutation. The estimates below are not
measured throughput of the new models. This preparation made no real-model calls.

| Stage | Fixed workload | Maximum allocations | GPU allocation-hour ceiling |
|---|---|---:|---:|
| Shared cache | 80k fit + 8k val rows; three history/far encodings and one local target per eligible row | 1 x 4h | 4 |
| Matched training | 2 families x 3 seeds x 12k updates x batch128 | 6 x 4h | 24 |
| Technical integration | 2 refs x 2H x 2 families, seed8301; independent slot/lifecycle checks within these jobs | 4 x 20min | 1.3333 |
| Development | 32 refs x 2H x 2 families x 3 seeds | 192 x 20min (one reference/H pair per model) | 64 |
| Total | 384 primary + 8 technical episodes; no live reference-system arms | **203 GPU jobs max** | **93.3333 (336,000s)** |

CPU: at most one 4CPU/8GiB/7200s allocation for preparation sealing, aggregation
and verification after compute; host dispatch/transfer CPU and time reported
separately, not falsely counted as GPU work. GPU jobs request4CPU/24GiB/oneA6000.
All failed/technical allocations count; no automatic retries, replacement seeds,
changed rows or larger envelope. Existing successful artifacts are never repeated.

## Actual-cost checks and staged release

The envelope is conservative, not a request to spend it all. After authorization,
first cache generation checks row/role/alignment validity and measured throughput.
Every first256 training updates are part of that fit's12,000, not an extra trial;
use elapsed/resource statistics only. If conservative projected completion
(1.5 x observed seconds/update for remaining updates) does not fit the allocation,
stop with preserved artifacts before consuming the remainder. Do not inspect
validation performance to alter budget or architecture. No automatic resumption.

Training sensitivity arithmetic: 72,000 updates at 0.1/0.5/1.0seconds/update
means2/10/20GPU-hours, before validation and I/O. At more than roughly1.1s/update,
a4h fit becomes tight; it is not silently extended. No guarantee of these rates.

Closed-loop maximum per H75/H150 pair is30 planning stages and450 physical actions.
One stage scores30 populations of300 candidate15-action chunks:9,000candidate
trajectories and135,000predicted primitive steps. Thus:

- Primary maximum:5,760stages;51,840,000candidate trajectories;
  777,600,000predicted primitive steps;86,400actual delivered actions.
- Technical maximum:120stages;1,080,000candidate trajectories;
  16,200,000predicted primitive steps;1,800actual actions.
- Early success reduces actual workloads, not the allocated case set.

At0.5/2/5seconds per300-candidate cost population, main scoring alone would take
24/96/240hours. Therefore the64h main-stage envelope is **not guaranteed feasible**:
the technical stage must measure a conservative complete-stage time comfortably
below40seconds including proposal generation and physics to fit the20min pair
allocations. Account for diffusion separately. If not, return measured cost and
stop; reducing rounds, candidates, references or seeds needs a new explicit
design approval. This avoids presenting a strong30-round planner as cheap.
Cache/fits may finish yet the development envelope may be infeasible; that risk
is explicit. No overnight full-grid assumption hides it.

Report proposer generation time (GMM once; diffusion five calls), generator,
LeWM scoring, CEM reduction, physics, transfer and totalallocation time separately.
Equal candidate counts and equal CEM rounds do not imply equal compute.

## Storage

Proposed cap **12,000,000,000new bytes on cluster**, plus a byte-verified external
SSD copy of that evidence (total two-location cap24GB). Existing read-only data
and checkpoints are not copied into a new cache unnecessarily. Minimum40GB free
on designated THESIS_SSD before final backup; no laptop fallback. Remote compute
must not depend on laptop/SSD liveness after launch. Backup is after compute.

Expected shared float32cache payload roughly0.36GB (960latent +11state +30action
coordinates per row, before metadata); no RGB image duplication. Six final weights
are a few hundredMB; six optional optimizer states for technical preservation
can raise this to about1GB. No rolling checkpoint history or full CEM candidate
trace retention. Per-episode compressed diagnostics capped10MB,384main plus
8technical <=3.92GB; source/control/log reserve0.2GB; aggregate and one sealed
archive fit the12GBcluster cap if payload stays<=5.9GB. Check byte accounting
before each stage and archive; stop rather than delete historical evidence.

Record every source hash, eligible-role and selected-row manifest, normalization,
generator/model/input lock, six final checkpoints, per-source outcomes and
technical accounting. Seal workers before reading aggregate outcomes. Verify
archive and every copied member SHA256 on external SSD. Do not claim backup
from an HTTPhealthcheck, fileexistence or a completed computation marker.

## Decision requested later

Bindings are now implemented and synthetically tested (PROTOCOL §10 and
IMPLEMENTATION-COMPLETION.md). The next decision is approval of this exact
bounded launch package, not another general design review. An approval must bind
its source manifest, input lock, data roles, resources and accounting. The
generated disabled template grants nothing. No real inference, GPU allocation,
research training or simulator execution was launched here.

## Completed execution accounting clarifications

Each 4h fit includes final-checkpoint validation: 8,000 loss rows and 300
sampled action chunks per validation row (2.4 million chunks per fit). These
are supporting offline diagnostics within the same fit allocation, not an
extra job or checkpoint-selection rule. All six fits include this cost. It is
not safe to estimate fit feasibility from optimizer time alone: the wall guard
covers validation, authentication, checkpoint I/O and checks as well.

Cache and fitting guards inspect timing after 256 existing rows/updates. The
cache estimate covers the remaining cache rows; fitting projection covers
remaining updates and cannot guarantee that validation will fit. A timeout in
validation still stops the chain, even if the fixed final weights exist. No
workload is reduced to fit. Technical integration uses a 1.5x worst observed
planning-stage plus per-action delivery estimate for a full 30-stage pair.

Wrapper/container authentication is part of Slurm allocation wall time. Worker
wall/CPU/RSS are separately recorded and cannot replace terminal Slurm charges.
Host-side dispatch, final archive construction, copied-member verification and
transfer consume no extra scheduler allocation and are reported separately.
The one CPU job is final complete-grid aggregation and independent worker checks.

Worker payload <=5.9GB; source/root control/logs <=200MB; every episode <=10MB
(each two-horizon worker <=20MB). One uncompressed final archive is reserved
from actual bytes before creation; payload plus source/control plus tar overhead
and archive must remain <=12GB. Two times the individual subcaps would exceed
12GB, so archive creation must check the total, not assume subcaps guarantee it.
No deletion or laptop fallback is used to satisfy a cap.
