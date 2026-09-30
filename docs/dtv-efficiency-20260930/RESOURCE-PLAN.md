# Finite profiling resource contract — proposed, not launched

| Resource | Fixed reservation |
| --- | ---: |
| Workers | 9: three tasks × three existing scorer seeds; serial |
| Per worker | 1 exact RTX 6000 Ada, 4 CPU, 8 GiB, 800 allocation seconds |
| Work/preservation boundary | 740 seconds work + 60 seconds preservation |
| Aggregate GPU allocation | 9 × 800 = 7,200 seconds = 2 hours, including failures |
| Complete CEM workload | 140 solves/worker; 1,260 total, of which 900 warmed timed |
| CEM configuration | 300 candidates × 5 transitions × 30 rounds; 30 elites |
| Timing repetitions | 5 balanced blocks × 2 repetitions; all 5 methods; 2 contexts/worker |
| Offline A lane | ACID/forward/legacy, 2 full passes each after one 300-sequence warmup |
| Worker artifacts | 4,000,000 bytes/worker, including seal or preserved failure |
| Console logs | 2,000,000 bytes combined stdout/stderr per worker |
| Package reservation | 4,000,000 bytes; exact freeze inventory checked |
| Other controller/report metadata | 2,000,000 bytes; dispatch ledger at most 1,000,000 |
| Full live bound | 9 × (4 + 2) MB + 4 MB + 2 MB = 60 MB |
| Archive bound | 60 MB contents + 2 MB tar header/padding allowance = 62 MB |
| Inclusive new artifacts | 250 MB, including live, archive, preparation/copies and failures |
| CPU-only final acceptance/preservation | at most 600 local wall-seconds, 4 threads, 8 GiB |

Existing checkpoints and saved inputs are authenticated and read in place;
their hundreds of MB are not copied into the small result archive. The source
package is included once. No thousands-of-episodes campaign or simulator work
is in this reservation. Only existing legitimate site/env/container routes
are used; no dependency, permission, WSL or account changes.

140 solves/worker consists of 100 warmed timed, 20 original/trace equivalence,
10 post-equivalence reset and 10 warmup solves. The first original solve in
each equivalence pair is timed separately, not an extra solve. First B0
reproduction, independent scaling checks, first cost calls, A/B warmups,
offline passes, hashes and loading are also included in the 800 seconds.
No favorable outcome is needed for technical acceptance.

The historical 1.6–1.81-second solve medians give a direct scenario of
approximately 1,260 × (1.6–1.81) / 60 = **33.6–38.0 minutes** for CEM work
alone. This is neither a total forecast nor a new measurement: source/RNG
paths, setup/equivalence, overhead and runtime variability may differ. It
does not justify shorter timeouts or extra work. Retain the full two-hour
ceiling; preserve and report a specific arithmetic/scope fault if it cannot fit.

The controller reserves the entire future grid before the first submission
and all remaining maximum durations before each next job. Intent/raw response
precede allocation acceptance. Exactly one attempt per task; no requeue,
duplicate, restart, automatic retry or cap reset. Terminal faults are charged
before refusal; live/ambiguous work must be reconciled before any new decision.
Worker and supervisor check scoped output/log limits outside headline timers.
Their checks are fail-stops, not a guarantee against a large external crash
message overshooting a log threshold between checks; such a fault and its
retained bytes still count against the inclusive bound.

One final source-authenticated report must retain all cells and outcomes of
technical checks. The result-only archive must include source/approval,
allocation/charge/raw control records, profiles/seals/failures and report,
without checkpoint/input copies or hidden exclusions. Create it once, retain
failed partials, transfer natively to designated THESIS_SSD with at least
40 GB free, then authenticate exact bytes and every member. No fallback disk,
evidence deletion, old-study rearchive or blind transfer retry is permitted.

These are proposed timing ceilings. Current preparation is separately bounded
by two cumulative local scripted wall-hours, four CPU threads, 8 GiB and
250 MB new artifacts, with instrumented receipts and a conservative charge
for uninstrumented checks in `PREPARATION-ACCOUNTING.json`.
