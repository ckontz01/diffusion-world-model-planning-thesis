# Corrected finite reservations — proposed research ceilings only

| Resource | Corrected fixed contract |
| --- | ---: |
| Workers | 9, serial, unchanged task/seed order |
| Worker | 1 exact RTX 6000 Ada on gpu09, 4 CPUs, 8 GiB |
| Slurm time | `00:13:00`, 780 seconds per worker |
| Work / preservation | 720 / 60 seconds |
| Complete future grid | 9 × 780 = 7,020 seconds = 117 minutes |
| Aggregate actual GPU allocation ceiling | 7,200 seconds = 120 minutes, failures included |
| Slack between reservation and aggregate ceiling | 180 seconds, not extra-work authority |
| CEM solves | 140/worker; 1,260 total, including 900 warmed timed solves |
| CEM shape | 300 candidates, 5 transitions, 30 rounds, 30 elites |
| Full worker artifacts | 4,000,000 bytes each, all seals/journals or failure |
| Worker stdout + stderr | 2,000,000 bytes per worker |
| Complete frozen source dependencies | 4,000,000 bytes |
| Other controller/report metadata | 2,000,000 bytes; ledger threshold 1,000,000 |
| Full live bound | 9 × (4 + 2) MB + 4 MB + 2 MB = 60 MB |
| One result archive | 62 MB, including 2 MB tar metadata/padding reservation |
| Inclusive new result artifacts | 250 MB, all retained failures/copies included |
| CPU final acceptance/preservation | at most 600 wall seconds, 4 threads, 8 GiB |

No work was removed. 140 solves/worker includes 100 warm timed, 20
original/trace equivalence, 10 post-equivalence reset and 10 warmup solves.
The first original equivalence solve is separately timed, not an extra solve.
All A/B calls, first B0 reproduction, loading/authentication, hashes,
independent equivalence/scaling and 2 offline repetitions per
ACID/forward/legacy arm also remain inside the worker reservation.

The initial full-grid reservation is 7,020. Before each next submission,
known actual charges plus every remaining 780-second worker reservation
must stay below 7,200. Terminal failures/timeouts still charge; unresolved
allocations prevent another submission rather than receiving guessed charges.
No blind retry, evidence deletion, hidden footprint or cap reset is permitted.

Supervisor journals are included in the worker's 4 MB, not hidden in a second
namespace. Child RSS is a scoped process measure, not aggregate node memory;
Slurm's 8 GiB envelope also includes the lightweight supervisor. Output/log
checks cannot guarantee no overshoot from a large external error between
checks. Retain and account for any overshoot; do not erase evidence to fit.

These are proposed ceilings, not current spending authority. The correction
itself is separately limited to 1,800 cumulative local scripted wall seconds,
4 CPU threads, 8 GiB and 50 MB new artifacts. Suite receipts charge full
Windows-to-WSL startup time, not only nested test time. A conservative
600-second reserve covers other local scripts and eventual publication/backup.
No GPU, Slurm, real checkpoint, Le-WM or simulator test is permitted.
